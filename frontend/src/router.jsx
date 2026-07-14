import { createRouter, createRoute, createRootRoute } from '@tanstack/react-router'
import { lazy, Suspense } from 'react'

// Import AppShell directly as the root component
import AppShell from './App.jsx'

const rootRoute = createRootRoute({
  component: AppShell,
})

// Lazy load pages
const lazyComponent = (importFn) => {
  const LazyComp = lazy(importFn)
  return function Wrapper() {
    return (
      <Suspense fallback={
        <div style={{ display: 'grid', placeItems: 'center', minHeight: '60vh', gap: 12, color: 'var(--text-muted)' }}>
          <i className="ti ti-loader animate-spin" style={{ fontSize: 24, color: 'var(--accent)' }} />
          <span>Loading...</span>
        </div>
      }>
        <LazyComp />
      </Suspense>
    )
  }
}

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: lazyComponent(() => import('./pages/Dashboard')),
})

const recruitersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/recruiters',
  component: lazyComponent(() => import('./pages/Recruiters')),
})

const analyticsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/analytics',
  component: lazyComponent(() => import('./pages/Analytics')),
})

const aiSearchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/ai-search',
  component: lazyComponent(() => import('./pages/AISearch')),
})

const directoryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/directory',
  component: lazyComponent(() => import('./pages/Directory')),
})

const statesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/states',
  component: lazyComponent(() => import('./pages/Directory')),
})

const companiesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies',
  component: lazyComponent(() => import('./pages/Directory')),
})

const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/admin',
  component: lazyComponent(() => import('./pages/AdminTerminal')),
})

const activityRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/activity',
  component: lazyComponent(() => import('./pages/ActivityLog')),
})

const reviewQueueRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/review-queue',
  component: lazyComponent(() => import('./pages/ReviewQueue')),
})

const visitorLogsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/visitor-logs',
  component: lazyComponent(() => import('./pages/VisitorTracking')),
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: lazyComponent(() => import('./pages/auth/Login')),
})

const registerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/register',
  component: lazyComponent(() => import('./pages/auth/Register')),
})

const forgotPasswordRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/forgot-password',
  component: lazyComponent(() => import('./pages/auth/ForgotPassword')),
})

const resetPasswordRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/reset-password',
  component: lazyComponent(() => import('./pages/auth/ResetPassword')),
})

const verifyEmailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/verify-email',
  component: lazyComponent(() => import('./pages/auth/VerifyEmail')),
})

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  registerRoute,
  forgotPasswordRoute,
  resetPasswordRoute,
  verifyEmailRoute,
  recruitersRoute,
  analyticsRoute,
  aiSearchRoute,
  directoryRoute,
  statesRoute,
  companiesRoute,
  adminRoute,
  activityRoute,
  reviewQueueRoute,
  visitorLogsRoute
])

export const router = createRouter({ routeTree })
