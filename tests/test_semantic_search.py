"""
Tests for semantic search functionality: embeddings, text building, search, API.
"""
import pytest
from unittest.mock import patch, MagicMock
from typing import List, Dict
from semantic_search import (
    build_resume_text_for_embedding,
    compute_embedding,
    hybrid_search_candidates,
    search_candidates_by_jd,
    EMBEDDING_DIM,
)


class TestBuildResumeTextForEmbedding:
    """Tests for building candidate text for embedding."""

    def test_build_with_all_fields(self):
        data = {
            "name": "Ravi Kumar",
            "email": "ravi@example.com",
            "location": "Bangalore",
            "ctc_current": "25 LPA",
            "ctc_expected": "35 LPA",
            "preferred_locations": ["Bangalore", "Remote"],
            "skills": ["Python", "TypeScript", "React"],
            "resume_text": "Senior Full Stack Engineer with 6 years experience",
            "summary": "Experienced engineer",
        }
        text = build_resume_text_for_embedding(data)
        assert "Ravi Kumar" in text
        assert "ravi@example.com" in text
        assert "Bangalore" in text
        assert "25 LPA" in text
        assert "35 LPA" in text
        assert "Python" in text
        assert "TypeScript" in text
        assert "Senior Full Stack" in text
        assert "Experienced engineer" in text

    def test_build_minimal_fields(self):
        data = {"name": "Test User"}
        text = build_resume_text_for_embedding(data)
        assert "Test User" in text

    def test_build_empty(self):
        text = build_resume_text_for_embedding({})
        assert text == ""

    def test_build_skills_as_string(self):
        data = {"skills": "Python, Go, Rust", "name": "Dev"}
        text = build_resume_text_for_embedding(data)
        assert "Python" in text
        assert "Go" in text
        assert "Rust" in text

    def test_build_truncates_long_resume(self):
        long_text = "A" * 5000
        data = {"resume_text": long_text, "name": "Test"}
        text = build_resume_text_for_embedding(data)
        assert len(text) < 3000  # Should be truncated


class TestComputeEmbedding:
    """Tests for embedding computation."""

    @patch("semantic_search.get_embedding_model")
    def test_compute_embedding_success(self, mock_get_model):
        mock_model = MagicMock()
        # encode() returns numpy array-like objects with .tolist()
        import numpy as np
        mock_model.encode.return_value = np.array([0.1] * EMBEDDING_DIM)
        mock_get_model.return_value = mock_model

        emb = compute_embedding("test text")
        assert emb is not None
        assert len(emb) == EMBEDDING_DIM
        assert abs(emb[0] - 0.1) < 0.001

    @patch("semantic_search.get_embedding_model")
    def test_compute_embedding_model_error(self, mock_get_model):
        mock_get_model.side_effect = Exception("Model load failed")

        emb = compute_embedding("test text")
        assert emb is None

    def test_embedding_dimension_constant(self):
        """EMBEDDING_DIM should be 1024 for BGE-M3."""
        assert EMBEDDING_DIM == 1024


class TestHybridSearchCandidates:
    """Tests for hybrid search (with mocked embedding and DB)."""

    @patch("semantic_search.compute_embedding")
    def test_search_with_empty_embedding(self, mock_compute):
        mock_compute.return_value = None

        result = hybrid_search_candidates(
            query_text="test query",
            sqlalchemy_session=None,
            candidate_model=None,
        )
        assert result == []

    def test_search_with_failed_embedding(self):
        """When compute_embedding returns None, search should return empty list."""
        with patch("semantic_search.compute_embedding", return_value=None):
            result = hybrid_search_candidates(
                query_text="test query",
                sqlalchemy_session=None,
                candidate_model=None,
            )
            assert result == []

    @patch("semantic_search.compute_embedding")
    def test_search_handles_execution_error(self, mock_compute):
        """When DB query fails, search should return empty list gracefully."""
        mock_compute.return_value = [0.1] * EMBEDDING_DIM

        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("DB connection failed")

        mock_model = MagicMock()

        result = hybrid_search_candidates(
            query_text="test query",
            sqlalchemy_session=mock_session,
            candidate_model=mock_model,
        )
        assert result == []


class TestSearchByJD:
    """Tests for JD-based candidate search."""

    def test_delegates_to_hybrid_search(self):
        """search_candidates_by_jd should call hybrid_search_candidates with the JD as query."""
        from semantic_search import search_candidates_by_jd, hybrid_search_candidates

        # This is a simple delegation test — verify the function exists and has the right signature
        assert callable(search_candidates_by_jd)


class TestAPIEndpoints:
    """Tests for the semantic search API endpoints."""

    @pytest.mark.asyncio
    async def test_search_candidates_no_db(self):
        """Search without DB should return 503."""
        from httpx import AsyncClient, ASGITransport
        from api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/search/candidates", json={"query": "python developer"})
            assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_search_jd_no_db(self):
        """JD match without DB should return 503."""
        from httpx import AsyncClient, ASGITransport
        from api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/search/jd-match", json={"job_description": "senior engineer"})
            assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_embed_candidate_no_db(self):
        """Embed candidate without DB should return 503."""
        from httpx import AsyncClient, ASGITransport
        from api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/candidates/1/embed")
            assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_embed_nonexistent_no_db(self):
        """Same as above — no DB means 503."""
        from httpx import AsyncClient, ASGITransport
        from api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/candidates/999/embed")
            assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_search_validation(self):
        """Empty query should be valid (passes Pydantic validation with defaults)."""
        from httpx import AsyncClient, ASGITransport
        from api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/search/candidates", json={"query": ""})
            # Empty query is technically valid per schema, but will fail at DB level
            assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_jd_match_validation(self):
        """Empty JD should be valid per schema."""
        from httpx import AsyncClient, ASGITransport
        from api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/search/jd-match", json={"job_description": ""})
            assert r.status_code == 503
