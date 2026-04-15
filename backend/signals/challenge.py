"""Stage 2c — Counter-argument challenge.

For each non-neutral LLM signal, run a second LLM call that argues
against the proposed trade and decides whether to proceed, reduce
position size, or reject. Updates the signal record in-place.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.models import ChallengeOutput
from backend.signals.llm_client import UnifiedLLMClient
from backend.signals.signal_generator import _extract_json

logger = logging.getLogger("forex_sentinel.challenge")


def run_challenge(db, config) -> dict[str, Any]:
    """Run Stage 2c: counter-argument challenge on pending LLM signals.

    Args:
        db: Database instance
        config: Loaded config dict

    Returns:
        Summary dict with counts of challenged, proceeded, reduced, rejected.
    """
    # 1. Get pending LLM signals that haven't been challenged yet
    pending = db.get_signals(status="pending", limit=100)
    to_challenge = [
        s for s in pending
        if s.get("source") == "llm"
        and s.get("direction") != "neutral"
        and not s.get("challenge_output")
    ]

    if not to_challenge:
        logger.info("No unchallenged LLM signals — skipping")
        return {"signals_challenged": 0, "proceeded": 0, "reduced": 0, "rejected": 0, "model": None}

    logger.info(f"Found {len(to_challenge)} LLM signals to challenge")

    # 2. Load challenge prompt
    prompt_row = db.get_active_prompt("challenge_v1")
    if not prompt_row:
        raise RuntimeError("No active 'challenge_v1' prompt found in database")
    template = prompt_row["template"]
    prompt_version = f"{prompt_row['name']}/{prompt_row['version']}"

    # 3. Build LLM client (same config path as signal generation)
    llm_config = config.get("streams", {}).get("news_stream", {}).get("llm", {})
    primary_model = llm_config.get("signal_model", "groq/llama-4-scout")
    primary = UnifiedLLMClient.from_model_key(primary_model)

    fallbacks = []
    for model_key in llm_config.get("comparison_models", []):
        try:
            fallbacks.append(UnifiedLLMClient.from_model_key(model_key))
        except ValueError as e:
            logger.warning(f"Skipping fallback model {model_key}: {e}")

    # 4. Challenge each signal
    proceeded = 0
    reduced = 0
    rejected = 0
    model_used = None

    for signal in to_challenge:
        try:
            signal_id = signal["id"]
            instrument = signal["instrument"]

            # Price context stored on the signal itself
            price_ctx = signal.get("price_context")
            if isinstance(price_ctx, str):
                price_ctx = json.loads(price_ctx)
            price_ctx = price_ctx or {}

            # Key/risk factors may be JSON strings from DB
            key_factors = signal.get("key_factors")
            if isinstance(key_factors, str):
                key_factors = json.loads(key_factors)
            key_factors = key_factors or []

            risk_factors = signal.get("risk_factors")
            if isinstance(risk_factors, str):
                risk_factors = json.loads(risk_factors)
            risk_factors = risk_factors or []

            # Fill prompt template
            filled = (
                template
                .replace("{direction}", signal["direction"])
                .replace("{instrument}", instrument.replace("_", "/"))
                .replace("{reasoning}", signal.get("reasoning") or "N/A")
                .replace("{key_factors}", "\n".join(f"- {f}" for f in key_factors))
                .replace("{risk_factors}", "\n".join(f"- {f}" for f in risk_factors))
                .replace("{current_price}", str(price_ctx.get("current_price", "N/A")))
                .replace("{daily_change_pct}", str(price_ctx.get("daily_change_pct", "N/A")))
                .replace("{trend_description}", str(price_ctx.get("trend", "N/A")))
            )

            # Call LLM
            logger.info(f"Challenging {instrument} {signal['direction']} (conf={signal['confidence']:.2f})")
            raw_response, model_used = primary.analyze_json_with_fallback(
                filled, fallbacks, max_tokens=1500,
            )

            # Parse and validate
            data = _extract_json(raw_response)
            output = ChallengeOutput.model_validate(data)

            # Build challenge record for storage
            challenge_data = {
                "counter_argument": output.counter_argument,
                "alternative_interpretation": output.alternative_interpretation,
                "conviction_after_challenge": output.conviction_after_challenge,
                "recommendation": output.recommendation,
                "prompt_version": prompt_version,
                "model": model_used,
                "raw_response": raw_response,
            }

            # Apply recommendation
            update_kwargs: dict[str, Any] = {"challenge_output": challenge_data}

            if output.recommendation == "reject":
                update_kwargs["status"] = "rejected"
                rejected += 1
                logger.info(f"  REJECTED — {output.counter_argument[:80]}...")
            elif output.recommendation == "reduce_size":
                update_kwargs["confidence"] = output.conviction_after_challenge
                reduced += 1
                logger.info(
                    f"  REDUCED — conf {signal['confidence']:.2f} → "
                    f"{output.conviction_after_challenge:.2f}"
                )
            else:
                # "proceed" — keep original confidence
                proceeded += 1
                logger.info(f"  PROCEED — conviction={output.conviction_after_challenge:.2f}")

            db.update_signal(signal_id, **update_kwargs)

        except Exception as e:
            logger.error(f"Error challenging signal {signal.get('id', '?')} ({signal.get('instrument', '?')}): {e}")
            continue

    total = proceeded + reduced + rejected
    logger.info(f"Challenge complete: {total} challenged — {proceeded} proceed, {reduced} reduced, {rejected} rejected")
    return {
        "signals_challenged": total,
        "proceeded": proceeded,
        "reduced": reduced,
        "rejected": rejected,
        "model": model_used,
    }
