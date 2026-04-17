import BiasCard from './BiasCard'
import { useBias } from '../hooks/useDashboardData'
import { INSTRUMENTS } from '../lib/constants'

const DIRECTION_ORDER = { bullish: 0, bearish: 1, neutral: 2 }

export default function BiasCardRow() {
  const { instruments, loading } = useBias()

  const biasMap = {}
  for (const b of instruments) {
    biasMap[b.instrument] = b
  }

  const ordered = [...INSTRUMENTS].sort((a, b) => {
    const da = biasMap[a]?.direction || 'neutral'
    const db = biasMap[b]?.direction || 'neutral'
    const oa = DIRECTION_ORDER[da] ?? 2
    const ob = DIRECTION_ORDER[db] ?? 2
    if (oa !== ob) return oa - ob
    return INSTRUMENTS.indexOf(a) - INSTRUMENTS.indexOf(b)
  })

  return (
    <div className="flex gap-3 overflow-x-auto scrollbar-none p-1">
      {ordered.map(inst => {
        const bias = biasMap[inst]
        return (
          <BiasCard
            key={inst}
            instrument={inst}
            direction={bias?.direction || 'neutral'}
            strength={bias?.strength || 0}
            totalPnl={bias?.total_pnl ?? 0}
            tradeCount={bias?.trade_count ?? 0}
          />
        )
      })}
      {loading && instruments.length === 0 && (
        <p className="text-sm italic text-tertiary">Loading bias data...</p>
      )}
    </div>
  )
}
