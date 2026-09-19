"""
Evaluation Node — Step 4 of the BGV pipeline.

Cross-document rule engine — NO LLM calls.

Routing outcomes:
  PASSED          → demasking node (all checks passed)
  NEEDS_REVIEW    → human_review_node (discrepancies need admin decision)
  NEEDS_FALLBACK  → fallback_node (CV employer missing from EPFO → need bank statement)

─── Document-type logic ──────────────────────────────────────────────────────

CV_RESUME (processed first, becomes the baseline):
  - Extracts the "claimed profile" (employers, dates, name)
  - Compared against offer_reference_data if available
  - Passes easily — we're just verifying the CV was readable
  - Stored in DB as cv_profile for later EPFO/bank cross-verification

EPFO_HISTORY (verified AGAINST cv_profile):
  - CV employers → are they all in EPFO? → if missing → NEEDS_FALLBACK (need bank stmt)
  - EPFO employers not in CV → potential hidden employment → NEEDS_REVIEW
  - Name match: cv_profile.full_name vs epfo.member_name
  - UAN consistency if declared in CV
  - Date mismatches per employer → NEEDS_REVIEW
  - Timeline gaps (months between EPFO exits and joins)

BANK_STATEMENT (verified AGAINST cv_profile, triggered by NEEDS_FALLBACK):
  - Account holder name vs cv_profile.full_name → HIGH RISK if mismatch
  - Salary credits from the unconfirmed CV employer (check narrations)
  - Monthly salary frequency and amount consistency
  - Date coverage aligns with CV employment dates
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from rapidfuzz import fuzz

from app.graph.state import VerificationState

# ─── Thresholds ───────────────────────────────────────────────────────────────
EMPLOYER_MATCH_PASS    = 80   # employer name fuzzy match to consider it found
EMPLOYER_MATCH_REVIEW  = 60   # below this → hard flag
NAME_MATCH_PASS        = 80
NAME_MATCH_REVIEW      = 65
DATE_GAP_REVIEW_DAYS   = 45   # employment date difference that triggers review


# ─── Utilities ────────────────────────────────────────────────────────────────

def _norm(val: Any) -> str:
    return str(val or "").lower().strip()


def _fuzzy(a: str, b: str) -> float:
    """token_set_ratio handles "Tata Consultancy Services" vs "TCS Ltd" better."""
    return fuzz.token_set_ratio(_norm(a), _norm(b))


def _best_match(query: str, candidates: List[str]) -> float:
    if not candidates:
        return 0.0
    return max(_fuzzy(query, c) for c in candidates)


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Try multiple date formats; return None on failure."""
    if not date_str or _norm(date_str) in ("present", "current", "null", "none", ""):
        return None
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%Y", "%Y-%m",
        "%B %Y", "%b %Y", "%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _date_diff_days(d1_str: Optional[str], d2_str: Optional[str]) -> Optional[int]:
    d1, d2 = _parse_date(d1_str), _parse_date(d2_str)
    if d1 and d2:
        return abs((d1 - d2).days)
    return None


def _add_discrepancy(
    discrepancies: list,
    field: str,
    expected: Any,
    found: Any,
    confidence: float,
    severity: str,   # "review" | "mismatch" | "missing" | "hidden_employment"
):
    discrepancies.append({
        "field": field,
        "expected": str(expected),
        "found": str(found),
        "confidence": round(confidence, 1),
        "severity": severity,
    })


# ─────────────────────────────────────────────────────────────────────────────
# CV Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_cv(
    extracted: dict,
    reference: dict,
    discrepancies: list,
    reasoning: list,
) -> str:
    """
    CV is the BASELINE document. It almost always passes — we're verifying
    the document was readable and contains employment history.
    Optional check: if offer_reference_data has an expected_employer, fuzzy-match it.
    """
    reasoning.append("[EVAL:CV] Evaluating CV as baseline claimed profile")

    employment_history = extracted.get("employment_history", [])
    full_name = extracted.get("full_name")

    if not employment_history:
        reasoning.append("[EVAL:CV] ⚠️  No employment history found in CV — needs review")
        _add_discrepancy(
            discrepancies, "cv.employment_history",
            "At least one employer entry", "None found", 0, "review"
        )
        return "NEEDS_REVIEW"

    if not full_name:
        reasoning.append("[EVAL:CV] ⚠️  Candidate name not found in CV")
        _add_discrepancy(
            discrepancies, "cv.full_name",
            "Candidate name", "Not found in CV", 0, "review"
        )
        # Don't fail — proceed but flag

    reasoning.append(
        f"[EVAL:CV] Extracted {len(employment_history)} employer(s): "
        + ", ".join(e.get("company_name", "?") for e in employment_history)
    )

    # Optional: check against offer letter expected employer
    expected_employer = reference.get("expected_employer")
    if expected_employer:
        cv_companies = [e.get("company_name", "") for e in employment_history]
        best = _best_match(expected_employer, cv_companies)
        if best >= EMPLOYER_MATCH_PASS:
            reasoning.append(
                f"[EVAL:CV] Offer employer '{expected_employer}' found in CV ({best:.0f}% match)"
            )
        else:
            reasoning.append(
                f"[EVAL:CV] Offer employer '{expected_employer}' not strongly found in CV "
                f"(best match: {best:.0f}%) — will flag but not fail CV"
            )
            _add_discrepancy(
                discrepancies, "cv.expected_employer",
                expected_employer, cv_companies, best, "review"
            )

    reasoning.append("[EVAL:CV] CV passed — claimed profile captured. Awaiting EPFO cross-verification.")
    return "PASSED"


