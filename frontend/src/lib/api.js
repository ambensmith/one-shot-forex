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
  const data = await fetchJSON('models.json')
  return data?.models || []
}
