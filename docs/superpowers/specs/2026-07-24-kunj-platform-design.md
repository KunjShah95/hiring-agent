# Kunj Platform Design Specification

**Date:** 2026-07-24  
**Status:** Draft  
**Author:** Brainstorming session

---

## 1. Executive Summary

Transform the existing `hiring-agent` CLI pipeline (HackerRank origin) into **Kunj** — a rebranded, observable, India-market-ready hiring evaluation platform with:

- **Service + Client architecture**: FastAPI core service + Textual TUI client
- **Two-way Indian job board integrations**: Naukri, Indeed, Glassdoor (resume ingestion + job posting)
- **Comprehensive observability**: LangFuse (LLM traces) + Grafana Stack (infrastructure)
- **Full rebrand**: Package, CLI, docs, license from HackerRank → Kunj

---

## 2. Architecture

### 2.1 High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              KUNJ PLATFORM                                   │
├─────────────────────────┬─────────────────────────┬─────────────────────────┤
│      CORE SERVICE       │       TUI CLIENT        │     INTEGRATIONS        │
│      (FastAPI)          │      (Textual)          │   (Naukri/Indeed/       │
│                         │                         │    Glassdoor)           │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ • POST /evaluate        │ • Dashboard             │ • Resume ingestion      │
│ • POST /batch-evaluate  │ • History browser       │ • Job posting           │
│ • GET  /candidates      │ • Candidate mgmt        │ • Candidate search      │
│ • GET  /jobs            │ • Live log tail         │ • Webhook handlers      │
│ • GET  /health          │ • Config wizard         │ • Sync scheduler        │
│ • GET  /metrics         │ • Evaluation detail     │                         │
└───────────┬─────────────┴───────────┬─────────────┴───────────┬─────────────┘
            │                         │                         │
            ▼                         ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SHARED INFRASTRUCTURE                                │
