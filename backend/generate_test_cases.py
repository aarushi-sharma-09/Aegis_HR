"""
generate_test_cases.py
Generates 4 complete sets of test documents to cover all BGV scenarios:

Case 1: Perfect Match (VERIFIED)
Case 2: Hidden Employment (NEEDS_REVIEW) 
Case 3: Missing Employer → Fallback Bank Statement (NEEDS_FALLBACK → VERIFIED)
Case 4: Name Mismatch (NEEDS_REVIEW)

Usage:
    cd backend
    source venv/bin/activate
    python generate_test_cases.py
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUTPUT_DIR = Path("./sample_docs/scenarios")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def make_doc(filename: str, lines: list[str], width=900, bg="#ffffff"):
    line_height = 28
    padding = 60
    height = padding * 2 + len(lines) * line_height + 20
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    try:
        font_regular = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_bold    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_mono    = ImageFont.truetype("/System/Library/Fonts/Courier New.ttf", 17)
    except Exception:
        font_regular = ImageFont.load_default()
        font_bold    = font_regular
        font_mono    = font_regular

    y = padding
    for line in lines:
        if line.startswith("##"):
            draw.text((padding, y), line[2:].strip(), fill="#1a1a2e", font=font_bold)
        elif line.startswith("  "):
            draw.text((padding + 20, y), line.strip(), fill="#444444", font=font_mono)
        elif line == "---":
            draw.line([(padding, y + 10), (width - padding, y + 10)], fill="#cccccc", width=1)
        else:
            draw.text((padding, y), line, fill="#222222", font=font_regular)
        y += line_height

    path = OUTPUT_DIR / filename
    img.save(str(path))
    return path

# ─────────────────────────────────────────────────────────────────────────────
# CASE 1: PERFECT MATCH (Expected: VERIFIED)
# ─────────────────────────────────────────────────────────────────────────────
make_doc("case1_cv_perfect.png", [
    "## CURRICULUM VITAE", "---",
    "## Name:    Priya Sharma",
    "## Email:   priya.sharma@test.com",
    "", "## WORK EXPERIENCE",
    "  Software Engineer — Infosys Limited",
    "  June 2020 – Present",
])

make_doc("case1_epfo_perfect.png", [
    "## EPFO SERVICE HISTORY", "---",
    "## Member Name:   Priya Sharma",
    "", "## EMPLOYER DETAILS", "---",
    "  Establishment Name:   Infosys Limited",
    "  Date of Joining:      01/06/2020",
    "  Date of Exit:         Not Available (Current)",
])


# ─────────────────────────────────────────────────────────────────────────────
# CASE 2: HIDDEN EMPLOYMENT (Expected: NEEDS_REVIEW)
# ─────────────────────────────────────────────────────────────────────────────
make_doc("case2_cv_hidden.png", [
    "## CURRICULUM VITAE", "---",
    "## Name:    Rahul Mehta",
    "## Email:   rahul@test.com",
    "", "## WORK EXPERIENCE",
    "  Senior Analyst — Tata Consultancy Services",
    "  Jan 2022 – Present",
])

make_doc("case2_epfo_hidden.png", [
    "## EPFO SERVICE HISTORY", "---",
    "## Member Name:   Rahul Mehta",
    "", "## EMPLOYER DETAILS", "---",
    "  Establishment Name:   Tata Consultancy Services",
    "  Date of Joining:      15/01/2022",
    "  Date of Exit:         Current",
    "",
    "  Establishment Name:   Moonlight Tech Private Limited", # <-- Hidden employer!
    "  Date of Joining:      01/03/2023",
    "  Date of Exit:         Current",
])


# ─────────────────────────────────────────────────────────────────────────────
# CASE 3: MISSING EMPLOYER → FALLBACK REQUIRED
# ─────────────────────────────────────────────────────────────────────────────
make_doc("case3_cv_fallback.png", [
    "## CURRICULUM VITAE", "---",
    "## Name:    Anjali Verma",
    "## Email:   anjali@test.com",
    "", "## WORK EXPERIENCE",
    "  Consultant — Wipro Technologies",
    "  Jan 2024 – Present",
])

make_doc("case3_epfo_fallback.png", [
    "## EPFO SERVICE HISTORY", "---",
    "## Member Name:   Anjali Verma",
    "", "## EMPLOYER DETAILS", "---",
    "  Establishment Name:   Reliance Retail", # Wipro is completely missing here
    "  Date of Joining:      01/01/2022",
    "  Date of Exit:         31/12/2023",
])

make_doc("case3_bank_statement.png", [
    "## BANK STATEMENT", "---",
    "## Account Holder:   Anjali Verma",
    "", "## TRANSACTIONS", "---",
    "  05-Feb-2024   SALARY WIPRO TECHNOLOGIES     75,000.00",
    "  05-Mar-2024   SALARY WIPRO TECHNOLOGIES     75,000.00",
    "  05-Apr-2024   SALARY WIPRO TECHNOLOGIES     75,000.00",
])


# ─────────────────────────────────────────────────────────────────────────────
# CASE 4: NAME MISMATCH (Expected: NEEDS_REVIEW - HIGH RISK)
# ─────────────────────────────────────────────────────────────────────────────
make_doc("case4_cv_mismatch.png", [
    "## CURRICULUM VITAE", "---",
    "## Name:    Amit Patel",
    "## Email:   amit@test.com",
    "", "## WORK EXPERIENCE",
    "  Manager — HDFC Bank",
    "  April 2021 – Present",
])

make_doc("case4_epfo_mismatch.png", [
    "## EPFO SERVICE HISTORY", "---",
    "## Member Name:   Suresh Kumar Patel", # <-- Name is drastically different
    "", "## EMPLOYER DETAILS", "---",
    "  Establishment Name:   HDFC Bank Limited",
    "  Date of Joining:      10/04/2021",
    "  Date of Exit:         Current",
])

print("\n🎉 Generated 4 complete test scenarios in ./sample_docs/scenarios/")
for case in [1, 2, 3, 4]:
    print(f"  ✓ Case {case} files created")
