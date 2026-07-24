import os
import re
import logging
from collections import Counter
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

TECH_KEYWORDS = [
    "python", "javascript", "typescript", "java", "go", "golang", "rust", "c++", "c#", "ruby",
    "swift", "kotlin", "scala", "php", "perl", "r", "matlab", "sql", "bash", "shell",
    "react", "angular", "vue", "next.js", "node.js", "express", "django", "flask", "spring",
    "fastapi", "graphql", "rest", "api", "docker", "kubernetes", "k8s", "aws", "azure", "gcp",
    "terraform", "ansible", "jenkins", "ci/cd", "git", "linux", "nginx", "redis", "mongodb",
    "postgresql", "mysql", "elasticsearch", "kafka", "rabbitmq", "grpc", "websocket",
    "machine learning", "deep learning", "ai", "llm", "nlp", "computer vision", "tensorflow",
    "pytorch", "scikit-learn", "langchain", "rag", "vector database", "openai", "hugging face",
    "llama", "gpt", "bert", "transformer", "agent", "autogen", "crewai",
    "typescript", "tailwind", "sass", "redux", "webpack", "vite", "jest", "cypress",
    "pandas", "numpy", "jupyter", "spark", "hadoop", "airflow", "dbt",
    "microservices", "serverless", "lambda", "containers", "orchestration",
    "oauth", "jwt", "saml", "ldap", "ssl", "tls", "https",
    "agile", "scrum", "kanban", "jira", "confluence",
    "tableau", "power bi", "looker", "datadog", "grafana", "prometheus",
]

SOFT_SKILLS = [
    "leadership", "communication", "teamwork", "problem.solving", "critical thinking",
    "mentorship", "collaboration", "presentation", "writing", "analytical",
    "strategic", "decision.making", "time management", "project management",
]

EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience",
    r"experience\s*(?:of\s+)?(\d+)\+?\s*(?:years?|yrs?)",
    r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:professional\s+)?(?:work\s+)?experience",
]


