import { useState } from 'react'
import { useDashboard, useHybrids } from '../hooks/useStreamData'
import { triggerStream, pollWorkflow } from '../lib/api'
import MetricTile from '../components/MetricTile'
import HelpTooltip from '../components/HelpTooltip'
import HowItWorks from '../components/HowItWorks'
import { formatPnl, STRATEGY_INFO } from '../lib/constants'

const AVAILABLE_MODULES = [
  { type: 'news', name: 'News Signals', icon: 'N' },
  ...Object.keys(STRATEGY_INFO).map(name => ({
    type: 'strategy', name, icon: 'S',
  })),
]

const COMBINER_MODES = [
  { value: 'weighted', label: 'Weighted Score', desc: 'Sum of weighted signals — the higher the total weight in one direction, the stronger the signal.', glossaryKey: 'combiner_weighted' },
  { value: 'all_agree', label: 'All Must Agree', desc: 'Every module must produce the same direction. Strictest mode — fewest trades but highest conviction.', glossaryKey: 'combiner_all_agree' },
  { value: 'majority', label: 'Majority Vote', desc: 'More than half of modules must agree. A balanced approach.', glossaryKey: 'combiner_majority' },
  { value: 'any', label: 'Any One Triggers', desc: 'If any single module produces a signal, a trade is placed. Loosest mode — most trades.', glossaryKey: 'combiner_any' },
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
  const [confirmDelete, setConfirmDelete] = useState(null)

  const anyActive = savedHybrids.some(h => h.is_active)

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

  function handleToggle(h) {
    const newActive = !h.is_active
    handleWorkflow('toggle-hybrid', 'all', `${newActive ? 'Activate' : 'Deactivate'} ${h.name}`, {
      hybrid_id: h.id,
      hybrid_active: newActive ? 1 : 0,
    })
  }

  function handleDelete(h) {
    setConfirmDelete(null)
    handleWorkflow('delete-hybrid', 'all', `Delete ${h.name}`, { hybrid_id: h.id })
  }

  function handleToggleAll() {
    const newActive = !anyActive
    handleWorkflow('toggle-all-hybrids', 'all', `${newActive ? 'Enable' : 'Disable'} all hybrids`, {
      hybrid_active: newActive ? 1 : 0,
    })
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

  // Build a lookup from dashboard data by hybrid name for performance metrics
  const dashByName = {}
  for (const dh of dashHybrids) {
    const name = dh.id.replace('hybrid:', '')
    dashByName[name] = dh
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Custom Hybrid</h2>
          <p className="text-sm text-gray-500 mt-1">Combine news + strategies into custom recipes</p>
        </div>
        <div className="flex items-center gap-3">
          {savedHybrids.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400">Hybrid Trading</span>
              <button
                onClick={handleToggleAll}
                className={`relative w-10 h-5 rounded-full transition-colors ${anyActive ? 'bg-brand-500' : 'bg-gray-600'}`}
              >
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${anyActive ? 'left-5' : 'left-0.5'}`} />
              </button>
            </div>
          )}
          <button
            onClick={() => handleWorkflow('tick', 'hybrid', 'Hybrid stream')}
            disabled={running || saving || !anyActive}
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

      <HowItWorks>
        <p>Hybrids let you combine multiple signal sources into a single trading recipe. For example, you could require both the AI news analysis AND the momentum strategy to agree before placing a trade.</p>
        <p><strong>Modules</strong> are the signal sources (News AI, or any of the 5 strategies). Each module gets a weight and an optional "must participate" flag.</p>
        <p><strong>Combiner mode</strong> controls how module signals are merged into a final trading decision.</p>
        <p>This is the most customizable part of the system — experiment with different combinations to find what works best.</p>
      </HowItWorks>

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

      {/* Saved Hybrids with toggle/delete and optional dashboard metrics */}
      {savedHybrids.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {savedHybrids.map(h => {
            const perf = dashByName[h.name]
            return (
              <div key={h.id || h.name} className={`bg-gray-800/50 rounded-lg border p-4 ${h.is_active ? 'border-gray-700/50' : 'border-gray-700/30 opacity-60'}`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleToggle(h)}
                      className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ${h.is_active ? 'bg-brand-500' : 'bg-gray-600'}`}
                    >
                      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${h.is_active ? 'left-5' : 'left-0.5'}`} />
                    </button>
                    <h3 className="font-semibold">{h.name}</h3>
                  </div>
                  {confirmDelete === h.id ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">Delete?</span>
                      <button onClick={() => handleDelete(h)} className="text-xs text-red-400 hover:text-red-300 font-medium">Yes</button>
                      <button onClick={() => setConfirmDelete(null)} className="text-xs text-gray-400 hover:text-gray-300">No</button>
                    </div>
                  ) : (
                    <button onClick={() => setConfirmDelete(h.id)} className="text-xs text-red-400/70 hover:text-red-400">
                      Delete
                    </button>
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {h.combiner_mode} | {(h.instruments || []).join(', ')}
                </div>
                {perf && (
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    <MetricTile label="P&L" value={formatPnl(perf.total_pnl)} positive={perf.total_pnl > 0} helpTerm="pnl" />
                    <MetricTile label="Trades" value={perf.trade_count} />
                    <MetricTile label="Win %" value={`${(perf.win_rate * 100).toFixed(0)}%`} helpTerm="win_rate" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {savedHybrids.length === 0 && !editing && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-8 text-center">
          <p className="text-gray-400 mb-2">No hybrid strategies yet</p>
          <p className="text-gray-500 text-sm">Create one by combining news signals with mechanical strategies. Click "+ Create New Hybrid" above to get started.</p>
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
                <p className="text-gray-500 text-sm">Click modules on the left to add them to your recipe.</p>
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
                        <label className="text-xs text-gray-500 flex items-center">
                          Weight
                          <HelpTooltip term="module_weight" />
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
                          <HelpTooltip term="must_participate" />
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Combiner Mode */}
              <h4 className="text-xs text-gray-500 uppercase tracking-wider mt-4 mb-2 flex items-center">
                Combiner Mode
              </h4>
              <div className="space-y-1">
                {COMBINER_MODES.map(mode => (
                  <label key={mode.value} className="flex items-start gap-2 p-2 rounded hover:bg-gray-900/50 cursor-pointer">
                    <input
                      type="radio"
                      name="combiner"
                      value={mode.value}
                      checked={combinerMode === mode.value}
                      onChange={() => setCombinerMode(mode.value)}
                      className="mt-0.5"
                    />
                    <div>
                      <div className="text-sm flex items-center">
                        {mode.label}
                        <HelpTooltip term={mode.glossaryKey} />
                      </div>
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
