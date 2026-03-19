import { useState } from 'react'
import { useConfig } from '../hooks/useStreamData'
import { saveConfig, pollWorkflow } from '../lib/api'
import { INSTRUMENT_META, STRATEGY_INFO } from '../lib/constants'

const ALL_INSTRUMENTS = Object.keys(INSTRUMENT_META)
const ALL_STRATEGIES = Object.keys(STRATEGY_INFO)

export default function Settings() {
  const { config, loading, refresh } = useConfig()
  const [saving, setSaving] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)
  const [changes, setChanges] = useState({})

  function setOverride(key, value) {
    setChanges(prev => ({ ...prev, [key]: value }))
  }

  function getValue(dotKey, fallback) {
    if (dotKey in changes) return changes[dotKey]
    // Navigate config by dot path
    const parts = dotKey.split('.')
    let val = config
    for (const p of parts) {
      if (val == null) return fallback
      val = val[p]
    }
    return val ?? fallback
  }

  async function handleSave() {
    if (Object.keys(changes).length === 0) {
      setStatusMsg({ type: 'info', text: 'No changes to save.' })
      return
    }
    setSaving(true)
    setStatusMsg({ type: 'info', text: 'Saving config...' })
    try {
      const { run_id } = await saveConfig(changes)
      if (run_id) {
        setStatusMsg({ type: 'info', text: `Workflow started (${run_id}). Waiting...` })
        const result = await pollWorkflow(run_id, (status) => {
          setStatusMsg({ type: 'info', text: `Workflow ${status}...` })
        })
        if (result.conclusion === 'success' || result.status === 'completed') {
          setStatusMsg({ type: 'ok', text: 'Config saved! Refreshing...' })
          setChanges({})
          setTimeout(refresh, 5000)
        } else {
          setStatusMsg({ type: 'error', text: `Workflow ${result.conclusion || result.status}` })
        }
      } else {
        setStatusMsg({ type: 'ok', text: 'Config dispatched. Refresh in ~2 min.' })
        setChanges({})
      }
    } catch (e) {
      setStatusMsg({ type: 'error', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="text-gray-500">Loading config...</p>
  if (!config) return <p className="text-gray-500">No config data. Run get-config first or trigger a trading cycle.</p>

  const hasChanges = Object.keys(changes).length > 0

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Settings</h2>
        <button
          onClick={handleSave}
          disabled={saving || !hasChanges}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            hasChanges
              ? 'bg-brand-500 hover:bg-brand-400 text-white'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
          }`}
        >
          {saving ? 'Saving...' : hasChanges ? `Save ${Object.keys(changes).length} change(s)` : 'No changes'}
        </button>
      </div>

      {statusMsg && (
        <div className={`rounded-lg p-4 mb-6 text-sm border ${
          statusMsg.type === 'ok' ? 'bg-green-900/20 border-green-800/50 text-green-300'
          : statusMsg.type === 'error' ? 'bg-red-900/20 border-red-800/50 text-red-300'
          : 'bg-blue-900/20 border-blue-800/50 text-blue-300'
        }`}>
          {statusMsg.text}
        </div>
      )}

      {/* Scheduler */}
      <Section title="Scheduler">
        <ToggleRow
          label="Pause automatic runs"
          description="When paused, cron runs will skip without placing trades"
          checked={getValue('scheduler.paused', false)}
          onChange={v => setOverride('scheduler.paused', v)}
        />
        <InfoRow label="Interval" value={getValue('scheduler.interval', '1h')} />
      </Section>

      {/* News Stream */}
      <Section title="News Stream">
        <ToggleRow
          label="Enabled"
          checked={getValue('streams.news_stream.enabled', false)}
          onChange={v => setOverride('streams.news_stream.enabled', v)}
        />
        <NumberRow
          label="Capital Allocation"
          value={getValue('streams.news_stream.capital_allocation', 33333)}
          onChange={v => setOverride('streams.news_stream.capital_allocation', v)}
          step={1000}
        />
        <SliderRow
          label="Min Confidence"
          value={getValue('streams.news_stream.min_confidence', 0.6)}
          onChange={v => setOverride('streams.news_stream.min_confidence', v)}
          min={0.1} max={0.95} step={0.05}
          format={v => `${(v * 100).toFixed(0)}%`}
        />
        <InstrumentPicker
          label="Instruments"
          selected={getValue('streams.news_stream.instruments', [])}
          onChange={v => setOverride('streams.news_stream.instruments', v)}
        />
      </Section>

      {/* Strategy Stream */}
      <Section title="Strategy Stream">
        <ToggleRow
          label="Enabled"
          checked={getValue('streams.strategy_stream.enabled', false)}
          onChange={v => setOverride('streams.strategy_stream.enabled', v)}
        />
        <NumberRow
          label="Capital Allocation"
          value={getValue('streams.strategy_stream.capital_allocation', 33333)}
          onChange={v => setOverride('streams.strategy_stream.capital_allocation', v)}
          step={1000}
        />
        <InstrumentPicker
          label="Instruments"
          selected={getValue('streams.strategy_stream.instruments', [])}
          onChange={v => setOverride('streams.strategy_stream.instruments', v)}
        />

        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-2">Strategies</p>
          {(getValue('streams.strategy_stream.strategies', []) || []).map((strat, i) => (
            <div key={strat.name} className="flex items-center gap-3 py-1">
              <ToggleRow
                label={`${strat.name.replace('_', ' ')}${STRATEGY_INFO[strat.name] ? ` (${STRATEGY_INFO[strat.name].desc})` : ''}`}
                checked={strat.enabled !== false}
                onChange={v => {
                  const strategies = [...getValue('streams.strategy_stream.strategies', [])]
                  strategies[i] = { ...strategies[i], enabled: v }
                  setOverride('streams.strategy_stream.strategies', strategies)
                }}
                compact
              />
            </div>
          ))}
        </div>
      </Section>

      {/* Risk Parameters */}
      <Section title="Risk Management">
        <SliderRow
          label="Max Risk Per Trade"
          value={getValue('risk.max_risk_per_trade', 0.01)}
          onChange={v => setOverride('risk.max_risk_per_trade', v)}
          min={0.005} max={0.05} step={0.005}
          format={v => `${(v * 100).toFixed(1)}%`}
        />
        <NumberRow
          label="Max Open Positions (per stream)"
          value={getValue('risk.max_open_positions_per_stream', 5)}
          onChange={v => setOverride('risk.max_open_positions_per_stream', v)}
          min={1} max={20} step={1}
        />
        <SliderRow
          label="Max Daily Loss (per stream)"
          value={getValue('risk.max_daily_loss_per_stream', 0.03)}
          onChange={v => setOverride('risk.max_daily_loss_per_stream', v)}
          min={0.01} max={0.10} step={0.01}
          format={v => `${(v * 100).toFixed(0)}%`}
        />
        <NumberRow
          label="Max Correlated Positions"
          value={getValue('risk.max_correlated_positions', 2)}
          onChange={v => setOverride('risk.max_correlated_positions', v)}
          min={1} max={10} step={1}
        />
        <SliderRow
          label="Default R:R Ratio"
          value={getValue('risk.default_rr_ratio', 1.5)}
          onChange={v => setOverride('risk.default_rr_ratio', v)}
          min={1.0} max={4.0} step={0.1}
          format={v => `${v.toFixed(1)}:1`}
        />
        <InfoRow label="Stop Loss Method" value={getValue('risk.stop_loss_method', 'atr')} />
        <SliderRow
          label="ATR Multiplier"
          value={getValue('risk.atr_multiplier', 1.5)}
          onChange={v => setOverride('risk.atr_multiplier', v)}
          min={0.5} max={3.0} step={0.1}
          format={v => `${v.toFixed(1)}x`}
        />
        <NumberRow
          label="ATR Period"
          value={getValue('risk.atr_period', 14)}
          onChange={v => setOverride('risk.atr_period', v)}
          min={5} max={50} step={1}
        />
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-4">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function ToggleRow({ label, description, checked, onChange, compact }) {
  return (
    <div className={`flex items-center justify-between ${compact ? '' : 'py-1'}`}>
      <div>
        <span className={`${compact ? 'text-xs text-gray-400 capitalize' : 'text-sm text-gray-300'}`}>{label}</span>
        {description && <p className="text-xs text-gray-500">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative w-10 h-5 rounded-full transition-colors ${checked ? 'bg-brand-500' : 'bg-gray-600'}`}
      >
        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${checked ? 'left-5' : 'left-0.5'}`} />
      </button>
    </div>
  )
}

function NumberRow({ label, value, onChange, min, max, step = 1 }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-gray-300">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={e => onChange(Number(e.target.value))}
        className="w-28 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200 text-right font-mono"
      />
    </div>
  )
}

function SliderRow({ label, value, onChange, min, max, step, format }) {
  return (
    <div className="py-1">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-gray-300">{label}</span>
        <span className="text-sm font-mono text-gray-200">{format ? format(value) : value}</span>
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-brand-500"
      />
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-gray-300">{label}</span>
      <span className="text-sm font-mono text-gray-400">{value}</span>
    </div>
  )
}

function InstrumentPicker({ label, selected, onChange }) {
  const toggle = (inst) => {
    if (selected.includes(inst)) {
      onChange(selected.filter(i => i !== inst))
    } else {
      onChange([...selected, inst])
    }
  }

  return (
    <div className="py-1">
      <p className="text-sm text-gray-300 mb-2">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {ALL_INSTRUMENTS.map(inst => {
          const active = selected.includes(inst)
          return (
            <button
              key={inst}
              onClick={() => toggle(inst)}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                active
                  ? 'bg-brand-500/20 text-brand-300 border border-brand-500/40'
                  : 'bg-gray-700/50 text-gray-500 border border-gray-600/50 hover:text-gray-300'
              }`}
            >
              {INSTRUMENT_META[inst]?.name || inst}
            </button>
          )
        })}
      </div>
    </div>
  )
}
