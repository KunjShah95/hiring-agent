import os
import sys
import json
import logging
import csv
import io
from pdf import PDFHandler
from github import fetch_and_display_github_info
from models import JSONResume, EvaluationData
from typing import List, Optional, Dict
from evaluator import ResumeEvaluator
from pathlib import Path
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from transform import (
    transform_evaluation_response,
    convert_json_resume_to_text,
    convert_github_data_to_text,
    convert_blog_data_to_text,
)
from portfolio import fetch_portfolio, convert_portfolio_to_text
from live_check import verify_urls, extract_urls_from_github, extract_urls_from_portfolio, get_bonus_points as demo_bonus, format_demo_evidence
from improvement import generate_improvements, get_top_recommendations
from report import generate_html_report
from history import record_score, show_history
from config import DEVELOPMENT_MODE

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
)


def print_evaluation_results(
    evaluation: EvaluationData, candidate_name: str = "Candidate"
):
    """Print evaluation results in a readable format."""
    print("\n" + "=" * 80)
    print(f"📊 RESUME EVALUATION RESULTS FOR: {candidate_name}")
    print("=" * 80)

    if not evaluation:
        print("❌ No evaluation data available")
        return

    # Calculate overall score
    total_score = 0
    max_score = 0

    if hasattr(evaluation, "scores") and evaluation.scores:
        for category_name, category_data in evaluation.scores.model_dump().items():
            category_score = min(category_data["score"], category_data["max"])
            total_score += category_score
            max_score += category_data["max"]

            # Log warning if score was capped
            if category_score < category_data["score"]:
                print(
                    f"⚠️  Warning: {category_name} score capped from {category_data['score']} to {category_score} (max: {category_data['max']})"
                )

    # Add bonus points
    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        total_score += evaluation.bonus_points.total

    # Subtract deductions
    if hasattr(evaluation, "deductions") and evaluation.deductions:
        total_score -= evaluation.deductions.total

    # Ensure total score doesn't exceed maximum possible score
    max_possible_score = max_score + 20  # 120 (100 categories + 20 bonus)
    if total_score > max_possible_score:
        total_score = max_possible_score
        print(f"⚠️  Warning: Total score capped at maximum possible value")

    # Overall Score
    print(f"\n🎯 OVERALL SCORE: {total_score:.1f}/{max_score}")

    # Detailed Scores
    print("\n📈 DETAILED SCORES:")
    print("-" * 60)

    if hasattr(evaluation, "scores") and evaluation.scores:
        # Define category maximums
        category_maxes = {
            "open_source": 35,
            "self_projects": 30,
            "production": 25,
            "technical_skills": 10,
        }

        # Open Source
        if hasattr(evaluation.scores, "open_source") and evaluation.scores.open_source:
            os_score = evaluation.scores.open_source
            capped_score = min(os_score.score, category_maxes["open_source"])
            print(f"🌐 Open Source:          {capped_score}/{os_score.max}")
            print(f"   Evidence: {os_score.evidence}")
            print()

        # Self Projects
        if (
            hasattr(evaluation.scores, "self_projects")
            and evaluation.scores.self_projects
        ):
            sp_score = evaluation.scores.self_projects
            capped_score = min(sp_score.score, category_maxes["self_projects"])
            print(f"🚀 Self Projects:        {capped_score}/{sp_score.max}")
            print(f"   Evidence: {sp_score.evidence}")
            print()

        # Production Experience
        if hasattr(evaluation.scores, "production") and evaluation.scores.production:
            prod_score = evaluation.scores.production
            capped_score = min(prod_score.score, category_maxes["production"])
            print(f"🏢 Production Experience: {capped_score}/{prod_score.max}")
            print(f"   Evidence: {prod_score.evidence}")
            print()

        # Technical Skills
        if (
            hasattr(evaluation.scores, "technical_skills")
            and evaluation.scores.technical_skills
        ):
            tech_score = evaluation.scores.technical_skills
            capped_score = min(tech_score.score, category_maxes["technical_skills"])
            print(f"💻 Technical Skills:     {capped_score}/{tech_score.max}")
            print(f"   Evidence: {tech_score.evidence}")
            print()

    # Bonus Points
    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        print(f"\n⭐ BONUS POINTS: {evaluation.bonus_points.total}")
        print("-" * 30)
        print(f"   {evaluation.bonus_points.breakdown}")

    # Deductions
    if (
        hasattr(evaluation, "deductions")
        and evaluation.deductions
        and evaluation.deductions.total > 0
    ):
        print(f"\n⚠️  DEDUCTIONS: -{evaluation.deductions.total}")
        print("-" * 30)
        if evaluation.deductions.reasons:
            print(f"   {evaluation.deductions.reasons}")

    # Key Strengths
    if hasattr(evaluation, "key_strengths") and evaluation.key_strengths:
        print(f"\n✅ KEY STRENGTHS:")
        print("-" * 30)
        for i, strength in enumerate(evaluation.key_strengths, 1):
            print(f"  {i}. {strength}")

    # Areas for Improvement
    if (
        hasattr(evaluation, "areas_for_improvement")
        and evaluation.areas_for_improvement
    ):
        print(f"\n🔧 AREAS FOR IMPROVEMENT:")
        print("-" * 30)
        for i, area in enumerate(evaluation.areas_for_improvement, 1):
            print(f"  {i}. {area}")

    print("\n" + "=" * 80)


