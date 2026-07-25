"""
Observability for Kunj — logging, tracing, metrics.
"""
import structlog
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from fastapi import FastAPI
from config import settings


def configure_logging() -> bool:
    """Configure structlog for structured logging."""
    env = settings.get("ENV", "development")
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer() if env == "development"
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    return True


def setup_tracing(app: FastAPI = None) -> bool:
    """Configure OpenTelemetry tracing."""
    endpoint = settings.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    provider = TracerProvider()
    processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=endpoint)
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    if app:
        FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
    return True


def get_tracer(name: str = "kunj"):
    """Get a tracer for the given name."""
    return trace.get_tracer(name)