├──────────────────────┬──────────────────────┬──────────────────────────────┤
│   PostgreSQL         │      Redis           │    OBSERVABILITY             │
│   (Primary DB          │  Queue + Cache     │  ┌────────────────────┐     │
│   • evaluations      │  • Celery broker     │  │ LangFuse             │     │
│   • candidates       │  • Rate limit cache  │  │   - LLM traces       │     │
│   • jobs             │  • Session store     │  │   - Prompt versions  │     │
│   • sync_state       │  • Result backend    │  │   - Token costs      │     │
└──────────────────────┴──────────────────────┘  │   - Eval feedback    │     │
                                                 │  └────────────────────┘     │
                                                 │  ┌────────────────────┐     │
                                                 │  │ Grafana Stack      │     │
                                                 │  │   - Prometheus     │     │
                                                 │  │   - Loki (logs)    │     │
                                                 │  │   - Tempo (traces) │     │
                                                 │  │   - Grafana (dash) │     │
                                                 │  └────────────────────┘     │
                                                 └──────────────────────────────┘
```

### 2.2 Component Details

#### Core Service (FastAPI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/evaluate` | POST | Single resume evaluation (async, returns job_id) |
| `/evaluate/{job_id}` | GET | Poll for result |
| `/batch-evaluate` | POST | Multiple resumes (CSV/zip upload) |
| `/candidates` | GET/POST | List/create candidates |
| `/candidates/{id}` | GET/PUT/DELETE | CRUD candidate |
| `/jobs` | GET/POST | Job management (posting to boards) |
| `/integrations/naukri/sync` | POST | Trigger Naukri resume fetch |
| `/integrations/indeed/sync` | POST | Trigger Indeed resume fetch |
| `/integrations/glassdoor/sync` | POST | Trigger Glassdoor resume fetch |
| `/health` | GET | Health check (DB, Redis, integrations) |
| `/metrics` | GET | Prometheus metrics endpoint |

#### TUI Client (Textual)

| Screen | Purpose |
|--------|---------|
| `Dashboard` | Overview: recent evaluations, queue status, system health |
| `Candidates` | Browse, search, filter, view candidate profiles |
| `Evaluations` | History with scores, drill-down to evidence |
| `Jobs` | Manage job postings, sync status per board |
| `Integrations` | Configure API keys, test connections, view sync logs |
| `Observability` | Live tail: logs, traces, metrics summary |
| `Settings` | Model config, API keys, notification preferences |

#### Integrations Layer

| Platform | Capabilities | Auth |
|----------|--------------|------|
| Naukri | Resume search/download, job posting, application webhooks | API key + secret |
| Indeed | Resume search, job posting, candidate apply webhooks | Publisher API |
| Glassdoor | Job posting, employer branding, review sync | Partner API |

---

## 3. Rebranding Scope

### 3.1 Package & Code

| Current | New |
|---------|-----|
| Package: `hiring-agent` | `kunj` |
| CLI entry: `score.py` | `kunj evaluate` |
| Import: `from hiring_agent...` | `from kunj...` |
| Config: `config.py` | `kunj/config.py` |
| Module structure | `kunj/{core,tui,integrations,observability}` |

### 3.2 Documentation & Branding

- README: New title, badge, description
- LICENSE: Update copyright from `© HackerRank` → `© Kunj Contributors`
- CONTRIBUTING.md: Update org references
- PyPI: Publish as `kunj` (if public)
- ASCII logo for TUI header

### 3.3 Prompts & Templates

- No functional changes needed (provider-agnostic)
- Update template headers/comments to reference Kunj

---

## 4. Observability Design

### 4.1 Dual-Stack Approach

#### LangFuse (LLM Observability) — Self-Hosted

```
Instrumentation points:
├── PDF Extraction (per-section LLM calls)
├── GitHub Project Selection (LLM call)
├── Resume Evaluation (LLM call)
└── Improvement Generation (LLM call)

Captured per trace:
- prompt template + rendered prompt
- model + parameters (temp, top_p)
- input tokens / output tokens / cost
- latency
- structured output (parsed JSON)
- user feedback (thumbs up/down on eval quality)
```

**Deployment:** Docker Compose (PostgreSQL + ClickHouse + LangFuse)

- Free self-hosted, unlimited traces
- OpenTelemetry native ingestion

#### Grafana Stack (Infrastructure Observability)

```
Metrics (Prometheus):
- HTTP: request rate, latency (p50/p95/p99), error rate by endpoint
- Queue: depth, processing time, worker count, retry rate
- DB: connection pool, query latency, slow queries
- Cache: hit rate, memory usage
- Business: evaluations/day, avg score, pass rate

Logs (Loki):
- Structured JSON via structlog
- Correlation ID: request_id → trace_id → span_id
- Levels: DEBUG, INFO, WARN, ERROR
- Labels: service, endpoint, user_id, candidate_id

Traces (Tempo):
- OpenTelemetry auto-instrumentation (FastAPI, Redis, SQLAlchemy, httpx)
- Manual spans for: PDF parse, LLM call, GitHub fetch, evaluation
- Link to LangFuse trace via trace_id

Dashboards (Grafana):
- "Kunj Overview": health, throughput, error rate
- "Evaluation Pipeline": stage latencies, success rates
- "LLM Costs": tokens/day, cost/model, prompt version performance
- "Integrations": sync status, API latency, error rates per board
```

### 4.2 Alerting Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | `rate(http_errors[5m]) > 0.05` | Critical |
| QueueBacklog | `celery_queue_depth > 100` | Warning |
| LLMCostSpike | `daily_tokens > 2x 7d_avg` | Warning |
| SyncFailure | `integration_sync_failed > 0` | Critical |
| EvalQualityDrift | `avg_score change > 15% vs baseline` | Warning |

---

## 5. Indian Market Adaptation

### 5.1 Data Model Extensions

```python
# Additional fields for Indian context
class IndianCandidateProfile(BaseModel):
    ctc_current: Optional[str] = None          # "25 LPA"
    ctc_expected: Optional[str] = None
    notice_period_days: Optional[int] = None   # 30, 60, 90
    preferred_locations: List[str] = []        # ["Bangalore", "Hyderabad", "Remote"]
    visa_status: Optional[str] = None          # "Indian Citizen", "OCI", "H1B"
    education_board: Optional[str] = None      # "CBSE", "ICSE", "State Board"
    graduation_year: Optional[int] = None
```

### 5.2 Resume Normalization

- Parse Indian resume formats (Naukri PDF, Indeed PDF, LinkedIn PDF)
- Extract: CTC, notice period, preferred location, visa status
- Map Indian education boards to standardized format
- Handle multi-column layouts common in Indian resumes

### 5.3 Job Board Integrations

#### Naukri (Primary)

- **Resume Ingestion**: Search API → download resumes → normalize → evaluate
- **Job Posting**: Create job via API → track application webhooks
- **Candidate Search**: Keyword + location + experience + salary filters

#### Indeed (Secondary)

- **Resume Ingestion**: Indeed Resume API (if approved)
- **Job Posting**: Indeed Publisher API / XML feed
- **Webhooks**: Application notifications

#### Glassdoor (Tertiary)

- **Job Posting**: Partner API
- **Employer Branding**: Sync company profile, reviews
- **Salary Data**: Benchmark CTC expectations

### 5.4 Sync Scheduler

```
Cron: Every 4 hours
├── Naukri: Fetch new resumes matching saved searches
├── Indeed: Fetch new resumes
├── Glassdoor: Sync job status
└── Webhook processor: Handle async callbacks
```

---

## 6. Database Schema (PostgreSQL)

```sql
-- Core tables
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50),           -- 'upload', 'naukri', 'indeed', 'glassdoor'
    source_id VARCHAR(200),       -- external ID
    name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(50),
    location VARCHAR(200),
    ctc_current VARCHAR(50),
    ctc_expected VARCHAR(50),
    notice_period_days INT,
    preferred_locations TEXT[],
    visa_status VARCHAR(50),
    resume_text TEXT,
    resume_json JSONB,
    github_data JSONB,
    portfolio_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID REFERENCES candidates(id),
    job_id UUID REFERENCES jobs(id),
    status VARCHAR(20),           -- 'pending', 'running', 'completed', 'failed'
    overall_score DECIMAL(5,2),
    max_score INT,
    category_scores JSONB,        -- {open_source: {score, max, evidence}, ...}
    bonus_points JSONB,
    deductions JSONB,
    key_strengths TEXT[],
    areas_for_improvement TEXT[],
    llm_trace_id VARCHAR(100),    -- LangFuse trace ID
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(300),
    description TEXT,
    requirements TEXT,
    location VARCHAR(200),
    ctc_range VARCHAR(100),
    experience_min INT,
    experience_max INT,
    skills TEXT[],
    status VARCHAR(20),           -- 'draft', 'posted', 'closed'
    posted_to JSONB,              -- {naukri: {job_id, posted_at}, indeed: {...}}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE integration_syncs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50),         -- 'naukri', 'indeed', 'glassdoor'
    sync_type VARCHAR(50),        -- 'resume_ingest', 'job_post', 'webhook'
    status VARCHAR(20),           -- 'pending', 'running', 'completed', 'failed'
    items_processed INT DEFAULT 0,
    items_failed INT DEFAULT 0,
    error_details JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_candidates_source ON candidates(source, source_id);
CREATE INDEX idx_evaluations_candidate ON evaluations(candidate_id);
CREATE INDEX idx_evaluations_status ON evaluations(status);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_syncs_platform_status ON integration_syncs(platform, status);
```

---

## 7. Configuration

### 7.1 Environment Variables

```bash
# Core
KUNJ_ENV=development              # development, staging, production
KUNJ_SECRET_KEY=...               # JWT secret
KUNJ_DATABASE_URL=postgresql://...
KUNJ_REDIS_URL=redis://...

# LLM Providers
KUNJ_LLM_PROVIDER=ollama          # ollama, gemini
KUNJ_DEFAULT_MODEL=deepseek-v4-flash
KUNJ_OLLAMA_HOST=https://ollama.com
KUNJ_OLLAMA_API_KEY=...
KUNJ_GEMINI_API_KEY=...

# Observability
KUNJ_LANGFUSE_HOST=http://langfuse:3000
KUNJ_LANGFUSE_PUBLIC_KEY=...
KUNJ_LANGFUSE_SECRET_KEY=...
KUNJ_OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317

# Integrations
KUNJ_NAUKRI_API_KEY=...
KUNJ_NAUKRI_API_SECRET=...
KUNJ_INDEED_PUBLISHER_ID=...
KUNJ_INDEED_API_KEY=...
KUNJ_GLASSDOOR_PARTNER_ID=...
KUNJ_GLASSDOOR_API_KEY=...

# Celery
KUNJ_CELERY_BROKER_URL=redis://...
KUNJ_CELERY_RESULT_BACKEND=redis://...
```

---

## 8. Deployment

### 8.1 Local Development (Docker Compose)

```yaml
services:
  postgres: postgres:16
  redis: redis:7-alpine
  langfuse: langfuse/langfuse:latest
  tempo: grafana/tempo:latest
  loki: grafana/loki:latest
  prometheus: prom/prometheus:latest
  grafana: grafana/grafana:latest
  api: kunj-api (FastAPI + Uvicorn)
  worker: kunj-worker (Celery)
  tui: kunj-tui (Textual)
```

### 8.2 Production Options

| Target | Services |
|--------|----------|
| VM (single) | Docker Compose + systemd |
| Kubernetes | Helm charts for each component |
| Cloud Run / Container Apps | API + Worker as separate services |
| Fly.io / Railway | Simple git-push deploy |

---

## 9. Implementation Phases

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| **1. Rebrand & Core** | Rename package, restructure modules, FastAPI service with `/evaluate` | `kunj` package, API service |
| **2. TUI Client** | Textual dashboard with Dashboard, Candidates, Evaluations screens | Interactive CLI |
| **3. Observability** | LangFuse + Grafana stack, instrumentation, dashboards | Full observability |
| **4. Database & Persistence** | PostgreSQL models, migrations, candidate/eval CRUD | Persistent storage |
| **5. Async & Queue** | Celery + Redis, batch evaluation, job polling | Scalable processing |
| **6. Naukri Integration** | Resume ingestion + job posting + webhooks | Primary Indian board |
| **7. Indeed/Glassdoor** | Additional board integrations | Multi-board support |
| **8. Polish & Harden** | Tests, docs, CI/CD, security review | Production-ready |

---

## 10. Open Questions

1. **Naukri API access**: Requires partnership approval — timeline?
2. **Indeed Resume API**: Requires application — approved?
3. **Glassdoor Partner API**: Access level confirmed?
4. **Self-hosted vs Cloud LangFuse**: Preference for data residency?
5. **Authentication**: JWT for API? TUI uses local config only?
6. **Multi-tenancy**: Single org or multiple companies?

---

## 11. Approval

- [ ] Architecture approved
- [ ] Rebranding scope approved
- [ ] Observability stack approved
- [ ] Indian market scope approved
- [ ] Phase breakdown approved

*Next step: Invoke `writing-plans` skill to create detailed implementation plan.*
