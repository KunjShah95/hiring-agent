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
