import { useState } from 'react'
import { useConfig } from '../hooks/useStreamData'
import { saveConfig, pollWorkflow } from '../lib/api'
import { INSTRUMENT_META, STRATEGY_INFO, STRATEGY_PARAMS, RISK_PRESETS } from '../lib/constants'
import { SETTING_HELP } from '../lib/glossary'
import HelpTooltip from '../components/HelpTooltip'
import HowItWorks from '../components/HowItWorks'

const ALL_INSTRUMENTS = Object.keys(INSTRUMENT_META)
const ALL_STRATEGIES = Object.keys(STRATEGY_INFO)

const NEWS_SOURCES = [
  { key: 'bbc', label: 'BBC Business', desc: 'RSS feed from BBC business section' },
  { key: 'cnbc', label: 'CNBC Business', desc: 'RSS feed from CNBC business section' },
  { key: 'gdelt', label: 'GDELT', desc: 'Global event database — wide coverage of world events' },
  { key: 'calendar', label: 'Economic Calendar', desc: 'Scheduled economic data releases (NFP, CPI, rate decisions)' },
]

export default function Settings() {
  const { config, loading, refresh } = useConfig()
  const [saving, setSaving] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)
  const [changes, setChanges] = useState({})
  const [expandedStrategy, setExpandedStrategy] = useState(null)

  function setOverride(key, value) {
    setChanges(prev => ({ ...prev, [key]: value }))
  }

  function getValue(dotKey, fallback) {
    if (dotKey in changes) return changes[dotKey]
    const parts = dotKey.split('.')
    let val = config
    for (const p of parts) {
      if (val == null) return fallback
      val = val[p]
    }
    return val ?? fallback
  }

  function applyPreset(presetKey) {
    const preset = RISK_PRESETS[presetKey]
    if (!preset) return
    const newChanges = { ...changes }
    for (const [key, value] of Object.entries(preset.values)) {
      newChanges[key] = value
    }
    setChanges(newChanges)
    setStatusMsg({ type: 'info', text: `Applied "${preset.label}" preset. Click Save to apply.` })
  }

  async function handleSave() {
    if (Object.keys(changes).length === 0) {
      setStatusMsg({ type: 'info', text: 'No changes to save.' })
      return
    }
    setSaving(true)
    setStatusMsg({ type: 'info', text: 'Saving config...' })
    try {
      const result = await saveConfig(changes)
      if (result.status === 'ok' && !result.run_id) {
        // Direct save succeeded — fast path
        setStatusMsg({ type: 'ok', text: 'Config saved! Changes take effect on next trading cycle.' })
        setChanges({})
        setTimeout(refresh, 3000)
      } else if (result.run_id) {
        // Workflow-based save
        setStatusMsg({ type: 'info', text: `Workflow started (${result.run_id}). Waiting...` })
        const wfResult = await pollWorkflow(result.run_id, (status) => {
          setStatusMsg({ type: 'info', text: `Workflow ${status}...` })
        })
        if (wfResult.conclusion === 'success' || wfResult.status === 'completed') {
          setStatusMsg({ type: 'ok', text: 'Config saved! Refreshing...' })
          setChanges({})
          setTimeout(refresh, 5000)
        } else {
          setStatusMsg({ type: 'error', text: `Workflow ${wfResult.conclusion || wfResult.status}` })
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
  const riskPct = getValue('risk.max_risk_per_trade', 0.01)
  const capitalNews = getValue('streams.news_stream.capital_allocation', 100)
  const capitalStrategy = getValue('streams.strategy_stream.capital_allocation', 100)
  const maxDailyLoss = getValue('risk.max_daily_loss_per_stream', 0.03)

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

      <HowItWorks>
        <p>These settings control how the trading system behaves. Changes are saved to the database and take effect on the next trading cycle.</p>
        <p>If you're new, start with the <strong>risk presets</strong> below — choose Conservative to minimize risk while learning.</p>
      </HowItWorks>

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
          description="When paused, the hourly cron will skip without analyzing markets or placing trades. Manual runs from the UI still work."
          checked={getValue('scheduler.paused', false)}
          onChange={v => setOverride('scheduler.paused', v)}
        />
        <InfoRow label="Interval" value={getValue('scheduler.interval', '1h')} />
      </Section>

      {/* News Stream */}
      <Section title="News Stream">
        <ToggleRow
          label="Enabled"
          description="When disabled, no news signals or trades are generated."
          checked={getValue('streams.news_stream.enabled', false)}
          onChange={v => setOverride('streams.news_stream.enabled', v)}
        />
        <NumberRow
          label="Capital Allocation"
          value={getValue('streams.news_stream.capital_allocation', 100)}
          onChange={v => setOverride('streams.news_stream.capital_allocation', v)}
          step={1000}
          settingKey="streams.news_stream.capital_allocation"
        />
        <SliderRow
          label="Min Confidence"
          value={getValue('streams.news_stream.min_confidence', 0.6)}
          onChange={v => setOverride('streams.news_stream.min_confidence', v)}
          min={0.1} max={0.95} step={0.05}
          format={v => `${(v * 100).toFixed(0)}%`}
          settingKey="streams.news_stream.min_confidence"
        />
        <SliderRow
          label="News Lookback Hours"
          value={getValue('streams.news_stream.news_lookback_hours', 4)}
          onChange={v => setOverride('streams.news_stream.news_lookback_hours', v)}
          min={1} max={12} step={1}
          format={v => `${v}h`}
          settingKey="streams.news_stream.news_lookback_hours"
        />
        <InstrumentPicker
          label="Instruments"
          selected={getValue('streams.news_stream.instruments', [])}
          onChange={v => setOverride('streams.news_stream.instruments', v)}
        />

        {/* News Sources */}
        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-2 flex items-center">
            News Sources
            <HelpTooltip text="Toggle individual news sources on or off. Disabling a source means its headlines won't be fetched or analyzed." />
          </p>
          {NEWS_SOURCES.map(src => (
            <div key={src.key} className="flex items-center justify-between py-1">
              <div>
                <span className="text-xs text-gray-400">{src.label}</span>
                <p className="text-[10px] text-gray-600">{src.desc}</p>
              </div>
              <button
                onClick={() => {
                  const current = getValue(`streams.news_stream.sources.${src.key}.enabled`, true)
                  setOverride(`streams.news_stream.sources.${src.key}.enabled`, !current)
                }}
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  getValue(`streams.news_stream.sources.${src.key}.enabled`, true) ? 'bg-brand-500' : 'bg-gray-600'
                }`}
              >
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  getValue(`streams.news_stream.sources.${src.key}.enabled`, true) ? 'left-5' : 'left-0.5'
                }`} />
              </button>
            </div>
          ))}
        </div>
      </Section>

      {/* Strategy Stream */}
      <Section title="Strategy Stream">
        <ToggleRow
          label="Enabled"
          description="Enable or disable all mechanical strategies. Individual strategies can be toggled below."
          checked={getValue('streams.strategy_stream.enabled', false)}
          onChange={v => setOverride('streams.strategy_stream.enabled', v)}
        />
        <NumberRow
          label="Capital Allocation"
          value={getValue('streams.strategy_stream.capital_allocation', 100)}
          onChange={v => setOverride('streams.strategy_stream.capital_allocation', v)}
          step={1000}
          settingKey="streams.strategy_stream.capital_allocation"
        />
        <InstrumentPicker
          label="Instruments"
          selected={getValue('streams.strategy_stream.instruments', [])}
          onChange={v => setOverride('streams.strategy_stream.instruments', v)}
        />

        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-2">Strategies</p>
          {(getValue('streams.strategy_stream.strategies', []) || []).map((strat, i) => {
            const info = STRATEGY_INFO[strat.name]
            const params = STRATEGY_PARAMS[strat.name] || []
            const isExpanded = expandedStrategy === strat.name

            return (
              <div key={strat.name} className="border-b border-gray-700/30 pb-2 mb-2">
                <div className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        const strategies = [...getValue('streams.strategy_stream.strategies', [])]
                        strategies[i] = { ...strategies[i], enabled: !(strat.enabled !== false) }
                        setOverride('streams.strategy_stream.strategies', strategies)
                      }}
                      className={`relative w-10 h-5 rounded-full transition-colors ${strat.enabled !== false ? 'bg-brand-500' : 'bg-gray-600'}`}
                    >
                      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${strat.enabled !== false ? 'left-5' : 'left-0.5'}`} />
                    </button>
                    <span className="text-xs text-gray-400 capitalize">{strat.name.replace('_', ' ')}</span>
                    {info && <HelpTooltip term={info.glossaryKey || strat.name} />}
                  </div>
                  {params.length > 0 && (
                    <button
                      onClick={() => setExpandedStrategy(isExpanded ? null : strat.name)}
                      className="text-[10px] text-blue-400 hover:text-blue-300"
                    >
                      {isExpanded ? 'Hide params' : 'Tune params'}
                    </button>
                  )}
                </div>

                {info && <p className="text-[10px] text-gray-600 ml-12 mb-1">{info.explanation}</p>}

                {/* Strategy Parameters (expandable) */}
                {isExpanded && params.length > 0 && (
                  <div className="ml-12 mt-2 bg-gray-900/30 rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-gray-500 uppercase">Parameters</span>
                      <button
                        onClick={() => {
                          const strategies = [...getValue('streams.strategy_stream.strategies', [])]
                          const defaults = {}
                          params.forEach(p => { defaults[p.key] = p.default })
                          strategies[i] = { ...strategies[i], params: defaults }
                          setOverride('streams.strategy_stream.strategies', strategies)
                        }}
                        className="text-[10px] text-gray-500 hover:text-gray-300"
                      >
                        Reset to defaults
                      </button>
                    </div>
                    {params.map(param => {
                      const currentVal = strat.params?.[param.key] ?? param.default
                      const updateParam = (val) => {
                        const strategies = [...getValue('streams.strategy_stream.strategies', [])]
                        strategies[i] = {
                          ...strategies[i],
                          params: { ...strategies[i].params, [param.key]: val },
                        }
                        setOverride('streams.strategy_stream.strategies', strategies)
                      }

                      if (param.type === 'readonly') {
                        return (
                          <div key={param.key} className="flex items-center justify-between py-0.5">
                            <span className="text-xs text-gray-400 flex items-center">
                              {param.label}
                              {param.glossaryKey && <HelpTooltip term={param.glossaryKey} />}
                            </span>
                            <span className="text-xs font-mono text-gray-500">{currentVal}</span>
                          </div>
                        )
                      }

                      if (param.type === 'select') {
                        return (
                          <div key={param.key} className="flex items-center justify-between py-0.5">
                            <span className="text-xs text-gray-400 flex items-center">
                              {param.label}
                              {param.glossaryKey && <HelpTooltip term={param.glossaryKey} />}
                            </span>
                            <select
                              value={currentVal}
                              onChange={e => updateParam(e.target.value)}
                              className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-0.5 text-gray-300"
                            >
                              {param.options.map(opt => (
                                <option key={opt} value={opt}>{opt}</option>
                              ))}
                            </select>
                          </div>
                        )
                      }

                      if (param.type === 'slider') {
                        return (
                          <div key={param.key} className="py-0.5">
                            <div className="flex items-center justify-between mb-0.5">
                              <span className="text-xs text-gray-400 flex items-center">
                                {param.label}
                                {param.glossaryKey && <HelpTooltip term={param.glossaryKey} />}
                              </span>
                              <span className="text-xs font-mono text-gray-300">{currentVal}</span>
                            </div>
                            <input
                              type="range"
                              value={currentVal}
                              min={param.min} max={param.max} step={param.step}
                              onChange={e => updateParam(Number(e.target.value))}
                              className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-brand-500"
                            />
                          </div>
                        )
                      }

                      // number type
                      return (
                        <div key={param.key} className="flex items-center justify-between py-0.5">
                          <span className="text-xs text-gray-400 flex items-center">
                            {param.label}
                            {param.glossaryKey && <HelpTooltip term={param.glossaryKey} />}
                          </span>
                          <input
                            type="number"
                            value={currentVal}
                            min={param.min} max={param.max} step={param.step}
                            onChange={e => updateParam(Number(e.target.value))}
                            className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-0.5 text-xs text-gray-300 text-right font-mono"
                          />
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </Section>

      {/* Risk Parameters */}
      <Section title="Risk Management">
        {/* Presets */}
        <div className="mb-4">
          <p className="text-xs text-gray-500 mb-2 flex items-center">
            Risk Presets
            <HelpTooltip term="risk_profile" />
          </p>
          <div className="flex gap-2">
            {Object.entries(RISK_PRESETS).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => applyPreset(key)}
                className="px-3 py-1.5 text-xs rounded border border-gray-600/50 bg-gray-700/50 text-gray-300 hover:bg-gray-600/50 hover:text-gray-200 transition-colors"
              >
                <div className="font-medium">{preset.label}</div>
                <div className="text-[10px] text-gray-500">{preset.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Leverage */}
        <SelectRow
          label="Leverage"
          value={getValue('risk.leverage', 1)}
          onChange={v => setOverride('risk.leverage', v)}
          options={[
            { value: 1, label: 'None (1:1)' },
            { value: 2, label: '2:1' },
            { value: 5, label: '5:1' },
            { value: 10, label: '10:1' },
            { value: 20, label: '20:1' },
            { value: 30, label: '30:1' },
          ]}
          settingKey="risk.leverage"
        />

        {/* Live risk estimate */}
        <div className="bg-blue-900/10 border border-blue-800/20 rounded-lg p-3 mb-4 text-xs text-blue-300">
          At current settings: max <strong>€{(capitalNews * riskPct).toFixed(0)}</strong> per trade,
          max <strong>€{(capitalNews * maxDailyLoss).toFixed(0)}</strong> daily loss per stream
        </div>

        <SliderRow
          label="Max Risk Per Trade"
          value={getValue('risk.max_risk_per_trade', 0.01)}
          onChange={v => setOverride('risk.max_risk_per_trade', v)}
          min={0.005} max={0.05} step={0.005}
          format={v => `${(v * 100).toFixed(1)}%`}
          settingKey="risk.max_risk_per_trade"
        />
        <NumberRow
          label="Max Open Positions (per stream)"
          value={getValue('risk.max_open_positions_per_stream', 5)}
          onChange={v => setOverride('risk.max_open_positions_per_stream', v)}
          min={1} max={20} step={1}
          settingKey="risk.max_open_positions_per_stream"
        />
        <SliderRow
          label="Max Daily Loss (per stream)"
          value={getValue('risk.max_daily_loss_per_stream', 0.03)}
          onChange={v => setOverride('risk.max_daily_loss_per_stream', v)}
          min={0.01} max={0.10} step={0.01}
          format={v => `${(v * 100).toFixed(0)}%`}
          settingKey="risk.max_daily_loss_per_stream"
        />
        <NumberRow
          label="Max Correlated Positions"
          value={getValue('risk.max_correlated_positions', 2)}
          onChange={v => setOverride('risk.max_correlated_positions', v)}
          min={1} max={10} step={1}
          settingKey="risk.max_correlated_positions"
        />
        <SliderRow
          label="Default R:R Ratio"
          value={getValue('risk.default_rr_ratio', 1.5)}
          onChange={v => setOverride('risk.default_rr_ratio', v)}
          min={1.0} max={4.0} step={0.1}
          format={v => `${v.toFixed(1)}:1`}
          settingKey="risk.default_rr_ratio"
        />
        <InfoRow label="Stop Loss Method" value={getValue('risk.stop_loss_method', 'atr')} settingKey="risk.stop_loss_method" />
        <SliderRow
          label="ATR Multiplier"
          value={getValue('risk.atr_multiplier', 1.5)}
          onChange={v => setOverride('risk.atr_multiplier', v)}
          min={0.5} max={3.0} step={0.1}
          format={v => `${v.toFixed(1)}x`}
          settingKey="risk.atr_multiplier"
        />
        <NumberRow
          label="ATR Period"
          value={getValue('risk.atr_period', 14)}
          onChange={v => setOverride('risk.atr_period', v)}
          min={5} max={50} step={1}
          settingKey="risk.atr_period"
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

function NumberRow({ label, value, onChange, min, max, step = 1, settingKey }) {
  const helpInfo = settingKey ? SETTING_HELP[settingKey] : null
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-gray-300 flex items-center">
        {label}
        {helpInfo?.glossaryKey && <HelpTooltip term={helpInfo.glossaryKey} />}
        {helpInfo && !helpInfo.glossaryKey && <HelpTooltip text={helpInfo.help} />}
      </span>
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

function SliderRow({ label, value, onChange, min, max, step, format, settingKey }) {
  const helpInfo = settingKey ? SETTING_HELP[settingKey] : null
  return (
    <div className="py-1">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-gray-300 flex items-center">
          {label}
          {helpInfo?.glossaryKey && <HelpTooltip term={helpInfo.glossaryKey} />}
          {helpInfo && !helpInfo.glossaryKey && <HelpTooltip text={helpInfo.help} />}
        </span>
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

function InfoRow({ label, value, settingKey }) {
  const helpInfo = settingKey ? SETTING_HELP[settingKey] : null
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-gray-300 flex items-center">
        {label}
        {helpInfo && <HelpTooltip text={helpInfo.help} />}
      </span>
      <span className="text-sm font-mono text-gray-400">{value}</span>
    </div>
  )
}

function SelectRow({ label, value, onChange, options, settingKey }) {
  const helpInfo = settingKey ? SETTING_HELP[settingKey] : null
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-gray-300 flex items-center">
        {label}
        {helpInfo?.glossaryKey && <HelpTooltip term={helpInfo.glossaryKey} />}
        {helpInfo && !helpInfo.glossaryKey && <HelpTooltip text={helpInfo.help} />}
      </span>
      <select
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-28 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200 text-right font-mono"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
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
