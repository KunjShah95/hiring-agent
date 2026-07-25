"""
Database models and session management for Resumind.
"""
import logging
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON,
    ForeignKey, create_engine, event, text
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from datetime import datetime
from config import settings
from semantic_search import EMBEDDING_DIM

# pgvector support — gracefully handle if not installed
try:
    from pgvector.sqlalchemy import VECTOR
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    VECTOR = None


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
    embedding = Column(VECTOR(EMBEDDING_DIM), nullable=True) if HAS_PGVECTOR else Column(Text, nullable=True)
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


class IntegrationSync(Base):
    __tablename__ = "integration_syncs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50))  # 'naukri', 'indeed', 'glassdoor'
    sync_type = Column(String(50))  # 'resume_ingest', 'job_post', 'webhook'
    status = Column(String(20), default="pending")  # 'pending', 'running', 'completed', 'failed'
    items_processed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    error_details = Column(JSON)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_engine():
    url = settings.get("DATABASE_URL", "")
    if not url:
        return None
    return create_engine(url, echo=settings.get("ENV") == "development")


def init_db():
    engine = get_engine()
    if engine:
        Base.metadata.create_all(engine)
        _create_vector_index(engine)


logger = logging.getLogger(__name__)


def _create_vector_index(engine):
    """Create HNSW index on the embedding column for fast approximate search.

    HNSW (Hierarchical Navigable Small World) is a graph-based index that
    provides logarithmic search complexity. This index is for cosine distance
    (vector_cosine_ops) which matches our normalized embeddings.
    """
    if not HAS_PGVECTOR:
        logger.info("pgvector not available — skipping vector index creation")
        return

    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_candidates_embedding "
                    "ON candidates USING hnsw (embedding vector_cosine_ops)"
                )
            )
            conn.commit()
            logger.info("Created HNSW index on candidates.embedding")
    except Exception as e:
        logger.warning(f"Failed to create vector index: {e}")