import { useEffect, useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

function StatCard({ title, value, sub, icon, color }) {
  return (
    <div className="card" style={{ padding: '18px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>{title}</span>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: color + '18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className={`ti ${icon}`} style={{ fontSize: 16, color }} />
        </div>
      </div>
      <p style={{ fontSize: 26, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', margin: 0 }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </p>
      {sub && <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{sub}</p>}
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
          <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>Dashboard</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{today}</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/ai-search')}>
          <i className="ti ti-search" style={{ fontSize: 14 }} /> AI Search
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: 16, marginBottom: 24 }}>
        <StatCard title="Total Recruiters" value={v(kpi?.recruiters?.total)} sub={`${kpi?.recruiters?.active ?? '...'} active`} icon="ti-users" color="#185FA5" />
        <StatCard title="Companies" value={v(kpi?.companies?.total)} sub="Partner firms" icon="ti-building" color="#BA7517" />
      </div>

      {/* Quick actions */}
      <div className="card" style={{ padding: 20 }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 14 }}>Quick Actions</p>
        {[
          { label: 'Search recruiters by name', icon: 'ti-search', color: '#185FA5', path: '/ai-search' },
          { label: 'View all recruiters', icon: 'ti-users', color: '#0F6E56', path: '/recruiters' },
          { label: 'Upload recruiters list', icon: 'ti-upload', color: '#534AB7', path: '/upload' },
          { label: 'View analytics', icon: 'ti-chart-bar', color: 'var(--text-secondary)', path: '/analytics' },
        ].map(({ label, icon, color, path }) => (
          <div key={label} onClick={() => navigate(path)}
            style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 8, cursor: 'pointer', marginBottom: 4, transition: 'background 0.12s' }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
            <div style={{ width: 32, height: 32, borderRadius: 6, background: color + '15', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <i className={`ti ${icon}`} style={{ fontSize: 16, color }} />
            </div>
            <span style={{ fontSize: 13.5, color: 'var(--text-primary)' }}>{label}</span>
            <i className="ti ti-arrow-right" style={{ marginLeft: 'auto', fontSize: 14, color: 'var(--text-muted)' }} />
          </div>
        ))}
      </div>
    </div>
  )
}
