"""Tests for metrics module."""
from metrics import (
    evaluations_total,
    llm_calls_total,
    evaluation_duration,
    queue_depth,
    track_duration,
)


class TestMetrics:
    def test_counters_exist(self):
        assert evaluations_total is not None
        assert llm_calls_total is not None

    def test_histograms_exist(self):
        assert evaluation_duration is not None

    def test_gauges_exist(self):
        assert queue_depth is not None

    def test_track_duration_decorator(self):
        import asyncio

        @track_duration
        async def sample():
            return 42

        result = asyncio.run(sample())
        assert result == 42
