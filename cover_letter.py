import os
import sys
import logging
from llm_utils import initialize_llm_provider, extract_json_from_response
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from pdf import PDFHandler
from transform import convert_json_resume_to_text
from portfolio import fetch_portfolio, convert_portfolio_to_text
from github import fetch_and_display_github_info

logger = logging.getLogger(__name__)


def generate_cover_letter(
    resume_text: str,
    jd_text: str,
    candidate_name: str = None,
    company_name: str = None,
    tone: str = "professional",
    length: str = "medium",
) -> str:
    provider = initialize_llm_provider(DEFAULT_MODEL)
    model_params = MODEL_PARAMETERS.get(
        DEFAULT_MODEL, {"temperature": 0.5, "top_p": 0.9}
    )

    length_guide = {
        "short": "3-4 sentences, very concise",
        "medium": "3-4 paragraphs, standard cover letter length",
        "long": "5-6 paragraphs, detailed and comprehensive",
    }.get(length, "3-4 paragraphs")

    system = f"""You are an expert career coach and professional writer. Generate a {tone} cover letter that is {length_guide}.
The letter should:
- Be tailored specifically to the job description
- Highlight the MOST relevant skills and experiences from the resume
- Use specific examples from the candidate's projects and work
- Show enthusiasm without being generic
- Be ready to send (no placeholders, no brackets)
- {f'Mention the company name naturally' if company_name else 'Address the hiring team'}
- End with a professional closing
Return ONLY the letter text, no JSON, no analysis."""

    prompt = f"""Generate a tailored cover letter for the following candidate and job.

CANDIDATE RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

{f'COMPANY: {company_name}' if company_name else ''}

The cover letter should highlight the specific skills and experiences that make this candidate a strong fit for this role.
Use concrete examples from the resume (project names, technologies, achievements).
Do NOT use generic phrases like "I am writing to apply" — start strong with enthusiasm and specificity."""

    chat_params = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "stream": False,
            "temperature": 0.7,
            "top_p": 0.9,
        },
    }

    response = provider.chat(**chat_params)
    letter = response["message"]["content"]
    letter = letter.strip().strip('"').strip("'")

    return letter


def main(resume_pdf: str, jd_file: str, output: str = None, tone: str = "professional", length: str = "medium"):
    print(f"📄 Reading resume: {resume_pdf}")
    handler = PDFHandler()
    resume_data = handler.extract_json_from_pdf(resume_pdf)
    if not resume_data:
        print("❌ Failed to extract resume data")
        return

    resume_text = convert_json_resume_to_text(resume_data)
    candidate_name = resume_data.basics.name if resume_data.basics else "Candidate"

    print(f"📋 Reading job description: {jd_file}")
    if not os.path.exists(jd_file):
        print(f"❌ Job description file not found: {jd_file}")
        return
    with open(jd_file, "r", encoding="utf-8") as f:
        jd_text = f.read()

    company_name = None
    import re
    for line in jd_text.split("\n"):
        line = line.strip()
        m = re.match(r"^(?:Company|Organization|At)\s*:?\s*(.+)$", line, re.IGNORECASE)
        if m:
            company_name = m.group(1).strip()
            break

    print(f"✍️  Generating {tone} cover letter ({length})...")
    letter = generate_cover_letter(
        resume_text=resume_text,
        jd_text=jd_text,
        candidate_name=candidate_name,
        company_name=company_name,
        tone=tone,
        length=length,
    )

    print("\n" + "=" * 70)
    print(f"📝 COVER LETTER — {candidate_name}")
    if company_name:
        print(f"   For: {company_name}")
    print("=" * 70)
    print()
    print(letter)
    print()
    print("=" * 70)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(letter)
        print(f"💾 Saved to {output}")

    return letter


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a tailored cover letter")
    parser.add_argument("resume", help="Path to resume PDF")
    parser.add_argument("jd", help="Path to job description text file")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--tone", choices=["professional", "enthusiastic", "confident", "warm"], default="professional")
    parser.add_argument("--length", choices=["short", "medium", "long"], default="medium")
    args = parser.parse_args()

    main(args.resume, args.jd, output=args.output, tone=args.tone, length=args.length)
