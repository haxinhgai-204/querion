"""Predefined AI model registry — provider + purpose + dimensions."""

MODELS = [
    # --- OpenAI Embeddings ---
    {"provider": "openai", "model": "text-embedding-3-small", "purpose": "embedding", "dimensions": 1536, "label": "Text Embedding 3 Small"},
    {"provider": "openai", "model": "text-embedding-ada-002", "purpose": "embedding", "dimensions": 1536, "label": "Ada 002 (Legacy)"},
    # --- OpenAI LLMs ---
    {"provider": "openai", "model": "gpt-4o", "purpose": "llm", "dimensions": None, "label": "GPT-4o"},
    {"provider": "openai", "model": "gpt-4o-mini", "purpose": "llm", "dimensions": None, "label": "GPT-4o Mini"},
    {"provider": "openai", "model": "gpt-4-turbo", "purpose": "llm", "dimensions": None, "label": "GPT-4 Turbo"},
    {"provider": "openai", "model": "gpt-3.5-turbo", "purpose": "llm", "dimensions": None, "label": "GPT-3.5 Turbo"},
    # --- Google Embeddings ---
    {"provider": "google", "model": "gemini-embedding-001", "purpose": "embedding", "dimensions": 768, "label": "Gemini Embedding 001"},
    {"provider": "google", "model": "gemini-embedding-2-preview", "purpose": "embedding", "dimensions": 768, "label": "Gemini Embedding 2 Preview"},
    # --- Google LLMs ---
    {"provider": "google", "model": "gemini-2.5-flash", "purpose": "llm", "dimensions": None, "label": "Gemini 2.5 Flash"},
    {"provider": "google", "model": "gemini-2.5-pro", "purpose": "llm", "dimensions": None, "label": "Gemini 2.5 Pro"},
    {"provider": "google", "model": "gemini-2.0-flash-lite", "purpose": "llm", "dimensions": None, "label": "Gemini 2.0 Flash Lite"},
    # --- Anthropic LLMs ---
    {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "purpose": "llm", "dimensions": None, "label": "Claude Sonnet 4"},
    {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "purpose": "llm", "dimensions": None, "label": "Claude 3.5 Sonnet"},
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "purpose": "llm", "dimensions": None, "label": "Claude 3.5 Haiku"},

    # ============================================================
    # OpenRouter — Embeddings (all available models)
    # ============================================================
    # -- OpenAI via OR --
    {"provider": "openrouter", "model": "openai/text-embedding-3-small", "purpose": "embedding", "dimensions": 1536, "label": "OpenAI Embed 3 Small"},
    {"provider": "openrouter", "model": "openai/text-embedding-3-large", "purpose": "embedding", "dimensions": 3072, "label": "OpenAI Embed 3 Large"},
    {"provider": "openrouter", "model": "openai/text-embedding-ada-002", "purpose": "embedding", "dimensions": 1536, "label": "OpenAI Ada 002"},
    # -- Google via OR --
    {"provider": "openrouter", "model": "google/gemini-embedding-001", "purpose": "embedding", "dimensions": 768, "label": "Gemini Embedding 001"},
    # -- Qwen via OR --
    {"provider": "openrouter", "model": "qwen/qwen3-embedding-8b", "purpose": "embedding", "dimensions": 1024, "label": "Qwen3 Embedding 8B"},
    {"provider": "openrouter", "model": "qwen/qwen3-embedding-4b", "purpose": "embedding", "dimensions": 1024, "label": "Qwen3 Embedding 4B"},
    # -- Mistral via OR --
    {"provider": "openrouter", "model": "mistralai/mistral-embed-2312", "purpose": "embedding", "dimensions": 1024, "label": "Mistral Embed"},
    {"provider": "openrouter", "model": "mistralai/codestral-embed-2505", "purpose": "embedding", "dimensions": 1024, "label": "Codestral Embed"},
    # -- Perplexity via OR --
    {"provider": "openrouter", "model": "perplexity/pplx-embed-v1-4b", "purpose": "embedding", "dimensions": 1024, "label": "Perplexity Embed V1 4B"},
    {"provider": "openrouter", "model": "perplexity/pplx-embed-v1-0.6b", "purpose": "embedding", "dimensions": 1024, "label": "Perplexity Embed V1 0.6B"},
    # -- NVIDIA via OR (free) --
    {"provider": "openrouter", "model": "nvidia/llama-nemotron-embed-vl-1b-v2:free", "purpose": "embedding", "dimensions": 1024, "label": "NVIDIA Nemotron Embed 1B (Free)"},
    # -- BAAI via OR --
    {"provider": "openrouter", "model": "baai/bge-m3", "purpose": "embedding", "dimensions": 1024, "label": "BAAI BGE-M3 (Multilingual)"},
    {"provider": "openrouter", "model": "baai/bge-large-en-v1.5", "purpose": "embedding", "dimensions": 1024, "label": "BAAI BGE Large EN v1.5"},
    {"provider": "openrouter", "model": "baai/bge-base-en-v1.5", "purpose": "embedding", "dimensions": 768, "label": "BAAI BGE Base EN v1.5"},
    # -- Intfloat via OR --
    {"provider": "openrouter", "model": "intfloat/multilingual-e5-large", "purpose": "embedding", "dimensions": 1024, "label": "E5 Large Multilingual"},
    {"provider": "openrouter", "model": "intfloat/e5-large-v2", "purpose": "embedding", "dimensions": 1024, "label": "E5 Large v2"},
    {"provider": "openrouter", "model": "intfloat/e5-base-v2", "purpose": "embedding", "dimensions": 768, "label": "E5 Base v2"},
    # -- Sentence Transformers via OR --
    {"provider": "openrouter", "model": "sentence-transformers/all-mpnet-base-v2", "purpose": "embedding", "dimensions": 768, "label": "all-mpnet-base-v2"},
    {"provider": "openrouter", "model": "sentence-transformers/all-minilm-l12-v2", "purpose": "embedding", "dimensions": 384, "label": "all-MiniLM-L12-v2"},
    {"provider": "openrouter", "model": "sentence-transformers/all-minilm-l6-v2", "purpose": "embedding", "dimensions": 384, "label": "all-MiniLM-L6-v2"},
    {"provider": "openrouter", "model": "sentence-transformers/paraphrase-minilm-l6-v2", "purpose": "embedding", "dimensions": 384, "label": "paraphrase-MiniLM-L6-v2"},
    {"provider": "openrouter", "model": "sentence-transformers/multi-qa-mpnet-base-dot-v1", "purpose": "embedding", "dimensions": 768, "label": "multi-qa-mpnet-base-dot-v1"},
    # -- GTE via OR --
    {"provider": "openrouter", "model": "thenlper/gte-large", "purpose": "embedding", "dimensions": 1024, "label": "GTE Large"},
    {"provider": "openrouter", "model": "thenlper/gte-base", "purpose": "embedding", "dimensions": 768, "label": "GTE Base"},

    # ============================================================
    # OpenRouter — LLMs (Qwen, Google, OpenAI picks)
    # ============================================================
    # -- Google via OR --
    {"provider": "openrouter", "model": "google/gemini-2.5-flash", "purpose": "llm", "dimensions": None, "label": "Gemini 2.5 Flash"},
    {"provider": "openrouter", "model": "google/gemini-2.5-pro", "purpose": "llm", "dimensions": None, "label": "Gemini 2.5 Pro"},
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-001", "purpose": "llm", "dimensions": None, "label": "Gemini 2.0 Flash"},
    {"provider": "openrouter", "model": "google/gemini-2.0-flash-lite-001", "purpose": "llm", "dimensions": None, "label": "Gemini 2.0 Flash Lite"},
    # -- OpenAI via OR --
    {"provider": "openrouter", "model": "openai/gpt-4o", "purpose": "llm", "dimensions": None, "label": "GPT-4o"},
    {"provider": "openrouter", "model": "openai/gpt-4o-mini", "purpose": "llm", "dimensions": None, "label": "GPT-4o Mini"},
    {"provider": "openrouter", "model": "openai/gpt-4.1-nano", "purpose": "llm", "dimensions": None, "label": "GPT-4.1 Nano"},
    {"provider": "openrouter", "model": "openai/gpt-4.1-mini", "purpose": "llm", "dimensions": None, "label": "GPT-4.1 Mini"},
    {"provider": "openrouter", "model": "openai/gpt-4.1", "purpose": "llm", "dimensions": None, "label": "GPT-4.1"},
    # -- Qwen via OR --
    {"provider": "openrouter", "model": "qwen/qwen-2.5-72b-instruct", "purpose": "llm", "dimensions": None, "label": "Qwen 2.5 72B Instruct"},
    {"provider": "openrouter", "model": "qwen/qwen-2.5-7b-instruct", "purpose": "llm", "dimensions": None, "label": "Qwen 2.5 7B Instruct"},
    {"provider": "openrouter", "model": "qwen/qwen3-235b-a22b", "purpose": "llm", "dimensions": None, "label": "Qwen3 235B"},
    {"provider": "openrouter", "model": "qwen/qwen3-30b-a3b", "purpose": "llm", "dimensions": None, "label": "Qwen3 30B"},
    {"provider": "openrouter", "model": "qwen/qwen3-32b", "purpose": "llm", "dimensions": None, "label": "Qwen3 32B"},
    {"provider": "openrouter", "model": "qwen/qwen3-8b", "purpose": "llm", "dimensions": None, "label": "Qwen3 8B"},
    {"provider": "openrouter", "model": "qwen/qwq-32b", "purpose": "llm", "dimensions": None, "label": "QwQ 32B (Reasoning)"},
]

PROVIDERS = [
    {"value": "openrouter", "label": "OpenRouter"},
    {"value": "openai", "label": "OpenAI"},
    {"value": "google", "label": "Google Gemini"},
    {"value": "anthropic", "label": "Anthropic"},
]


def get_models_for_provider(provider: str, purpose: str | None = None) -> list[dict]:
    """Get models for a provider, optionally filtered by purpose."""
    result = [m for m in MODELS if m["provider"] == provider]
    if purpose:
        result = [m for m in result if m["purpose"] == purpose]
    return result


def get_model_dimensions(provider: str, model: str) -> int | None:
    """Get embedding dimensions for a specific model."""
    for m in MODELS:
        if m["provider"] == provider and m["model"] == model:
            return m["dimensions"]
    return None
