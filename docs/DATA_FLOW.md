# End-to-End Data Flow

This is the contract between all layers of the system. Each stage defines what it consumes and produces.

---

## Overview

```
INGEST → ANALYSE → BIAS → DECIDE → EXECUTE → RECORD → DISPLAY
```

Two parallel pipelines feed into a directional bias tracker, then a shared execution layer:

```
News Sources ──→ LLM Pipeline ──→ LLM Signals ──┐
                                                  ├──→ Bias Tracker ──→ Risk Manager ──→ Executor ──→ Broker
Price Data ────→ Strategy Engine ─→ Strategy Signals ┘        │
                                                          Database ──→ API ──→ Dashboard
```

---

## Stage 1: INGEST

### News Ingestion

**Sources:**
- Finnhub news API (primary — forex news + sentiment)
- Finnhub economic calendar
- BBC Business RSS
- CNBC Business RSS
- Central bank RSS feeds (ECB, Fed, BoE, BoJ, SNB, RBA, BoC)

**Output per news item (capture everything available, not just headlines):**
```json
{
  "id": "uuid",
  "headline": "ECB signals pause in rate hiking cycle",
  "summary": "The European Central Bank indicated today that...",
  "content": "Full article text if available from source, null otherwise",
  "source": "finnhub|bbc|cnbc|ecb|fed|...",
  "source_url": "https://...",
  "image_url": "https://...",
  "category": "central_bank|macro|geopolitical|...",
  "published_at": "2026-04-14T10:00:00Z",
  "ingested_at": "2026-04-14T10:05:00Z",
  "sentiment_score": 0.65,  // from Finnhub if available, null otherwise
  "source_metadata": { ... }  // full original payload from API/RSS for audit
}
```

Each source provides different fields — Finnhub gives sentiment scores and categories, RSS gives descriptions and sometimes full content, central bank feeds give structured policy statements. We store **everything available** and let the LLM use as much context as the prompt window allows.

**Deduplication:** Token overlap matching (raised to 80% threshold, with directional word protection — "raise" and "cut" prevent dedup even if other tokens overlap).

### Price Ingestion

**Source:** Capital.com API (already working)

**Output per instrument per tick:**
```json
{
  "instrument": "EUR_USD",
  "candles": [ ... ],  // H1 OHLCV, 200 periods
  "current_price": 1.0852,
  "bid": 1.0851,
  "ask": 1.0853,
  "daily_change_pct": 0.23,
  "fetched_at": "2026-04-14T10:05:00Z"
}
```

---

## Stage 2: ANALYSE (LLM Pipeline)

Three-stage prompt pipeline. All prompts are editable and stored in the database.

### Stage 2a: Relevance Assessment

**Input:** All deduplicated headlines from the last N hours (configurable, default 4).

**Prompt (editable, stored in DB):**
```
You are a forex market analyst. Given these recent headlines, identify which 
of our instruments each headline is relevant to, and why.

Instruments: EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, EUR/GBP, XAU/USD

News items (headline + summary/content where available):
{news_items_formatted}

For each item, respond with:
- relevant_instruments: list of instrument codes
- relevance_reasoning: why this affects each instrument
- Skip items that are not relevant to any instrument.
```

**Output:**
```json
{
  "assessments": [
    {
      "headline_id": "uuid",
      "headline": "ECB signals pause in rate hiking cycle",
      "relevant_instruments": ["EUR_USD", "EUR_GBP"],
      "relevance_reasoning": "ECB policy directly affects EUR. Pause suggests EUR weakness vs USD and GBP."
    }
  ],
  "prompt_version": "relevance_v1",
  "model": "groq/llama-3.3-70b",
  "raw_response": "...",  // full LLM response for audit
  "timestamp": "2026-04-14T10:06:00Z"
}
```

**Key:** All headlines are processed in one LLM call (batched). The LLM decides relevance, not a keyword mapper.

### Stage 2b: Signal Generation (per instrument)

**Input:** All headlines assessed as relevant to this instrument + price context.

