# Kunj Platform Implementation Plan (Existing Codebase)

> **For agentic workers:** Use subagent-driven-development to implement task-by-task.

**Goal:** Transform the hiring-agent CLI into Kunj — rebranded, with TUI, observability, and Indian job board integrations.

**Architecture:** All changes go into existing project root. New files added alongside existing ones (tui.py, api.py, observability.py, etc). Existing modules (models.py, evaluator.py, etc.) modified in-place.

**Tech Stack:** Python 3.11+, FastAPI, Textual, Celery, OpenTelemetry, LangFuse, structlog, Prometheus

---

## Phase 1: Rebrand

### Task 1.1: Update README, LICENSE, CONTRIBUTING

**Files:**

- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `LICENSE`

- [ ] **Step 1: Update README.md**
  - Title: "Kunj" instead of "Hiring Agent"
  - Description: emphasize Indian market, TUI, observability
  - GitHub badge: update to Kunj
  - Footer: remove HackerRank ©

- [ ] **Step 2: Update CONTRIBUTING.md** — replace HackerRank refs with Kunj

- [ ] **Step 3: Update LICENSE** — change "HackerRank" to "Kunj Contributors"

- [ ] **Step 4: Commit**
  `git add README.md CONTRIBUTING.md LICENSE`
  `git commit -m "docs: rebrand from HackerRank to Kunj"`

### Task 1.2: Update code references from HackerRank to Kunj

**Files:**

- Modify: `config.py`
- Modify: `models.py` (module docstring)

- [ ] **Step 1: Update config.py**

```python
"""
Configuration settings for the Kunj platform.
"""
DEVELOPMENT_MODE = True
```

- [ ] **Step 2: Update models.py docstring** — replace "HackerRank" with "Kunj" in any headers

- [ ] **Step 3: Commit**
  `git commit -m "refactor: update code references to Kunj"`

---

## Phase 2: Core Settings & API

### Task 2.1: Add settings to config.py

**Files:**

- Modify: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write test**

```python
# tests/test_config.py
from config import settings


class TestConfig:
    def test_default_env(self):
        assert settings["ENV"] == "development"

    def test_app_name(self):
        assert settings["APP_NAME"] == "Kunj"
```

- [ ] **Step 2: Update config.py** — add settings dictionary

```python
"""
Configuration settings for the Kunj platform.
"""
import os
from typing import Dict, Any

DEVELOPMENT_MODE = True


def load_settings() -> Dict[str, Any]:
    return {
        "APP_NAME": "Kunj",
        "ENV": os.getenv("KUNJ_ENV", "development"),
        "SECRET_KEY": os.getenv("KUNJ_SECRET_KEY", "dev-secret-key"),
        "DATABASE_URL": os.getenv("KUNJ_DATABASE_URL", ""),
        "REDIS_URL": os.getenv("KUNJ_REDIS_URL", ""),
        "LLM_PROVIDER": os.getenv("KUNJ_LLM_PROVIDER", "ollama"),
        "DEFAULT_MODEL": os.getenv("KUNJ_DEFAULT_MODEL", "deepseek-v4-flash"),
        "OLLAMA_HOST": os.getenv("KUNJ_OLLAMA_HOST"),
        "OLLAMA_API_KEY": os.getenv("KUNJ_OLLAMA_API_KEY"),
        "GEMINI_API_KEY": os.getenv("KUNJ_GEMINI_API_KEY"),
        "LANGFUSE_HOST": os.getenv("KUNJ_LANGFUSE_HOST"),
        "LANGFUSE_PUBLIC_KEY": os.getenv("KUNJ_LANGFUSE_PUBLIC_KEY"),
        "LANGFUSE_SECRET_KEY": os.getenv("KUNJ_LANGFUSE_SECRET_KEY"),
        "OTEL_EXPORTER_OTLP_ENDPOINT": os.getenv("KUNJ_OTEL_EXPORTER_OTLP_ENDPOINT"),
        "CELERY_BROKER_URL": os.getenv("KUNJ_CELERY_BROKER_URL", "redis://localhost:6379/0"),
        "CELERY_RESULT_BACKEND": os.getenv("KUNJ_CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        "NAUKRI_API_KEY": os.getenv("KUNJ_NAUKRI_API_KEY"),
        "NAUKRI_API_SECRET": os.getenv("KUNJ_NAUKRI_API_SECRET"),
        "INDEED_PUBLISHER_ID": os.getenv("KUNJ_INDEED_PUBLISHER_ID"),
        "INDEED_API_KEY": os.getenv("KUNJ_INDEED_API_KEY"),
        "GLASSDOOR_PARTNER_ID": os.getenv("KUNJ_GLASSDOOR_PARTNER_ID"),
        "GLASSDOOR_API_KEY": os.getenv("KUNJ_GLASSDOOR_API_KEY"),
    }


settings = load_settings()
```

