# Forex Sentinel — System Context

This file is auto-generated from the current system configuration.
It provides full context for Cowork review sessions.

---

## Active Streams

### News Stream
- **Capital:** 33333
- **Instruments:** EUR_USD, GBP_USD, USD_JPY, XAU_USD, BCO_USD
- **Primary Model:** groq/llama-3.3-70b
- **Min Confidence:** 0.6

### Strategy Stream
- **Capital:** 33333
- **Instruments:** EUR_USD, GBP_USD, USD_JPY, USD_CHF, AUD_USD, XAU_USD
- **Strategies:**
  - momentum [ON] — params: {'lookback_months': 12, 'rebalance_frequency': 'weekly'}
  - carry [ON] — params: {'rate_data': 'manual'}
  - breakout [ON] — params: {'asian_start': '22:00', 'asian_end': '06:00', 'breakout_buffer_pips': 10}
  - mean_reversion [ON] — params: {'bb_period': 20, 'bb_std': 2.0, 'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70}
  - volatility_breakout [ON] — params: {'atr_period': 14, 'atr_contraction_threshold': 0.7, 'breakout_atr_multiplier': 1.0}

### Active Hybrids
- **Geopolitical Edge**: weighted combiner
  Instruments: EUR_USD, GBP_USD, XAU_USD
  - momentum (weight: 0.6, must_participate: False)
  - mean_reversion (weight: 0.4, must_participate: False)
- **All-equal-majority**: majority combiner
  Instruments: EUR_USD, GBP_USD, USD_JPY, XAU_USD, BCO_USD
  - news (weight: 0.5, must_participate: False)
  - momentum (weight: 0.5, must_participate: False)
  - carry (weight: 0.5, must_participate: False)
  - breakout (weight: 0.5, must_participate: False)
  - mean_reversion (weight: 0.5, must_participate: False)
  - volatility_breakout (weight: 0.5, must_participate: False)

---

## Risk Settings

- Max risk per trade: 1.0%
- Max open positions per stream: 5
- Max daily loss per stream: 3.0%
- Max correlated positions: 2
- Default R:R ratio: 1.5
- Stop loss method: atr

---

## What I Want From Reviews

- Which stream is performing best and why
- Which instruments are profitable vs loss-making
- Whether the LLM reasoning was correct on winning AND losing trades
- Suggestions for parameter changes backed by the data
- Whether any strategy should be enabled/disabled
- Correlation between streams — are they taking the same trades?
