import os
import sys
import json
import logging
from llm_utils import initialize_llm_provider, extract_json_from_response
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from pdf import PDFHandler
from transform import convert_json_resume_to_text, convert_github_data_to_text
from portfolio import convert_portfolio_to_text
from portfolio import fetch_portfolio
from github import fetch_and_display_github_info

logger = logging.getLogger(__name__)


def parse_job_description(text: str) -> dict:
    provider = initialize_llm_provider(DEFAULT_MODEL)
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL, {"temperature": 0.5, "top_p": 0.9})

    system = "You are an expert job description parser. Extract structured fields from the job description text. Return ONLY valid JSON."

    prompt = f"""Parse the following job description into structured JSON with these exact fields:
- required_skills: list of required technical/professional skills
- nice_to_have_skills: list of preferred but not required skills
- experience_years: integer for minimum years of experience required (0 if unspecified)
- education: list of education requirements (e.g. ["Bachelor's in Computer Science", "Master's in Data Science"])
- responsibilities: list of key job responsibilities
- key_qualities: list of soft skills and personal qualities mentioned

Job Description:
{text}

Return ONLY valid JSON. No markdown, no explanation."""

    response = provider.chat(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        options={
            "temperature": model_params.get("temperature", 0.5),
            "top_p": model_params.get("top_p", 0.9),
        }
    )

    raw = extract_json_from_response(response["message"]["content"])
    json_start = raw.find("{")
    json_end = raw.rfind("}")
    if json_start != -1 and json_end != -1:
        raw = raw[json_start:json_end + 1]

    return json.loads(raw)


def score_match(resume_text: str, jd_data: dict, github_data: dict = None, portfolio_data: dict = None) -> dict:
    provider = initialize_llm_provider(DEFAULT_MODEL)
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL, {"temperature": 0.5, "top_p": 0.9})

    system = "You are a precise resume-job matching evaluator. Analyze how well the candidate matches the job description and return a detailed JSON score."

    jd_json = json.dumps(jd_data, indent=2)

    additional_context = ""
    if github_data:
        github_text = convert_github_data_to_text(github_data)
        additional_context += github_text
    if portfolio_data:
        portfolio_text = convert_portfolio_to_text(portfolio_data)
        additional_context += portfolio_text

    prompt = f"""Evaluate the match between this candidate's resume and the job description.

Job Description (parsed):
{jd_json}

Resume:
{resume_text}
{additional_context}

Return a JSON object with the following structure:
{{
    "skill_match": {{
        "score": <integer 0-40>,
        "matched": ["skill1", "skill2", ...],
        "missing": ["skill1", "skill2", ...]
    }},
    "experience_match": {{
        "score": <integer 0-25>,
        "evidence": "explanation of experience match"
    }},
    "education_match": {{
        "score": <integer 0-15>,
        "evidence": "explanation of education match"
    }},
    "project_relevance": {{
        "score": <integer 0-20>,
        "evidence": "explanation of project relevance"
    }},
    "overall_assessment": "brief overall assessment",
    "gap_analysis": ["gap1", "gap2", ...]
}}

Scoring guidelines:
- Skill Match (0-40): What fraction of required skills are present in the resume. Deduct for missing required skills.
- Experience Match (0-25): How well years of experience and role relevance align with requirements.
- Education Match (0-15): How well education background matches the education requirements.
- Project Relevance (0-20): How relevant the candidate's projects are to the job responsibilities.

Return ONLY valid JSON. No markdown, no explanation."""

    response = provider.chat(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        options={
            "temperature": model_params.get("temperature", 0.5),
            "top_p": model_params.get("top_p", 0.9),
        }
    )

    raw = extract_json_from_response(response["message"]["content"])
    json_start = raw.find("{")
    json_end = raw.rfind("}")
    if json_start != -1 and json_end != -1:
        raw = raw[json_start:json_end + 1]

    result = json.loads(raw)

    total = 0
    total += min(result.get("skill_match", {}).get("score", 0), 40)
    total += min(result.get("experience_match", {}).get("score", 0), 25)
    total += min(result.get("education_match", {}).get("score", 0), 15)
    total += min(result.get("project_relevance", {}).get("score", 0), 20)

    result["jd_match_score"] = total
    result["skill_match"]["max"] = 40
    result["experience_match"]["max"] = 25
    result["education_match"]["max"] = 15
    result["project_relevance"]["max"] = 20

    return result


