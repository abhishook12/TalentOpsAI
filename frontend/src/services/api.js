import axios from 'axios'

export const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

export async function checkAuth() {
  try {
    const { data } = await api.get('/auth/me')
    return data.authenticated === true
  } catch {
    return false
  }
}

export async function login(password, rememberDevice = false) {
  const { data } = await api.post('/auth/login', {
    password,
    remember_device: rememberDevice,
  })
  return data
}

export async function logout() {
  await api.post('/auth/logout')
}

export function getErrorMessage(err, fallback = 'Something went wrong') {
  if (err?.message === 'Network Error' || err?.code === 'ERR_NETWORK') {
    return `Cannot reach the API at ${API}. Start the backend (uvicorn) or check VITE_API_URL in frontend/.env`
  }
  return err?.response?.data?.detail || err?.message || fallback
}

export default api