def _evaluate_resume(
    resume_data: JSONResume, github_data: dict = None, blog_data: dict = None,
    portfolio_data: dict = None, live_demo_results: list = None,
    position_type: str = None,
) -> Optional[EvaluationData]:
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)

    # Build live demo context string
    live_demo_text = ""
    if live_demo_results:
        working = sum(1 for r in live_demo_results if r["status"] == "ok")
        total = len(live_demo_results)
        lines = [f"\n\n=== LIVE DEMO STATUS ==="]
        lines.append(f"Verified {working}/{total} working project URLs:")
        for r in live_demo_results:
            icon = {"ok": "✅", "broken": "❌", "timeout": "⏰", "unreachable": "❌", "error": "⚠️"}.get(r["status"], "❓")
            lines.append(f"  {icon} {r['url']} ({r['status']})")
        lines.append(f"Bonus: +{min(working, 5)} points for working demos")
        live_demo_text = "\n".join(lines)

    evaluator = ResumeEvaluator(
        model_name=DEFAULT_MODEL,
        model_params=model_params,
        position_type=position_type,
        live_demo_data=live_demo_text,
    )

    resume_text = convert_json_resume_to_text(resume_data)

    if github_data:
        resume_text += convert_github_data_to_text(github_data)

    if portfolio_data:
        resume_text += convert_portfolio_to_text(portfolio_data)

    if live_demo_results:
        resume_text += live_demo_text

    if blog_data:
        resume_text += convert_blog_data_to_text(blog_data)

    evaluation_result = evaluator.evaluate_resume(resume_text)

    # print(evaluation_result)

    return evaluation_result


def is_valid_resume_data(resume_data: JSONResume) -> bool:
    """Check if the resume data has at least some extracted core content."""
    if not resume_data:
        return False
    core_sections = [
        resume_data.basics,
        resume_data.work,
        resume_data.education,
        resume_data.skills,
        resume_data.projects,
    ]
    return any(section is not None for section in core_sections)


def find_profile(profiles, network):
    if not profiles:
        return None
    return next(
        (p for p in profiles if p.network and p.network.lower() == network.lower()),
        None,
    )


