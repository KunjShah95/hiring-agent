"""Tests for observability module."""
from observability import configure_logging, get_tracer


class TestObservability:
    def test_configure_logging(self):
        result = configure_logging()
        assert result is True

    def test_get_tracer(self):
        tracer = get_tracer("test")
        assert tracer is not None