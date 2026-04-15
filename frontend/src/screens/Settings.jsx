import { useState, useEffect, useCallback } from 'react'
import { useSystemStatus } from '../hooks/useLLMData'

export default function Settings() {
  const { status, loading } = useSystemStatus()
  const [runState, setRunState] = useState('idle') // idle | dispatching | running | done | error
  const [runId, setRunId] = useState(null)
  const [runError, setRunError] = useState(null)

  const triggerRun = useCallback(async () => {
    setRunState('dispatching')
    setRunError(null)
    try {
      const resp = await fetch('/api/trigger-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'tick' }),
      })
      const data = await resp.json()
      if (!resp.ok || data.error) {
        setRunError(data.error || 'Dispatch failed')
        setRunState('error')
        return
      }
      setRunId(data.run_id)
      setRunState('running')
    } catch (err) {
      setRunError(err.message)
      setRunState('error')
    }
  }, [])

  // Poll workflow status while running
  useEffect(() => {
    if (runState !== 'running') return
    const poll = setInterval(async () => {
      try {
        const url = runId ? `/api/workflow-status?run_id=${runId}` : '/api/workflow-status'
        const resp = await fetch(url)
        const data = await resp.json()
        if (data.status === 'completed') {
          setRunState(data.conclusion === 'success' ? 'done' : 'error')
          if (data.conclusion !== 'success') setRunError(`Run ${data.conclusion}`)
          clearInterval(poll)
        }
      } catch { /* keep polling */ }
    }, 5000)
    return () => clearInterval(poll)
  }, [runState, runId])

  const runLabel = {
    idle: 'Run Pipeline Now',
    dispatching: 'Dispatching…',
    running: 'Running…',
    done: 'Complete — Run Again?',
    error: 'Failed — Retry?',
  }[runState]

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-4xl font-bold tracking-tight text-primary" style={{ letterSpacing: '-0.5px', lineHeight: 1.15 }}>
        Settings
      </h1>
      <p className="text-tertiary mt-1 text-xs">System configuration and status</p>

      <div className="mt-8 space-y-6">
        {/* Manual Trigger */}
        <Section title="Pipeline Control">
          <p className="text-xs text-tertiary mb-3">
            The pipeline runs automatically every hour during market hours. You can also trigger a run manually.
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => { setRunState('idle'); triggerRun() }}
              disabled={runState === 'dispatching' || runState === 'running'}
              className="px-4 py-2 text-sm font-medium rounded-button bg-primary text-white disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
            >
              {runLabel}
            </button>
            {runState === 'running' && (
              <span className="text-xs text-tertiary animate-pulse">Pipeline is running…</span>
            )}
            {runState === 'done' && (
              <span className="text-xs text-profitable-text">Pipeline completed. Refresh the page to see new data.</span>
            )}
            {runState === 'error' && runError && (
              <span className="text-xs text-loss-text">{runError}</span>
            )}
          </div>
        </Section>

        {/* System Status */}
        <Section title="System Status">
          <InfoRow label="Pipeline" value="Hourly tick via GitHub Actions" />
          <InfoRow label="Broker" value="Capital.com API" />
          <InfoRow label="LLM Provider" value="Groq (Llama 3.3 70B)" />
          <InfoRow label="News Source" value="Finnhub + RSS feeds" />
          {!loading && status?.streams && (
            <>
              {status.streams.news && (
                <InfoRow label="LLM Signals (total)" value={String(status.streams.news.signals ?? 0)} />
              )}
              {status.streams.strategy && (
                <InfoRow label="Strategy Signals (total)" value={String(status.streams.strategy.signals ?? 0)} />
              )}
              <InfoRow
                label="Open Positions"
                value={String(
                  Object.values(status.streams).reduce((sum, s) => sum + (s.open_positions || 0), 0)
                )}
              />
            </>
          )}
        </Section>

        {/* Risk Parameters */}
        <Section title="Risk Parameters">
          <p className="text-xs text-tertiary mb-3">
            Risk parameters are configured in <code className="font-mono text-xs bg-hover px-1 py-0.5 rounded">config/settings.yaml</code> and enforced at runtime.
          </p>
          <InfoRow label="Max Positions Per Stream" value="5" />
          <InfoRow label="Daily Loss Limit" value="3%" />
          <InfoRow label="Max Correlated Positions" value="2" />
          <InfoRow label="Default R:R Ratio" value="2.0" />
          <InfoRow label="Position Size" value="1 unit (demo mode)" />
        </Section>

        {/* Links */}
        <Section title="Links">
          <a
            href="https://github.com/ambensmith/one-shot-forex"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-info-text hover:underline"
          >
            GitHub Repository
          </a>
        </Section>
      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="bg-surface border border-border rounded-card p-6 shadow-whisper">
      <h3 className="text-sm font-semibold uppercase tracking-[0.5px] text-tertiary mb-4">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-secondary">{label}</span>
      <span className="text-sm font-mono text-primary font-tabular">{value}</span>
    </div>
  )
}
