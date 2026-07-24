"""
Configuration settings for the Resumind platform.
"""
import os
from typing import Dict, Any

DEVELOPMENT_MODE = True


def load_settings() -> Dict[str, Any]:
    return {
        "APP_NAME": "Resumind",
        "ENV": os.getenv("RESUMIND_ENV", "development"),
        "SECRET_KEY": os.getenv("RESUMIND_SECRET_KEY", "dev-secret-key"),
        "DATABASE_URL": os.getenv("RESUMIND_DATABASE_URL", ""),
        "REDIS_URL": os.getenv("RESUMIND_REDIS_URL", ""),
        "LLM_PROVIDER": os.getenv("RESUMIND_LLM_PROVIDER", "ollama"),
        "DEFAULT_MODEL": os.getenv("RESUMIND_DEFAULT_MODEL", "deepseek-v4-flash"),
        "OLLAMA_HOST": os.getenv("RESUMIND_OLLAMA_HOST"),
        "OLLAMA_API_KEY": os.getenv("RESUMIND_OLLAMA_API_KEY"),
        "GEMINI_API_KEY": os.getenv("RESUMIND_GEMINI_API_KEY"),
        "LANGFUSE_HOST": os.getenv("RESUMIND_LANGFUSE_HOST"),
        "LANGFUSE_PUBLIC_KEY": os.getenv("RESUMIND_LANGFUSE_PUBLIC_KEY"),
        "LANGFUSE_SECRET_KEY": os.getenv("RESUMIND_LANGFUSE_SECRET_KEY"),
        "OTEL_EXPORTER_OTLP_ENDPOINT": os.getenv("RESUMIND_OTEL_EXPORTER_OTLP_ENDPOINT"),
        "CELERY_BROKER_URL": os.getenv("RESUMIND_CELERY_BROKER_URL", "redis://localhost:6379/0"),
        "CELERY_RESULT_BACKEND": os.getenv("RESUMIND_CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        "NAUKRI_API_KEY": os.getenv("RESUMIND_NAUKRI_API_KEY"),
        "NAUKRI_API_SECRET": os.getenv("RESUMIND_NAUKRI_API_SECRET"),
        "INDEED_PUBLISHER_ID": os.getenv("RESUMIND_INDEED_PUBLISHER_ID"),
        "INDEED_API_KEY": os.getenv("RESUMIND_INDEED_API_KEY"),
        "GLASSDOOR_PARTNER_ID": os.getenv("RESUMIND_GLASSDOOR_PARTNER_ID"),
        "GLASSDOOR_API_KEY": os.getenv("RESUMIND_GLASSDOOR_API_KEY"),
    }


settings = load_settings()