import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
export const API = String(API_URL).replace(/\/$/, '')

const clientCache = new Map()
let onUnauthorizedCallback = null;

export const setOnUnauthorizedCallback = (callback) => {
  onUnauthorizedCallback = callback;
};

const createClient = (baseURL) => {
  if (!clientCache.has(baseURL)) {
    clientCache.set(baseURL, axios.create({
      baseURL,
      withCredentials: true,
      headers: { 'Content-Type': 'application/json' },
    }))
  }
  return clientCache.get(baseURL)
}

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

const ADMIN_TOKEN_KEY = 'admin_access_token'
const APP_TOKEN_KEY = 'app_access_token'

const getStoredToken = (scope = 'admin') => {
  if (typeof window === 'undefined') return null
  if (scope === 'app') {
    return localStorage.getItem(APP_TOKEN_KEY) || sessionStorage.getItem(APP_TOKEN_KEY)
  }
  if (scope === 'none') return null
  return localStorage.getItem(ADMIN_TOKEN_KEY) || sessionStorage.getItem(ADMIN_TOKEN_KEY)
}

export const setStoredToken = (scope, token, remember = false) => {
  if (typeof window === 'undefined') return
  const storage = remember ? localStorage : sessionStorage
  const key = scope === 'app' ? APP_TOKEN_KEY : ADMIN_TOKEN_KEY
  localStorage.removeItem(key)
  sessionStorage.removeItem(key)
  if (token) storage.setItem(key, token)
}

export const clearStoredToken = (scope = 'admin') => {
  if (typeof window === 'undefined') return
  if (scope === 'app') {
    localStorage.removeItem(APP_TOKEN_KEY)
    sessionStorage.removeItem(APP_TOKEN_KEY)
    return
  }
  localStorage.removeItem(ADMIN_TOKEN_KEY)
  sessionStorage.removeItem(ADMIN_TOKEN_KEY)
}

const isRetryableError = (error) => {
  const status = error?.response?.status
  return error?.message === 'Network Error'
    || error?.code === 'ERR_NETWORK'
    || status === 502
    || status === 503
    || status === 504
}

async function smartRequest(method, url, data, config = {}) {
  const retryable = config.retryable ?? ['get', 'delete', 'head'].includes(method)
  const retryDelayMs = config.retryDelayMs ?? 1200
  const maxAttempts = retryable ? 2 : 1
  const authScope = config.authScope ?? 'admin'
  const authToken = getStoredToken(authScope)
  let lastError = null
  const client = createClient(API)
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const requestConfig = { ...config }
      delete requestConfig.retryable
      delete requestConfig.retryDelayMs
      delete requestConfig.authScope

      requestConfig.headers = {
        ...(requestConfig.headers || {}),
      }
      if (authToken && authScope !== 'none') {
        requestConfig.headers.Authorization = `Bearer ${authToken}`
      }

      if (method === 'get' || method === 'delete' || method === 'head') {
        return await client[method](url, requestConfig)
      }
      return await client[method](url, data, requestConfig)
    } catch (error) {
      lastError = error
      // Don't retry if the request was cancelled
      if (axios.isCancel(error)) {
        throw error
      }
      if (attempt < maxAttempts && isRetryableError(error)) {
        await sleep(retryDelayMs)
        continue
      }
      
      if (error.response && error.response.status === 401) {
        if (onUnauthorizedCallback) {
          onUnauthorizedCallback();
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
  await api.post('/auth/logout', undefined, { authScope: 'admin' })
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
  if (err?.message === 'Network Error' || err?.code === 'ERR_NETWORK') {
    return `Cannot reach the API at ${API}. Start the backend (uvicorn) or check VITE_API_URL in frontend/.env`
  }
  return err?.response?.data?.detail || err?.message || fallback
}

export default api
