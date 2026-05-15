import { useEffect, useState } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

function StatCard({ title, value, icon, color, sub }) {
  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e8edf4',
      borderRadius: '10px',
      padding: '18px 20px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>{title}</span>
        <div style={{
          width: 32, height: 32, borderRadius: '8px',
          background: color + '18',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <i className={`ti ${icon}`} style={{ fontSize: 16, color }} aria-hidden="true" />
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
  const [stats, setStats] = useState({ recruiters: 0, candidates: 0, submissions: 0, companies: 0 })
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/recruiters?limit=50000`),
      axios.get(`${API}/candidates?limit=50000`),
      axios.get(`${API}/submissions?limit=50000`),
      axios.get(`${API}/companies?limit=50000`),
    ]).then(([r, c, s, co]) => {
      setStats({
        recruiters: r.data.length,
        candidates: c.data.length,
        submissions: s.data.length,
        companies: co.data.length,
      })
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })

  return (
    <div className="page-enter">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 4 }}>Dashboard</h1>
          <p style={{ fontSize: 13, color: '#94a3b8' }}>{today}</p>
        </div>
        <button className="btn-primary" onClick={() => navigate('/ai-search')}>
          <i className="ti ti-search" style={{ fontSize: 14 }} aria-hidden="true" />
          AI Search
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gap: '12px', marginBottom: '24px' }}>
        <StatCard title="Total Recruiters" value={loading ? '...' : stats.recruiters} icon="ti-users" color="#185FA5" sub="Active database" />
        <StatCard title="Candidates" value={loading ? '...' : stats.candidates} icon="ti-user-check" color="#0F6E56" sub="In pipeline" />
        <StatCard title="Submissions" value={loading ? '...' : stats.submissions} icon="ti-file-text" color="#534AB7" sub="Total tracked" />
        <StatCard title="Companies" value={loading ? '...' : stats.companies} icon="ti-building" color="#BA7517" sub="Partner firms" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <div style={{ background: '#fff', border: '1px solid #e8edf4', borderRadius: '10px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <p style={{ fontSize: 13, fontWeight: 500, color: '#0f172a', marginBottom: '14px' }}>Quick actions</p>
          {[
            { label: 'Search recruiters by name', icon: 'ti-search', color: '#185FA5', path: '/ai-search' },
            { label: 'View all recruiters', icon: 'ti-users', color: '#0F6E56', path: '/recruiters' },
            { label: 'Add new candidate', icon: 'ti-user-plus', color: '#534AB7', path: '/candidates' },
            { label: 'View submissions', icon: 'ti-file-text', color: '#BA7517', path: '/submissions' },
          ].map(({ label, icon, color, path }) => (
            <div key={label} onClick={() => navigate(path)}
              style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '9px 12px', borderRadius: '8px', cursor: 'pointer', marginBottom: '4px', transition: 'background 0.12s' }}
              onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ width: 28, height: 28, borderRadius: '6px', background: color + '15', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <i className={`ti ${icon}`} style={{ fontSize: 14, color }} aria-hidden="true" />
              </div>
              <span style={{ fontSize: 13, color: '#334155' }}>{label}</span>
              <i className="ti ti-arrow-right" style={{ marginLeft: 'auto', fontSize: 13, color: '#cbd5e1' }} aria-hidden="true" />
            </div>
          ))}
        </div>

        <div style={{ background: '#fff', border: '1px solid #e8edf4', borderRadius: '10px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <p style={{ fontSize: 13, fontWeight: 500, color: '#0f172a', marginBottom: '14px' }}>Platform overview</p>
          {[
            { label: 'Recruiter database', value: loading ? '...' : stats.recruiters.toLocaleString(), color: '#185FA5' },
            { label: 'Active candidates', value: loading ? '...' : stats.candidates.toLocaleString(), color: '#0F6E56' },
            { label: 'Total submissions', value: loading ? '...' : stats.submissions.toLocaleString(), color: '#534AB7' },
            { label: 'Partner companies', value: loading ? '...' : stats.companies.toLocaleString(), color: '#BA7517' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
                <span style={{ fontSize: 13, color: '#64748b' }}>{label}</span>
              </div>
              <span style={{ fontSize: 13, fontWeight: 500, color: '#0f172a' }}>{value}</span>
            </div>
          ))}
          <p style={{ fontSize: 11, color: '#cbd5e1', marginTop: '12px', textAlign: 'right' }}>Last updated just now</p>
        </div>
      </div>
    </div>
  )
}
