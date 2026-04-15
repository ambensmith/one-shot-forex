# Research Notes

Collected during the build for use in the report.

---

## Free Data Sources Available

### News APIs (Recommended)
- **Finnhub** — best free option. 50-60 req/min, news + sentiment + economic calendar. Free API key. https://finnhub.io
- **Financial Modeling Prep (FMP)** — forex news API, 250 calls/day free. https://site.financialmodelingprep.com
- **Alpha Vantage** — news with AI sentiment scores, but only 25 req/day free. https://www.alphavantage.co
- **NewsAPI.org** — 100 queries/day but 24hr delay on free tier. Broad, not finance-specific.

### RSS Feeds (Free, No Limits)
- **Central banks (critical for forex):** ECB (ecb.europa.eu/home/html/rss.en.html), Fed (federalreserve.gov/feeds/), BoE (bankofengland.co.uk/rss/news), BoJ (boj.or.jp/en/rss/whatsnew.xml), SNB (snb.ch/public/en/rss/news), RBA (rba.gov.au/rss/), BoC (bankofcanada.ca/rates/notifications/)
- **Financial news:** BBC Business (in use), CNBC (in use), Bloomberg (feeds.bloomberg.com/markets/news.rss), Investing.com (investing.com/webmaster-tools/rss), Reuters via RSS.app

### Economic Calendar
- **Finnhub** (included in main API) — best free option
- **ForexFactory via faireconomy.media** (currently in use) — still works
- **FRED** (Federal Reserve Economic Data) — unlimited, free key, excellent for USD pairs. https://fred.stlouisfed.org/docs/api/fred/

### Currently Used — Assessment
- BBC/CNBC RSS: still good, keep
- GDELT: 55% accuracy, noisy. Replace with Finnhub
- ForexFactory calendar: keep as backup, add Finnhub calendar as primary

### Decision: Add Finnhub as primary news + calendar source, add central bank RSS feeds, keep BBC/CNBC, drop GDELT.

---

## Existing Open Source Projects

### Most Relevant
- **TradingAgents** (github.com/TauricResearch/TradingAgents) — multi-agent LLM framework with 7 specialised roles (fundamentals analyst, sentiment analyst, news analyst, technical analyst, researcher, trader, risk manager). Built with LangGraph. Actively maintained. Paper: arXiv:2412.20138
- **FinGPT** (github.com/AI4Finance-Foundation/FinGPT) — financial LLM with data-centric approach, domain-specific fine-tuning, sentiment classification. 8% improvement over baseline. Paper: arXiv:2306.06031
- **FinRL** (github.com/AI4Finance-Foundation/FinRL) — deep RL library for automated trading. DQN, DDPG, PPO, SAC algorithms. NeurIPS 2020. Comprehensive framework.
- **LLM-Enhanced-Trading** (github.com/Ronitt272/LLM-Enhanced-Trading) — sentiment-driven system using FinGPT + 4 technical strategies (SMA crossover, RSI, stochastic, breakouts). Closest to our architecture.
- **Freqtrade** (github.com/freqtrade/freqtrade) — production-ready crypto trading bot with ML optimisation. Large community.
- **Tickermind** (github.com/DarmorGamz/Tickermind) — local LLM sentiment analysis, McMaster capstone 2025. Privacy-focused.

### Key Models
- **FinBERT** (github.com/ProsusAI/finBERT) — BERT fine-tuned on financial text. 0.88 accuracy, outperforms GPT-4o zero-shot on sentiment. Widely used in industry.

### Key Insight
TradingAgents' multi-agent approach (separate analyst roles) is the most architecturally interesting. Our two-stream approach (LLM vs traditional) is a simpler but valid comparison framework. The research validates that combining news/sentiment with technical strategies is the standard approach.

---

## Best Practices for LLM Signal Pipelines

### Multi-Stage Prompt Design
- Decompose into atomic steps (relevance → signal generation)
- Use structured output (JSON mode or constrained decoding) for machine-readable outputs between stages
- JSON mode causes 10-15% performance degradation on reasoning vs free-form + conversion
- Recommendation: structured output with constrained decoding for both stages

### Confidence Calibration (Critical)
- LLM self-reported confidence is systematically overconfident and unreliable
- Professional systems don't use raw LLM confidence outputs
- Methods: isotonic regression, holdout validation calibration, SEP framework
- For comparing LLM vs strategy confidence: separately calibrate each source, dynamically weight based on recent performance
- Key insight: you need historical data to calibrate. Initial deployment should collect data without acting on confidence scores directly.