**Prompt (editable, stored in DB):**
```
You are a forex trading analyst. Based on the following recent news and market 
context for {instrument}, provide a trading signal.

Recent relevant news (headlines, summaries, and content where available):
{relevant_news_with_reasoning}

Market context:
- Current price: {current_price}
- 24h change: {daily_change_pct}%
- Recent trend: {trend_description}

Reason through:
1. What fundamental factors are these headlines affecting?
2. What is the likely directional impact on {instrument}?
3. How strong is the evidence (multiple confirming sources, or single ambiguous headline)?
4. What could go wrong with this view?

Respond with:
- direction: "long" | "short" | "neutral"
- confidence: 0.0-1.0 (how strong is the evidence, not how certain you are)
- reasoning: your full analysis
- key_factors: list of the main drivers
- risk_factors: what could invalidate this signal
```

**Output:**
```json
{
  "instrument": "EUR_USD",
  "direction": "short",
  "confidence": 0.72,
  "reasoning": "ECB pause signal from 3 sources suggests...",
  "key_factors": ["ECB policy pause", "rate differential narrowing"],
  "risk_factors": ["Fed could also pause", "headline could be misinterpreted"],
  "headlines_used": ["uuid1", "uuid2", "uuid3"],
  "prompt_version": "signal_v1",
  "model": "groq/llama-3.3-70b",
  "raw_response": "...",
  "price_context": { "current_price": 1.0852, "daily_change_pct": 0.23 },
  "timestamp": "2026-04-14T10:07:00Z"
}
```

### Stage 2c: Counter-Argument Challenge (per signal)

Lightweight adaptation of TradingAgents' bull/bear debate mechanism. Only runs for non-neutral signals from Stage 2b. One additional LLM call per signal — at most 8 per tick (one per instrument).

**Input:** The signal from Stage 2b (direction, reasoning, key factors, risk factors) + the same market context.

**Prompt (editable, stored in DB):**
```
You are a senior risk analyst reviewing a proposed trade. Your job is to argue 
against this position and find weaknesses in the reasoning.

Proposed trade: {direction} {instrument}
Signal reasoning: {reasoning}
Key factors cited: {key_factors}
Risk factors already identified: {risk_factors}

Market context:
- Current price: {current_price}
- 24h change: {daily_change_pct}%
- Recent trend: {trend_description}

Challenge this trade:
1. What is the strongest argument against this direction?
2. Are there alternative interpretations of the same news?
3. What market conditions could make this trade fail quickly?
4. How convincing is the original reasoning on a scale of 0.0-1.0?

Respond with:
- counter_argument: your strongest case against the trade
- alternative_interpretation: a different reading of the same evidence
- conviction_after_challenge: 0.0-1.0 (how strong does the original signal look after scrutiny?)
- recommendation: "proceed" | "reduce_size" | "reject"
```

**Output:**
```json
{
  "signal_id": "uuid",
  "instrument": "EUR_USD",
  "original_direction": "short",
  "original_confidence": 0.72,
  "counter_argument": "ECB pause was already priced in last week. EUR has been range-bound suggesting market has digested this. Fed is also likely to pause, neutralising any rate differential shift.",
  "alternative_interpretation": "The pause could be seen as ECB being cautious about overtightening — actually EUR-positive if it signals soft landing confidence.",
  "conviction_after_challenge": 0.45,
  "recommendation": "reduce_size",
  "prompt_version": "challenge_v1",
  "model": "groq/llama-3.3-70b",
  "raw_response": "...",
  "timestamp": "2026-04-14T10:07:30Z"
}
```