# ─────────────────────────────────────────────────────────────────────────────
# EPFO Evaluation (cross-verified against cv_profile)
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_epfo(
    extracted: dict,
    reference: dict,
    discrepancies: list,
    reasoning: list,
) -> str:
    """
    Cross-verify EPFO records against the CV claimed profile.
    reference_data = cv_profile (populated from previous CV processing).
    """
    reasoning.append("[EVAL:EPFO] Cross-verifying EPFO against CV claimed profile")

    # ── Load CV employers from reference_data (cv_profile) ───────────────────
    cv_employment = reference.get("employment_history", [])
    cv_employers = [e.get("company_name", "") for e in cv_employment]

    epfo_employers_raw = extracted.get("employers", [])
    epfo_employer_names = [e.get("employer_name", "") for e in epfo_employers_raw]

    reasoning.append(f"[EVAL:EPFO] CV claimed employers:  {cv_employers}")
    reasoning.append(f"[EVAL:EPFO] EPFO employer records: {epfo_employer_names}")

    if not epfo_employers_raw:
        reasoning.append("[EVAL:EPFO] No EPFO employer records found — document may be invalid")
        _add_discrepancy(
            discrepancies, "epfo.employers",
            "At least one EPFO record", "None found", 0, "missing"
        )
        return "NEEDS_REVIEW"

    result_flags: List[str] = []   # collect "review" or "fallback" signals

    # ── 1. Name match ─────────────────────────────────────────────────────────
    cv_name = reference.get("full_name") or reference.get("applicant_name")
    epfo_name = extracted.get("member_name")
    if cv_name and epfo_name:
        name_score = _fuzzy(cv_name, epfo_name)
        if name_score >= NAME_MATCH_PASS:
            reasoning.append(f"[EVAL:EPFO] Name match: '{cv_name}' ↔ '{epfo_name}' ({name_score:.0f}%) ✓")
        elif name_score >= NAME_MATCH_REVIEW:
            reasoning.append(
                f"[EVAL:EPFO] Name partial match: '{cv_name}' ↔ '{epfo_name}' ({name_score:.0f}%) — review"
            )
            _add_discrepancy(
                discrepancies, "epfo.member_name", cv_name, epfo_name, name_score, "review"
            )
            result_flags.append("review")
        else:
            reasoning.append(
                f"[EVAL:EPFO] ❌ Name mismatch: CV='{cv_name}' vs EPFO='{epfo_name}' ({name_score:.0f}%)"
            )
            _add_discrepancy(
                discrepancies, "epfo.member_name", cv_name, epfo_name, name_score, "mismatch"
            )
            result_flags.append("review")

    # ── 2. CV employers → are they in EPFO? ──────────────────────────────────
    unverified_cv_employers = []
    for cv_emp in cv_employment:
        cv_company = cv_emp.get("company_name", "")
        if not cv_company:
            continue
        match_score = _best_match(cv_company, epfo_employer_names)
        if match_score >= EMPLOYER_MATCH_PASS:
            reasoning.append(
                f"[EVAL:EPFO] CV employer '{cv_company}' → found in EPFO ({match_score:.0f}%) ✓"
            )
            # ── Date check for matched employer ──────────────────────────────
            # Find the best-matching EPFO record
            best_epfo = max(
                epfo_employers_raw,
                key=lambda e: _fuzzy(cv_company, e.get("employer_name", "")),
            )
            cv_start  = cv_emp.get("start_date")
            cv_end    = cv_emp.get("end_date")
            epfo_join = best_epfo.get("date_of_joining")
            epfo_exit = best_epfo.get("date_of_exit")

            for cv_date, epfo_date, label in [
                (cv_start, epfo_join, "start/joining date"),
                (cv_end, epfo_exit, "end/exit date"),
            ]:
                if cv_date and epfo_date and _norm(cv_date) != "present":
                    diff = _date_diff_days(cv_date, epfo_date)
                    if diff is not None:
                        if diff <= DATE_GAP_REVIEW_DAYS:
                            reasoning.append(
                                f"[EVAL:EPFO] {cv_company} {label}: "
                                f"CV='{cv_date}' EPFO='{epfo_date}' — diff {diff}d ✓"
                            )
                        else:
                            reasoning.append(
                                f"[EVAL:EPFO] ⚠️  {cv_company} {label} mismatch: "
                                f"CV='{cv_date}' EPFO='{epfo_date}' — diff {diff}d"
                            )
                            _add_discrepancy(
                                discrepancies,
                                f"epfo.{cv_company}.{label}",
                                cv_date, epfo_date, 0, "review"
                            )
                            result_flags.append("review")
        else:
            reasoning.append(
                f"[EVAL:EPFO] ❌ CV employer '{cv_company}' NOT found in EPFO "
                f"(best match: {match_score:.0f}%) → bank statement required"
            )
            _add_discrepancy(
                discrepancies,
                f"epfo.missing_cv_employer",
                cv_company, f"Not found in EPFO (best: {match_score:.0f}%)",
                match_score, "missing"
            )
            unverified_cv_employers.append(cv_company)

    # ── 3. EPFO employers not in CV → hidden employment check ────────────────
    for epfo_emp in epfo_employers_raw:
        epfo_company = epfo_emp.get("employer_name", "")
        if not epfo_company:
            continue
        match_score = _best_match(epfo_company, cv_employers)
        if match_score < EMPLOYER_MATCH_REVIEW:
            reasoning.append(
                f"[EVAL:EPFO] ⚠️  EPFO employer '{epfo_company}' NOT in CV — possible hidden employment"
            )
            _add_discrepancy(
                discrepancies, "epfo.hidden_employer",
                "Present in CV", f"'{epfo_company}' in EPFO but missing from CV",
                match_score, "hidden_employment"
            )
            result_flags.append("review")

    # ── Determine result ──────────────────────────────────────────────────────
    if unverified_cv_employers:
        reasoning.append(
            f"[EVAL:EPFO] {len(unverified_cv_employers)} CV employer(s) unverified by EPFO. "
            "Requesting bank statement as supporting evidence."
        )
        return "NEEDS_FALLBACK"

    if result_flags:
        reasoning.append(f"[EVAL:EPFO] {len(result_flags)} issue(s) flagged — admin review required")
        return "NEEDS_REVIEW"

    reasoning.append("[EVAL:EPFO] All CV employers confirmed in EPFO with acceptable date accuracy ✓")
    return "PASSED"


