"""
Resumind FastAPI service — resume evaluation API.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from pydantic import BaseModel
from typing import List, Optional, Dict
import tempfile
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.get("APP_NAME", "Resumind"),
    version="0.1.0",
    description="Resumind hiring evaluation platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic schemas for request/response ────────────────────────────────

class CandidateCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = "manual"
    source_id: Optional[str] = None
    ctc_current: Optional[str] = None
    ctc_expected: Optional[str] = None
    notice_period_days: Optional[int] = None
    preferred_locations: Optional[List[str]] = None
    visa_status: Optional[str] = None

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    ctc_current: Optional[str] = None
    ctc_expected: Optional[str] = None
    notice_period_days: Optional[int] = None
    preferred_locations: Optional[List[str]] = None
    visa_status: Optional[str] = None

class JobCreate(BaseModel):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    ctc_range: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[str] = "draft"

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    ctc_range: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[str] = None


# ─── Health & Metrics ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check with DB, Redis, and integration status."""
    health_data = {
        "status": "ok",
        "app": settings.get("APP_NAME", "Resumind"),
        "version": "0.1.0",
        "env": settings.get("ENV", "development"),
    }

    # Check DB connectivity
    try:
        from db import get_engine
        from sqlalchemy import text
        engine = get_engine()
        if engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health_data["database"] = "connected"
        else:
            health_data["database"] = "not_configured"
    except Exception as e:
        health_data["database"] = f"error: {str(e)}"

    return health_data


@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest, REGISTRY
    return generate_latest(REGISTRY)


# ─── Evaluate Endpoints ──────────────────────────────────────────────────

@app.post("/evaluate")
async def evaluate_resume(file: UploadFile = File(...)):
    """Single resume evaluation (sync)."""
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files supported")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        content = await file.read()
        tmp.write(content)
        tmp.close()

        from pdf import PDFHandler
        from github import fetch_and_display_github_info
        from evaluator import ResumeEvaluator
        from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
        from transform import (
            convert_json_resume_to_text,
            convert_github_data_to_text,
        )

        handler = PDFHandler()
        resume = handler.extract_json_from_pdf(tmp.name)
        if not resume:
            raise HTTPException(422, "Failed to extract resume")

        github_data = {}
        if resume.basics and resume.basics.profiles:
            for p in resume.basics.profiles:
                if p.network and p.network.lower() == "github":
                    github_data = fetch_and_display_github_info(p.url)
                    break

        resume_text = convert_json_resume_to_text(resume)
        if github_data:
            resume_text += convert_github_data_to_text(github_data)

        evaluator = ResumeEvaluator(
            model_name=settings.get("DEFAULT_MODEL", DEFAULT_MODEL),
            model_params=MODEL_PARAMETERS.get(settings.get("DEFAULT_MODEL", DEFAULT_MODEL)),
        )
        evaluation = evaluator.evaluate_resume(resume_text)

        return {
            "candidate_name": resume.basics.name if resume.basics else "Unknown",
            "evaluation": json.loads(evaluation.model_dump_json()) if evaluation else None,
            "github": github_data,
        }
    finally:
        os.unlink(tmp.name)


@app.post("/batch-evaluate")
async def batch_evaluate(files: List[UploadFile] = File(...)):
    """Evaluate multiple resumes asynchronously (returns Celery task IDs)."""
    from tasks import evaluate_resume as evaluate_task
    from metrics import evaluations_total

    task_ids = []
    for file in files:
        if not file.filename or not file.filename.endswith(".pdf"):
            continue

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        try:
            content = await file.read()
            tmp.write(content)
            tmp.close()

            task = evaluate_task.delay(tmp.name)
            task_ids.append({
                "filename": file.filename,
                "task_id": task.id,
            })
        except Exception as e:
            logger.error(f"Failed to submit {file.filename}: {e}")
            task_ids.append({
                "filename": file.filename,
                "task_id": None,
                "error": str(e),
            })

    evaluations_total.labels(status="batched").inc(len(task_ids))

    return {
        "message": f"Submitted {len(task_ids)} resumes for evaluation",
        "tasks": task_ids,
    }


