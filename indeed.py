"""
Indeed integration for Resumind.
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
