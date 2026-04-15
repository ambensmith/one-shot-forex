import BiasCard from './BiasCard'
import { useBias } from '../hooks/useDashboardData'
import { INSTRUMENTS } from '../lib/constants'

export default function BiasCardRow() {
  const { instruments, loading } = useBias()

  // Build a map of instrument -> bias data for quick lookup
  const biasMap = {}
  for (const b of instruments) {
    biasMap[b.instrument] = b
  }

  return (
    <div className="flex gap-3 overflow-x-auto scrollbar-none p-1">
      {INSTRUMENTS.map(inst => {
        const bias = biasMap[inst]
        return (
          <BiasCard
            key={inst}
            instrument={inst}
            direction={bias?.direction || 'neutral'}
            strength={bias?.strength || 0}
          />
        )
      })}
      {loading && instruments.length === 0 && (
        <p className="text-sm italic text-tertiary">Loading bias data...</p>
      )}
    </div>
  )
}
