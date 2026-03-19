# Forex Sentinel — Review

**Period:** Last 7 days (2026-03-12 to 2026-03-19)
**Generated:** 2026-03-19 16:03 UTC
**Trigger:** manual

---

## Headlines

- **Overall P&L:** -935.86
- **Total Trades:** 14
- **Best Performer:** strategy (+0.00)
- **Worst Performer:** hybrid:All-equal-majority (-481.71)
- **Biggest Winner:** BCO_USD short (-454.15)
- **Biggest Loser:** BCO_USD short (-454.15)
- **Signals Generated:** 79 (14 traded, 28 rejected, 37 neutral)

---

## Stream Performance

| Stream | P&L | Trades | Win % | Sharpe | Max DD |
|--------|-----|--------|-------|--------|--------|
| news | -454.15 | 6 | 0% | 0.00 | 0.0% |
| strategy | +0.00 | 5 | 0% | 0.00 | 0.0% |
| hybrid:Geopolitical Edge | +0.00 | 0 | 0% | 0.00 | 0.0% |
| hybrid:All-equal-majority | -481.71 | 3 | 0% | 0.00 | 0.0% |

---

## Strategy Breakdown

| Strategy | Signals | Trades | Conv % | P&L | Win % |
|----------|---------|--------|--------|-----|-------|
| momentum | 12 | 2 | 17% | +0.00 | 0% |
| carry | 12 | 2 | 17% | +0.00 | 0% |
| breakout | 12 | 1 | 8% | +0.00 | 0% |
| mean_reversion | 12 | 0 | 0% | +0.00 | 0% |
| volatility_breakout | 12 | 0 | 0% | +0.00 | 0% |

---

## Instrument Analysis

| Instrument | Trades | P&L | Win % |
|------------|--------|-----|-------|
| XAU_USD | 7 | +0.00 | 0% |
| USD_CHF | 1 | +0.00 | 0% |
| USD_JPY | 1 | +0.00 | 0% |
| EUR_USD | 1 | +0.00 | 0% |
| GBP_USD | 1 | +0.00 | 0% |
| BCO_USD | 3 | -935.87 | 0% |

---

## Signal Pipeline

- **Total Signals:** 79 (excl. comparison models)
- **Actionable (non-neutral):** 42
- **Traded:** 14
- **Rejected:** 28
- **Neutral (no action):** 37
- **Conversion Rate:** 33.3%

### Rejection Reasons

| Reason | Count | % of Rejections |
|--------|-------|-----------------|
| Below confidence threshold | 15 | 54% |
| Below threshold | 9 | 32% |
| Max open positions | 4 | 14% |

---

## Rejected Signals

