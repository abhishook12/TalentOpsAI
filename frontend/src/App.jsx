import { useLocation, useNavigate, Outlet, Navigate } from '@tanstack/react-router'
import { useEffect, useMemo, useRef, useState, Component, lazy, Suspense } from 'react'
import Sidebar from './components/Sidebar'
import UpdateCenter from './components/UpdateCenter'
import { AuthProvider, useAuth } from './context/AuthContext'
import Maintenance from './pages/Maintenance'
import api from './services/api'
import BombproofErrorBoundary from './components/ui/BombproofErrorBoundary'
import { AnalyticsProvider } from './context/AnalyticsProvider'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import { Toaster } from 'react-hot-toast'
import NotificationCenter from './components/NotificationCenter'
import { Bot, Settings, Sun, Moon, User as UserIcon } from 'lucide-react'

const CommandPalette = lazy(() => import('./components/CommandPalette'))
const AISidePanel = lazy(() => import('./components/ai/AISidePanel'))
const ProcessLoadModal = lazy(() => import('./components/telemetry/ProcessLoadModal'))

// Global settings
// axios credentials set in main.jsx

function ThemeSwitcher() {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      className="cc-icon-button"
      onClick={toggleTheme}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? <Sun size={19} /> : <Moon size={19} />}
    </button>
  )
}

const PAGE_NAMES = {
  '/': 'Dashboard',
  '/campaigns': 'Email Outreach & Campaigns',
  '/recruiters': 'Recruiters Directory',
  '/analytics': 'Analytics & Reporting',
  '/search': 'Search & Query Intelligence',
  '/directory': 'Directory Browser',
  '/states': 'Directory > States',
  '/companies': 'Directory > Companies',
  '/profile': 'User Profile',
  '/settings': 'System Settings',
  '/admin': 'Admin Terminal',
  '/sentinel': 'Data Quality Center (SENTINEL)',
  '/mailintel': 'MailIntel Deliverability & Reputation',
  '/review-queue': 'Review Queue',
  '/admin/users': 'User Management',
  '/admin/visitor-analytics': 'Visitor Analytics',
  '/admin/devices': 'Trusted Devices',
  '/activity': 'Activity Feed',
  '/admin/jobs': 'Background Jobs',
  '/admin/audit-logs': 'Audit Logs',
  '/admin/health': 'System Health',
  '/admin/settings': 'Admin Settings',
  '/download-scout': 'Desktop Scout & Telemetry Fleet',
  '/extension': 'Scout Extension Hub',
  '/extension-hub': 'Scout Extension Hub',
  '/admin/scout-contributors': 'Scout Contributors',
  '/admin/staging': 'Staging Pipeline',
}

function getSessionId() {
  let sid = sessionStorage.getItem('talentops_sid')
  if (!sid) {
    sid = crypto.randomUUID ? crypto.randomUUID() : `${Math.random().toString(36).slice(2)}${Date.now()}`
    sessionStorage.setItem('talentops_sid', sid)
  }
  return sid
}

export default function AppShellWrapper() {
  return (
    <ThemeProvider>
      <AnalyticsProvider>
        <AuthProvider>
          <AppShell />
        </AuthProvider>
      </AnalyticsProvider>
    </ThemeProvider>
  )
}

