"""Price ingestion — fetches candles and current prices from Capital.com."""

from __future__ import annotations

import logging
from typing import Any

from backend.data.capitalcom_client import CapitalComClient

logger = logging.getLogger("forex_sentinel.price_ingestor")


def _get_all_instruments(config: dict) -> list[str]:
    """Return the union of instruments from both streams."""
    streams = config.get("streams", {})
    instruments: set[str] = set()
    for stream_key in ("news_stream", "strategy_stream"):
        stream = streams.get(stream_key, {})
        for inst in stream.get("instruments", []):
            instruments.add(inst)
    return sorted(instruments)


def _calc_daily_change_pct(df) -> float | None:
    """Calculate daily change % from H1 candle data.

    Compares latest close to the close 24 bars ago (24 H1 = 1 day).
    Returns None if insufficient data.
    """
    if df is None or len(df) < 25:
        return None
    closes = df["Close"]
    current = closes.iloc[-1]
    day_ago = closes.iloc[-25]
    if day_ago == 0:
        return None
    return round(((current - day_ago) / day_ago) * 100, 4)


def ingest_prices(config: dict, db) -> dict[str, Any]:
    """Fetch H1 candles + current prices for all instruments and store in DB.

    Returns a summary dict with counts.
    """
    instruments = _get_all_instruments(config)
    if not instruments:
        logger.warning("No instruments configured in streams — skipping price ingestion.")
        return {"instruments_fetched": 0, "candles_stored": 0, "snapshots_stored": 0}

    client = CapitalComClient(config)
    logger.info(
        f"Price ingestion starting for {len(instruments)} instruments "
        f"(online={client.is_connected})"
    )

    total_candles = 0
    total_snapshots = 0
    errors: list[str] = []

    for instrument in instruments:
        try:
            # Fetch H1 candles (200 periods)
            df = client.get_candles(instrument, granularity="H1", count=200)
            if df is not None and len(df) > 0:
                inserted = db.insert_candles(instrument, df)
                total_candles += inserted
                logger.info(f"  {instrument}: {inserted} new candles (total {len(df)} fetched)")
            else:
                logger.warning(f"  {instrument}: no candle data returned")

            # Fetch current price
            price = client.get_current_price(instrument)
            daily_change = _calc_daily_change_pct(df)
            db.insert_price_snapshot(
                instrument=instrument,
                bid=price["bid"],
                ask=price["ask"],
                mid=price["mid"],
                daily_change_pct=daily_change,
            )
            total_snapshots += 1
            logger.info(
                f"  {instrument}: price snapshot bid={price['bid']:.5f} "
                f"ask={price['ask']:.5f} daily_change={daily_change}%"
            )

        except Exception as e:
            logger.error(f"  {instrument}: price ingestion failed — {e}")
            errors.append(f"{instrument}: {e}")

    result = {
        "instruments_fetched": len(instruments),
        "candles_stored": total_candles,
        "snapshots_stored": total_snapshots,
        "offline_mode": not client.is_connected,
    }
    if errors:
        result["errors"] = errors

    logger.info(f"Price ingestion complete: {result}")
    return result
