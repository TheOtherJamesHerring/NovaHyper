import type { TokenResponse } from '../types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/* Prevent multiple simultaneous refresh calls */
let _refreshPromise: Promise<boolean> | null = null

export async function attemptRefresh(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise
  _refreshPromise = (async () => {
    try {
      const rt = sessionStorage.getItem('refresh_token')
      if (!rt) return false
      const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      })
      if (!res.ok) return false
      const data: TokenResponse = await res.json()
      sessionStorage.setItem('access_token', data.access_token)
      if (data.refresh_token) {
        sessionStorage.setItem('refresh_token', data.refresh_token)
      }
      return true
    } catch {
      return false
    } finally {
      _refreshPromise = null
    }
  })()
  return _refreshPromise
}

export async function request<T>(
  path: string,
  options?: RequestInit,
  _retry = true,
): Promise<T> {
  const token = sessionStorage.getItem('access_token')
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })

  if (res.status === 401 && _retry) {
    const refreshed = await attemptRefresh()
    if (!refreshed) {
      sessionStorage.removeItem('access_token')
      sessionStorage.removeItem('refresh_token')
      window.location.href = '/login'
      throw new Error('Session expired')
    }
    return request<T>(path, options, false)
  }

  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${body}`)
  }

  /* Handle 204 No Content */
  if (res.status === 204) return undefined as unknown as T

  return res.json() as Promise<T>
}

/** Download a blob (used for CSV export) */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const token = sessionStorage.getItem('access_token')
  const res = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`)
  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