- [ ] **Step 3: Commit**
  `git commit -m "feat: add settings loader to config.py"`

### Task 2.2: Create FastAPI service (api.py)

**Files:**

- Create: `api.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write test**

```python
# tests/test_api.py
from httpx import AsyncClient, ASGITransport
from api import app


class TestAPI:
    async def test_health(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/health")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"

    async def test_evaluate_no_file(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/evaluate", json={})
            assert r.status_code == 422

    async def test_metrics(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/metrics")
            assert r.status_code == 200
```

- [ ] **Step 2: Create api.py**

```python
"""
Kunj FastAPI service — resume evaluation API.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import settings
import tempfile
import os
import json

app = FastAPI(
    title=settings.get("APP_NAME", "Kunj"),
    version="0.1.0",
    description="Kunj hiring evaluation platform",
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
        "app": settings.get("APP_NAME", "Kunj"),
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
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 4: Commit**
  `git add api.py tests/test_api.py`
  `git commit -m "feat: add FastAPI service with evaluate endpoint"`

---

## Phase 3: Observability

### Task 3.1: Create observability module

**Files:**

- Create: `observability.py`
- Create: `tests/test_observability.py`

- [ ] **Step 1: Write test**

```python
# tests/test_observability.py
from observability import configure_logging, get_tracer


class TestObservability:
    def test_configure_logging(self):
        result = configure_logging()
        assert result is True

    def test_get_tracer(self):
        tracer = get_tracer("test")
        assert tracer is not None
```

- [ ] **Step 2: Create observability.py**

```python
"""
Observability for Kunj — logging, tracing, metrics.
"""
import structlog
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from fastapi import FastAPI
from config import settings


def configure_logging() -> bool:
    """Configure structlog for structured logging."""
    env = settings.get("ENV", "development")
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer() if env == "development"
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    return True


def setup_tracing(app: FastAPI = None) -> bool:
    """Configure OpenTelemetry tracing."""
    endpoint = settings.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    provider = TracerProvider()
    processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=endpoint)
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    if app:
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
    return True


def get_tracer(name: str = "kunj"):
    """Get a tracer for the given name."""
    return trace.get_tracer(name)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_observability.py -v`
Expected: PASS

- [ ] **Step 4: Commit**
  `git add observability.py tests/test_observability.py`
  `git commit -m "feat: add observability module (logging + tracing)"`

### Task 3.2: Add LangFuse integration

**Files:**

- Modify: `evaluator.py`
- Create: `tests/test_langfuse.py` (optional, depends on network)

- [ ] **Step 1: Add LangFuse callback to evaluator**

Modify `evaluator.py` — add optional LangFuse trace logging after evaluation:

```python
# At top of evaluator.py:
from config import settings
import logging

logger = logging.getLogger(__name__)


# At end of evaluate_resume method, after getting response:
def _record_langfuse_trace(self, prompt: str, response_text: str, duration_ms: float):
    """Send evaluation trace to LangFuse if configured."""
    host = settings.get("LANGFUSE_HOST")
    pk = settings.get("LANGFUSE_PUBLIC_KEY")
    sk = settings.get("LANGFUSE_SECRET_KEY")
    if not all([host, pk, sk]):
        return None

    try:
        from langfuse import Langfuse
        lf = Langfuse(host=host, public_key=pk, secret_key=sk)
        trace = lf.trace(
            name="resume_evaluation",
            input=prompt[:2000],
            output=response_text[:2000],
            metadata={
                "model": self.model_name,
                "duration_ms": duration_ms,
                "position_type": self.position_type,
            },
        )
        return trace.id
    except Exception as e:
        logger.warning(f"LangFuse trace failed: {e}")
        return None
```

- [ ] **Step 2: Wire into evaluator** — call `_record_langfuse_trace` after each evaluation

- [ ] **Step 3: Commit**
  `git commit -am "feat: add LangFuse observability to evaluator"`

### Task 3.3: Create metrics module

**Files:**

- Create: `metrics.py`

- [ ] **Step 1: Create metrics.py**

```python
"""
Prometheus metrics for Kunj platform.
"""
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps


evaluations_total = Counter("kunj_evaluations_total", "Total evaluations", ["status"])
llm_calls_total = Counter("kunj_llm_calls_total", "Total LLM calls", ["provider", "model"])
candidates_processed = Counter("kunj_candidates_processed_total", "Candidates processed", ["source"])

evaluation_duration = Histogram(
    "kunj_evaluation_duration_seconds",
    "Evaluation duration",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)
llm_latency = Histogram(
    "kunj_llm_latency_seconds",
    "LLM call latency",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

queue_depth = Gauge("kunj_queue_depth", "Queue depth", ["queue"])
active_workers = Gauge("kunj_active_workers", "Active workers")


def track_duration(func):
    """Decorator to track function duration as a Prometheus histogram."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            evaluations_total.labels(status="success").inc()
            return result
        except Exception:
            evaluations_total.labels(status="error").inc()
            raise
        finally:
            duration = time.time() - start
            evaluation_duration.observe(duration)
    return wrapper
```

- [ ] **Step 2: Commit**
  `git add metrics.py`
  `git commit -m "feat: add Prometheus metrics module"`

---

## Phase 4: Async Queue

### Task 4.1: Create Celery worker

**Files:**

- Create: `worker.py`
- Create: `tasks.py`

- [ ] **Step 1: Create worker.py**

```python
"""
Celery worker configuration for Kunj.
"""
from celery import Celery
from config import settings

app = Celery(
    "kunj",
    broker=settings.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=settings.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

- [ ] **Step 2: Create tasks.py**

```python
"""
Async tasks for Kunj evaluation pipeline.
"""
from worker import app as celery_app
from pdf import PDFHandler
from github import fetch_and_display_github_info
from evaluator import ResumeEvaluator
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from transform import convert_json_resume_to_text, convert_github_data_to_text
from metrics import evaluation_duration
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

        evaluator = ResumeEvaluator(
            model_name=settings.get("DEFAULT_MODEL", DEFAULT_MODEL),
            model_params=MODEL_PARAMETERS.get(settings.get("DEFAULT_MODEL", DEFAULT_MODEL)),
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
```

- [ ] **Step 3: Commit**
  `git add worker.py tasks.py`
  `git commit -m "feat: add Celery worker and async evaluation task"`

---

## Phase 5: Database

### Task 5.1: Create database models

**Files:**

- Create: `db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write test**

```python
# tests/test_db.py
from db import Candidate, Evaluation, Job


class TestModels:
    def test_candidate_fields(self):
        c = Candidate()
        assert hasattr(c, "id")
        assert hasattr(c, "name")
        assert hasattr(c, "ctc_current")

    def test_evaluation_fields(self):
        e = Evaluation()
        assert hasattr(e, "candidate_id")
        assert hasattr(e, "status")
        assert hasattr(e, "overall_score")

    def test_job_fields(self):
        j = Job()
        assert hasattr(j, "title")
        assert hasattr(j, "ctc_range")
```

- [ ] **Step 2: Create db.py**

```python
"""
Database models and session management for Kunj.
"""
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON,
    ForeignKey, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from datetime import datetime
from config import settings


class Base(DeclarativeBase):
    pass


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50))
    source_id = Column(String(200))
    name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))
    location = Column(String(200))
    ctc_current = Column(String(50))
    ctc_expected = Column(String(50))
    notice_period_days = Column(Integer)
    preferred_locations = Column(JSON)
    visa_status = Column(String(50))
    resume_text = Column(Text)
    resume_json = Column(JSON)
    github_data = Column(JSON)
    portfolio_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evaluations = relationship("Evaluation", back_populates="candidate")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    status = Column(String(20), default="pending")
    overall_score = Column(Float)
    max_score = Column(Integer)
    category_scores = Column(JSON)
    bonus_points = Column(JSON)
    deductions = Column(JSON)
    key_strengths = Column(JSON)
    areas_for_improvement = Column(JSON)
    llm_trace_id = Column(String(100))
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="evaluations")
    job = relationship("Job", back_populates="evaluations")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300))
    description = Column(Text)
    location = Column(String(200))
    ctc_range = Column(String(100))
    skills = Column(JSON)
    status = Column(String(20), default="draft")
    posted_to = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evaluations = relationship("Evaluation", back_populates="job")


