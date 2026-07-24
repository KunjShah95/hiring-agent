"""
Async tasks for Resumind evaluation pipeline.
"""
from worker import app as celery_app
from pdf import PDFHandler
from github import fetch_and_display_github_info
from evaluator import ResumeEvaluator
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from transform import convert_json_resume_to_text, convert_github_data_to_text
from metrics import evaluation_duration
from config import settings
import time
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="evaluate_resume")
def evaluate_resume(self, pdf_path: str):
    """Evaluate a resume PDF asynchronously."""
    start = time.time()
    try:
        handler = PDFHandler()
        resume = handler.extract_json_from_pdf(pdf_path)
        if not resume:
            raise ValueError("Failed to extract resume")

        github_data = {}
        if resume.basics and resume.basics.profiles:
            for p in resume.basics.profiles:
                if p.network and p.network.lower() == "github":
                    github_data = fetch_and_display_github_info(p.url)
                    break

        resume_text = convert_json_resume_to_text(resume)
        if github_data:
            resume_text += convert_github_data_to_text(github_data)

        model = settings.get("DEFAULT_MODEL", DEFAULT_MODEL)
        evaluator = ResumeEvaluator(
            model_name=model,
            model_params=MODEL_PARAMETERS.get(model),
        )
        evaluation = evaluator.evaluate_resume(resume_text)

        duration = time.time() - start
        evaluation_duration.observe(duration)

        return {
            "candidate_name": resume.basics.name if resume.basics else "Unknown",
            "overall_score": evaluation.overall_score if evaluation else None,
            "status": "completed",
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(f"Evaluation task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