function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const isAuthPage = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email'].includes(location.pathname)
  const { user, isAdmin, loading } = useAuth()
  const pageName = useMemo(() => PAGE_NAMES[location.pathname] || 'Dashboard', [location.pathname])
  
  const [backendVersion, setBackendVersion] = useState('v4.0.2-Stable')
  const [aiPanelOpen, setAiPanelOpen] = useState(false)
  const [dbConnected, setDbConnected] = useState(true)
  const [dbRecordCount, setDbRecordCount] = useState('437k+')
  const [processModalOpen, setProcessModalOpen] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      api.get('/version', { signal: controller.signal }).catch(() => null),
      api.get('/health', { signal: controller.signal }).catch(() => null)
    ]).then(([versionRes, healthRes]) => {
      if (versionRes?.data?.version) setBackendVersion(versionRes.data.version)
      if (healthRes?.data?.status === 'healthy' || healthRes?.data?.components?.database?.status === 'healthy') {
        setDbConnected(true)
        const records = healthRes?.data?.components?.recruiter_store?.records
        if (records) setDbRecordCount(`${(records / 1000).toFixed(0)}k+`)
      }
    })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const el = document.querySelector('.cc-content')
    if (el) el.scrollTop = 0
  }, [location.pathname])

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center', backgroundColor: '#09090b', color: '#f4f4f5' }}>
        <div style={{ width: 36, height: 36, border: '3px solid rgba(255,255,255,0.15)', borderTopColor: '#ffffff', borderRadius: '50%', animation: 'spin 0.8s linear infinite', marginBottom: '1rem' }} />
        <p style={{ fontFamily: 'system-ui, -apple-system, sans-serif', fontSize: '0.875rem', color: '#a1a1aa', fontWeight: 500, letterSpacing: '0.01em', margin: 0 }}>Loading workspace...</p>
        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const isPublicDownloadPage = location.pathname === '/download-scout'

  if (!user && !isAuthPage && !isPublicDownloadPage) {
    const redirectUrl = window.location.pathname + window.location.search;
    return <Navigate to="/login" search={{ redirect: redirectUrl }} replace />
  }

  if (user && isAuthPage) {
    return <Navigate to="/" replace />
  }

  const isLockdown = import.meta.env.VITE_DEVELOPMENT_LOCKDOWN === 'true';
  if (isLockdown && user && !isAdmin && !isAuthPage && !isPublicDownloadPage) {
    return (
      <>
        <BombproofErrorBoundary>
          <Maintenance />
        </BombproofErrorBoundary>
      </>
    );
  }

  // Removed forced redirection so users can use the app even without a company

  if (isAuthPage) {
    return (
      <>
        <BombproofErrorBoundary componentName="Authentication Portal">
          <Outlet />
        </BombproofErrorBoundary>
      </>
    )
  }

  if (!user && isPublicDownloadPage) {
    return (
      <div className="cc-public-shell" style={{ minHeight: '100vh', backgroundColor: 'var(--main-bg, #09090b)', color: 'var(--text-primary, #fafafa)', display: 'flex', flexDirection: 'column' }}>
        <header style={{
          padding: '16px 32px',
          borderBottom: '1px solid var(--border, rgba(255,255,255,0.08))',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--card-bg, #0b0b0c)',
          position: 'sticky',
          top: 0,
          zIndex: 50
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src="/talentops-logo.png" alt="TalentOps" style={{ width: 34, height: 34, borderRadius: 8 }} />
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary, #fafafa)', lineHeight: 1.1 }}>TalentOps</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted, #a1a1aa)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>Desktop Scout Official Setup</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <ThemeSwitcher />
            <button
              onClick={() => navigate({ to: '/login' })}
              style={{
                padding: '8px 16px',
                background: 'transparent',
                border: '1px solid var(--border, #27272a)',
                borderRadius: 8,
                color: 'var(--text-primary, #e4e4e7)',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Sign In
            </button>
            <button
              onClick={() => navigate({ to: '/register' })}
              style={{
                padding: '8px 16px',
                background: 'var(--text-primary, #e4e4e7)',
                border: 'none',
                borderRadius: 8,
                color: 'var(--bg-base, #09090b)',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              Create Account
            </button>
          </div>
        </header>
        <main style={{ flex: 1 }}>
          <BombproofErrorBoundary componentName="TalentOps Scout Setup Portal">
            <Outlet />
          </BombproofErrorBoundary>
        </main>
      </div>
    );
  }

  return (
    <>
      <Suspense fallback={null}>
        <CommandPalette />
        <AISidePanel
          isOpen={aiPanelOpen}
          onToggle={() => setAiPanelOpen(!aiPanelOpen)}
          currentContext={{ name: pageName, path: location.pathname, search: location.search }}
        />
        {processModalOpen && (
          <ProcessLoadModal
            isOpen={processModalOpen}
            onClose={() => setProcessModalOpen(false)}
            dbRecordCount={dbRecordCount}
          />
        )}
      </Suspense>
      <Toaster position="top-right" toastOptions={{ style: { background: 'var(--main-bg)', color: 'var(--text-primary)', border: '1px solid var(--border)', fontSize: '13px', borderRadius: '8px' } }} />
      <UpdateCenter />
      <div className="cc-shell">
        <Sidebar />
        <div className="cc-main">
          <header className="cc-topbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 0 }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', minWidth: 0 }}>
                {pageName}
              </div>
              <button
                onClick={() => setProcessModalOpen(true)}
                title="View Real-Time System Process Load & Engine Vitals"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '3px 10px',
                  borderRadius: 999,
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.14)',
                  color: '#ffffff',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <span style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: '#ffffff',
                  boxShadow: '0 0 6px rgba(255, 255, 255, 0.8)'
                }} />
                <span>System Online</span>
                <span style={{ opacity: 0.4 }}>•</span>
                <span style={{ color: 'var(--text-secondary, #a1a1aa)', fontWeight: 500 }}>Telemetry</span>
              </button>
            </div>
            <div className="cc-top-actions">
              <div id="header-actions" style={{ display: 'flex', alignItems: 'center', gap: 10 }} />
              <button
                className="cc-icon-button"
                title="TalentOps Copilot"
                aria-label="TalentOps Copilot"
                style={{ color: aiPanelOpen ? '#ffffff' : 'var(--text-secondary, #a1a1aa)' }}
                onClick={() => setAiPanelOpen(!aiPanelOpen)}
              >
                <Bot size={19} />
              </button>
              <button
                className="cc-icon-button"
                title="Settings"
                aria-label="Settings"
                onClick={() => navigate({ to: '/settings' })}
              >
                <Settings size={19} />
              </button>
              <NotificationCenter />
              <button
                className="cc-icon-button"
                title="Account"
                aria-label="Account"
                onClick={() => navigate({ to: isAdmin ? '/admin' : '/profile' })}
              >
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt="Profile" style={{ width: 28, height: 28, borderRadius: '50%', objectFit: 'cover' }} />
                ) : (
                  <UserIcon size={19} />
                )}
              </button>
              <ThemeSwitcher />
            </div>
          </header>

          <div className="cc-content">
            <main className="cc-page-body">
              <BombproofErrorBoundary componentName={pageName || "Application Body"}>
                <Outlet />
              </BombproofErrorBoundary>
            </main>

            <footer className="cc-footer">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, lineHeight: 1.2, color: 'var(--text-primary)' }}>
                    TalentOps
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Recruiter intelligence workspace
                  </div>
                </div>
              </div>

              <div className="cc-footer-center" style={{ display: 'flex', justifyContent: 'center' }}>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '3px 10px',
                  borderRadius: '9999px',
                  fontSize: '11px',
                  fontWeight: 500,
                  backgroundColor: dbConnected ? 'rgba(255, 255, 255, 0.06)' : 'rgba(239, 68, 68, 0.12)',
                  color: dbConnected ? '#ffffff' : '#ef4444',
                  border: dbConnected ? '1px solid rgba(255, 255, 255, 0.16)' : '1px solid rgba(239, 68, 68, 0.35)'
                }}>
                  <span style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    backgroundColor: dbConnected ? '#ffffff' : '#ef4444',
                    display: 'inline-block',
                    boxShadow: dbConnected ? '0 0 6px rgba(255, 255, 255, 0.7)' : '0 0 6px rgba(239, 68, 68, 0.7)'
                  }} />
                  {dbConnected ? 'Database Connected' : 'Database Reconnecting...'}
                </span>
              </div>

              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'flex-end', fontSize: 12, color: 'var(--text-muted)' }}>
                <span>© {new Date().getFullYear()} TalentOps</span>
              </div>
            </footer>
          </div>
        </div>
      </div>
      <UpdateCenter />
    </>
  )
}






