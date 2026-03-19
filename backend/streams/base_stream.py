"""Abstract base class for all trading streams."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("forex_sentinel.stream")


@dataclass
class StreamSignal:
    stream_id: str
    instrument: str
    direction: str  # "long", "short", "neutral"
    confidence: float
    sources: list[str] = field(default_factory=list)
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamState:
    stream_id: str
    name: str
    status: str  # "running", "paused", "error"
    open_positions: list[dict] = field(default_factory=list)
    total_pnl: float = 0.0
    trade_count: int = 0
    last_tick: datetime | None = None


class BaseStream(ABC):
    """All three stream types inherit from this.
    Each stream has its own capital allocation, trades, and P&L."""

    def __init__(self, stream_id: str, config: dict, db, oanda, risk, executor):
        self.stream_id = stream_id
        self.config = config
        self.db = db
        self.oanda = oanda
        self.risk = risk
        self.executor = executor
        self.logger = logging.getLogger(f"forex_sentinel.stream.{stream_id}")

    @abstractmethod
    async def tick(self) -> list[StreamSignal]:
        """Run one cycle."""

    def get_state(self) -> StreamState:
        open_trades = self.db.get_open_trades(self.stream_id)
        all_trades = self.db.get_trades(self.stream_id)
        total_pnl = sum(t.get("pnl", 0) or 0 for t in all_trades)
        return StreamState(
            stream_id=self.stream_id,
            name=self.stream_id,
            status="running",
            open_positions=open_trades,
            total_pnl=total_pnl,
            trade_count=len(all_trades),
        )

    def record_signal(self, signal: StreamSignal, source: str,
                      is_comparison: bool = False) -> int:
        return self.db.insert_signal(
            stream=self.stream_id,
            source=source,
            instrument=signal.instrument,
            direction=signal.direction,
            confidence=signal.confidence,
            reasoning=signal.reasoning,
            is_comparison=1 if is_comparison else 0,
            metadata=signal.metadata,
        )

    def record_equity(self):
        equity = self.db.get_stream_equity(self.stream_id)
        open_count = self.db.count_open_positions(self.stream_id)
        self.db.insert_equity_snapshot(self.stream_id, equity, open_count)
