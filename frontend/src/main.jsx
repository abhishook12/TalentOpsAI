import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import "@fontsource/inter"
import axios from 'axios'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: true,
      retry: 1
    },
  },
})

const savedTheme = localStorage.getItem('theme')
document.documentElement.setAttribute('data-theme', savedTheme || 'light')
if (!savedTheme) {
  localStorage.setItem('theme', 'light')
}
axios.defaults.withCredentials = true

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
