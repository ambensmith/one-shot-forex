/**
 * Glossary — single source of truth for all forex/trading term definitions.
 * Used by HelpTooltip component throughout the UI.
 *
 * Each entry has:
 *   term: display name
 *   definition: plain-English explanation (1-2 sentences)
 *   hint: optional "good range" or practical guidance
 */

const GLOSSARY = {
  sharpe_ratio: {
    term: 'Sharpe Ratio',
    definition: 'Measures return per unit of risk. Higher means better risk-adjusted performance.',
    hint: '> 1.0 is good, > 2.0 is excellent, < 0 means losing money.',
  },
  max_drawdown: {
    term: 'Max Drawdown',
    definition: 'The largest peak-to-trough drop in your portfolio value. Shows the worst-case loss you experienced before recovery.',
    hint: '< 10% is conservative, > 20% is aggressive.',
  },
  atr: {
    term: 'ATR (Average True Range)',
    definition: 'Measures how much a currency pair moves on average per time period. Used to set dynamic stop losses that adapt to market volatility.',
    hint: 'Higher ATR = more volatile market = wider stop losses.',
  },
  rr_ratio: {
    term: 'R:R Ratio (Reward-to-Risk)',
    definition: 'How much you stand to gain vs. lose per trade. A 1.5:1 ratio means your take profit is 1.5x further than your stop loss.',
    hint: '1.5:1 is standard. Higher ratio = bigger wins but fewer of them.',
  },
  pips: {
    term: 'Pips',
    definition: 'The smallest standard price movement in forex. For most pairs, 1 pip = 0.0001. For JPY pairs, 1 pip = 0.01.',
    hint: 'Used to measure price movements and calculate profit/loss.',
  },
  confidence: {
    term: 'Confidence',
    definition: 'How strongly the AI model or strategy believes in a signal, from 0% to 100%. Only signals above your minimum confidence threshold become trades.',
    hint: '> 70% is high conviction. < 50% is speculative.',
  },
  win_rate: {
    term: 'Win Rate',
    definition: 'The percentage of closed trades that were profitable. A 60% win rate means 6 out of 10 trades made money.',
    hint: '> 50% with a good R:R ratio is profitable. Even 40% wins with 2:1 R:R makes money.',
  },
  pnl: {
    term: 'P&L (Profit & Loss)',
    definition: 'Your total profit or loss. Green/positive means you\'re making money, red/negative means losing.',
    hint: 'Shown in virtual currency (paper trading).',
  },
  stop_loss: {
    term: 'Stop Loss (SL)',
    definition: 'A price level where a losing trade is automatically closed to limit damage. Prevents small losses from becoming catastrophic.',
    hint: 'Set automatically based on ATR or fixed pips. Never trade without one.',
  },
  take_profit: {
    term: 'Take Profit (TP)',
    definition: 'A price level where a winning trade is automatically closed to lock in gains. Calculated from the R:R ratio and stop loss distance.',
    hint: 'With 1.5:1 R:R, TP is 1.5x further from entry than the stop loss.',
  },
  position_size: {
    term: 'Position Size',
    definition: 'How many units of a currency pair to trade. Calculated automatically based on your risk percentage and stop loss distance.',
    hint: 'Larger risk % or tighter stop loss = larger position size.',
  },
  capital_allocation: {
    term: 'Capital Allocation',
    definition: 'The amount of virtual money assigned to each trading stream. Each stream manages its own capital independently.',
    hint: 'Default: £33,333 per stream (£100K split 3 ways).',
  },
  equity: {
    term: 'Equity',
    definition: 'The current total value of a stream\'s account — starting capital plus or minus all realized and unrealized profits and losses.',
  },
  paper_trading: {
    term: 'Paper Trading',
    definition: 'Trading with virtual (fake) money on a demo account. All trades are real market prices but no actual money is at risk.',
    hint: 'This entire system uses paper trading on Capital.com\'s demo account.',
  },
  correlation_group: {
    term: 'Correlation Group',
    definition: 'Currency pairs that tend to move together (e.g., EUR/USD and EUR/GBP). The system limits how many correlated trades can be open at once to avoid overexposure to the same risk.',
    hint: 'Groups: EUR pairs, GBP pairs, JPY pairs, Oil types, Precious metals.',
  },
  max_risk_per_trade: {
    term: 'Max Risk Per Trade',
    definition: 'The maximum percentage of a stream\'s capital that can be lost on a single trade. Controls position sizing.',
    hint: 'At 1% with £33,333 capital = £333 max loss per trade. Beginners: stay at 0.5-1%.',
  },
  max_daily_loss: {
    term: 'Max Daily Loss',
    definition: 'A circuit breaker that stops all trading for the day if cumulative losses exceed this percentage. Protects against catastrophic losing streaks.',
    hint: '3% is the default safety net. Lower = more conservative.',
  },
  max_open_positions: {
    term: 'Max Open Positions',
    definition: 'The maximum number of trades that can be active at the same time per stream. Limits total exposure.',
    hint: '3-5 is moderate. More positions = more diversification but also more risk.',
  },
  max_correlated_positions: {
    term: 'Max Correlated Positions',
    definition: 'Maximum trades allowed in the same correlation group (e.g., multiple EUR pairs). Prevents concentrated risk in one currency.',
    hint: '2 is default. Set to 1 for maximum diversification.',
  },
  atr_multiplier: {
    term: 'ATR Multiplier',
    definition: 'How many ATRs away from entry to place the stop loss. Higher = wider stop loss = gives trades more room but risks more per trade.',
    hint: '1.5x is standard. Below 1.0 is very tight. Above 2.5 is very wide.',
  },
  atr_period: {
    term: 'ATR Period',
    definition: 'How many candles to look back when calculating ATR. More periods = smoother, less reactive to recent spikes.',
    hint: '14 is the standard default. 7 is more responsive. 28 is smoother.',
  },
  min_confidence: {
    term: 'Min Confidence Threshold',
    definition: 'Signals below this confidence level are ignored and won\'t generate trades. Higher threshold = fewer but more convicted trades.',
    hint: '60% is default. Raise to 70-80% for fewer, higher-quality signals.',
  },

  // Strategy-specific terms
  momentum: {
    term: 'Momentum Strategy',
    definition: 'Bets that recent price trends will continue. If a currency has been rising over the lookback period, it goes long (buys). If falling, it goes short (sells).',
    hint: 'Based on academic research by Moskowitz (2012). Works best in trending markets.',
  },
  carry: {
    term: 'Carry Trade Strategy',
    definition: 'Buys currencies with higher interest rates and sells those with lower rates, profiting from the interest rate differential.',
    hint: 'Based on Menkhoff (2012). Works best in stable, low-volatility markets. Vulnerable to sudden risk-off events.',
  },
  breakout: {
    term: 'Breakout Strategy',
    definition: 'Waits for price to break out of the overnight Asian trading range, then trades in the breakout direction when London or New York opens.',
    hint: 'Based on Breedon (2012). Most active during London open (07:00 UTC).',
  },
  mean_reversion: {
    term: 'Mean Reversion Strategy',
    definition: 'Bets that prices will return to average after extreme moves. Uses Bollinger Bands to detect when price is stretched too far, and RSI to confirm.',
    hint: 'Based on Pojarliev (2008). Works best in range-bound, choppy markets. Struggles in strong trends.',
  },
  volatility_breakout: {
    term: 'Volatility Breakout Strategy',
    definition: 'Detects when a market goes from calm to volatile (ATR contracts then suddenly expands) and enters in the direction of the breakout.',
    hint: 'Based on Alizadeh (2002). Catches the start of big moves after quiet periods.',
  },

  // Strategy parameters
  lookback_months: {
    term: 'Lookback Months',
    definition: 'How many months of price history the momentum strategy examines to determine the trend direction.',
    hint: '12 months is the academic standard. Shorter = more reactive. Longer = smoother.',
  },
  rebalance_frequency: {
    term: 'Rebalance Frequency',
    definition: 'How often the momentum strategy re-evaluates its positions. Weekly catches changes faster, monthly is more stable.',
  },
  breakout_buffer_pips: {
    term: 'Breakout Buffer (Pips)',
    definition: 'Extra pips beyond the Asian range high/low that price must move before a breakout is confirmed. Filters out false breakouts.',
    hint: '10 pips is default. Higher = fewer but more reliable breakouts.',
  },
  bb_period: {
    term: 'Bollinger Band Period',
    definition: 'Number of candles used to calculate the moving average at the center of the Bollinger Bands. More periods = smoother bands.',
    hint: '20 is the standard. 10 is very reactive. 50 is very smooth.',
  },
  bb_std: {
    term: 'Bollinger Band Width (Std Dev)',
    definition: 'How many standard deviations wide the bands are. Wider bands mean price has to move further to trigger a signal.',
    hint: '2.0 is standard. Below 1.5 = many signals. Above 2.5 = very few signals.',
  },
  rsi_period: {
    term: 'RSI Period',
    definition: 'Number of candles used to calculate the Relative Strength Index. Shorter period = more sensitive to recent price changes.',
    hint: '14 is the standard. 7 is more responsive. 28 is smoother.',
  },
  rsi_oversold: {
    term: 'RSI Oversold Level',
    definition: 'When RSI drops below this level, the asset is considered oversold (potentially due for a bounce). The strategy looks to buy.',
    hint: '30 is standard. Lower (20) = stricter filter, fewer signals.',
  },
  rsi_overbought: {
    term: 'RSI Overbought Level',
    definition: 'When RSI rises above this level, the asset is considered overbought (potentially due for a pullback). The strategy looks to sell.',
    hint: '70 is standard. Higher (80) = stricter filter, fewer signals.',
  },
  atr_contraction_threshold: {
    term: 'ATR Contraction Threshold',
    definition: 'How much ATR must shrink (relative to its average) before the strategy considers the market "calm" and ready for a breakout.',
    hint: '0.7 means ATR must drop to 70% of its average. Lower = stricter, fewer signals.',
  },
  breakout_atr_multiplier: {
    term: 'Breakout ATR Multiplier',
    definition: 'How far price must move (in ATR units) from the contraction zone to confirm a volatility breakout.',
    hint: '1.0 is default. Higher = needs a bigger move to trigger.',
  },

  // News-specific
  news_lookback: {
    term: 'News Lookback Hours',
    definition: 'How many hours of news history to analyze. Shorter = more reactive to breaking news. Longer = broader context but may include stale headlines.',
    hint: '4 hours is default. 1-2h for breaking news focus. 8-12h for broader context.',
  },
  news_dedup: {
    term: 'Deduplication',
    definition: 'Removing duplicate or near-identical headlines so the AI doesn\'t analyze the same story multiple times from different sources.',
  },
  instrument_mapping: {
    term: 'Instrument Mapping',
    definition: 'Matching news headlines to currency pairs using keyword lists. For example, a headline mentioning "ECB" or "eurozone" maps to EUR/USD.',
  },

  // Hybrid-specific
  combiner_weighted: {
    term: 'Weighted Score (Combiner)',
    definition: 'Each module\'s signal is multiplied by its weight, then summed. The final score determines the trade direction.',
  },
  combiner_all_agree: {
    term: 'All Must Agree (Combiner)',
    definition: 'Every module in the recipe must produce the same direction (all long or all short). The strictest mode — fewest trades but highest conviction.',
  },
  combiner_majority: {
    term: 'Majority Vote (Combiner)',
    definition: 'More than half of the modules must agree on direction. A balanced approach between strictness and trade frequency.',
  },
  combiner_any: {
    term: 'Any One Triggers (Combiner)',
    definition: 'If any single module produces a signal above the threshold, a trade is placed. The loosest mode — most trades.',
  },
  must_participate: {
    term: 'Must Participate',
    definition: 'If checked, this module must produce a non-neutral signal for any trade to happen, regardless of what other modules say. Use this to make one module the "gatekeeper."',
    hint: 'Example: News with "must participate" means no trade unless the AI has an opinion.',
  },
  module_weight: {
    term: 'Module Weight',
    definition: 'How much influence this module has in the weighted combiner. 1.0 = full influence, 0.5 = half influence, 0.0 = ignored.',
    hint: 'Only used with "Weighted Score" combiner mode.',
  },

  // Trade statuses
  status_open: {
    term: 'Open',
    definition: 'This trade is currently active. It will close when price hits the stop loss, take profit, or the next signal says to exit.',
  },
  status_closed_tp: {
    term: 'Target Hit (closed_tp)',
    definition: 'This trade closed because price reached the take profit level. A winning trade.',
  },
  status_closed_sl: {
    term: 'Stopped Out (closed_sl)',
    definition: 'This trade closed because price hit the stop loss level. A losing trade, but the loss was limited by the stop loss.',
  },
  status_closed_signal: {
    term: 'Signal Close',
    definition: 'This trade was closed because a new signal in the opposite direction was generated.',
  },
  status_failed: {
    term: 'Failed',
    definition: 'This trade could not be executed due to a broker or API error.',
  },

  // Risk
  risk_profile: {
    term: 'Risk Profile',
    definition: 'A preset combination of risk settings. Conservative risks less per trade, aggressive risks more. Choose based on your comfort with potential losses.',
  },
  capital_at_risk: {
    term: 'Capital at Risk',
    definition: 'The total amount of money currently exposed across all open positions. If every open trade hit its stop loss, this is roughly how much you\'d lose.',
  },
  unrealized_pnl: {
    term: 'Unrealized P&L',
    definition: 'Profit or loss on trades that are still open. This number changes with every price tick and only becomes "real" when the trade closes.',
  },
  return_pct: {
    term: 'Return %',
    definition: 'Percentage gain or loss relative to the starting capital allocation. Calculated as (current equity - starting capital) / starting capital.',
  },

  // Market
  market_session: {
    term: 'Market Session',
    definition: 'Forex trades 24/5 across four overlapping sessions: Sydney, Tokyo, London, and New York. Each session has different liquidity and volatility.',
    hint: 'London + New York overlap (12:00-16:00 UTC) has the highest volume.',
  },
}

