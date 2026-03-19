import { useState } from 'react'
import { useDashboard, useHybrids } from '../hooks/useStreamData'
import { triggerStream, pollWorkflow } from '../lib/api'
import MetricTile from '../components/MetricTile'
import { formatPnl, STRATEGY_INFO } from '../lib/constants'

const AVAILABLE_MODULES = [
  { type: 'news', name: 'News Signals', icon: 'N' },
  ...Object.keys(STRATEGY_INFO).map(name => ({
    type: 'strategy', name, icon: 'S',
  })),
]

const COMBINER_MODES = [
  { value: 'weighted', label: 'Weighted Score', desc: 'Sum of weighted signals' },
  { value: 'all_agree', label: 'All Must Agree', desc: 'Strictest — fewest trades' },
  { value: 'majority', label: 'Majority Vote', desc: 'More than half agree' },
  { value: 'any', label: 'Any One Triggers', desc: 'Loosest — most trades' },
]

const DEFAULT_INSTRUMENTS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'BCO_USD']

export default function HybridBuilder() {
  const { data: dashboard, refresh: refreshDashboard } = useDashboard()
  const { hybrids: savedHybrids, refresh: refreshHybrids } = useHybrids()
  const dashHybrids = dashboard?.streams?.filter(s => s.id.startsWith('hybrid:')) || []

  const [editing, setEditing] = useState(false)
  const [hybridName, setHybridName] = useState('')
  const [selectedModules, setSelectedModules] = useState([])
  const [combinerMode, setCombinerMode] = useState('weighted')
  const [selectedInstruments, setSelectedInstruments] = useState([...DEFAULT_INSTRUMENTS])
  const [running, setRunning] = useState(false)
  const [saving, setSaving] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)

  async function handleWorkflow(mode, stream, label, extra = {}) {
    const setter = mode === 'save-hybrid' ? setSaving : setRunning
    setter(true)
    setStatusMsg({ type: 'info', text: `Dispatching ${label}...` })
    try {
      const { run_id } = await triggerStream({ mode, stream, ...extra })
      if (run_id) {
        setStatusMsg({ type: 'info', text: `Workflow started. ${label}...` })
        const result = await pollWorkflow(run_id, (status) => {
          setStatusMsg({ type: 'info', text: `Workflow ${status}...` })
        })
        if (result.conclusion === 'success' || result.status === 'completed') {
          setStatusMsg({ type: 'ok', text: `${label} complete!` })
          setTimeout(() => { refreshDashboard(); refreshHybrids() }, 5000)
          if (mode === 'save-hybrid') setEditing(false)
        } else {
          setStatusMsg({ type: 'error', text: `Workflow ${result.conclusion || result.status}` })
        }
      } else {
        setStatusMsg({ type: 'ok', text: `${label} dispatched. Refresh in ~2 min.` })
      }
    } catch (e) {
      setStatusMsg({ type: 'error', text: e.message })
    } finally {
      setter(false)
    }
  }

  function handleSaveHybrid() {
    if (!hybridName.trim()) {
      setStatusMsg({ type: 'error', text: 'Please enter a hybrid name' })
      return
    }
    if (selectedModules.length < 2) {
      setStatusMsg({ type: 'error', text: 'Please select at least 2 modules' })
      return
    }

    const hybrid = {
      name: hybridName.trim(),
      description: `${combinerMode} combiner with ${selectedModules.length} modules`,
      modules: selectedModules.map(m => ({
        type: m.type,
        name: m.type === 'news' ? 'news' : m.name,
        weight: m.weight,
        must_participate: m.mustParticipate,
      })),
      combiner_mode: combinerMode,
      instruments: selectedInstruments,
      interval: '1h',
      is_active: 1,
    }

    handleWorkflow('save-hybrid', 'all', 'Hybrid save', { hybrid })
  }

  const addModule = (mod) => {
    if (!selectedModules.find(m => m.name === mod.name)) {
      setSelectedModules([...selectedModules, { ...mod, weight: 0.5, mustParticipate: false }])
    }
  }

  const removeModule = (name) => {
    setSelectedModules(selectedModules.filter(m => m.name !== name))
  }

  const updateModule = (name, field, value) => {
    setSelectedModules(selectedModules.map(m =>
      m.name === name ? { ...m, [field]: value } : m
    ))
  }

  const toggleInstrument = (inst) => {
    setSelectedInstruments(prev =>
      prev.includes(inst) ? prev.filter(i => i !== inst) : [...prev, inst]
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Custom Hybrid</h2>
          <p className="text-sm text-gray-500 mt-1">Combine news + strategies into custom recipes</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleWorkflow('tick', 'hybrid', 'Hybrid stream')}
            disabled={running || saving || dashHybrids.length === 0}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium rounded-lg transition-colors"
          >
            {running ? 'Running...' : 'Run Hybrid Stream'}
          </button>
          <button
            onClick={() => setEditing(!editing)}
            className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm hover:bg-brand-600 transition-colors"
          >
            {editing ? 'Cancel' : '+ Create New Hybrid'}
          </button>
        </div>
      </div>

      {/* Status banner */}
      {statusMsg && (
        <div className={`rounded-lg p-4 mb-6 text-sm border ${
          statusMsg.type === 'ok' ? 'bg-green-900/20 border-green-800/50 text-green-300'
          : statusMsg.type === 'error' ? 'bg-red-900/20 border-red-800/50 text-red-300'
          : 'bg-blue-900/20 border-blue-800/50 text-blue-300'
        }`}>
          {statusMsg.text}
        </div>
      )}

      {/* Existing Hybrids from Dashboard */}
      {dashHybrids.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {dashHybrids.map(h => (
            <div key={h.id} className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4">
              <h3 className="font-semibold">{h.name}</h3>
              <div className="grid grid-cols-3 gap-2 mt-2">
                <MetricTile label="P&L" value={formatPnl(h.total_pnl)} positive={h.total_pnl > 0} />
                <MetricTile label="Trades" value={h.trade_count} />
                <MetricTile label="Win %" value={`${(h.win_rate * 100).toFixed(0)}%`} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Saved Hybrids from DB */}
      {savedHybrids.length > 0 && dashHybrids.length === 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {savedHybrids.map(h => (
            <div key={h.id || h.name} className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4">
              <h3 className="font-semibold">{h.name}</h3>
              <div className="text-xs text-gray-500 mt-1">
                {h.combiner_mode} | {(h.instruments || []).join(', ')} |
                {h.is_active ? ' Active' : ' Inactive'}
              </div>
            </div>
          ))}
        </div>
      )}

      {dashHybrids.length === 0 && savedHybrids.length === 0 && !editing && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-8 text-center">
          <p className="text-gray-400 mb-2">No hybrid strategies yet</p>
          <p className="text-gray-500 text-sm">Create one by combining news signals with mechanical strategies</p>
        </div>
      )}

      {/* Builder */}
      {editing && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-6">
          <h3 className="font-semibold mb-4">Build Recipe</h3>

          <div className="mb-4">
            <label className="text-xs text-gray-500 block mb-1">Hybrid Name</label>
            <input
              type="text"
              value={hybridName}
              onChange={e => setHybridName(e.target.value)}
              placeholder="e.g., Geopolitical Edge"
              className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm w-full max-w-xs"
            />
          </div>

          {/* Instruments */}
          <div className="mb-4">
            <label className="text-xs text-gray-500 block mb-2">Instruments</label>
            <div className="flex flex-wrap gap-2">
              {DEFAULT_INSTRUMENTS.map(inst => (
                <button
                  key={inst}
                  onClick={() => toggleInstrument(inst)}
                  className={`text-xs px-2 py-1 rounded border transition-colors ${
                    selectedInstruments.includes(inst)
                      ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
                      : 'bg-gray-900/50 border-gray-700/50 text-gray-500'
                  }`}
                >
                  {inst}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Available Modules */}
            <div>
              <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">Available Modules</h4>
              <div className="space-y-2">
                {AVAILABLE_MODULES.map(mod => (
                  <button
                    key={mod.name}
                    onClick={() => addModule(mod)}
                    disabled={selectedModules.find(m => m.name === mod.name)}
                    className="w-full flex items-center gap-3 p-3 bg-gray-900/50 rounded border border-gray-700/50
                               hover:border-brand-500/50 transition-colors text-left disabled:opacity-30"
                  >
                    <span className={`w-8 h-8 rounded flex items-center justify-center text-xs font-bold ${
                      mod.type === 'news' ? 'bg-blue-500/20 text-blue-400' : 'bg-green-500/20 text-green-400'
                    }`}>
                      {mod.icon}
                    </span>
                    <div>
                      <div className="text-sm font-medium capitalize">{mod.name.replace('_', ' ')}</div>
                      <div className="text-xs text-gray-500">
                        {mod.type === 'news' ? 'LLM news analysis' : STRATEGY_INFO[mod.name]?.desc}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Selected Modules */}
            <div>
              <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-3">Recipe</h4>
              {selectedModules.length === 0 ? (
                <p className="text-gray-500 text-sm">Click modules on the left to add them</p>
              ) : (
                <div className="space-y-3">
                  {selectedModules.map((mod) => (
                    <div key={mod.name} className="bg-gray-900/50 rounded border border-gray-700/50 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium capitalize">{mod.name.replace('_', ' ')}</span>
                        <button onClick={() => removeModule(mod.name)} className="text-xs text-red-400 hover:text-red-300">
                          Remove
                        </button>
                      </div>
                      <div className="flex items-center gap-4">
                        <label className="text-xs text-gray-500">
                          Weight:
                          <input
                            type="number"
                            min="0" max="1" step="0.1"
                            value={mod.weight}
                            onChange={e => updateModule(mod.name, 'weight', parseFloat(e.target.value))}
                            className="ml-2 w-16 bg-gray-800 border border-gray-700 rounded px-2 py-0.5 text-xs"
                          />
                        </label>
                        <label className="text-xs text-gray-500 flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={mod.mustParticipate}
                            onChange={e => updateModule(mod.name, 'mustParticipate', e.target.checked)}
                            className="rounded"
                          />
                          Must participate
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Combiner Mode */}
              <h4 className="text-xs text-gray-500 uppercase tracking-wider mt-4 mb-2">Combiner Mode</h4>
              <div className="space-y-1">
                {COMBINER_MODES.map(mode => (
                  <label key={mode.value} className="flex items-center gap-2 p-2 rounded hover:bg-gray-900/50 cursor-pointer">
                    <input
                      type="radio"
                      name="combiner"
                      value={mode.value}
                      checked={combinerMode === mode.value}
                      onChange={() => setCombinerMode(mode.value)}
                    />
                    <div>
                      <div className="text-sm">{mode.label}</div>
                      <div className="text-xs text-gray-500">{mode.desc}</div>
                    </div>
                  </label>
                ))}
              </div>

              {/* Action buttons */}
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleSaveHybrid}
                  disabled={saving || !hybridName.trim() || selectedModules.length < 2}
                  className="px-4 py-2 bg-brand-500 text-white rounded text-sm hover:bg-brand-600 disabled:bg-gray-700 disabled:text-gray-500 transition-colors"
                >
                  {saving ? 'Saving...' : 'Save & Activate'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
