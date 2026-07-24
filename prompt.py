"""
Prompts for Resume Evaluation System

This module contains all the prompts used by the resume evaluation system.
Centralizing prompts here makes them easier to maintain and update.
"""

import os
from dotenv import load_dotenv
from models import ModelProvider

# Load environment variables
load_dotenv()

# Constants
DEFAULT_MODEL_NAME = "gemma3:4b"
DEFAULT_PROVIDER = ModelProvider.OLLAMA
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

# Get model and provider from environment or use defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_NAME)
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value)

# Ollama cloud settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

# Validate provider
if PROVIDER not in [p.value for p in ModelProvider]:
    PROVIDER = DEFAULT_PROVIDER.value

# Model-specific parameters
MODEL_PARAMETERS = {
    # Ollama models
    "qwen3:1.7b": {"temperature": 0.0, "top_p": 0.9},
    "gemma3:1b": {"temperature": 0.0, "top_p": 0.9},
    "qwen3:4b": {"temperature": 0.1, "top_p": 0.4},
    "gemma3:4b": {"temperature": 0.1, "top_p": 0.9},
    "gemma3:12b": {"temperature": 0.1, "top_p": 0.9},
    "mistral:7b": {"temperature": 0.1, "top_p": 0.9},
    # Ollama Cloud models (via direct API at https://ollama.com)
    "gemma4:31b": {"temperature": 0.1, "top_p": 0.9},
    "gpt-oss:20b": {"temperature": 0.1, "top_p": 0.9},
    "gpt-oss:120b": {"temperature": 0.1, "top_p": 0.9},
    "deepseek-v4-flash": {"temperature": 0.1, "top_p": 0.9},
    "deepseek-v3.1:671b": {"temperature": 0.1, "top_p": 0.9},
    "kimi-k2.6": {"temperature": 0.1, "top_p": 0.9},
    "qwen3-coder:480b": {"temperature": 0.1, "top_p": 0.9},
    # Google Gemini models
    "gemini-2.0-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.0-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-pro": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    "gemini-3.5-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-3.1-flash-lite": {"temperature": 0.1, "top_p": 0.9},
}

# Model provider mapping
# Maps model names to their provider
MODEL_PROVIDER_MAPPING = {
    # Ollama models
    "qwen3:1.7b": ModelProvider.OLLAMA,
    "gemma3:1b": ModelProvider.OLLAMA,
    "qwen3:4b": ModelProvider.OLLAMA,
    "gemma3:4b": ModelProvider.OLLAMA,
    "gemma3:12b": ModelProvider.OLLAMA,
    "mistral:7b": ModelProvider.OLLAMA,
    # Ollama Cloud models (all map to OLLAMA provider)
    "gemma4:31b": ModelProvider.OLLAMA,
    "gpt-oss:20b": ModelProvider.OLLAMA,
    "gpt-oss:120b": ModelProvider.OLLAMA,
    "deepseek-v4-flash": ModelProvider.OLLAMA,
    "deepseek-v3.1:671b": ModelProvider.OLLAMA,
    "kimi-k2.6": ModelProvider.OLLAMA,
    "qwen3-coder:480b": ModelProvider.OLLAMA,
    # Google Gemini models
    "gemini-2.0-flash": ModelProvider.GEMINI,
    "gemini-2.0-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-flash": ModelProvider.GEMINI,
    "gemini-2.5-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-pro": ModelProvider.GEMINI,
    "gemini-3.5-flash": ModelProvider.GEMINI,
    "gemini-3.1-flash-lite": ModelProvider.GEMINI,
}

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
