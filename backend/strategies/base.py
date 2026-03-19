"""Abstract strategy base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class TechnicalSignal:
    instrument: str
    direction: str  # "long", "short", "neutral"
    confidence: float  # 0.0 - 1.0
    strategy_name: str
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict = field(default_factory=dict)


class Strategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier matching config."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description with paper reference."""

    @abstractmethod
    def analyze(self, df: pd.DataFrame, instrument: str) -> TechnicalSignal:
        """Analyze OHLCV data and return a signal."""

    @abstractmethod
    def get_parameters(self) -> dict:
        """Return current parameters for logging."""

    @abstractmethod
    def set_parameters(self, params: dict) -> None:
        """Update parameters for backtesting optimization."""
