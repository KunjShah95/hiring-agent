"""
Async tasks for Resumind.evaluation pipeline.
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

        # Auto-generate embedding for semantic search if DB is available
        try:
            from db import get_engine, Candidate
            from sqlalchemy.orm import Session
            from semantic_search import compute_embedding, build_resume_text_for_embedding

            engine = get_engine()
            if engine and resume.basics and resume.basics.name:
                # Extract skills from parsed resume data
                skills = []
                if resume.skills:
                    for skill in resume.skills:
                        if skill.name:
                            skills.append(skill.name)
                        if skill.keywords:
                            skills.extend(skill.keywords)

                candidate_data = {
                    "name": resume.basics.name,
                    "email": resume.basics.email,
                    "location": f"{resume.basics.location.city}, {resume.basics.location.region}" if resume.basics.location else None,
                    "skills": skills,
                    "resume_text": resume_text,
                }
                emb_text = build_resume_text_for_embedding(candidate_data)
                embedding = compute_embedding(emb_text)

                if embedding:
                    with Session(engine) as session:
                        # Match by email first, fall back to name
                        candidate = None
                        if resume.basics.email:
                            candidate = session.query(Candidate).filter(
                                Candidate.email == resume.basics.email
                            ).first()
                        if not candidate and resume.basics.name:
                            candidate = session.query(Candidate).filter(
                                Candidate.name == resume.basics.name
                            ).first()
                            if candidate:
                                logger.warning(
                                    f"Matched candidate by name only: {resume.basics.name}. "
                                    "Consider adding email to resume data for precise matching."
                                )

                        if candidate:
                            candidate.embedding = embedding
                            candidate.resume_text = resume_text
                            session.commit()
                            logger.info(f"Stored embedding for {resume.basics.name}")
                        else:
                            candidate = Candidate(
                                name=resume.basics.name,
                                email=resume.basics.email,
                                resume_text=resume_text,
                                embedding=embedding,
                            )
                            session.add(candidate)
                            session.commit()
                            logger.info(f"Created candidate with embedding: {resume.basics.name}")
        except Exception as embed_err:
            logger.warning(f"Failed to auto-embed candidate: {embed_err}")

        return {
            "candidate_name": resume.basics.name if resume.basics else "Unknown",
            "overall_score": evaluation.overall_score if evaluation else None,
            "status": "completed",
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(f"Evaluation task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2, name="sync_integration")
def sync_integration(self, platform: str):
    """Sync candidates from a job board integration."""
    from db import get_engine, IntegrationSync, Candidate
    from sqlalchemy.orm import Session
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)
    start = datetime.utcnow()

    integration_map = {
        "naukri": ("NaukriIntegration", "naukri"),
        "indeed": ("IndeedIntegration", "indeed"),
        "glassdoor": ("GlassdoorIntegration", "glassdoor"),
    }

    if platform not in integration_map:
        raise ValueError(f"Unknown platform: {platform}")

    class_name, module_name = integration_map[platform]

    # Record sync start
    engine = get_engine()
    sync_record = None
    if engine:
        with Session(engine) as session:
            sync_record = IntegrationSync(
                platform=platform,
                sync_type="resume_ingest",
                status="running",
                started_at=start,
            )
            session.add(sync_record)
            session.commit()
            session.refresh(sync_record)

    try:
        # Import the integration module dynamically
        import importlib
        mod = importlib.import_module(module_name)
        integration_class = getattr(mod, class_name)
        integration = integration_class()

        # Test connection
        if not integration.test_connection():
            raise ConnectionError(f"Cannot connect to {platform}")

        # Search for resumes
        resumes = integration.search_resumes(limit=50)
        processed = 0
        failed = 0
        errors = []

        for resume in resumes:
            try:
                candidate_name = resume.get("name", "Unknown")
                candidate_email = resume.get("email", "")

                # Store candidate in DB if available
                if engine and candidate_name:
                    with Session(engine) as session:
                        existing = session.query(Candidate).filter(
                            Candidate.source == platform,
                            Candidate.source_id == str(resume.get("id", "")),
                        ).first()

                        if not existing:
                            candidate = Candidate(
                                source=platform,
                                source_id=str(resume.get("id", "")),
                                name=candidate_name,
                                email=candidate_email,
                                resume_text=resume.get("summary", ""),
                            )
                            session.add(candidate)
                            session.commit()

                processed += 1

            except Exception as e:
                errors.append(str(e))
                failed += 1

        duration = (datetime.utcnow() - start).total_seconds()

        # Update sync record
        if sync_record and engine:
            with Session(engine) as session:
                rec = session.get(IntegrationSync, sync_record.id)
                if rec:
                    rec.status = "completed"
                    rec.items_processed = processed
                    rec.items_failed = failed
                    rec.error_details = errors if errors else None
                    rec.completed_at = datetime.utcnow()
                    session.commit()

        logger.info(f"{platform} sync completed: {processed} processed, {failed} failed in {duration:.1f}s")

        return {
            "platform": platform,
            "status": "completed",
            "items_processed": processed,
            "items_failed": failed,
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(f"{platform} sync failed: {exc}")

        if sync_record and engine:
            with Session(engine) as session:
                rec = session.get(IntegrationSync, sync_record.id)
                if rec:
                    rec.status = "failed"
                    rec.error_details = [str(exc)]
                    rec.completed_at = datetime.utcnow()
                    session.commit()

        raise self.retry(exc=exc, countdown=120)


@celery_app.task(name="sync_all_integrations")
def sync_all_integrations():
    """Sync all configured integrations (scheduled task)."""
    platforms = []
    from config import settings

    if settings.get("NAUKRI_API_KEY"):
        platforms.append("naukri")
    if settings.get("INDEED_API_KEY"):
        platforms.append("indeed")
    if settings.get("GLASSDOOR_API_KEY"):
        platforms.append("glassdoor")

    results = []
    for platform in platforms:
        try:
            task = sync_integration.delay(platform)
            results.append({"platform": platform, "task_id": task.id})
        except Exception as e:
            results.append({"platform": platform, "error": str(e)})

    return {"message": f"Triggered sync for {len(results)} platforms", "results": results}

