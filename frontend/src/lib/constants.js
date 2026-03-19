export const STREAM_COLORS = {
  news: '#4c6ef5',
  strategy: '#37b24d',
  hybrid: '#f59f00',
}

export const DIRECTION_COLORS = {
  long: '#37b24d',
  short: '#f03e3e',
  neutral: '#868e96',
}

export const INSTRUMENT_META = {
  EUR_USD: { name: 'EUR/USD', type: 'forex' },
  GBP_USD: { name: 'GBP/USD', type: 'forex' },
  USD_JPY: { name: 'USD/JPY', type: 'forex' },
  USD_CHF: { name: 'USD/CHF', type: 'forex' },
  AUD_USD: { name: 'AUD/USD', type: 'forex' },
  USD_CAD: { name: 'USD/CAD', type: 'forex' },
  NZD_USD: { name: 'NZD/USD', type: 'forex' },
  XAU_USD: { name: 'Gold', type: 'commodity' },
  XAG_USD: { name: 'Silver', type: 'commodity' },
  BCO_USD: { name: 'Brent Crude', type: 'commodity' },
  WTICO_USD: { name: 'WTI Crude', type: 'commodity' },
  NATGAS_USD: { name: 'Natural Gas', type: 'commodity' },
  EUR_GBP: { name: 'EUR/GBP', type: 'forex' },
  EUR_JPY: { name: 'EUR/JPY', type: 'forex' },
  GBP_JPY: { name: 'GBP/JPY', type: 'forex' },
}

export const STRATEGY_INFO = {
  momentum: {
    paper: 'Moskowitz 2012',
    desc: 'Time Series Momentum',
    glossaryKey: 'momentum',
    explanation: 'Looks at price trends over the past 12 months. If a currency has been rising, it buys. If falling, it sells. Based on the idea that trends tend to continue.',
  },
  carry: {
    paper: 'Menkhoff 2012',
    desc: 'Carry Trade',
    glossaryKey: 'carry',
    explanation: 'Buys currencies with higher interest rates and sells those with lower rates, profiting from the interest rate differential. Works best in calm markets.',
  },
  breakout: {
    paper: 'Breedon 2012',
    desc: 'London/NY Session Breakout',
    glossaryKey: 'breakout',
    explanation: 'Monitors the overnight Asian trading range, then trades in the direction of the breakout when London or New York markets open with higher volume.',
  },
  mean_reversion: {
    paper: 'Pojarliev 2008',
    desc: 'Bollinger Mean Reversion',
    glossaryKey: 'mean_reversion',
    explanation: 'Bets that prices will bounce back after moving too far from their average. Uses Bollinger Bands to detect extreme moves and RSI to confirm oversold/overbought conditions.',
  },
  volatility_breakout: {
    paper: 'Alizadeh 2002',
    desc: 'Volatility Breakout',
    glossaryKey: 'volatility_breakout',
    explanation: 'Detects when a market shifts from calm to volatile — ATR contracts then expands — and enters in the direction of the breakout to catch the start of big moves.',
  },
}

