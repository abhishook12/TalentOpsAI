import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import React, { useEffect, useState, lazy, Suspense, useRef, Component } from 'react'
import Sidebar from './components/Sidebar'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Recruiters = lazy(() => import('./pages/Recruiters'))
const Analytics  = lazy(() => import('./pages/Analytics'))
const AISearch   = lazy(() => import('./pages/AISearch'))
const Upload     = lazy(() => import('./pages/Upload'))
const StateDirectory = lazy(() => import('./pages/StateDirectory'))
const CompanyDirectory = lazy(() => import('./pages/CompanyDirectory'))
const AdminTerminal = lazy(() => import('./pages/AdminTerminal'))

class GlobalErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true }
  }
  componentDidCatch(error, errorInfo) {
    console.error("Caught by GlobalErrorBoundary:", error, errorInfo)
    if (error.name === 'ChunkLoadError' || error.message.includes('dynamically imported module')) {
      window.location.reload()
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 50, textAlign: 'center', color: 'var(--text-primary)' }}>
          <h2 style={{ marginBottom: 16 }}>Oops, something went wrong.</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>A new version of the app may have been deployed.</p>
          <button onClick={() => window.location.reload()} style={{ padding: '8px 16px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>
            Reload Page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.0.0/dist/tabler-icons.min.css');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  /* ── Default is DARK ── */
  :root {
    --sidebar-bg: #0a101b;
    --sidebar-border: #1e2c42;
    --sidebar-width: 248px;
    --accent: #22d3ee;
    --accent-glow: rgba(34,211,238,0.2);
    --accent-light: #67e8f9;
    --main-bg: #060b14;
    --panel-bg: #0b1220;
    --card-bg: #111a2b;
    --card-bg-hover: #152136;
    --card-border: #22324a;
    --card-border-hover: #335177;
    --text-primary: #edf3ff;
    --text-secondary: #a3b4cd;
    --text-muted: #667a99;
    --font: 'Inter', system-ui, sans-serif;
    --mono: 'JetBrains Mono', monospace;
    --radius: 10px;
    --radius-lg: 14px;
    --shadow: 0 6px 20px rgba(2, 8, 24, 0.35);
    --shadow-lg: 0 16px 40px rgba(2, 8, 24, 0.45);
    --bg-hover: rgba(255,255,255,0.04);
    --accent-bg: rgba(59,130,246,0.12);
    --accent-hover: #60a5fa;
    --text-inverse: #ffffff;
    --green: #3fb950;
    --red: #f85149;
    --amber: #d29922;
  }

  [data-theme="dark"] {
    --sidebar-bg: #0a101b;
    --sidebar-border: #1e2c42;
    --accent: #22d3ee;
    --accent-glow: rgba(34,211,238,0.2);
    --accent-light: #67e8f9;
    --main-bg: #060b14;
    --panel-bg: #0b1220;
    --card-bg: #111a2b;
    --card-bg-hover: #152136;
    --card-border: #22324a;
    --card-border-hover: #335177;
    --text-primary: #edf3ff;
    --text-secondary: #a3b4cd;
    --text-muted: #667a99;
    --shadow: 0 6px 20px rgba(2, 8, 24, 0.35);
    --bg-hover: rgba(255,255,255,0.04);
    --accent-bg: rgba(59,130,246,0.12);
    --accent-hover: #60a5fa;
    --text-inverse: #ffffff;
  }

  [data-theme="light"] {
    --sidebar-bg: #0d1117;
    --sidebar-border: #1e2d3d;
    --accent: #2563eb;
    --accent-glow: rgba(37,99,235,0.14);
    --accent-light: #3b82f6;
    --main-bg: #f0f4f8;
    --panel-bg: #f8fafc;
    --card-bg: #ffffff;
    --card-bg-hover: #f8fafc;
    --card-border: #e2e8f0;
    --card-border-hover: #cbd5e1;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #94a3b8;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.04);
    --bg-hover: rgba(0,0,0,0.04);
    --accent-bg: rgba(37,99,235,0.08);
    --accent-hover: #1d4ed8;
    --text-inverse: #ffffff;
  }

  [data-theme="sepia"] {
    --sidebar-bg: #1a1208;
    --sidebar-border: #2d200f;
    --accent: #c98a2e;
    --accent-glow: rgba(201,138,46,0.15);
    --accent-light: #e0a84a;
    --main-bg: #1a1208;
    --panel-bg: #1f1710;
    --card-bg: #251c12;
    --card-bg-hover: #2a2015;
    --card-border: #362a18;
    --card-border-hover: #4a3c28;
    --text-primary: #d9c8a8;
    --text-secondary: #a08060;
    --text-muted: #5c4830;
    --shadow: 0 2px 8px rgba(0,0,0,0.4);
    --bg-hover: rgba(255,200,100,0.05);
    --accent-bg: rgba(201,138,46,0.12);
    --accent-hover: #e0a84a;
    --text-inverse: #fffef0;
  }

  html, body, #root {
    height: 100%;
    overflow: hidden;
    font-family: var(--font);
    background:
      radial-gradient(1200px 600px at 90% -10%, rgba(34,211,238,0.08), transparent 60%),
      radial-gradient(900px 500px at -10% 20%, rgba(59,130,246,0.07), transparent 55%),
      var(--main-bg);
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    transition: background 0.3s ease, color 0.3s ease;
    font-size: 14px;
    line-height: 1.5;
  }

  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--card-border); border-radius: 10px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

  table { border-collapse: collapse; width: 100%; }
  th {
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 10px 16px;
    background: var(--panel-bg);
    border-bottom: 1px solid var(--card-border);
    text-align: left;
    white-space: nowrap;
  }
  td {
    padding: 11px 16px;
    font-size: 13.5px;
    color: var(--text-primary);
    border-bottom: 1px solid var(--card-border);
    vertical-align: middle;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--bg-hover); }

  input, select, textarea {
    font-family: var(--font);
    font-size: 13.5px;
    color: var(--text-primary);
    background: var(--panel-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 9px 13px;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  input::placeholder, textarea::placeholder { color: var(--text-muted); }
  input:focus, select:focus, textarea:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow), 0 6px 18px rgba(2, 8, 24, 0.35);
  }

  button {
    font-family: var(--font);
    cursor: pointer;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.15s ease;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  @keyframes glow-pulse { 0%,100%{box-shadow:0 0 0 0 var(--accent-glow)} 50%{box-shadow:0 0 16px 4px var(--accent-glow)} }

  .page-enter { animation: fadeUp 0.22s ease forwards; }

  .card {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 16px !important;
    box-shadow: var(--shadow) !important;
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s, background 0.2s;
    backdrop-filter: blur(8px);
  }
  .card:hover {
    border-color: var(--card-border-hover) !important;
    transform: translateY(-1px);
  }

  .btn-primary {
    background: linear-gradient(135deg, var(--accent), #3b82f6);
    color: #fff;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 500;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s;
    box-shadow: 0 0 0 0 var(--accent-glow);
  }
  .btn-primary:hover { filter: brightness(1.1); box-shadow: 0 10px 20px var(--accent-glow); transform: translateY(-1px); }

  .shell-main {
    background:
      linear-gradient(180deg, rgba(255,255,255,0.02), transparent 15%),
      var(--main-bg);
  }

  .topbar-glass {
    margin: 10px 12px 0;
    border: 1px solid var(--card-border);
    border-radius: 14px;
    background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015));
    box-shadow: 0 10px 24px rgba(2, 8, 24, 0.35);
    backdrop-filter: blur(10px);
  }

  .badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.02em;
  }
  .badge-blue { background: var(--accent-bg); color: var(--accent-light); }
  .badge-green { background: rgba(63,185,80,0.1); color: #3fb950; }
  .badge-gray { background: rgba(139,148,158,0.1); color: var(--text-secondary); }
  .badge-red { background: rgba(248,81,73,0.1); color: #f85149; }
  .badge-amber { background: rgba(210,153,34,0.1); color: #d29922; }

  /* Section headings */
  .section-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted);
  }
`

function ThemeSwitcher() {
  const themes = ['dark', 'light', 'sepia']
  const icons  = ['ti-moon', 'ti-sun', 'ti-eye']
  const labels = ['Dark', 'Light', 'Sepia']
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggle = () => {
    const next = themes[(themes.indexOf(theme) + 1) % themes.length]
    setTheme(next)
  }

  const idx = themes.indexOf(theme)

  return (
    <button
      onClick={toggle}
      title={`Theme: ${labels[idx]} — click to switch`}
      style={{
        width: 36, height: 36, borderRadius: 8,
        background: 'var(--card-bg)', border: '1px solid var(--card-border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--text-primary)', fontSize: 18, cursor: 'pointer',
        transition: 'background 0.15s, transform 0.15s', flexShrink: 0,
      }}
      onMouseEnter={e => { e.currentTarget.style.background = 'var(--card-bg-hover)'; e.currentTarget.style.transform = 'scale(1.05)' }}
      onMouseLeave={e => { e.currentTarget.style.background = 'var(--card-bg)'; e.currentTarget.style.transform = 'scale(1)' }}
    >
      <i className={`ti ${icons[idx]}`} />
    </button>
  )
}

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const PAGE_NAMES = {
  '/': 'Dashboard',
  '/recruiters': 'Recruiters',
  '/analytics': 'Analytics',
  '/ai-search': 'AI Search',
  '/directory': 'State Directory',
  '/companies': 'Company Directory',
  '/upload': 'ETL Upload',
  '/admin': 'Admin',
}

// Ensure a stable session ID for this browser tab session
function getSessionId() {
  let sid = sessionStorage.getItem('talentops_sid')
  if (!sid) {
    sid = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now()
    sessionStorage.setItem('talentops_sid', sid)
  }
  return sid
}

function PageTracker() {
  const location = useLocation()
  const entryTimeRef = useRef(Date.now())

  useEffect(() => {
    const prevPath  = entryTimeRef._prevPath
    const enteredAt = entryTimeRef.current
    const timeOnPage = prevPath ? Math.round((Date.now() - enteredAt) / 1000) : null

    // Reset for the new page
    entryTimeRef.current   = Date.now()
    entryTimeRef._prevPath = location.pathname

    const page = PAGE_NAMES[location.pathname] || location.pathname
    const session = (() => { try { return JSON.parse(localStorage.getItem('auth_session') || '{}') } catch { return {} } })()

    fetch(`${API}/analytics/log-visit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
      body: JSON.stringify({
        page,
        path: location.pathname,
        user_email:   session.email   || null,
        session_id:   getSessionId(),
        time_on_page: timeOnPage,
      }),
    }).catch(() => {})
  }, [location.pathname])
  return null
}