| Time | Stream | Instrument | Dir | Conf | Source | Reason |
|------|--------|------------|-----|------|--------|--------|
| 2026-03-19 15:49 | hybrid:All-equal-majority | BCO_USD | short | 0.54 | hybrid:All-equal-majority | Below threshold (0.5445 < 0.6) |
| 2026-03-19 15:49 | hybrid:All-equal-majority | USD_JPY | short | 0.07 | hybrid:All-equal-majority | Below threshold (0.0665 < 0.6) |
| 2026-03-19 15:49 | hybrid:All-equal-majority | EUR_USD | short | 0.40 | hybrid:All-equal-majority | Below threshold (0.39699999999999996 < 0.6) |
| 2026-03-19 15:49 | hybrid:Geopolitical Edge | XAU_USD | short | 0.50 | hybrid:Geopolitical Edge | Below threshold (0.502 < 0.6) |
| 2026-03-19 15:49 | strategy | XAU_USD | short | 1.00 | breakout | Max open positions (5) reached |
| 2026-03-19 15:49 | strategy | USD_JPY | short | 0.10 | breakout | Below confidence threshold (0.099 < 0.6) |
| 2026-03-19 15:49 | strategy | USD_CHF | long | 0.65 | carry | Max open positions (5) reached |
| 2026-03-19 15:49 | strategy | AUD_USD | short | 0.09 | carry | Below confidence threshold (0.091 < 0.6) |
| 2026-03-19 15:49 | strategy | USD_JPY | long | 0.94 | carry | Max open positions (5) reached |
| 2026-03-19 15:49 | strategy | EUR_USD | short | 0.09 | carry | Below confidence threshold (0.094 < 0.6) |
| 2026-03-19 15:49 | strategy | USD_CHF | long | 0.09 | momentum | Below confidence threshold (0.092 < 0.6) |
| 2026-03-19 15:49 | strategy | AUD_USD | long | 0.02 | momentum | Below confidence threshold (0.019 < 0.6) |
| 2026-03-19 15:49 | strategy | GBP_USD | long | 0.03 | momentum | Below confidence threshold (0.031 < 0.6) |
| 2026-03-19 15:49 | strategy | USD_JPY | short | 0.03 | momentum | Below confidence threshold (0.034 < 0.6) |
| 2026-03-19 15:49 | news | EUR_USD | short | 0.70 | groq/llama-3.3-70b | Max open positions (5) reached |
| 2026-03-19 15:34 | hybrid:All-equal-majority | USD_JPY | short | 0.09 | hybrid:All-equal-majority | Below threshold (0.094 < 0.6) |
| 2026-03-19 15:34 | hybrid:All-equal-majority | GBP_USD | short | 0.32 | hybrid:All-equal-majority | Below threshold (0.316 < 0.6) |
| 2026-03-19 15:34 | hybrid:All-equal-majority | EUR_USD | short | 0.40 | hybrid:All-equal-majority | Below threshold (0.39799999999999996 < 0.6) |
| 2026-03-19 15:34 | hybrid:Geopolitical Edge | XAU_USD | short | 0.47 | hybrid:Geopolitical Edge | Below threshold (0.467 < 0.6) |
| 2026-03-19 15:28 | hybrid:Geopolitical Edge | XAU_USD | short | 0.45 | hybrid:Geopolitical Edge | Below threshold (0.453 < 0.6) |

*Showing 20 of 28 rejected signals. See signals.csv for complete list.*

---

## Trade Analysis

### Best Trade (news)
- **BCO_USD** short — P&L: -454.15 (-331.4999999999998 pips)
- Entry: 96.54300 | Exit: 99.85800
- SL: 98.97857 | TP: 92.88964
- Size: 137.0 | Duration: N/A
- Planned R:R: 1:1.5
  > **Signal:** conf 0.7, source: groq/llama-3.3-70b
  > **Reasoning:** The recent news headlines suggest a potential increase in inflation and a global energy crisis due to the Iran war, which may lead to a decrease in the value of BCO_USD, and the current bearish trend supports this outlook. The Fed's decision to hold interest rates steady also implies a cautious stance, which may further weaken the BCO_USD.
  > **Headlines:** Bank of England 'ready to act' as it warns Iran war 'shock' will push up inflation; How the Iran war may affect your money and bills; US holds interest rates as Iran war triggers inflation fears

### Worst Trade (news)
- **BCO_USD** short — P&L: -454.15 (-331.4999999999998 pips)
- Entry: 96.54300 | Exit: 99.85800
- SL: 98.97857 | TP: 92.88964
- Size: 137.0 | Duration: N/A
- Planned R:R: 1:1.5
  > **Signal:** conf 0.7, source: groq/llama-3.3-70b
  > **Reasoning:** The recent news headlines suggest a potential increase in inflation and a global energy crisis due to the Iran war, which may lead to a decrease in the value of BCO_USD, and the current bearish trend supports this outlook. The Fed's decision to hold interest rates steady also implies a cautious stance, which may further weaken the BCO_USD.
  > **Headlines:** Bank of England 'ready to act' as it warns Iran war 'shock' will push up inflation; How the Iran war may affect your money and bills; US holds interest rates as Iran war triggers inflation fears

### Best Trade (hybrid:All-equal-majority)
- **BCO_USD** short — P&L: -481.71 (-354.20000000000016 pips)
- Entry: 96.29600 | Exit: 99.83800
- SL: 98.74261 | TP: 92.62609
- Size: 136.0 | Duration: N/A
- Planned R:R: 1:1.5
  > **Signal:** conf 0.7404999999999999, source: hybrid:All-equal-majority
  > **Reasoning:** Majority (2/2): short

