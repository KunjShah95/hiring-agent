"""
Resumind FastAPI service — resume evaluation API.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import settings
import tempfile
import os
import json

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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.get("APP_NAME", "Resumind"),
        "version": "0.1.0",
        "env": settings.get("ENV", "development"),
    }


@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest, REGISTRY
    return generate_latest(REGISTRY)


@app.post("/evaluate")
async def evaluate_resume(file: UploadFile = File(...)):
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)