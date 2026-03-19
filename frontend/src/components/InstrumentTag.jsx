import { INSTRUMENT_META } from '../lib/constants'

export default function InstrumentTag({ instrument }) {
  const meta = INSTRUMENT_META[instrument] || { name: instrument, type: 'forex' }
  const bgColor = meta.type === 'commodity' ? 'bg-amber-500/10 text-amber-400' : 'bg-blue-500/10 text-blue-400'

  return (
    <span className={`inline-flex items-center text-xs font-mono px-2 py-0.5 rounded ${bgColor}`}>
      {meta.name}
    </span>
  )
}