### Worst Trade (hybrid:All-equal-majority)
- **BCO_USD** short — P&L: -481.71 (-354.20000000000016 pips)
- Entry: 96.29600 | Exit: 99.83800
- SL: 98.74261 | TP: 92.62609
- Size: 136.0 | Duration: N/A
- Planned R:R: 1:1.5
  > **Signal:** conf 0.7404999999999999, source: hybrid:All-equal-majority
  > **Reasoning:** Majority (2/2): short

---

## Complete Trade Log

### hybrid:All-equal-majority

| # | Instrument | Dir | Entry | Exit | SL | TP | Size | P&L | Pips | Status | Duration | R:R Plan |
|---|------------|-----|-------|------|----|----|------|-----|------|--------|----------|----------|
| 1 | XAU_USD | short | 4583.96000 | N/A | 4669.02071 | 4456.36893 | 4.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.92, source: hybrid:All-equal-majority | | | | | | | | | | | |
| | > *Majority (2/3): short* | | | | | | | | | | | |
| 2 | BCO_USD | short | 96.29600 | 99.83800 | 98.74261 | 92.62609 | 136.0 | -481.71 | -354.2 | closed_sl | N/A | 1:1.5 |
| | > **Signal:** conf 0.74, source: hybrid:All-equal-majority | | | | | | | | | | | |
| | > *Majority (2/2): short* | | | | | | | | | | | |
| 3 | XAU_USD | short | 4578.18000 | N/A | 4660.74429 | 4454.33357 | 4.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.88, source: hybrid:All-equal-majority | | | | | | | | | | | |
| | > *Majority (2/3): short* | | | | | | | | | | | |

### news

| # | Instrument | Dir | Entry | Exit | SL | TP | Size | P&L | Pips | Status | Duration | R:R Plan |
|---|------------|-----|-------|------|----|----|------|-----|------|--------|----------|----------|
| 1 | BCO_USD | short | 99.77700 | N/A | 102.47555 | 95.72917 | 124.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.70, source: groq/llama-3.3-70b | | | | | | | | | | | |
| | > *The recent news headlines suggest a potential global energy crisis due to the Iran war, which could lead to increased volatility and downward pressure on BCO_USD, and the Fed's decision to hold rates * | | | | | | | | | | | |
| | > Headlines: Bank ready to raise interest rates if Iran war price 'shock' persists; How the Iran war may affect your money and bills; US holds interest rates as Iran war triggers inflation fears | | | | | | | | | | | |
| 2 | XAU_USD | long | 4582.56000 | N/A | 4497.49929 | 4710.15107 | 4.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.70, source: groq/llama-3.3-70b | | | | | | | | | | | |
| | > *The Iran war is likely to trigger inflation fears and a global energy crisis, which could lead to a flight to safe-haven assets like gold, thus increasing the price of XAU_USD. The recent bearish tren* | | | | | | | | | | | |
| | > Headlines: Bank ready to raise interest rates if Iran war price 'shock' persists; How the Iran war may affect your money and bills; US holds interest rates as Iran war triggers inflation fears | | | | | | | | | | | |
| 3 | EUR_USD | short | 1.15160 | N/A | 1.15488 | 1.14670 | 101869.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.70, source: groq/llama-3.3-70b | | | | | | | | | | | |
| | > *The expectation of a delayed Fed rate cut, as indicated by the hot inflation report, may strengthen the US dollar, putting downward pressure on EUR_USD. This is because higher interest rates in the US* | | | | | | | | | | | |
| | > Headlines: Expectations for the next Fed rate cut get pushed back after hot inflation report | | | | | | | | | | | |
| 4 | BCO_USD | short | 96.54300 | 99.85800 | 98.97857 | 92.88964 | 137.0 | -454.15 | -331.5 | closed_sl | N/A | 1:1.5 |
| | > **Signal:** conf 0.70, source: groq/llama-3.3-70b | | | | | | | | | | | |
| | > *The recent news headlines suggest a potential increase in inflation and a global energy crisis due to the Iran war, which may lead to a decrease in the value of BCO_USD, and the current bearish trend * | | | | | | | | | | | |
| | > Headlines: Bank of England 'ready to act' as it warns Iran war 'shock' will push up inflation; How the Iran war may affect your money and bills; US holds interest rates as Iran war triggers inflation fears | | | | | | | | | | | |
| 5 | XAU_USD | long | 4608.27000 | N/A | 4525.70571 | 4732.11643 | 4.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.70, source: groq/llama-3.3-70b | | | | | | | | | | | |
| | > *The recent news headlines suggest a potential increase in inflation and uncertainty due to the Iran war, which could lead to a flight to safe-haven assets like gold, thus driving up the price of XAU_U* | | | | | | | | | | | |
| | > Headlines: Bank of England 'ready to act' as it warns Iran war 'shock' will push up inflation; How the Iran war may affect your money and bills; US holds interest rates as Iran war triggers inflation fears | | | | | | | | | | | |
| 6 | GBP_USD | short | 1.33688 | N/A | 1.34085 | 1.33093 | 84049.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.60, source: groq/llama-3.3-70b | | | | | | | | | | | |
| | > *The potential for increased inflation due to a war with Iran may lead the Bank of England to raise interest rates, but in the short term, the uncertainty and risk associated with such a geopolitical e* | | | | | | | | | | | |
| | > Headlines: Bank of England 'ready to act' as it warns Iran war 'shock' will push up inflation | | | | | | | | | | | |