/** Strategy-specific tunable parameters metadata */
export const STRATEGY_PARAMS = {
  momentum: [
    { key: 'lookback_months', label: 'Lookback Months', type: 'number', min: 1, max: 24, step: 1, default: 12, glossaryKey: 'lookback_months' },
    { key: 'rebalance_frequency', label: 'Rebalance Frequency', type: 'select', options: ['weekly', 'monthly'], default: 'weekly', glossaryKey: 'rebalance_frequency' },
  ],
  carry: [
    { key: 'rate_data', label: 'Rate Data Source', type: 'readonly', default: 'manual' },
  ],
  breakout: [
    { key: 'breakout_buffer_pips', label: 'Breakout Buffer (pips)', type: 'number', min: 5, max: 30, step: 1, default: 10, glossaryKey: 'breakout_buffer_pips' },
    { key: 'asian_start', label: 'Asian Range Start', type: 'readonly', default: '22:00' },
    { key: 'asian_end', label: 'Asian Range End', type: 'readonly', default: '06:00' },
  ],
  mean_reversion: [
    { key: 'bb_period', label: 'Bollinger Period', type: 'number', min: 10, max: 50, step: 1, default: 20, glossaryKey: 'bb_period' },
    { key: 'bb_std', label: 'Bollinger Std Dev', type: 'slider', min: 1.0, max: 3.0, step: 0.1, default: 2.0, glossaryKey: 'bb_std' },
    { key: 'rsi_period', label: 'RSI Period', type: 'number', min: 7, max: 28, step: 1, default: 14, glossaryKey: 'rsi_period' },
    { key: 'rsi_oversold', label: 'RSI Oversold', type: 'number', min: 20, max: 40, step: 1, default: 30, glossaryKey: 'rsi_oversold' },
    { key: 'rsi_overbought', label: 'RSI Overbought', type: 'number', min: 60, max: 80, step: 1, default: 70, glossaryKey: 'rsi_overbought' },
  ],
  volatility_breakout: [
    { key: 'atr_period', label: 'ATR Period', type: 'number', min: 7, max: 28, step: 1, default: 14, glossaryKey: 'atr_period' },
    { key: 'atr_contraction_threshold', label: 'Contraction Threshold', type: 'slider', min: 0.3, max: 0.9, step: 0.05, default: 0.7, glossaryKey: 'atr_contraction_threshold' },
    { key: 'breakout_atr_multiplier', label: 'Breakout ATR Multiplier', type: 'slider', min: 0.5, max: 2.0, step: 0.1, default: 1.0, glossaryKey: 'breakout_atr_multiplier' },
  ],
}

/** Trade status labels — plain-English descriptions */
export const TRADE_STATUS_LABELS = {
  open: { label: 'Open', desc: 'Trade is currently active', color: 'text-blue-400' },
  closed_tp: { label: 'Target Hit', desc: 'Closed at take profit — a winning trade', color: 'text-green-400' },
  closed_sl: { label: 'Stopped Out', desc: 'Closed at stop loss — loss was limited', color: 'text-red-400' },
  closed_signal: { label: 'Signal Close', desc: 'Closed by a new opposing signal', color: 'text-yellow-400' },
  closed_reconciled: { label: 'Reconciled', desc: 'Closed by broker (SL/TP hit on broker side)', color: 'text-gray-400' },
  failed: { label: 'Failed', desc: 'Could not execute due to broker/API error', color: 'text-gray-500' },
}

/** Risk profile presets */
export const RISK_PRESETS = {
  conservative: {
    label: 'Conservative',
    desc: 'Lower risk, smaller positions. Good for learning.',
    values: {
      'risk.max_risk_per_trade': 0.005,
      'risk.default_rr_ratio': 1.5,
      'risk.max_open_positions_per_stream': 3,
      'risk.max_daily_loss_per_stream': 0.02,
      'risk.max_correlated_positions': 1,
    },
  },
  moderate: {
    label: 'Moderate',
    desc: 'Balanced risk and reward. The default setting.',
    values: {
      'risk.max_risk_per_trade': 0.01,
      'risk.default_rr_ratio': 1.5,
      'risk.max_open_positions_per_stream': 5,
      'risk.max_daily_loss_per_stream': 0.03,
      'risk.max_correlated_positions': 2,
    },
  },
  aggressive: {
    label: 'Aggressive',
    desc: 'Higher risk, larger positions. More potential gain and loss.',
    values: {
      'risk.max_risk_per_trade': 0.02,
      'risk.default_rr_ratio': 2.0,
      'risk.max_open_positions_per_stream': 8,
      'risk.max_daily_loss_per_stream': 0.05,
      'risk.max_correlated_positions': 3,
    },
  },
}

export function formatPnl(value) {
  if (value == null) return '—'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}`
}

export function formatPnlCurrency(value, currency = '€') {
  if (value == null) return '—'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${currency}${Math.abs(value).toFixed(2)}`
}

export function formatPercent(value) {
  if (value == null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

export function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
