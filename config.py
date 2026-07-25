"""
Configuration settings for the Kunj platform.
"""
import os
from typing import Dict, Any

DEVELOPMENT_MODE = True


def load_settings() -> Dict[str, Any]:
    return {
        "APP_NAME": "Kunj",
        "ENV": os.getenv("KUNJ_ENV", "development"),
        "SECRET_KEY": os.getenv("KUNJ_SECRET_KEY", "dev-secret-key"),
        "DATABASE_URL": os.getenv("KUNJ_DATABASE_URL", ""),
        "REDIS_URL": os.getenv("KUNJ_REDIS_URL", ""),
        "LLM_PROVIDER": os.getenv("KUNJ_LLM_PROVIDER", "ollama"),
        "DEFAULT_MODEL": os.getenv("KUNJ_DEFAULT_MODEL", "deepseek-v4-flash"),
        "OLLAMA_HOST": os.getenv("KUNJ_OLLAMA_HOST"),
        "OLLAMA_API_KEY": os.getenv("KUNJ_OLLAMA_API_KEY"),
        "GEMINI_API_KEY": os.getenv("KUNJ_GEMINI_API_KEY"),
        "LANGFUSE_HOST": os.getenv("KUNJ_LANGFUSE_HOST"),
        "LANGFUSE_PUBLIC_KEY": os.getenv("KUNJ_LANGFUSE_PUBLIC_KEY"),
        "LANGFUSE_SECRET_KEY": os.getenv("KUNJ_LANGFUSE_SECRET_KEY"),
        "OTEL_EXPORTER_OTLP_ENDPOINT": os.getenv("KUNJ_OTEL_EXPORTER_OTLP_ENDPOINT"),
        "CELERY_BROKER_URL": os.getenv("KUNJ_CELERY_BROKER_URL", "redis://localhost:6379/0"),
        "CELERY_RESULT_BACKEND": os.getenv("KUNJ_CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        "NAUKRI_API_KEY": os.getenv("KUNJ_NAUKRI_API_KEY"),
        "NAUKRI_API_SECRET": os.getenv("KUNJ_NAUKRI_API_SECRET"),
        "INDEED_PUBLISHER_ID": os.getenv("KUNJ_INDEED_PUBLISHER_ID"),
        "INDEED_API_KEY": os.getenv("KUNJ_INDEED_API_KEY"),
        "GLASSDOOR_PARTNER_ID": os.getenv("KUNJ_GLASSDOOR_PARTNER_ID"),
        "GLASSDOOR_API_KEY": os.getenv("KUNJ_GLASSDOOR_API_KEY"),
    }


settings = load_settings()