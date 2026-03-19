"""Pydantic data models for the entire system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Signal:
    stream: str
    source: str
    instrument: str
    direction: str  # "long", "short", "neutral"
    confidence: float
    reasoning: str | None = None
    was_traded: bool = False
    trade_id: int | None = None
    rejection_reason: str | None = None
    is_comparison: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    id: int | None = None


@dataclass
class Trade:
    stream: str
    instrument: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    exit_price: float | None = None
    pnl: float | None = None
    pnl_pips: float | None = None
    status: str = "open"
    signal_ids: list[int] = field(default_factory=list)
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    id: int | None = None


@dataclass
class EquitySnapshot:
    stream: str
    equity: float
    open_positions: int
    recorded_at: datetime | None = None
    id: int | None = None


@dataclass
class NewsItem:
    headline: str
    source: str
    url: str | None = None
    summary: str | None = None
    mapped_instruments: list[str] = field(default_factory=list)
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    id: int | None = None


@dataclass
class HybridConfig:
    name: str
    modules: list[dict[str, Any]]
    combiner_mode: str
    instruments: list[str]
    interval: str = "1h"
    description: str | None = None
    is_active: bool = False
    created_at: datetime | None = None
    id: int | None = None