### Signal Aggregation
- **Recommended approach:** Feed all relevant headlines to LLM at once for unified synthesis (not 1:1 mapping)
- Batch headlines by time window (e.g., last 4 hours per instrument)
- Include conflicting signals in reasoning output for audit trail
- Weight by number of supporting headlines and source credibility

### Prompt Engineering for Finance
- Domain Knowledge Chain-of-Thought: identify financial concepts first, then reason about instrument impact
- Specificity: "Given this Fed policy change, impact on gold relative to USD? Consider: inflation expectations, real rates, dollar strength"
- Zero-shot works well for financial sentiment — no fine-tuning needed
- Don't ask for probabilities directly (LLMs hallucinate numbers)

### Editable Prompts
- Database-backed storage preferred for auditability
- Version control, template variables ({instrument}, {current_price})
- For our system: store prompts in database with version tracking, expose via API for frontend editing

### Trade Recording / Audit Trail
- Record everything: headlines, relevance scores, LLM reasoning, price context, risk calculations, execution details
- Immutable event log architecture
- Timestamp everything precisely
- Append-only — never edit historical records

---

## Academic References for Report

- TradingAgents Framework: arXiv:2412.20138
- FinGPT Open-Source Financial LLMs: arXiv:2306.06031
- FinBERT Sentiment Analysis: arXiv:2306.02136
- News-Aware Direct Reinforcement Trading: arXiv:2510.19173
- Language Model Guided RL in Quant Trading: arXiv:2508.02366
- RL Framework for Quantitative Trading: arXiv:2411.07585
- Large Language Models in Equity Markets (survey): Frontiers in AI 2025
- When Valid Signals Fail (regime boundaries): arXiv:2604.10996
- End-to-End LLM Enhanced Trading: arXiv:2502.01574
- Hierarchical Signal-to-Policy Learning: MDPI Finance 14/3/75
- Machine Learning Framework for Algorithmic Trading: MDPI 2813-0324/12/1/12

---

## Architecture Learnings from Open Source Projects

### TradingAgents (50K stars, arXiv:2412.20138)
- Multi-agent framework with 7 specialised LLM roles (analysts, researchers, trader, risk manager)
- **Key pattern adopted:** structured JSON output at every stage — prevents context loss in pipelines
- **Key pattern adopted:** separation of analysis → synthesis → execution as distinct stages
- **Key pattern adopted (lightweight version):** bull/bear debate mechanism — simplified to a single counter-argument challenge call per signal. LLM argues against the proposed trade; can confirm, reduce size, or reject. Addresses overconfidence without full multi-agent debate overhead.
- **Key pattern adopted:** single approval gate (risk manager) before execution
- Built with LangGraph, supports multiple LLM providers via factory pattern

### LLM-Enhanced-Trading (arXiv:2502.01574)
- Closest to our architecture: FinGPT sentiment + 4 technical strategies
- **Key pattern adopted:** weight signals by confidence, reduce position on disagreement
- Sharpe improvement from 0.34 → 3.47 on TSLA with sentiment integration
- Validates our two-stream approach (LLM + traditional strategies)

### FinGPT (arXiv:2306.06031)
- Financial LLM with LoRA fine-tuning, data-centric approach
- 8% improvement over baseline with enhanced sentiment
- Five-layer architecture: data source → data engineering → LLMs → task → application
- **Key insight:** domain-specific training matters, but zero-shot with good prompting works for our use case

### Design Principles Extracted
- Every stage produces structured JSON, not free-form text
- Each stage has one job and produces a structured handoff to the next
- Confidence scores on all signals, weighted aggregation (not equal averaging)
- Explicit handling of disagreement between signal sources
- Approval gate before execution
- Full capture of all available data (not just headlines — summaries, content, metadata)

---

## Key Design Decisions (for report contribution section)

1. **Two-stream comparison** (LLM vs traditional) rather than single combined approach — enables direct evaluation of LLM effectiveness. Validated by LLM-Enhanced-Trading's similar architecture.
2. **Multi-stage prompts** rather than single prompt — better relevance filtering, more auditable. Follows TradingAgents' principle of "each stage has one job."
3. **Structured JSON output** at every pipeline stage — adopted from TradingAgents. Prevents context loss, enables reliable parsing, supports audit trail.
4. **Editable prompts** — enables iteration without code changes, important for practical systems
5. **Full data capture** — store everything available from each source (headline, summary, content, metadata, sentiment), not just headlines. Let the LLM use maximum context.
6. **Full trade recording** — every input stored as structured data, renderable as markdown. Enables post-hoc analysis.
7. **Free-tier only** — demonstrates accessibility, relevant to democratisation argument
8. **Separate confidence calibration** per source rather than raw scores — addresses the fundamental problem of incomparable confidence metrics