@app.get("/evaluate/{job_id}")
async def get_evaluation_result(job_id: str):
    """Poll for Celery task result."""
    from celery.result import AsyncResult
    from worker import app as celery_app

    result = AsyncResult(job_id, app=celery_app)

    if result.failed():
        return {
            "status": "failed",
            "error": str(result.result),
        }
    elif result.successful():
        return {
            "status": "completed",
            "result": result.result,
        }
    else:
        return {
            "status": "pending",
            "state": result.state,
        }


# ─── Candidates CRUD ─────────────────────────────────────────────────────

@app.get("/candidates")
async def list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
):
    """List candidates with optional filtering."""
    from db import get_engine, Candidate

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        query = select(Candidate).offset(skip).limit(limit).order_by(Candidate.created_at.desc())
        if source:
            query = query.where(Candidate.source == source)
        candidates = session.execute(query).scalars().all()

        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "location": c.location,
                "source": c.source,
                "ctc_current": c.ctc_current,
                "ctc_expected": c.ctc_expected,
                "notice_period_days": c.notice_period_days,
                "preferred_locations": c.preferred_locations,
                "visa_status": c.visa_status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in candidates
        ]


@app.post("/candidates")
async def create_candidate(data: CandidateCreate):
    """Create a new candidate."""
    from db import get_engine, Candidate

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy.orm import Session

    try:
        with Session(engine) as session:
            candidate = Candidate(
                name=data.name,
                email=data.email,
                phone=data.phone,
                location=data.location,
                source=data.source,
                source_id=data.source_id,
                ctc_current=data.ctc_current,
                ctc_expected=data.ctc_expected,
                notice_period_days=data.notice_period_days,
                preferred_locations=data.preferred_locations,
                visa_status=data.visa_status,
            )
            session.add(candidate)
            session.commit()
            session.refresh(candidate)

            return {
                "id": candidate.id,
                "name": candidate.name,
                "message": "Candidate created",
            }
    except Exception as e:
        raise HTTPException(500, f"Failed to create candidate: {str(e)}")


@app.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: int):
    """Get a single candidate with evaluations."""
    from db import get_engine, Candidate

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(404, "Candidate not found")

        evaluations = []
        if candidate.evaluations:
            for e in candidate.evaluations:
                evaluations.append({
                    "id": e.id,
                    "status": e.status,
                    "overall_score": e.overall_score,
                    "max_score": e.max_score,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                })

        return {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "source": candidate.source,
            "ctc_current": candidate.ctc_current,
            "ctc_expected": candidate.ctc_expected,
            "notice_period_days": candidate.notice_period_days,
            "preferred_locations": candidate.preferred_locations,
            "visa_status": candidate.visa_status,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "evaluations": evaluations,
        }


@app.put("/candidates/{candidate_id}")
async def update_candidate(candidate_id: int, data: CandidateUpdate):
    """Update a candidate."""
    from db import get_engine, Candidate

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(404, "Candidate not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(candidate, key, value)

        session.commit()
        return {"message": "Candidate updated", "id": candidate_id}


@app.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: int):
    """Delete a candidate."""
    from db import get_engine, Candidate

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(404, "Candidate not found")

        session.delete(candidate)
        session.commit()
        return {"message": "Candidate deleted", "id": candidate_id}


# ─── Jobs Management ─────────────────────────────────────────────────────

