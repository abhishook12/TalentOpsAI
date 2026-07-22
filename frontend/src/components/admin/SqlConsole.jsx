import { useState } from 'react'
import api from '../../services/api'
import Section from './Section'
import Badge from './Badge'

export default function SqlConsole() {
  const [sql, setSql] = useState('SELECT name, email, location FROM recruiters LIMIT 10')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = async () => {
    setLoading(true); setError(null); setResult(null)
    try {
      const res = await api.post('/admin/sql', { sql })
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

  const fmt = (n) => n?.toLocaleString?.() ?? '—';

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
          color: 'var(--text-primary)', padding: '9px 22px', borderRadius: 8, fontSize: 13, fontWeight: 600,
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
