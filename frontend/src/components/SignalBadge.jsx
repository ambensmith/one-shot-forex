import { DIRECTION_COLORS } from '../lib/constants'

export default function SignalBadge({ direction, size = 'md' }) {
  const color = DIRECTION_COLORS[direction] || DIRECTION_COLORS.neutral
  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1'

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium uppercase ${sizeClasses}`}
      style={{ backgroundColor: `${color}20`, color }}
    >
      <span
        className="w-2 h-2 rounded-full mr-1.5"
        style={{ backgroundColor: color }}
      />
      {direction}
    </span>
  )
}
