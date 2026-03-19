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

export function saveModelComparison(modelComparison) {
  if (modelComparison && modelComparison.length > 0) {
    localStorage.setItem('model_comparison', JSON.stringify(modelComparison))
  }
}