function LoginScreen({ onLoginSuccess }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      setError('Please fill in all fields.')
      return
    }
    // Basic email format check
    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address.')
      return
    }
    if (password !== '1012') {
      setError('Incorrect password.')
      return
    }
    setError('')
    onLoginSuccess(email)
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', width: '100vw', background: '#0b1329',
      fontFamily: 'var(--font)', color: '#fff', padding: 20,
      position: 'fixed', top: 0, left: 0, zIndex: 100000,
    }}>
      <div className="card" style={{
        width: '100%', maxWidth: 400, padding: 36,
        background: '#131c35', border: '1px solid #232e52',
        borderRadius: 16, boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
        display: 'flex', flexDirection: 'column', gap: 24,
      }}>
        {/* Logo / Header */}
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 48, height: 48, background: '#185FA5', borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px', boxShadow: '0 0 16px rgba(24, 95, 165, 0.4)'
          }}>
            <i className="ti ti-lock" style={{ color: '#fff', fontSize: 24 }} />
          </div>
          <h2 style={{ fontSize: 22, fontWeight: 600, color: '#fff', marginBottom: 6 }}>Authentication Required</h2>
          <p style={{ fontSize: 13, color: '#94a3b8' }}>Please enter your credentials to access the platform</p>
        </div>

        {/* Error message */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)',
            color: '#f87171', padding: '10px 14px', borderRadius: 8, fontSize: 12.5,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <i className="ti ti-alert-circle" style={{ fontSize: 16 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Email Address</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="e.g. admin@talentops.ai"
              style={{
                background: '#0b1329', border: '1px solid #232e52',
                color: '#fff', outline: 'none', borderRadius: 8, padding: 12, fontSize: 13.5
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{
                background: '#0b1329', border: '1px solid #232e52',
                color: '#fff', outline: 'none', borderRadius: 8, padding: 12, fontSize: 13.5
              }}
            />
          </div>

          <button
            type="submit"
            style={{
              background: '#185FA5', color: '#fff', fontWeight: 600,
              padding: 12, borderRadius: 8, border: 'none', cursor: 'pointer',
              fontSize: 13.5, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              marginTop: 6, transition: 'background 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#1b6dbd'}
            onMouseLeave={e => e.currentTarget.style.background = '#185FA5'}
          >
            <span>Unlock Platform</span>
            <i className="ti ti-arrow-right" style={{ fontSize: 14 }} />
          </button>
        </form>
      </div>
    </div>
  )
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Verify session on mount + periodic check
  useEffect(() => {
    const checkSession = () => {
      const sessionStr = localStorage.getItem('auth_session')
      if (sessionStr) {
        try {
          const session = JSON.parse(sessionStr)
          const isExpired = Date.now() - session.loginTime >= 24 * 60 * 60 * 1000 // 24 hours
          if (isExpired) {
            localStorage.removeItem('auth_session')
            setIsAuthenticated(false)
          } else {
            setIsAuthenticated(true)
          }
        } catch {
          localStorage.removeItem('auth_session')
          setIsAuthenticated(false)
        }
      } else {
        setIsAuthenticated(false)
      }
    }

    checkSession()
    // Run periodic validation check every 10 seconds to catch timeout in real time
    const interval = setInterval(checkSession, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleLoginSuccess = (email) => {
    localStorage.setItem('auth_session', JSON.stringify({
      email: email,
      loginTime: Date.now()
    }))
    setIsAuthenticated(true)
  }

  useEffect(() => {
    const style = document.createElement('style')
    style.textContent = globalStyles
    document.head.appendChild(style)
    return () => document.head.removeChild(style)
  }, [])

  if (!isAuthenticated) {
    return (
      <div style={{ position: 'relative', minHeight: '100vh' }}>
        <div style={{ position: 'absolute', top: 20, right: 20, zIndex: 100001 }}>
          <ThemeSwitcher />
        </div>
        <LoginScreen onLoginSuccess={handleLoginSuccess} />
      </div>
    )
  }

  return (
    <Router>
      <AppLayout />
    </Router>
  )
}

function AppLayout() {
  const location = useLocation()
  const isAnalytics = location.pathname === '/analytics'
  const isAdmin = location.pathname.startsWith('/admin')
  const isFullHeightPage = isAnalytics || isAdmin

  return (
    <>
      <PageTracker />
      <div style={{ display: 'flex', height: '100dvh', maxHeight: '100dvh', overflow: 'hidden', background: 'var(--main-bg)' }}>
        <Sidebar />
        <div className="shell-main" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, minWidth: 0 }}>
          <header style={{
            display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
            padding: isFullHeightPage ? (isAdmin ? '6px 16px' : '6px 16px') : '12px 32px',
            borderBottom: 'none',
            background: 'transparent', flexShrink: 0,
          }} className="topbar-glass">
            <div id="header-actions" style={{ display: 'flex', alignItems: 'center', gap: 12, marginRight: 16 }}></div>
            <ThemeSwitcher />
          </header>
          <main style={{
            flex: 1,
            minHeight: 0,
            padding: isFullHeightPage ? (isAdmin ? 0 : '8px 12px') : '16px 24px',
            overflow: isAnalytics ? 'hidden' : 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}>
            <div style={{
              flex: '1 1 0',
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: isAnalytics ? 'hidden' : (isAdmin ? 'hidden' : 'visible'),
            }}>
              <Suspense fallback={
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 12 }}>
                  <i className="ti ti-loader" style={{ fontSize: 22, color: 'var(--accent)', animation: 'spin 0.8s linear infinite' }} />
                  <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading...</span>
                </div>
              }>
                <GlobalErrorBoundary>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/recruiters" element={<Recruiters />} />
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/ai-search" element={<AISearch />} />
                    <Route path="/directory" element={<StateDirectory />} />
                    <Route path="/companies" element={<CompanyDirectory />} />
                    <Route path="/upload" element={<Upload />} />
                    <Route path="/admin" element={<AdminTerminal />} />
                  </Routes>
                </GlobalErrorBoundary>
              </Suspense>
            </div>
          </main>

          {!isFullHeightPage && (
            <footer style={{
              borderTop: '1px solid var(--card-border)',
              padding: '22px 36px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'var(--card-bg)',
              flexShrink: 0,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 26, height: 26, background: 'var(--accent)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ti ti-bolt" style={{ color: '#fff', fontSize: 14 }} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>TalentOps AI</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>— Recruitment Intelligence Platform</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Built by</span>
                <span style={{
                  fontSize: 15,
                  fontWeight: 700,
                  fontStyle: 'italic',
                  color: 'var(--text-primary)',
                  letterSpacing: '-0.01em',
                }}>
                  Abhishek Jadon
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 10, marginRight: 10 }}>|</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>© {new Date().getFullYear()}</span>
              </div>
            </footer>
          )}
        </div>
      </div>
    </>
  )
}

export default App