def get_engine():
    url = settings.get("DATABASE_URL", "")
    if not url:
        return None
    return create_engine(url, echo=settings.get("ENV") == "development")


def init_db():
    engine = get_engine()
    if engine:
        Base.metadata.create_all(engine)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 4: Commit**
  `git add db.py tests/test_db.py`
  `git commit -m "feat: add database models and session management"`

---

## Phase 6: TUI Client

### Task 6.1: Create Textual TUI

**Files:**

- Create: `tui.py`
- Create: `tests/test_tui.py` (optional — Textual requires terminal)
- Modify: `score.py` (add ASCII header on startup)

- [ ] **Step 1: Create tui.py**

```python
"""
Kunj Terminal UI — Textual-based interactive dashboard.
"""
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, DataTable, Button
from textual.containers import Horizontal, Vertical
import httpx
import asyncio


class DashboardScreen(Screen):
    BINDINGS = [
        Binding("1", "show_dashboard", "Dashboard"),
        Binding("2", "show_candidates", "Candidates"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📊 Kunj Dashboard", classes="title")
            with Horizontal():
                yield Static("API: Checking...", id="api-status")
                yield Static("Queue: -", id="queue-status")
                yield Static("Evals: -", id="eval-count")
            yield DataTable(id="recent-evals")
            yield Button("Evaluate Resume", id="evaluate-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#recent-evals", DataTable)
        table.add_columns("Candidate", "Score", "Status", "Date")
        self.set_interval(30, self.refresh_status)
        asyncio.create_task(self.refresh_status())

    async def refresh_status(self) -> None:
        api_url = self.app.api_url
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{api_url}/health", timeout=5)
                if r.status_code == 200:
                    self.query_one("#api-status", Static).update("✅ Connected")
                else:
                    self.query_one("#api-status", Static).update("❌ Error")
        except Exception as e:
            self.query_one("#api-status", Static).update(f"❌ {str(e)}")


class KunjTUI(App):
    TITLE = "Kunj"
    SUB_TITLE = "Hiring Evaluation Platform"

    def __init__(self, api_url: str = "http://localhost:8000", api_key: str = None):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key

    def on_ready(self) -> None:
        self.push_screen(DashboardScreen())


def run_tui(api_url: str = "http://localhost:8000", api_key: str = None):
    """Launch the Kunj TUI."""
    app = KunjTUI(api_url=api_url, api_key=api_key)
    app.run()


if __name__ == "__main__":
    run_tui()
```

