"""Stage 2b — LLM signal generation.

For each instrument with relevant headlines, produce a directional
trading signal using the LLM. Stores results in the signals table.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.models import Signal, SignalOutput
from backend.signals.llm_client import UnifiedLLMClient

logger = logging.getLogger("forex_sentinel.signals")


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response, handling code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


def _compute_trend(candles: list[dict]) -> str:
    """Compute simple SMA trend from recent candles.

    Compares 20-period SMA vs 50-period SMA of close prices.
    Returns "bullish", "bearish", or "ranging".
    """
    if len(candles) < 50:
        return "insufficient data"

    closes = [c["close"] for c in candles]
    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes[-50:]) / 50

    if sma50 == 0:
        return "ranging"

    diff_pct = (sma20 - sma50) / sma50 * 100
    if diff_pct > 0.1:
        return "bullish"
    elif diff_pct < -0.1:
        return "bearish"
    return "ranging"


def _format_relevant_news(headlines: list[dict]) -> str:
    """Format relevant headlines into a numbered list for the prompt."""
    items = []
    for i, h in enumerate(headlines[:10], 1):  # Cap at 10 per instrument
        summary = h.get("summary") or "N/A"
        content = h.get("content") or ""
        source = h.get("source", "unknown")
        published = h.get("published_at", "N/A")
        reasoning = h.get("relevance_reasoning") or "N/A"

        entry = (
            f"[{i}] Headline: {h['headline']}\n"
            f"Summary: {summary}\n"
            f"Source: {source} | Published: {published}\n"
            f"Why relevant: {reasoning}"
        )
        if content:
            entry += f"\nContent: {content}"
        items.append(entry)
    return "\n\n".join(items)


def run_signals(db, config) -> dict[str, Any]:
    """Run Stage 2b: LLM signal generation for instruments with relevant news.

    Args:
        db: Database instance
        config: Loaded config (dotdict from settings + streams YAML)

    Returns:
        Summary dict with instruments_processed, signals_stored, model.
    """
    # 1. Load relevant headlines grouped by instrument
    lookback_hours = config.get("streams", {}).get("news_stream", {}).get("news_lookback_hours", 4)
    by_instrument = db.get_relevant_headlines_by_instrument(hours=lookback_hours)

    if not by_instrument:
        logger.info("No instruments with relevant headlines — skipping signal generation")
        return {"instruments_processed": 0, "signals_stored": 0, "model": None}

    logger.info(f"Found relevant headlines for {len(by_instrument)} instruments")

    # 1b. Skip instruments that already have a recent LLM signal
    already_signalled = db.get_recent_llm_signal_instruments(hours=lookback_hours)
    if already_signalled:
        for inst in already_signalled:
            if inst in by_instrument:
                del by_instrument[inst]
                logger.info(f"Skipping {inst} — already has recent LLM signal")

    if not by_instrument:
        logger.info("All instruments already have recent LLM signals — nothing to do")
        return {"instruments_processed": 0, "signals_stored": 0, "skipped_existing": len(already_signalled), "model": None}

    # 2. Load prompt template
    prompt_row = db.get_active_prompt("signal_v1")
    if not prompt_row:
        raise RuntimeError("No active 'signal_v1' prompt found in database")
    template = prompt_row["template"]
    prompt_version = f"{prompt_row['name']}/{prompt_row['version']}"

    # 3. Build LLM clients
    llm_config = config.get("streams", {}).get("news_stream", {}).get("llm", {})
    primary_model = llm_config.get("signal_model", "groq/llama-4-scout")
    primary = UnifiedLLMClient.from_model_key(primary_model)

    fallbacks = []
    for model_key in llm_config.get("comparison_models", []):
        try:
            fallbacks.append(UnifiedLLMClient.from_model_key(model_key))
        except ValueError as e:
            logger.warning(f"Skipping fallback model {model_key}: {e}")

    # 4. Generate signal for each instrument
    signals_stored = 0
    model_used = None

    for instrument, headlines in by_instrument.items():
        try:
            # Get price context
            price_snap = db.get_latest_price(instrument)
            current_price = price_snap["mid"] if price_snap else "N/A"
            daily_change = price_snap["daily_change_pct"] if price_snap else "N/A"

            # Compute trend from candles
            candles = db.get_candles(instrument, limit=200)
            trend = _compute_trend(candles) if candles else "no data"

            # Fill prompt
            news_formatted = _format_relevant_news(headlines)
            filled = (
                template
                .replace("{instrument}", instrument.replace("_", "/"))
                .replace("{relevant_news_with_reasoning}", news_formatted)
                .replace("{current_price}", str(current_price))
                .replace("{daily_change_pct}", str(daily_change))
                .replace("{trend_description}", trend)
            )

            # Call LLM
            logger.info(f"Calling LLM for {instrument} ({len(headlines)} headlines)")
            raw_response, model_used = primary.analyze_json_with_fallback(
                filled, fallbacks, max_tokens=2000,
            )

            # Parse response
            data = _extract_json(raw_response)
            output = SignalOutput.model_validate(data)

            # Build price context dict
            price_context = {
                "current_price": current_price,
                "daily_change_pct": daily_change,
                "trend": trend,
            }

            # Store signal
            headline_ids = [h["headline_id"] for h in headlines]
            signal = Signal(
                source="llm",
                instrument=instrument,
                direction=output.direction,
                confidence=output.confidence,
                reasoning=output.reasoning,
                key_factors=output.key_factors,
                risk_factors=output.risk_factors,
                headlines_used=headline_ids,
                prompt_version=prompt_version,
                model=model_used,
                price_context=price_context,
                status="pending",
            )
            db.insert_signal(signal)
            signals_stored += 1

            logger.info(
                f"{instrument} | {output.direction} | conf={output.confidence:.2f} | "
                f"factors={len(output.key_factors)}"
            )

        except Exception as e:
            logger.error(f"Error generating signal for {instrument}: {e}")
            continue

    logger.info(f"Signal generation complete: {signals_stored} signals stored")
    return {
        "instruments_processed": len(by_instrument),
        "signals_stored": signals_stored,
        "model": model_used,
    }
