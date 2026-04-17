# One Shot Forex

An autonomous forex trading system that compares LLM-based and traditional quantitative signal generation, end to end: news ingestion → signal generation → risk filtering → live execution on a retail broker → full trade recording.

**Live dashboard:** https://one-shot-forex.vercel.app

Built as the original contribution for **CS3062 Computing in Society (UCC, 2025–2026)** on the topic *AI and the Future of Society*. The technical contract for the pipeline is in [docs/DATA_FLOW.md](docs/DATA_FLOW.md).

---

## What it does

Two independent signal sources feed a single execution pipeline:

1. **LLM stream** — pulls headlines from Finnhub, BBC Business, CNBC, and central bank RSS feeds (ECB, Fed, BoE, BoJ, SNB, RBA, BoC), then runs a 3-stage prompt pipeline (relevance → signal → counter-argument challenge) to produce structured trading signals.
2. **Strategy stream** — runs peer-reviewed quantitative strategies (momentum, carry, breakout, mean reversion, volatility breakout) over the same price data.

Both streams pass through a directional bias tracker (anti-whipsaw: no conflicting positions, bias alignment required, cooldown on flip), then a risk manager, then execute on Capital.com. Trades are set-and-forget — stop loss and take profit handle exits.

**Instruments traded:** EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, EUR/GBP, XAU/USD.

Every input to every decision is recorded in SQLite and renderable from the dashboard, so any trade can be reconstructed completely after the fact.

## Architecture

The full specification — every stage, every input and output, the database schema, and the tick cycle — lives in [docs/DATA_FLOW.md](docs/DATA_FLOW.md).

The pipeline runs on an hourly schedule during the forex trading week via GitHub Actions.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLite (WAL mode), Pydantic
- **Frontend:** React 18, Tailwind, Vite, deployed on Vercel
- **LLM:** Groq API (primary) with Mistral and Google as fallbacks through a unified client
- **Broker:** Capital.com REST API (demo account during development)
- **News:** Finnhub (primary) + BBC / CNBC / central-bank RSS feeds
- **Scheduling:** GitHub Actions

## Running locally

```bash
git clone https://github.com/ambensmith/one-shot-forex.git
cd one-shot-forex

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in the keys below
python -m backend.cli tick

# Frontend
cd frontend
npm install
npm run dev
```

### Required environment variables

```
CAPITALCOM_EMAIL=
CAPITALCOM_PASSWORD=
CAPITALCOM_API_KEY=
GROQ_API_KEY=
FINNHUB_API_KEY=
```

`MISTRAL_API_KEY` and `GOOGLE_API_KEY` are optional and enable LLM provider fallback. All API tiers used are free at time of writing.

### CLI — every stage runs in isolation

```bash
python -m backend.cli ingest        # Fetch news + prices into the DB
python -m backend.cli relevance     # Stage 2a: which instruments does each headline affect?
python -m backend.cli signals       # Stage 2b: directional signal per instrument
python -m backend.cli challenge     # Stage 2c: counter-argument pass
python -m backend.cli strategies    # Run all quant strategies over price data
python -m backend.cli bias          # Update directional bias tracker
python -m backend.cli risk          # Risk checks on pending signals
python -m backend.cli execute       # Execute approved trades
python -m backend.cli tick          # Run the full pipeline end to end
python -m backend.cli reconcile     # Sync DB with broker positions
```

After each stage, inspect the relevant SQLite table to verify.

## Repository layout

```
backend/        Pipeline stages, broker client, LLM client, strategies, CLI, API server
frontend/       React dashboard
config/         YAML configs (instruments.yaml, settings.yaml, streams.yaml)
docs/           Pipeline specification
.github/        GitHub Actions workflows for the scheduled pipeline
api/            Vercel serverless proxies used by the deployed dashboard
```

## Prior work and acknowledgements

Parts of this repository were carried forward from an earlier iteration of the project and explicitly reused rather than rewritten:

- `backend/data/capitalcom_client.py` — Capital.com broker client
- `backend/signals/llm_client.py` — unified LLM client (Groq / Mistral / Google)
- `backend/strategies/` — strategy implementations (reviewed, confidence calculations revised)
- `.github/workflows/trade.yml` — Actions workflow (entry point updated)

Everything else was rebuilt against the specification in [docs/DATA_FLOW.md](docs/DATA_FLOW.md). Generative AI tools (Claude) were used during development.

## Academic submission

The state of this repository at the point of CS3062 submission is tagged:

```
git checkout v1.0-submission
```

The accompanying report is `CS3062_Individual-Project_117409052.pdf`.

## Disclaimer

This is a research and educational project. It runs on a demo Capital.com account by default. Forex and CFD trading carry substantial risk of loss. Retail investor accounts predominantly lose money (ESMA, 2018). Do not deploy against live capital without understanding what it does.
