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
  momentum: { paper: 'Moskowitz 2012', desc: 'Time Series Momentum' },
  carry: { paper: 'Menkhoff 2012', desc: 'Carry Trade' },
  breakout: { paper: 'Breedon 2012', desc: 'London/NY Session Breakout' },
  mean_reversion: { paper: 'Pojarliev 2008', desc: 'Bollinger Mean Reversion' },
  volatility_breakout: { paper: 'Alizadeh 2002', desc: 'Volatility Breakout' },
}

export function formatPnl(value) {
  if (value == null) return '—'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}`
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
