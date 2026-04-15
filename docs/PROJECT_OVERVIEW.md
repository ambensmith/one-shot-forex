# Project Overview

## What This Is

A university individual project (CS3062 — Computing in Society) that doubles as the vehicle for properly rebuilding and running an autonomous forex trading system.

**Report topic:** AI Agents in Financial Trading — designing an autonomous trading system that compares LLM-based and traditional approaches.

**Original contribution:** The system itself — a multi-stream trading agent that ingests news via LLM analysis alongside classical quant strategies, manages risk, and executes trades on a real broker API.

**Submission deadline:** 17th April 2026

---

## The System

Two independent signal sources, one execution pipeline:

1. **News/LLM stream** — LLMs analyse financial news from multiple free sources and produce directional trading signals via a multi-stage prompt pipeline
2. **Strategy stream** — traditional quant strategies (momentum, carry, breakout, mean reversion) based on price data only

Both streams feed through the same risk management layer (position sizing, stop losses, correlation limits) before executing on Capital.com via API.

The comparison between the two streams is the core of the academic contribution — same instruments, same risk rules, different signal sources.

**Instruments (8):** EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, EUR/GBP, and gold (XAU_USD).

**Stack:** Python/FastAPI backend, React + shadcn/ui dashboard, GitHub Actions automation, SQLite, Capital.com API, Groq LLM API.

---

## The Dashboard

Clean, simple UI using shadcn components with appropriate colours for readability.

**Dashboard / Trades**
- Open trades table (live, never drifts)
- Closed trades table with filters: won/lost, recency, pair/commodity, source (LLM or strategy)
- Each trade expandable to show full drill-down: properly rendered markdown of everything that went into the trade — headlines analysed, LLM reasoning, strategy outputs, risk calculations, price context, timestamps
- For open trades, show whatever info is available so far

**LLM Analysis**
- Full view of the news/LLM pipeline activity
- Sources connected, headlines ingested, relevance assessments, signals generated
- Editable prompts for each stage (relevance assessment, signal generation)
- Accessible and digestible presentation

**Strategies**
- Each strategy visible and explained (what it does, how it works)
- Signals generated, trades triggered, outcomes
- Accessible — someone reading the report should understand what each strategy does

---

## LLM Signal Pipeline (Redesigned)

**Multi-source ingestion:** Connect as many free, quality news sources as possible beyond BBC/CNBC.

**Multi-stage prompt pipeline with editable prompts:**
- **Stage 1 — Relevance:** Given a batch of news items, which instruments are they relevant to?
- **Stage 2 — Signal generation:** Given the relevant news for a specific instrument + price context, produce a directional signal with reasoning
- **Stage 3 — Counter-argument challenge:** A second LLM call argues against the proposed trade, testing the signal's robustness. Can confirm, reduce position size, or kill the signal. Lightweight adaptation of TradingAgents' bull/bear debate mechanism.

**Aggregation, not 1:1 mapping:** Multiple sources and headlines combine to inform a single signal per instrument.

**Full recording:** Every input to the pipeline is stored — raw headlines, relevance assessments, price context, prompt used, LLM response, confidence score, reasoning. All available for drill-down.

---

## The Report

**Main body (60%):** Research and analysis of AI in financial trading and its societal implications — regulation, market stability, accessibility, ethics, the shift from human to AI decision-making.

**Original contribution (40%):** Design and implementation of the system. Architecture, design decisions, how the LLM pipeline works, how it compares to traditional approaches. The system is deployed and running at submission.

**Report approach:** Build first, collect research and decisions along the way. Every design decision is content for the contribution section. Societal analysis written at the end drawing on implementation experience + targeted research.

---

## Workstreams

### Backend
- Redesign LLM signal pipeline (multi-stage, multi-source, editable prompts)
- Fix confidence calibration across both streams
- Remove hybrid stream
- Update instrument list (8 instruments)
- Fix position sizing (minimum size, rounding)
- Move hardcoded risk params to config
- Full trade recording (all inputs stored as structured data, renderable as markdown)
- Add more free news sources

### Frontend
- Install shadcn/ui, build clean simple UI
- Dashboard with open/closed trade tables, drill-down with full rendered markdown
- LLM analysis page with editable prompts and pipeline activity
- Strategy page with explanations and activity
- Filters on closed trades (won/lost, recency, pair, source)
- Live position updates that don't drift

### Deploy & Run
- Reset database
- Deploy the rebuilt system
- Confirm end-to-end: signal generation → risk check → trade execution → logging → dashboard display
- Let it run

### Report
- Compile decisions and reasoning captured during build
- Write societal analysis (AI in trading, regulation, accessibility, ethics)
- Architecture diagrams, screenshots, code walkthrough
- Link to GitHub repo
- Document AI tool usage (required by brief)
- Submit by 17th April

---

## Scope

**In scope:** Full build as described above. The integrations (Capital.com, LLM providers, GitHub Actions) already work. The work is restructuring the pipeline, rebuilding the frontend, and writing the report.

**Out of scope:** Local LLM (Ollama). Claude feedback loop automation. Meaningful trading results — the system may only trigger a handful of trades before submission. The contribution is the design and working implementation.

## What Success Looks Like

- Full system running: multi-stage LLM pipeline, traditional strategies, risk management, broker execution, full trade recording
- Dashboard with shadcn/ui: open trades (live), closed trades (filtered), drill-down with full markdown of all inputs
- LLM page with editable prompts and pipeline visibility
- Strategy page with explanations and activity
- Report that argues clearly about AI in trading, with the system as a substantial original contribution
- A foundation to keep running and improving for months
