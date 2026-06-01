import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import React, { useEffect, useState, lazy, Suspense, useRef, Component } from 'react'
import Sidebar from './components/Sidebar'
import UpdateCenter from './components/UpdateCenter'
import { API } from './services/api'

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

  /* ── Default light editorial shell ── */
  :root {
    --sidebar-bg: #efefec;
    --sidebar-border: #d8d8d8;
    --sidebar-width: 248px;
    --accent: #15171b;
    --accent-glow: rgba(0,0,0,0.08);
    --accent-light: #20252b;
    --main-bg: #f7f7f5;
    --panel-bg: #ffffff;
    --card-bg: #ffffff;
    --card-bg-hover: #fafaf9;
    --card-border: #d8d8d8;
    --card-border-hover: #c7c7c7;
    --text-primary: #17191d;
    --text-secondary: #3f454f;
    --text-muted: #727a85;
    --font: 'Inter', system-ui, sans-serif;
    --mono: 'JetBrains Mono', monospace;
    --radius: 10px;
    --radius-lg: 14px;
    --shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    --shadow-lg: 0 10px 24px rgba(0, 0, 0, 0.08);
    --bg-hover: rgba(0,0,0,0.04);
    --accent-bg: rgba(0,0,0,0.06);
    --accent-hover: #0f1114;
    --text-inverse: #ffffff;
    --green: #3fb950;
    --red: #f85149;
    --amber: #d29922;
  }

  [data-theme="light"], [data-theme="sepia"] {}

  [data-theme="dark"] {
    --sidebar-bg: #141619;
    --sidebar-border: #2a2d33;
    --accent: #7f8794;
    --accent-glow: rgba(127,135,148,0.16);
    --accent-light: #9aa2ad;
    --main-bg: #101214;
    --panel-bg: #16191d;
    --card-bg: #1b1f24;
    --card-bg-hover: #21262d;
    --card-border: #2c323a;
    --card-border-hover: #3a424d;
    --text-primary: #e8ebef;
    --text-secondary: #b2b8c0;
    --text-muted: #7f8793;
    --shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 16px 36px rgba(0, 0, 0, 0.4);
    --bg-hover: rgba(255,255,255,0.04);
    --accent-bg: rgba(255,255,255,0.08);
    --accent-hover: #ffffff;
    --text-inverse: #ffffff;
  }

  html, body, #root {
    height: 100%;
    overflow: hidden;
    font-family: var(--font);
    background: var(--main-bg);
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
    box-shadow: 0 0 0 3px var(--accent-glow);
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
    backdrop-filter: none;
  }
  .card:hover {
    border-color: var(--card-border-hover) !important;
    transform: translateY(-1px);
  }

  .btn-primary {
    background: #15171b;
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
  .btn-primary:hover { filter: brightness(1.03); box-shadow: 0 6px 14px var(--accent-glow); transform: translateY(-1px); }

  .shell-main { background: var(--main-bg); }

  .topbar-glass {
    margin: 10px 12px 0;
    border: 1px solid var(--card-border);
    border-radius: 14px;
    background: #ffffff;
    box-shadow: var(--shadow);
    backdrop-filter: none;
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
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      style={{
        width: 36,
        height: 36,
        borderRadius: 8,
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text-primary)',
        cursor: 'pointer',
      }}
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
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [remember, setRemember] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const pinRef = useRef(pin)
  pinRef.current = pin

  const pressKey = (k) => {
    if (submitting) return
    if (k === 'backspace') setPin(p => p.slice(0, -1))
    else if (k === 'enter') handleSubmit()
    else setPin(p => (p.length < 12 ? p + k : p))
  }

  const handleSubmit = async (e) => {
    if (e?.preventDefault) e.preventDefault()
    if (!email.trim() || !pinRef.current.trim()) {
      setError('Please fill in all fields.')
      return
    }
    // Basic email format check
    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await appLogin(pinRef.current, remember)
      onLoginSuccess(email)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Authentication failed.')
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    const onKeyDown = (e) => {
      if (submitting) return
      if (/^[0-9]$/.test(e.key)) {
        e.preventDefault()
        pressKey(e.key)
        return
      }
      if (e.key === 'Backspace' || e.key === 'Delete') {
        e.preventDefault()
        pressKey('backspace')
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        pressKey('enter')
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [pressKey, submitting])

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100000,
      display: 'grid',
      gridTemplateColumns: '1.2fr 1fr',
      background: 'linear-gradient(135deg, #0a0f1e 0%, #070a12 55%, #05060b 100%)',
      color: '#e5e7eb',
      fontFamily: 'var(--font)',
    }}>
      {/* Left brand panel */}
      <div style={{
        padding: 44,
        background: 'radial-gradient(1200px 800px at 30% 20%, rgba(99,102,241,0.22), transparent 55%), radial-gradient(900px 600px at 60% 70%, rgba(59,130,246,0.18), transparent 60%)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        flexDirection: 'column',
        gap: 22,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 52, height: 52, borderRadius: 14, background: 'rgba(99,102,241,0.22)', border: '1px solid rgba(99,102,241,0.28)', display: 'grid', placeItems: 'center' }}>
            <i className="ti ti-terminal-2" style={{ fontSize: 22, color: '#c7d2fe' }} />
          </div>
          <div style={{ fontSize: 34, fontWeight: 900, letterSpacing: '-0.02em' }}>RECRUIT-INTEL</div>
        </div>
        <div style={{ fontSize: 14, color: 'rgba(229,231,235,0.85)' }}>Recruitment Intelligence Platform</div>
        <div style={{ fontSize: 22, lineHeight: 1.55, color: 'rgba(229,231,235,0.62)', maxWidth: 620 }}>
          Manage recruiter intelligence, company data, state directories, ETL operations, analytics, and platform administration within our unified operational command center.
        </div>
        <div style={{ marginTop: 'auto', display: 'flex', gap: 14, alignItems: 'center', opacity: 0.9 }}>
          <div className="card" style={{ padding: 16, borderRadius: 18, width: 220, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: 10, color: 'rgba(229,231,235,0.65)', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase' }}>ETL Pipeline</div>
            <div style={{ marginTop: 10, height: 6, borderRadius: 999, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
              <div style={{ width: '62%', height: '100%', background: 'rgba(99,102,241,0.75)' }} />
            </div>
            <div style={{ marginTop: 10, fontSize: 12, color: 'rgba(229,231,235,0.75)' }}>98.2% Accuracy Rate</div>
          </div>
          <div className="card" style={{ padding: 16, borderRadius: 18, width: 220, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: 10, color: 'rgba(229,231,235,0.65)', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Active Clusters</div>
            <div style={{ marginTop: 8, fontSize: 26, fontWeight: 900 }}>1,204</div>
            <div style={{ marginTop: 2, fontSize: 12, color: '#34d399' }}>+12%</div>
          </div>
        </div>
      </div>

      {/* Right access panel */}
      <div style={{ display: 'grid', placeItems: 'center', padding: 28 }}>
        <div className="card" style={{
          width: '100%',
          maxWidth: 440,
          borderRadius: 22,
          padding: '28px 26px',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 24px 60px rgba(0,0,0,0.55)',
          backdropFilter: 'blur(14px)',
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
          alignItems: 'center',
        }}>
          <div style={{ fontSize: 14, fontWeight: 900, letterSpacing: '-0.01em' }}>Platform Access</div>
          <div style={{ fontSize: 13, color: 'rgba(229,231,235,0.65)', textAlign: 'center', lineHeight: 1.5 }}>
            Enter your secure credentials to access the platform.
          </div>

          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            {[0,1,2,3].map(i => (
              <div key={i} style={{ width: 12, height: 12, borderRadius: 999, border: '1px solid rgba(255,255,255,0.22)', background: pin.length > i ? 'rgba(99,102,241,0.9)' : 'transparent', boxShadow: pin.length > i ? '0 0 12px rgba(99,102,241,0.35)' : 'none' }} />
            ))}
          </div>

          <div style={{ width: '100%', marginTop: 8, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
            {[
              { key: '1', label: '1' },
              { key: '2', label: '2' },
              { key: '3', label: '3' },
              { key: '4', label: '4' },
              { key: '5', label: '5' },
              { key: '6', label: '6' },
              { key: '7', label: '7' },
              { key: '8', label: '8' },
              { key: '9', label: '9' },
              { key: 'backspace', label: <i className="ti ti-backspace" /> },
              { key: '0', label: '0' },
              { key: 'enter', label: <i className="ti ti-arrow-right" /> },
            ].map((k) => (
              <button
                key={k.key}
                type="button"
                onClick={() => pressKey(k.key)}
                disabled={submitting}
                style={{
                  height: 58,
                  borderRadius: 999,
                  border: '1px solid rgba(255,255,255,0.10)',
                  background: 'rgba(255,255,255,0.02)',
                  color: '#e5e7eb',
                  fontSize: 18,
                  fontWeight: 800,
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  opacity: submitting ? 0.65 : 1,
                  display: 'grid',
                  placeItems: 'center',
                }}
              >
                {k.label}
              </button>
            ))}
          </div>

          <div style={{ width: '100%', display: 'grid', gap: 10, marginTop: 6 }}>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email (for session label)"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 14, border: '1px solid rgba(255,255,255,0.10)', background: 'rgba(255,255,255,0.02)', color: '#e5e7eb', outline: 'none' }}
            />
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'rgba(229,231,235,0.7)', cursor: submitting ? 'not-allowed' : 'pointer', opacity: submitting ? 0.7 : 1 }}>
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} disabled={submitting} />
              Remember session
            </label>
            {error && <div style={{ fontSize: 12, color: '#f87171', textAlign: 'center' }}>{error}</div>}
            <button
              type="button"
              className="btn-primary"
              onClick={handleSubmit}
              disabled={submitting}
              style={{ width: '100%', borderRadius: 14, padding: '12px 14px', fontWeight: 900, justifyContent: 'center', opacity: submitting ? 0.75 : 1 }}
            >
              {submitting ? 'Verifying…' : 'Access Platform'}
            </button>
          </div>

          <div style={{ marginTop: 8, fontSize: 11, letterSpacing: '0.14em', color: 'rgba(229,231,235,0.45)', textTransform: 'uppercase', textAlign: 'center' }}>
            Restricted access • authorized personnel only
          </div>
        </div>
      </div>
    </div>
  )
}

function App() {
  useEffect(() => {
    const style = document.createElement('style')
    style.textContent = globalStyles
    document.head.appendChild(style)
    return () => document.head.removeChild(style)
  }, [])

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
      <UpdateCenter />
      <div style={{ display: 'flex', height: '100dvh', maxHeight: '100dvh', overflow: 'hidden', background: 'var(--main-bg)' }}>
        <Sidebar />
        <div className="shell-main" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, minWidth: 0 }}>
          <header style={{
            display: 'none',
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
        <div style={{ position: 'fixed', top: 14, right: 16, zIndex: 1200 }}>
          <ThemeSwitcher />
        </div>
      </div>
    </>
  )
}

export default App

