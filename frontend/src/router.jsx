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

const routeTree = rootRoute.addChildren([
  indexRoute,
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
