"""
Extraction Node — Step 3 of the BGV pipeline.

Document-type specific Gemini prompts designed for cross-document verification:
  - cv_resume:      Extracts the claimed employment profile (becomes baseline)
  - epfo_history:   Extracts employer records to verify against CV claims
  - bank_statement: Extracts salary credits to verify unconfirmed CV employers

Error handling:
  - Quota exhausted (429) → evaluation_result=NEEDS_REVIEW, graph exits cleanly
  - Any other API error   → same graceful exit with diagnostic reasoning
"""

import json
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.graph.state import VerificationState

# ─── LLM singleton ────────────────────────────────────────────────────────────
_llm = ChatGoogleGenerativeAI(
    model=settings.gemini_model,
    google_api_key=settings.google_api_key,
    temperature=0,
)

# ─── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a document data extraction assistant for an HR background verification system.
Extract ONLY the fields listed below. Return a valid JSON object and NOTHING else.
Do not add explanations, markdown fences, or any text outside the JSON.
If a field is not found, use null. For lists with no items, use [].
IMPORTANT: The text contains masked tokens like [MASKED_UAN_0] or [MASKED_EMAIL_0].
Preserve these tokens exactly in your output — do NOT replace them with guesses."""

# ─── Document-type prompts ────────────────────────────────────────────────────

PROMPTS = {

    # ── CV / Resume ────────────────────────────────────────────────────────────
    # This becomes the baseline "claimed profile" against which EPFO and bank
    # statements are cross-verified. Extract as much employment detail as possible.
    "cv_resume": """Extract these fields from the CV / resume below.
This data becomes the candidate's CLAIMED PROFILE used for cross-verification.
Be precise about employer names and dates — these will be checked against EPFO records.

Return JSON exactly in this structure:
{{
  "full_name": "string or null",
  "email": "masked token or null",
  "phone": "masked token or null",
  "current_employer": "string or null",
  "employment_history": [
    {{
      "company_name": "string — use the full official company name",
      "job_title": "string or null",
      "start_date": "string in format YYYY-MM or MM/YYYY or as written, or null",
      "end_date": "string or null — use 'Present' if current",
      "employment_type": "Full-time / Contract / Intern or null",
      "location": "string or null"
    }}
  ],
  "education": [
    {{
      "institution": "string",
      "degree": "string",
      "field": "string or null",
      "year": "string or null"
    }}
  ],
  "skills": ["string"],
  "declared_uan": "masked token or null"
}}

Document text:
{masked_text}""",

    # ── EPFO Passbook / Service History ────────────────────────────────────────
    # Used to cross-verify CV-claimed employers, dates, and gaps.
    "epfo_history": """Extract these fields from the EPFO passbook / service history below.
This data will be cross-verified against the candidate's CV to confirm claimed employers,
detect hidden employment, and identify date discrepancies.

Return JSON exactly in this structure:
{{
  "member_name": "string or null",
  "uan": "masked token or null",
  "pan": "masked token or null",
  "employers": [
    {{
      "employer_name": "string — use full official name",
      "establishment_id": "string or null",
      "member_id": "string or null",
      "date_of_joining": "string in YYYY-MM-DD or DD/MM/YYYY as written, or null",
      "date_of_exit": "string or null — use null if currently employed",
      "is_current": true or false,
      "monthly_wage": "string or null",
      "epf_contribution_months": "number or null"
    }}
  ],
  "total_balance": "string or null",
  "statement_date": "string or null"
}}

Document text:
{masked_text}""",

    # ── Bank Statement ──────────────────────────────────────────────────────────
    # Requested only when EPFO cannot confirm a CV-claimed employer.
    # Focus on salary credits and employer name in narration.
    "bank_statement": """Extract these fields from the bank statement below.
This data will be used to verify salary credits from a specific employer
that could not be confirmed via EPFO.

