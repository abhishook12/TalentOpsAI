import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const ADMIN_TOKEN = 'talentops-admin-1012'
const ADMIN_PIN = '1012'

const adminAxios = axios.create({
  baseURL: API,
  headers: { 'X-Admin-Token': ADMIN_TOKEN }
})

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmt(n) { return n?.toLocaleString?.() ?? '—' }
function pct(n, t) { return t ? Math.round(n / t * 100) : 0 }

function StatCard({ icon, label, value, sub, color = '#185FA5', glow }) {
  return (
    <div style={{
      background: '#0d1829', border: `1px solid ${glow ? color : '#1e2d45'}`,
      borderRadius: 12, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 8,
      boxShadow: glow ? `0 0 20px ${color}33` : 'none',
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 34, height: 34, borderRadius: 8, background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className={`ti ${icon}`} style={{ color, fontSize: 18 }} />
        </div>
        <span style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600 }}>{label}</span>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: '#e2e8f0', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub && <div style={{ fontSize: 11.5, color: '#475569' }}>{sub}</div>}
    </div>
  )
}

function Section({ title, icon, children, action }) {
  return (
    <div style={{ background: '#0d1829', border: '1px solid #1e2d45', borderRadius: 14, overflow: 'hidden', marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid #1e2d45', background: '#0b1525' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <i className={`ti ${icon}`} style={{ color: '#38bdf8', fontSize: 17 }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: '#cbd5e1', letterSpacing: '-0.01em' }}>{title}</span>
        </div>
        {action}
      </div>
      <div style={{ padding: 20 }}>{children}</div>
    </div>
  )
}

function Badge({ children, color = '#38bdf8' }) {
  return <span style={{ background: `${color}22`, color, fontSize: 10.5, fontWeight: 600, padding: '2px 8px', borderRadius: 99, display: 'inline-block' }}>{children}</span>
}

// ── Lock Screen ───────────────────────────────────────────────────────────────
function AdminLock({ onUnlock }) {
  const [pin, setPin] = useState('')
  const [shake, setShake] = useState(false)
  const [attempts, setAttempts] = useState(0)

  const submit = () => {
    if (pin === ADMIN_PIN) { onUnlock(); return }
    setShake(true); setAttempts(a => a + 1); setPin('')
    setTimeout(() => setShake(false), 600)
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #020817 0%, #0b1525 50%, #020817 100%)',
      fontFamily: "'DM Mono', monospace",
    }}>
      {/* Animated grid background */}
      <div style={{ position: 'fixed', inset: 0, opacity: 0.05, backgroundImage: 'linear-gradient(#38bdf8 1px, transparent 1px), linear-gradient(90deg, #38bdf8 1px, transparent 1px)', backgroundSize: '40px 40px', pointerEvents: 'none' }} />

      <div style={{ position: 'relative', width: 360, animation: shake ? 'shake 0.5s' : 'none' }}>
        <style>{`
          @keyframes shake { 0%,100%{transform:translateX(0)} 20%,60%{transform:translateX(-8px)} 40%,80%{transform:translateX(8px)} }
          @keyframes pulse-ring { 0%{transform:scale(1);opacity:0.4} 100%{transform:scale(1.5);opacity:0} }
          @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        `}</style>

        {/* Glow ring */}
        <div style={{ position: 'absolute', top: -60, left: '50%', transform: 'translateX(-50%)', width: 80, height: 80, borderRadius: '50%', background: '#38bdf822', animation: 'pulse-ring 2s ease-out infinite' }} />

        <div style={{
          background: '#0d1829', border: '1px solid #1e3a5f',
          borderRadius: 20, padding: '40px 36px', backdropFilter: 'blur(12px)',
          boxShadow: '0 0 60px rgba(56,189,248,0.08), 0 24px 48px rgba(0,0,0,0.5)',
          display: 'flex', flexDirection: 'column', gap: 28, alignItems: 'center',
        }}>
          {/* Icon */}
          <div style={{ position: 'relative' }}>
            <div style={{ width: 64, height: 64, borderRadius: 16, background: 'linear-gradient(135deg, #0ea5e9, #1d4ed8)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 30px rgba(14,165,233,0.4)' }}>
              <i className="ti ti-terminal-2" style={{ color: '#fff', fontSize: 30 }} />
            </div>
            <div style={{ position: 'absolute', top: -4, right: -4, width: 16, height: 16, borderRadius: '50%', background: '#ef4444', border: '2px solid #0d1829', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <i className="ti ti-lock" style={{ color: '#fff', fontSize: 8 }} />
            </div>
          </div>

          {/* Title */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.02em', marginBottom: 6 }}>ADMIN TERMINAL</div>
            <div style={{ fontSize: 12, color: '#475569', fontFamily: "'DM Mono', monospace" }}>
              <span style={{ color: '#38bdf8', animation: 'blink 1.2s step-end infinite' }}>▌</span> Restricted access. Authorisation required.
            </div>
          </div>

          {/* PIN dots */}
          <div style={{ display: 'flex', gap: 12 }}>
            {[0,1,2,3].map(i => (
              <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid', borderColor: pin.length > i ? '#38bdf8' : '#1e3a5f', background: pin.length > i ? '#38bdf8' : 'transparent', transition: 'all 0.15s', boxShadow: pin.length > i ? '0 0 8px #38bdf8' : 'none' }} />
            ))}
          </div>

          {/* Keypad */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, width: '100%' }}>
            {['1','2','3','4','5','6','7','8','9','⌫','0','↵'].map(k => (
              <button key={k} onClick={() => {
                if (k === '⌫') setPin(p => p.slice(0, -1))
                else if (k === '↵') submit()
                else if (pin.length < 4) setPin(p => p + k)
              }} style={{
                height: 52, borderRadius: 10, fontSize: k.length > 1 ? 16 : 18, fontWeight: 600,
                background: k === '↵' ? 'linear-gradient(135deg, #0ea5e9, #1d4ed8)' : '#111c30',
                color: k === '↵' ? '#fff' : '#94a3b8',
                border: '1px solid #1e3a5f',
                cursor: 'pointer', transition: 'all 0.1s',
                boxShadow: k === '↵' ? '0 0 16px rgba(14,165,233,0.3)' : 'none',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = k === '↵' ? 'linear-gradient(135deg, #38bdf8, #3b82f6)' : '#1a2840'; e.currentTarget.style.color = '#e2e8f0' }}
              onMouseLeave={e => { e.currentTarget.style.background = k === '↵' ? 'linear-gradient(135deg, #0ea5e9, #1d4ed8)' : '#111c30'; e.currentTarget.style.color = k === '↵' ? '#fff' : '#94a3b8' }}
              >{k}</button>
            ))}
          </div>

          {attempts > 0 && (
            <div style={{ fontSize: 11.5, color: '#f87171', display: 'flex', alignItems: 'center', gap: 6 }}>
              <i className="ti ti-alert-triangle" style={{ fontSize: 13 }} />
              Invalid PIN — {attempts} failed attempt{attempts > 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── SQL Console ───────────────────────────────────────────────────────────────
function SqlConsole() {
  const [sql, setSql] = useState('SELECT name, email, location FROM recruiters LIMIT 10')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = async () => {
    setLoading(true); setError(null); setResult(null)
    try {
      const res = await adminAxios.post('/admin/sql', { sql })
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Query failed.')
    }
    setLoading(false)
  }

  const PRESET_QUERIES = [
    { label: 'Recruiters by state', sql: "SELECT TRIM(SPLIT_PART(location,',',-1)) AS state, COUNT(*) AS n FROM recruiters WHERE location IS NOT NULL GROUP BY state ORDER BY n DESC LIMIT 20" },
    { label: 'Top companies', sql: "SELECT c.company_name, COUNT(r.recruiter_id) AS recruiters FROM companies c LEFT JOIN recruiters r ON r.company_id=c.company_id GROUP BY c.company_name ORDER BY recruiters DESC LIMIT 20" },
    { label: 'Missing emails', sql: "SELECT name, phone, location FROM recruiters WHERE email IS NULL OR email='' ORDER BY created_at DESC LIMIT 50" },
    { label: 'Recent additions', sql: "SELECT name, email, location, created_at FROM recruiters ORDER BY created_at DESC LIMIT 25" },
    { label: 'Duplicate emails', sql: "SELECT LOWER(TRIM(email)) AS email, COUNT(*) AS n FROM recruiters WHERE email IS NOT NULL GROUP BY LOWER(TRIM(email)) HAVING COUNT(*)>1 ORDER BY n DESC LIMIT 30" },
  ]

  return (
    <Section title="SQL Read Console" icon="ti-code" action={
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Badge color="#22c55e">READ-ONLY</Badge>
        <Badge color="#f59e0b">SELECT only</Badge>
      </div>
    }>
      {/* Presets */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        {PRESET_QUERIES.map(q => (
          <button key={q.label} onClick={() => setSql(q.sql)} style={{
            background: '#111c30', border: '1px solid #1e3a5f', color: '#94a3b8',
            padding: '5px 12px', borderRadius: 6, fontSize: 11.5, cursor: 'pointer',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = '#38bdf8'; e.currentTarget.style.color = '#38bdf8' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = '#1e3a5f'; e.currentTarget.style.color = '#94a3b8' }}
          >{q.label}</button>
        ))}
      </div>

      {/* Editor */}
      <textarea
        value={sql}
        onChange={e => setSql(e.target.value)}
        rows={5}
        style={{
          width: '100%', fontFamily: "'DM Mono', monospace", fontSize: 12.5,
          background: '#060e1a', border: '1px solid #1e3a5f', color: '#a5f3fc',
          borderRadius: 10, padding: 16, resize: 'vertical', outline: 'none',
          lineHeight: 1.7,
        }}
      />

      <div style={{ display: 'flex', gap: 10, marginTop: 10, alignItems: 'center' }}>
        <button onClick={run} disabled={loading} style={{
          background: loading ? '#1e3a5f' : 'linear-gradient(135deg, #0ea5e9, #1d4ed8)',
          color: '#fff', padding: '9px 22px', borderRadius: 8, fontSize: 13, fontWeight: 600,
          border: 'none', cursor: loading ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          {loading ? <i className="ti ti-loader" style={{ animation: 'spin 0.8s linear infinite' }} /> : <i className="ti ti-player-play" />}
          {loading ? 'Running...' : 'Run Query'}
        </button>
        {result && <span style={{ fontSize: 11.5, color: '#64748b' }}>✓ {result.total} row{result.total !== 1 ? 's' : ''} in {result.query_ms}ms</span>}
      </div>

      {error && (
        <div style={{ marginTop: 12, background: '#300', border: '1px solid #7f1d1d', color: '#f87171', padding: '10px 14px', borderRadius: 8, fontSize: 12, fontFamily: "'DM Mono', monospace" }}>
          ✗ {error}
        </div>
      )}

      {result && result.rows.length > 0 && (
        <div style={{ marginTop: 14, overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: "'DM Mono', monospace" }}>
            <thead>
              <tr style={{ background: '#111c30' }}>
                {result.columns.map(c => (
                  <th key={c} style={{ padding: '8px 14px', textAlign: 'left', color: '#38bdf8', fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase', borderBottom: '1px solid #1e3a5f', whiteSpace: 'nowrap' }}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #0e1e30' }}
                  onMouseEnter={e => e.currentTarget.style.background = '#111c30'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  {result.columns.map(c => (
                    <td key={c} style={{ padding: '7px 14px', color: '#94a3b8', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {String(row[c] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {result.total > 200 && <div style={{ fontSize: 11, color: '#475569', marginTop: 8 }}>Showing first 200 of {fmt(result.total)} rows</div>}
        </div>
      )}
    </Section>
  )
}

// ── Main Terminal ─────────────────────────────────────────────────────────────
export default function AdminTerminal() {
  const [unlocked, setUnlocked] = useState(() => sessionStorage.getItem('admin_unlocked') === 'yes')
  const [stats, setStats] = useState(null)
  const [topStates, setTopStates] = useState([])
  const [recentImports, setRecentImports] = useState([])
  const [dupes, setDupes] = useState(null)
  const [fieldAudit, setFieldAudit] = useState(null)
  const [tableSizes, setTableSizes] = useState([])
  const [sysInfo, setSysInfo] = useState(null)
  const [orphans, setOrphans] = useState(null)
  const [cacheMsg, setCacheMsg] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [logLines, setLogLines] = useState([])
  const logRef = useRef()

  const log = (msg, type = 'info') => {
    const ts = new Date().toLocaleTimeString('en-US', { hour12: false })
    setLogLines(prev => [...prev.slice(-80), { ts, msg, type }])
  }

  const unlock = () => {
    sessionStorage.setItem('admin_unlocked', 'yes')
    setUnlocked(true)
  }

  const loadAll = useCallback(async () => {
    if (!unlocked) return
    setLoading(true)
    log('Connecting to TalentOps AI backend…')
    try {
      const [s, ts, ri, fa, tbl, sys, orp] = await Promise.all([
        adminAxios.get('/admin/stats'),
        adminAxios.get('/admin/top-states'),
        adminAxios.get('/admin/recent-imports'),
        adminAxios.get('/admin/field-audit'),
        adminAxios.get('/admin/table-sizes'),
        adminAxios.get('/admin/system-info'),
        adminAxios.get('/admin/orphan-companies'),
      ])
      setStats(s.data); setTopStates(ts.data); setRecentImports(ri.data)
      setFieldAudit(fa.data); setTableSizes(tbl.data); setSysInfo(sys.data); setOrphans(orp.data)
      log(`✓ Stats loaded: ${s.data.total_recruiters?.toLocaleString()} recruiters, ${s.data.total_companies?.toLocaleString()} companies`, 'ok')
      log(`✓ DB size: ${sys.data.database_size} · Uptime: ${sys.data.uptime}`, 'ok')
    } catch (e) {
      log('✗ Failed to load admin data: ' + (e.message || 'unknown error'), 'error')
    }
    setLoading(false)
  }, [unlocked])

  useEffect(() => { loadAll() }, [loadAll])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logLines])

  const loadDupes = async () => {
    log('Scanning for duplicate emails…')
    try {
      const res = await adminAxios.get('/admin/duplicates')
      setDupes(res.data)
      log(`✓ Found ${res.data.total_duplicate_groups} duplicate email groups`, res.data.total_duplicate_groups > 0 ? 'warn' : 'ok')
    } catch { log('✗ Failed to load duplicates', 'error') }
  }

  const clearCache = async () => {
    try {
      await adminAxios.post('/admin/clear-cache')
      setCacheMsg('✓ Analytics cache cleared!'); setTimeout(() => setCacheMsg(null), 3000)
      log('✓ Analytics cache cleared', 'ok')
    } catch { log('✗ Failed to clear cache', 'error') }
  }

  if (!unlocked) return <AdminLock onUnlock={unlock} />

  const TABS = [
    { id: 'overview',  icon: 'ti-layout-dashboard', label: 'Overview' },
    { id: 'data',      icon: 'ti-database',          label: 'Data Health' },
    { id: 'sql',       icon: 'ti-code',              label: 'SQL Console' },
    { id: 'system',    icon: 'ti-server',            label: 'System' },
    { id: 'logs',      icon: 'ti-terminal',          label: 'Activity Log' },
  ]

  const baseStyle = {
    minHeight: '100vh', background: '#020917', fontFamily: "'DM Sans', sans-serif",
    color: '#e2e8f0',
  }

  return (
    <div style={baseStyle} className="page-enter">
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {/* Header */}
      <div style={{ background: '#0b1525', borderBottom: '1px solid #1e2d45', padding: '14px 28px', display: 'flex', alignItems: 'center', gap: 14, position: 'sticky', top: 0, zIndex: 50 }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #0ea5e9, #1d4ed8)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 16px rgba(14,165,233,0.4)' }}>
          <i className="ti ti-terminal-2" style={{ color: '#fff', fontSize: 18 }} />
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.01em' }}>ADMIN TERMINAL</div>
          <div style={{ fontSize: 11, color: '#38bdf8', fontFamily: "'DM Mono', monospace" }}>TalentOps AI · Privileged Access</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 10, alignItems: 'center' }}>
          {loading && <span style={{ fontSize: 12, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}><i className="ti ti-loader" style={{ animation: 'spin 0.8s linear infinite' }} /> Loading…</span>}
          <button onClick={loadAll} style={{ background: '#0d1829', border: '1px solid #1e3a5f', color: '#94a3b8', padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <i className="ti ti-refresh" /> Refresh
          </button>
          <button onClick={clearCache} style={{ background: '#0d1829', border: '1px solid #1e3a5f', color: '#f59e0b', padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <i className="ti ti-trash" /> Clear Cache
          </button>
          {cacheMsg && <span style={{ fontSize: 12, color: '#22c55e' }}>{cacheMsg}</span>}
          <button onClick={() => { sessionStorage.removeItem('admin_unlocked'); setUnlocked(false) }} style={{ background: '#300', border: '1px solid #7f1d1d', color: '#f87171', padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <i className="ti ti-lock" /> Lock
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 2, padding: '0 28px', background: '#0b1525', borderBottom: '1px solid #1e2d45' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            background: 'none', border: 'none', padding: '12px 18px', fontSize: 12.5, fontWeight: 500,
            color: activeTab === t.id ? '#38bdf8' : '#475569', cursor: 'pointer',
            borderBottom: activeTab === t.id ? '2px solid #38bdf8' : '2px solid transparent',
            display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.15s',
          }}
          onMouseEnter={e => { if (activeTab !== t.id) e.currentTarget.style.color = '#94a3b8' }}
          onMouseLeave={e => { if (activeTab !== t.id) e.currentTarget.style.color = '#475569' }}
          >
            <i className={`ti ${t.icon}`} style={{ fontSize: 14 }} />{t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: '28px 28px', maxWidth: 1300, margin: '0 auto' }}>

        {/* ── OVERVIEW TAB ── */}
        {activeTab === 'overview' && stats && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            {/* KPI Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14, marginBottom: 24 }}>
              <StatCard icon="ti-users" label="Total Recruiters" value={fmt(stats.total_recruiters)} sub={`${fmt(stats.active_recruiters)} active`} color="#38bdf8" glow />
              <StatCard icon="ti-building" label="Companies" value={fmt(stats.total_companies)} color="#a78bfa" />
              <StatCard icon="ti-user-check" label="Candidates" value={fmt(stats.total_candidates)} color="#34d399" />
              <StatCard icon="ti-briefcase" label="Submissions" value={fmt(stats.total_submissions)} color="#fb923c" />
              <StatCard icon="ti-mail" label="With Email" value={fmt(stats.with_email)} sub={`${pct(stats.with_email, stats.total_recruiters)}% coverage`} color="#f472b6" />
              <StatCard icon="ti-phone" label="With Phone" value={fmt(stats.with_phone)} sub={`${pct(stats.with_phone, stats.total_recruiters)}% coverage`} color="#fbbf24" />
              <StatCard icon="ti-map-pin" label="Unique Locations" value={fmt(stats.unique_locations)} color="#60a5fa" />
              <StatCard icon="ti-calendar-plus" label="Added Today" value={fmt(stats.added_today)} sub={`${fmt(stats.added_week)} this week`} color="#22c55e" glow={stats.added_today > 0} />
            </div>

            {/* Top States + Recent Imports */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <Section title="Top States by Recruiter Count" icon="ti-map-2">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {topStates.map((s, i) => {
                    const max = topStates[0]?.count || 1
                    const w = Math.round(s.count / max * 100)
                    return (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 11, color: '#475569', minWidth: 18, textAlign: 'right' }}>{i+1}</span>
                        <span style={{ fontSize: 12, color: '#94a3b8', minWidth: 100, fontFamily: "'DM Mono', monospace" }}>{s.state || '(blank)'}</span>
                        <div style={{ flex: 1, height: 6, background: '#111c30', borderRadius: 99, overflow: 'hidden' }}>
                          <div style={{ width: `${w}%`, height: '100%', background: 'linear-gradient(90deg, #0ea5e9, #38bdf8)', borderRadius: 99, transition: 'width 0.6s ease' }} />
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#38bdf8', minWidth: 50, textAlign: 'right', fontFamily: "'DM Mono', monospace" }}>{fmt(s.count)}</span>
                      </div>
                    )
                  })}
                </div>
              </Section>

              <Section title="Recent Import Activity" icon="ti-calendar">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {recentImports.map((r, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: '#0b1525', borderRadius: 8, fontSize: 12 }}>
                      <span style={{ color: '#64748b', fontFamily: "'DM Mono', monospace" }}>{r.import_date}</span>
                      <span style={{ fontWeight: 600, color: '#38bdf8' }}>+{fmt(r.count)} records</span>
                    </div>
                  ))}
                  {recentImports.length === 0 && <span style={{ color: '#475569', fontSize: 12 }}>No import history found.</span>}
                </div>
              </Section>
            </div>
          </div>
        )}

        {/* ── DATA HEALTH TAB ── */}
        {activeTab === 'data' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            {/* Field Audit */}
            {fieldAudit && (
              <Section title="Field Coverage Audit" icon="ti-clipboard-check">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                  {Object.entries(fieldAudit.fields || {}).map(([field, info]) => {
                    const filled = fieldAudit.total - info.missing
                    const coverage = 100 - info.pct
                    const color = coverage > 80 ? '#22c55e' : coverage > 50 ? '#f59e0b' : '#ef4444'
                    return (
                      <div key={field} style={{ background: '#0b1525', border: '1px solid #1e2d45', borderRadius: 10, padding: 16 }}>
                        <div style={{ fontSize: 10.5, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{field.replace('missing_', '')}</div>
                        <div style={{ fontSize: 22, fontWeight: 700, color, marginBottom: 4, fontFamily: "'DM Mono', monospace" }}>{coverage}%</div>
                        <div style={{ height: 4, background: '#1e2d45', borderRadius: 99, overflow: 'hidden', marginBottom: 8 }}>
                          <div style={{ width: `${coverage}%`, height: '100%', background: color, borderRadius: 99, transition: 'width 0.6s' }} />
                        </div>
                        <div style={{ fontSize: 11, color: '#475569' }}>{fmt(filled)} / {fmt(fieldAudit.total)} filled</div>
                      </div>
                    )
                  })}
                </div>
              </Section>
            )}

            {/* Duplicates */}
            <Section title="Duplicate Email Detection" icon="ti-copy" action={
              <button onClick={loadDupes} style={{ background: '#111c30', border: '1px solid #1e3a5f', color: '#38bdf8', padding: '6px 14px', borderRadius: 7, fontSize: 12, cursor: 'pointer' }}>
                <i className="ti ti-search" /> Scan Duplicates
              </button>
            }>
              {!dupes && <span style={{ fontSize: 12.5, color: '#475569' }}>Click "Scan Duplicates" to detect emails appearing more than once in the database.</span>}
              {dupes && (
                <>
                  <div style={{ marginBottom: 14, display: 'flex', gap: 14 }}>
                    <div style={{ background: '#0b1525', borderRadius: 10, padding: '12px 20px', textAlign: 'center' }}>
                      <div style={{ fontSize: 28, fontWeight: 700, color: dupes.total_duplicate_groups > 0 ? '#f87171' : '#22c55e', fontFamily: "'DM Mono', monospace" }}>{dupes.total_duplicate_groups}</div>
                      <div style={{ fontSize: 11, color: '#64748b' }}>duplicate groups</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' }}>
                    {dupes.duplicates.slice(0, 30).map((d, i) => (
                      <div key={i} style={{ background: '#0b1525', border: '1px solid #2d1a1a', borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                        <span style={{ background: '#f8717122', color: '#f87171', fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 99, whiteSpace: 'nowrap' }}>×{d.count}</span>
                        <div>
                          <div style={{ fontSize: 12, color: '#94a3b8', fontFamily: "'DM Mono', monospace", marginBottom: 4 }}>{d.email}</div>
                          <div style={{ fontSize: 11, color: '#475569' }}>{d.names.join(' · ')}</div>
                        </div>
                      </div>
                    ))}
                    {dupes.duplicates.length === 0 && <span style={{ fontSize: 12.5, color: '#22c55e' }}>✓ No duplicate emails found. Database is clean!</span>}
                  </div>
                </>
              )}
            </Section>

            {/* Orphan Companies */}
            {orphans && (
              <Section title={`Companies with No Recruiters (${fmt(orphans.count)} found)`} icon="ti-building-off">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 300, overflowY: 'auto' }}>
                  {orphans.companies.slice(0, 30).map((c, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 12px', background: '#0b1525', borderRadius: 8, fontSize: 12 }}>
                      <span style={{ color: '#94a3b8' }}>{c.company_name}</span>
                      <span style={{ color: '#475569' }}>{c.location || '—'}</span>
                    </div>
                  ))}
                  {orphans.count === 0 && <span style={{ color: '#22c55e', fontSize: 12.5 }}>✓ All companies have linked recruiters.</span>}
                </div>
              </Section>
            )}
          </div>
        )}

        {/* ── SQL TAB ── */}
        {activeTab === 'sql' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            <SqlConsole />
          </div>
        )}

        {/* ── SYSTEM TAB ── */}
        {activeTab === 'system' && sysInfo && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14, marginBottom: 24 }}>
              <StatCard icon="ti-database" label="Database Size" value={sysInfo.database_size} color="#a78bfa" glow />
              <StatCard icon="ti-clock" label="PG Uptime" value={sysInfo.uptime} color="#34d399" />
              <StatCard icon="ti-users-group" label="Connections" value={sysInfo.active_connections} color="#fb923c" />
              <StatCard icon="ti-alert-triangle" label="Slow Queries" value={sysInfo.slow_queries} color={sysInfo.slow_queries > 0 ? '#ef4444' : '#22c55e'} glow={sysInfo.slow_queries > 0} />
            </div>

            <Section title="PostgreSQL Version" icon="ti-server">
              <pre style={{ fontFamily: "'DM Mono', monospace", fontSize: 12, color: '#64748b', whiteSpace: 'pre-wrap', margin: 0 }}>{sysInfo.postgres_version}</pre>
            </Section>

            <Section title="Table Storage Sizes" icon="ti-table">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {tableSizes.map((t, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 14px', background: '#0b1525', borderRadius: 8 }}>
                    <span style={{ fontSize: 12, color: '#38bdf8', minWidth: 160, fontFamily: "'DM Mono', monospace" }}>{t.table_name}</span>
                    <span style={{ fontSize: 12, color: '#94a3b8', minWidth: 80 }}>{t.total_size}</span>
                    <span style={{ fontSize: 11.5, color: '#475569' }}>{fmt(t.live_rows)} rows</span>
                    <div style={{ flex: 1, height: 4, background: '#1e2d45', borderRadius: 99, overflow: 'hidden' }}>
                      <div style={{ width: `${Math.round(t.size_bytes / (tableSizes[0]?.size_bytes || 1) * 100)}%`, height: '100%', background: 'linear-gradient(90deg, #1d4ed8, #38bdf8)', borderRadius: 99 }} />
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          </div>
        )}

        {/* ── ACTIVITY LOG TAB ── */}
        {activeTab === 'logs' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            <Section title="Activity Log" icon="ti-terminal">
              <div ref={logRef} style={{
                background: '#060e1a', borderRadius: 10, padding: 16, height: 420, overflowY: 'auto',
                fontFamily: "'DM Mono', monospace", fontSize: 12.5, lineHeight: 1.9,
              }}>
                {logLines.length === 0 && <span style={{ color: '#1e3a5f' }}>— No activity yet —</span>}
                {logLines.map((l, i) => (
                  <div key={i} style={{ color: l.type === 'error' ? '#f87171' : l.type === 'warn' ? '#fbbf24' : l.type === 'ok' ? '#4ade80' : '#64748b' }}>
                    <span style={{ color: '#1e3a5f', userSelect: 'none' }}>[{l.ts}] </span>{l.msg}
                  </div>
                ))}
                <span style={{ color: '#1e3a5f', animation: 'blink 1.2s step-end infinite' }}>▌</span>
              </div>
            </Section>
          </div>
        )}
      </div>
    </div>
  )
}
