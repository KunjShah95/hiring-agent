"""Tests for Celery tasks."""
import tasks
from worker import app as celery_app


class TestCeleryConfig:
    def test_app_configured(self):
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.main == "kunj"

    def test_evaluate_task_registered(self):
        assert "evaluate_resume" in celery_app.tasks
