const BASE = import.meta.env.VITE_API_BASE || ''

async function get(path, params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  })
  const url = `${BASE}${path}${query.size ? `?${query.toString()}` : ''}`
  const response = await fetch(url)
  if (!response.ok) {
    let message = `请求失败（${response.status}）`
    try {
      const body = await response.json()
      if (body?.detail) message = body.detail
    } catch {
      // Ignore non-JSON error bodies.
    }
    throw new Error(message)
  }
  return response.json()
}

export const api = {
  meta: () => get('/api/meta'),
  bridge: (month) => get('/api/mrr/bridge', { month }),
  retention: () => get('/api/retention'),
  retentionCell: (cohort, month) => get('/api/retention/cell', { cohort, month }),
  customerDetail: (customerId, month) =>
    get(`/api/customers/${encodeURIComponent(customerId)}/detail`, { month }),
  health: () => get('/api/health'),
}
