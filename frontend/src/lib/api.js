/**
 * Dual-mode API layer.
 * - Dev (Vite): proxies to FastAPI at /api/*
 * - Production (Vercel): reads static JSON from /data/*.json
 */

const IS_DEV = import.meta.env.DEV

// ── Helpers ──────────────────────────────────────────────────

async function fetchLiveJSON(path, options) {
  const resp = await fetch(`/api${path}`, options)
  if (!resp.ok) return null
  return resp.json()
}

async function fetchStaticJSON(filename) {
  const resp = await fetch(`/data/${filename}`)
  if (!resp.ok) return null
  return resp.json()
}

async function putJSON(path, body) {
  if (!IS_DEV) return null  // writes not supported in static mode
  const resp = await fetch(`/api${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok) return null
  return resp.json()
}

// ── Cache for static JSON (avoid re-fetching same file) ─────

const _staticCache = {}
async function cachedStatic(filename) {
  if (!_staticCache[filename]) {
    _staticCache[filename] = fetchStaticJSON(filename)
  }
  return _staticCache[filename]
}

// ── Public API ──────────────────────────────────────────────

export async function fetchOpenTrades() {
  if (IS_DEV) {
    const data = await fetchLiveJSON('/trades/open')
    return data?.trades || []
  }
  const data = await cachedStatic('trades.json')
  const trades = data?.trades || []
  return trades.filter(t => t.status === 'open')
}

export async function fetchClosedTrades({ filter, instrument, source, days, limit } = {}) {
  if (IS_DEV) {
    const params = new URLSearchParams()
    if (filter) params.set('filter', filter)
    if (instrument) params.set('instrument', instrument)
    if (source) params.set('source', source)
    if (days) params.set('days', String(days))
    if (limit) params.set('limit', String(limit))
    const qs = params.toString()
    const data = await fetchLiveJSON(`/trades/closed${qs ? `?${qs}` : ''}`)
    return { trades: data?.trades || [], count: data?.count || 0 }
  }
  const data = await cachedStatic('trades.json')
  let trades = (data?.trades || []).filter(t => t.status !== 'open')
  // Client-side filters
  if (filter === 'won') trades = trades.filter(t => t.pnl > 0)
  if (filter === 'lost') trades = trades.filter(t => t.pnl != null && t.pnl <= 0)
  if (instrument) trades = trades.filter(t => t.instrument === instrument)
  if (source) trades = trades.filter(t => (t.stream || t.source || '').includes(source))
  if (days) {
    const cutoff = Date.now() - days * 86400000
    trades = trades.filter(t => t.closed_at && new Date(t.closed_at).getTime() >= cutoff)
  }
  if (limit) trades = trades.slice(0, limit)
  return { trades, count: trades.length }
}

export async function fetchTradeDetail(tradeId) {
  if (IS_DEV) {
    const data = await fetchLiveJSON(`/trades/${tradeId}`)
    return data?.trade || null
  }
  const data = await cachedStatic('trades.json')
  const trade = (data?.trades || []).find(t => t.id === tradeId)
  if (!trade) return null
  // Wrap to match the shape the server returns: { record: {...} }
  return { trade_id: trade.id, record: trade.record || {}, created_at: trade.opened_at }
}

export async function fetchBias() {
  if (IS_DEV) {
    const data = await fetchLiveJSON('/bias')
    return data?.bias || []
  }
  const data = await fetchStaticJSON('bias.json')
  return data?.bias || []
}

export async function fetchEquity(stream) {
  if (IS_DEV) {
    const params = stream ? `?stream=${stream}` : ''
    const data = await fetchLiveJSON(`/equity${params}`)
    return (data?.equity || []).map(d => ({
      ...d,
      timestamp: d.timestamp || d.recorded_at || d.time,
    }))
  }
  // Static equity.json has shape:
  //   { curves: { account:  [{time, equity, positions}],
  //               combined: [{time, equity, positions}],
  //               news/strategy/hybrid:<name>: [...] } }
  // Default (`stream` undefined) → `account`: the broker balance line,
  // matching what Capital.com shows. `combined` is realized PnL across
  // all streams; per-stream curves are realized within one stream.
  const data = await fetchStaticJSON('equity.json')
  const curves = data?.curves || {}
  const key = stream || 'account'
  const series = curves[key] || []
  return series.map(d => ({ ...d, timestamp: d.time || d.recorded_at }))
}

export async function fetchPerformance() {
  if (IS_DEV) {
    const data = await fetchLiveJSON('/performance')
    return data?.series || []
  }
  const data = await fetchStaticJSON('performance.json')
  return data?.series || []
}

export async function fetchLLMActivity(hours = 12) {
  if (IS_DEV) {
    const data = await fetchLiveJSON(`/llm/activity?hours=${hours}`)
    return data || { headlines_by_source: {}, relevance_assessments: [], signals: [], summary: {} }
  }
  const data = await fetchStaticJSON('llm_activity.json')
  return data || { headlines_by_source: {}, relevance_assessments: [], signals: [], summary: {} }
}

export async function fetchStrategies() {
  if (IS_DEV) {
    const data = await fetchLiveJSON('/strategies')
    return data?.strategies || []
  }
  const data = await fetchStaticJSON('strategies.json')
  return data?.strategies || []
}

export async function fetchPrompts() {
  if (IS_DEV) {
    const data = await fetchLiveJSON('/prompts')
    return data?.prompts || []
  }
  const data = await fetchStaticJSON('prompts.json')
  return data?.prompts || []
}

export async function updatePrompt(name, template, currentVersion) {
  if (!IS_DEV) return null  // read-only in production
  const num = currentVersion ? parseInt(currentVersion.replace(/[^0-9]/g, '') || '0', 10) + 1 : 1
  const version = `v${num}`
  return putJSON(`/prompts/${name}`, { template, version })
}

export async function fetchStatus() {
  if (IS_DEV) {
    const data = await fetchLiveJSON('/status')
    return data || {}
  }
  const data = await fetchStaticJSON('dashboard.json')
  return data ? { status: 'ok', generated_at: data.generated_at, streams: data.streams } : {}
}
