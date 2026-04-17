"""Pydantic data models for all pipeline data contracts."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class _DBSerializable(BaseModel):
    """Base with to_db_dict() that JSON-serializes complex fields for SQLite."""

    model_config = ConfigDict(from_attributes=True)

    def to_db_dict(self) -> dict[str, Any]:
        """Return a dict suitable for SQLite insertion.

        - Serializes list/dict values to JSON strings.
        - Converts bool to int.
        - Converts datetime to ISO8601 string.
        - Drops None values.
        """
        out: dict[str, Any] = {}
        for key, val in self.model_dump().items():
            if val is None:
                continue
            if isinstance(val, (dict, list)):
                out[key] = json.dumps(val)
            elif isinstance(val, bool):
                out[key] = int(val)
            elif isinstance(val, datetime):
                out[key] = val.isoformat()
            else:
                out[key] = val
        return out


# ── Pipeline data models ────────────────────────────────────


class Headline(_DBSerializable):
    id: str = Field(default_factory=_uuid)
    headline: str
    summary: str | None = None
    content: str | None = None
    source: str
    source_url: str | None = None
    image_url: str | None = None
    category: str | None = None
    published_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=_utcnow)
    sentiment_score: float | None = None
    source_metadata: dict[str, Any] | None = None


class RelevanceAssessment(_DBSerializable):
    id: int | None = None
    headline_id: str
    instrument: str
    relevance_reasoning: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    run_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class Signal(_DBSerializable):
    id: str = Field(default_factory=_uuid)
    run_id: str | None = None
    source: str  # 'llm' or 'strategy:<name>'
    instrument: str
    direction: str  # 'long', 'short', 'neutral'
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None
    key_factors: list[str] | None = None
    risk_factors: list[str] | None = None
    headlines_used: list[str] | None = None
    prompt_version: str | None = None
    model: str | None = None
    price_context: dict[str, Any] | None = None
    challenge_output: dict[str, Any] | None = None
    bias_check: dict[str, Any] | None = None
    risk_check: dict[str, Any] | None = None
    was_traded: bool = False
    trade_id: str | None = None
    status: str = "pending"  # 'pending', 'approved', 'rejected'
    rejection_reason: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class Trade(_DBSerializable):
    id: str = Field(default_factory=_uuid)
    broker_deal_id: str | None = None
    instrument: str
    direction: str
    size: float | None = None
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    exit_price: float | None = None
    pnl: float | None = None
    pnl_pips: float | None = None
    status: str = "open"
    source: str | None = None  # 'llm' or 'strategy:<name>'
    signal_id: str | None = None
    opened_at: datetime = Field(default_factory=_utcnow)
    closed_at: datetime | None = None
    close_reason: str | None = None


class TradeRecord(_DBSerializable):
    id: int | None = None
    trade_id: str
    record: dict[str, Any]
    created_at: datetime = Field(default_factory=_utcnow)


class BiasState(_DBSerializable):
    instrument: str
    current_bias: str | None = None  # 'bullish', 'bearish', 'neutral'
    bias_strength: float | None = None
    bias_since: datetime | None = None
    contributing_signals: list[dict[str, Any]] | None = None
    updated_at: datetime = Field(default_factory=_utcnow)


class Prompt(_DBSerializable):
    id: int | None = None
    name: str
    template: str
    version: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class EquitySnapshot(_DBSerializable):
    id: int | None = None
    stream: str
    equity: float
    open_positions: int = 0
    recorded_at: datetime = Field(default_factory=_utcnow)


class Run(_DBSerializable):
    id: str = Field(default_factory=_uuid)
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: datetime | None = None
    market_open: bool = True
    stages_run: list[str] | None = None
    signals_generated: list[str] | None = None
    trades_opened: list[str] | None = None
    status: str = "running"


# ── LLM structured output models ───────────────────────────
# Used to parse/validate JSON responses from LLM calls.


class RelevanceItem(BaseModel):
    headline_id: str = Field(alias="headline_id", default="")
    headline: str = ""
    relevant_instruments: list[str] = []
    relevance_reasoning: str = ""

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("relevance_reasoning", mode="before")
    @classmethod
    def _coerce_reasoning(cls, v):
        """Handle 8B model returning reasoning as a dict per instrument."""
        if isinstance(v, dict):
            return "; ".join(f"{k}: {r}" for k, r in v.items() if r)
        return v

    def __init__(self, **data):
        # Accept 'id' as alias for 'headline_id' from LLM responses
        if "id" in data and "headline_id" not in data:
            data["headline_id"] = data.pop("id")
        super().__init__(**data)


class RelevanceOutput(BaseModel):
    assessments: list[RelevanceItem]


class SignalOutput(BaseModel):
    direction: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_factors: list[str]
    risk_factors: list[str]


class Candle(_DBSerializable):
    id: int | None = None
    instrument: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    fetched_at: datetime = Field(default_factory=_utcnow)


class PriceSnapshot(_DBSerializable):
    id: int | None = None
    instrument: str
    bid: float
    ask: float
    mid: float
    daily_change_pct: float | None = None
    fetched_at: datetime = Field(default_factory=_utcnow)


class ChallengeOutput(BaseModel):
    counter_argument: str
    alternative_interpretation: str
    conviction_after_challenge: float = Field(ge=0.0, le=1.0)
    recommendation: str  # 'proceed', 'reduce_size', 'reject'