- [ ] **Step 2: Add Kunj ASCII art to score.py**

Modify `score.py` to print Kunj header when run:

```python
# At top of main() in score.py:
print("""
╔══════════════════════════════════════════╗
║           KUNJ - EVALUATION              ║
║     AI-Powered Hiring Platform           ║
╚══════════════════════════════════════════╝
""")
```

- [ ] **Step 3: Commit**
  `git add tui.py`
  `git commit -m "feat: add Textual TUI client"`

---

## Phase 7: Indian Job Board Integrations

### Task 7.1: Add Indian candidate fields to models.py

**Files:**

- Modify: `models.py`

- [ ] **Step 1: Add IndianCandidateProfile class**

```python
# Add to models.py:
class IndianCandidateProfile(BaseModel):
    """Indian market-specific candidate fields."""
    ctc_current: Optional[str] = None
    ctc_expected: Optional[str] = None
    notice_period_days: Optional[int] = None
    preferred_locations: Optional[List[str]] = None
    visa_status: Optional[str] = None
    education_board: Optional[str] = None
    graduation_year: Optional[int] = None
```

- [ ] **Step 2: Commit**
  `git commit -am "feat: add Indian candidate profile to models"`

### Task 7.2: Create integration base

**Files:**

- Create: `integration_base.py`
- Create: `naukri.py`
- Create: `indeed.py`
- Create: `glassdoor.py`