**How it affects the trade:**
- `"proceed"` → signal passes to risk manager at original confidence
- `"reduce_size"` → signal passes but confidence is replaced with `conviction_after_challenge` (lower confidence → smaller position via risk manager's sizing formula)
- `"reject"` → signal is killed before reaching risk manager

**Why this works:** LLMs are bad at self-assessing confidence but good at critiquing arguments. The counter-argument quality is a more meaningful filter than a self-reported confidence number. This directly addresses the overconfidence problem identified in the existing system.

---

## Stage 2 (parallel): ANALYSE (Strategy Engine)

Each strategy runs independently on price data. No LLM involved.

**Input:** OHLCV candles for each instrument.

**Output per strategy per instrument:**
```json
{
  "instrument": "EUR_USD",
  "strategy": "momentum",
  "direction": "long",
  "confidence": 0.65,
  "reasoning": "12-month return +3.2%, 1-month return +0.8%. Combined signal positive.",
  "parameters": { "lookback_months": 12, "short_window": 1 },
  "entry_price": 1.0852,
  "suggested_stop": 1.0790,
  "timestamp": "2026-04-14T10:07:00Z"
}
```

**Confidence calibration (both streams):** For now, use a configurable minimum threshold per stream. Architecture supports adding proper calibration later once we have enough historical data.

---

## Stage 3: DIRECTIONAL BIAS TRACKER

Each instrument maintains a persistent directional bias that builds over multiple ticks. This prevents whipsaw trading (going long one hour, short the next) and gives a rolling view of "where do we think this instrument is heading?"

### How it works

**State per instrument (persisted in DB):**
```json
{
  "instrument": "EUR_USD",
  "current_bias": "bearish",
  "bias_strength": 0.65,
  "bias_since": "2026-04-14T06:00:00Z",
  "contributing_signals": [
    { "tick": "2026-04-14T06:00Z", "source": "llm", "direction": "short", "confidence": 0.55 },
    { "tick": "2026-04-14T07:00Z", "source": "strategy:momentum", "direction": "short", "confidence": 0.62 },
    { "tick": "2026-04-14T08:00Z", "source": "llm", "direction": "short", "confidence": 0.70 },
    { "tick": "2026-04-14T09:00Z", "source": "strategy:mean_reversion", "direction": "long", "confidence": 0.40 },
    { "tick": "2026-04-14T10:00Z", "source": "llm", "direction": "short", "confidence": 0.45 }
  ],
  "updated_at": "2026-04-14T10:07:00Z"
}
```

**Update logic each tick:**
1. New signals (LLM + strategy) for this instrument are added to the contributing_signals list
2. Older signals decay — signals from >N hours ago (configurable, default 12) are dropped
3. Bias direction = weighted majority of recent signals (more recent signals weighted higher)
4. Bias strength = how one-sided the recent signals are (all agreeing = strong, mixed = weak)

**Rules enforced:**

1. **No conflicting positions:** If you have an open trade on an instrument, you cannot open a trade in the opposite direction. The existing trade must close first (SL, TP, or manual close).

2. **Bias alignment required:** New trades must align with the current bias direction. A single bullish tick cannot open a long if the rolling bias is bearish. The bias must first flip (which requires sustained evidence over multiple ticks).

3. **Bias flip cooldown:** When bias direction changes, a configurable cooldown period (default 2 ticks / 2 hours) must pass before any new trade in the new direction. This prevents acting on noise.

4. **Open trades are hands-off:** Once a trade is open, it is managed by its stop loss and take profit only. The system does not second-guess or early-close positions. The bias tracker only governs new entries, not existing positions.

**What the bias tracker outputs for each signal:**
```json
{
  "signal_id": "uuid",
  "instrument": "EUR_USD",
  "signal_direction": "short",
  "bias_direction": "bearish",
  "bias_strength": 0.65,
  "bias_aligned": true,
  "has_conflicting_position": false,
  "in_cooldown": false,
  "approved_by_bias": true,
  "open_position_review": null
}
```

Only signals where `approved_by_bias = true` proceed to the risk manager.

### Dashboard display

The bias per instrument is shown on the dashboard — a simple indicator per pair showing current direction and strength. This gives you the "aggregated idea of direction" at a glance.

---

## Stage 4: DECIDE (Risk Manager)

**Input:** All signals that pass minimum confidence threshold AND are approved by the bias tracker.

**Checks (in order):**
1. Is market open?
2. Max open positions per stream (configurable, default 5)
3. Daily loss limit (configurable, default 3%)
4. Correlation limit (configurable groups, max 2 per group)
5. Position sizing: if `fixed_position_size` is set in config, use that value directly (bypasses formula). Otherwise: units = (equity × risk_pct) / stop_distance. Default: 1 unit (demo/data-collection mode).
6. Minimum position size check (configurable, default 1 unit — prevents rounding to 0)

**Demo/testing defaults:** leverage=0, fixed_position_size=1, default_rr_ratio=2.0. This keeps orders minimal and focuses on signal quality over position sizing. Trade size does not affect whether a signal is correct — a 1-unit trade hits TP or SL the same as a 5,000-unit trade.

**Output:**
```json
{
  "signal_id": "uuid",
  "approved": true,
  "position_size": 1,
  "stop_loss": 1.0790,
  "take_profit": 1.0943,
  "risk_amount": 50.00,
  "rejection_reason": null,  // or "daily_loss_limit_exceeded" etc.
  "checks_passed": ["market_open", "max_positions", "daily_loss", "correlation", "position_size"],
  "timestamp": "2026-04-14T10:08:00Z"
}
```

**All risk parameters in config, not code.** Correlation groups, thresholds, limits — all configurable.

---

## Stage 5: EXECUTE

**Input:** Approved signals with position size, SL, TP.

**Action:** Place order via Capital.com API (existing client).

**Output:**
```json
{
  "trade_id": "uuid",
  "broker_deal_id": "DEAL-12345",
  "instrument": "EUR_USD",
  "direction": "short",
  "size": 1000,
  "entry_price": 1.0852,
  "stop_loss": 1.0790,
  "take_profit": 1.0943,
  "status": "open",
  "source": "llm",  // or "strategy:momentum"
  "signal_id": "uuid",
  "opened_at": "2026-04-14T10:08:30Z"
}
```

---

## Stage 6: RECORD (Full Trade Recording)

Every trade gets a complete record of all inputs, stored as structured JSON and renderable as markdown.

**Trade record structure:**
```json
{
  "trade_id": "uuid",
  "instrument": "EUR_USD",
  "direction": "short",
  "source": "llm",
  "status": "open|closed_tp|closed_sl|closed_manual",
  
  "entry": {
    "price": 1.0852,
    "size": 1000,
    "stop_loss": 1.0790,
    "take_profit": 1.0943,
    "opened_at": "2026-04-14T10:08:30Z",
    "broker_deal_id": "DEAL-12345"
  },
  
  "exit": {
    "price": 1.0790,
    "pnl": -6.20,
    "pnl_pips": -62,
    "closed_at": "2026-04-14T14:30:00Z",
    "close_reason": "stop_loss_hit"
  },
  
  "signal": {
    "direction": "short",
    "confidence": 0.72,
    "reasoning": "ECB pause signal from 3 sources suggests...",
    "key_factors": ["ECB policy pause", "rate differential narrowing"],
    "risk_factors": ["Fed could also pause"],
    "prompt_version": "signal_v1",
    "model": "groq/llama-3.3-70b"
  },
  
  "challenge": {
    "counter_argument": "ECB pause was already priced in last week...",
    "alternative_interpretation": "Pause could signal soft landing confidence — EUR-positive",
    "conviction_after_challenge": 0.45,
    "recommendation": "reduce_size",
    "prompt_version": "challenge_v1",
    "model": "groq/llama-3.3-70b"
  },
  
  "headlines_analysed": [
    {
      "headline": "ECB signals pause in rate hiking cycle",
      "source": "finnhub",
      "published_at": "2026-04-14T09:30:00Z",
      "relevance_reasoning": "ECB policy directly affects EUR"
    }
  ],
  
  "price_context_at_signal": {
    "current_price": 1.0852,
    "daily_change_pct": 0.23,
    "trend": "ranging"
  },
  
  "bias_at_trade": {
    "direction": "bearish",
    "strength": 0.65,
    "bias_since": "2026-04-14T06:00:00Z",
    "contributing_signals_count": 5,
    "aligned": true
  },
  
  "risk_decision": {
    "approved": true,
    "position_size": 1,
    "risk_amount": 50.00,
    "checks_passed": ["market_open", "max_positions", "daily_loss", "correlation", "position_size"]
  }
}
```

**For strategy-sourced trades**, the `signal` block contains strategy name, parameters, indicator values, and reasoning instead of LLM fields. The `headlines_analysed` block is absent.

**Markdown rendering:** The frontend renders this JSON as clean, readable markdown in the trade drill-down. Template:

```markdown
# Trade: SHORT EUR/USD

## Signal
**Source:** LLM (groq/llama-3.3-70b, prompt signal_v1)
**Direction:** Short | **Confidence:** 0.72
**Generated:** 2026-04-14 10:07 UTC

### Reasoning
ECB pause signal from 3 sources suggests...

### Key Factors
- ECB policy pause
- Rate differential narrowing

### Risk Factors
- Fed could also pause
- Headline could be misinterpreted

## Counter-Argument Challenge
**Recommendation:** Reduce size | **Conviction after challenge:** 0.45

### Counter-Argument
ECB pause was already priced in last week. EUR has been range-bound suggesting 
market has digested this. Fed is also likely to pause, neutralising any rate 
differential shift.

### Alternative Interpretation
The pause could be seen as ECB being cautious about overtightening — actually 
EUR-positive if it signals soft landing confidence.

## Directional Bias
**Current bias:** Bearish (strength 0.65) since 06:00 UTC
**Signal aligned:** Yes
**Contributing signals:** 5 over last 4 hours (4 bearish, 1 bullish)

## Headlines Analysed
1. **"ECB signals pause in rate hiking cycle"** (Finnhub, 09:30 UTC)
   Relevance: ECB policy directly affects EUR

## Market Context at Signal Time
- Price: 1.0852
- 24h change: +0.23%
- Trend: Ranging

## Risk Decision
- Position size: 1,000 units
- Risk amount: £50.00
- Stop loss: 1.0790 | Take profit: 1.0943
- All checks passed

## Entry
- Price: 1.0852
- Opened: 2026-04-14 10:08 UTC
- Broker ref: DEAL-12345

## Exit
- Price: 1.0790
- P&L: -£6.20 (-62 pips)
- Closed: 2026-04-14 14:30 UTC
- Reason: Stop loss hit
```

---

## Stage 7: DISPLAY (Dashboard)

### API Endpoints

The backend serves JSON to the frontend via FastAPI:

- `GET /api/trades/open` — current open trades with latest prices
- `GET /api/trades/closed?filter=won|lost&instrument=EUR_USD&source=llm&days=7` — closed trades with filters
- `GET /api/trades/{id}` — full trade record (the complete JSON above)
- `GET /api/signals/recent` — recent signals from both streams
- `GET /api/llm/activity` — LLM pipeline activity (headlines, relevance, signals)
- `GET /api/strategies` — strategy definitions + recent activity
- `GET /api/prompts` — current prompts with versions
- `PUT /api/prompts/{name}` — update a prompt
- `GET /api/bias` — current directional bias per instrument (direction, strength, since, contributing signals)
- `GET /api/equity` — equity snapshots over time

### Frontend Pages

**Dashboard / Trades:**
- Open trades table (polls /api/trades/open on interval, never drifts)
- Closed trades table (calls /api/trades/closed with filters)
- Click any trade → expandable panel with rendered markdown from /api/trades/{id}

**LLM Analysis:**
- Recent headlines ingested, grouped by source
- Relevance assessments (which headlines matched which instruments)
- Signals generated with reasoning
- Editable prompts (loads from /api/prompts, saves via PUT)

**Strategies:**
- Card per strategy with name, description, how it works
- Recent signals and trades per strategy
- Parameters shown

---

## Database Schema (Key Tables)

```sql
-- Raw headlines as ingested
headlines (id, headline, summary, source, source_url, published_at, ingested_at, sentiment_score, raw_data)

-- LLM relevance assessments  
relevance_assessments (id, headline_id, instrument, reasoning, prompt_version, model, run_id, created_at)

-- Signals from both streams
signals (id, instrument, source, direction, confidence, reasoning, key_factors, risk_factors, 
         prompt_version, model, headlines_used, price_context, run_id, created_at)

-- Trades
trades (id, instrument, direction, source, signal_id, 
        entry_price, exit_price, size, stop_loss, take_profit,
        pnl, pnl_pips, status, broker_deal_id,
        risk_decision, opened_at, closed_at)

-- Full trade records (the complete JSON for drill-down)
trade_records (trade_id, full_record)

-- Directional bias state per instrument
bias_state (id, instrument, direction, strength, bias_since, contributing_signals, updated_at)

-- Editable prompts
prompts (id, name, content, version, created_at, is_active)

-- Equity snapshots
equity_snapshots (id, stream, equity, timestamp)

-- Run log
runs (id, started_at, completed_at, signals_generated, trades_opened, trades_closed, config_snapshot)
```

---

## Tick Cycle (What Happens Each Hour)

```
1. Check market hours → skip if closed
2. Ingest news (Finnhub + RSS feeds) → store news items (full content)
3. Ingest prices (Capital.com) → store candles
4. LLM Stage 2a: relevance assessment on new news items → store assessments
5. LLM Stage 2b: signal generation per instrument (where relevant news exists) → store signals
6. LLM Stage 2c: counter-argument challenge on non-neutral signals → update confidence or reject
7. Strategy engine (parallel with 4-6): run all strategies per instrument → store signals
8. Bias tracker: update directional bias per instrument, check alignment, block conflicting trades
9. Risk manager: evaluate all bias-approved signals → approve/reject
10. Executor: place approved trades → store trades + full trade records
11. Reconcile: check open trades against broker positions (detect SL/TP hits, sync status)
12. Record equity snapshot
13. Export updated data for dashboard
```
