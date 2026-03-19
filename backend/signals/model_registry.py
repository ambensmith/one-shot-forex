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
    "google/gemini-2.5-flash": {
        "provider": "google",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash",
        "env_key": "GOOGLE_API_KEY",
        "cost_per_1m_tokens": 0,
        "rate_limit": "1500 req/day, 1M tokens/min",
        "notes": "Google model. Strong on news/financial analysis.",
    },
    "groq/llama-3.1-8b": {
        "provider": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "env_key": "GROQ_API_KEY",
        "cost_per_1m_tokens": 0,
        "rate_limit": "Shared with groq/llama-3.3-70b",
        "notes": "Small model. Disagreement with 70B = low confidence signal.",
    },
}


def get_model_info(model_key: str) -> dict | None:
    return MODELS.get(model_key)


def get_all_models() -> dict:
    return MODELS.copy()
