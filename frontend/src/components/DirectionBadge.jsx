export default function DirectionBadge({ direction, size = 'default' }) {
  const isLong = direction === 'long'
  const isShort = direction === 'short'
  const arrow = isLong ? ' \u25b2' : isShort ? ' \u25bc' : ''
  const color = isLong ? 'text-profitable-text' : isShort ? 'text-loss-text' : 'text-tertiary'
  const bg = isLong
    ? 'rgba(34, 197, 94, 0.08)'
    : isShort
      ? 'rgba(239, 68, 68, 0.08)'
      : 'rgba(148, 163, 184, 0.08)'

  const sizeClass = size === 'small' ? 'text-[11px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5'

  return (
    <span
      className={`inline-block font-semibold tracking-[0.3px] rounded-md ${color} ${sizeClass}`}
      style={{ background: bg }}
    >
      {(direction || 'neutral').toUpperCase()}{arrow}
    </span>
  )
}