def extract_keywords(text: str) -> Counter:
    text_lower = text.lower()
    found = Counter()
    for kw in TECH_KEYWORDS:
        count = len(re.findall(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", text_lower))
        if count > 0:
            found[kw] = count
    return found


def extract_soft_skills(text: str) -> Counter:
    text_lower = text.lower()
    found = Counter()
    for sk in SOFT_SKILLS:
        pattern = sk.replace(".", r"[.\s]")
        count = len(re.findall(rf"(?<![a-z]){pattern}(?![a-z])", text_lower))
        if count > 0:
            found[sk.replace(".", " ")] = count
    return found


def extract_experience_years(text: str) -> List[int]:
    years = []
    text_lower = text.lower()
    for pattern in EXPERIENCE_PATTERNS:
        for m in re.finditer(pattern, text_lower):
            years.append(int(m.group(1)))
    return years


def compute_match(
    resume_text: str, jd_text: str
) -> Dict:
    resume_kws = extract_keywords(resume_text)
    jd_kws = extract_keywords(jd_text)

    resume_soft = extract_soft_skills(resume_text)
    jd_soft = extract_soft_skills(jd_text)

    all_jd_kws = set(jd_kws.keys())
    all_resume_kws = set(resume_kws.keys())
    matched = all_resume_kws & all_jd_kws
    missing = all_jd_kws - all_resume_kws
    extra = all_resume_kws - all_jd_kws

    if len(all_jd_kws) > 0:
        coverage = len(matched) / len(all_jd_kws) * 100
    else:
        coverage = 0

    jd_years = extract_experience_years(jd_text)
    resume_years = extract_experience_years(resume_text)
    max_jd_years = max(jd_years) if jd_years else None
    max_resume_years = max(resume_years) if resume_years else None

    return {
        "keyword_coverage_pct": round(coverage, 1),
        "matched_keywords": sorted(matched),
        "missing_keywords": sorted(missing),
        "extra_keywords_not_in_jd": sorted(extra),
        "jd_keyword_count": len(all_jd_kws),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "resume_keywords_top": resume_kws.most_common(15),
        "jd_keywords_top": jd_kws.most_common(15),
        "matched_soft_skills": sorted(set(resume_soft.keys()) & set(jd_soft.keys())),
        "missing_soft_skills": sorted(set(jd_soft.keys()) - set(resume_soft.keys())),
        "jd_experience_years": max_jd_years,
        "resume_experience_years": max_resume_years,
    }


def format_ats_report(analysis: Dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append(f"📊 ATS KEYWORD ANALYSIS")
    lines.append("=" * 70)
    lines.append(f"Keyword Coverage: {analysis['keyword_coverage_pct']}%")
    lines.append(f"  Matched: {analysis['matched_count']}/{analysis['jd_keyword_count']} JD keywords found in resume")
    lines.append(f"  Missing: {analysis['missing_count']} keywords from JD not in resume")
    lines.append("")

    if analysis["matched_keywords"]:
        lines.append(f"✅ MATCHED ({len(analysis['matched_keywords'])}):")
        lines.append(f"   {', '.join(analysis['matched_keywords'][:20])}")
        lines.append("")

    if analysis["missing_keywords"]:
        lines.append(f"❌ MISSING ({len(analysis['missing_keywords'])}):")
        lines.append(f"   {', '.join(analysis['missing_keywords'][:20])}")
        lines.append("")

    if analysis["matched_soft_skills"]:
        lines.append(f"👤 SOFT SKILLS MATCHED: {', '.join(analysis['matched_soft_skills'])}")
        lines.append("")

    if analysis["missing_soft_skills"]:
        lines.append(f"⚠️  SOFT SKILLS MISSING: {', '.join(analysis['missing_soft_skills'])}")
        lines.append("")

    if analysis["jd_experience_years"]:
        lines.append(f"⏱️  Experience: JD asks {analysis['jd_experience_years']}+ years, resume indicates {analysis['resume_experience_years'] or 'unknown'} years")
        lines.append("")

    lines.append(f"📈 Top JD Keywords: {', '.join(f'{kw}({n})' for kw, n in analysis['jd_keywords_top'][:10])}")
    lines.append(f"📈 Top Resume Keywords: {', '.join(f'{kw}({n})' for kw, n in analysis['resume_keywords_top'][:10])}")
    lines.append("=" * 70)

    return "\n".join(lines)


def keyword_suggestions(analysis: Dict) -> List[str]:
    suggestions = []
    if analysis["missing_keywords"]:
        suggestions.append(f"Add these missing keywords to your resume: {', '.join(analysis['missing_keywords'][:10])}")
    if analysis["keyword_coverage_pct"] < 50:
        suggestions.append("Your keyword coverage is below 50% — consider adding more relevant skills and technologies")
    if analysis["jd_experience_years"] and analysis["resume_experience_years"]:
        if analysis["jd_experience_years"] > analysis["resume_experience_years"]:
            suggestions.append(f"The JD requires {analysis['jd_experience_years']}+ years of experience")
    if analysis["missing_soft_skills"]:
        suggestions.append(f"Consider highlighting these soft skills: {', '.join(analysis['missing_soft_skills'][:5])}")
    return suggestions


def main(resume_file: str, jd_file: str):
    from pdf import PDFHandler
    from transform import convert_json_resume_to_text

    print(f"📄 Reading resume: {resume_file}")
    handler = PDFHandler()
    resume_data = handler.extract_json_from_pdf(resume_file)
    if not resume_data:
        print("❌ Failed to extract resume")
        return
    resume_text = convert_json_resume_to_text(resume_data)

    print(f"📋 Reading JD: {jd_file}")
    if not os.path.exists(jd_file):
        print(f"❌ File not found: {jd_file}")
        return
    with open(jd_file, "r", encoding="utf-8") as f:
        jd_text = f.read()

    print(f"🔍 Analyzing keyword match...")
    analysis = compute_match(resume_text, jd_text)
    report = format_ats_report(analysis)
    print(report)

    suggestions = keyword_suggestions(analysis)
    if suggestions:
        print("\n💡 KEYWORD SUGGESTIONS:")
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s}")
        print()

    return analysis


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ats_analysis.py <resume.pdf> <job_description.txt>")
        exit(1)
    import sys
    main(sys.argv[1], sys.argv[2])
