"""DataProvider protocol — interface for broker/data API clients."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataProvider(Protocol):
    """Protocol that all broker/data clients must satisfy.

    Implemented by OandaClient, CapitalComClient, etc.
    """

    @property
    def is_connected(self) -> bool: ...

    def get_account_summary(self) -> dict[str, Any]: ...

    def get_candles(self, instrument: str, granularity: str = "H1",
                    count: int = 200) -> pd.DataFrame: ...

    def get_current_price(self, instrument: str) -> dict[str, float]: ...

    def place_order(self, instrument: str, units: float, side: str,
                    stop_loss: float, take_profit: float) -> dict[str, Any]: ...

    def get_open_trades(self) -> list[dict]: ...

    def close_trade(self, trade_id: str) -> dict: ...

    @staticmethod
    def pip_value(instrument: str) -> float: ...


def pip_value(instrument: str) -> float:
    """Return the pip size for an instrument (provider-agnostic)."""
    if "JPY" in instrument:
        return 0.01
    if instrument.startswith("XAU"):
        return 0.1
    if instrument.startswith("XAG"):
        return 0.01
    if "NATGAS" in instrument:
        return 0.001
    if instrument.startswith(("BCO", "WTICO")):
        return 0.01
    return 0.0001
