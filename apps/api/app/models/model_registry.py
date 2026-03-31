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
]

PROVIDERS = [
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
