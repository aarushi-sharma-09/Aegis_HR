"""
generate_sample_docs.py
Run this once to generate sample PNG test documents for all 3 document types.
These can be directly uploaded to the BGV system for end-to-end testing.

Usage:
    cd backend
    source venv/bin/activate
    python generate_sample_docs.py
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUTPUT_DIR = Path("./sample_docs")
OUTPUT_DIR.mkdir(exist_ok=True)


def make_doc(filename: str, lines: list[str], width=900, bg="#ffffff"):
    """Create a white-background PNG that looks like a document."""
    line_height = 28
    padding = 60
    height = padding * 2 + len(lines) * line_height + 20
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Try system fonts; fall back to default
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
    print(f"✅  Created: {path}")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# 1. CV / RESUME
# ─────────────────────────────────────────────────────────────────────────────
make_doc("sample_cv_resume.png", [
    "## CURRICULUM VITAE",
    "---",
    "## Name:    Priya Sharma",
    "## Email:   priya.sharma@gmail.com",
    "## Phone:   +91 9876543210",
    "",
    "## EDUCATION",
    "  B.Tech Computer Science — Delhi Technological University (2019)",
    "  CGPA: 8.4 / 10",
    "",
    "## WORK EXPERIENCE",
    "  Software Engineer — Infosys Limited",
    "  June 2019 – Present",
    "  - Developed microservices using Spring Boot and Python FastAPI",
    "  - Led a team of 4 engineers on the digital KYC project",
    "  - Reduced API latency by 40% through Redis caching",
    "",
    "  Intern — Wipro Technologies",
    "  Jan 2019 – May 2019",
    "  - Built data pipelines using Apache Spark",
    "",
    "## SKILLS",
    "  Python, Java, FastAPI, PostgreSQL, Docker, LangGraph, React",
    "",
    "## CERTIFICATIONS",
    "  AWS Certified Solutions Architect (2021)",
    "  Google Professional Cloud Developer (2022)",
])

# ─────────────────────────────────────────────────────────────────────────────
# 2. EPFO PASSBOOK
# ─────────────────────────────────────────────────────────────────────────────
make_doc("sample_epfo_history.png", [
    "## EMPLOYEES PROVIDENT FUND ORGANISATION",
    "## MEMBER PASSBOOK",
    "---",
    "## Member Name:   Rahul Mehta",
    "## UAN:           100987654321",
    "## PAN:           ABCPM1234D",
    "## Date of Birth: 15/04/1995",
    "",
    "## EMPLOYER DETAILS",
    "---",
    "  Establishment Name:   Tata Consultancy Services Limited",
    "  Establishment ID:     MHBAN0012345000",
    "  Date of Joining:      01/07/2018",
    "  Date of Exit:         (Currently Employed)",
    "  Member ID:            MHBAN0012345000-0001",
    "",
    "## CONTRIBUTION HISTORY (Last 6 months)",
    "---",
    "  Month        Employee    Employer    Pension",
    "  Mar 2026     1800        1800        1250",
    "  Feb 2026     1800        1800        1250",
    "  Jan 2026     1800        1800        1250",
    "  Dec 2025     1800        1800        1250",
    "  Nov 2025     1800        1800        1250",
    "  Oct 2025     1800        1800        1250",
    "",
    "## Total Balance: INR 2,34,560",
])

# ─────────────────────────────────────────────────────────────────────────────
# 3. BANK STATEMENT
# ─────────────────────────────────────────────────────────────────────────────
make_doc("sample_bank_statement.png", [
    "## STATE BANK OF INDIA",
    "## ACCOUNT STATEMENT",
    "---",
    "## Account Holder:   Anjali Verma",
    "## Account Number:   32145678901234",
    "## IFSC Code:        SBIN0001234",
    "## Branch:           Connaught Place, New Delhi",
    "## Statement Period: 01-Apr-2026 to 30-Jun-2026",
    "",
    "## TRANSACTION HISTORY",
    "---",
    "  Date         Description                  Debit      Credit     Balance",
    "  01-Apr-2026  Opening Balance                                     45,230.00",
    "  05-Apr-2026  SALARY WIPRO TECHNOLOGIES               78,500.00   1,23,730.00",
    "  10-Apr-2026  UPI/Amazon Pay               2,340.00               1,21,390.00",
    "  15-Apr-2026  EMI/HDFC Home Loan          18,500.00               1,02,890.00",
    "  20-Apr-2026  ATM Withdrawal               5,000.00                97,890.00",
    "  05-May-2026  SALARY WIPRO TECHNOLOGIES               78,500.00   1,76,390.00",
    "  10-May-2026  UPI/Swiggy                   1,250.00               1,75,140.00",
    "  05-Jun-2026  SALARY WIPRO TECHNOLOGIES               78,500.00   2,53,640.00",
    "",
    "## Closing Balance: INR 2,53,640.00",
    "## Average Monthly Balance: INR 1,45,230.00",
])

print("\n🎉  All 3 sample documents created in ./sample_docs/")
print("   Upload them at http://localhost:5173/new-verification")
print("\n   Match these to applicants:")
print("   sample_cv_resume.png      → Applicant: Priya Sharma (expected_employer: Infosys Limited)")
print("   sample_epfo_history.png   → Applicant: Rahul Mehta  (expected_employer: Tata Consultancy Services)")
print("   sample_bank_statement.png → Applicant: Anjali Verma (expected_employer: Wipro Technologies)")