def generate_gap_analysis(jd_match_result: dict) -> list[dict]:
    gaps = []
    skill = jd_match_result.get("skill_match", {})
    missing_skills = skill.get("missing", [])
    if missing_skills:
        gaps.append({
            "category": "skill",
            "issue": f"Missing required skills: {', '.join(missing_skills)}",
            "severity": "high",
            "recommendation": f"Acquire or demonstrate proficiency in: {', '.join(missing_skills)}"
        })

    exp = jd_match_result.get("experience_match", {})
    exp_score = exp.get("score", 25)
    if exp_score < 15:
        gaps.append({
            "category": "experience",
            "issue": "Insufficient relevant experience",
            "severity": "high",
            "recommendation": "Gain more years or depth in relevant roles, or highlight transferable experience"
        })
    elif exp_score < 20:
        gaps.append({
            "category": "experience",
            "issue": "Moderate experience gap",
            "severity": "medium",
            "recommendation": "Consider additional training or projects to bridge experience gap"
        })

    edu = jd_match_result.get("education_match", {})
    edu_score = edu.get("score", 15)
    if edu_score < 8:
        gaps.append({
            "category": "education",
            "issue": "Education requirements not fully met",
            "severity": "medium",
            "recommendation": "Consider relevant certifications or coursework to supplement education"
        })

    proj = jd_match_result.get("project_relevance", {})
    proj_score = proj.get("score", 20)
    if proj_score < 10:
        gaps.append({
            "category": "project",
            "issue": "Projects lack relevance to job responsibilities",
            "severity": "medium",
            "recommendation": "Work on projects that align with the target role's core technologies and domain"
        })
    elif proj_score < 5:
        gaps.append({
            "category": "project",
            "issue": "No relevant projects demonstrated",
            "severity": "high",
            "recommendation": "Build and showcase portfolio projects matching the job domain"
        })

    severity_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda g: severity_order.get(g["severity"], 99))
    return gaps


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python jd_match.py <resume.pdf> <job_description.txt>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    jd_path = sys.argv[2]

    if not os.path.exists(pdf_path):
        print(f"Error: Resume file '{pdf_path}' does not exist.")
        sys.exit(1)
    if not os.path.exists(jd_path):
        print(f"Error: Job description file '{jd_path}' does not exist.")
        sys.exit(1)

    with open(jd_path, "r", encoding="utf-8") as f:
        jd_text = f.read()

    print("Parsing job description...")
    jd_data = parse_job_description(jd_text)
    print(json.dumps(jd_data, indent=2))

    print("\nExtracting resume from PDF...")
    pdf_handler = PDFHandler()
    resume_data = pdf_handler.extract_json_from_pdf(pdf_path)
    if not resume_data:
        print("Error: Failed to extract resume data from PDF.")
        sys.exit(1)

    resume_text = convert_json_resume_to_text(resume_data)

    github_data = None
    if resume_data.basics and resume_data.basics.profiles:
        for profile in resume_data.basics.profiles:
            if profile.network and profile.network.lower() == "github":
                print(f"Fetching GitHub data for {profile.username}...")
                github_data = fetch_and_display_github_info(profile.url)
                break

    portfolio_data = None
    if resume_data.basics and resume_data.basics.url:
        print(f"Fetching portfolio from {resume_data.basics.url}...")
        portfolio_data = fetch_portfolio(resume_data.basics.url)

    print("\nScoring match...")
    match_result = score_match(resume_text, jd_data, github_data, portfolio_data)

    print("\n" + "=" * 60)
    print("JD MATCH RESULTS")
    print("=" * 60)
    print(f"\nOverall JD Match Score: {match_result['jd_match_score']}/100")

    print(f"\nSkill Match: {match_result['skill_match']['score']}/{match_result['skill_match']['max']}")
    if match_result['skill_match'].get('matched'):
        print(f"  Matched: {', '.join(match_result['skill_match']['matched'])}")
    if match_result['skill_match'].get('missing'):
        print(f"  Missing: {', '.join(match_result['skill_match']['missing'])}")

    print(f"\nExperience Match: {match_result['experience_match']['score']}/{match_result['experience_match']['max']}")
    print(f"  Evidence: {match_result['experience_match'].get('evidence', '')}")

    print(f"\nEducation Match: {match_result['education_match']['score']}/{match_result['education_match']['max']}")
    print(f"  Evidence: {match_result['education_match'].get('evidence', '')}")

    print(f"\nProject Relevance: {match_result['project_relevance']['score']}/{match_result['project_relevance']['max']}")
    print(f"  Evidence: {match_result['project_relevance'].get('evidence', '')}")

    print(f"\nOverall Assessment: {match_result.get('overall_assessment', '')}")

    if match_result.get('gap_analysis'):
        print(f"\nGap Analysis:")
        for gap in generate_gap_analysis(match_result):
            print(f"  [{gap['severity'].upper()}] {gap['category']}: {gap['issue']}")
            print(f"    -> {gap['recommendation']}")

    print("\n" + "=" * 60)
