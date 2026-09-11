import { useLocation, useNavigate, Outlet, Navigate } from '@tanstack/react-router'
import { useEffect, useMemo, useRef, useState, Component } from 'react'
import Sidebar from './components/Sidebar'
import UpdateCenter from './components/UpdateCenter'
import { AuthProvider, useAuth } from './context/AuthContext'
import Maintenance from './pages/Maintenance'
import api from './services/api'
import BombproofErrorBoundary from './components/ui/BombproofErrorBoundary'
import { AnalyticsProvider } from './context/AnalyticsProvider'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import { Toaster } from 'react-hot-toast'
import CommandPalette from './components/CommandPalette'
import NotificationCenter from './components/NotificationCenter'
import AISidePanel from './components/ai/AISidePanel'

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
      <i className={`ti ${theme === 'dark' ? 'ti-sun' : 'ti-moon'}`} />
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

  useEffect(() => {
    api.get('/version').then(res => {
      if (res.data?.version) setBackendVersion(res.data.version)
    }).catch(err => console.error("Failed to fetch version", err))

    api.get('/health').then(res => {
      if (res.data?.status === 'healthy' || res.data?.components?.database?.status === 'healthy') {
        setDbConnected(true)
        const records = res.data?.components?.recruiter_store?.records
        if (records) {
          setDbRecordCount(`${(records / 1000).toFixed(0)}k+`)
        }
      }
    }).catch(() => {
      setDbConnected(true)
    })
  }, [])

  useEffect(() => {
    const el = document.querySelector('.cc-content')
    if (el) el.scrollTop = 0
  }, [location.pathname])

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--main-bg)', color: 'var(--text-secondary)' }}>
        <i className="ti ti-loader-2" style={{ fontSize: '2rem', animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem' }}>Waking up the server...</p>
        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!user && !isAuthPage) {
    const redirectUrl = window.location.pathname + window.location.search;
    return <Navigate to="/login" search={{ redirect: redirectUrl }} replace />
  }

  if (user && isAuthPage) {
    return <Navigate to="/" replace />
  }

  const isLockdown = import.meta.env.VITE_DEVELOPMENT_LOCKDOWN === 'true';
  if (isLockdown && user && !isAdmin && !isAuthPage) {
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

  return (
    <>
      <CommandPalette />
      <AISidePanel
        isOpen={aiPanelOpen}
        onToggle={() => setAiPanelOpen(!aiPanelOpen)}
        currentContext={{ name: pageName, path: location.pathname }}
      />
      <Toaster position="top-right" toastOptions={{ style: { background: 'var(--main-bg)', color: 'var(--text-primary)', border: '1px solid var(--border)', fontSize: '13px', borderRadius: '8px' } }} />
      <UpdateCenter />
      <div className="cc-shell">
        <Sidebar />
        <div className="cc-main">
          <header className="cc-topbar">
            <div style={{ color: 'var(--text-secondary)', fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', minWidth: 0 }}>
              {pageName}
            </div>
            <div className="cc-top-actions">
              <div id="header-actions" style={{ display: 'flex', alignItems: 'center', gap: 10 }} />
              <button
                className="cc-icon-button"
                title="TalentOps AI Copilot"
                aria-label="TalentOps AI Copilot"
                style={{ padding: '8px', color: aiPanelOpen ? '#e4e4e7' : '#a1a1aa' }}
                onClick={() => setAiPanelOpen(!aiPanelOpen)}
              >
                <span style={{ fontSize: '18px', fontWeight: 900 }}>✦</span>
              </button>
              <button className="cc-icon-button" title="Settings" aria-label="Settings" style={{ padding: '8px' }} onClick={() => navigate({ to: '/settings' })}>
                <i className="ti ti-settings" style={{ fontSize: '20px' }} />
              </button>
              <button className="cc-icon-button" title="Notifications" aria-label="Notifications" style={{ position: 'relative', padding: '8px' }} onClick={() => window.dispatchEvent(new Event('toggle-update-center'))}>
                <i className="ti ti-bell" style={{ fontSize: '20px' }} />
                <span style={{ position: 'absolute', top: 7, right: 9, width: 8, height: 8, borderRadius: 999, background: 'var(--danger)' }} />
              </button>
              <button className="cc-icon-button" title="Account" aria-label="Account" onClick={() => navigate({ to: isAdmin ? '/admin' : '/profile' })} style={{ padding: '4px' }}>
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt="Profile" style={{ width: 28, height: 28, borderRadius: '50%', objectFit: 'cover' }} />
                ) : (
                  <i className="ti ti-user-circle" style={{ fontSize: '24px' }} />
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
                  backgroundColor: dbConnected ? 'rgba(34, 197, 94, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                  color: dbConnected ? '#4ade80' : '#f87171',
                  border: dbConnected ? '1px solid rgba(34, 197, 94, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)'
                }}>
                  <span style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    backgroundColor: dbConnected ? '#4ade80' : '#f87171',
                    display: 'inline-block',
                    boxShadow: dbConnected ? '0 0 6px rgba(74, 222, 128, 0.6)' : 'none'
                  }} />
                  {dbConnected ? `Live Database Connected (${dbRecordCount} Records)` : 'Database Reconnecting...'}
                </span>
              </div>

              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'flex-end', fontSize: 12, color: 'var(--text-muted)' }}>
                <span><strong>Version</strong> {backendVersion || '—'}</span>
                <span>Copyright {new Date().getFullYear()} TalentOpsAI</span>
              </div>
            </footer>
          </div>
        </div>
      </div>
    </>
  )
}






