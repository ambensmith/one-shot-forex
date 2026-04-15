import { useState, useEffect, useRef } from 'react'
import { useLLMActivity, usePrompts } from '../hooks/useLLMData'
import InstrumentTag from '../components/InstrumentTag'
import DirectionBadge from '../components/DirectionBadge'
import { ConfidenceBar } from '../components/TimelineChapter'
import { timeAgo } from '../lib/constants'

export default function LLMAnalysis() {
  const { data, loading, error } = useLLMActivity()
  const { prompts, loading: promptsLoading, save, saving } = usePrompts()

  if (loading) {
    return (
      <div>
        <PageHeader />
        <p className="text-sm text-tertiary mt-8">Loading pipeline activity...</p>
      </div>
    )
  }

  const { headlines_by_source, relevance_assessments, signals, summary } = data

  return (
    <div>
      <PageHeader count={summary?.headlines_count} />

      {/* Headlines by Source */}
      <section className="mt-10">
        <h2 className="font-display text-[28px] font-semibold tracking-tight text-primary" style={{ lineHeight: 1.2, letterSpacing: '-0.3px' }}>
          Recent Headlines
        </h2>
        <p className="text-[11px] font-semibold uppercase tracking-[0.8px] text-tertiary mt-2">Grouped by source</p>
        <HeadlineGrid sources={headlines_by_source} />
      </section>

      {/* Relevance Assessments */}
      <section className="mt-10">
        <h2 className="font-display text-[28px] font-semibold tracking-tight text-primary" style={{ lineHeight: 1.2, letterSpacing: '-0.3px' }}>
          Relevance Assessments
        </h2>
        <RelevanceList assessments={relevance_assessments} headlines={headlines_by_source} />
      </section>

      {/* Generated Signals */}
      <section className="mt-10">
        <h2 className="font-display text-[28px] font-semibold tracking-tight text-primary" style={{ lineHeight: 1.2, letterSpacing: '-0.3px' }}>
          Generated Signals
        </h2>
        <SignalCards signals={signals} />
      </section>

      {/* Editable Prompts */}
      <section className="mt-10">
        <h2 className="font-display text-[28px] font-semibold tracking-tight text-primary" style={{ lineHeight: 1.2, letterSpacing: '-0.3px' }}>
          Prompts
        </h2>
        <p className="text-sm text-secondary mt-1">Edit the prompts used in each pipeline stage</p>
        {promptsLoading ? (
          <p className="text-sm text-tertiary mt-4">Loading prompts...</p>
        ) : (
          <PromptEditor prompts={prompts} onSave={save} saving={saving} />
        )}
      </section>
    </div>
  )
}

function PageHeader({ count }) {
  return (
    <>
      <h1 className="font-display text-4xl font-bold tracking-tight text-primary" style={{ letterSpacing: '-0.5px', lineHeight: 1.15 }}>
        LLM Analysis
      </h1>
      <p className="text-tertiary mt-1 text-xs">
        Pipeline activity from the last 12 hours
        {count != null && <span> &middot; {count} headlines processed</span>}
      </p>
    </>
  )
}


/* ── Headlines Grid ────────────────────────────────── */

function HeadlineGrid({ sources }) {
  const entries = Object.entries(sources || {})
  if (entries.length === 0) {
    return <p className="text-sm italic text-tertiary mt-4">No headlines ingested recently.</p>
  }

  return (
    <div className="mt-4 grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
      {entries.map(([source, headlines]) => (
        <HeadlineSourceGroup key={source} source={source} headlines={headlines} />
      ))}
    </div>
  )
}

function HeadlineSourceGroup({ source, headlines }) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? headlines : headlines.slice(0, 5)
  const remaining = headlines.length - 5

  return (
    <div className="bg-surface border border-border rounded-card p-4 shadow-whisper">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.8px] text-tertiary">
          {formatSourceName(source)}
        </span>
        <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-hover text-tertiary">
          {headlines.length}
        </span>
      </div>
      <div className="space-y-2">
        {visible.map((h, i) => (
          <div key={h.id || i}>
            <p className="text-sm text-primary leading-snug line-clamp-2">{h.headline}</p>
            <p className="text-xs text-tertiary mt-0.5">{h.published_at ? timeAgo(h.published_at) : ''}</p>
          </div>
        ))}
      </div>
      {remaining > 0 && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="text-xs text-info-text font-medium mt-2 hover:underline"
        >
          +{remaining} more
        </button>
      )}
      {expanded && remaining > 0 && (
        <button
          onClick={() => setExpanded(false)}
          className="text-xs text-info-text font-medium mt-2 hover:underline"
        >
          Show less
        </button>
      )}
    </div>
  )
}

