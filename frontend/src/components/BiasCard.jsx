import { INSTRUMENT_META, biasToSemantic, semanticStyle } from '../lib/constants'

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

export default function BiasCard({ instrument, direction, strength }) {
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

  return (
    <div
      className="flex-shrink-0 w-[140px] h-[80px] bg-surface rounded-card border p-3 flex flex-col justify-between transition-shadow duration-200"
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
    </div>
  )
}