export default GLOSSARY

/**
 * Setting-specific help text — extends glossary with
 * practical "what does this slider do" guidance.
 */
export const SETTING_HELP = {
  'scheduler.paused': {
    glossaryKey: null,
    help: 'When paused, the hourly automated trading cycle will skip without analyzing markets or placing any trades. Manual runs from the UI still work.',
  },
  'streams.news_stream.enabled': {
    glossaryKey: null,
    help: 'Enable or disable the AI news-driven trading stream entirely. When disabled, no news signals or trades are generated.',
  },
  'streams.news_stream.capital_allocation': {
    glossaryKey: 'capital_allocation',
    help: 'Virtual money assigned to this stream. Larger allocation = larger position sizes (proportional to risk %).',
  },
  'streams.news_stream.min_confidence': {
    glossaryKey: 'min_confidence',
    help: 'AI signals below this confidence are ignored. Higher = fewer trades but higher quality.',
  },
  'streams.news_stream.news_lookback_hours': {
    glossaryKey: 'news_lookback',
    help: 'How far back to fetch news headlines. 4h is default. Shorter = reactive, longer = broader.',
  },
  'streams.strategy_stream.enabled': {
    glossaryKey: null,
    help: 'Enable or disable all mechanical strategies. Individual strategies can be toggled separately below.',
  },
  'streams.strategy_stream.capital_allocation': {
    glossaryKey: 'capital_allocation',
    help: 'Virtual money assigned to all strategies combined. Shared across the 5 strategies.',
  },
  'risk.max_risk_per_trade': {
    glossaryKey: 'max_risk_per_trade',
    help: 'Controls position sizing. 1% of £33,333 = £333 max loss per trade.',
  },
  'risk.max_open_positions_per_stream': {
    glossaryKey: 'max_open_positions',
    help: 'Safety limit on how many trades can be open at once per stream.',
  },
  'risk.max_daily_loss_per_stream': {
    glossaryKey: 'max_daily_loss',
    help: 'Circuit breaker. Trading stops for the day if losses exceed this.',
  },
  'risk.max_correlated_positions': {
    glossaryKey: 'max_correlated_positions',
    help: 'Prevents overexposure to related currency pairs (e.g., multiple EUR trades).',
  },
  'risk.default_rr_ratio': {
    glossaryKey: 'rr_ratio',
    help: 'Sets take profit distance relative to stop loss. 1.5:1 means aiming to win 50% more than you risk.',
  },
  'risk.stop_loss_method': {
    glossaryKey: null,
    help: 'How stop losses are calculated. "ATR" adapts to volatility (recommended). "Fixed pips" uses a static distance.',
  },
  'risk.atr_multiplier': {
    glossaryKey: 'atr_multiplier',
    help: 'Wider multiplier = bigger stop loss = more room for price to move but larger potential loss.',
  },
  'risk.atr_period': {
    glossaryKey: 'atr_period',
    help: 'Lookback for ATR calculation. Standard is 14 candles.',
  },
}
