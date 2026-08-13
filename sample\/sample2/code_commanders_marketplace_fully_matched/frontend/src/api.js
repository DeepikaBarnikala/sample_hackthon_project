const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export async function api(path, options = {}) {
  const token = localStorage.getItem('token')
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${BASE}${path}`, { ...options, headers })
  const text = await response.text()
  let data = {}
  try { data = text ? JSON.parse(text) : {} } catch { data = { detail: text } }
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`)
  return data
}

export const money = (value = 0) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value || 0))
export const percent = (value = 0) => `${(Number(value || 0) * 100).toFixed(1)}%`
