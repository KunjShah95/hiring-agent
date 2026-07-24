"""
Base classes for job board integrations.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
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
