const BASE_PATH = './data'

async function fetchJSON(filename) {
  try {
    const resp = await fetch(`${BASE_PATH}/${filename}`)
    if (!resp.ok) return null
    return await resp.json()
  } catch {
    return null
  }
}

export async function loadDashboard() {
  return fetchJSON('dashboard.json')
}

export async function loadTrades() {
  const data = await fetchJSON('trades.json')
  return data?.trades || []
}

export async function loadEquity() {
  const data = await fetchJSON('equity.json')
  return data?.curves || {}
}

export async function loadSignals() {
  const data = await fetchJSON('signals.json')
  return data?.signals || []
}

export async function loadModels() {
  // Check for live model comparison data saved by the last news fetch
  try {
    const cached = localStorage.getItem('model_comparison')
    if (cached) {
      const live = JSON.parse(cached)
      const staticData = await fetchJSON('models.json')
      const staticModels = staticData?.models || []
      return live.map(m => {
        const meta = staticModels.find(s => s.key === m.key) || {}
        return { ...meta, ...m }
      })
    }
  } catch {
    // Fall through to static data
  }
  const data = await fetchJSON('models.json')
  return data?.models || []
}

export async function loadReview() {
  return fetchJSON('review.json')
}

export async function loadHybrids() {
  const data = await fetchJSON('hybrids.json')
  return data?.hybrids || []
}

export async function loadConfig() {
  const data = await fetchJSON('config.json')
  return data?.config || null
}

export async function loadRunReviews() {
  const data = await fetchJSON('run_reviews.json')
  return data?.runs || []
}

/**
 * Save config overrides using smart routing:
 * - Simple config changes (toggles, sliders) → fast direct commit (~5s)
 * - Falls back to workflow dispatch if direct save fails
 */
export async function saveConfig(overrides) {
  // Try the fast direct save first
  try {
    const directResp = await fetch('/api/config-direct', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ overrides }),
    })
    if (directResp.ok) {
      const result = await directResp.json()
      // Return a synthetic result that Settings.jsx can handle
      return { status: 'ok', message: result.message }
    }
  } catch {
    // Direct save not available, fall through to workflow
  }

  // Fallback: workflow-based save
  const resp = await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ overrides }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }))
    throw new Error(err.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export function saveModelComparison(modelComparison) {
  if (modelComparison && modelComparison.length > 0) {
    localStorage.setItem('model_comparison', JSON.stringify(modelComparison))
  }
}

// ── Live Positions ────────────────────────────────────────

export async function loadLivePositions() {
  try {
    const resp = await fetch('/api/live-positions')
    if (!resp.ok) return null
    return await resp.json()
  } catch {
    return null
  }
}

// ── Hybrid Management ────────────────────────────────────

async function hybridManage(body) {
  const resp = await fetch('/api/hybrid-manage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }))
    throw new Error(err.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export function toggleHybrid(configId, isActive) {
  return hybridManage({ action: 'toggle', id: configId, is_active: isActive })
}

export function deleteHybrid(configId) {
  return hybridManage({ action: 'delete', id: configId })
}

export function toggleAllHybrids(isActive) {
  return hybridManage({ action: 'toggle-all', is_active: isActive })
}

// ── Workflow Trigger Helpers ──────────────────────────────

/**
 * Trigger a GitHub Actions workflow via the Vercel API.
 * @param {Object} params - { mode, stream?, hybrid?, period? }
 * @returns {{ run_id, status, message }}
 */
export async function triggerStream({ mode = 'tick', stream = 'all', hybrid, period = '7d' }) {
  const resp = await fetch('/api/trigger-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, stream, hybrid, period }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }))
    throw new Error(err.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

/**
 * Poll a GitHub Actions workflow run until complete.
 * @param {number} runId
 * @param {function} onProgress - called with status string on each poll
 * @param {number} maxAttempts - max poll attempts (default 60 = ~5 min)
 * @returns {{ status, conclusion }}
 */
export async function pollWorkflow(runId, onProgress, maxAttempts = 60) {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(r => setTimeout(r, 5000))
    try {
      const resp = await fetch(`/api/workflow-status?run_id=${runId}`)
      if (!resp.ok) continue
      const data = await resp.json()
      onProgress?.(data.status)
      if (data.status === 'completed') return data
      if (data.conclusion === 'failure' || data.conclusion === 'cancelled') return data
    } catch {
      // Network error, keep polling
    }
  }
  return { status: 'timeout', conclusion: 'timeout' }
}
