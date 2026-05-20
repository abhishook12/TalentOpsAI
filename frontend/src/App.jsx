import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import { useEffect, useState, lazy, Suspense } from 'react'
import Sidebar from './components/Sidebar'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Recruiters = lazy(() => import('./pages/Recruiters'))
const Analytics  = lazy(() => import('./pages/Analytics'))
const AISearch   = lazy(() => import('./pages/AISearch'))
const Upload     = lazy(() => import('./pages/Upload'))
const StateDirectory = lazy(() => import('./pages/StateDirectory'))
const CompanyDirectory = lazy(() => import('./pages/CompanyDirectory'))

const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
  @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.0.0/dist/tabler-icons.min.css');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root, [data-theme="light"] {
    --sidebar-bg: #0b1120;
    --sidebar-border: #172033;
    --sidebar-width: 220px;
    --accent: #185FA5;
    --accent-light: #7dd3fc;
    --main-bg: #f8fafc;
    --card-bg: #ffffff;
    --card-border: #e8edf4;
    --text-primary: #0f172a;
    --text-secondary: #64748b;
    --text-muted: #94a3b8;
    --font: 'DM Sans', sans-serif;
    --mono: 'DM Mono', monospace;
    --radius: 10px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.04);
  }

  [data-theme="dark"] {
    --sidebar-bg: #09090b;
    --sidebar-border: #27272a;
    --accent: #38bdf8;
    --accent-light: #7dd3fc;
    --main-bg: #0f172a;
    --card-bg: #1e293b;
    --card-border: #334155;
    --text-primary: #f8fafc;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    --shadow: 0 4px 12px rgba(0,0,0,0.2);
  }

  [data-theme="sepia"] {
    --sidebar-bg: #2d261b;
    --sidebar-border: #4a4132;
    --accent: #d08770;
    --accent-light: #bf616a;
    --main-bg: #fbf0d9;
    --card-bg: #fdf6e3;
    --card-border: #e6d5b8;
    --text-primary: #5c4b37;
    --text-secondary: #8a7b66;
    --text-muted: #b5a691;
    --shadow: 0 1px 3px rgba(92,75,55,0.06);
  }

  html, body, #root {
    height: 100%;
    font-family: var(--font);
    background: var(--main-bg);
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
    transition: background 0.3s ease, color 0.3s ease;
  }

  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 10px; }

  table { border-collapse: collapse; width: 100%; }
  th {
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 10px 16px;
    background: var(--main-bg);
    border-bottom: 1px solid var(--card-border);
    text-align: left;
  }
  td {
    padding: 11px 16px;
    font-size: 13.5px;
    color: var(--text-primary);
    border-bottom: 1px solid var(--card-border);
    vertical-align: middle;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--main-bg); }

  input, select, textarea {
    font-family: var(--font);
    font-size: 13.5px;
    color: var(--text-primary);
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 9px 13px;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  input:focus, select:focus, textarea:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(24,95,165,0.1);
  }

  button {
    font-family: var(--font);
    cursor: pointer;
    border: none;
    border-radius: 8px;
    font-size: 13.5px;
    font-weight: 500;
    transition: all 0.15s ease;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  .page-enter { animation: fadeUp 0.25s ease forwards; }

  .card {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
  }

  .btn-primary {
    background: var(--accent);
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
    transition: background 0.15s;
  }
  .btn-primary:hover { filter: brightness(1.1); }

  .badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
  }
  .badge-blue { background: rgba(59,130,246,0.1); color: var(--accent); }
  .badge-green { background: rgba(34,197,94,0.1); color: #22c55e; }
  .badge-gray { background: rgba(100,116,139,0.1); color: var(--text-secondary); }
  .badge-red { background: rgba(239,68,68,0.1); color: #ef4444; }
  .badge-amber { background: rgba(245,158,11,0.1); color: #f59e0b; }
`
function ThemeSwitcher() {
  const themes = ['light', 'dark', 'sepia']
  const icons = ['ti-sun', 'ti-moon', 'ti-eye']
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggle = () => {
    const next = themes[(themes.indexOf(theme) + 1) % themes.length]
    setTheme(next)
  }

  return (
    <button onClick={toggle} style={{
      position: 'fixed', bottom: 24, right: 24, width: 48, height: 48,
      borderRadius: '50%', background: 'var(--card-bg)', border: '1px solid var(--card-border)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 9999, color: 'var(--text-primary)', fontSize: 22, transition: 'transform 0.2s'
    }} onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'} onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}>
      <i className={`ti ${icons[themes.indexOf(theme)]}`} />
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
  '/upload': 'Upload',
}

function PageTracker() {
  const location = useLocation()
  useEffect(() => {
    const page = PAGE_NAMES[location.pathname] || location.pathname
    fetch(`${API}/analytics/log-visit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page, path: location.pathname }),
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
      <>
        <LoginScreen onLoginSuccess={handleLoginSuccess} />
        <ThemeSwitcher />
      </>
    )
  }

  return (
    <Router>
      <PageTracker />
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--main-bg)' }}>
        <Sidebar />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--main-bg)' }}>
          <main style={{ flex: 1, padding: '28px 32px', overflowY: 'auto' }}>
            <Suspense fallback={
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 12 }}>
                <i className="ti ti-loader" style={{ fontSize: 22, color: 'var(--accent)', animation: 'spin 0.8s linear infinite' }} />
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading...</span>
              </div>
            }>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/recruiters" element={<Recruiters />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/ai-search" element={<AISearch />} />
                  <Route path="/directory" element={<StateDirectory />} />
                  <Route path="/companies" element={<CompanyDirectory />} />
                  <Route path="/upload" element={<Upload />} />
                </Routes>
            </Suspense>
          </main>

          {/* Footer */}
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
        </div>
        <ThemeSwitcher />
      </div>
    </Router>
  )
}

export default App

