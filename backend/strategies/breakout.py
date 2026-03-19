"""London/NY Session Breakout — Breedon & Ranaldo (2012).

Logic: Measure price range during Asian session (22:00-06:00 UTC).
Trade breakout when London opens."""

from __future__ import annotations

import pandas as pd

from backend.strategies.base import Strategy, TechnicalSignal


class BreakoutStrategy(Strategy):
    def __init__(self):
        self._asian_start = 22  # UTC hour
        self._asian_end = 6     # UTC hour
        self._breakout_buffer_pips = 10

    @property
    def name(self) -> str:
        return "breakout"

    @property
    def description(self) -> str:
        return "London/NY Session Breakout (Breedon 2012) — trades breakouts from Asian range"

    def analyze(self, df: pd.DataFrame, instrument: str) -> TechnicalSignal:
        if len(df) < 24:
            return TechnicalSignal(
                instrument=instrument, direction="neutral",
                confidence=0.0, strategy_name=self.name,
                metadata={"reason": "Insufficient data"},
            )

        from backend.data.provider import pip_value
        pip_val = pip_value(instrument)
        buffer = self._breakout_buffer_pips * pip_val

        # Get Asian session range from recent data
        # Look at last 24 hours to find Asian session candles
        recent = df.tail(48)  # Last 48 hours for safety
        asian_mask = self._get_asian_mask(recent)

        if asian_mask.sum() < 3:
            # Not enough Asian session data, use last 8 candles as proxy
            asian_data = df.tail(8)
        else:
            asian_data = recent[asian_mask]

        asian_high = asian_data["High"].max()
        asian_low = asian_data["Low"].min()
        asian_range = asian_high - asian_low

        current_price = df["Close"].iloc[-1]

        # Check for breakout
        if current_price > asian_high + buffer:
            direction = "long"
            distance_from_range = current_price - asian_high
            confidence = min(distance_from_range / (asian_range + 1e-10), 1.0)
        elif current_price < asian_low - buffer:
            direction = "short"
            distance_from_range = asian_low - current_price
            confidence = min(distance_from_range / (asian_range + 1e-10), 1.0)
        else:
            direction = "neutral"
            confidence = 0.0

        confidence = round(max(0.0, min(confidence, 1.0)), 3)

        return TechnicalSignal(
            instrument=instrument,
            direction=direction,
            confidence=confidence,
            strategy_name=self.name,
            entry_price=current_price,
            metadata={
                "asian_high": round(asian_high, 5),
                "asian_low": round(asian_low, 5),
                "asian_range": round(asian_range, 5),
                "buffer": round(buffer, 5),
            },
        )

    def _get_asian_mask(self, df: pd.DataFrame) -> pd.Series:
        """Get boolean mask for Asian session hours."""
        if not hasattr(df.index, 'hour'):
            return pd.Series(False, index=df.index)
        hours = df.index.hour
        if self._asian_start > self._asian_end:
            # Wraps midnight (e.g., 22:00-06:00)
            return (hours >= self._asian_start) | (hours < self._asian_end)
        else:
            return (hours >= self._asian_start) & (hours < self._asian_end)

    def get_parameters(self) -> dict:
        return {
            "asian_start": f"{self._asian_start}:00",
            "asian_end": f"{self._asian_end}:00",
            "breakout_buffer_pips": self._breakout_buffer_pips,
        }

    def set_parameters(self, params: dict) -> None:
        if "asian_start" in params:
            val = params["asian_start"]
            self._asian_start = int(val.split(":")[0]) if isinstance(val, str) else int(val)
        if "asian_end" in params:
            val = params["asian_end"]
            self._asian_end = int(val.split(":")[0]) if isinstance(val, str) else int(val)
        if "breakout_buffer_pips" in params:
            self._breakout_buffer_pips = params["breakout_buffer_pips"]
