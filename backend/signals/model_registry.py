"""Model registry — all available LLM models + metadata."""

from __future__ import annotations

MODELS = {
    "groq/llama-3.3-70b": {
        "provider": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "cost_per_1m_tokens": 0,
        "rate_limit": "1000 req/day, 6000 tokens/min",
        "notes": "Fastest free option. Strong reasoning.",
    },
    "mistral/mistral-small": {
        "provider": "mistral",
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "env_key": "MISTRAL_API_KEY",
        "cost_per_1m_tokens": 0,
        "rate_limit": "1B tokens/month",
        "notes": "Most generous free quota.",
    },
}


def get_model_info(model_key: str) -> dict | None:
    return MODELS.get(model_key)


def get_all_models() -> dict:
    return MODELS.copy()
