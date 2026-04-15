# Session-by-Session Build Guide

Each session is a self-contained unit of work. Start each Claude Code session by saying:

> "Read CLAUDE.md and docs/SESSIONS.md. I'm working on Session N."

Claude Code will have the full context from the spec documents.

---

## Session 1: Database Schema + Project Scaffold

**Goal:** New project structure, database schema, CLI framework, config system.

**What to build:**
- New project directory structure alongside old code (or replace — your call)
- SQLite database with all tables from DATA_FLOW.md:
  - headlines, relevance_assessments, signals, trades, trade_records, bias_state, prompts, equity_snapshots, runs
- Pydantic models for all data contracts (matching the JSON specs in DATA_FLOW.md)
- CLI entry point (`python -m backend.cli <command>`) with stub commands for each pipeline stage
- Config system: YAML for static config (instruments, risk params, strategy params), DB for dynamic config (prompts)
- Seed the prompts table with the initial prompts from DATA_FLOW.md

**Reuse from old code:** Config loading patterns from `core/config.py`. Database WAL mode setup from `core/database.py`.

**Verify:** Run `python -m backend.cli init-db` and inspect the schema. Check that all tables exist and prompts are seeded.

---

## Session 2: News Ingestion (Stage 1)

**Goal:** Fetch news from all sources and store in the headlines table.

**What to build:**

**Finnhub news client** (API key required, 60 calls/min free tier):
- General news endpoint: returns `headline`, `summary` (synopsis, not full text), `source`, `url`, `image`, `category`, `related` (comma-separated ticker symbols), `datetime` (unix timestamp), `id`. Store ALL of these fields.
- Note: Finnhub does NOT provide full article text on free tier — only headline + summary. This is fine.
- The `related` field contains stock tickers, not forex pairs — store it as metadata but don't rely on it for instrument mapping (the LLM handles that in Stage 2a).

**Finnhub economic calendar client:**
- Returns: `event` (name), `country`, `actual`, `estimate` (forecast), `prev` (previous value), `impact` (low/medium/high), `time`, `unit`.
- Store as headlines with a clear source indicator (e.g., source="finnhub_calendar").
- Format the headline from the calendar data, e.g.: "[HIGH IMPACT] US Non-Farm Payrolls — Actual: 256K (Forecast: 200K, Previous: 223K)"
- These are the highest-value items for forex — rate decisions, employment data, inflation prints directly move currency pairs.

**RSS feed client:**
- BBC Business: `https://feeds.bbci.co.uk/news/business/rss.xml`
- CNBC Business: `https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664`
- Central bank feeds (critical for forex — rate decisions, policy statements, speeches):
  - ECB: `https://www.ecb.europa.eu/home/html/rss.en.html`
  - Federal Reserve: `https://www.federalreserve.gov/feeds/press_all.xml`
  - Bank of England: `https://www.bankofengland.co.uk/rss/news` (requires User-Agent header — see note below)
  - Bank of Japan: `https://www.boj.or.jp/en/rss/whatsnew.xml`
  - SNB: `https://www.snb.ch/public/en/rss/pressrel` (note: /public/ in path — old URL without it 404s)
  - RBA: `https://www.rba.gov.au/rss/rss-cb-media-releases.xml`
  - Bank of Canada: `https://www.bankofcanada.ca/feed/`
- RSS feeds provide: `title` (headline), `description` or `summary` (often a paragraph or more), `link` (URL), `published` (datetime). Store all available fields.
- Some central bank feeds may have different structures — handle gracefully, log warnings for feeds that return unexpected formats.
- **Important:** All RSS requests must include a User-Agent header (e.g., `User-Agent: Mozilla/5.0 (compatible; ForexSentinel/1.0)`). Some central banks (BoE in particular) return 403 without it.

