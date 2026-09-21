import axios from 'axios'

const RAW_API_URL = import.meta.env.VITE_API_URL || 'https://talentopsai-1.onrender.com'
export const API = import.meta.env.DEV 
  ? (typeof window !== 'undefined' && window.location?.hostname ? `http://${window.location.hostname}:8000` : 'http://127.0.0.1:8000') 
  : RAW_API_URL

// ── Immediate Backend Warm-Up ──────────────────────────────────────────────
// Fire a lightweight /ping the instant this module loads (before React mounts).
// This gives Render's cold start a head start while the JS bundle parses.
if (!import.meta.env.DEV) {
  fetch(`${RAW_API_URL}/ping`, { method: 'GET', mode: 'cors', cache: 'no-store' }).catch(() => {})
  fetch('/api/ping', { method: 'GET', cache: 'no-store' }).catch(() => {})
}

// Keep backend warm while user has a tab open (Render sleeps after 15m)
if (typeof window !== 'undefined' && !import.meta.env.DEV) {
  setInterval(() => {
    fetch(`${RAW_API_URL}/ping`, { method: 'GET', mode: 'cors', cache: 'no-store' }).catch(() => {})
  }, 4 * 60 * 1000)
}

const clientCache = new Map()
let onUnauthorizedCallback = null;

export const setOnUnauthorizedCallback = (callback) => {
  onUnauthorizedCallback = callback;
};

const createClient = (baseURL) => {
  if (!clientCache.has(baseURL)) {
    const client = axios.create({
      baseURL,
      withCredentials: true,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    })


    const responseCache = new Map()
    const CACHE_TTL = 5000 // 5 seconds

    client.interceptors.request.use(config => {
      if (config.method === 'get' && !config.skipCache) {
        const key = config.url + JSON.stringify(config.params || {})
        const cached = responseCache.get(key)
        if (cached && Date.now() - cached.time < CACHE_TTL) {
          config.adapter = () => Promise.resolve(cached.response)
        }
      }
      return config
    })

    client.interceptors.response.use(response => {
      if (response.config.method === 'get' && !response.config.skipCache) {
        const key = response.config.url + JSON.stringify(response.config.params || {})
        responseCache.set(key, { response, time: Date.now() })
      }
      return response
    })

    clientCache.set(baseURL, client)
  }
  return clientCache.get(baseURL)
}

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

const SESSION_TOKEN_KEY = 'session_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

export const getStoredToken = () => {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(SESSION_TOKEN_KEY) || sessionStorage.getItem(SESSION_TOKEN_KEY)
}

export const getStoredRefreshToken = () => {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(REFRESH_TOKEN_KEY) || sessionStorage.getItem(REFRESH_TOKEN_KEY)
}

export const setStoredToken = (token, remember = true) => {
  if (typeof window === 'undefined') return
  // Always write to localStorage so browser restart / tab reload never kicks user out
  if (token) {
    localStorage.setItem(SESSION_TOKEN_KEY, token)
    sessionStorage.setItem(SESSION_TOKEN_KEY, token)
  }
}

export const setStoredRefreshToken = (token) => {
  if (typeof window === 'undefined') return
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
    sessionStorage.setItem(REFRESH_TOKEN_KEY, token)
  }
}

export const clearStoredToken = () => {
  if (typeof window === 'undefined') return
  localStorage.removeItem(SESSION_TOKEN_KEY)
  sessionStorage.removeItem(SESSION_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
}

const isRetryableError = (error) => {
  const status = error?.response?.status
  return error?.message === 'Network Error'
    || error?.code === 'ERR_NETWORK'
    || error?.code === 'ECONNABORTED'
    || error?.message?.includes('timeout')
    || status === 502
    || status === 503
    || status === 504
}

let isRefreshing = false
let refreshSubscribers = []

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb)
}

function onRefreshed(error) {
  refreshSubscribers.forEach(cb => cb(error))
  refreshSubscribers = []
}

async function trySilentRefresh() {
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      subscribeTokenRefresh((err) => {
        if (err) reject(err)
        else resolve()
      })
    })
  }

  isRefreshing = true
  const client = createClient(API)
  const storedRefreshToken = getStoredRefreshToken()
  try {
    const res = await client.post('/auth/refresh', 
      { refresh_token: storedRefreshToken },
      { headers: storedRefreshToken ? { Authorization: `Bearer ${storedRefreshToken}` } : {} }
    )
    if (res?.data?.token) {
      setStoredToken(res.data.token, true)
    }
    if (res?.data?.refresh_token) {
      setStoredRefreshToken(res.data.refresh_token)
    }
    isRefreshing = false
    onRefreshed(null)
  } catch (err) {
    isRefreshing = false
    onRefreshed(err)
    throw err
  }
}

