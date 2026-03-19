"""Tests for LLM client and signal parsing."""

from backend.signals.llm_client import parse_llm_signal
from backend.signals.model_registry import get_all_models, get_model_info


def test_parse_valid_json():
    response = '{"direction": "long", "confidence": 0.78, "reasoning": "test", "key_factors": ["a"]}'
    result = parse_llm_signal(response)
    assert result["direction"] == "long"
    assert result["confidence"] == 0.78


def test_parse_json_with_markdown():
    response = '```json\n{"direction": "short", "confidence": 0.65, "reasoning": "test"}\n```'
    result = parse_llm_signal(response)
    assert result["direction"] == "short"


def test_parse_invalid_json():
    response = "This is not JSON at all"
    result = parse_llm_signal(response)
    assert result["direction"] == "neutral"
    assert result["confidence"] == 0.0


def test_parse_embedded_json():
    response = 'Here is my analysis:\n\n{"direction": "long", "confidence": 0.9, "reasoning": "strong"}\n\nEnd.'
    result = parse_llm_signal(response)
    assert result["direction"] == "long"


def test_model_registry():
    models = get_all_models()
    assert len(models) == 3
    assert "groq/llama-3.3-70b" in models


def test_model_info():
    info = get_model_info("groq/llama-3.3-70b")
    assert info is not None
    assert info["provider"] == "groq"
    assert info["env_key"] == "GROQ_API_KEY"


def test_unknown_model():
    info = get_model_info("unknown/model")
    assert info is None