# ─────────────────────────────────────────────────────────────────────────────
# Bank Statement Evaluation (cross-verified against cv_profile)
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_bank_statement(
    extracted: dict,
    reference: dict,
    discrepancies: list,
    reasoning: list,
) -> str:
    """
    Verify salary credits from bank statement against CV-claimed employer.
    reference_data = cv_profile (employers, dates).
    Called only when EPFO could not confirm a CV employer.
    """
    reasoning.append("[EVAL:BANK] Cross-verifying bank statement against CV claimed profile")

    cv_name = reference.get("full_name") or reference.get("applicant_name")
    account_holder = extracted.get("account_holder_name")
    salary_credits = extracted.get("salary_credits", [])
    cv_employment  = reference.get("employment_history", [])

    result_flags = []

    # ── 1. Account holder name vs CV name (HIGH RISK on mismatch) ────────────
    if cv_name and account_holder:
        name_score = _fuzzy(cv_name, account_holder)
        if name_score >= NAME_MATCH_PASS:
            reasoning.append(
                f"[EVAL:BANK] Account holder '{account_holder}' matches CV name '{cv_name}' "
                f"({name_score:.0f}%) ✓"
            )
        else:
            reasoning.append(
                f"[EVAL:BANK] ❌ HIGH RISK: Account holder '{account_holder}' vs "
                f"CV name '{cv_name}' — {name_score:.0f}% match"
            )
            _add_discrepancy(
                discrepancies, "bank.account_holder_name",
                cv_name, account_holder, name_score, "mismatch"
            )
            result_flags.append("mismatch")
    elif not account_holder:
        reasoning.append("[EVAL:BANK] ⚠️  Account holder name not found in statement")
        _add_discrepancy(discrepancies, "bank.account_holder_name", cv_name, "Not found", 0, "missing")
        result_flags.append("review")

    # ── 2. Salary credits from CV employers ───────────────────────────────────
    if not salary_credits:
        reasoning.append("[EVAL:BANK] No salary credits found in bank statement")
        _add_discrepancy(
            discrepancies, "bank.salary_credits",
            "Monthly salary credits", "None found", 0, "missing"
        )
        result_flags.append("review")
    else:
        reasoning.append(f"[EVAL:BANK] Found {len(salary_credits)} salary credit(s)")

        # For each CV employer, see if salary credits mention them
        confirmed_employers = []
        for cv_emp in cv_employment:
            cv_company = cv_emp.get("company_name", "")
            employer_credits = []
            for credit in salary_credits:
                narration = credit.get("narration", "") + " " + credit.get("employer_hint", "")
                match_score = _fuzzy(cv_company, narration)
                if match_score >= 55 or any(
                    word.lower() in narration.lower()
                    for word in cv_company.split()
                    if len(word) > 3
                ):
                    employer_credits.append(credit)

            if employer_credits:
                reasoning.append(
                    f"[EVAL:BANK] '{cv_company}': {len(employer_credits)} salary credit(s) found ✓"
                )
                confirmed_employers.append(cv_company)

                # ── Amount consistency check ──────────────────────────────────
                amounts = []
                for c in employer_credits:
                    try:
                        amt_str = re.sub(r"[^\d.]", "", c.get("amount", "0"))
                        amounts.append(float(amt_str))
                    except ValueError:
                        pass
                if amounts and max(amounts) > 0:
                    variation = (max(amounts) - min(amounts)) / max(amounts) * 100
                    if variation < 15:
                        reasoning.append(
                            f"[EVAL:BANK] '{cv_company}' salary consistent "
                            f"({min(amounts):.0f}–{max(amounts):.0f}) — variation {variation:.1f}% ✓"
                        )
                    else:
                        reasoning.append(
                            f"[EVAL:BANK] ⚠️  '{cv_company}' salary variation {variation:.1f}% "
                            "— inconsistent credits"
                        )
                        _add_discrepancy(
                            discrepancies,
                            f"bank.salary_consistency.{cv_company}",
                            "Consistent monthly salary",
                            f"Variation: {variation:.1f}%", 0, "review"
                        )
                        result_flags.append("review")
            else:
                reasoning.append(
                    f"[EVAL:BANK] ⚠️  No salary credits attributable to '{cv_company}'"
                )
                _add_discrepancy(
                    discrepancies,
                    f"bank.no_salary_credits.{cv_company}",
                    f"Salary credits from {cv_company}",
                    "Not found in narrations", 0, "review"
                )
                result_flags.append("review")

    # ── Determine result ──────────────────────────────────────────────────────
    has_mismatch = any(f == "mismatch" for f in result_flags)
    if has_mismatch:
        reasoning.append("[EVAL:BANK] Hard mismatch detected (account holder name) — needs review")
        return "NEEDS_REVIEW"
    if result_flags:
        reasoning.append(f"[EVAL:BANK] {len(result_flags)} issue(s) flagged — admin review required")
        return "NEEDS_REVIEW"

    reasoning.append("[EVAL:BANK] Bank statement confirms salary credits from CV employers ✓")
    return "PASSED"


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluation node
# ─────────────────────────────────────────────────────────────────────────────

