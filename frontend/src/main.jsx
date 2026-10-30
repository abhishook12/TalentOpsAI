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
      refetchOnWindowFocus: false,
      refetchIntervalInBackground: false, // Do not poll when tab/browser is in background
      retry: 1
    },
  },
})

// Strict Mandate: Enforce Apple True Black and White text across entire site
localStorage.setItem('theme', 'dark')
document.documentElement.setAttribute('data-theme', 'dark')
document.documentElement.classList.add('dark')
document.documentElement.classList.remove('light')
axios.defaults.withCredentials = true

import { RouterProvider } from '@tanstack/react-router'
import { router } from './router.jsx'

import { GoogleOAuthProvider } from '@react-oauth/google'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'dummy-client-id-for-dev.apps.googleusercontent.com'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </GoogleOAuthProvider>
  </React.StrictMode>,
)
