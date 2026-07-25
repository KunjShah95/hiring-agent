"""
Semantic search for Kunj — BGE-M3 embeddings + pgvector similarity search.

Provides:
- EmbedAndSearchMixin: Generate embeddings and search across candidates
- CandidateSearch: High-level API for semantic candidate matching
"""
import logging
import numpy as np
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Will be lazily loaded
_model = None

# BGE-M3 outputs 1024-dimensional dense embeddings
EMBEDDING_DIM = 1024


def get_embedding_model():
    """Lazy-load the BGE-M3 embedding model (loaded once, cached globally)."""
    global _model
    if _model is None:
        logger.info("Loading BGE-M3 embedding model (first load may take a moment)...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('BAAI/bge-m3')
        logger.info("BGE-M3 model loaded successfully")
    return _model


def compute_embedding(text: str) -> Optional[List[float]]:
    """Compute a BGE-M3 dense embedding for a single text string."""
    try:
        model = get_embedding_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to compute embedding: {e}")
        return None


def build_resume_text_for_embedding(candidate_data: Dict[str, Any]) -> str:
    """Build a compact text representation of a candidate for embedding.

    Combines key fields into a single searchable string so similar
    candidates can be found by semantic similarity.
    """
    parts = []
    if candidate_data.get("name"):
        parts.append(f"Name: {candidate_data['name']}")
    if candidate_data.get("email"):
        parts.append(f"Email: {candidate_data['email']}")
    if candidate_data.get("location"):
        parts.append(f"Location: {candidate_data['location']}")
    if candidate_data.get("ctc_current"):
        parts.append(f"Current CTC: {candidate_data['ctc_current']}")
    if candidate_data.get("ctc_expected"):
        parts.append(f"Expected CTC: {candidate_data['ctc_expected']}")
    if candidate_data.get("preferred_locations"):
        locs = candidate_data["preferred_locations"]
        if isinstance(locs, list):
            parts.append(f"Preferred Locations: {', '.join(locs)}")
    if candidate_data.get("skills"):
        skills = candidate_data["skills"]
        if isinstance(skills, list):
            parts.append(f"Skills: {', '.join(skills)}")
        elif isinstance(skills, str):
            parts.append(f"Skills: {skills}")
    if candidate_data.get("resume_text"):
        # Take first 2000 chars of resume to stay within reasonable token limit
        text = candidate_data["resume_text"][:2000]
        parts.append(f"Resume: {text}")
    if candidate_data.get("summary"):
        parts.append(f"Summary: {candidate_data['summary']}")

    return "\n".join(parts)


def hybrid_search_candidates(
    query_text: str,
    sqlalchemy_session,
    candidate_model,
    limit: int = 20,
    min_score: float = 0.0,
    filters: Optional[Dict] = None,
) -> List[Dict]:
    """Search candidates by semantic similarity to a query text.

    Args:
        query_text: Natural language query (e.g. "senior python dev in Bangalore")
        sqlalchemy_session: SQLAlchemy Session object
        candidate_model: SQLAlchemy Candidate model class
        limit: Max results to return
        min_score: Minimum similarity threshold (0.0-1.0)
        filters: Optional dict of field filters e.g. {"location": "Bangalore"}

    Returns:
        List of dicts with candidate info and similarity score
    """
    from sqlalchemy import select

    query_emb = compute_embedding(query_text)
    if query_emb is None:
        logger.error("Failed to compute query embedding")
        return []

    try:
        # Use cosine distance via pgvector's <=> operator
        # pgvector cosine_distance returns 0 (identical) to 2 (opposite)
        # We convert to similarity: 1 - (distance / 2)
        distance_col = candidate_model.embedding.cosine_distance(query_emb)

        stmt = select(
            candidate_model,
            distance_col.label("distance"),
        ).order_by(distance_col).limit(limit)

        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                col = getattr(candidate_model, field, None)
                if col is not None:
                    stmt = stmt.where(col == value)

        rows = sqlalchemy_session.execute(stmt).all()
        results = []
        for row in rows:
            candidate = row[0]
            distance = row[1]
            # Convert cosine distance (0-2) to similarity score (1-0)
            similarity = max(0.0, 1.0 - (distance / 2.0))

            if similarity < min_score:
                continue

            results.append({
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
                "similarity_score": round(similarity, 4),
                "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            })

        return results

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return []


def search_candidates_by_jd(
    job_description: str,
    sqlalchemy_session,
    candidate_model,
    limit: int = 20,
    min_score: float = 0.0,
) -> List[Dict]:
    """Find candidates matching a job description using semantic search.

    This is the primary use case: given a JD, find the best matching candidates.
    """
    return hybrid_search_candidates(
        query_text=job_description,
        sqlalchemy_session=sqlalchemy_session,
        candidate_model=candidate_model,
        limit=limit,
        min_score=min_score,
    )