**Deduplication:**
- 80% token overlap threshold (raised from old system's 70%)
- Directional word protection: if headlines differ on directional words (raise/cut, hawkish/dovish, rise/fall, up/down, bull/bear), do NOT treat them as duplicates even if other tokens overlap
- Track source_count — if the same story appears in multiple sources, increment the count (this is a signal of importance)

**Storage:** Every news item stored with ALL available fields from the source. The headlines table should have columns for: id, headline, summary, content (null if not available), source, source_url, image_url, category, published_at, ingested_at, source_metadata (JSON blob with everything else from the raw API/RSS response).

**Reuse from old code:** The async fetching pattern and RSS parsing from `data/news_ingestor.py`. The feedparser approach works — extend it, don't rewrite.

**Verify:** Run `python -m backend.cli ingest`. Check the headlines table:
- Should have items from Finnhub news, Finnhub calendar, BBC, CNBC, and at least some central bank feeds
- Each item should have headline + summary (not just headline)
- Calendar events should be formatted as readable headlines with actual/forecast/previous
- Source metadata JSON should contain the full raw response
- Run dedup check: similar headlines from different sources should be merged (source_count > 1), but directionally opposite headlines should be kept separate

---

## Session 3: Price Ingestion + Capital.com Client

**Goal:** Fetch price data for all 8 instruments and store candles.

**What to build:**
- Integrate existing `capitalcom_client.py` with new project structure
- Fetch H1 candles (200 periods) + current bid/ask for all 8 instruments
- Store in a format the strategy engine and LLM pipeline can consume
- Update instrument config to the 8 instruments we're using (drop commodities except gold, add USD/CAD and EUR/GBP)

**Reuse from old code:** `data/capitalcom_client.py` almost entirely. Update the instrument epic mapping for new instrument list.

**Verify:** Run `python -m backend.cli ingest` (now fetches news AND prices). Check candle data is stored for all 8 instruments.

**Note:** Sessions 2 and 3 could be combined into one if they go quickly. Both are ingestion.

---

## Session 4: LLM Relevance Assessment (Stage 2a)

**Goal:** Given stored headlines, use LLM to assess which instruments each is relevant to.

**What to build:**
- Load the relevance prompt from the prompts table
- Batch all recent headlines (last N hours) into one LLM call
- Parse structured JSON response
- Store relevance assessments in the relevance_assessments table
- Link assessments back to headline IDs

**Reuse from old code:** `signals/llm_client.py` for the Groq API call. Extend it to request structured/JSON output.

**Verify:** Run `python -m backend.cli ingest` then `python -m backend.cli relevance`. Check relevance_assessments table — each headline should have 0 or more instrument mappings with reasoning.

---

## Session 5: LLM Signal Generation (Stage 2b)

**Goal:** For each instrument with relevant headlines, produce a directional signal.

**What to build:**
- Load the signal prompt from the prompts table
- For each instrument: gather all relevant headlines + price context (current price, 24h change, trend)
- Call LLM with the signal prompt
- Parse structured JSON response (direction, confidence, reasoning, key_factors, risk_factors)
- Store in signals table with full metadata

**Reuse from old code:** Price context calculation (SMA trend, daily change) from `streams/news_stream.py`. LLM client.

**Verify:** Run full pipeline so far: `ingest` → `relevance` → `signals`. Check signals table — should have directional signals with reasoning for instruments that had relevant news.

---

## Session 6: Counter-Argument Challenge (Stage 2c)

**Goal:** For each non-neutral signal, run a counter-argument to test its robustness.

**What to build:**
- Load the challenge prompt from the prompts table
- For each signal with direction != neutral: call LLM with the signal's reasoning + market context
- Parse response: counter_argument, alternative_interpretation, conviction_after_challenge, recommendation
- Update the signal record based on recommendation (proceed / reduce_size / reject)
- Store the challenge output linked to the signal

**Verify:** Run: `ingest` → `relevance` → `signals` → `challenge`. Check that signals have been updated — some should have reduced confidence, some may be rejected. Check the challenge data is stored.

---

## Session 7: Strategy Engine (Stage 2 parallel)

**Goal:** Run all traditional strategies on price data and produce signals.

**What to build:**
- Integrate existing strategy implementations (momentum, carry, breakout, mean_reversion)
- Fix confidence calculations where they're broken:
  - Mean reversion: confidence should decrease (not increase) with extremeness
  - Breakout: handle tight ranges without inflating confidence to 1.0
  - Momentum: review the 10x scaling factor
- Each strategy writes a signal to the signals table with source = "strategy:{name}"
- Include strategy parameters and indicator values in the signal metadata

**Reuse from old code:** All strategy files from `strategies/`. Fix the confidence formulas but keep the core logic.

**Verify:** Run `python -m backend.cli strategies`. Check signals table has entries from each strategy for each instrument. Verify confidence scores are sensible (not all 0.01 or all 1.0).

---

## Session 8: Bias Tracker (Stage 3)

**Goal:** Maintain rolling directional bias per instrument, enforce anti-whipsaw rules.

**What to build:**
- Load or create bias_state record per instrument
- Add new signals to contributing list, decay old ones (>N hours, configurable)
- Calculate bias direction (weighted majority) and strength (how one-sided)
- Enforce rules: no conflicting positions, bias alignment required, cooldown on flip
- Output: for each pending signal, approved_by_bias = true/false

**Verify:** Run full pipeline so far, then `python -m backend.cli bias`. Check bias_state table — each instrument should have a direction and strength. Check that signals conflicting with bias are blocked.

---

## Session 9: Risk Manager + Executor (Stage 4 + 5)

**Goal:** Risk-check approved signals, size positions, execute trades on Capital.com.

**What to build:**
- Risk manager: all checks from DATA_FLOW.md (market hours, max positions, daily loss, correlation, position sizing with minimum)
- All parameters from config, not code
- Executor: place orders via Capital.com client with SL/TP
- Full trade recording: assemble the complete trade record JSON (all inputs from all stages)
- Store trade + trade_record in DB
- Reconciliation: check open broker positions, detect SL/TP hits, update trade status

**Reuse from old code:** `risk/risk_manager.py` (restructure but keep logic), `execution/executor.py` (keep broker integration, fix reconciliation).

**Verify:** This is the big one. Run `python -m backend.cli tick` (full pipeline). Check:
- Signals generated from both streams
- Bias checked
- Risk approved/rejected with reasons
- Trade placed on Capital.com (check broker dashboard)
- Trade record in DB with full drill-down data

---

## Session 10: FastAPI Endpoints

**Goal:** API layer serving data to the frontend.

**What to build:**
- All endpoints from DATA_FLOW.md:
  - GET /api/trades/open, /api/trades/closed (with filters: won|lost, instrument, source, days), /api/trades/{id}
  - GET /api/signals/recent (supports ?source=strategy filter for Strategies page)
  - GET /api/llm/activity (headlines grouped by source, relevance assessments, signals — for LLM Analysis page)
  - GET /api/strategies (strategy definitions + recent signals + trade stats per strategy — for Strategies page)
  - GET /api/prompts, PUT /api/prompts/{name} (for editable prompts on LLM page)
  - GET /api/bias (current directional bias per instrument — direction, strength, since, contributing signals count)
  - GET /api/equity (equity snapshots over time for chart)
- **Trade record structure matters:** The `/api/trades/{id}` endpoint must return the complete trade record JSON as defined in DATA_FLOW.md Stage 6 (RECORD). The frontend's narrative timeline drill-down (see DESIGN.md Section 8) maps each chapter directly to a field in this JSON: `headlines_analysed`, `signal`, `challenge`, `price_context_at_signal`, `bias_at_trade`, `risk_decision`, `entry`, `exit`. All fields must be present (null/empty for pending stages).

**Verify:** Run the server, hit each endpoint with curl or a browser. Check that:
- Trade drill-down returns the complete record with all sub-objects populated
- `/api/bias` returns all 8 instruments with direction and strength
- `/api/llm/activity` returns headlines grouped by source
- `/api/trades/closed` respects filter parameters

---

## Session 11: Frontend — Dashboard + Trade Tables

**Goal:** Main dashboard page with open/closed trade tables and drill-down, plus the shared layout (pill nav, account summary panel).

**Read first:** `DESIGN.md` — the complete frontend design system. Every color, font, shadow, spacing, and component spec is defined there. Follow it exactly.

**What to build:**
- New React app with Tailwind, Vite, React Router
- Install Google Fonts: Playfair Display (400–700) + Inter (400–600) + JetBrains Mono (400)
- Set up the design tokens from DESIGN.md Section 2 (Color Palette) as CSS custom properties or Tailwind config
- **Bottom floating pill navigation** (DESIGN.md Section 7): fixed pill bar at bottom of viewport with Dashboard / LLM Analysis / Strategies + settings gear icon. Chevron expands the account summary panel (slides up from behind the pill, z-index layering).
- **Dashboard page** (DESIGN.md Section 9.1):
  - Bias cards: horizontal scrollable row of 8 instrument cards with semantic shadows per direction
  - Open trades table: polls `/api/trades/open` every 30s. Expandable rows revealing the **narrative timeline drill-down** (DESIGN.md Section 8) — two variants for LLM-sourced and strategy-sourced trades, chapters map to trade record JSON fields
  - Closed trades table: fetches `/api/trades/closed` with filter bar (Won/Lost/All toggle, Instrument dropdown, Source dropdown). Same expandable row drill-down.
  - Equity curve: Recharts line chart from `/api/equity`
- Light theme throughout: warm off-white canvas (`#FAFAF9`), semantic colored shadows (not block colors), Playfair Display for headings, Inter for functional text
- All page content must have `padding-bottom: 96px` to clear the floating nav

**Verify:** Run backend + frontend. See trades (if any exist from testing). Verify:
- Pill nav is fixed at bottom, active state highlights correctly, chevron expands account panel
- Open trades poll and update without drift
- Drill-down renders the full narrative timeline with completed/pending chapter states
- Bias cards show correct directional colors
- Light theme matches DESIGN.md — warm off-white canvas, semantic shadows, no pure black text

---

## Session 12: Frontend — LLM + Strategy Pages

**Goal:** LLM analysis page with editable prompts, strategy page with explanations, settings page.

**Read first:** `DESIGN.md` — particularly Sections 9.2 (LLM Analysis), 9.3 (Strategies), and 9.4 (Settings).

**What to build:**
- **LLM Analysis page** (DESIGN.md Section 9.2):
  - Headlines grouped by source in a responsive grid (Finnhub, BBC, central banks, etc.) from `/api/llm/activity`
  - Relevance assessments: headline → instrument tag mappings with reasoning
  - Generated signals: one semantic-shadow card per instrument signal, showing direction, confidence bar, reasoning, challenge result
  - Editable prompts: one expandable section per prompt (Relevance, Signal, Challenge) with JetBrains Mono textarea, Save (primary button) and Reset (ghost button). Loads from `/api/prompts`, saves via `PUT /api/prompts/{name}`
- **Strategies page** (DESIGN.md Section 9.3):
  - One large card per strategy (Momentum, Carry, Breakout, Mean Reversion) from `/api/strategies`
  - Each card: Playfair heading, plain-English description (written for university assessor — what it does, why it works, weaknesses), "How it works" section, parameters display, recent signals mini-table, trade summary stats
- **Settings page** (DESIGN.md Section 9.4):
  - System status: last run, next run, connection status
  - Risk parameters: read-only display of current config values
- All pages follow the same light editorial theme from DESIGN.md — Playfair headings, Inter body, semantic shadows, generous whitespace

**Verify:** 
- LLM page shows pipeline activity with headlines grouped correctly by source
- Edit a prompt, save, verify it persists (reload page, check it's still there)
- Strategy page shows each strategy with readable descriptions and correct parameters
- Navigation between all pages works via the bottom pill nav
- All pages match the DESIGN.md visual language consistently

---

## Session 13: Deploy + GitHub Actions

**Goal:** System running automatically.

**What to build:**
- Update GitHub Actions workflow to call new pipeline entry point
- Verify cron schedule still correct for market hours
- Reset database for fresh experiment
- Deploy frontend (Vercel or wherever it was hosted)
- Run a few manual ticks to confirm everything works end-to-end in production

**Verify:** Trigger a manual workflow run. Check: news ingested, signals generated, bias updated, trade potentially placed, dashboard shows it all.

---

## Session 14: Report

**Goal:** Write and submit the university report.

**Input:** RESEARCH.md (references, design decisions), the working system, screenshots of the dashboard.

**What to write:**
- Introduction: AI in financial trading, historical context, the shift to LLM-based approaches
- Analysis: societal implications — regulation, market stability, accessibility, ethics, democratisation
- Original contribution: system design walkthrough — architecture, LLM pipeline, counter-argument mechanism, bias tracker, comparison framework. Include architecture diagrams, screenshots, code references.
- Conclusion
- References (see RESEARCH.md for academic citations)
- Document AI tool usage as required by brief
- Link to GitHub repo as auxiliary material

**Submit by 17th April.**
