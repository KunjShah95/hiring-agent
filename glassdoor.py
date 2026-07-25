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
