"""Capture rich context for trade events — snapshots and close context."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.data.provider import pip_value

logger = logging.getLogger("forex_sentinel.sync")


def capture_position_snapshot(trade: dict, broker) -> dict:
    """Record unrealized P&L snapshot for an open trade.

    Returns the snapshot data dict (also suitable for inserting as trade_event).
    """
    try:
        price_data = broker.get_current_price(trade["instrument"])
        current_price = price_data["mid"]
    except Exception as e:
        logger.warning(f"Snapshot: failed to get price for {trade['instrument']}: {e}")
        return {}

    pip_val = pip_value(trade["instrument"])
    entry = trade["entry_price"]

    if trade["direction"] == "long":
        unrealized_pips = (current_price - entry) / pip_val
    else:
        unrealized_pips = (entry - current_price) / pip_val

    unrealized_pl = unrealized_pips * pip_val * trade["size"]

    sl = trade.get("stop_loss", 0)
    tp = trade.get("take_profit", 0)

    if trade["direction"] == "long":
        distance_sl_pips = (current_price - sl) / pip_val if sl else 0
        distance_tp_pips = (tp - current_price) / pip_val if tp else 0
    else:
        distance_sl_pips = (sl - current_price) / pip_val if sl else 0
        distance_tp_pips = (current_price - tp) / pip_val if tp else 0

    return {
        "current_price": round(current_price, 6),
        "unrealized_pl": round(unrealized_pl, 2),
        "unrealized_pips": round(unrealized_pips, 1),
        "distance_sl_pips": round(distance_sl_pips, 1),
        "distance_tp_pips": round(distance_tp_pips, 1),
    }


def capture_close_context(trade: dict, broker, db) -> dict:
    """Gather rich market context when a trade closes.

    Collects: candles, ATR, active signals, recent headlines, MFE/MAE.
    """
    instrument = trade["instrument"]
    context = {
        "detection_time": datetime.now(timezone.utc).isoformat(),
    }

    # Current market price at detection
    try:
        price_data = broker.get_current_price(instrument)
        context["market_price_at_detection"] = {
            "bid": round(price_data["bid"], 6),
            "ask": round(price_data["ask"], 6),
        }
    except Exception as e:
        logger.warning(f"Close context: failed to get price for {instrument}: {e}")

    # Last 10 H1 candles
    try:
        candles_df = broker.get_candles(instrument, granularity="H1", count=14)
        if not candles_df.empty:
            last_10 = candles_df.tail(10)
            context["last_10_candles"] = [
                {
                    "time": str(idx),
                    "o": round(row["Open"], 6),
                    "h": round(row["High"], 6),
                    "l": round(row["Low"], 6),
                    "c": round(row["Close"], 6),
                }
                for idx, row in last_10.iterrows()
            ]

            # ATR(14)
            atr = _compute_atr(candles_df)
            if atr is not None:
                context["atr_14"] = round(atr, 6)
    except Exception as e:
        logger.warning(f"Close context: failed to get candles for {instrument}: {e}")

    # Active signals at close time (last 4 hours for the same instrument)
    try:
        recent_signals = db.get_signals(limit=50)
        active = [
            {
                "stream": s["stream"],
                "instrument": s["instrument"],
                "direction": s["direction"],
                "confidence": s["confidence"],
                "source": s.get("source"),
            }
            for s in recent_signals
            if s["instrument"] == instrument and s["direction"] != "neutral"
        ][:5]
        if active:
            context["active_signals_at_close"] = active
    except Exception as e:
        logger.warning(f"Close context: failed to get signals: {e}")

    # Recent headlines for this instrument
    try:
        recent_news = db.get_recent_news(hours=6)
        relevant = []
        for n in recent_news:
            mapped = n.get("mapped_instruments")
            if isinstance(mapped, str):
                import json
                try:
                    mapped = json.loads(mapped)
                except Exception:
                    mapped = []
            if isinstance(mapped, list) and instrument in mapped:
                relevant.append({
                    "headline": n["headline"],
                    "source": n["source"],
                    "time": n.get("published_at") or n.get("fetched_at"),
                })
        if relevant:
            context["recent_headlines"] = relevant[:5]
    except Exception as e:
        logger.warning(f"Close context: failed to get headlines: {e}")

    # Trade duration
    opened_at = trade.get("opened_at")
    if opened_at:
        try:
            open_dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            duration_hours = (now - open_dt).total_seconds() / 3600
            context["trade_duration_hours"] = round(duration_hours, 1)
        except Exception:
            pass

    # MFE/MAE from position snapshots
    try:
        events = db.get_trade_events(trade["id"])
        snapshots = [e for e in events if e.get("event_type") == "snapshot"]
        if snapshots:
            excursion = _get_max_excursion(snapshots)
            context.update(excursion)
    except Exception as e:
        logger.warning(f"Close context: failed to compute MFE/MAE: {e}")

    return context


def _compute_atr(candles_df, period: int = 14) -> float | None:
    """Calculate ATR from a candle DataFrame."""
    if len(candles_df) < period:
        return None

    high = candles_df["High"].values
    low = candles_df["Low"].values
    close = candles_df["Close"].values

    tr_values = []
    for i in range(1, len(candles_df)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        tr_values.append(tr)

    if len(tr_values) < period:
        return sum(tr_values) / len(tr_values) if tr_values else None

    return sum(tr_values[-period:]) / period


def _get_max_excursion(snapshots: list[dict]) -> dict:
    """Calculate max favorable excursion (MFE) and max adverse excursion (MAE) from snapshots."""
    max_favorable = 0.0
    max_adverse = 0.0

    for snap in snapshots:
        data = snap.get("data", {})
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except Exception:
                continue

        pips = data.get("unrealized_pips", 0)
        if pips > max_favorable:
            max_favorable = pips
        if pips < max_adverse:
            max_adverse = pips

    return {
        "max_favorable_pips": round(max_favorable, 1),
        "max_adverse_pips": round(max_adverse, 1),
    }
