"""Volatility Breakout — Alizadeh, Brandt & Diebold (2002).

Logic: When ATR contracts below a threshold and price breaks out,
enter in the breakout direction."""

from __future__ import annotations

import pandas as pd

from backend.strategies.base import Strategy, TechnicalSignal


class VolatilityBreakoutStrategy(Strategy):
    def __init__(self):
        self._atr_period = 14
        self._atr_contraction_threshold = 0.7
        self._breakout_atr_multiplier = 1.0

    @property
    def name(self) -> str:
        return "volatility_breakout"

    @property
    def description(self) -> str:
        return "Volatility Breakout (Alizadeh 2002) — trades breakouts after ATR contraction"

    def analyze(self, df: pd.DataFrame, instrument: str) -> TechnicalSignal:
        if len(df) < self._atr_period * 3:
            return TechnicalSignal(
                instrument=instrument, direction="neutral",
                confidence=0.0, strategy_name=self.name,
                metadata={"reason": "Insufficient data"},
            )

        # Calculate ATR
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift()).abs(),
            (df["Low"] - df["Close"].shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(self._atr_period).mean()

        current_atr = atr.iloc[-1]
        avg_atr = atr.rolling(self._atr_period * 2).mean().iloc[-1]

        # Check for ATR contraction
        if avg_atr == 0:
            atr_ratio = 1.0
        else:
            atr_ratio = current_atr / avg_atr

        is_contracted = atr_ratio < self._atr_contraction_threshold

        if not is_contracted:
            return TechnicalSignal(
                instrument=instrument, direction="neutral",
                confidence=0.0, strategy_name=self.name,
                entry_price=df["Close"].iloc[-1],
                metadata={
                    "atr": round(current_atr, 5),
                    "avg_atr": round(avg_atr, 5),
                    "atr_ratio": round(atr_ratio, 3),
                    "reason": "No ATR contraction",
                },
            )

        # Look for breakout from recent range
        lookback = self._atr_period
        recent_high = df["High"].tail(lookback).max()
        recent_low = df["Low"].tail(lookback).min()
        current_price = df["Close"].iloc[-1]
        breakout_distance = current_atr * self._breakout_atr_multiplier

        direction = "neutral"
        confidence = 0.0

        if current_price > recent_high - breakout_distance * 0.5:
            direction = "long"
            excess = (current_price - recent_high + breakout_distance * 0.5) / breakout_distance
            confidence = min(excess * 0.8 + (1 - atr_ratio) * 0.4, 1.0)
        elif current_price < recent_low + breakout_distance * 0.5:
            direction = "short"
            excess = (recent_low + breakout_distance * 0.5 - current_price) / breakout_distance
            confidence = min(excess * 0.8 + (1 - atr_ratio) * 0.4, 1.0)

        confidence = round(max(0.0, min(confidence, 1.0)), 3)

        return TechnicalSignal(
            instrument=instrument,
            direction=direction,
            confidence=confidence,
            strategy_name=self.name,
            entry_price=current_price,
            metadata={
                "atr": round(current_atr, 5),
                "avg_atr": round(avg_atr, 5),
                "atr_ratio": round(atr_ratio, 3),
                "recent_high": round(recent_high, 5),
                "recent_low": round(recent_low, 5),
                "contracted": True,
            },
        )

    def get_parameters(self) -> dict:
        return {
            "atr_period": self._atr_period,
            "atr_contraction_threshold": self._atr_contraction_threshold,
            "breakout_atr_multiplier": self._breakout_atr_multiplier,
        }

    def set_parameters(self, params: dict) -> None:
        for key in ("atr_period", "atr_contraction_threshold", "breakout_atr_multiplier"):
            if key in params:
                setattr(self, f"_{key}", params[key])
