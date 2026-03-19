import HelpTooltip from './HelpTooltip'

/**
 * RiskGauge — horizontal progress bar showing usage of a limit.
 * Green (<50%), Yellow (50-80%), Red (>80%).
 */
export default function RiskGauge({ label, used, limit, helpTerm }) {
  const pct = limit > 0 ? Math.min((used / limit) * 100, 100) : 0
  const color = pct > 80 ? '#f03e3e' : pct > 50 ? '#f59f00' : '#37b24d'

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 shrink-0">
        {label}
        {helpTerm && <HelpTooltip term={helpTerm} />}
      </span>
      <div className="flex-1 bg-gray-700/50 rounded-full h-2 relative">
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: `${Math.max(pct, 1)}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-mono text-gray-400 shrink-0 w-20 text-right">
        {used.toFixed(0)} / {limit.toFixed(0)}
      </span>
    </div>
  )
}
