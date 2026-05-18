import { useEffect, useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

function StatCard({ title, value, sub, icon, color }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e8edf4', borderRadius: 10,
      padding: '18px 20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>{title}</span>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: color + '18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className={`ti ${icon}`} style={{ fontSize: 16, color }} />
        </div>
      </div>
      <p style={{ fontSize: 26, fontWeight: 500, color: '#0f172a', letterSpacing: '-0.02em', margin: 0 }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </p>
      {sub && <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const [kpi, setKpi] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    axios.get(`${API}/analytics/dashboard`)
      .then(r => { setKpi(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
  const v = (n) => loading ? '...' : n

  return (
    <div className="page-enter">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 4 }}>Dashboard</h1>
          <p style={{ fontSize: 13, color: '#94a3b8' }}>{today}</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/ai-search')}>
          <i className="ti ti-search" style={{ fontSize: 14 }} /> AI Search
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gap: 12, marginBottom: 24 }}>
        <StatCard title="Total Recruiters" value={v(kpi?.recruiters?.total)} sub={`${kpi?.recruiters?.active ?? '...'} active`} icon="ti-users" color="#185FA5" />
        <StatCard title="Candidates" value={v(kpi?.candidates?.total)} sub={`${kpi?.candidates?.duplicates ?? '...'} duplicates`} icon="ti-user-check" color="#0F6E56" />
        <StatCard title="Submissions" value={v(kpi?.submissions?.total)} sub={`${kpi?.submissions?.placement_rate_percent ?? '...'}% placement rate`} icon="ti-file-text" color="#534AB7" />
        <StatCard title="Companies" value={v(kpi?.companies?.total)} sub="Partner firms" icon="ti-building" color="#BA7517" />
      </div>

      {/* Second row — pipeline + quick actions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Pipeline status */}
        <div style={{ background: '#fff', border: '1px solid #e8edf4', borderRadius: 10, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <p style={{ fontSize: 13, fontWeight: 500, color: '#0f172a', marginBottom: 16 }}>Submission Pipeline</p>
          {[
            { label: 'Placed', value: kpi?.submissions?.placed, color: '#0F6E56', bg: '#dcfce7' },
            { label: 'Offers', value: kpi?.submissions?.offers, color: '#534AB7', bg: '#ede9fe' },
            { label: 'Interviews', value: kpi?.submissions?.interviews, color: '#BA7517', bg: '#fef9c3' },
          ].map(({ label, value, color, bg }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 28, height: 28, borderRadius: 6, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                </div>
                <span style={{ fontSize: 13, color: '#64748b' }}>{label}</span>
              </div>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>{loading ? '...' : (value ?? 0)}</span>
            </div>
          ))}
          <div style={{ marginTop: 14, padding: '10px 14px', background: '#f8fafc', borderRadius: 8 }}>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Placement rate — </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#0F6E56' }}>{loading ? '...' : `${kpi?.submissions?.placement_rate_percent ?? 0}%`}</span>
          </div>
        </div>

        {/* Quick actions */}
        <div style={{ background: '#fff', border: '1px solid #e8edf4', borderRadius: 10, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <p style={{ fontSize: 13, fontWeight: 500, color: '#0f172a', marginBottom: 14 }}>Quick Actions</p>
          {[
            { label: 'Search recruiters by name', icon: 'ti-search', color: '#185FA5', path: '/ai-search' },
            { label: 'View all recruiters', icon: 'ti-users', color: '#0F6E56', path: '/recruiters' },
            { label: 'Add new candidate', icon: 'ti-user-plus', color: '#534AB7', path: '/candidates' },
            { label: 'Track submissions', icon: 'ti-file-text', color: '#BA7517', path: '/submissions' },
            { label: 'View analytics', icon: 'ti-chart-bar', color: '#64748b', path: '/analytics' },
          ].map(({ label, icon, color, path }) => (
            <div key={label} onClick={() => navigate(path)}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 8, cursor: 'pointer', marginBottom: 2, transition: 'background 0.12s' }}
              onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: color + '15', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <i className={`ti ${icon}`} style={{ fontSize: 14, color }} />
              </div>
              <span style={{ fontSize: 13, color: '#334155' }}>{label}</span>
              <i className="ti ti-arrow-right" style={{ marginLeft: 'auto', fontSize: 13, color: '#cbd5e1' }} />
            </div>
          ))}
        </div>
      </div>

      {/* Candidate data quality row */}
      <div style={{ background: '#fff', border: '1px solid #e8edf4', borderRadius: 10, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: '#0f172a', marginBottom: 14 }}>Data Quality</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {[
            { label: 'Total Candidates', value: kpi?.candidates?.total, color: '#185FA5' },
            { label: 'Duplicate Candidates', value: kpi?.candidates?.duplicates, color: '#dc2626' },
            { label: 'Duplicate Rate', value: `${kpi?.candidates?.duplicate_rate_percent ?? 0}%`, color: '#BA7517' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ padding: '14px 16px', borderRadius: 8, background: '#f8fafc', border: '1px solid #f1f5f9' }}>
              <p style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>{label}</p>
              <p style={{ fontSize: 20, fontWeight: 600, color }}>{loading ? '...' : (value ?? 0)}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
