# CLAUDE.md

## Project: Forex Sentinel

An autonomous forex trading system that compares LLM-based and traditional strategy approaches to generating trading signals. Also a university project (CS3062 — Computing in Society, UCC) on "AI and the Future of Society."

## What This Is

Two independent signal sources feed into one execution pipeline:

1. **LLM stream** — ingests financial news from multiple free sources, uses a 3-stage prompt pipeline (relevance → signal → counter-argument challenge) to produce trading signals
2. **Strategy stream** — runs peer-reviewed quant strategies (momentum, carry, breakout, mean reversion) on price data

Both streams pass through a directional bias tracker (prevents whipsaw trading), then a risk manager, then execute on Capital.com via API. Trades are "set and forget" — SL/TP handle exits.

**Instruments:** EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, EUR/GBP, XAU/USD (gold).

**Stack:** Python 3.12 / FastAPI backend, React 18 + Tailwind + Vite frontend, SQLite (WAL mode), GitHub Actions automation, Capital.com broker API, Groq LLM API. Frontend design system defined in DESIGN.md (light editorial theme, Playfair Display + Inter, semantic colored shadows, bottom pill nav).

## Key Architecture Documents

Read these before starting any work:

- `docs/PROJECT_OVERVIEW.md` — what the project is, workstreams, scope, success criteria
- `docs/DATA_FLOW.md` — the complete end-to-end data flow spec. Every stage defines what it consumes and produces. This is the contract.
- `DESIGN.md` — the frontend design system. Light editorial theme, Playfair Display + Inter typography, semantic colored shadows, bottom floating pill nav, narrative timeline drill-downs. **Read this before any frontend work.**
- `docs/RESEARCH.md` — collected research on free APIs, open source projects, best practices, academic references. Used for report content.
- `docs/SESSIONS.md` — session-by-session build guide. Each session is a self-contained unit of work with clear inputs, outputs, and verification steps.
- `docs/CHECKS.md` — post-development checklist. Gotchas, ambiguities, and things to reconcile after all dev sessions are complete. Review before submission.

## Build Approach

The system is being built in sessions, each handling one pipeline stage. Each session:

1. Implements one stage according to the spec in DATA_FLOW.md
2. Writes to / reads from the SQLite database using the schema defined in Session 1
3. Has a standalone CLI trigger so it can be tested in isolation (`python -m backend.cli <stage>`)
4. Is verified by running it and inspecting the database output

**Do not change the data contracts between stages without updating DATA_FLOW.md.**

## Existing Code

The `one-shot-forex/` directory contains the previous version of this system. Key pieces to reuse:

- `backend/data/capitalcom_client.py` — Capital.com broker API client. Works. Do not rewrite unless necessary.
- `backend/signals/llm_client.py` — Unified LLM client (Groq, Mistral, Google). Works. Extend for structured output but keep the core.
- `backend/strategies/` — Strategy implementations (momentum, carry, breakout, mean_reversion, volatility_breakout). Review and fix confidence calculations but keep the logic.
- `.github/workflows/trade.yml` — GitHub Actions automation. Update entry point but keep the schedule/structure.
- `config/` — YAML configs. Will be restructured but the patterns are useful reference.

Everything else is being rebuilt to match the spec in DATA_FLOW.md.

## Critical Design Decisions (Do Not Change)

These have been thought through and decided. Do not revisit:

1. **Two streams (LLM vs strategy), no hybrid.** The comparison is the academic contribution.
2. **3-stage LLM pipeline** (relevance → signal → counter-argument challenge). All prompts editable and stored in DB.
3. **LLM handles relevance, not keyword matching.** The old instrument_mapper.py is replaced by Stage 2a.
4. **Directional bias tracker** with anti-whipsaw rules. No conflicting positions, bias alignment required, cooldown on flip.
5. **Set and forget trades.** SL/TP handle exits. No LLM-driven exit decisions.
6. **Structured JSON output** at every pipeline stage. No free-form parsing.
7. **Full trade recording.** Every input to a trade stored and renderable as markdown in the dashboard drill-down.
8. **Finnhub as primary news source.** Plus BBC/CNBC RSS and central bank RSS feeds. GDELT dropped.
9. **Editorial light-theme frontend.** Playfair Display + Inter typography, semantic colored shadows (not block colors), bottom floating pill nav, narrative timeline trade drill-downs. Full spec in DESIGN.md.
10. **All risk parameters in config, not code.** Correlation groups, thresholds, limits, position minimums.

## Code Style

- Python: async where I/O is involved, type hints, Pydantic models for data contracts
- Frontend: React functional components, shadcn/ui, Tailwind utilities
- Commit messages: descriptive, prefix with area (e.g., "backend: add bias tracker", "frontend: trade drill-down")
- No magic numbers in code — everything configurable

## Environment Variables Required

```
CAPITALCOM_EMAIL=
CAPITALCOM_PASSWORD=
CAPITALCOM_API_KEY=
GROQ_API_KEY=
FINNHUB_API_KEY=
```

## Testing

Each pipeline stage must be testable in isolation via CLI:

```bash
python -m backend.cli ingest          # Fetch news + prices, store in DB
python -m backend.cli relevance       # Run Stage 2a on stored headlines
python -m backend.cli signals         # Run Stage 2b on relevant headlines
python -m backend.cli challenge       # Run Stage 2c on generated signals
python -m backend.cli strategies      # Run all strategies on price data
python -m backend.cli bias            # Update bias tracker
python -m backend.cli risk            # Run risk checks on all pending signals
python -m backend.cli execute         # Execute approved trades
python -m backend.cli tick            # Run full pipeline (all of the above in order)
python -m backend.cli reconcile       # Sync with broker positions
```

After each stage, verify by inspecting the relevant database table.
