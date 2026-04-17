import { useState, useEffect, useCallback } from 'react'
import { NavLink } from 'react-router-dom'
import { Settings, ChevronUp, Play, Loader, RefreshCw } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/llm', label: 'LLM Analysis' },
  { to: '/strategies', label: 'Strategies' },
]

function useWorkflowTrigger(endpoint, body) {
  const [state, setState] = useState('idle') // idle | running | done | error
  const [runId, setRunId] = useState(null)

  const trigger = useCallback(async () => {
    if (state === 'running') return
    setState('running')
    try {
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        ...(body ? { body: JSON.stringify(body) } : {}),
      })
      const data = await resp.json()
      if (!resp.ok || data.error) { setState('error'); return }
      setRunId(data.run_id)
    } catch { setState('error') }
  }, [state, endpoint, body])

  useEffect(() => {
    if (state !== 'running') return
    const poll = setInterval(async () => {
      try {
        const url = runId ? `/api/workflow-status?run_id=${runId}` : '/api/workflow-status'
        const data = await (await fetch(url)).json()
        if (data.status === 'completed') {
          setState(data.conclusion === 'success' ? 'done' : 'error')
          clearInterval(poll)
          setTimeout(() => setState('idle'), 3000)
        }
      } catch { /* keep polling */ }
    }, 5000)
    return () => clearInterval(poll)
  }, [state, runId])

  return [state, trigger]
}

export default function PillNav({ expanded, onToggleExpand }) {
  const [runState, triggerRun] = useWorkflowTrigger('/api/trigger-stream', { mode: 'tick' })
  const [syncState, triggerSync] = useWorkflowTrigger('/api/trigger-sync')

  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-2">
      <div
        className="font-serif text-[11px] tracking-[0.22em] uppercase text-[rgba(28,25,23,0.55)]"
      >
        One Shot Forex
      </div>
      <nav
      className="flex items-center gap-1 px-2 py-1.5 rounded-pill max-w-[520px]"
      style={{
        background: 'rgba(28, 25, 23, 0.92)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)',
      }}
    >
      <button
        onClick={triggerRun}
        disabled={runState === 'running'}
        className={`p-2.5 transition-colors duration-150 rounded-[10px] ${
          runState === 'running'
            ? 'text-[rgba(250,250,249,0.8)] animate-pulse'
            : runState === 'done'
            ? 'text-emerald-400'
            : runState === 'error'
            ? 'text-red-400'
            : 'text-[rgba(250,250,249,0.5)] hover:text-[rgba(250,250,249,0.75)]'
        }`}
        aria-label="Run pipeline"
      >
        {runState === 'running' ? <Loader size={18} className="animate-spin" /> : <Play size={18} />}
      </button>

      <button
        onClick={triggerSync}
        disabled={syncState === 'running'}
        className={`p-2.5 transition-colors duration-150 rounded-[10px] ${
          syncState === 'running'
            ? 'text-[rgba(250,250,249,0.8)]'
            : syncState === 'done'
            ? 'text-emerald-400'
            : syncState === 'error'
            ? 'text-red-400'
            : 'text-[rgba(250,250,249,0.5)] hover:text-[rgba(250,250,249,0.75)]'
        }`}
        aria-label="Sync positions"
      >
        <RefreshCw size={18} className={syncState === 'running' ? 'animate-spin' : ''} />
      </button>

      {NAV_ITEMS.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `px-4 py-2.5 text-[13px] font-medium transition-colors duration-150 rounded-[10px] whitespace-nowrap ${
              isActive
                ? 'text-[#FAFAF9]'
                : 'text-[rgba(250,250,249,0.5)] hover:text-[rgba(250,250,249,0.75)]'
            }`
          }
          style={({ isActive }) =>
            isActive ? { background: 'rgba(250, 250, 249, 0.12)' } : undefined
          }
        >
          {label}
        </NavLink>
      ))}

      <NavLink
        to="/settings"
        className={({ isActive }) =>
          `p-2.5 transition-colors duration-150 rounded-[10px] ${
            isActive
              ? 'text-[#FAFAF9]'
              : 'text-[rgba(250,250,249,0.5)] hover:text-[rgba(250,250,249,0.75)]'
          }`
        }
        style={({ isActive }) =>
          isActive ? { background: 'rgba(250, 250, 249, 0.12)' } : undefined
        }
      >
        <Settings size={18} />
      </NavLink>

      <button
        onClick={onToggleExpand}
        className="p-2.5 text-[rgba(250,250,249,0.5)] hover:text-[rgba(250,250,249,0.75)] transition-all duration-300 rounded-[10px]"
        aria-label="Toggle account summary"
      >
        <ChevronUp
          size={18}
          className="transition-transform duration-300"
          style={{
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
          }}
        />
      </button>
    </nav>
    </div>
  )
}
