import { INSTRUMENT_META } from '../lib/constants'

export default function InstrumentTag({ instrument }) {
  const meta = INSTRUMENT_META[instrument]
  const label = meta?.name || instrument?.replace('_', '/')
  return (
    <span className="inline-block text-[11px] font-semibold tracking-[0.5px] uppercase px-2 py-0.5 rounded-md bg-hover text-secondary">
      {label}
    </span>
  )
}
