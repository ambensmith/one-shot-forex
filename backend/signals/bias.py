"""Stage 3 — Directional bias tracker.

Maintains a rolling directional bias per instrument using signals from
both the LLM and strategy streams.  Prevents whipsaw trading by
enforcing three rules before a signal can proceed to the risk manager:

1. No conflicting open positions (opposite direction)
2. Signal must align with current bias direction
3. Cooldown period after a bias flip
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from backend.core.models import BiasState

logger = logging.getLogger("forex_sentinel.bias")

# Direction mapping: signal direction <-> bias direction
_DIRECTION_TO_BIAS = {"long": "bullish", "short": "bearish"}
_BIAS_TO_DIRECTION = {"bullish": "long", "bearish": "short"}


def run_bias(db, config: dict) -> dict[str, Any]:
    """Run Stage 3: directional bias tracker on pending signals.

    Args:
        db: Database instance
        config: Loaded config dict

    Returns:
        Summary dict with approval/rejection counts.
    """
    bias_cfg = config.get("bias", {})
    decay_hours = bias_cfg.get("decay_hours", 12)
    cooldown_hours = bias_cfg.get("cooldown_hours", 2)

    now = datetime.now(timezone.utc)
    decay_cutoff = now - timedelta(hours=decay_hours)
    cooldown_cutoff = now - timedelta(hours=cooldown_hours)

    # 1. Gather pending signals without a bias check
    pending = db.get_signals(status="pending", limit=200)
    to_check = [
        s for s in pending
        if not s.get("bias_check")
    ]

    if not to_check:
        logger.info("No unchecked pending signals — skipping bias tracker")
        return {
            "signals_checked": 0, "approved": 0,
            "rejected_conflict": 0, "rejected_alignment": 0,
            "rejected_cooldown": 0,
        }

    logger.info(f"Found {len(to_check)} signals to check against bias")

    # 2. Group by instrument
    by_instrument: dict[str, list[dict]] = {}
    for s in to_check:
        by_instrument.setdefault(s["instrument"], []).append(s)

    approved = 0
    rejected_conflict = 0
    rejected_alignment = 0
    rejected_cooldown = 0

    for instrument, signals in by_instrument.items():
        # 3. Load or create bias state
        bias_rows = db.get_bias_state(instrument)
        if bias_rows:
            row = bias_rows[0]
            contrib = row.get("contributing_signals")
            if isinstance(contrib, str):
                contrib = json.loads(contrib)
            existing_signals = contrib or []
            old_bias = row.get("current_bias")
            bias_since_raw = row.get("bias_since")
            if isinstance(bias_since_raw, str) and bias_since_raw:
                bias_since = datetime.fromisoformat(bias_since_raw)
                if bias_since.tzinfo is None:
                    bias_since = bias_since.replace(tzinfo=timezone.utc)
            else:
                bias_since = None
        else:
            existing_signals = []
            old_bias = None
            bias_since = None

        # Add new signals to contributing list
        for s in signals:
            existing_signals.append({
                "tick": s["created_at"] if isinstance(s["created_at"], str) else s["created_at"].isoformat(),
                "source": s["source"],
                "direction": s["direction"],
                "confidence": s["confidence"],
            })

        # Decay old signals
        filtered = []
        for cs in existing_signals:
            tick_str = cs.get("tick", "")
            try:
                tick_dt = datetime.fromisoformat(tick_str)
                if tick_dt.tzinfo is None:
                    tick_dt = tick_dt.replace(tzinfo=timezone.utc)
                if tick_dt >= decay_cutoff:
                    filtered.append(cs)
            except (ValueError, TypeError):
                # Keep signals with unparseable timestamps (shouldn't happen)
                filtered.append(cs)
        existing_signals = filtered

        # Calculate bias direction and strength
        new_bias, strength = _calculate_bias(existing_signals, now, decay_hours)

        # Detect bias flip vs initial establishment
        if old_bias is not None and new_bias != old_bias and new_bias != "neutral":
            # Actual flip — set bias_since to now, cooldown will apply
            bias_since = now
            logger.info(f"{instrument}: bias flipped {old_bias} → {new_bias}")
        elif bias_since is None and new_bias != "neutral":
            # First time establishing bias — backdate so cooldown doesn't trigger
            bias_since = now - timedelta(hours=cooldown_hours + 1)

        # Persist updated bias state
        state = BiasState(
            instrument=instrument,
            current_bias=new_bias,
            bias_strength=strength,
            bias_since=bias_since,
            contributing_signals=existing_signals,
        )
        db.upsert_bias_state(state)

        logger.info(
            f"{instrument}: bias={new_bias} strength={strength:.2f} "
            f"contributing={len(existing_signals)}"
        )

        # 4. Check each signal against bias
        open_trades = db.get_open_trades(instrument)

        for s in signals:
            signal_id = s["id"]
            direction = s["direction"]

            # Neutral signals get auto-approved
            if direction == "neutral":
                bias_check = _make_bias_check(
                    direction, new_bias, strength,
                    aligned=True, conflicting=False, cooldown=False, approved=True,
                )
                db.update_signal(signal_id, bias_check=bias_check)
                approved += 1
                continue

            # Check 1: conflicting open positions
            has_conflict = _has_conflicting_position(open_trades, direction)

            # Check 2: bias alignment
            expected_bias = _DIRECTION_TO_BIAS.get(direction)
            is_aligned = (new_bias == expected_bias)

            # Check 3: cooldown after bias flip
            in_cooldown = False
            if is_aligned and bias_since is not None:
                # Only applies if bias recently flipped to THIS direction
                if bias_since > cooldown_cutoff:
                    in_cooldown = True

            is_approved = (not has_conflict) and is_aligned and (not in_cooldown)

            bias_check = _make_bias_check(
                direction, new_bias, strength,
                aligned=is_aligned, conflicting=has_conflict,
                cooldown=in_cooldown, approved=is_approved,
            )

            update_kwargs: dict[str, Any] = {"bias_check": bias_check}
            if not is_approved:
                update_kwargs["status"] = "rejected"

            db.update_signal(signal_id, **update_kwargs)

            if is_approved:
                approved += 1
                logger.info(f"  {instrument} {direction} — APPROVED")
            else:
                reasons = []
                if has_conflict:
                    reasons.append("conflicting_position")
                    rejected_conflict += 1
                elif not is_aligned:
                    reasons.append("bias_misaligned")
                    rejected_alignment += 1
                elif in_cooldown:
                    reasons.append("cooldown")
                    rejected_cooldown += 1
                logger.info(f"  {instrument} {direction} — REJECTED ({', '.join(reasons)})")

    total = approved + rejected_conflict + rejected_alignment + rejected_cooldown
    logger.info(
        f"Bias check complete: {total} checked — {approved} approved, "
        f"{rejected_conflict} conflict, {rejected_alignment} misaligned, "
        f"{rejected_cooldown} cooldown"
    )
    return {
        "signals_checked": total,
        "approved": approved,
        "rejected_conflict": rejected_conflict,
        "rejected_alignment": rejected_alignment,
        "rejected_cooldown": rejected_cooldown,
    }


def _calculate_bias(
    signals: list[dict], now: datetime, decay_hours: int
) -> tuple[str, float]:
    """Calculate bias direction and strength from contributing signals.

    Uses confidence-weighted voting with a linear recency decay:
    most recent signal gets weight 1.0, signal at the decay boundary
    gets weight 0.5.

    Returns:
        (direction, strength) where direction is 'bullish'/'bearish'/'neutral'
        and strength is 0.0-1.0.
    """
    if not signals:
        return "neutral", 0.0

    bullish_weight = 0.0
    bearish_weight = 0.0
    decay_seconds = decay_hours * 3600

    for s in signals:
        direction = s.get("direction", "neutral")
        confidence = s.get("confidence", 0.5)

        # Calculate recency weight (1.0 for now, 0.5 at decay boundary)
        try:
            tick_dt = datetime.fromisoformat(s.get("tick", ""))
            if tick_dt.tzinfo is None:
                tick_dt = tick_dt.replace(tzinfo=timezone.utc)
            age_seconds = (now - tick_dt).total_seconds()
            recency = max(0.5, 1.0 - 0.5 * (age_seconds / decay_seconds))
        except (ValueError, TypeError):
            recency = 0.5

        weight = confidence * recency

        if direction == "long":
            bullish_weight += weight
        elif direction == "short":
            bearish_weight += weight

    total = bullish_weight + bearish_weight
    if total == 0:
        return "neutral", 0.0

    # Direction: whichever side has more weight
    if bullish_weight > bearish_weight:
        bias = "bullish"
        strength = bullish_weight / total
    elif bearish_weight > bullish_weight:
        bias = "bearish"
        strength = bearish_weight / total
    else:
        bias = "neutral"
        strength = 0.5

    return bias, round(strength, 4)


def _has_conflicting_position(open_trades: list[dict], signal_direction: str) -> bool:
    """Check if any open trade conflicts with the signal direction."""
    for trade in open_trades:
        if trade["direction"] != signal_direction:
            return True
    return False


def _make_bias_check(
    signal_direction: str,
    bias_direction: str | None,
    bias_strength: float,
    *,
    aligned: bool,
    conflicting: bool,
    cooldown: bool,
    approved: bool,
) -> dict[str, Any]:
    """Build the bias_check dict stored on the signal."""
    return {
        "signal_direction": signal_direction,
        "bias_direction": bias_direction,
        "bias_strength": bias_strength,
        "bias_aligned": aligned,
        "has_conflicting_position": conflicting,
        "in_cooldown": cooldown,
        "approved_by_bias": approved,
    }
