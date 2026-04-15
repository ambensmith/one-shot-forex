"""Unified LLM client — works with any OpenAI-compatible provider."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("forex_sentinel.llm")


class UnifiedLLMClient:
    """Works with any OpenAI-compatible provider."""

    def __init__(self, provider: str, model: str, base_url: str, api_key: str):
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise RuntimeError("openai package required. pip install openai")
        return self._client

    def _call_with_retry(self, **kwargs):
        """Call LLM API with retry on 429 rate limit."""
        for attempt in range(3):
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                if "rate_limit" in type(e).__name__.lower() or "429" in str(e):
                    wait = min(float(getattr(e, "retry_after", 10)), 60)
                    logger.warning(
                        f"Rate limited ({self.provider}/{self.model}), "
                        f"retry {attempt + 1}/3 after {wait:.0f}s"
                    )
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError(f"Rate limit exceeded after 3 retries: {self.provider}/{self.model}")

    def analyze(self, prompt: str) -> str:
        response = self._call_with_retry(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        return response.choices[0].message.content

    def analyze_json(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call LLM with JSON mode enabled. Returns raw JSON string."""
        response = self._call_with_retry(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def analyze_with_fallback(self, prompt: str,
                               fallback_clients: list[UnifiedLLMClient]) -> tuple[str, str]:
        """Try primary, fall back on failure. Returns (response, model_used)."""
        try:
            return self.analyze(prompt), f"{self.provider}/{self.model}"
        except Exception as e:
            logger.warning(f"Primary LLM failed ({self.provider}): {e}")
            for fb in fallback_clients:
                try:
                    return fb.analyze(prompt), f"{fb.provider}/{fb.model}"
                except Exception as e2:
                    logger.warning(f"Fallback LLM failed ({fb.provider}): {e2}")
            raise RuntimeError("All LLM providers failed")

    def analyze_json_with_fallback(self, prompt: str,
                                    fallback_clients: list[UnifiedLLMClient],
                                    max_tokens: int = 2000) -> tuple[str, str]:
        """Try primary with JSON mode, fall back on failure. Returns (response, model_used)."""
        try:
            return self.analyze_json(prompt, max_tokens), f"{self.provider}/{self.model}"
        except Exception as e:
            logger.warning(f"Primary LLM failed ({self.provider}): {e}")
            for fb in fallback_clients:
                try:
                    return fb.analyze_json(prompt, max_tokens), f"{fb.provider}/{fb.model}"
                except Exception as e2:
                    logger.warning(f"Fallback LLM failed ({fb.provider}): {e2}")
            raise RuntimeError("All LLM providers failed")

    @classmethod
    def from_model_key(cls, model_key: str) -> UnifiedLLMClient:
        """Create client from model registry key."""
        from backend.signals.model_registry import get_model_info
        info = get_model_info(model_key)
        if not info:
            raise ValueError(f"Unknown model: {model_key}")

        api_key = os.environ.get(info["env_key"], "")
        if not api_key:
            raise ValueError(f"API key not configured for {model_key} (env: {info['env_key']})")

        return cls(
            provider=info["provider"],
            model=info["model"],
            base_url=info["base_url"],
            api_key=api_key,
        )


def parse_llm_signal(response: str) -> dict[str, Any]:
    """Parse LLM response JSON into signal dict."""
    # Strip markdown code fences if present
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
        else:
            logger.warning(f"Failed to parse LLM response as JSON: {text[:200]}")
            return {
                "direction": "neutral",
                "confidence": 0.0,
                "reasoning": "Failed to parse LLM response",
                "key_factors": [],
            }

    return {
        "direction": data.get("direction", "neutral"),
        "confidence": float(data.get("confidence", 0.0)),
        "reasoning": data.get("reasoning", ""),
        "time_horizon": data.get("time_horizon", "short"),
        "key_factors": data.get("key_factors", []),
    }