- [ ] **Step 1: Create integration_base.py**

```python
"""
Base classes for job board integrations.
"""
from abc import ABC, abstractmethod
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SyncResult:
    platform: str
    sync_type: str
    items_processed: int
    items_failed: int
    errors: List[str]
    started_at: datetime
    completed_at: datetime


class JobBoardIntegration(ABC):
    @abstractmethod
    def test_connection(self) -> bool:
        ...

    @abstractmethod
    def search_resumes(self, query: str, **filters) -> List[Dict]:
        ...

    @abstractmethod
    def post_job(self, job_data: Dict) -> str:
        ...

    @abstractmethod
    def sync_resumes(self) -> SyncResult:
        ...
```

- [ ] **Step 2: Create naukri.py**

```python
"""
Naukri.com integration for Kunj.
"""
from typing import List, Dict, Optional
from datetime import datetime
import httpx
import logging
from integration_base import JobBoardIntegration, SyncResult
from config import settings

logger = logging.getLogger(__name__)


class NaukriIntegration(JobBoardIntegration):
    BASE_URL = "https://api.naukri.com/v1"

    def __init__(self):
        self.api_key = settings.get("NAUKRI_API_KEY", "")
        self.api_secret = settings.get("NAUKRI_API_SECRET", "")

    def _headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> bool:
        try:
            resp = httpx.get(f"{self.BASE_URL}/ping", headers=self._headers(), timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Naukri connection failed: {e}")
            return False

    def search_resumes(self, query: str = "software engineer", **filters) -> List[Dict]:
        params = {"query": query, **filters}
        try:
            resp = httpx.get(
                f"{self.BASE_URL}/resumes/search",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("resumes", [])
        except Exception as e:
            logger.error(f"Naukri search failed: {e}")
            return []

    def post_job(self, job_data: Dict) -> str:
        try:
            resp = httpx.post(
                f"{self.BASE_URL}/jobs",
                headers=self._headers(),
                json=job_data,
                timeout=30,
            )
            resp.raise_for_status()
            job_id = resp.json().get("id", "")
            logger.info(f"Naukri job posted: {job_id}")
            return job_id
        except Exception as e:
            logger.error(f"Naukri job posting failed: {e}")
            raise

    def sync_resumes(self) -> SyncResult:
        start = datetime.utcnow()
        errors, processed, failed = [], 0, 0
        try:
            resumes = self.search_resumes(limit=50)
            for r in resumes:
                try:
                    processed += 1
                except Exception as e:
                    errors.append(str(e))
                    failed += 1
        except Exception as e:
            errors.append(str(e))
        return SyncResult("naukri", "resume_ingest", processed, failed, errors, start, datetime.utcnow())
```

- [ ] **Step 3: Create indeed.py**

