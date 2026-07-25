"""Tests for API module."""
import pytest
from httpx import AsyncClient, ASGITransport
from api import app


@pytest.mark.asyncio
class TestAPI:
    async def test_health(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/health")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "ok"
            assert data["app"] == "Resumind"

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

    async def test_batch_evaluate_no_files(self):
        """batch-evaluate without files should return 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/batch-evaluate", json={})
            assert r.status_code == 422

    async def test_evaluate_result_invalid_id(self):
        """Poll for a non-existent task ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/evaluate/nonexistent-id")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] in ("pending", "failed")

    async def test_candidates_list_no_db(self):
        """List candidates without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/candidates")
            assert r.status_code == 503

    async def test_candidates_create_no_db(self):
        """Create candidate without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/candidates", json={"name": "Test"})
            assert r.status_code == 503

    async def test_get_candidate_not_found(self):
        """Get non-existent candidate without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/candidates/1")
            assert r.status_code == 503

    async def test_update_candidate_no_db(self):
        """Update candidate without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.put("/candidates/1", json={"name": "Updated"})
            assert r.status_code == 503

    async def test_delete_candidate_no_db(self):
        """Delete candidate without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.delete("/candidates/1")
            assert r.status_code == 503

    async def test_jobs_list_no_db(self):
        """List jobs without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/jobs")
            assert r.status_code == 503

    async def test_jobs_create_no_db(self):
        """Create job without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/jobs", json={"title": "Test Job"})
            assert r.status_code == 503

    async def test_get_job_not_found(self):
        """Get non-existent job without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/jobs/1")
            assert r.status_code == 503

    async def test_post_job_to_boards_no_db(self):
        """Post job to boards without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/jobs/1/post")
            assert r.status_code == 503

    async def test_naukri_sync(self):
        """Trigger Naukri sync should return task info."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/integrations/naukri/sync")
            assert r.status_code == 200
            data = r.json()
            assert "task_id" in data
            assert data["message"] == "Naukri sync triggered"

    async def test_indeed_sync(self):
        """Trigger Indeed sync should return task info."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/integrations/indeed/sync")
            assert r.status_code == 200
            data = r.json()
            assert "task_id" in data

    async def test_glassdoor_sync(self):
        """Trigger Glassdoor sync should return task info."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/integrations/glassdoor/sync")
            assert r.status_code == 200
            data = r.json()
            assert "task_id" in data

    async def test_syncs_list_no_db(self):
        """List sync history without DB should return 503."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/integrations/syncs")
            assert r.status_code == 503

    async def test_unknown_platform_sync(self):
        """Unknown platform route should return 404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/integrations/unknown/sync")
            assert r.status_code == 404