def evaluation_node(state: VerificationState) -> dict:
    """
    LangGraph node: pure Python cross-document rule engine.
    Sets evaluation_result, discrepancies, reasoning.
    """
    doc_type   = state.get("document_type", "cv_resume")
    extracted  = state.get("extracted_data", {})
    reference  = state.get("reference_data", {})
    reasoning  = list(state.get("reasoning", []))
    discrepancies: List[Dict] = []

    # If extraction node already set evaluation_result (e.g. quota error), skip evaluation
    if state.get("evaluation_result") in ("NEEDS_REVIEW", "NEEDS_FALLBACK"):
        reasoning.append("[EVAL] Skipping evaluation — extraction node already set result")
        return {"discrepancies": discrepancies, "reasoning": reasoning}

    reasoning.append(f"[EVAL] Starting cross-document evaluation for: {doc_type}")
    reasoning.append(
        f"[EVAL] Reference data keys: {list(reference.keys())}"
    )

    if doc_type == "cv_resume":
        result = _evaluate_cv(extracted, reference, discrepancies, reasoning)
    elif doc_type == "epfo_history":
        result = _evaluate_epfo(extracted, reference, discrepancies, reasoning)
    elif doc_type == "bank_statement":
        result = _evaluate_bank_statement(extracted, reference, discrepancies, reasoning)
    else:
        reasoning.append(f"[EVAL] Unknown doc type '{doc_type}' → NEEDS_REVIEW")
        result = "NEEDS_REVIEW"

    reasoning.append(
        f"[EVAL] Final result: {result} | Discrepancies: {len(discrepancies)}"
    )
    return {
        "evaluation_result": result,
        "discrepancies": discrepancies,
        "reasoning": reasoning,
    }