### strategy

| # | Instrument | Dir | Entry | Exit | SL | TP | Size | P&L | Pips | Status | Duration | R:R Plan |
|---|------------|-----|-------|------|----|----|------|-----|------|--------|----------|----------|
| 1 | XAU_USD | short | 4568.53000 | N/A | 4653.99679 | 4440.32982 | 4.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.84, source: momentum | | | | | | | | | | | |
| | > *momentum: {'lookback_return': np.float64(-0.09536), 'short_return': np.float64(-0.06585), 'combined_signal': np.float64(-0.08356)}* | | | | | | | | | | | |
| 2 | XAU_USD | short | 4608.52000 | N/A | 4691.08429 | 4484.67357 | 4.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.93, source: breakout | | | | | | | | | | | |
| | > *breakout: {'asian_high': np.float64(5016.23), 'asian_low': np.float64(4805.15), 'asian_range': np.float64(211.08), 'buffer': 1.0}* | | | | | | | | | | | |
| 3 | USD_CHF | long | 0.79075 | N/A | 0.78822 | 0.79455 | 131630.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.65, source: carry | | | | | | | | | | | |
| | > *carry: {'base_rate': 5.25, 'quote_rate': 1.75, 'differential': 3.5, 'vol_penalty': np.float64(0.051)}* | | | | | | | | | | | |
| 4 | USD_JPY | long | 158.39400 | N/A | 157.98696 | 159.00455 | 819.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.94, source: carry | | | | | | | | | | | |
| | > *carry: {'base_rate': 5.25, 'quote_rate': 0.1, 'differential': 5.15, 'vol_penalty': np.float64(0.059)}* | | | | | | | | | | | |
| 5 | XAU_USD | short | 4612.92000 | N/A | 4695.48429 | 4489.07357 | 4.0 | open | open | open | N/A | 1:1.5 |
| | > **Signal:** conf 0.75, source: momentum | | | | | | | | | | | |
| | > *momentum: {'lookback_return': np.float64(-0.08657), 'short_return': np.float64(-0.05678), 'combined_signal': np.float64(-0.07465)}* | | | | | | | | | | | |

---

## Comparison Model Performance

| Instrument | Primary Dir | Primary Conf | Comparison Dir | Comparison Conf | Source |
|------------|-------------|--------------|----------------|-----------------|--------|
| BCO_USD | short | 0.70 | long | 0.75 | mistral/mistral-small |
| BCO_USD | short | 0.70 | short | 0.85 | mistral/mistral-small |
| EUR_USD | short | 0.70 | short | 0.75 | mistral/mistral-small |
| EUR_USD | short | 0.70 | short | 0.75 | mistral/mistral-small |
| GBP_USD | short | 0.60 | long | 0.75 | mistral/mistral-small |
| XAU_USD | long | 0.70 | short | 0.85 | mistral/mistral-small |
| XAU_USD | long | 0.70 | short | 0.85 | mistral/mistral-small |

---

## Questions for Review

- 'Below confidence threshold' accounts for 15/28 rejections — review the related parameters?
- Comparison model disagreed with primary on 4/7 signals — investigate divergence.
