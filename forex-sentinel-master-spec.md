# Forex Sentinel — Master Specification

## Overview

Forex Sentinel is a modular, automated forex and commodities trading system with three independent signal streams, a custom hybrid builder, a performance dashboard, model comparison testing, and a Cowork review system.

It runs for free on GitHub Actions (hourly schedule), with a static React dashboard on Vercel. State is stored in SQLite committed to the repository. All LLM providers are free tier. Broker is OANDA (free demo account, zero platform fees on live).

The architecture is designed to extend without code changes: new models, instruments, and strategies are added through configuration and plugin files.

-----

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  GITHUB REPOSITORY (public)                                      │
│                                                                  │
│  ┌────────────────────────────────────────────────┐             │
│  │  GitHub Actions — Cron: every hour, Mon-Fri     │             │
│  │                                                  │             │
│  │  1. Checkout repo                                │             │
│  │  2. python -m backend.main --mode tick           │             │
│  │     ├─ Fetch news from RSS / GDELT / calendar    │             │
│  │     ├─ Map headlines → instruments               │             │
│  │     ├─ Run LLM analysis (primary model)          │             │
│  │     ├─ Run comparison models (if enabled)        │             │
│  │     ├─ Run peer-reviewed strategies              │             │
│  │     ├─ Run active hybrid streams                 │             │
│  │     ├─ Risk check all proposed trades            │             │
│  │     ├─ Execute approved trades via OANDA API     │             │
│  │     ├─ Log signals, trades, equity to SQLite     │             │
│  │     └─ Export dashboard JSON files               │             │
│  │  3. Generate Cowork review (if scheduled)        │             │
│  │  4. Commit updated data/ logs/ reviews/          │             │
│  │  5. Push to main                                 │             │
│  └────────────────────────────────────────────────┘             │
│                                                                  │
│  data/sentinel.db            ← SQLite (source of truth)         │
│  data/dashboard/*.json       ← Static JSON for frontend         │
│  logs/app.log                ← Application log                  │
│  reviews/                    ← Cowork review packets            │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │  Push triggers Vercel rebuild
                       ▼
              ┌──────────────────┐
              │  Vercel (free)   │
              │  Static React    │
              │  Dashboard       │
              │  Reads *.json    │
              └──────────────────┘
```

### Market Hours

Forex operates 24 hours Monday through Friday. The market opens Sunday ~22:00 UTC (Sydney session) and closes Friday ~22:00 UTC (New York close). There is no central exchange — trading follows the sun:

|Session |Hours (UTC)  |Key Pairs    |
|--------|-------------|-------------|
|Sydney  |22:00 - 07:00|AUD, NZD     |
|Tokyo   |00:00 - 09:00|JPY, AUD     |
|London  |07:00 - 16:00|EUR, GBP, CHF|
|New York|12:00 - 22:00|USD, CAD     |

London + New York overlap (12:00-16:00 UTC) is the highest-volume window. The system runs hourly and naturally captures all sessions.

Gold and oil CFDs trade during the same forex hours via OANDA, with a brief daily pause around 21:00-22:00 UTC.

-----

## Three Streams + Custom Hybrid

The system runs three independent trading pipelines. Each has its own simulated capital allocation, its own trades, and its own performance tracking. They never interfere with each other.

### Stream 1: News Stream

Ingests headlines from free news sources. LLM analyzes relevance and directional impact per instrument. Trades purely on news-derived signals. This is where geopolitical insight is expressed.

### Stream 2: Strategy Stream

Runs peer-reviewed, purely mechanical strategies. No news, no LLM — just price data and math. Each strategy operates independently within this stream and can be enabled/disabled individually.

### Stream 3: Custom Hybrid

User-defined recipes that combine news signals with any selection of strategies. Configurable combiner logic determines how modules interact. Multiple hybrids can run simultaneously.

### Dashboard

Compares performance of all streams and sub-strategies side by side. Time period controls, equity curves, metric tables, trade history, instrument breakdown, and model comparison.

-----

## Tech Stack

### Backend (Python 3.12+)

```
pandas           — Data manipulation and indicator calculation
backtesting.py   — Strategy backtesting engine
oandapyV20       — OANDA v20 REST API client
openai           — Unified LLM client (OpenAI-compatible API)
aiohttp          — Async HTTP for news fetching
feedparser       — RSS parsing
pydantic         — Config validation and data models
APScheduler      — Local scheduling (for future Mac/server hosting)
```

### Frontend (React on Vercel)

```
React 18         — UI framework
React Router     — Multi-screen navigation
Recharts         — Performance charts and equity curves
Tailwind CSS     — Styling
Lucide Icons     — Icon set
```

### Data

```
SQLite           — All state: trades, signals, equity, configs
Static JSON      — Dashboard data exported each cycle
Parquet          — Cached historical data for backtesting
```

-----

## Directory Structure

```
forex-sentinel/
├── CLAUDE.md                          # Claude Code project instructions
├── pyproject.toml                     # Python project config
├── requirements.txt                   # Pip dependencies
├── .github/
│   └── workflows/
│       └── trade.yml                  # GitHub Actions workflow
│
├── config/
│   ├── settings.yaml                  # Master config
│   ├── instruments.yaml               # Instruments + news keyword mapping
│   ├── streams.yaml                   # Stream-specific configs
│   └── prompts/
│       └── forex_signal.txt           # LLM prompt template (editable)
│
├── backend/
│   ├── __init__.py
│   ├── main.py                        # CLI entry point
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic config loader
│   │   ├── database.py                # SQLite connection + queries
│   │   └── models.py                  # All data models
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── oanda_client.py            # OANDA v20: candles, orders, account
│   │   └── news_ingestor.py           # RSS + GDELT + calendar fetching
│   │
│   ├── streams/
│   │   ├── __init__.py
│   │   ├── base_stream.py             # Abstract base for all streams
│   │   ├── news_stream.py             # Stream 1: News → LLM → trades
│   │   ├── strategy_stream.py         # Stream 2: Strategies → trades
│   │   └── hybrid_stream.py           # Stream 3: Custom combinations
│   │
│   ├── signals/
│   │   ├── __init__.py
│   │   ├── llm_client.py              # Unified OpenAI-compatible LLM client
│   │   ├── model_registry.py          # All available models + metadata
│   │   ├── instrument_mapper.py       # Headlines → instrument mapping
│   │   └── prompts/
│   │       └── forex_signal.txt       # Prompt template
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py                    # Abstract strategy base class
│   │   ├── registry.py                # Auto-discovers strategy files
│   │   ├── momentum.py                # Time Series Momentum (Moskowitz 2012)
│   │   ├── carry.py                   # Carry Trade (Menkhoff 2012)
│   │   ├── breakout.py                # London/NY Session Breakout (Breedon 2012)
│   │   ├── mean_reversion.py          # Bollinger Mean Reversion (Pojarliev 2008)
│   │   ├── volatility_breakout.py     # ATR Breakout (Alizadeh 2002)
│   │   └── README.md                  # How to add a new strategy
│   │
│   ├── risk/
│   │   ├── __init__.py
│   │   └── risk_manager.py            # Per-stream + global risk checks
│   │
│   ├── execution/
│   │   ├── __init__.py
│   │   └── executor.py                # OANDA order placement + management
│   │
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py                  # Backtesting harness
│   │   ├── data_loader.py             # Historical OANDA data → parquet cache
│   │   └── runner.py                  # CLI backtest execution
│   │
│   ├── reviews/
│   │   ├── __init__.py
│   │   ├── generator.py               # Review packet builder
│   │   ├── metrics.py                 # Performance metric computation
│   │   ├── narratives.py              # REVIEW.md prose generation
│   │   └── exporter.py                # Write files to reviews/
│   │
│   └── dashboard/
│       ├── __init__.py
│       └── json_exporter.py           # Export SQLite → static JSON for frontend
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── public/
│   │   └── data/                      # Static JSON (gitignored locally, committed by Actions)
│   │       ├── dashboard.json
│   │       ├── trades.json
│   │       ├── equity.json
│   │       ├── signals.json
│   │       └── models.json
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                    # Router + layout
│   │   ├── components/
│   │   │   ├── Layout.jsx             # Sidebar nav + screen container
│   │   │   ├── StreamCard.jsx         # Signal/trade card
│   │   │   ├── TradeRow.jsx           # Trade history row
│   │   │   ├── SignalBadge.jsx        # Long/Short/Neutral indicator
│   │   │   ├── MetricTile.jsx         # Single metric display
│   │   │   ├── EquityCurve.jsx        # Recharts line chart
│   │   │   ├── InstrumentTag.jsx      # Currency pair pill
│   │   │   ├── ConfidenceMeter.jsx    # Visual confidence bar
│   │   │   └── ModelToggle.jsx        # On/off switch for models
│   │   ├── screens/
│   │   │   ├── NewsStream.jsx         # Screen 1
│   │   │   ├── StrategyStream.jsx     # Screen 2
│   │   │   ├── HybridBuilder.jsx      # Screen 3
│   │   │   ├── Dashboard.jsx          # Screen 4
│   │   │   └── ModelComparison.jsx    # Screen 5 (or tab within Dashboard)
│   │   ├── hooks/
│   │   │   ├── useStreamData.js       # Load stream JSON
│   │   │   ├── useMetrics.js          # Compute derived metrics
│   │   │   └── useConfig.js           # Load/display config
│   │   └── lib/
│   │       ├── api.js                 # Read from /data/*.json
│   │       └── constants.js           # Labels, colors, instrument metadata
│   └── tailwind.config.js
│
├── data/
│   ├── sentinel.db                    # SQLite database
│   └── cache/                         # Parquet files for backtest data
│
├── reviews/
│   ├── SYSTEM_CONTEXT.md              # Static system description for Cowork
│   ├── latest/                        # Symlink → most recent snapshot
│   │   ├── REVIEW.md
│   │   ├── trades.csv
│   │   ├── signals.csv
│   │   ├── equity_curves.csv
│   │   └── open_positions.csv
│   └── archive/                       # Timestamped snapshots
│       └── YYYY-MM-DD_HH-MM/
│
├── tests/
│   ├── test_news_stream.py
│   ├── test_strategy_stream.py
│   ├── test_hybrid_stream.py
│   ├── test_strategies.py
│   ├── test_risk.py
│   ├── test_llm_client.py
│   └── test_json_export.py
│
└── logs/
    └── app.log
```

-----

## GitHub Actions Workflow

```yaml
# .github/workflows/trade.yml

name: Trading Cycle
on:
  schedule:
    # Every hour, every day (backend skips weekends in code)
    - cron: '0 * * * *'
  workflow_dispatch:
    # Manual trigger from GitHub UI with optional parameters
    inputs:
      mode:
        description: 'Run mode'
        required: false
        default: 'tick'
        type: choice
        options:
          - tick
          - review
          - backtest

jobs:
  trade:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run trading cycle
        env:
          OANDA_API_KEY: ${{ secrets.OANDA_API_KEY }}
          OANDA_ACCOUNT_ID: ${{ secrets.OANDA_ACCOUNT_ID }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          MISTRAL_API_KEY: ${{ secrets.MISTRAL_API_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: python -m backend.main --mode ${{ github.event.inputs.mode || 'tick' }}

      - name: Export dashboard JSON
        run: python -m backend.dashboard.json_exporter

      - name: Commit results
        run: |
          git config user.name "forex-sentinel-bot"
          git config user.email "bot@forex-sentinel"
          git add data/ logs/ reviews/ frontend/public/data/
          git diff --staged --quiet || git commit -m "cycle $(date -u +%Y-%m-%dT%H:%M)"
          git push
```

-----

## Backend Entry Point

```python
# backend/main.py

import argparse
import asyncio
from datetime import datetime, timezone

async def run_tick():
    """Execute one trading cycle across all active streams."""
    config = load_config()
    db = Database("data/sentinel.db")
    oanda = OandaClient(config)
    risk = RiskManager(config, oanda, db)
    executor = Executor(config, oanda, db)

    # Check if forex market is open
    if not is_market_open():
        print("Market closed. Skipping cycle.")
        return

    # Run News Stream
    if config.streams.news.enabled:
        news_stream = NewsStream(
            config=config, db=db, oanda=oanda,
            risk=risk, executor=executor
        )
        await news_stream.tick()

    # Run Strategy Stream
    if config.streams.strategy.enabled:
        strategy_stream = StrategyStream(
            config=config, db=db, oanda=oanda,
            risk=risk, executor=executor
        )
        await strategy_stream.tick()

    # Run all active Hybrid Streams
    for hybrid_config in db.get_active_hybrids():
        hybrid = HybridStream(
            hybrid_config=hybrid_config,
            config=config, db=db, oanda=oanda,
            risk=risk, executor=executor
        )
        await hybrid.tick()

    # Record equity snapshots for all streams
    record_all_equity_snapshots(db, oanda)

    # Generate review if due
    if should_generate_review(config):
        from backend.reviews.generator import ReviewGenerator
        ReviewGenerator(db, config).generate(
            trigger="scheduled"
        )

def is_market_open() -> bool:
    """Returns True if forex market is currently open.
    Open: Sunday 22:00 UTC through Friday 22:00 UTC."""
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # 0=Mon, 6=Sun
    hour = now.hour

    if weekday == 5:  # Saturday
        return False
    if weekday == 6 and hour < 22:  # Sunday before 22:00
        return False
    if weekday == 4 and hour >= 22:  # Friday after 22:00
        return False
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forex Sentinel")
    parser.add_argument(
        "--mode",
        choices=["tick", "backtest", "review"],
        default="tick",
        help="tick: run one trading cycle. backtest: run backtests. review: generate Cowork review."
    )
    parser.add_argument("--strategy", help="Strategy name for backtest mode")
    parser.add_argument("--instrument", help="Instrument for backtest mode")
    parser.add_argument("--period", help="Period for review, e.g. '7d' or '30d'")
    args = parser.parse_args()

    if args.mode == "tick":
        asyncio.run(run_tick())
    elif args.mode == "backtest":
        from backend.backtest.runner import run_backtest
        run_backtest(args.strategy, args.instrument)
    elif args.mode == "review":
        from backend.reviews.generator import ReviewGenerator
        ReviewGenerator.from_cli(args.period)
```

-----

## Database Schema

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT NOT NULL,              -- 'news', 'strategy', 'hybrid:{name}'
    source TEXT NOT NULL,              -- 'groq/llama-3.3-70b', 'momentum', etc.
    instrument TEXT NOT NULL,          -- 'EUR_USD', 'XAU_USD', etc.
    direction TEXT NOT NULL,           -- 'long', 'short', 'neutral'
    confidence REAL NOT NULL,          -- 0.0 - 1.0
    reasoning TEXT,
    was_traded INTEGER DEFAULT 0,      -- 0 or 1
    trade_id INTEGER,                  -- FK to trades.id if traded
    rejection_reason TEXT,             -- Why not traded (if applicable)
    is_comparison INTEGER DEFAULT 0,   -- 1 if from comparison model (not traded)
    metadata JSON,                     -- Headlines, indicators, model-specific data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT NOT NULL,
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    position_size REAL NOT NULL,
    pnl REAL,                          -- NULL while open
    pnl_pips REAL,
    status TEXT DEFAULT 'open',        -- 'open', 'closed_tp', 'closed_sl', 'closed_signal', 'closed_manual'
    signal_ids JSON,                   -- Array of signal IDs that triggered this
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE TABLE equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT NOT NULL,
    equity REAL NOT NULL,
    open_positions INTEGER NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    summary TEXT,
    mapped_instruments JSON,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE hybrid_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    modules JSON NOT NULL,             -- [{type: "news"|"strategy", name: "...", weight: 0.6, must_participate: true}]
    combiner_mode TEXT NOT NULL,       -- 'all_agree', 'majority', 'weighted', 'any'
    instruments JSON NOT NULL,
    interval TEXT NOT NULL,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_stream ON signals(stream, created_at);
CREATE INDEX idx_signals_instrument ON signals(instrument, created_at);
CREATE INDEX idx_trades_stream ON trades(stream, opened_at);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_equity_stream ON equity_snapshots(stream, recorded_at);
```

-----

## Instruments

All instruments are OANDA CFDs. Add new instruments by adding entries to `instruments.yaml`.

### Forex Majors

|OANDA Symbol|Pair                    |Geopolitical Keywords                                                                 |
|------------|------------------------|--------------------------------------------------------------------------------------|
|EUR_USD     |Euro / US Dollar        |ecb, european central bank, eurozone, lagarde, federal reserve, fed rate, us inflation|
|GBP_USD     |Pound / US Dollar       |bank of england, boe, uk economy, uk gdp, uk inflation, sterling                      |
|USD_JPY     |Dollar / Yen            |bank of japan, boj, yen intervention, japan economy, risk sentiment                   |
|USD_CHF     |Dollar / Swiss Franc    |swiss national bank, snb, safe haven, swiss franc                                     |
|AUD_USD     |Aussie / US Dollar      |reserve bank australia, rba, china demand, iron ore, australian economy               |
|USD_CAD     |Dollar / Canadian Dollar|bank of canada, boc, oil prices, canadian economy                                     |
|NZD_USD     |Kiwi / US Dollar        |reserve bank new zealand, rbnz, dairy prices, new zealand                             |

### Commodities

|OANDA Symbol|Instrument     |Geopolitical Keywords                                                               |
|------------|---------------|------------------------------------------------------------------------------------|
|XAU_USD     |Gold           |gold, safe haven, real yields, treasury, geopolitical risk, war, conflict, sanctions|
|XAG_USD     |Silver         |silver, industrial demand, precious metals                                          |
|BCO_USD     |Brent Crude Oil|oil, opec, crude, petroleum, saudi, iran, pipeline, energy crisis                   |
|WTICO_USD   |WTI Crude Oil  |wti, us oil production, strategic petroleum reserve, shale                          |
|NATGAS_USD  |Natural Gas    |natural gas, lng, european energy, gas pipeline                                     |

### Crosses (for correlation plays)

|OANDA Symbol|Pair        |Use Case             |
|------------|------------|---------------------|
|EUR_GBP     |Euro / Pound|EU vs UK divergence  |
|EUR_JPY     |Euro / Yen  |Risk-on/off barometer|
|GBP_JPY     |Pound / Yen |High volatility carry|

-----

## LLM Architecture

All providers use the OpenAI-compatible chat completions API. Switching models requires changing config only.

### Model Registry

```python
# backend/signals/model_registry.py

MODELS = {
    "groq/llama-3.3-70b": {
        "provider": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
        "cost_per_1m_tokens": 0,
        "rate_limit": "1000 req/day, 6000 tokens/min",
        "notes": "Fastest free option. Strong reasoning."
    },
    "mistral/mistral-small": {
        "provider": "mistral",
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "env_key": "MISTRAL_API_KEY",
        "cost_per_1m_tokens": 0,
        "rate_limit": "1B tokens/month",
        "notes": "Most generous free quota."
    },
    "openrouter/deepseek-v3": {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "env_key": "OPENROUTER_API_KEY",
        "cost_per_1m_tokens": 0,
        "rate_limit": "50 req/day",
        "notes": "Strong reasoning. Low rate limit — comparison only."
    },
}
```

New models are added by appending entries to this registry. The UI reads from the same registry to render toggle switches.

### Unified LLM Client

```python
# backend/signals/llm_client.py

from openai import OpenAI

class UnifiedLLMClient:
    """Works with any OpenAI-compatible provider."""

    def __init__(self, provider: str, model: str,
                 base_url: str, api_key: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.provider = provider

    def analyze(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        return response.choices[0].message.content

    def analyze_with_fallback(self, prompt: str,
                               fallback_clients: list) -> tuple[str, str]:
        """Try primary, fall back on failure. Returns (response, model_used)."""
        try:
            return self.analyze(prompt), f"{self.provider}/{self.model}"
        except Exception:
            for fb in fallback_clients:
                try:
                    return fb.analyze(prompt), f"{fb.provider}/{fb.model}"
                except Exception:
                    continue
            raise RuntimeError("All LLM providers failed")
```

### Model Comparison Mode

The news stream sends the same headlines to all enabled models. The primary model’s signal is traded. Comparison models’ signals are logged with `is_comparison=1` for later analysis.

In `streams.yaml`:

```yaml
news_stream:
  llm:
    primary_model: "groq/llama-3.3-70b"
    comparison_models:
      - "mistral/mistral-small"
      - "openrouter/deepseek-v3"
    comparison_enabled: false           # Off by default. Toggle in UI.
```

Each model can be toggled on/off independently from the UI. The dashboard computes hypothetical P&L for comparison models (“if this model had been primary, it would have returned X”).

### Prompt Template

Stored in `config/prompts/forex_signal.txt`. Editable without code changes.

```
You are a forex market analyst. Analyze the following recent news headlines
and current market context for {instrument}. Provide a trading signal.

## Recent News
{news_headlines}

## Current Market Context
- Current price: {current_price}
- 24h change: {daily_change}%
- Recent trend: {trend_description}

## Task
Assess the likely impact on {instrument} over the next {time_horizon}.
Consider:
1. Direct economic impact
2. Central bank policy implications
3. Risk sentiment shifts
4. Historical precedent for similar events

Respond ONLY in this exact JSON format, no other text:
{
  "direction": "long" | "short" | "neutral",
  "confidence": 0.0-1.0,
  "reasoning": "1-2 sentence explanation",
  "time_horizon": "short" | "medium" | "long",
  "key_factors": ["factor1", "factor2"]
}
```

-----

## News Pipeline

### Sources (all free, no API key required)

|Source               |Type    |Endpoint                                                                                                  |
|---------------------|--------|----------------------------------------------------------------------------------------------------------|
|BBC Business         |RSS     |`https://feeds.bbci.co.uk/news/business/rss.xml`                                                          |
|Reuters Business     |RSS     |`https://www.reutersagency.com/feed/`                                                                     |
|GDELT                |REST API|`http://api.gdeltproject.org/api/v2/doc/doc?query=forex+OR+economy&mode=artlist&maxrecords=50&format=json`|
|ForexFactory Calendar|JSON    |`https://nfs.faireconomy.media/ff_calendar_thisweek.json`                                                 |

New sources are added to `streams.yaml`. Implement a fetcher function following the existing pattern in `news_ingestor.py`.

### Instrument Mapper

Headlines are matched to instruments via keyword lists defined in `instruments.yaml`. A headline can map to multiple instruments (e.g., “Fed raises rates” maps to EUR_USD, GBP_USD, USD_JPY, XAU_USD). Headlines that match no keywords are discarded. The LLM only analyzes instruments that have relevant news — this keeps costs minimal.

### Deduplication

Near-duplicate headlines across sources are removed by fuzzy string matching before LLM analysis.

-----

## Strategy System

### Base Class

Every strategy implements this interface. New strategies are auto-discovered by the registry — drop a file in `backend/strategies/`, it appears in the system.

```python
# backend/strategies/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import pandas as pd

@dataclass
class TechnicalSignal:
    instrument: str
    direction: str              # "long", "short", "neutral"
    confidence: float           # 0.0 - 1.0
    strategy_name: str
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict = field(default_factory=dict)

class Strategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier matching config. Example: 'momentum'"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description with paper reference."""

    @abstractmethod
    def analyze(self, df: pd.DataFrame, instrument: str) -> TechnicalSignal:
        """
        Analyze OHLCV data and return a signal.

        Args:
            df: DataFrame with columns [Open, High, Low, Close, Volume]
                indexed by datetime, most recent last.
                Contains self.lookback_periods rows.
            instrument: OANDA instrument symbol (e.g., 'EUR_USD')

        Returns:
            TechnicalSignal with direction and confidence.
        """

    @abstractmethod
    def get_parameters(self) -> dict:
        """Return current parameters for logging and optimization."""

    @abstractmethod
    def set_parameters(self, params: dict) -> None:
        """Update parameters for backtesting optimization."""
```

### Strategies to Implement

**1. Time Series Momentum** (`momentum.py`)

- **Paper:** Moskowitz, Ooi & Pedersen (2012), “Time Series Momentum,” Journal of Financial Economics
- **Logic:** Calculate returns over past 1-12 months. If positive, go long. If negative, go short. Rebalance weekly.
- **Default params:** `lookback_months: 12, rebalance_frequency: "weekly"`

**2. Carry Trade** (`carry.py`)

- **Paper:** Menkhoff, Sarno, Schmeling & Schrimpf (2012), “Currency Momentum Strategies,” Journal of Financial Economics
- **Logic:** Buy currencies with higher interest rates, sell those with lower rates. Earn the rate differential daily.
- **Default params:** `rate_data: "manual"` (central bank rates updated periodically in config)
- **Note:** Known to blow up during crises. The news stream’s veto function in hybrids is specifically valuable here.

**3. London/NY Session Breakout** (`breakout.py`)

- **Paper:** Breedon & Ranaldo (2012), “Intraday Patterns in FX Returns and Order Flow,” Journal of Money, Credit & Banking
- **Logic:** Measure price range during Asian session (22:00-06:00 UTC). Trade breakout when London opens.
- **Default params:** `asian_start: "22:00", asian_end: "06:00", breakout_buffer_pips: 10`

**4. Mean Reversion** (`mean_reversion.py`)

- **Paper:** Pojarliev & Levich (2008), “Do Professional Currency Managers Beat the Benchmark?”, Financial Analysts Journal
- **Logic:** When price reaches outer Bollinger Band and RSI shows divergence, trade the reversal.
- **Default params:** `bb_period: 20, bb_std: 2.0, rsi_period: 14, rsi_oversold: 30, rsi_overbought: 70`

**5. Volatility Breakout** (`volatility_breakout.py`)

- **Paper:** Alizadeh, Brandt & Diebold (2002), “Range-Based Estimation of Stochastic Volatility Models,” Journal of Finance
- **Logic:** When ATR contracts below a threshold and price breaks out, enter in the breakout direction.
- **Default params:** `atr_period: 14, atr_contraction_threshold: 0.7, breakout_atr_multiplier: 1.0`

### Adding a New Strategy

1. Create `backend/strategies/{name}.py`
1. Subclass `Strategy` from `base.py`
1. Implement `name`, `description`, `analyze()`, `get_parameters()`, `set_parameters()`
1. The registry auto-discovers it
1. Add default params to `streams.yaml` under `strategy_stream.strategies`
1. Write tests in `tests/test_strategies.py`
1. Run backtest: `python -m backend.main --mode backtest --strategy {name}`

-----

## Stream Base Class

```python
# backend/streams/base_stream.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StreamSignal:
    stream_id: str
    instrument: str
    direction: str              # "long", "short", "neutral"
    confidence: float
    sources: list[str]          # Which modules contributed
    reasoning: str
    metadata: dict

@dataclass
class StreamState:
    stream_id: str
    name: str
    status: str                 # "running", "paused", "error"
    open_positions: list[dict]
    total_pnl: float
    trade_count: int
    last_tick: datetime | None

class BaseStream(ABC):
    """
    All three stream types inherit from this.
    Each stream has its own capital allocation, trades, and P&L.
    """

    def __init__(self, stream_id: str, config, db, oanda, risk, executor):
        self.stream_id = stream_id
        self.config = config
        self.db = db
        self.oanda = oanda
        self.risk = risk
        self.executor = executor

    @abstractmethod
    async def tick(self) -> list[StreamSignal]:
        """
        Run one cycle:
        1. Gather inputs (news, price data, or both)
        2. Generate signals
        3. Filter by confidence threshold
        4. Risk check
        5. Execute trades
        6. Log everything to database
        Returns all signals generated (even if not traded).
        """

    def get_state(self) -> StreamState:
        """Query database for current stream state."""
        ...

    def record_signal(self, signal: StreamSignal):
        """Insert signal into signals table."""
        ...

    def record_trade(self, trade: dict):
        """Insert trade into trades table."""
        ...

    def record_equity(self):
        """Snapshot current equity into equity_snapshots table."""
        ...
```

-----

## Hybrid Combiner Modes

When a user creates a custom hybrid, they select modules (news, any strategies) and a combiner mode:

|Mode       |Logic                                                                                            |Use Case                                     |
|-----------|-------------------------------------------------------------------------------------------------|---------------------------------------------|
|`all_agree`|Every module must produce the same direction                                                     |Strictest — fewest trades, highest conviction|
|`majority` |More than half agree on direction                                                                |Balanced                                     |
|`weighted` |Each signal (long=+1, short=-1, neutral=0) × weight. Sum > threshold → long, < -threshold → short|Most flexible                                |
|`any`      |Any single module above confidence threshold triggers                                            |Loosest — most trades                        |

The **“must participate” flag** per module: if set, that module must produce a non-neutral signal for any trade to happen. Example: news with `must_participate: true` means no trade occurs if the LLM says “neutral” — even if momentum says “strong long.” This makes news the gatekeeper.

-----

## Risk Manager

```python
# backend/risk/risk_manager.py

@dataclass
class RiskCheck:
    approved: bool
    position_size: float          # Units to trade (0 if rejected)
    rejection_reason: str | None = None

class RiskManager:
    """Validates trades against risk rules before execution."""

    def check_trade(self, stream_id: str, instrument: str,
                    direction: str, entry_price: float,
                    stop_loss: float) -> RiskCheck:
        """
        Checks (in order):
        1. Is the market open?
        2. Has this stream hit max open positions?
        3. Has this stream hit daily loss limit?
        4. Would this trade exceed max risk per trade?
        5. Correlation check (not overexposed to correlated instruments)
        6. Calculate position size based on risk % and stop distance
        Returns RiskCheck with position_size if approved.
        """

    def calculate_position_size(self, account_balance: float,
                                 risk_pct: float, entry: float,
                                 stop_loss: float,
                                 instrument: str) -> float:
        """
        Position size = (balance × risk%) / (|entry - stop_loss| × pip_value)
        """
```

-----

## Configuration Files

### settings.yaml

```yaml
# Master configuration — all tuneable parameters

scheduler:
  interval: "1h"
  timezone: "UTC"

risk:
  max_risk_per_trade: 0.01         # 1% of stream's capital per trade
  max_open_positions_per_stream: 5
  max_daily_loss_per_stream: 0.03  # 3% — stop trading for the day
  max_correlated_positions: 2
  default_rr_ratio: 1.5            # Take profit = 1.5× stop loss distance
  stop_loss_method: "atr"          # "atr" or "fixed_pips"
  atr_multiplier: 1.5
  atr_period: 14

execution:
  mode: "practice"                 # "practice" or "live"
  oanda_environment: "practice"    # "practice" or "live"

data:
  candle_granularity: "H1"         # Matches scheduler interval
  lookback_periods: 200
  secondary_granularity: "D"       # For daily trend context

reviews:
  auto_generate: true
  schedule: "daily"
  time: "22:00"                    # After NY close
  review_period_days: 7
  max_archive_count: 30
  output_dir: "reviews"
```

### streams.yaml

```yaml
news_stream:
  id: "news"
  name: "News Stream"
  enabled: true
  capital_allocation: 33333
  instruments:
    - EUR_USD
    - GBP_USD
    - USD_JPY
    - XAU_USD
    - BCO_USD
  news_sources:
    - type: "rss"
      url: "https://feeds.bbci.co.uk/news/business/rss.xml"
      name: "BBC Business"
    - type: "rss"
      url: "https://www.reutersagency.com/feed/"
      name: "Reuters"
    - type: "gdelt"
      enabled: true
    - type: "economic_calendar"
      url: "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
  news_lookback_hours: 4
  min_confidence: 0.60
  llm:
    primary_model: "groq/llama-3.3-70b"
    comparison_models:
      - "mistral/mistral-small"
      - "openrouter/deepseek-v3"
    comparison_enabled: false

strategy_stream:
  id: "strategy"
  name: "Strategy Stream"
  enabled: true
  capital_allocation: 33333
  instruments:
    - EUR_USD
    - GBP_USD
    - USD_JPY
    - USD_CHF
    - AUD_USD
    - XAU_USD
  strategies:
    - name: "momentum"
      enabled: true
      params:
        lookback_months: 12
        rebalance_frequency: "weekly"
    - name: "carry"
      enabled: true
      params:
        rate_data: "manual"
    - name: "breakout"
      enabled: true
      params:
        asian_start: "22:00"
        asian_end: "06:00"
        breakout_buffer_pips: 10
    - name: "mean_reversion"
      enabled: true
      params:
        bb_period: 20
        bb_std: 2.0
        rsi_period: 14
        rsi_oversold: 30
        rsi_overbought: 70
    - name: "volatility_breakout"
      enabled: true
      params:
        atr_period: 14
        atr_contraction_threshold: 0.7
        breakout_atr_multiplier: 1.0

hybrid_defaults:
  capital_allocation: 33333
  min_confidence: 0.60
```

### instruments.yaml

```yaml
# Each instrument has an OANDA symbol and keyword list for news mapping.
# Add new instruments by appending entries.

EUR_USD:
  display_name: "EUR/USD"
  type: "forex"
  keywords:
    - ecb
    - european central bank
    - eurozone
    - euro area
    - lagarde
    - bundesbank
    - federal reserve
    - fed rate
    - us dollar
    - us inflation
    - us jobs
    - non-farm payrolls
    - fomc

GBP_USD:
  display_name: "GBP/USD"
  type: "forex"
  keywords:
    - bank of england
    - boe
    - uk economy
    - uk gdp
    - uk inflation
    - sterling
    - british pound
    - bailey

USD_JPY:
  display_name: "USD/JPY"
  type: "forex"
  keywords:
    - bank of japan
    - boj
    - yen
    - intervention
    - japan economy
    - ueda
    - risk sentiment
    - risk off
    - risk on

USD_CHF:
  display_name: "USD/CHF"
  type: "forex"
  keywords:
    - swiss national bank
    - snb
    - safe haven
    - swiss franc

AUD_USD:
  display_name: "AUD/USD"
  type: "forex"
  keywords:
    - reserve bank australia
    - rba
    - china demand
    - iron ore
    - australian economy
    - australia employment

USD_CAD:
  display_name: "USD/CAD"
  type: "forex"
  keywords:
    - bank of canada
    - boc
    - canadian economy
    - canada jobs

NZD_USD:
  display_name: "NZD/USD"
  type: "forex"
  keywords:
    - reserve bank new zealand
    - rbnz
    - dairy prices
    - new zealand economy

XAU_USD:
  display_name: "Gold"
  type: "commodity"
  keywords:
    - gold
    - safe haven
    - real yields
    - treasury yields
    - geopolitical risk
    - war
    - conflict
    - sanctions
    - central bank gold

XAG_USD:
  display_name: "Silver"
  type: "commodity"
  keywords:
    - silver
    - industrial demand
    - precious metals

BCO_USD:
  display_name: "Brent Crude"
  type: "commodity"
  keywords:
    - oil
    - opec
    - crude
    - petroleum
    - saudi arabia
    - iran
    - pipeline
    - energy crisis
    - brent

WTICO_USD:
  display_name: "WTI Crude"
  type: "commodity"
  keywords:
    - wti
    - us oil
    - shale
    - strategic petroleum reserve
    - us production

NATGAS_USD:
  display_name: "Natural Gas"
  type: "commodity"
  keywords:
    - natural gas
    - lng
    - european energy
    - gas pipeline
    - gas storage

EUR_GBP:
  display_name: "EUR/GBP"
  type: "forex"
  keywords:
    - eu uk
    - brexit
    - euro pound
    - european uk divergence

EUR_JPY:
  display_name: "EUR/JPY"
  type: "forex"
  keywords:
    - euro yen
    - risk appetite
    - risk barometer

GBP_JPY:
  display_name: "GBP/JPY"
  type: "forex"
  keywords:
    - pound yen
    - carry trade
```

-----

## Screen Designs

### Navigation

Persistent left sidebar:

```
┌──────┐
│ ≡    │  Forex Sentinel
│      │
│ 📰   │  News Stream
│      │
│ 📊   │  Strategies
│      │
│ 🔧   │  Custom Hybrid
│      │
│ 📈   │  Dashboard
│      │
│      │
│ ⚙️   │  Settings
└──────┘
```

### Screen 1: News Stream

```
┌─────────────────────────────────────────────────────────────────┐
│  NEWS STREAM                          Last cycle: 14 mins ago   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MODEL: Groq/Llama 3.3 70B [ON]                                │
│  Comparison: Mistral [OFF] DeepSeek [OFF]                       │
│                                                                  │
│  LATEST SIGNALS                              STREAM METRICS     │
│  ┌─────────────────────────────────────┐    ┌─────────────────┐ │
│  │ 🔴 SHORT EUR_USD  conf: 0.78       │    │ P&L:  +£1,240   │ │
│  │ "ECB dovish pivot signals rate      │    │ Trades: 47      │ │
│  │  divergence with hawkish Fed"       │    │ Win:   53%      │ │
│  │ Sources: Reuters, BBC Business      │    │ Sharpe: 1.42    │ │
│  │ 14 mins ago                         │    │ Drawdown: -2.1% │ │
│  ├─────────────────────────────────────┤    └─────────────────┘ │
│  │ 🟢 LONG XAU_USD   conf: 0.65       │                        │
│  │ "Middle East escalation drives      │    ACTIVE POSITIONS    │
│  │  safe haven demand"                 │    ┌─────────────────┐ │
│  │ Sources: GDELT, Al Jazeera          │    │ EUR_USD SHORT    │ │
│  │ 1h ago                              │    │ entry: 1.0845   │ │
│  ├─────────────────────────────────────┤    │ P&L: +34 pips   │ │
│  │ ⚪ NEUTRAL GBP_USD  conf: 0.41     │    ├─────────────────┤ │
│  │ Below threshold (0.60) → NO TRADE   │    │ XAU_USD LONG    │ │
│  └─────────────────────────────────────┘    │ entry: 2,341.50 │ │
│                                              │ P&L: -12 pips   │ │
│  NEWS FEED                                   └─────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ ● Reuters  "ECB's Lagarde: inflation progress..."           ││
│  │            → EUR_USD, EUR_GBP                     3m ago    ││
│  │ ● GDELT    "Iran nuclear talks breakdown..."               ││
│  │            → BCO_USD, XAU_USD, USD_JPY            45m ago   ││
│  │ ● Calendar "US Non-Farm Payrolls: 256K (exp 180K)"         ││
│  │            → EUR_USD, GBP_USD, USD_JPY, XAU_USD   2h ago   ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### Screen 2: Strategy Stream

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY STREAM                        Last cycle: 14 mins ago │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ MOMENTUM (Moskowitz 2012)                         [ON] ⚙️   │ │
│  │ "12-month time series momentum across instruments"          │ │
│  │ P&L: +£890   Win: 58%   Sharpe: 1.21   Trades: 23          │ │
│  │ ┌──────────────────────────────┐  Active: 🟢 LONG AUD_USD  │ │
│  │ │ equity curve                 │          🔴 SHORT USD_JPY  │ │
│  │ └──────────────────────────────┘                            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ CARRY TRADE (Menkhoff 2012)                       [ON] ⚙️   │ │
│  │ "Long high-yield, short low-yield currencies"               │ │
│  │ P&L: +£430   Win: 64%   Sharpe: 0.89   Trades: 8           │ │
│  │ ┌──────────────────────────────┐  Active: 🟢 LONG AUD_JPY  │ │
│  │ │ equity curve                 │                            │ │
│  │ └──────────────────────────────┘                            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ BREAKOUT (Breedon 2012)                           [ON] ⚙️   │ │
│  │ ... (same pattern for each strategy)                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [Run Backtest on All]  [+ Add Strategy]                        │
└──────────────────────────────────────────────────────────────────┘
```

### Screen 3: Custom Hybrid Builder

```
┌─────────────────────────────────────────────────────────────────┐
│  CUSTOM HYBRID                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MY HYBRIDS                                                      │
│  ┌───────────────────────┐  ┌───────────────────────┐           │
│  │ ★ Geopolitical Edge   │  │ Conservative Blend    │           │
│  │   News + Momentum     │  │ Momentum + Mean Rev   │           │
│  │   P&L: +£1,680        │  │ P&L: +£520            │           │
│  └───────────────────────┘  └───────────────────────┘           │
│                                                                  │
│  [+ Create New Hybrid]                                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  EDITING: Geopolitical Edge                                  ││
│  │                                                              ││
│  │  MODULES                         RECIPE                      ││
│  │  Available:                      ┌────────────────────────┐  ││
│  │  ┌──────────────┐               │ 1. 📰 News Signals     │  ││
│  │  │ 📰 News       │ ─[Add]─→    │    Weight: 0.6          │  ││
│  │  ├──────────────┤               │    ☑ Must participate   │  ││
│  │  │ 📊 Momentum   │ ─[Add]─→    ├────────────────────────┤  ││
│  │  ├──────────────┤               │ 2. 📊 Momentum         │  ││
│  │  │ 📊 Carry      │              │    Weight: 0.4          │  ││
│  │  ├──────────────┤               │    ☐ Must participate   │  ││
│  │  │ 📊 Breakout   │              └────────────────────────┘  ││
│  │  ├──────────────┤                                            ││
│  │  │ 📊 Mean Rev   │             COMBINER: ● Weighted score    ││
│  │  ├──────────────┤              ○ All must agree               ││
│  │  │ 📊 Vol Break  │             ○ Majority vote                ││
│  │  └──────────────┘              ○ Any one triggers             ││
│  │                                                              ││
│  │  INSTRUMENTS       MIN CONFIDENCE                            ││
│  │  ☑ EUR_USD         ┌────────┐                                ││
│  │  ☑ GBP_USD         │ 0.65   │                                ││
│  │  ☑ USD_JPY         └────────┘                                ││
│  │  ☑ XAU_USD                                                   ││
│  │  ☐ BCO_USD         [Run Backtest]  [Save & Activate]        ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### Screen 4: Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  DASHBOARD                                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TIME PERIOD:  [1W] [1M] [3M] [6M] [YTD] [ALL] [Custom ▼]      │
│                                                                  │
│  EQUITY CURVES (overlaid, toggle streams on/off)                 │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ £102k ┤          ╱──── Geopolitical Edge (hybrid)            ││
│  │       │    ╱────╱                                            ││
│  │ £101k ┤───╱──────────── News Stream                          ││
│  │ £100k ┤═══════════════════ Strategy Stream                   ││
│  │  £99k ┤ ╲───────── Conservative Blend (hybrid)               ││
│  │       ┼──────────────────────────────────── time              ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  COMPARISON TABLE                                                │
│  ┌────────────────────┬────────┬────────┬────────┬──────┬──────┐│
│  │ Stream             │ Return │ Sharpe │ MaxDD  │ Win% │ Trds ││
│  ├────────────────────┼────────┼────────┼────────┼──────┼──────┤│
│  │ 📰 News Stream     │ +2.4%  │ 1.42   │ -2.1%  │ 53%  │ 47  ││
│  │ 📊 Strategy Stream │ +1.1%  │ 1.08   │ -1.8%  │ 52%  │ 62  ││
│  │   ├ Momentum       │ +0.9%  │ 1.21   │ -1.2%  │ 58%  │ 23  ││
│  │   ├ Carry          │ +0.4%  │ 0.89   │ -0.8%  │ 64%  │ 8   ││
│  │   ├ Breakout       │ -0.2%  │ 0.34   │ -1.8%  │ 35%  │ 31  ││
│  │   └ Mean Reversion │ +0.0%  │ 0.45   │ -1.1%  │ 48%  │ 19  ││
│  │ 🔧 Geopolitical    │ +3.2%  │ 1.67   │ -1.5%  │ 57%  │ 38  ││
│  │ 🔧 Conservative    │ +0.5%  │ 0.91   │ -0.9%  │ 55%  │ 14  ││
│  └────────────────────┴────────┴────────┴────────┴──────┴──────┘│
│                                                                  │
│  MODEL COMPARISON (when comparison models enabled)               │
│  ┌────────────────────┬──────────┬──────────────┬──────────────┐│
│  │ Model              │ Agree w/ │ Hypothetical │ Monthly Cost ││
│  │                    │ Outcome  │ P&L          │              ││
│  ├────────────────────┼──────────┼──────────────┼──────────────┤│
│  │ groq/llama-3.3-70b │ 58%      │ +£840        │ £0           ││
│  │ mistral/small      │ 54%      │ +£520        │ £0           ││
│  │ deepseek-v3        │ 61%      │ +£1,040      │ £0           ││
│  └────────────────────┴──────────┴──────────────┴──────────────┘│
│                                                                  │
│  RECENT TRADES                    INSTRUMENT BREAKDOWN           │
│  ┌──────────────────────────┐    ┌────────────────────────────┐ │
│  │ Stream │ Instr │ P&L     │    │ EUR_USD  ████████  +£620   │ │
│  │ 📰 News│EUR_USD│ +34pip  │    │ XAU_USD  ██████    +£440   │ │
│  │ 📊 Mom │AUD_USD│ -18pip  │    │ GBP_USD  ███       +£180   │ │
│  │ 🔧 Geo │XAU_USD│ +52pip  │    │ USD_JPY  █         +£60    │ │
│  └──────────────────────────┘    └────────────────────────────┘ │
│                                                                  │
│  COWORK REVIEWS                                                  │
│  [📋 Generate Review Now]  Period: [7 days ▼]                    │
│  Latest: 2026-03-18 22:00 (scheduled)                           │
│  Location: reviews/latest/                                       │
└──────────────────────────────────────────────────────────────────┘
```

-----

## Cowork Review System

The system periodically generates a self-contained review packet that Claude in Cowork can analyze immediately without additional context.

### Review Folder Structure

```
reviews/
├── SYSTEM_CONTEXT.md              # Current system config (auto-regenerated)
├── latest/                        # Symlink → most recent archive entry
│   ├── REVIEW.md                  # Pre-computed summary with metrics
│   ├── trades.csv                 # All trades in review period
│   ├── signals.csv                # All signals (including comparison models)
│   ├── equity_curves.csv          # Hourly equity per stream
│   └── open_positions.csv         # Currently open positions
└── archive/
    ├── 2026-03-18_22-00_scheduled/
    ├── 2026-03-17_22-00_scheduled/
    └── ...
```

### SYSTEM_CONTEXT.md

Auto-generated from `settings.yaml`, `streams.yaml`, and `instruments.yaml`. Describes the entire system: what streams exist, what strategies run, what instruments are traded, what risk settings are in place, and what the user wants from reviews. Regenerated whenever config changes.

Includes a user-editable section:

```markdown
### What I Want From Reviews
- Which stream is performing best and why
- Which instruments are profitable vs loss-making
- Whether the LLM reasoning was correct on winning AND losing trades
- Suggestions for parameter changes backed by the data
- Whether any strategy should be enabled/disabled
- Correlation between streams — are they taking the same trades?
```

### REVIEW.md Contents

Each review contains:

1. **Headlines** — Overall P&L, best/worst performer, trade counts, biggest winner/loser
1. **Stream Performance** — Per-stream metrics table with week-over-week comparison
1. **Winning Trades** — What signal triggered them, what the reasoning was, how long held
1. **Losing Trades** — What went wrong (post-mortem per trade)
1. **Strategy Breakdown** — Per-strategy metrics within the strategy stream
1. **Instrument Analysis** — P&L per instrument across all streams
1. **Model Comparison** — If comparison models are enabled, accuracy comparison
1. **Inter-Stream Correlation** — Did multiple streams trade the same way?
1. **Auto-Generated Questions** — Data-driven questions (e.g., “Low-confidence signals went 1/3 — raise threshold?”)

### Review Triggers

|Trigger        |How                                               |When                             |
|---------------|--------------------------------------------------|---------------------------------|
|Scheduled      |Automatic in trading cycle                        |Daily at 22:00 UTC (configurable)|
|Manual (UI)    |Dashboard button “Generate Review Now”            |Anytime                          |
|Manual (CLI)   |`python -m backend.main --mode review --period 7d`|Anytime                          |
|Manual (GitHub)|`workflow_dispatch` with `mode: review`           |GitHub UI                        |

### File Sizes

|File              |~Size (1 week)|~Size (1 month)|
|------------------|--------------|---------------|
|REVIEW.md         |5-10 KB       |15-25 KB       |
|trades.csv        |2-5 KB        |10-20 KB       |
|signals.csv       |5-10 KB       |20-40 KB       |
|equity_curves.csv |10-15 KB      |40-60 KB       |
|open_positions.csv|<1 KB         |<1 KB          |
|**Total**         |**~30 KB**    |**~100 KB**    |

30 daily snapshots = ~1 MB total. Negligible.

-----

## Extensibility

### Adding a new model

Add an entry to `MODELS` dict in `backend/signals/model_registry.py`:

```python
"newprovider/new-model": {
    "provider": "newprovider",
    "base_url": "https://api.newprovider.com/v1",
    "model": "new-model-name",
    "env_key": "NEWPROVIDER_API_KEY",
    "cost_per_1m_tokens": 0,
    "rate_limit": "...",
    "notes": "..."
}
```

Add the API key to GitHub Secrets. The model appears in the UI automatically.

### Adding a new instrument

Add an entry to `instruments.yaml` with OANDA symbol, display name, type, and keywords. Add the symbol to the relevant streams in `streams.yaml`. No code changes.

### Adding a new strategy

Create `backend/strategies/{name}.py` implementing the `Strategy` base class. The registry auto-discovers it. Add default params to `streams.yaml`. Write tests.

### Adding a new news source

Add the source config to `streams.yaml` under `news_sources`. Implement a fetcher function in `news_ingestor.py` following the existing RSS/GDELT pattern.

### Moving to local hosting (M1 Mac)

Clone the repo. Install dependencies. Run `python -m backend.main --mode tick` on a schedule using cron or APScheduler. The SQLite database, logs, and reviews all work identically. For a live dashboard, run the FastAPI wrapper locally (future enhancement — same trading logic, just wrapped in a server).

### Moving to paid hosting

Deploy to Railway, Fly.io, or any VPS. Wrap the trading logic in a FastAPI server with APScheduler. Add WebSocket for live updates. The core trading logic, strategies, risk manager, and database are unchanged.

-----

## Required Accounts (all free)

|Service   |URL               |What You Get                                       |
|----------|------------------|---------------------------------------------------|
|OANDA     |oanda.com         |Demo account with £100K fake money, free API access|
|Groq      |console.groq.com  |1000 requests/day, Llama 3.3 70B                   |
|Mistral   |console.mistral.ai|1B tokens/month, Mistral Small                     |
|OpenRouter|openrouter.ai     |50 req/day on free models, DeepSeek V3             |
|GitHub    |github.com        |Public repo, Actions (unlimited minutes)           |
|Vercel    |vercel.com        |Static site hosting, auto-deploys from GitHub      |

Total setup time: ~30 minutes. Total cost: £0.

-----

## Build Phases

### Phase 0: Repository Setup (Day 0)

1. Create public GitHub repo
1. Set up project structure, `pyproject.toml`, `requirements.txt`
1. GitHub Actions workflow file (`.github/workflows/trade.yml`)
1. Add all API keys to GitHub Secrets
1. **Milestone:** Action runs manually, prints “Forex Sentinel initialized”

### Phase 1: Core Infrastructure (Day 1)

1. Pydantic config loader (`settings.yaml`, `streams.yaml`, `instruments.yaml`)
1. SQLite database schema + connection
1. OANDA client (connect to practice account, fetch candles, get account info)
1. Basic CLI entry point
1. **Milestone:** `python -m backend.main --mode tick` connects to OANDA and prints account balance

### Phase 2: Strategy Stream (Day 2-3)

1. Strategy base class + registry (auto-discovery)
1. Implement momentum strategy
1. Implement mean_reversion strategy
1. Implement remaining strategies (carry, breakout, volatility_breakout)
1. Strategy stream class
1. Backtest engine
1. **Milestone:** `python -m backend.main --mode backtest --strategy momentum --instrument EUR_USD` produces results

### Phase 3: News Stream (Day 3-4)

1. News ingestor (RSS + GDELT + calendar)
1. Instrument mapper (keyword matching)
1. Unified LLM client + model registry
1. News stream class
1. **Milestone:** System fetches live news, generates signals via Groq, logs to SQLite

### Phase 4: Risk + Execution (Day 4-5)

1. Risk manager (per-stream checks, position sizing)
1. Executor (OANDA practice mode order placement)
1. Wire both streams through risk → execution pipeline
1. **Milestone:** Both streams place paper trades on OANDA demo account

### Phase 5: Dashboard JSON Export (Day 5-6)

1. JSON exporter (SQLite → static JSON files)
1. Dashboard data models (summary, trades, equity curves, signals)
1. Wire into trading cycle (export after each tick)
1. **Milestone:** After a tick, `frontend/public/data/dashboard.json` contains valid data

### Phase 6: Frontend (Day 6-9)

1. Vite + React + Tailwind setup
1. Layout with sidebar navigation
1. News Stream screen
1. Strategy Stream screen
1. Dashboard screen (equity curves, comparison table, trades, instruments)
1. Model comparison section in dashboard
1. Vercel deployment config
1. **Milestone:** Open browser, see all screens with real data from last trading cycle

### Phase 7: Hybrid Builder (Day 9-11)

1. Hybrid config CRUD in database
1. Hybrid stream class (dynamic module loading + combiner logic)
1. Hybrid builder UI (module selection, combiner mode, instruments, weights)
1. Wire hybrids into trading cycle
1. **Milestone:** Create “News + Momentum” hybrid, it runs next cycle, appears on dashboard

### Phase 8: Cowork Review System (Day 11-12)

1. Review generator (metrics computation + narrative)
1. SYSTEM_CONTEXT.md auto-generation from config
1. REVIEW.md builder with all sections
1. CSV exporters (trades, signals, equity, positions)
1. Archive management + latest symlink
1. Scheduled + manual trigger integration
1. Dashboard review section with generate button
1. **Milestone:** Generate review, open in Cowork, Claude understands everything immediately

-----

## CLAUDE.md

```markdown
# Forex Sentinel — Claude Code Instructions

## Project Overview
Multi-stream forex/commodities trading system. Runs as GitHub Actions on
hourly cron. Static React dashboard on Vercel. SQLite for all state.
Three independent trading streams + custom hybrid builder + performance
dashboard + Cowork review system.

## Tech Stack
- Python 3.12+, pip
- pandas, backtesting.py, oandapyV20, openai, aiohttp, feedparser, pydantic
- React 18, Vite, Tailwind, Recharts
- SQLite (single file: data/sentinel.db)
- GitHub Actions (scheduled hourly)
- Vercel (static frontend)

## Architecture
- Backend is CLI-based: `python -m backend.main --mode tick|backtest|review`
- Each tick runs all active streams once, writes to SQLite, exports dashboard JSON
- Frontend reads from static JSON files in frontend/public/data/
- GitHub Actions commits updated data after each cycle
- Vercel auto-deploys on push to main

## Key Design Rules
1. Streams are independent: own capital, own trades, own P&L tracking
2. Strategies are plugins: one file each, auto-discovered by registry
3. Models are config-driven: OpenAI-compatible API, swap by changing config
4. Instruments are config-driven: add to instruments.yaml, no code changes
5. All state in SQLite: trades, signals, equity, hybrid configs
6. Log everything: every signal, trade, and rejection
7. Backtest before live: nothing trades real money without backtesting

## When Adding a New Strategy
1. Create backend/strategies/{name}.py
2. Subclass Strategy from backend/strategies/base.py
3. Implement: name, description, analyze(), get_parameters(), set_parameters()
4. It auto-registers via the registry
5. Add default params to config/streams.yaml
6. Write tests in tests/test_strategies.py
7. Backtest: python -m backend.main --mode backtest --strategy {name}

## When Adding a New Model
1. Add entry to MODELS dict in backend/signals/model_registry.py
2. Add API key to GitHub Secrets
3. It appears in the UI automatically

## When Adding a New Instrument
1. Add entry to config/instruments.yaml (symbol, display name, type, keywords)
2. Add symbol to relevant streams in config/streams.yaml
3. No code changes needed

## When Adding a New News Source
1. Add source to config/streams.yaml under news_sources
2. Implement fetcher in backend/data/news_ingestor.py

## Environment Variables (GitHub Secrets)
- OANDA_API_KEY — OANDA practice account API key
- OANDA_ACCOUNT_ID — OANDA account ID
- GROQ_API_KEY — Groq free tier
- MISTRAL_API_KEY — Mistral free tier
- OPENROUTER_API_KEY — OpenRouter free tier

## Testing
- pytest tests/ -v
- Mock external calls (OANDA, LLM) in tests
- Strategies should have backtest-based integration tests

## Code Style
- Python: type hints everywhere, black formatter
- React: functional components, hooks only
- All config in YAML files, never hardcoded
```

-----

## Risk Warnings

- **76.8% of retail CFD accounts lose money** (OANDA’s own regulatory disclosure).
- **Start on demo.** Run for at least 3 months on the OANDA practice account before considering real money.
- **Backtest results do not equal live results.** Slippage, spread widening during news events, and execution delays all erode backtested returns.
- **The LLM is not an oracle.** It is pattern-matching on training data. It can and will produce incorrect signals. The multi-stream architecture exists specifically so you can measure which approach works and which does not.
- **Never risk money you cannot afford to lose.** When you do go live, start with the absolute minimum amount.
