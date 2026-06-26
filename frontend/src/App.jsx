import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import { useEffect, useMemo, useRef, useState, lazy, Suspense, Component } from 'react'
import Sidebar from './components/Sidebar'
import UpdateCenter from './components/UpdateCenter'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Recruiters = lazy(() => import('./pages/Recruiters'))
const Analytics = lazy(() => import('./pages/Analytics'))
const AISearch = lazy(() => import('./pages/AISearch'))
const Upload = lazy(() => import('./pages/Upload'))
const Directory = lazy(() => import('./pages/Directory'))
const AdminTerminal = lazy(() => import('./pages/AdminTerminal'))
const ActivityLog = lazy(() => import('./pages/ActivityLog'))

class GlobalErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
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

const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
  @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.0.0/dist/tabler-icons.min.css');

  :root {
    --sidebar-width: 276px;
    --main-bg: #f4f5f2;
    --panel-bg: #ffffff;
    --card-bg: #ffffff;
    --bg-primary: #f4f5f2;
    --bg-surface: #ffffff;
    --card-border: #d5d8d3;
    --card-border-strong: #b8bcb6;
    --sidebar-bg: #0d1527;
    --sidebar-border: #1c2741;
    --text-primary: #101318;
    --text-secondary: #4a5563;
    --text-muted: #788392;
    --text-inverse: #ffffff;
    --accent: #c35d08;
    --accent-strong: #8f4303;
    --accent-bg: rgba(195, 93, 8, 0.1);
    --success: #177245;
    --warning: #cb7a11;
    --danger: #c43a32;
    --muted-grid: rgba(16, 19, 24, 0.055);
    --dark-panel: #111a2f;
    --shadow: 0 10px 28px rgba(18, 24, 33, 0.08);
    --shadow-lg: 0 18px 48px rgba(18, 24, 33, 0.14);
    --radius: 14px;
    --radius-lg: 18px;
    --font: 'Inter', system-ui, sans-serif;
    --mono: 'IBM Plex Mono', monospace;
  }

  [data-theme='dark'] {
    --main-bg: #141414;
    --panel-bg: #1b1b1b;
    --card-bg: #202020;
    --bg-primary: #141414;
    --bg-surface: #1b1b1b;
    --card-border: #343434;
    --card-border-strong: #4a4a4a;
    --sidebar-bg: #151515;
    --sidebar-border: #2a2a2a;
    --text-primary: #f2f2f2;
    --text-secondary: #cdcdcd;
    --text-muted: #959595;
    --text-inverse: #111111;
    --accent: #dddddd;
    --accent-strong: #bbbbbb;
    --accent-bg: rgba(255, 255, 255, 0.06);
    --success: #d7d7d7;
    --warning: #c9c9c9;
    --danger: #aaaaaa;
    --muted-grid: rgba(255, 255, 255, 0.05);
    --dark-panel: #171717;
    --shadow: 0 10px 24px rgba(0, 0, 0, 0.24);
    --shadow-lg: 0 18px 44px rgba(0, 0, 0, 0.34);
  }

  *, *::before, *::after { box-sizing: border-box; }
  html, body, #root {
    min-height: 100%;
    margin: 0;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.0)),
      linear-gradient(180deg, var(--bg-primary), var(--bg-primary));
    color: var(--text-primary);
    font-family: var(--font);
    overflow-x: hidden;
    overflow-y: auto;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  html[data-theme='dark'] body,
  html[data-theme='dark'] #root {
    background: var(--main-bg);
  }

  html[data-theme='dark'] .cc-content {
    background: linear-gradient(180deg, var(--bg-primary), var(--bg-primary)) !important;
  }

  html[data-theme='dark'] .cc-footer {
    background: rgba(22,22,22,0.95) !important;
    border-top-color: #313131 !important;
  }

  html[data-theme='dark'] .card,
  html[data-theme='dark'] .cc-card,
  html[data-theme='dark'] .cc-metric {
    background: #1c1c1c !important;
    border-color: #343434 !important;
    box-shadow: none !important;
  }

  html[data-theme='dark'] th {
    background: #181818 !important;
    color: #dddddd !important;
    border-bottom-color: #333333 !important;
  }

  html[data-theme='dark'] td {
    color: #f0f0f0 !important;
    border-bottom-color: #333333 !important;
  }

  html[data-theme='dark'] tr:hover td {
    background: #242424 !important;
  }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
      linear-gradient(to right, var(--muted-grid) 1px, transparent 1px),
      linear-gradient(to bottom, var(--muted-grid) 1px, transparent 1px);
    background-size: 32px 32px;
    mask-image: linear-gradient(to bottom, rgba(0,0,0,0.55), transparent 92%);
    opacity: 0.8;
    z-index: 0;
  }

  #root {
    position: relative;
    z-index: 1;
    min-height: 100dvh;
  }

  ::-webkit-scrollbar { width: 10px; height: 10px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(120, 130, 145, 0.35); border-radius: 999px; border: 2px solid transparent; background-clip: padding-box; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(120, 130, 145, 0.58); border: 2px solid transparent; background-clip: padding-box; }

  a { color: inherit; text-decoration: none; }
  button, input, select, textarea { font: inherit; }
  button { border: none; }

  input, select, textarea {
    background: var(--panel-bg);
    color: var(--text-primary);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 10px 12px;
    outline: none;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease, background 0.15s ease;
  }
  input:focus, select:focus, textarea:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-bg);
  }
  input::placeholder, textarea::placeholder { color: var(--text-muted); }

  table { border-collapse: collapse; width: 100%; }
  th, td { text-align: left; }
  th {
    padding: 12px 14px;
    font-size: 10.5px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
    font-weight: 800;
    background: rgba(255,255,255,0.55);
    border-bottom: 1px solid var(--card-border);
  }
  td {
    padding: 12px 14px;
    border-bottom: 1px solid var(--card-border);
    color: var(--text-primary);
  }
  tr:hover td { background: rgba(255,255,255,0.65); }

  .card, .cc-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow);
  }

  .page-enter { animation: ccFadeUp 0.26s ease both; }

  .cc-shell {
    min-height: 100dvh;
    display: flex;
    background: transparent;
    color: var(--text-primary);
  }

  .cc-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    min-height: 100dvh;
  }

  .cc-topbar {
    position: sticky;
    top: 0;
    z-index: 30;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 16px;
    align-items: center;
    padding: 10px 14px 10px 12px;
    background: rgba(21, 21, 21, 0.96);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    backdrop-filter: blur(8px);
  }

  .cc-session-strip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .cc-session-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.9);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 800;
  }

  .cc-session-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #22c55e;
    box-shadow: 0 0 0 4px rgba(34,197,94,0.15);
  }

  .cc-session-time {
    padding: 7px 11px;
    border-radius: 10px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.9);
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.08em;
  }

  .cc-top-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .cc-icon-button, .cc-ghost-button, .cc-primary-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border-radius: 12px;
    cursor: pointer;
    transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease, box-shadow 0.15s ease;
  }

  .cc-icon-button {
    width: 38px;
    height: 38px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.92);
  }

  .cc-icon-button:hover, .cc-ghost-button:hover, .cc-primary-button:hover { transform: translateY(-1px); }

  .cc-ghost-button {
    padding: 10px 14px;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-weight: 700;
  }

  .cc-primary-button {
    padding: 10px 14px;
    background: linear-gradient(135deg, var(--accent), var(--accent-strong));
    color: var(--text-inverse);
    box-shadow: 0 10px 22px rgba(195,93,8,0.16);
    font-weight: 800;
  }

  .cc-layout {
    flex: 1;
    min-height: 0;
    display: flex;
    min-width: 0;
  }

  .cc-content {
    flex: 1 0 auto;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: visible;
    background: linear-gradient(180deg, rgba(244,245,242,0.8), rgba(244,245,242,1));
  }

  .cc-page-body {
    flex: 1 0 auto;
    min-height: auto;
    overflow: visible;
    padding: 18px 18px 96px;
  }

  .cc-footer {
    position: fixed;
    bottom: 0;
    left: var(--sidebar-width);
    right: 0;
    z-index: 25;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    padding: 14px 20px;
    border-top: 1px solid var(--card-border);
    background: var(--bg-surface);
    backdrop-filter: blur(6px);
    font-size: 12px;
    color: var(--text-secondary);
  }

  .cc-footer strong { color: var(--text-primary); }

  .cc-footer-center {
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    min-width: 0;
    padding: 0 16px;
    text-align: center;
  }

  .cc-eyebrow {
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 6px;
  }

  .cc-section-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .cc-title-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    min-width: 0;
  }

  .cc-title-icon {
    width: 34px;
    height: 34px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    background: var(--accent-bg);
    color: var(--accent);
    border: 1px solid rgba(195,93,8,0.18);
    flex-shrink: 0;
  }

  .cc-section-title {
    margin: 0;
    font-size: 18px;
    line-height: 1.1;
    font-weight: 900;
    letter-spacing: -0.03em;
  }

  .cc-section-subtitle {
    margin: 4px 0 0;
    color: var(--text-muted);
    font-size: 12.5px;
    line-height: 1.5;
  }

  .cc-metric {
    padding: 18px 18px 16px;
    border: 1px solid var(--card-border);
    border-radius: 16px;
    background: rgba(255,255,255,0.9);
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .cc-metric-contrast {
    background: linear-gradient(180deg, #232323, #181818);
    color: #fff;
    border-color: rgba(255,255,255,0.08);
  }

  .cc-metric-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
  }

  .cc-metric-label {
    font-size: 11px;
    font-weight: 900;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: inherit;
    opacity: 0.7;
  }

  .cc-metric-value {
    font-size: 30px;
    line-height: 1;
    font-weight: 900;
    letter-spacing: -0.04em;
    color: inherit;
  }

  .cc-metric-sub {
    font-size: 12px;
    color: inherit;
    opacity: 0.72;
  }

  .cc-metric-icon {
    font-size: 18px;
    color: var(--accent);
    flex-shrink: 0;
  }

  .cc-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 10.5px;
    font-weight: 900;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
    border: 1px solid transparent;
  }

  .cc-badge-neutral { background: rgba(120,130,145,0.12); color: var(--text-secondary); border-color: rgba(120,130,145,0.18); }
  .cc-badge-success { background: rgba(23,114,69,0.12); color: var(--success); border-color: rgba(23,114,69,0.18); }
  .cc-badge-warning { background: rgba(203,122,17,0.12); color: var(--warning); border-color: rgba(203,122,17,0.18); }
  .cc-badge-danger { background: rgba(196,58,50,0.12); color: var(--danger); border-color: rgba(196,58,50,0.18); }
  .cc-badge-contrast { background: rgba(255,255,255,0.1); color: #fff; border-color: rgba(255,255,255,0.12); }

  .cc-progress {
    width: 100%;
    height: 10px;
    border-radius: 999px;
    background: rgba(120,130,145,0.16);
    overflow: hidden;
  }

  .cc-progress-fill {
    height: 100%;
    border-radius: inherit;
    transition: width 0.25s ease;
    background: linear-gradient(90deg, var(--accent), var(--accent-strong));
  }
  .cc-progress-success { background: linear-gradient(90deg, var(--success), #26a96d); }
  .cc-progress-warning { background: linear-gradient(90deg, var(--warning), #d39a12); }
  .cc-progress-danger { background: linear-gradient(90deg, var(--danger), #d95d5d); }

  .cc-empty {
    display: grid;
    place-items: center;
    gap: 8px;
    min-height: 240px;
    padding: 24px;
    text-align: center;
    color: var(--text-muted);
  }
  .cc-empty-icon {
    width: 54px;
    height: 54px;
    border-radius: 18px;
    display: grid;
    place-items: center;
    color: var(--accent);
    background: var(--accent-bg);
    border: 1px solid rgba(195,93,8,0.16);
    font-size: 20px;
  }
  .cc-empty-title { font-size: 14px; font-weight: 900; color: var(--text-primary); }
  .cc-empty-desc { font-size: 12px; line-height: 1.55; max-width: 560px; }

  .cc-timeline-item {
    display: grid;
    grid-template-columns: 20px 1fr;
    gap: 12px;
    align-items: start;
  }
  .cc-timeline-dot {
    width: 20px;
    height: 20px;
    border-radius: 999px;
    display: grid;
    place-items: center;
    font-size: 10px;
    background: rgba(120,130,145,0.12);
    color: var(--text-secondary);
    border: 1px solid rgba(120,130,145,0.18);
    margin-top: 2px;
  }
  .cc-timeline-title { font-size: 13px; font-weight: 800; color: var(--text-primary); }
  .cc-timeline-meta { margin-top: 2px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); }
  .cc-timeline-desc { margin-top: 4px; font-size: 12px; line-height: 1.5; color: var(--text-secondary); }

  .cc-error-shell {
    min-height: 100dvh;
    display: grid;
    place-items: center;
    gap: 12px;
    padding: 24px;
    text-align: center;
    background: var(--main-bg);
  }
  .cc-error-shell h2 { margin: 0; font-size: 20px; font-weight: 900; }
  .cc-error-shell p { margin: 0; max-width: 520px; color: var(--text-muted); line-height: 1.6; }
  .cc-error-icon { font-size: 44px; color: var(--danger); }
  .cc-error-actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }

  .badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 10.5px; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; }
  .badge-green { background: rgba(23,114,69,0.12); color: var(--success); }
  .badge-blue { background: rgba(120,120,120,0.12); color: var(--text-secondary); }
  .badge-amber { background: rgba(203,122,17,0.12); color: var(--warning); }
  .badge-red { background: rgba(196,58,50,0.12); color: var(--danger); }
  .badge-gray { background: rgba(120,130,145,0.12); color: var(--text-secondary); }

  .page-container { display: flex; flex-direction: column; gap: 16px; }
  .page-title { margin: 0; font-size: 24px; line-height: 1.05; font-weight: 900; letter-spacing: -0.04em; }
  .page-subtitle { margin: 6px 0 0; color: var(--text-muted); font-size: 13px; line-height: 1.5; }

  @keyframes ccFadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes ccSpin { to { transform: rotate(360deg); } }
  @keyframes ccPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.45; } }
  .animate-spin { animation: ccSpin 0.9s linear infinite; }
`

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
  '/states': 'Directory',
  '/companies': 'Directory',
  '/upload': 'ETL',
  '/admin': 'Admin Ops',
  '/activity': 'Global Activity Log',
}

function getSessionId() {
  let sid = sessionStorage.getItem('talentops_sid')
  if (!sid) {
    sid = crypto.randomUUID ? crypto.randomUUID() : `${Math.random().toString(36).slice(2)}${Date.now()}`
    sessionStorage.setItem('talentops_sid', sid)
  }
  return sid
}

function PageTracker() {
  const location = useLocation()
  const entryTimeRef = useRef(null)
  const lastLoggedRef = useRef(null)

  useEffect(() => {
    if (entryTimeRef.current === null) {
      entryTimeRef.current = Date.now()
    }
    const prevPath = entryTimeRef._prevPath
    const enteredAt = entryTimeRef.current
    const timeOnPage = prevPath ? Math.round((Date.now() - enteredAt) / 1000) : null
    entryTimeRef.current = Date.now()
    entryTimeRef._prevPath = location.pathname
    const page = PAGE_NAMES[location.pathname] || location.pathname
    const session = (() => {
      try {
        return JSON.parse(localStorage.getItem('auth_session') || '{}')
      } catch {
        return {}
      }
    })()

    const apiUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
    const logKey = `${location.pathname}:${page}:${session?.email || ''}`
    if (lastLoggedRef.current === logKey) {
      return
    }
    lastLoggedRef.current = logKey
    fetch(`${apiUrl}/analytics/log-visit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
      body: JSON.stringify({
        page,
        path: location.pathname,
        user_email: session.email || null,
        session_id: getSessionId(),
        time_on_page: timeOnPage,
      }),
    }).catch(() => {})
  }, [location.pathname])

  return null
}

