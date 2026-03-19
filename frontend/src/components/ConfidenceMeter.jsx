export default function ConfidenceMeter({ value, width = 80 }) {
  const pct = Math.max(0, Math.min(1, value || 0))
  const color = pct >= 0.7 ? '#37b24d' : pct >= 0.5 ? '#f59f00' : '#868e96'

  return (
    <div className="flex items-center gap-2">
      <div className="bg-gray-700 rounded-full h-1.5" style={{ width }}>
        <div
          className="h-1.5 rounded-full transition-all"
          style={{ width: `${pct * 100}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-mono text-gray-400">{(pct * 100).toFixed(0)}%</span>
    </div>
  )
}
