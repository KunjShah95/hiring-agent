"""
Prometheus metrics for Resumind platform.
"""
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps


evaluations_total = Counter("resumind_evaluations_total", "Total evaluations", ["status"])
llm_calls_total = Counter("resumind_llm_calls_total", "Total LLM calls", ["provider", "model"])
candidates_processed = Counter("resumind_candidates_processed_total", "Candidates processed", ["source"])

evaluation_duration = Histogram(
    "resumind_evaluation_duration_seconds",
    "Evaluation duration",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)
llm_latency = Histogram(
    "resumind_llm_latency_seconds",
    "LLM call latency",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

queue_depth = Gauge("resumind_queue_depth", "Queue depth", ["queue"])
active_workers = Gauge("resumind_active_workers", "Active workers")


def track_duration(func):
    """Decorator to track function duration as a Prometheus histogram."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            evaluations_total.labels(status="success").inc()
            return result
        except Exception:
            evaluations_total.labels(status="error").inc()
            raise
        finally:
            duration = time.time() - start
            evaluation_duration.observe(duration)
    return wrapper
