"""Tests for database models."""
from db import Candidate, Evaluation, Job


class TestModels:
    def test_candidate_fields(self):
        c = Candidate()
        assert hasattr(c, "id")
        assert hasattr(c, "name")
        assert hasattr(c, "email")
        assert hasattr(c, "ctc_current")
        assert hasattr(c, "notice_period_days")
        assert hasattr(c, "preferred_locations")

    def test_evaluation_fields(self):
        e = Evaluation()
        assert hasattr(e, "candidate_id")
        assert hasattr(e, "status")
        assert hasattr(e, "overall_score")
        assert hasattr(e, "llm_trace_id")

    def test_job_fields(self):
        j = Job()
        assert hasattr(j, "title")
        assert hasattr(j, "ctc_range")
        assert hasattr(j, "skills")