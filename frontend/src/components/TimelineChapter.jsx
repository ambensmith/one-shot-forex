/**
 * A single chapter in the narrative timeline drill-down.
 * Props:
 *   title: string
 *   status: 'completed' | 'active' | 'pending'
 *   semantic: 'profitable' | 'loss' | 'pending' | 'cooldown' | 'info'
 *   isLast: boolean
 *   children: content to render in the chapter body
 */

const ACCENT_COLORS = {
  profitable: '#22C55E',
  loss: '#EF4444',
  pending: '#F59E0B',
  info: '#6366F1',
  cooldown: '#94A3B8',
}

export default function TimelineChapter({ title, status = 'completed', semantic = 'cooldown', isLast = false, children }) {
  const accentColor = ACCENT_COLORS[semantic] || ACCENT_COLORS.cooldown

  // Node styles based on status
  let nodeStyle = {}
  let nodeClass = 'w-3 h-3 rounded-full flex-shrink-0'

  if (status === 'completed') {
    nodeStyle = { border: '2px solid #D6D3D1', background: '#FFFFFF' }
  } else if (status === 'active') {
    nodeStyle = { background: accentColor }
    nodeClass += ' animate-pulse'
  } else {
    // pending
    nodeStyle = { border: '2px dashed #D6D3D1', background: 'transparent' }
  }

  // Rail segment
  const railColor = status === 'pending' || isLast ? undefined : '#D6D3D1'
  const railDashed = status === 'pending'

  return (
    <div className="relative flex gap-6" style={{ paddingBottom: isLast ? 0 : '32px' }}>
      {/* Rail + Node column */}
      <div className="flex flex-col items-center" style={{ width: '12px', minWidth: '12px' }}>
        {/* Node */}
        <div className={nodeClass} style={nodeStyle} />
        {/* Rail segment below node */}
        {!isLast && (
          <div
            className="flex-1 mt-1"
            style={{
              width: '2px',
              background: railDashed ? 'transparent' : (railColor || '#E7E5E4'),
              borderLeft: railDashed ? '2px dashed #E7E5E4' : 'none',
            }}
          />
        )}
      </div>

      {/* Chapter content */}
      <div className="flex-1 max-w-narrative -mt-0.5 min-w-0">
        <h4
          className={`font-display text-lg leading-[1.3] ${
            status === 'pending' ? 'text-tertiary' : 'text-primary'
          }`}
          style={{ fontWeight: 500 }}
        >
          {title}
        </h4>
        <div
          className={`mt-2 text-sm leading-relaxed ${
            status === 'pending' ? 'italic text-tertiary' : 'text-secondary'
          }`}
        >
          {children}
        </div>
      </div>
    </div>
  )
}

/** Horizontal confidence bar display */
export function ConfidenceBar({ value, semantic = 'info' }) {
  if (value == null) return null
  const accentColor = ACCENT_COLORS[semantic] || ACCENT_COLORS.info
  const textColors = {
    profitable: '#15803D',
    loss: '#DC2626',
    pending: '#B45309',
    info: '#4F46E5',
    cooldown: '#64748B',
  }

  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="w-[120px] h-1 rounded-full bg-border">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${Math.round(value * 100)}%`,
            backgroundColor: accentColor,
          }}
        />
      </div>
      <span
        className="text-xs font-medium"
        style={{ color: textColors[semantic] || textColors.info }}
      >
        {Math.round(value * 100)}% confidence
      </span>
    </div>
  )
}
