# Ollama Cloud API Integration

## Goal
Connect Hiring Agent to Ollama's direct cloud API at `https://ollama.com`, bypassing the need for a local Ollama binary.

## Changes

### `models.py` — OllamaProvider
- Accept optional `host` and `api_key` in `__init__`
- Use `ollama.Client(host=..., headers=...)` instead of module-level `ollama.chat()`
- Drop `num_ctx` option (not supported by cloud API)

### `prompt.py`
- Add `OLLAMA_API_KEY` and `OLLAMA_HOST` env vars
- Add cloud model entries to `MODEL_PARAMETERS` and `MODEL_PROVIDER_MAPPING`

### `llm_utils.py`
- Pass host and api_key to `OllamaProvider.__init__` when configured

### `.env`
- Add `OLLAMA_API_KEY` and `OLLAMA_HOST` variables

### Cloud models available
- `gpt-oss:120b`, `gpt-oss:20b` — GPT-based OSS model
- `deepseek-v4-flash` — DeepSeek v4 Flash (recommended)
- `kimi-k2.6` — Kimi K2.6
- `qwen3-coder:480b` — Qwen 3 Coder
- `deepseek-v3.1:671b` — DeepSeek v3.1

## No changes needed
- Response format — `ollama.Client.chat()` returns same `{'message': {...}}` shape
- `GeminiProvider` — untouched
- `pdf.py`, `evaluator.py`, `github.py`, `score.py` — untouched
