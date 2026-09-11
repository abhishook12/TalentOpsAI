import { createRouter, createRoute, createRootRoute, Navigate } from '@tanstack/react-router'
import { lazy, Suspense } from 'react'

// Import AppShell directly as the root component
import AppShell from './App.jsx'

const rootRoute = createRootRoute({
  component: AppShell,
})

import AdminRoute from './components/AdminRoute'
const adminLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'adminLayout',
  component: AdminRoute,
})

// Lazy load pages
const lazyComponent = (importFn) => {
  const LazyComp = lazy(importFn)
  return function Wrapper() {
    return (
      <Suspense fallback={
        <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ height: 28, width: 200, background: 'var(--border)', borderRadius: 4, animation: 'ccPulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite' }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
             <div style={{ height: 180, background: 'rgba(33, 37, 41, 0.3)', borderRadius: 6, animation: 'ccPulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite' }} />
             <div style={{ height: 180, background: 'rgba(33, 37, 41, 0.3)', borderRadius: 6, animation: 'ccPulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite' }} />
             <div style={{ height: 180, background: 'rgba(33, 37, 41, 0.3)', borderRadius: 6, animation: 'ccPulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite' }} />
          </div>
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

const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/search',
  component: lazyComponent(() => import('./pages/Search')),
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
  getParentRoute: () => adminLayoutRoute,
  path: '/admin',
  component: lazyComponent(() => import('./pages/AdminTerminal')),
})

const activityRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/activity',
  component: lazyComponent(() => import('./pages/ActivityLog')),
})

const reviewQueueRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/review-queue',
  component: lazyComponent(() => import('./pages/admin/ReviewQueue')),
})

const sentinelRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/sentinel',
  component: lazyComponent(() => import('./pages/admin/DataQualityCenter')),
})

const intelligenceCenterRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/intelligence-center',
  component: lazyComponent(() => import('./pages/DatabaseIntelligenceCenter')),
})

const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/settings',
  component: lazyComponent(() => import('./pages/Settings')),
})

const extensionHubRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/extension',
  component: lazyComponent(() => import('./pages/DownloadScout')),
})

const downloadScoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/download-scout',
  component: lazyComponent(() => import('./pages/DownloadScout')),
})


const profileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/profile',
  component: lazyComponent(() => import('./pages/Profile')),
})


const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  validateSearch: (search) => ({
    redirect: search.redirect || '/',
  }),
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

const visitorAnalyticsRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/visitor-analytics',
  component: lazyComponent(() => import('./pages/admin/VisitorAnalytics')),
})

const userManagementRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/users',
  component: lazyComponent(() => import('./pages/admin/UserManagement')),
})

const adminSettingsRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/settings',
  component: lazyComponent(() => import('./pages/admin/AdminSettings')),
})

const auditLogsRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/audit-logs',
  component: lazyComponent(() => import('./pages/admin/AuditLogs')),
})

const backgroundJobsRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/jobs',
  component: lazyComponent(() => import('./pages/admin/BackgroundJobs')),
})

const systemHealthRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/health',
  component: lazyComponent(() => import('./pages/admin/SystemHealth')),
})

const trustedDevicesRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/devices',
  component: lazyComponent(() => import('./pages/admin/TrustedDevices')),
})

const extensionReportRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/extension',
  component: () => <Navigate to="/admin/scout-contributors" replace />,
})

const stagingPipelineRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/staging',
  component: lazyComponent(() => import('./pages/StagingPipeline')),
})

const scoutContributorsAdminRoute = createRoute({
  getParentRoute: () => adminLayoutRoute,
  path: '/admin/scout-contributors',
  component: lazyComponent(() => import('./pages/ScoutContributors')),
})

const scoutContributorsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/scout/contributors',
  component: lazyComponent(() => import('./pages/ScoutContributors')),
})


const campaignsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/campaigns',
  component: lazyComponent(() => import('./pages/Campaigns')),
})

const testCampaignsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/test-campaigns',
  component: lazyComponent(() => import('./pages/Campaigns')),
})

const mailIntelRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/mailintel',
  component: lazyComponent(() => import('./pages/MailIntelDashboard')),
})

const mcpRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/mcp',
  component: function MCPPage() {
    return (
      <div style={{ padding: 32, maxWidth: 800, margin: '0 auto', color: 'var(--text-primary)' }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>Model Context Protocol (MCP) Gateway</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
          Standardized JSON-RPC 2.0 interface for AI assistants and edge telemetry tools.
        </p>
        <div className="ds-card" style={{ marginBottom: 16 }}>
          <div className="ds-eyebrow" style={{ marginBottom: 8 }}>Registered Tools</div>
          <ul style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
            <li><strong>echo</strong> — Diagnostic roundtrip test tool.</li>
            <li><strong>list_recruiters</strong> — Query talent intelligence database with parameter filters.</li>
          </ul>
        </div>
        <div className="ds-card">
          <div className="ds-eyebrow" style={{ marginBottom: 8 }}>Endpoint Details</div>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>
            Protocol: <code style={{ fontFamily: 'var(--mono)' }}>mcp-jsonrpc-2.0</code> | Methods: <code style={{ fontFamily: 'var(--mono)' }}>tools/list</code>, <code style={{ fontFamily: 'var(--mono)' }}>tools/call</code>
          </p>
        </div>
      </div>
    )
  },
})

const notFoundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '*',
  component: function NotFound() {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: 16, color: 'var(--text-secondary)' }}>
        <div style={{ fontSize: 72, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>404</div>
        <p style={{ fontSize: 15, margin: 0 }}>This page doesn't exist.</p>
        <a href="/" style={{ marginTop: 8, padding: '10px 24px', background: 'var(--brand)', color: '#fff', borderRadius: 8, textDecoration: 'none', fontSize: 13, fontWeight: 500 }}>Return to Dashboard</a>
      </div>
    )
  },
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
  searchRoute,
  directoryRoute,
  statesRoute,
  companiesRoute,
  campaignsRoute,
  testCampaignsRoute,
  mailIntelRoute,
  profileRoute,
  settingsRoute,
  extensionHubRoute,
  downloadScoutRoute,
  scoutContributorsRoute,
  mcpRoute,
  adminLayoutRoute.addChildren([
    adminRoute,
    activityRoute,
    reviewQueueRoute,
    sentinelRoute,
    visitorAnalyticsRoute,
    userManagementRoute,
    adminSettingsRoute,
    systemHealthRoute,
    backgroundJobsRoute,
    auditLogsRoute,
    trustedDevicesRoute,
    intelligenceCenterRoute,
    extensionReportRoute,
    stagingPipelineRoute,
    scoutContributorsAdminRoute,
  ]),
  notFoundRoute
])

export const router = createRouter({ routeTree, defaultPreload: 'intent' })