function AppShell() {
  const location = useLocation()

  const pageName = useMemo(() => PAGE_NAMES[location.pathname] || 'Dashboard', [location.pathname])

  return (
    <>
      <PageTracker />
      <UpdateCenter />
      <div className="cc-shell">
        <Sidebar />
        <div className="cc-main">
          <header className="cc-topbar">
            <div style={{ color: 'rgba(255,255,255,0.72)', fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', minWidth: 0 }}>
              {pageName}
            </div>
            <div className="cc-top-actions">
              <div id="header-actions" style={{ display: 'flex', alignItems: 'center', gap: 10 }} />
              <button className="cc-icon-button" title="Settings" aria-label="Settings">
                <i className="ti ti-settings" />
              </button>
              <button className="cc-icon-button" title="Notifications" aria-label="Notifications" style={{ position: 'relative' }}>
                <i className="ti ti-bell" />
                <span style={{ position: 'absolute', top: 7, right: 9, width: 8, height: 8, borderRadius: 999, background: 'var(--danger)' }} />
              </button>
              <button className="cc-icon-button" title="Account" aria-label="Account">
                <i className="ti ti-user-circle" />
              </button>
              <ThemeSwitcher />
            </div>
          </header>

          <div className="cc-content">
            <main className="cc-page-body">
              <Suspense
                fallback={
                  <div style={{ display: 'grid', placeItems: 'center', minHeight: '60vh', gap: 12, color: 'var(--text-muted)' }}>
                    <i className="ti ti-loader animate-spin" style={{ fontSize: 24, color: 'var(--accent)' }} />
                    <span>Loading command center...</span>
                  </div>
                }
              >
                <GlobalErrorBoundary>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/recruiters" element={<Recruiters />} />
                    <Route path="/analytics" element={<Analytics />} />
                    <Route path="/ai-search" element={<AISearch />} />
                    <Route path="/directory" element={<Directory />} />
                    <Route path="/states" element={<Directory />} />
                    <Route path="/companies" element={<Directory />} />
                    <Route path="/admin" element={<AdminTerminal />} />
                    <Route path="/activity" element={<ActivityLog />} />
                  </Routes>
                </GlobalErrorBoundary>
              </Suspense>
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

export default function App() {
  useEffect(() => {
    const style = document.createElement('style')
    style.textContent = globalStyles
    document.head.appendChild(style)
    return () => document.head.removeChild(style)
  }, [])

  return (
    <Router>
      <AppShell />
    </Router>
  )
}