function formatSourceName(source) {
  const names = {
    finnhub: 'Finnhub',
    finnhub_calendar: 'Economic Calendar',
    bbc: 'BBC',
    cnbc: 'CNBC',
    ecb: 'ECB',
    fed: 'Federal Reserve',
    boe: 'Bank of England',
    boj: 'Bank of Japan',
    snb: 'SNB',
    rba: 'RBA',
    boc: 'Bank of Canada',
  }
  return names[source?.toLowerCase()] || source?.replace(/_/g, ' ') || 'Unknown'
}


/* ── Relevance Assessments ─────────────────────────── */

function RelevanceList({ assessments, headlines }) {
  if (!assessments || assessments.length === 0) {
    return <p className="text-sm italic text-tertiary mt-4">No relevance assessments yet.</p>
  }

  // Group assessments by headline_id
  const grouped = {}
  for (const a of assessments) {
    if (!grouped[a.headline_id]) grouped[a.headline_id] = []
    grouped[a.headline_id].push(a)
  }

  // Build flat headline lookup
  const headlineMap = {}
  for (const items of Object.values(headlines || {})) {
    for (const h of items) {
      headlineMap[h.id] = h
    }
  }

  return (
    <div className="mt-4 space-y-3">
      {Object.entries(grouped).map(([headlineId, items]) => {
        const h = headlineMap[headlineId]
        return (
          <div key={headlineId} className="bg-surface border border-border rounded-card p-4 shadow-whisper">
            <p className="text-sm font-medium text-primary leading-snug">
              {h?.headline || `Headline ${headlineId.slice(0, 8)}...`}
            </p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              <span className="text-tertiary text-sm">&rarr;</span>
              {items.map((a, i) => (
                <InstrumentTag key={i} instrument={a.instrument} />
              ))}
              {items.length === 0 && (
                <span className="text-xs italic text-tertiary">No relevant instruments</span>
              )}
            </div>
            {items[0]?.relevance_reasoning && (
              <p className="text-sm text-secondary mt-2 leading-relaxed">{items[0].relevance_reasoning}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}


/* ── Signal Cards ──────────────────────────────────── */

function SignalCards({ signals }) {
  if (!signals || signals.length === 0) {
    return <p className="text-sm italic text-tertiary mt-4">No signals generated in this period.</p>
  }

  return (
    <div className="mt-4 space-y-4">
      {signals.map(signal => (
        <SignalCard key={signal.id} signal={signal} />
      ))}
    </div>
  )
}

function SignalCard({ signal }) {
  const isRejected = signal.challenge_output?.recommendation === 'reject' || signal.status === 'rejected'
  const semantic = isRejected ? 'cooldown' : signal.direction === 'long' ? 'profitable' : signal.direction === 'short' ? 'loss' : 'cooldown'

  return (
    <div
      className="bg-surface border rounded-card p-6"
      style={{
        borderColor: `var(--border-${semantic})`,
        background: `var(--tint-${semantic})`,
        boxShadow: `0 4px 24px var(--shadow-${semantic}), 0 1px 3px rgba(0,0,0,0.04)`,
      }}
    >
      <div className="flex items-center gap-3 flex-wrap">
        <h3 className="font-display text-[22px] font-semibold text-primary" style={{ letterSpacing: '-0.2px' }}>
          {signal.instrument?.replace('_', '/')}
        </h3>
        <DirectionBadge direction={signal.direction} />
        {isRejected && (
          <span className="text-[11px] font-semibold tracking-[0.3px] px-2 py-0.5 rounded-md"
            style={{ background: 'rgba(148, 163, 184, 0.08)', color: '#64748B' }}>
            Rejected
          </span>
        )}
      </div>
      <ConfidenceBar value={signal.confidence} semantic={semantic} />

      {signal.reasoning && (
        <p className="text-sm text-secondary leading-relaxed mt-3 max-w-narrative">{signal.reasoning}</p>
      )}

      {signal.key_factors?.length > 0 && (
        <div className="mt-3">
          <span className="text-[11px] font-semibold uppercase tracking-[0.5px] text-tertiary">Key factors</span>
          <ul className="mt-1 space-y-0.5">
            {signal.key_factors.map((f, i) => (
              <li key={i} className="text-sm text-secondary">&bull; {f}</li>
            ))}
          </ul>
        </div>
      )}

      {signal.challenge_output && (
        <div className="mt-4 p-4 rounded-lg" style={{ background: '#F5F5F4' }}>
          <span className="text-[11px] font-semibold uppercase tracking-[0.5px] text-tertiary">Challenge result</span>
          <div className="mt-2 flex items-center gap-3 flex-wrap">
            {signal.challenge_output.recommendation && (
              <span className="text-xs font-medium text-secondary capitalize">
                {signal.challenge_output.recommendation.replace(/_/g, ' ')}
              </span>
            )}
            {signal.challenge_output.conviction_after_challenge != null && (
              <span className="text-xs text-tertiary">
                Conviction: {Math.round(signal.challenge_output.conviction_after_challenge * 100)}%
              </span>
            )}
          </div>
          {signal.challenge_output.counter_argument && (
            <p className="text-sm text-secondary mt-2 leading-relaxed">{signal.challenge_output.counter_argument}</p>
          )}
          {signal.challenge_output.alternative_interpretation && (
            <p className="text-sm text-tertiary mt-1 leading-relaxed italic">{signal.challenge_output.alternative_interpretation}</p>
          )}
        </div>
      )}
    </div>
  )
}


/* ── Editable Prompts ──────────────────────────────── */

function PromptEditor({ prompts, onSave, saving }) {
  const order = ['relevance', 'signal', 'challenge']
  // Match prompts by prefix (e.g. 'relevance_v1' matches 'relevance')
  const sorted = order
    .map(prefix => prompts.find(p => p.name.startsWith(prefix)))
    .filter(Boolean)
  const matchedNames = new Set(sorted.map(p => p.name))
  const extra = prompts.filter(p => !matchedNames.has(p.name))

  return (
    <div className="mt-4 space-y-4">
      {[...sorted, ...extra].map(prompt => (
        <PromptSection key={prompt.name} prompt={prompt} onSave={onSave} saving={saving} />
      ))}
    </div>
  )
}

function PromptSection({ prompt, onSave, saving }) {
  const [expanded, setExpanded] = useState(false)
  const [value, setValue] = useState(prompt.template || '')
  const [saved, setSaved] = useState(false)
  const originalRef = useRef(prompt.template || '')

  useEffect(() => {
    setValue(prompt.template || '')
    originalRef.current = prompt.template || ''
  }, [prompt.template])

  const handleSave = async () => {
    const success = await onSave(prompt.name, value, prompt.version)
    if (success) {
      setSaved(true)
      originalRef.current = value
      setTimeout(() => setSaved(false), 2000)
    }
  }

  const handleReset = () => {
    setValue(originalRef.current)
  }

  const isDirty = value !== originalRef.current
  const isSaving = saving === prompt.name
  // Strip version suffix for display (e.g. 'challenge_v1' → 'Challenge')
  const baseName = prompt.name.replace(/_v\d+$/, '')
  const title = baseName.charAt(0).toUpperCase() + baseName.slice(1)

  return (
    <div className="bg-surface border border-border rounded-card shadow-whisper overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-hover transition-colors"
      >
        <div className="flex items-center gap-3">
          <h3 className="font-display text-lg font-medium text-primary">{title} Prompt</h3>
          {prompt.version && (
            <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-hover text-tertiary">
              {prompt.version}
            </span>
          )}
          {saved && (
            <span className="text-xs font-medium text-profitable-text animate-pulse">Saved</span>
          )}
        </div>
        <svg
          className={`w-4 h-4 text-tertiary transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-5 pb-5">
          <textarea
            value={value}
            onChange={e => setValue(e.target.value)}
            className="w-full font-mono text-[13px] leading-[1.7] p-4 rounded-lg border border-border bg-hover text-primary resize-y focus:outline-none focus:border-brand focus:ring-[3px] focus:ring-brand/10"
            style={{ minHeight: '200px' }}
          />
          <div className="flex items-center gap-3 mt-3">
            <button
              onClick={handleSave}
              disabled={!isDirty || isSaving}
              className="px-5 py-2.5 rounded-button text-sm font-medium text-white transition-all disabled:opacity-40"
              style={{
                background: '#4F46E5',
                boxShadow: '0 1px 3px rgba(79, 70, 229, 0.3), 0 1px 2px rgba(0, 0, 0, 0.06)',
              }}
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={handleReset}
              disabled={!isDirty}
              className="px-5 py-2.5 rounded-button text-sm font-medium text-primary border border-border hover:bg-hover transition-all disabled:opacity-40"
            >
              Reset
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
