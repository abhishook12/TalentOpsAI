import { useLocation, useNavigate, Outlet, Navigate } from '@tanstack/react-router'
import { useEffect, useMemo, useRef, useState, Component } from 'react'
import Sidebar from './components/Sidebar'
import UpdateCenter from './components/UpdateCenter'
import { AuthProvider, useAuth } from './context/AuthContext'
import Maintenance from './pages/Maintenance'
class GlobalErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Caught by GlobalErrorBoundary:', error, errorInfo)
    if (error?.name === 'ChunkLoadError' || String(error?.message || '').includes('dynamically imported module')) {
      window.location.reload()
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="cc-error-shell">
          <i className="ti ti-alert-triangle cc-error-icon" />
          <h2>Component crashed</h2>
          <p>The app caught a render error before it could take down the whole session.</p>
          <pre style={{color: 'red', textAlign: 'left', padding: 20, maxWidth: 800, overflow: 'auto'}}>{String(this.state.error?.stack || this.state.error)}</pre>
          <div className="cc-error-actions">
            <button onClick={() => { window.location.href = '/' }} className="cc-ghost-button">Return to dashboard</button>
            <button onClick={() => window.location.reload()} className="cc-primary-button">Reload page</button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}


import { AnalyticsProvider } from './context/AnalyticsProvider'
import { Toaster } from 'react-hot-toast'
import CommandPalette from './components/CommandPalette'
import NotificationCenter from './components/NotificationCenter'

// Global settings
// axios credentials set in main.jsx

function ThemeSwitcher() {
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('theme')
    return savedTheme || 'light'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  return (
    <button
      className="cc-icon-button"
      onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label="Toggle theme"
    >
      <i className={`ti ${theme === 'dark' ? 'ti-sun' : 'ti-moon'}`} />
    </button>
  )
}

const PAGE_NAMES = {
  '/': 'Dashboard',
  '/recruiters': 'Recruiters',
  '/analytics': 'Analytics',
  '/ai-search': 'AI Search',
  '/directory': 'Directory',
  '/states': 'Directory > States',
  '/companies': 'Directory > Companies',
  '/admin': 'Admin Terminal',
  '/activity': 'Activity Feed',
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
    <AnalyticsProvider>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </AnalyticsProvider>
  )
}

function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const isAuthPage = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email'].includes(location.pathname)
  const { user, isAdmin, loading } = useAuth()
  const pageName = useMemo(() => PAGE_NAMES[location.pathname] || 'Dashboard', [location.pathname])
  
  if (loading) return null;

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
        <GlobalErrorBoundary>
          <Maintenance />
        </GlobalErrorBoundary>
      </>
    );
  }

  // Redirect users with incomplete profiles (e.g. no company) to the Profile completion page
  if (user && !isAdmin && !isAuthPage && !user.company && location.pathname !== '/profile') {
    return <Navigate to="/profile" replace />
  }

  if (isAuthPage) {
    return (
      <>
        <GlobalErrorBoundary>
          <Outlet />
        </GlobalErrorBoundary>
      </>
    )
  }

  return (
    <>
      <CommandPalette />
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
              <button className="cc-icon-button" title="Settings" aria-label="Settings" style={{ padding: '8px' }}>
                <i className="ti ti-settings" style={{ fontSize: '20px' }} />
              </button>
              <button className="cc-icon-button" title="Notifications" aria-label="Notifications" style={{ position: 'relative', padding: '8px' }} onClick={() => window.dispatchEvent(new Event('toggle-update-center'))}>
                <i className="ti ti-bell" style={{ fontSize: '20px' }} />
                <span style={{ position: 'absolute', top: 7, right: 9, width: 8, height: 8, borderRadius: 999, background: 'var(--danger)' }} />
              </button>
              <button className="cc-icon-button" title="Account" aria-label="Account" onClick={() => navigate({ to: '/admin' })} style={{ padding: '4px' }}>
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
              <GlobalErrorBoundary>
                <Outlet />
              </GlobalErrorBoundary>
            </main>

            <footer className="cc-footer">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                <div style={{ width: 28, height: 28, borderRadius: 10, background: 'linear-gradient(135deg, #d7d7d7, #8e8e8e)', color: '#111', display: 'grid', placeItems: 'center' }}>
                  <i className="ti ti-brand-graphql" />
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 16, fontWeight: 900, lineHeight: 1, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>
                    REC-INTEL v4.0
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Operational Command Center
                  </div>
                </div>
              </div>

              <div className="cc-footer-center">
                <div style={{ display: 'flex', alignItems: 'center', gap: 34, whiteSpace: 'nowrap' }}>
                  <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)' }}>
                    Built by
                  </span>
                  <span style={{ fontSize: 17, fontWeight: 500, fontStyle: 'italic', color: 'var(--text-primary)', letterSpacing: '0.01em' }}>
                    Abhishek
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                <span><strong>Version</strong> v4.0.2-Stable</span>
                <span><strong>Server Node</strong> US-EAST-01A</span>
                <span>Copyright {new Date().getFullYear()} TalentOpsAI</span>
              </div>
            </footer>
          </div>
        </div>
      </div>
    </>
  )
}






