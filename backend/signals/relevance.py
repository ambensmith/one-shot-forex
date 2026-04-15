"""Stage 2a — LLM relevance assessment.

Given recent headlines, use an LLM to determine which forex instruments
each headline is relevant to. Stores results in relevance_assessments table.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.models import RelevanceAssessment, RelevanceOutput
from backend.signals.llm_client import UnifiedLLMClient

logger = logging.getLogger("forex_sentinel.relevance")

# Instruments in slash format (as used in prompts) → underscore format (as used in DB)
INSTRUMENT_NORMALIZE = {
    "EUR/USD": "EUR_USD",
    "GBP/USD": "GBP_USD",
    "USD/JPY": "USD_JPY",
    "USD/CHF": "USD_CHF",
    "AUD/USD": "AUD_USD",
    "USD/CAD": "USD_CAD",
    "EUR/GBP": "EUR_GBP",
    "XAU/USD": "XAU_USD",
}

VALID_INSTRUMENTS = set(INSTRUMENT_NORMALIZE.values())


def _normalize_instrument(raw: str) -> str | None:
    """Convert instrument to DB format (EUR_USD). Returns None if invalid."""
    cleaned = raw.strip().upper()
    # Already in underscore format
    if cleaned in VALID_INSTRUMENTS:
        return cleaned
    # Slash format → underscore
    if cleaned in INSTRUMENT_NORMALIZE:
        return INSTRUMENT_NORMALIZE[cleaned]
    return None


def _format_news_items(headlines: list[dict]) -> str:
    """Format headlines into a numbered list for the prompt."""
    items = []
    for i, h in enumerate(headlines, 1):
        summary = (h.get("summary") or "N/A")[:200]
        source = h.get("source", "unknown")
        published = h.get("published_at", "N/A")
        items.append(
            f"[{i}] id={h['id']}\n"
            f"Headline: {h['headline']}\n"
            f"Summary: {summary}\n"
            f"Source: {source}\n"
            f"Published: {published}"
        )
    return "\n\n".join(items)


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


def run_relevance(db, config) -> dict[str, Any]:
    """Run Stage 2a: LLM relevance assessment on recent headlines.

    Args:
        db: Database instance
        config: Loaded config (dotdict from settings + streams YAML)

    Returns:
        Summary dict with headlines_processed, assessments_stored, model.
    """
    # 1. Load recent headlines
    lookback_hours = config.get("streams", {}).get("news_stream", {}).get("news_lookback_hours", 4)
    headlines = db.get_recent_headlines(hours=lookback_hours)

    if not headlines:
        logger.info("No recent headlines found — skipping relevance assessment")
        return {"headlines_processed": 0, "assessments_stored": 0, "model": None}

    logger.info(f"Loaded {len(headlines)} headlines from last {lookback_hours}h")

    # 2. Load prompt template
    prompt_row = db.get_active_prompt("relevance_v1")
    if not prompt_row:
        raise RuntimeError("No active 'relevance_v1' prompt found in database")
    template = prompt_row["template"]
    prompt_version = f"{prompt_row['name']}/{prompt_row['version']}"

    # 3. Build LLM clients
    llm_config = config.get("streams", {}).get("news_stream", {}).get("llm", {})
    primary_model = llm_config.get("primary_model", "groq/llama-3.3-70b")
    primary = UnifiedLLMClient.from_model_key(primary_model)

    fallbacks = []
    for model_key in llm_config.get("comparison_models", []):
        try:
            fallbacks.append(UnifiedLLMClient.from_model_key(model_key))
        except ValueError as e:
            logger.warning(f"Skipping fallback model {model_key}: {e}")

    # 4. Process headlines in batches to stay within LLM token limits
    BATCH_SIZE = 15
    headline_ids = {h["id"] for h in headlines}
    stored = 0
    model_used = None

    for batch_start in range(0, len(headlines), BATCH_SIZE):
        batch = headlines[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(headlines) + BATCH_SIZE - 1) // BATCH_SIZE

        news_formatted = _format_news_items(batch)
        filled_prompt = template.replace("{news_items_formatted}", news_formatted)

        logger.info(f"Calling LLM ({primary_model}) — batch {batch_num}/{total_batches} ({len(batch)} headlines)")
        try:
            raw_response, model_used = primary.analyze_json_with_fallback(
                filled_prompt, fallbacks, max_tokens=2000,
            )
        except Exception as e:
            logger.error(f"LLM call failed for batch {batch_num}: {e}")
            continue

        # Parse response
        try:
            data = _extract_json(raw_response)
            output = RelevanceOutput.model_validate(data)
            logger.info(f"Batch {batch_num}: parsed {len(output.assessments)} relevance items")
        except Exception as e:
            logger.error(f"Failed to parse LLM response for batch {batch_num}: {e}")
            continue

        # Store assessments
        for item in output.assessments:
            if item.headline_id not in headline_ids:
                logger.warning(f"LLM returned unknown headline_id: {item.headline_id}")
                continue

            if not item.relevant_instruments:
                continue

            for raw_instrument in item.relevant_instruments:
                instrument = _normalize_instrument(raw_instrument)
                if not instrument:
                    logger.warning(f"LLM returned invalid instrument: {raw_instrument}")
                    continue

                assessment = RelevanceAssessment(
                    headline_id=item.headline_id,
                    instrument=instrument,
                    relevance_reasoning=item.relevance_reasoning,
                    prompt_version=prompt_version,
                    model=model_used,
                )
                db.insert_relevance(assessment)
                stored += 1

    logger.info(f"Stored {stored} relevance assessments across {total_batches} batches")
    return {
        "headlines_processed": len(headlines),
        "assessments_stored": stored,
        "model": model_used,
    }
