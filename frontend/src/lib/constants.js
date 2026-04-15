export const INSTRUMENTS = [
  'EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CHF',
  'AUD_USD', 'USD_CAD', 'EUR_GBP', 'XAU_USD',
]

export const INSTRUMENT_META = {
  EUR_USD: { name: 'EUR/USD', type: 'forex' },
  GBP_USD: { name: 'GBP/USD', type: 'forex' },
  USD_JPY: { name: 'USD/JPY', type: 'forex' },
  USD_CHF: { name: 'USD/CHF', type: 'forex' },
  AUD_USD: { name: 'AUD/USD', type: 'forex' },
  USD_CAD: { name: 'USD/CAD', type: 'forex' },
  EUR_GBP: { name: 'EUR/GBP', type: 'forex' },
  XAU_USD: { name: 'Gold', type: 'commodity' },
}

export function formatPnl(value) {
  if (value == null) return '\u2014'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}`
}

export function formatPnlCurrency(value, currency = '\u00a3') {
  if (value == null) return '\u2014'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${currency}${Math.abs(value).toFixed(2)}`
}

export function formatPercent(value) {
  if (value == null) return '\u2014'
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

export function formatDuration(seconds) {
  if (seconds == null) return '\u2014'
  if (seconds < 60) return '<1m'
  const mins = Math.floor(seconds / 60)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  const remainMins = mins % 60
  if (hours < 24) return remainMins > 0 ? `${hours}h ${remainMins}m` : `${hours}h`
  const days = Math.floor(hours / 24)
  const remainHours = hours % 24
  return remainHours > 0 ? `${days}d ${remainHours}h` : `${days}d`
}

/**
 * Returns semantic status key for a trade, used to look up shadow/tint/border CSS vars.
 * Returns: 'profitable' | 'loss' | 'pending' | 'cooldown'
 */
export function semanticStatus(trade) {
  if (!trade) return 'cooldown'
  const status = trade.status
  if (status === 'open') {
    const pnl = trade.unrealized_pnl ?? trade.pnl
    if (pnl == null) return 'pending'
    return pnl >= 0 ? 'profitable' : 'loss'
  }
  if (status === 'closed_tp') return 'profitable'
  if (status === 'closed_sl') return 'loss'
  const pnl = trade.pnl
  if (pnl == null) return 'cooldown'
  return pnl >= 0 ? 'profitable' : 'loss'
}

/**
 * Returns inline style object for semantic shadow/tint/border given a status key.
 */
export function semanticStyle(status) {
  return {
    boxShadow: `var(--shadow-${status})`,
    background: `var(--tint-${status})`,
    borderColor: `var(--border-${status})`,
  }
}

/**
 * Maps bias direction to a semantic status key.
 */
export function biasToSemantic(direction) {
  if (direction === 'bullish') return 'profitable'
  if (direction === 'bearish') return 'loss'
  return 'cooldown'
}