```python
"""
Indeed integration for Kunj.
"""
from typing import List, Dict
from datetime import datetime
import httpx
import logging
from integration_base import JobBoardIntegration, SyncResult
from config import settings

logger = logging.getLogger(__name__)


class IndeedIntegration(JobBoardIntegration):
    BASE_URL = "https://apis.indeed.com/v1"

    def __init__(self):
        self.publisher_id = settings.get("INDEED_PUBLISHER_ID", "")
        self.api_key = settings.get("INDEED_API_KEY", "")

    def _headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def test_connection(self) -> bool:
        try:
            resp = httpx.get(f"{self.BASE_URL}/ping", headers=self._headers(), timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def search_resumes(self, query: str = "software engineer", **filters) -> List[Dict]:
        return []

    def post_job(self, job_data: Dict) -> str:
        try:
            resp = httpx.post(
                f"{self.BASE_URL}/jobs",
                headers=self._headers(),
                json=job_data,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("id", "")
        except Exception as e:
            logger.error(f"Indeed job posting failed: {e}")
            raise

    def sync_resumes(self) -> SyncResult:
        return SyncResult("indeed", "resume_ingest", 0, 0, [], datetime.utcnow(), datetime.utcnow())
```

- [ ] **Step 4: Create glassdoor.py**

```python
"""
Glassdoor integration for Kunj.
"""
from typing import List, Dict
from datetime import datetime
import httpx
import logging
from integration_base import JobBoardIntegration, SyncResult
from config import settings

logger = logging.getLogger(__name__)


class GlassdoorIntegration(JobBoardIntegration):
    BASE_URL = "https://api.glassdoor.com/v1"

    def __init__(self):
        self.partner_id = settings.get("GLASSDOOR_PARTNER_ID", "")
        self.api_key = settings.get("GLASSDOOR_API_KEY", "")

    def _headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def test_connection(self) -> bool:
        try:
            resp = httpx.get(f"{self.BASE_URL}/ping", headers=self._headers(), timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def search_resumes(self, query: str = "software engineer", **filters) -> List[Dict]:
        return []

    def post_job(self, job_data: Dict) -> str:
        return "glassdoor-mock-id"

    def sync_resumes(self) -> SyncResult:
        return SyncResult("glassdoor", "resume_ingest", 0, 0, [], datetime.utcnow(), datetime.utcnow())
```

- [ ] **Step 5: Commit**
  `git add integration_base.py naukri.py indeed.py glassdoor.py`
  `git commit -m "feat: add Indian job board integrations (Naukri, Indeed, Glassdoor)"`

---

## Phase 8: Docker & Infrastructure

### Task 8.1: Docker Compose

**Files:**

- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `prometheus.yml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      KUNJ_ENV: development
      KUNJ_DATABASE_URL: postgresql://kunj:kunj@postgres:5432/kunj
      KUNJ_REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  worker:
    build: .
    command: celery -A tasks worker -l info
    environment:
      KUNJ_DATABASE_URL: postgresql://kunj:kunj@postgres:5432/kunj
      KUNJ_REDIS_URL: redis://redis:6379/0
      KUNJ_CELERY_BROKER_URL: redis://redis:6379/0
      KUNJ_CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: kunj
      POSTGRES_PASSWORD: kunj
      POSTGRES_DB: kunj
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://kunj:kunj@postgres:5432/kunj
      NEXTAUTH_SECRET: change-me-secret
    depends_on:
      - postgres

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana-data:/var/lib/grafana

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  tempo:
    image: grafana/tempo:latest
    ports:
      - "4317:4317"
      - "3200:3200"

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"

volumes:
  pgdata:
  grafana-data:
```

- [ ] **Step 3: Create prometheus.yml**

```yaml
scrape_configs:
  - job_name: "kunj-api"
    scrape_interval: 15s
    static_configs:
      - targets: ["api:8000"]
```

- [ ] **Step 4: Commit**
  `git add Dockerfile docker-compose.yml prometheus.yml`
  `git commit -m "infra: add Docker Compose for Kunj platform stack"`