@app.get("/jobs")
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    """List jobs with optional status filter."""
    from db import get_engine, Job

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        query = select(Job).offset(skip).limit(limit).order_by(Job.created_at.desc())
        if status:
            query = query.where(Job.status == status)
        jobs = session.execute(query).scalars().all()

        return [
            {
                "id": j.id,
                "title": j.title,
                "description": j.description,
                "location": j.location,
                "ctc_range": j.ctc_range,
                "skills": j.skills,
                "status": j.status,
                "posted_to": j.posted_to,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]


@app.post("/jobs")
async def create_job(data: JobCreate):
    """Create a new job posting."""
    from db import get_engine, Job

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy.orm import Session

    try:
        with Session(engine) as session:
            job = Job(
                title=data.title,
                description=data.description,
                location=data.location,
                ctc_range=data.ctc_range,
                skills=data.skills,
                status=data.status,
            )
            session.add(job)
            session.commit()
            session.refresh(job)

            return {
                "id": job.id,
                "title": job.title,
                "message": "Job created",
            }
    except Exception as e:
        raise HTTPException(500, f"Failed to create job: {str(e)}")


@app.get("/jobs/{job_id}")
async def get_job(job_id: int):
    """Get a single job posting."""
    from db import get_engine, Job

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")

        return {
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "ctc_range": job.ctc_range,
            "skills": job.skills,
            "status": job.status,
            "posted_to": job.posted_to,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }


@app.post("/jobs/{job_id}/post")
async def post_job_to_boards(job_id: int):
    """Post a job to configured job boards."""
    from db import get_engine, Job
    from naukri import NaukriIntegration
    from indeed import IndeedIntegration
    from glassdoor import GlassdoorIntegration

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")

        job_data = {
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "ctc_range": job.ctc_range,
            "skills": job.skills,
        }

        results = {}

        # Post to Naukri
        try:
            naukri = NaukriIntegration()
            if naukri.api_key:
                naukri_id = naukri.post_job(job_data)
                results["naukri"] = {"status": "posted", "job_id": naukri_id}
            else:
                results["naukri"] = {"status": "skipped", "reason": "not configured"}
        except Exception as e:
            results["naukri"] = {"status": "failed", "error": str(e)}

        # Post to Indeed
        try:
            indeed = IndeedIntegration()
            if indeed.api_key:
                indeed_id = indeed.post_job(job_data)
                results["indeed"] = {"status": "posted", "job_id": indeed_id}
            else:
                results["indeed"] = {"status": "skipped", "reason": "not configured"}
        except Exception as e:
            results["indeed"] = {"status": "failed", "error": str(e)}

        # Post to Glassdoor
        try:
            glassdoor = GlassdoorIntegration()
            if glassdoor.api_key:
                glassdoor_id = glassdoor.post_job(job_data)
                results["glassdoor"] = {"status": "posted", "job_id": glassdoor_id}
            else:
                results["glassdoor"] = {"status": "skipped", "reason": "not configured"}
        except Exception as e:
            results["glassdoor"] = {"status": "failed", "error": str(e)}

        # Update job status
        job.status = "posted"
        job.posted_to = results
        session.commit()

        return {"message": "Job posted to boards", "results": results}


# ─── Integration Sync Endpoints ──────────────────────────────────────────

@app.post("/integrations/naukri/sync")
async def sync_naukri():
    """Trigger Naukri resume fetch."""
    return await _run_integration_sync("naukri")


@app.post("/integrations/indeed/sync")
async def sync_indeed():
    """Trigger Indeed resume fetch."""
    return await _run_integration_sync("indeed")


@app.post("/integrations/glassdoor/sync")
async def sync_glassdoor():
    """Trigger Glassdoor resume fetch."""
    return await _run_integration_sync("glassdoor")


async def _run_integration_sync(platform: str) -> dict:
    """Run sync for a given platform (async via Celery)."""
    valid_platforms = {"naukri", "indeed", "glassdoor"}

    if platform not in valid_platforms:
        raise HTTPException(400, f"Unknown platform: {platform}. Valid: {valid_platforms}")

    from tasks import sync_integration

    task = sync_integration.delay(platform)

    return {
        "message": f"{platform.title()} sync triggered",
        "task_id": task.id,
    }


@app.get("/integrations/syncs")
async def list_syncs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    platform: Optional[str] = None,
):
    """List integration sync history."""
    from db import get_engine, IntegrationSync

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        query = select(IntegrationSync).offset(skip).limit(limit).order_by(IntegrationSync.created_at.desc())
        if platform:
            query = query.where(IntegrationSync.platform == platform)
        syncs = session.execute(query).scalars().all()

        return [
            {
                "id": s.id,
                "platform": s.platform,
                "sync_type": s.sync_type,
                "status": s.status,
                "items_processed": s.items_processed,
                "items_failed": s.items_failed,
                "error_details": s.error_details,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in syncs
        ]


# ─── Semantic Search Endpoints ────────────────────────────────────────

class SearchQuery(BaseModel):
    query: str
    limit: int = 20
    min_score: float = 0.0
    filters: Optional[Dict] = None


class JDQuery(BaseModel):
    job_description: str
    limit: int = 20
    min_score: float = 0.0


@app.post("/search/candidates")
async def search_candidates(data: SearchQuery):
    """Semantic search for candidates by natural language query."""
    from db import get_engine, Candidate
    from sqlalchemy.orm import Session
    from semantic_search import hybrid_search_candidates

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    try:
        with Session(engine) as session:
            results = hybrid_search_candidates(
                query_text=data.query,
                sqlalchemy_session=session,
                candidate_model=Candidate,
                limit=data.limit,
                min_score=data.min_score,
                filters=data.filters,
            )
            return {
                "query": data.query,
                "results": results,
                "total": len(results),
            }
    except Exception as e:
        raise HTTPException(500, f"Search failed: {str(e)}")


@app.post("/search/jd-match")
async def search_by_jd(data: JDQuery):
    """Find candidates matching a job description."""
    from db import get_engine, Candidate
    from sqlalchemy.orm import Session
    from semantic_search import search_candidates_by_jd

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    try:
        with Session(engine) as session:
            results = search_candidates_by_jd(
                job_description=data.job_description,
                sqlalchemy_session=session,
                candidate_model=Candidate,
                limit=data.limit,
                min_score=data.min_score,
            )
            return {
                "job_description_preview": data.job_description[:100],
                "results": results,
                "total": len(results),
            }
    except Exception as e:
        raise HTTPException(500, f"JD match failed: {str(e)}")


@app.post("/candidates/{candidate_id}/embed")
async def embed_candidate(candidate_id: int):
    """Generate and store embedding for a specific candidate."""
    from db import get_engine, Candidate
    from sqlalchemy.orm import Session
    from semantic_search import compute_embedding, build_resume_text_for_embedding

    engine = get_engine()
    if not engine:
        raise HTTPException(503, "Database not configured")

    with Session(engine) as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(404, "Candidate not found")

        # Build text to embed — extract skills from resume_json if available
        skills = []
        if candidate.resume_json and isinstance(candidate.resume_json, dict):
            raw_skills = candidate.resume_json.get("skills", [])
            if isinstance(raw_skills, list):
                for s in raw_skills:
                    if isinstance(s, dict):
                        keywords = s.get("keywords", [])
                        if isinstance(keywords, list):
                            skills.extend(keywords)
                        elif isinstance(keywords, str):
                            skills.append(keywords)
                    elif isinstance(s, str):
                        skills.append(s)

        candidate_data = {
            "name": candidate.name,
            "email": candidate.email,
            "location": candidate.location,
            "ctc_current": candidate.ctc_current,
            "ctc_expected": candidate.ctc_expected,
            "preferred_locations": candidate.preferred_locations,
            "skills": skills,
            "resume_text": candidate.resume_text,
        }
        text = build_resume_text_for_embedding(candidate_data)

        embedding = compute_embedding(text)
        if embedding is None:
            raise HTTPException(500, "Failed to compute embedding")

        candidate.embedding = embedding
        session.commit()

        return {"message": "Embedding generated and stored", "candidate_id": candidate_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