def process_pipeline(pdf_path: str) -> Optional[dict]:
    """
    Run the complete resume processing pipeline for a single PDF.

    Returns a dict with all pipeline results, or None on critical failure.
    """
    cache_filename = (
        f"cache/resumecache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )
    github_cache_filename = (
        f"cache/githubcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )

    resume_data = None
    cache_loaded = False

    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"Loading cached data from {cache_filename}")
        try:
            cached_data = json.loads(Path(cache_filename).read_text(encoding="utf-8"))
            loaded_resume = JSONResume(**cached_data)
            if not is_valid_resume_data(loaded_resume):
                raise ValueError("Cached resume data contains no core content")
            resume_data = loaded_resume
            cache_loaded = True
        except Exception as e:
            print(f"⚠️ Warning: Invalid cache file {cache_filename}: {e}")
            print("Ignoring cache and reprocessing PDF...")
            try:
                os.remove(cache_filename)
            except Exception as delete_err:
                print(
                    f"Failed to delete invalid cache file {cache_filename}: {delete_err}"
                )

    if not cache_loaded:
        logger.debug(
            f"Extracting data from PDF"
            + (" and caching to " + cache_filename if DEVELOPMENT_MODE else "")
        )
        pdf_handler = PDFHandler()
        resume_data = pdf_handler.extract_json_from_pdf(pdf_path)

        if resume_data == None:
            return None

        if DEVELOPMENT_MODE:
            if is_valid_resume_data(resume_data):
                os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
                Path(cache_filename).write_text(
                    json.dumps(resume_data.model_dump(), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            else:
                logger.warning(
                    "Newly extracted resume data is empty/invalid. Skipping cache write."
                )

    github_data = {}
    github_cache_loaded = False
    if DEVELOPMENT_MODE and os.path.exists(github_cache_filename):
        print(f"Loading cached data from {github_cache_filename}")
        try:
            loaded_github = json.loads(
                Path(github_cache_filename).read_text(encoding="utf-8")
            )
            if (
                not isinstance(loaded_github, dict)
                or not loaded_github
                or "profile" not in loaded_github
            ):
                raise ValueError("Cached GitHub data is invalid or empty")
            github_data = loaded_github
            github_cache_loaded = True
        except Exception as e:
            print(f"⚠️ Warning: Invalid GitHub cache file {github_cache_filename}: {e}")
            print("Ignoring GitHub cache and refetching...")
            try:
                os.remove(github_cache_filename)
            except Exception as delete_err:
                print(
                    f"Failed to delete invalid GitHub cache file {github_cache_filename}: {delete_err}"
                )

    if not github_cache_loaded:
        profiles = []
        if resume_data and hasattr(resume_data, "basics") and resume_data.basics:
            profiles = resume_data.basics.profiles or []
        github_profile = find_profile(profiles, "Github")

        if github_profile:
            print(
                f"Fetching GitHub data"
                + (
                    " and caching to " + github_cache_filename
                    if DEVELOPMENT_MODE
                    else ""
                )
            )
            github_data = fetch_and_display_github_info(github_profile.url)

            if (
                DEVELOPMENT_MODE
                and github_data
                and isinstance(github_data, dict)
                and "profile" in github_data
            ):
                os.makedirs(os.path.dirname(github_cache_filename), exist_ok=True)
                Path(github_cache_filename).write_text(
                    json.dumps(github_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

    portfolio_data = None
    if resume_data and hasattr(resume_data, "basics") and resume_data.basics:
        portfolio_url = resume_data.basics.url
        if portfolio_url:
            print(f"Fetching portfolio from {portfolio_url}...")
            portfolio_data = fetch_portfolio(portfolio_url)
            if portfolio_data:
                print(f"  Found: {portfolio_data.get('title', '')}")

    # Live demo verification
    live_demo_results = []
    all_urls = []
    all_urls.extend(extract_urls_from_github(github_data))
    all_urls.extend(extract_urls_from_portfolio(portfolio_data))
    if all_urls:
        print(f"🔍 Verifying {len(all_urls)} project URLs...")
        live_demo_results = verify_urls(all_urls)
        working = sum(1 for r in live_demo_results if r["status"] == "ok")
        print(f"  {working}/{len(live_demo_results)} demos working")

    score = _evaluate_resume(
        resume_data, github_data,
        portfolio_data=portfolio_data,
        live_demo_results=live_demo_results,
    )

    # Generate improvements from evaluation
    improvements = None
    if score:
        resume_text = convert_json_resume_to_text(resume_data)
        if github_data:
            resume_text += convert_github_data_to_text(github_data)
        if portfolio_data:
            resume_text += convert_portfolio_to_text(portfolio_data)
        try:
            improvements = generate_improvements(score, resume_text)
        except Exception as e:
            logger.warning(f"Failed to generate improvements: {e}")

    candidate_name = os.path.basename(pdf_path).replace(".pdf", "")
    if (
        resume_data
        and hasattr(resume_data, "basics")
        and resume_data.basics
        and resume_data.basics.name
    ):
        candidate_name = resume_data.basics.name

    total_score = 0
    max_score = 0
    if score and hasattr(score, "scores") and score.scores:
        for category_name, category_data in score.scores.model_dump().items():
            category_score = min(category_data["score"], category_data["max"])
            total_score += category_score
            max_score += category_data["max"]

    if hasattr(score, "bonus_points") and score.bonus_points:
        total_score += score.bonus_points.total
    if hasattr(score, "deductions") and score.deductions:
        total_score -= score.deductions.total

    max_possible_score = max_score + 20
    if total_score > max_possible_score:
        total_score = max_possible_score

    return {
        "file": os.path.basename(pdf_path),
        "name": candidate_name,
        "resume_data": resume_data,
        "github_data": github_data,
        "portfolio_data": portfolio_data,
        "score": score,
        "overall_score": total_score,
        "max_score": max_score,
        "live_demo_results": live_demo_results,
        "improvements": improvements,
    }


def main(pdf_path):
    print("""
╔══════════════════════════════════════════╗
║             KUNJ - EVALUATION               ║
║     AI-Powered Hiring Platform           ║
╚══════════════════════════════════════════╝
""")
    result = process_pipeline(pdf_path)
    if result is None:
        return None

    score = result["score"]
    resume_data = result["resume_data"]
    github_data = result["github_data"]
    portfolio_data = result["portfolio_data"]
    candidate_name = result["name"]
    live_demo_results = result.get("live_demo_results", [])
    improvements = result.get("improvements")

    print_evaluation_results(score, candidate_name)

    if score:
        html_report = generate_html_report(
            candidate_name=candidate_name,
            resume_data=resume_data,
            evaluation=score,
            github_data=github_data,
            portfolio_data=portfolio_data,
            live_demo_status=live_demo_results,
            improvements=improvements,
        )
        report_filename = f"report_{os.path.basename(pdf_path).replace('.pdf', '')}.html"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(html_report)
        print(f"📄 HTML report saved to {report_filename}")

    # Record score history
    if score and hasattr(score, "scores"):
        s = score.scores
        record_score(
            file_name=os.path.basename(pdf_path),
            candidate_name=candidate_name,
            overall_score=result["overall_score"],
            max_score=result["max_score"],
            open_source=s.open_source.score if s.open_source else 0,
            self_projects=s.self_projects.score if s.self_projects else 0,
            production=s.production.score if s.production else 0,
            technical_skills=s.technical_skills.score if s.technical_skills else 0,
            bonus=score.bonus_points.total if score.bonus_points else 0,
            deductions=score.deductions.total if score.deductions else 0,
        )

    if DEVELOPMENT_MODE:
        csv_row = transform_evaluation_response(
            file_name=os.path.basename(pdf_path),
            evaluation=score,
            resume_data=resume_data,
            github_data=github_data,
        )

        csv_path = "resume_evaluations.csv"
        file_exists = os.path.exists(csv_path)

        with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = list(csv_row.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(csv_row)

    return score


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if len(sys.argv) < 2:
        print("Usage: python score.py <pdf_path> [--history]")
        exit(1)

    if "--history" in sys.argv:
        show_history()
        exit(0)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' does not exist.")
        exit(1)

    main(pdf_path)
