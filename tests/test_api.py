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
            assert data["app"] == "Kunj"

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