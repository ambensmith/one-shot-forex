import { INSTRUMENT_META, biasToSemantic, semanticStyle, formatPnlCurrency } from '../lib/constants'

function directionArrow(direction) {
  if (direction === 'bullish') return '\u25b2'
  if (direction === 'bearish') return '\u25bc'
  return '\u2014'
}

function directionLabel(direction) {
  if (direction === 'bullish') return 'Bullish'
  if (direction === 'bearish') return 'Bearish'
  return 'Neutral'
}

function pnlColor(pnl) {
  if (pnl == null || pnl === 0) return '#94A3B8'
  return pnl > 0 ? '#15803D' : '#DC2626'
}

export default function BiasCard({ instrument, direction, strength, totalPnl, tradeCount }) {
  const meta = INSTRUMENT_META[instrument]
  const semantic = biasToSemantic(direction)
  const style = semanticStyle(semantic)

  const accentColor = semantic === 'profitable'
    ? '#22C55E'
    : semantic === 'loss'
      ? '#EF4444'
      : '#94A3B8'

  const textColor = semantic === 'profitable'
    ? '#15803D'
    : semantic === 'loss'
      ? '#DC2626'
      : '#64748B'

  const hasTrades = (tradeCount || 0) > 0

  return (
    <div
      className="flex-shrink-0 w-[150px] h-[104px] bg-surface rounded-card border p-3 flex flex-col justify-between transition-shadow duration-200"
      style={{
        ...style,
        borderWidth: '1px',
        borderStyle: 'solid',
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-primary">
          {meta?.name || instrument.replace('_', '/')}
        </span>
        <span style={{ color: textColor }} className="text-sm">
          {directionArrow(direction)}
        </span>
      </div>
      <div>
        <p className="text-[11px] font-medium" style={{ color: textColor }}>
          {directionLabel(direction)}
        </p>
        <div className="mt-1 h-1 rounded-full bg-border" style={{ width: '100%' }}>
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{
              width: `${Math.round((strength || 0) * 100)}%`,
              backgroundColor: accentColor,
            }}
          />
        </div>
      </div>
      <div className="flex items-baseline justify-between pt-1 border-t border-border">
        <span
          className="text-[11px] font-semibold font-tabular"
          style={{ color: pnlColor(totalPnl) }}
        >
          {hasTrades ? formatPnlCurrency(totalPnl) : '\u2014'}
        </span>
        <span className="text-[10px] text-tertiary font-tabular">
          {hasTrades ? `${tradeCount} ${tradeCount === 1 ? 'trade' : 'trades'}` : 'no trades'}
        </span>
      </div>
    </div>
  )
}
