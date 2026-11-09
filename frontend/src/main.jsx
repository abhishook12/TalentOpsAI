import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import "@fontsource/inter"
import axios from 'axios'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'

// Initialize Sentry for React client crash monitoring & security exploit defense
const VITE_SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN

if (VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: VITE_SENTRY_DSN,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.05,
    replaysOnErrorSampleRate: 1.0,
    environment: import.meta.env.MODE || 'development',
    beforeSend(event) {
      if (event.request && event.request.headers) {
        delete event.request.headers['Authorization']
        delete event.request.headers['Cookie']
      }
      return event
    },
  })
}

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

function ErrorFallback({ error, resetError }) {
  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6 text-center select-none">
      <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
        <span className="text-red-400 font-bold text-lg">!</span>
      </div>
      <h1 className="text-xl font-bold mb-2 tracking-tight">Application Interface Notice</h1>
      <p className="text-zinc-400 text-sm max-w-md mb-6 leading-relaxed">
        An unexpected interface exception occurred. The runtime protection layer has intercepted this state to safeguard your session data.
      </p>
      <div className="flex gap-3">
        <button
          onClick={() => {
            if (resetError) resetError()
            window.location.reload()
          }}
          className="px-5 py-2.5 bg-white text-black font-semibold rounded-xl text-sm hover:bg-zinc-200 transition-colors"
        >
          Reload Interface
        </button>
      </div>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Sentry.ErrorBoundary fallback={ErrorFallback} showDialog={false}>
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </GoogleOAuthProvider>
    </Sentry.ErrorBoundary>
  </React.StrictMode>,
)