async function smartRequest(method, url, data, config = {}) {
  // Auth login/google POSTs should also retry on cold-start (502/503/timeout)
  const isAuthLogin = (method === 'post' && (url === '/auth/login' || url === '/auth/google'))
  const isAuthEndpoint = typeof url === 'string' && url.startsWith('/auth/')
  const retryable = config.retryable ?? (['get', 'delete', 'head'].includes(method) || isAuthLogin)
  const retryDelayMs = config.retryDelayMs ?? (isAuthLogin ? 2500 : 1200)
  const maxAttempts = retryable ? 2 : 1
  const authToken = getStoredToken()
  let lastError = null
  const client = createClient(API)

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const requestConfig = { ...config }
      delete requestConfig.retryable
      delete requestConfig.retryDelayMs

      // Cold start tolerance for all auth routes (60s)
      if (isAuthEndpoint && !requestConfig.timeout) {
        requestConfig.timeout = 60000
      }

      requestConfig.headers = {
        ...(requestConfig.headers || {}),
      }
      
      const sid = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('talentops_sid') : null
      const aid = typeof localStorage !== 'undefined' ? localStorage.getItem('talentops_aid') : null
      if (sid) requestConfig.headers['X-Session-ID'] = sid
      if (aid) requestConfig.headers['X-Anonymous-ID'] = aid
      
      if (authToken) {
        requestConfig.headers.Authorization = `Bearer ${authToken}`
      }

      if (method === 'get' || method === 'delete' || method === 'head') {
        return await client[method](url, requestConfig)
      }
      return await client[method](url, data, requestConfig)
    } catch (error) {
      lastError = error
      if (axios.isCancel(error)) {
        throw error
      }
      if (attempt < maxAttempts && isRetryableError(error)) {
        await sleep(retryDelayMs)
        continue
      }
      
      if (error.response) {
        const isUnauthorized = error.response.status === 401;
        const isDeviceRevoked = error.response.status === 403 && error.response.data?.detail?.includes('Access Restricted');
        const isAuthRoute = url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/logout') || url.includes('/auth/register');

        if (isUnauthorized && !isAuthRoute && !config._isRetry) {
          try {
            await trySilentRefresh()
            return await smartRequest(method, url, data, { ...config, _isRetry: true })
          } catch (refreshErr) {
            const refreshStatus = refreshErr?.response?.status;
            // ONLY force logout if the server explicitly rejected the refresh token (401/403)
            // NEVER logout on network errors, cold starts, or temporary 5xx errors
            if (refreshStatus === 401 || refreshStatus === 403) {
              if (onUnauthorizedCallback) {
                onUnauthorizedCallback(refreshErr?.response?.data?.detail || error.response?.data?.detail);
              }
            } else {
              console.warn('[TalentOps API] Refresh skipped due to server connection state. Keeping session intact.');
            }
          }
        } else if (isDeviceRevoked) {
          if (onUnauthorizedCallback && !url.includes('/auth/login')) {
            onUnauthorizedCallback(error.response.data?.detail);
          }
        }
      }
      
      break
    }
  }

  throw lastError
}

const api = {
  get: (url, config) => smartRequest('get', url, undefined, config),
  delete: (url, config) => smartRequest('delete', url, undefined, config),
  head: (url, config) => smartRequest('head', url, undefined, config),
  post: (url, data, config) => smartRequest('post', url, data, config),
  put: (url, data, config) => smartRequest('put', url, data, config),
  patch: (url, data, config) => smartRequest('patch', url, data, config),
}

export async function logout() {
  await api.post('/auth/logout', undefined, {})
}

export async function logAction(actionType, details = {}, status = 'success') {
  try {
    await api.post('/actions/log', {
      action_type: actionType,
      details,
      status,
    })
  } catch {
    // Never block core UX on analytics logging.
  }
}

export function getErrorMessage(err, fallback = 'Something went wrong') {
  if (err?.code === 'ECONNABORTED' || err?.message?.includes('timeout')) {
    return 'The server took longer than expected to respond. Please check your connection and try again.'
  }
  if (err?.message === 'Network Error' || err?.code === 'ERR_NETWORK') {
    return `Cannot reach the API at ${API}. Start the backend (uvicorn) or check VITE_API_URL in frontend/.env`
  }
  const url = err?.config?.url || 'unknown';
  const status = err?.response?.status || 'none';
  return err?.response?.data?.detail || `API Error [${status}] on ${url}: ${err?.message || fallback}`
}

export default api
