import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import { API, getErrorMessage } from '../services/api'
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
      background: 'var(--card-bg)', border: `1px solid ${glow ? color : 'var(--card-border)'}`,
      borderRadius: 12, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 8,
      boxShadow: glow ? `0 0 20px ${color}33` : 'var(--shadow)',
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 34, height: 34, borderRadius: 8, background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className={`ti ${icon}`} style={{ color, fontSize: 18 }} />
        </div>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600 }}>{label}</span>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub && <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  )
}

function Section({ title, icon, children, action, style }) {
  return (
    <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 14, overflow: 'hidden', marginBottom: 20, boxShadow: 'var(--shadow)', ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid var(--card-border)', background: 'var(--panel-bg)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <i className={`ti ${icon}`} style={{ color: 'var(--accent)', fontSize: 17 }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>{title}</span>
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
  const pinRef = useRef(pin)
  pinRef.current = pin

  const submit = useCallback(() => {
    if (pinRef.current === ADMIN_PIN) { onUnlock(); return }
    setShake(true)
    setAttempts(a => a + 1)
    setPin('')
    setTimeout(() => setShake(false), 600)
  }, [onUnlock])

  const pressKey = useCallback((k) => {
    if (k === '⌫') setPin(p => p.slice(0, -1))
    else if (k === '↵') submit()
    else setPin(p => (p.length < 4 ? p + k : p))
  }, [submit])

  useEffect(() => {
    const onKeyDown = (e) => {
      if (/^[0-9]$/.test(e.key)) {
        e.preventDefault()
        pressKey(e.key)
        return
      }
      if (e.key === 'Backspace' || e.key === 'Delete') {
        e.preventDefault()
        pressKey('⌫')
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        submit()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [pressKey, submit])

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
          background: 'var(--card-bg)', border: '1px solid var(--card-border)',
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
              <button key={k} type="button" onClick={() => pressKey(k)} style={{
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
            background: 'var(--card-bg)', border: '1px solid var(--card-border)', color: 'var(--text-secondary)',
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
              <tr style={{ background: 'var(--panel-bg)' }}>
                {result.columns.map(c => (
                  <th key={c} style={{ padding: '8px 14px', textAlign: 'left', color: '#38bdf8', fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase', borderBottom: '1px solid var(--card-border)', whiteSpace: 'nowrap' }}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--card-border)' }}
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

// ── Session Row Component ──────────────────────────────────────────────────────
function SessionRow({ session, isOpen, onToggle, index }) {
  const mins = Math.floor(session.total_seconds / 60)
  const secs = session.total_seconds % 60
  const duration = session.total_seconds > 0
    ? (mins > 0 ? `${mins}m ${secs}s` : `${secs}s`)
    : `${session.page_count} pages`
  const browserIcon = session.browser === 'Chrome' ? 'ti-brand-chrome'
    : session.browser === 'Firefox' ? 'ti-brand-firefox'
    : session.browser === 'Edge' ? 'ti-brand-edge'
    : session.browser === 'Safari' ? 'ti-brand-safari'
    : 'ti-browser'

  return (
    <div style={{ flexShrink: 0, background: 'var(--panel-bg)', border: `1px solid ${isOpen ? 'var(--card-border)' : 'var(--card-border)'}`, borderRadius: 10, overflow: 'hidden' }}>
      <div
        onClick={onToggle}
        style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
      >
        <div style={{ width: 28, height: 28, borderRadius: 7, background: 'var(--card-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <i className={`ti ${browserIcon}`} style={{ fontSize: 14, color: '#38bdf8' }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: session.user_email === 'Anonymous' ? '#94a3b8' : '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {session.user_email}
          </div>
          <div style={{ fontSize: 10.5, color: '#64748b', marginTop: 2 }}>
            {String(session.session_start).slice(0, 16).replace('T', ' ')} · {session.browser}
          </div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#38bdf8', fontFamily: "'DM Mono', monospace" }}>{duration}</div>
          <div style={{ fontSize: 10, color: '#64748b' }}>{session.page_count} pg</div>
        </div>
        <i className={`ti ${isOpen ? 'ti-chevron-up' : 'ti-chevron-down'}`} style={{ color: '#64748b', fontSize: 12 }} />
      </div>
      {isOpen && (
        <div style={{ borderTop: '1px solid #111c30', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 5 }}>
          <div style={{ fontSize: 10, color: '#475569', fontFamily: "'DM Mono', monospace" }}>{session.ip_address}</div>
          {session.pages.map((p, pi) => (
            <div key={pi} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#94a3b8' }}>
              <span style={{ color: '#475569', minWidth: 16 }}>{pi + 1}.</span>
              <span style={{ flex: 1 }}>{p}</span>
              <span style={{ color: '#64748b', fontFamily: "'DM Mono', monospace" }}>{String(session.timestamps[pi] || '').slice(11, 19)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main Terminal ─────────────────────────────────────────────────────────────
export default function AdminTerminal() {
  const [unlocked, setUnlocked] = useState(() => sessionStorage.getItem('admin_unlocked') === 'yes')
  const [stats, setStats] = useState(null)
  const [opsKpis, setOpsKpis] = useState(null)
  const [topStates, setTopStates] = useState([])
  const [recentImports, setRecentImports] = useState([])
  const [dupes, setDupes] = useState(null)
  const [dataOps, setDataOps] = useState(null)
  const [uploadOps, setUploadOps] = useState(null)
  const [features, setFeatures] = useState([])
  const [searchIntel, setSearchIntel] = useState(null)
  const [exportIntel, setExportIntel] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [activityFeed, setActivityFeed] = useState(null)
  const [stateCoverage, setStateCoverage] = useState(null)
  const [fieldAudit, setFieldAudit] = useState(null)
  const [tableSizes, setTableSizes] = useState([])
  const [sysInfo, setSysInfo] = useState(null)
  const [orphans, setOrphans] = useState(null)
  const [cacheMsg, setCacheMsg] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [logLines, setLogLines] = useState([])
  const logRef = useRef()
  const [visitorLogs, setVisitorLogs] = useState(null)
  const [visitorSummary, setVisitorSummary] = useState(null)
  const [logDays, setLogDays] = useState(7)
  const [expandedSession, setExpandedSession] = useState(null)
  const [loadingLogs, setLoadingLogs] = useState(false)
  const [logsError, setLogsError] = useState(null)

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
    
    const safeGet = async (url) => {
      try { const res = await adminAxios.get(url); return res.data; }
      catch (e) { log(`✗ Failed to load ${url}`, 'warn'); return null; }
    }

    const [s, ok, ts, ri, fa, tbl, sys, orp, dq, dop, uop, si, ei, al, feed, cov] = await Promise.all([
      safeGet('/admin/stats'),
      safeGet('/admin/ops-kpis'),
      safeGet('/admin/top-states'),
      safeGet('/admin/recent-imports'),
      safeGet('/admin/field-audit'),
      safeGet('/admin/table-sizes'),
      safeGet('/admin/system-info'),
      safeGet('/admin/orphan-companies'),
      safeGet('/admin/data-quality'),
      safeGet('/admin/data-operations'),
      safeGet('/admin/upload-operations'),
      safeGet('/admin/search-activity'),
      safeGet('/admin/export-analytics'),
      safeGet('/admin/alerts'),
      safeGet('/admin/activity-feed'),
      safeGet('/admin/state-coverage'),
    ])

    if (s) setStats(s); if (ok) setOpsKpis(ok); if (ts) setTopStates(ts || []); if (ri) setRecentImports(ri || [])
    if (fa) setFieldAudit(fa); if (tbl) setTableSizes(tbl || []); if (sys) setSysInfo(sys); if (orp) setOrphans(orp); if (dq) setDataQuality(dq)
    if (dop) setDataOps(dop); if (uop) setUploadOps(uop); if (si) setSearchIntel(si); if (ei) setExportIntel(ei)
    if (al) setAlerts(al.alerts || []); if (feed) setActivityFeed(feed); if (cov) setStateCoverage(cov)
    
    if (s && sys) {
      log(`✓ Stats loaded: ${s.total_recruiters?.toLocaleString()} recruiters, ${s.total_companies?.toLocaleString()} companies`, 'ok')
      log(`✓ DB size: ${sys.database_size} · Uptime: ${sys.uptime}`, 'ok')
    }
    
    setLoading(false)
  }, [unlocked])

  useEffect(() => { loadAll() }, [loadAll])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logLines])



  const verifyFeature = async (featureId, status) => {
    try {
      await adminAxios.post(`/updates/verify/${featureId}`, { status });
      log(`✓ Feature ${featureId} marked as ${status}`, 'ok');
      const res = await adminAxios.get('/updates/features');
      setFeatures(res.data);
    } catch(e) {
      log(`✗ Failed to update feature: ` + getErrorMessage(e), 'error');
    }
  }

  const runCleanup = async () => {
    if (!window.confirm('This will permanently delete recruiters missing both email and phone. Continue?')) return;
    setLoading(true);
    try {
      const res = await adminAxios.post('/admin/cleanup');
      log(`✓ Cleanup complete: ${res.data.deleted_count} records removed.`, 'ok');
      loadAll();
    } catch (e) {
      log('✗ Cleanup failed: ' + getErrorMessage(e), 'error');
    }
    setLoading(false);
  }

  const exportProblems = () => {
    if (!dataOps) return;
    const all = [...(dataOps.samples?.missing_emails || []), ...(dataOps.samples?.unmapped_states || [])];
    exportToExcel(all, 'problem_records');
  }

  const loadDupes = async () => {
    log('Scanning for duplicate emails…')
    try {
      const res = await adminAxios.get('/admin/duplicates')
      setDupes(res.data)
      log(`✓ Found ${res.data.total_duplicate_groups} duplicate email groups`, res.data.total_duplicate_groups > 0 ? 'warn' : 'ok')
    } catch { log('✗ Failed to load duplicates', 'error') }
  }

  const retryImport = async (jobId) => {
    if (!jobId) return
    log(`Retrying import job ${jobId}...`)
    try {
      await adminAxios.post(`/upload/jobs/${jobId}/retry`)
      log('✓ Retry triggered', 'ok')
      await loadAll()
    } catch (e) {
      log('✗ Retry failed: ' + getErrorMessage(e, e.message || 'unknown error'), 'error')
    }
  }

  const clearCache = async () => {
    try {
      await adminAxios.post('/admin/clear-cache')
      setCacheMsg('✓ Analytics cache cleared!'); setTimeout(() => setCacheMsg(null), 3000)
      log('✓ Analytics cache cleared', 'ok')
    } catch { log('✗ Failed to clear cache', 'error') }
  }

  const loadVisitorLogs = async (days = logDays) => {
    setLoadingLogs(true)
    setLogsError(null)
    log(`Loading visitor logs for last ${days} days…`)
    try {
      const [logsRes, summRes] = await Promise.all([
        adminAxios.get(`/admin/visitor-logs?days=${days}&limit=300`),
        adminAxios.get(`/admin/visitor-summary?days=${days}`),
      ])
      setVisitorLogs(logsRes.data)
      setVisitorSummary(summRes.data)
      const n = logsRes.data.total
      const v = logsRes.data.total_visits ?? 0
      log(`✓ Loaded ${n} session(s) from ${v} page visit(s)`, 'ok')
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'unknown error'
      setLogsError(msg)
      setVisitorLogs(null)
      setVisitorSummary(null)
      log('✗ Failed to load visitor logs: ' + msg, 'error')
    }
    setLoadingLogs(false)
  }

  useEffect(() => {
    if (unlocked && activeTab === 'logbook') {
      loadVisitorLogs(logDays)
    }
  }, [unlocked, activeTab])

  if (!unlocked) return <AdminLock onUnlock={unlock} />

  const TABS = [
    { id: 'overview', icon: 'ti-layout-dashboard', label: 'Overview' },
    { id: 'ops', icon: 'ti-database', label: 'Data Operations' },
    { id: 'uploads', icon: 'ti-cloud-upload', label: 'Upload Ops' },
    { id: 'intel', icon: 'ti-sparkles', label: 'Search Intelligence' },
    { id: 'exports', icon: 'ti-file-export', label: 'Export Analytics' },
    { id: 'system', icon: 'ti-server', label: 'System Health' },
    { id: 'logbook', icon: 'ti-book', label: 'Visitor Log Book' },
    { id: 'sql', icon: 'ti-code', label: 'SQL Console' },
    { id: 'logs', icon: 'ti-terminal', label: 'Activity Log' },
  ]

  const baseStyle = {
    height: '100%',
    minHeight: 0,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    background: 'var(--main-bg)',
    fontFamily: "'DM Sans', sans-serif",
    color: 'var(--text-primary)',
  }

  return (
    <div style={baseStyle}>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      {/* Header */}
      <div style={{ background: 'var(--panel-bg)', borderBottom: '1px solid var(--card-border)', padding: '14px 28px', display: 'flex', alignItems: 'center', gap: 14, position: 'sticky', top: 0, zIndex: 50 }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #0ea5e9, #1d4ed8)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 16px rgba(14,165,233,0.4)' }}>
          <i className="ti ti-terminal-2" style={{ color: '#fff', fontSize: 18 }} />
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>ADMIN TERMINAL</div>
          <div style={{ fontSize: 11, color: '#38bdf8', fontFamily: "'DM Mono', monospace" }}>TalentOps AI · Privileged Access</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 10, alignItems: 'center' }}>
          {loading && <span style={{ fontSize: 12, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}><i className="ti ti-loader" style={{ animation: 'spin 0.8s linear infinite' }} /> Loading…</span>}
          <button onClick={loadAll} style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', color: 'var(--text-secondary)', padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <i className="ti ti-refresh" /> Refresh
          </button>
          <button onClick={clearCache} style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', color: '#f59e0b', padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <i className="ti ti-trash" /> Clear Cache
          </button>
          {cacheMsg && <span style={{ fontSize: 12, color: '#22c55e' }}>{cacheMsg}</span>}
          <button onClick={() => { sessionStorage.removeItem('admin_unlocked'); setUnlocked(false) }} style={{ background: '#300', border: '1px solid #7f1d1d', color: '#f87171', padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <i className="ti ti-lock" /> Lock
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 2, padding: '0 28px', background: 'var(--panel-bg)', borderBottom: '1px solid var(--card-border)' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            background: 'none', border: 'none', padding: '12px 18px', fontSize: 12.5, fontWeight: 500,
            color: activeTab === t.id ? '#38bdf8' : 'var(--text-muted)', cursor: 'pointer',
            borderBottom: activeTab === t.id ? '2px solid #38bdf8' : '2px solid transparent',
            display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.15s',
          }}
          onMouseEnter={e => { if (activeTab !== t.id) e.currentTarget.style.color = 'var(--text-secondary)' }}
          onMouseLeave={e => { if (activeTab !== t.id) e.currentTarget.style.color = 'var(--text-muted)' }}
          >
            <i className={`ti ${t.icon}`} style={{ fontSize: 14 }} />{t.label}
          </button>
        ))}
      </div>

      {/* Content — scrollable */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '20px 24px 28px', maxWidth: 1300, margin: '0 auto', width: '100%' }}>

        {/* ── OVERVIEW TAB ── */}
        {activeTab === 'overview' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            {/* KPI Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14, marginBottom: 16 }}>
              <StatCard icon="ti-users" label="Total Recruiters" value={opsKpis?.total_recruiters != null ? fmt(opsKpis.total_recruiters) : 'No Data Available'} color="#38bdf8" glow />
              <StatCard icon="ti-building" label="Total Companies" value={opsKpis?.total_companies != null ? fmt(opsKpis.total_companies) : 'No Data Available'} color="#a78bfa" />
              <StatCard icon="ti-map" label="Total States" value={opsKpis?.total_states != null ? fmt(opsKpis.total_states) : 'No Data Available'} color="#34d399" />
              <StatCard icon="ti-search" label="Searches Today" value={opsKpis?.searches_today != null ? fmt(opsKpis.searches_today) : 'No Data Available'} color="#fb923c" />
              <StatCard icon="ti-cloud-upload" label="New Uploads" value={opsKpis?.new_uploads != null ? fmt(opsKpis.new_uploads) : 'No Data Available'} color="#60a5fa" />
              <StatCard icon="ti-database" label="Database Size" value={opsKpis?.database_size != null ? opsKpis.database_size : 'No Data Available'} color="#f472b6" glow />
            </div>

            {stats && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14, marginBottom: 24 }}>
                <StatCard icon="ti-mail" label="With Email" value={fmt(stats.with_email)} sub={`${pct(stats.with_email, stats.total_recruiters)}% coverage`} color="#fbbf24" />
                <StatCard icon="ti-phone" label="With Phone" value={fmt(stats.with_phone)} sub={`${pct(stats.with_phone, stats.total_recruiters)}% coverage`} color="#22c55e" />
                <StatCard icon="ti-map-pin" label="Unique Locations" value={fmt(stats.unique_locations)} color="#a78bfa" />
                <StatCard icon="ti-calendar-plus" label="Added Today" value={fmt(stats.added_today)} sub={`${fmt(stats.added_week)} this week`} color="#38bdf8" glow={stats.added_today > 0} />
              </div>
            )}

            {/* Top States + Recent Imports */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <Section title="Top States by Recruiter Count" icon="ti-map-2">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {topStates.map((s, i) => {
                    const max = topStates[0]?.count || 1
                    const w = Math.round(s.count / max * 100)
                    return (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 18, textAlign: 'right' }}>{i+1}</span>
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 100, fontFamily: "'DM Mono', monospace" }}>{s.state || '(blank)'}</span>
                        <div style={{ flex: 1, height: 6, background: 'var(--bg-hover)', borderRadius: 99, overflow: 'hidden' }}>
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
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: 'var(--panel-bg)', borderRadius: 8, fontSize: 12 }}>
                      <span style={{ color: 'var(--text-muted)', fontFamily: "'DM Mono', monospace" }}>{r.import_date}</span>
                      <span style={{ fontWeight: 600, color: '#38bdf8' }}>+{fmt(r.count)} records</span>
                    </div>
                  ))}
                  {recentImports.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>No import history found.</span>}
                </div>
              </Section>
            </div>

            {/* Operational panels */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20, marginTop: 20 }}>
              <Section
                title="System Alerts"
                icon="ti-alert-triangle"
                action={<Badge color={(alerts?.some(a => a.severity === 'critical') ? '#ef4444' : '#38bdf8')}>{alerts?.some(a => a.severity === 'critical') ? 'CRITICAL' : 'ACTIVE'}</Badge>}
                style={{ marginBottom: 0 }}
              >
                {(!alerts || alerts.length === 0) ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No alerts detected.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {alerts.slice(0, 4).map((a, i) => (
                      <div key={i} style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: 12, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                        <div style={{ width: 34, height: 34, borderRadius: 10, background: a.severity === 'critical' ? 'rgba(239,68,68,0.18)' : 'rgba(245,158,11,0.16)', border: `1px solid ${a.severity === 'critical' ? 'rgba(239,68,68,0.35)' : 'rgba(245,158,11,0.28)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <i className={`ti ${a.severity === 'critical' ? 'ti-alert-triangle' : 'ti-alert-circle'}`} style={{ color: a.severity === 'critical' ? '#f87171' : '#fbbf24' }} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-primary)' }}>{a.title}</div>
                          <div style={{ marginTop: 4, fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{a.detail}</div>
                          {a.action?.tab && (
                            <button
                              onClick={() => setActiveTab(a.action.tab)}
                              style={{ marginTop: 10, background: 'var(--bg-hover)', border: '1px solid var(--card-border)', color: '#38bdf8', padding: '6px 10px', borderRadius: 8, fontSize: 11.5, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                            >
                              <i className="ti ti-arrow-right" /> {a.action.label || 'Open'}
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Section>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                <Section title="Search Intelligence" icon="ti-sparkles" style={{ marginBottom: 0 }}>
                  <div style={{ display: 'grid', gap: 10 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 10, alignItems: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Most Searched States</div>
                      <Badge color="#a78bfa">Last 24h</Badge>
                    </div>
                    {(searchIntel?.most_searched_states?.length ? searchIntel.most_searched_states : []).slice(0, 5).map((r, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: 'var(--panel-bg)', borderRadius: 10, border: '1px solid var(--card-border)' }}>
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: "'DM Mono', monospace" }}>{r.key}</span>
                        <span style={{ fontSize: 12, fontWeight: 700, color: '#a78bfa', fontFamily: "'DM Mono', monospace" }}>{fmt(r.count)}</span>
                      </div>
                    ))}
                    {!(searchIntel?.most_searched_states?.length) && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>}
                  </div>
                </Section>

                <Section title="Activity Feed" icon="ti-activity" style={{ marginBottom: 0 }}>
                  <div style={{ maxHeight: 210, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {(activityFeed?.items || []).slice(0, 10).map((it, i) => (
                      <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '8px 10px', background: 'var(--panel-bg)', borderRadius: 10, border: '1px solid var(--card-border)' }}>
                        <div style={{ width: 28, height: 28, borderRadius: 9, background: 'var(--bg-hover)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <i className={`ti ${it.type === 'upload' ? 'ti-cloud-upload' : it.action_type?.startsWith('EXPORT_') ? 'ti-file-export' : it.action_type?.startsWith('SEARCH_') ? 'ti-search' : 'ti-bolt'}`} style={{ color: '#38bdf8', fontSize: 14 }} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12, fontWeight: 650, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {it.type === 'upload'
                              ? `Import: ${it.filename || it.job_id}`
                              : `${it.action_type || 'ACTION'}`}
                          </div>
                          <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 2, fontFamily: "'DM Mono', monospace" }}>
                            {String(it.ts || '').replace('T', ' ').slice(0, 19)} · {it.status || ''}
                          </div>
                        </div>
                      </div>
                    ))}
                    {!(activityFeed?.items?.length) && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>}
                  </div>
                </Section>
              </div>
            </div>
          </div>
        )}

        {/* ── DATA HEALTH TAB ── */}
        {activeTab === 'ops' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            {dataOps && (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14, marginBottom: 20 }}>
                  <StatCard icon="ti-copy" label="Duplicate Groups" value={fmt(dataOps.counts?.duplicate_email_groups)} sub={`${fmt(dataOps.counts?.duplicate_email_rows)} rows involved`} color="#f87171" glow={(dataOps.counts?.duplicate_email_groups || 0) > 0} />
                  <StatCard icon="ti-mail-off" label="Missing Emails" value={fmt(dataOps.counts?.missing_emails)} color="#fbbf24" glow={(dataOps.counts?.missing_emails || 0) > 0} />
                  <StatCard icon="ti-phone-off" label="Missing Phones" value={fmt(dataOps.counts?.missing_phones)} color="#fb923c" glow={(dataOps.counts?.missing_phones || 0) > 0} />
                  <StatCard icon="ti-map-pin-off" label="Missing Locations" value={fmt(dataOps.counts?.missing_locations)} color="#a78bfa" glow={(dataOps.counts?.missing_locations || 0) > 0} />
                  <StatCard icon="ti-building-off" label="Unknown Companies" value={fmt(dataOps.counts?.unknown_companies)} color="#60a5fa" glow={(dataOps.counts?.unknown_companies || 0) > 0} />
                  <StatCard icon="ti-map-question" label="Unmapped States" value={fmt(dataOps.counts?.unmapped_states)} color="#38bdf8" glow={(dataOps.counts?.unmapped_states || 0) > 0} />
                </div>

                
            <Section title="Feature Verification Center" icon="ti-checkbox" action={<Badge color="#38bdf8">Live Tracking</Badge>}>
              {features.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No features found. DB might be empty.</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-hover)' }}>
                      <th style={{ padding: '10px 12px', textAlign: 'left', color: '#38bdf8', fontSize: 10.5, borderBottom: '1px solid var(--card-border)' }}>Feature Name</th>
                      <th style={{ padding: '10px 12px', textAlign: 'left', color: '#38bdf8', fontSize: 10.5, borderBottom: '1px solid var(--card-border)' }}>Status</th>
                      <th style={{ padding: '10px 12px', textAlign: 'left', color: '#38bdf8', fontSize: 10.5, borderBottom: '1px solid var(--card-border)' }}>Last Tested</th>
                      <th style={{ padding: '10px 12px', textAlign: 'left', color: '#38bdf8', fontSize: 10.5, borderBottom: '1px solid var(--card-border)' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {features.map(f => (
                      <tr key={f.id} style={{ borderBottom: '1px solid var(--card-border)' }}>
                        <td style={{ padding: '10px 12px', color: 'var(--text-primary)' }}>{f.name}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <Badge color={f.status.includes('Verified') ? '#22c55e' : f.status.includes('Failed') ? '#ef4444' : '#fbbf24'}>
                            {f.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{f.last_tested ? new Date(f.last_tested).toLocaleDateString() : 'Never'}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <div style={{ display: 'flex', gap: 6 }}>
                            <button onClick={() => verifyFeature(f.id, 'Verified')} style={{ background: 'var(--card-bg)', border: '1px solid #22c55e', color: '#22c55e', padding: '4px 8px', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}>Verify</button>
                            <button onClick={() => verifyFeature(f.id, 'Failed Verification')} style={{ background: 'var(--card-bg)', border: '1px solid #ef4444', color: '#ef4444', padding: '4px 8px', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}>Fail</button>
                            <button onClick={() => verifyFeature(f.id, 'Pending Verification')} style={{ background: 'var(--card-bg)', border: '1px solid #fbbf24', color: '#fbbf24', padding: '4px 8px', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}>Retest</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Section>

                <Section title="Data Operations" icon="ti-tools" action={
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <Badge color="#38bdf8">DB-driven</Badge>
                    <Badge color="#22c55e">No fake values</Badge>
                  </div>
                }>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>Quick Actions</div>
                      <div style={{ display: 'grid', gap: 10 }}>
                        {[
                          { label: 'Export Problem Records', icon: 'ti-file-export', disabled: false, onClick: exportProblems },
                          { label: 'Run Cleanup', icon: 'ti-broom', disabled: false, onClick: runCleanup },
                          { label: 'Run Duplicate Scan', icon: 'ti-scan', onClick: loadDupes, disabled: false },
                          { label: 'Refresh Analytics', icon: 'ti-refresh', onClick: clearCache, disabled: false },
                        ].map((b) => (
                          <button
                            key={b.label}
                            onClick={b.onClick}
                            disabled={b.disabled}
                            title={b.disabled ? 'Coming soon' : b.label}
                            style={{
                              background: 'var(--bg-hover)',
                              border: '1px solid var(--card-border)',
                              color: b.disabled ? 'var(--text-muted)' : '#38bdf8',
                              padding: '9px 14px',
                              borderRadius: 10,
                              fontSize: 12.5,
                              cursor: b.disabled ? 'not-allowed' : 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              opacity: b.disabled ? 0.65 : 1,
                            }}
                          >
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><i className={`ti ${b.icon}`} /> {b.label}</span>
                            <i className={`ti ${b.disabled ? 'ti-lock' : 'ti-arrow-right'}`} />
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>State Coverage Center</div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflowY: 'auto' }}>
                        {(stateCoverage?.states || []).slice(0, 12).map((r, i) => (
                          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 10 }}>
                            <span style={{ color: 'var(--text-secondary)', fontFamily: "'DM Mono', monospace" }}>{r.state}</span>
                            <span style={{ color: '#38bdf8', fontWeight: 700, fontFamily: "'DM Mono', monospace" }}>{fmt(r.recruiters)} rec</span>
                          </div>
                        ))}
                        {!(stateCoverage?.states?.length) && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>}
                      </div>
                    </div>
                  </div>
                </Section>

                <Section title="Duplicate Resolution Center" icon="ti-git-merge" action={<Badge color="#64748b">Future-ready</Badge>}>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    No Data Available. Duplicate merge suggestions and review queue will appear here when implemented.
                  </div>
                </Section>
              </>
            )}
            {/* Field Audit */}
            {fieldAudit && (
              <Section title="Field Coverage Audit" icon="ti-clipboard-check">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                  {Object.entries(fieldAudit.fields || {}).map(([field, info]) => {
                    const filled = fieldAudit.total - info.missing
                    const coverage = 100 - info.pct
                    const color = coverage > 80 ? '#22c55e' : coverage > 50 ? '#f59e0b' : '#ef4444'
                    return (
                      <div key={field} style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 10, padding: 16 }}>
                        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{field.replace('missing_', '')}</div>
                        <div style={{ fontSize: 22, fontWeight: 700, color, marginBottom: 4, fontFamily: "'DM Mono', monospace" }}>{coverage}%</div>
                        <div style={{ height: 4, background: 'var(--card-border)', borderRadius: 99, overflow: 'hidden', marginBottom: 8 }}>
                          <div style={{ width: `${coverage}%`, height: '100%', background: color, borderRadius: 99, transition: 'width 0.6s' }} />
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{fmt(filled)} / {fmt(fieldAudit.total)} filled</div>
                      </div>
                    )
                  })}
                </div>
              </Section>
            )}

            {/* Duplicates */}
            <Section title="Duplicate Email Detection" icon="ti-copy" action={
              <button onClick={loadDupes} style={{ background: 'var(--bg-hover)', border: '1px solid var(--card-border)', color: '#38bdf8', padding: '6px 14px', borderRadius: 7, fontSize: 12, cursor: 'pointer' }}>
                <i className="ti ti-search" /> Scan Duplicates
              </button>
            }>
              {!dupes && <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>Click "Scan Duplicates" to detect emails appearing more than once in the database.</span>}
              {dupes && (
                <>
                  <div style={{ marginBottom: 14, display: 'flex', gap: 14 }}>
                    <div style={{ background: 'var(--panel-bg)', borderRadius: 10, padding: '12px 20px', textAlign: 'center' }}>
                      <div style={{ fontSize: 28, fontWeight: 700, color: dupes.total_duplicate_groups > 0 ? '#f87171' : '#22c55e', fontFamily: "'DM Mono', monospace" }}>{dupes.total_duplicate_groups}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>duplicate groups</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' }}>
                    {dupes.duplicates.slice(0, 30).map((d, i) => (
                      <div key={i} style={{ background: 'var(--panel-bg)', border: '1px solid #2d1a1a', borderRadius: 8, padding: '10px 14px', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                        <span style={{ background: '#f8717122', color: '#f87171', fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 99, whiteSpace: 'nowrap' }}>×{d.count}</span>
                        <div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: "'DM Mono', monospace", marginBottom: 4 }}>{d.email}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{d.names.join(' · ')}</div>
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
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 12px', background: 'var(--panel-bg)', borderRadius: 8, fontSize: 12 }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{c.company_name}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{c.location || '—'}</span>
                    </div>
                  ))}
                  {orphans.count === 0 && <span style={{ color: '#22c55e', fontSize: 12.5 }}>✓ All companies have linked recruiters.</span>}
                </div>
              </Section>
            )}
          </div>
        )}

        {/* ── SQL TAB ── */}
        {/* Upload Ops */}
        {activeTab === 'uploads' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            <Section title="Upload Operations Center" icon="ti-cloud-upload" action={<Badge color="#38bdf8">ETL History</Badge>}>
              {!(uploadOps?.jobs?.length) ? (
                <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ background: 'var(--bg-hover)' }}>
                        {['File Name', 'Rows', 'Status', 'Date', 'Source', 'Actions'].map(h => (
                          <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: '#38bdf8', fontSize: 10.5, letterSpacing: '0.06em', textTransform: 'uppercase', borderBottom: '1px solid var(--card-border)', whiteSpace: 'nowrap' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {uploadOps.jobs.slice(0, 30).map((j) => (
                        <tr key={j.job_id} style={{ borderBottom: '1px solid var(--card-border)' }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'var(--panel-bg)' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                        >
                          <td style={{ padding: '10px 12px', color: 'var(--text-primary)', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{j.filename}</td>
                          <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', fontFamily: "'DM Mono', monospace" }}>{fmt(j.total_rows)}</td>
                          <td style={{ padding: '10px 12px' }}>
                            <Badge color={j.status === 'completed' ? '#22c55e' : j.status === 'failed' ? '#ef4444' : j.status === 'processing' ? '#f59e0b' : '#38bdf8'}>
                              {String(j.status || 'unknown').toUpperCase()}
                            </Badge>
                          </td>
                          <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontFamily: "'DM Mono', monospace", whiteSpace: 'nowrap' }}>{String(j.started_at || '').replace('T', ' ').slice(0, 16) || '—'}</td>
                          <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{j.source || 'No Data Available'}</td>
                          <td style={{ padding: '10px 12px' }}>
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                              
                              <button onClick={() => retryImport(j.job_id)} style={{ background: 'var(--bg-hover)', border: '1px solid var(--card-border)', color: '#38bdf8', padding: '6px 10px', borderRadius: 8, fontSize: 11.5, cursor: 'pointer' }}>
                                Retry
                              </button>
                              
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Section>
          </div>
        )}

        {/* Search Intelligence */}
        {activeTab === 'intel' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>
              <Section title="Most Searched States" icon="ti-map-2" style={{ marginBottom: 0 }}>
                {(searchIntel?.most_searched_states || []).slice(0, 12).map((r, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: 'var(--panel-bg)', borderRadius: 10, border: '1px solid var(--card-border)', marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-secondary)', fontFamily: "'DM Mono', monospace" }}>{r.key}</span>
                    <span style={{ color: '#38bdf8', fontWeight: 700, fontFamily: "'DM Mono', monospace" }}>{fmt(r.count)}</span>
                  </div>
                ))}
                {!(searchIntel?.most_searched_states?.length) && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>}
              </Section>

              <Section title="Most Searched Companies" icon="ti-building" style={{ marginBottom: 0 }}>
                {(searchIntel?.most_searched_companies || []).slice(0, 12).map((r, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: 'var(--panel-bg)', borderRadius: 10, border: '1px solid var(--card-border)', marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.key}</span>
                    <span style={{ color: '#a78bfa', fontWeight: 700, fontFamily: "'DM Mono', monospace" }}>{fmt(r.count)}</span>
                  </div>
                ))}
                {!(searchIntel?.most_searched_companies?.length) && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>}
              </Section>

              <Section title="Most Searched Recruiters" icon="ti-users" style={{ marginBottom: 0 }}>
                {(searchIntel?.most_searched_recruiters || []).slice(0, 12).map((r, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: 'var(--panel-bg)', borderRadius: 10, border: '1px solid var(--card-border)', marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.key}</span>
                    <span style={{ color: '#22c55e', fontWeight: 700, fontFamily: "'DM Mono', monospace" }}>{fmt(r.count)}</span>
                  </div>
                ))}
                {!(searchIntel?.most_searched_recruiters?.length) && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>}
              </Section>
            </div>
          </div>
        )}

        {/* Export Analytics */}
        {activeTab === 'exports' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14, marginBottom: 20 }}>
              <StatCard icon="ti-file-export" label="Exports (Last 24h)" value={exportIntel?.exports != null ? fmt(exportIntel.exports) : 'No Data Available'} color="#38bdf8" glow />
              <StatCard icon="ti-building" label="Top Exported Company" value={exportIntel?.most_exported_companies?.[0]?.key || 'No Data Available'} sub={exportIntel?.most_exported_companies?.[0] ? `${fmt(exportIntel.most_exported_companies[0].count)} exports` : null} color="#a78bfa" />
              <StatCard icon="ti-map" label="Top Exported State" value={exportIntel?.most_exported_states?.[0]?.key || 'No Data Available'} sub={exportIntel?.most_exported_states?.[0] ? `${fmt(exportIntel.most_exported_states[0].count)} exports` : null} color="#22c55e" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <Section title="Most Exported States" icon="ti-map-2" style={{ marginBottom: 0 }}>
                {(exportIntel?.most_exported_states || []).slice(0, 15).map((r, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: 'var(--panel-bg)', borderRadius: 10, border: '1px solid var(--card-border)', marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-secondary)', fontFamily: "'DM Mono', monospace" }}>{r.key}</span>
                    <span style={{ color: '#22c55e', fontWeight: 700, fontFamily: "'DM Mono', monospace" }}>{fmt(r.count)}</span>
                  </div>
                ))}
                {!(exportIntel?.most_exported_states?.length) && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>}
              </Section>
              <Section title="Most Exported Companies" icon="ti-building" style={{ marginBottom: 0 }}>
                {(exportIntel?.most_exported_companies || []).slice(0, 15).map((r, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 12px', background: 'var(--panel-bg)', borderRadius: 10, border: '1px solid var(--card-border)', marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.key}</span>
                    <span style={{ color: '#a78bfa', fontWeight: 700, fontFamily: "'DM Mono', monospace" }}>{fmt(r.count)}</span>
                  </div>
                ))}
                {!(exportIntel?.most_exported_companies?.length) && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No Data Available</div>}
              </Section>
            </div>
          </div>
        )}

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
              <pre style={{ fontFamily: "'DM Mono', monospace", fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'pre-wrap', margin: 0 }}>{sysInfo.postgres_version}</pre>
            </Section>

            <Section title="Table Storage Sizes" icon="ti-table">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {tableSizes.map((t, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 14px', background: 'var(--panel-bg)', borderRadius: 8 }}>
                    <span style={{ fontSize: 12, color: '#38bdf8', minWidth: 160, fontFamily: "'DM Mono', monospace" }}>{t.table_name}</span>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 80 }}>{t.total_size}</span>
                    <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{fmt(t.live_rows)} rows</span>
                    <div style={{ flex: 1, height: 4, background: 'var(--card-border)', borderRadius: 99, overflow: 'hidden' }}>
                      <div style={{ width: `${Math.round(t.size_bytes / (tableSizes[0]?.size_bytes || 1) * 100)}%`, height: '100%', background: 'linear-gradient(90deg, #1d4ed8, #38bdf8)', borderRadius: 99 }} />
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          </div>
        )}

        {/* ── VISITOR LOG BOOK TAB ── */}
        {activeTab === 'logbook' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
              {[1, 7, 14, 30].map(d => (
                <button key={d} onClick={() => { setLogDays(d); loadVisitorLogs(d) }} style={{
                  background: logDays === d ? 'linear-gradient(135deg, #0ea5e9, #1d4ed8)' : 'var(--card-bg)',
                  border: '1px solid', borderColor: logDays === d ? '#0ea5e9' : 'var(--card-border)',
                  color: logDays === d ? '#fff' : 'var(--text-muted)', padding: '7px 18px', borderRadius: 8,
                  fontSize: 12.5, fontWeight: 500, cursor: 'pointer',
                }}>Last {d} day{d > 1 ? 's' : ''}</button>
              ))}
              <button onClick={() => loadVisitorLogs(logDays)} style={{
                marginLeft: 'auto', background: 'var(--card-bg)', border: '1px solid var(--card-border)',
                color: '#38bdf8', padding: '7px 16px', borderRadius: 8, fontSize: 12.5, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                {loadingLogs
                  ? <><i className="ti ti-loader" style={{ animation: 'spin 0.8s linear infinite' }} /> Loading…</>
                  : <><i className="ti ti-refresh" /> Refresh</>}
              </button>
            </div>

            {logsError && (
              <div style={{ background: 'rgba(248,113,113,0.1)', border: '1px solid #7f1d1d', borderRadius: 10, padding: '12px 16px', marginBottom: 16, color: '#f87171', fontSize: 12.5 }}>
                <i className="ti ti-alert-circle" style={{ marginRight: 6 }} />
                Could not load visitor log: {logsError}
              </div>
            )}

            {loadingLogs && !visitorSummary && (
              <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 14, padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                <i className="ti ti-loader" style={{ fontSize: 28, animation: 'spin 0.8s linear infinite', display: 'block', marginBottom: 10 }} />
                Loading visitor log book…
              </div>
            )}

            {visitorSummary && (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginBottom: 20 }}>
                  <StatCard icon="ti-users" label="Unique Sessions" value={fmt(visitorLogs?.total ?? 0)} color="#38bdf8" />
                  <StatCard icon="ti-eye" label="Page Views"
                    value={fmt(visitorLogs?.total_visits ?? visitorSummary.daily.reduce((s, d) => s + Number(d.page_views), 0))} color="#a78bfa" />
                  <StatCard icon="ti-mail" label="Unique Users"
                    value={fmt(visitorSummary.top_users?.length ?? 0)} color="#34d399" />
                  <StatCard icon="ti-chart-bar" label="Top Page"
                    value={visitorSummary.top_pages?.[0]?.page || '—'} color="#f472b6" />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                  <Section title="Daily Activity" icon="ti-calendar" style={{ marginBottom: 0 }}>
                    <div style={{ height: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {(visitorSummary.daily?.length ? [...visitorSummary.daily].reverse() : []).map((d, i) => {
                        const max = Math.max(...(visitorSummary.daily || []).map(x => Number(x.page_views)), 1)
                        const w = Math.round(Number(d.page_views) / max * 100)
                        return (
                          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                            <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 80, fontFamily: "'DM Mono', monospace" }}>{String(d.day).slice(0, 10)}</span>
                            <div style={{ flex: 1, height: 6, background: 'var(--bg-hover)', borderRadius: 99, overflow: 'hidden' }}>
                              <div style={{ width: `${w}%`, height: '100%', background: 'linear-gradient(90deg, #1d4ed8, #38bdf8)', borderRadius: 99 }} />
                            </div>
                            <span style={{ fontSize: 11, fontWeight: 600, color: '#38bdf8', minWidth: 30, textAlign: 'right', fontFamily: "'DM Mono', monospace" }}>{d.page_views}</span>
                          </div>
                        )
                      })}
                      {!(visitorSummary.daily?.length) && (
                        <div style={{ color: 'var(--text-muted)', fontSize: 12, textAlign: 'center', paddingTop: 40 }}>No daily data yet</div>
                      )}
                    </div>
                  </Section>

                  <Section title="Top Pages" icon="ti-map" style={{ marginBottom: 0 }}>
                    <div style={{ height: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {(visitorSummary.top_pages || []).map((p, i) => {
                        const max = visitorSummary.top_pages[0]?.views || 1
                        return (
                          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                            <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 16, textAlign: 'right' }}>{i + 1}</span>
                            <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 90, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.page}</span>
                            <div style={{ flex: 1, height: 5, background: 'var(--bg-hover)', borderRadius: 99, overflow: 'hidden' }}>
                              <div style={{ width: `${Math.round(p.views / max * 100)}%`, height: '100%', background: 'linear-gradient(90deg, #7c3aed, #a78bfa)', borderRadius: 99 }} />
                            </div>
                            <span style={{ fontSize: 11, fontWeight: 600, color: '#a78bfa', minWidth: 28, textAlign: 'right', fontFamily: "'DM Mono', monospace" }}>{p.views}</span>
                          </div>
                        )
                      })}
                      {!(visitorSummary.top_pages?.length) && (
                        <div style={{ color: 'var(--text-muted)', fontSize: 12, textAlign: 'center', paddingTop: 40 }}>No page data yet</div>
                      )}
                    </div>
                  </Section>
                </div>
              </>
            )}

            {visitorLogs && (
              <Section title={`Session Log (${visitorLogs.total} sessions)`} icon="ti-list" style={{ marginBottom: 0 }}>
                <div style={{ maxHeight: 550, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {visitorLogs.sessions.length > 0
                    ? visitorLogs.sessions.map((s, i) => (
                      <SessionRow
                        key={s.session_id || i}
                        session={s}
                        index={i}
                        isOpen={expandedSession === s.session_id}
                        onToggle={() => setExpandedSession(expandedSession === s.session_id ? null : s.session_id)}
                      />
                    ))
                    : (
                      <div style={{ color: 'var(--text-secondary)', fontSize: 12.5, textAlign: 'center', padding: '48px 16px', lineHeight: 1.6 }}>
                        <i className="ti ti-users" style={{ fontSize: 32, color: 'var(--card-border)', display: 'block', marginBottom: 12 }} />
                        No sessions in the last {logDays} day{logDays > 1 ? 's' : ''}.
                        {visitorLogs.total_visits > 0
                          ? <> ({visitorLogs.total_visits} raw visits found — try a longer range.)</>
                          : <> Browse the app (Dashboard, Recruiters, etc.) while logged in, then click <strong style={{ color: '#38bdf8' }}>Refresh</strong>.</>}
                      </div>
                    )}
                </div>
              </Section>
            )}
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
                {logLines.length === 0 && <span style={{ color: 'var(--card-border)' }}>— No activity yet —</span>}
                {logLines.map((l, i) => (
                  <div key={i} style={{ color: l.type === 'error' ? '#f87171' : l.type === 'warn' ? '#fbbf24' : l.type === 'ok' ? '#4ade80' : 'var(--text-muted)' }}>
                    <span style={{ color: 'var(--card-border)', userSelect: 'none' }}>[{l.ts}] </span>{l.msg}
                  </div>
                ))}
                <span style={{ color: 'var(--card-border)', animation: 'blink 1.2s step-end infinite' }}>▌</span>
              </div>
            </Section>
          </div>
        )}
      </div>
    </div>
  )
}
