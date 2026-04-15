import { INSTRUMENTS, INSTRUMENT_META } from '../lib/constants'

const OUTCOME_OPTIONS = [
  { value: null, label: 'All' },
  { value: 'won', label: 'Won' },
  { value: 'lost', label: 'Lost' },
]

const SOURCE_OPTIONS = [
  { value: null, label: 'Any Source' },
  { value: 'llm', label: 'LLM' },
  { value: 'strategy', label: 'Strategy' },
]

export default function TradeFilters({ filters, onChange }) {
  const { filter, instrument, source } = filters

  function setField(field, value) {
    onChange({ ...filters, [field]: value })
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Outcome toggles */}
      <div className="flex rounded-button border border-border overflow-hidden">
        {OUTCOME_OPTIONS.map(opt => {
          const isActive = filter === opt.value
          let activeClasses = 'bg-surface text-secondary'
          if (isActive && opt.value === 'won') {
            activeClasses = 'text-profitable-text'
          } else if (isActive && opt.value === 'lost') {
            activeClasses = 'text-loss-text'
          } else if (isActive) {
            activeClasses = 'bg-hover text-primary'
          }

          return (
            <button
              key={opt.label}
              onClick={() => setField('filter', opt.value)}
              className={`px-3 py-1.5 text-[11px] font-semibold tracking-[0.3px] transition-colors ${
                isActive ? activeClasses : 'text-tertiary hover:text-secondary hover:bg-hover'
              }`}
              style={
                isActive && opt.value === 'won'
                  ? { background: 'rgba(34, 197, 94, 0.08)' }
                  : isActive && opt.value === 'lost'
                    ? { background: 'rgba(239, 68, 68, 0.08)' }
                    : undefined
              }
            >
              {opt.label}
            </button>
          )
        })}
      </div>

      {/* Instrument dropdown */}
      <select
        value={instrument || ''}
        onChange={e => setField('instrument', e.target.value || null)}
        className="px-3 py-1.5 text-sm bg-surface border border-border rounded-button text-secondary focus:border-brand focus:outline-none focus:ring-[3px] focus:ring-brand/10"
      >
        <option value="">Any Pair</option>
        {INSTRUMENTS.map(inst => (
          <option key={inst} value={inst}>
            {INSTRUMENT_META[inst]?.name || inst}
          </option>
        ))}
      </select>

      {/* Source dropdown */}
      <select
        value={source || ''}
        onChange={e => setField('source', e.target.value || null)}
        className="px-3 py-1.5 text-sm bg-surface border border-border rounded-button text-secondary focus:border-brand focus:outline-none focus:ring-[3px] focus:ring-brand/10"
      >
        {SOURCE_OPTIONS.map(opt => (
          <option key={opt.label} value={opt.value || ''}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