Pay special attention to:
- Transaction narrations containing employer names (e.g. "SALARY/WIPRO/JUNE")
- Regular monthly credits that look like salary payments
- Account holder name (critical — must match the candidate's name)

Return JSON exactly in this structure:
{{
  "account_holder_name": "string or null",
  "account_number": "masked token or null",
  "ifsc_code": "masked token or null",
  "bank_name": "string or null",
  "statement_period": {{
    "from": "string or null",
    "to": "string or null"
  }},
  "closing_balance": "string or null",
  "salary_credits": [
    {{
      "date": "string",
      "amount": "string",
      "narration": "string — full transaction description",
      "employer_hint": "string or null — employer name if identifiable from narration"
    }}
  ],
  "all_transactions": [
    {{
      "date": "string",
      "description": "string",
      "debit": "string or null",
      "credit": "string or null",
      "balance": "string or null",
      "type": "credit or debit"
    }}
  ]
}}

Document text:
{masked_text}"""
}


def _clean_json_response(raw: str) -> dict:
    """Strip markdown fences and parse JSON."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


def _is_quota_error(e: Exception) -> bool:
    """Detect Google API quota / rate-limit errors."""
    msg = str(e).lower()
    return any(kw in msg for kw in [
        "quota", "rate limit", "resource_exhausted", "429",
        "too many requests", "exceeded",
    ])


def extraction_node(state: VerificationState) -> dict:
    """
    LangGraph node: calls Gemini with masked_text and document-type prompt.
    Returns extracted_data dict.

    On quota exhaustion the node sets evaluation_result=NEEDS_REVIEW so the
    graph routes to human review rather than crashing.
    """
    doc_type = state.get("document_type", "cv_resume")
    masked_text = state.get("masked_text", "")
    reasoning = list(state.get("reasoning", []))

    reasoning.append(f"[EXTRACT] Sending {doc_type} to Gemini for structured extraction")

    prompt_template = PROMPTS.get(doc_type, PROMPTS["cv_resume"])
    user_prompt = prompt_template.format(masked_text=masked_text[:8000])

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = _llm.invoke(messages)
        raw_content = response.content

        extracted_data = _clean_json_response(raw_content)
        field_count = len(extracted_data)
        reasoning.append(f"[EXTRACT] Gemini returned {field_count} top-level fields")

        # Log key extracted items for transparency
        if doc_type == "cv_resume":
            employers = [e.get("company_name", "?") for e in extracted_data.get("employment_history", [])]
            reasoning.append(f"[EXTRACT] CV employers found: {employers}")
        elif doc_type == "epfo_history":
            employers = [e.get("employer_name", "?") for e in extracted_data.get("employers", [])]
            reasoning.append(f"[EXTRACT] EPFO employers found: {employers}")
        elif doc_type == "bank_statement":
            salary_count = len(extracted_data.get("salary_credits", []))
            reasoning.append(f"[EXTRACT] Salary credits identified: {salary_count}")

        reasoning.append("[EXTRACT] Complete — extracted_data populated (masked tokens preserved)")
        return {"extracted_data": extracted_data, "reasoning": reasoning}

    except json.JSONDecodeError as e:
        reasoning.append(f"[EXTRACT] JSON parse error: {str(e)} — returning empty dict")
        return {"extracted_data": {}, "reasoning": reasoning}

    except Exception as e:
        if _is_quota_error(e):
            # ── Graceful quota exhaustion ─────────────────────────────────────
            reasoning.append(
                "[EXTRACT] ⚠️  Gemini API quota exhausted (HTTP 429). "
                "Extraction skipped — routing to human review for manual processing."
            )
            reasoning.append(
                "[EXTRACT] Action: Wait for quota reset or upgrade plan at "
                "https://aistudio.google.com"
            )
            return {
                "extracted_data": {},
                "evaluation_result": "NEEDS_REVIEW",
                "discrepancies": [{
                    "field": "gemini_extraction",
                    "expected": "Successful LLM extraction",
                    "found": "Quota exhausted — manual review required",
                    "confidence": 0,
                    "severity": "review",
                }],
                "reasoning": reasoning,
            }
        else:
            reasoning.append(
                f"[EXTRACT] LLM call failed: {str(e)[:200]}. Routing to human review."
            )
            return {
                "extracted_data": {},
                "evaluation_result": "NEEDS_REVIEW",
                "discrepancies": [{
                    "field": "gemini_extraction",
                    "expected": "Successful LLM extraction",
                    "found": f"API error: {str(e)[:100]}",
                    "confidence": 0,
                    "severity": "review",
                }],
                "reasoning": reasoning,
            }
