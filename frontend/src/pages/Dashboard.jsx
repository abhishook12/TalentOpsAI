import { useEffect, useState } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

function StatCard({ title, value, color }) {
  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '24px',
      borderLeft: `4px solid ${color}`
    }}>
      <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '8px' }}>{title}</p>
      <h2 style={{ color: '#f1f5f9', fontSize: '32px', fontWeight: 'bold' }}>{value.toLocaleString()}</h2>
    </div>
  )
}

function Dashboard() {
  const [stats, setStats] = useState({ recruiters: 0, candidates: 0, submissions: 0, companies: 0 })

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
    }).catch(() => {})
  }, [])

  return (
    <div>
      <h1 style={{ color: '#f1f5f9', fontSize: '24px', fontWeight: 'bold', marginBottom: '8px' }}>
        Dashboard
      </h1>
      <p style={{ color: '#64748b', marginBottom: '32px' }}>Welcome to TalentOps AI</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
        <StatCard title="Total Recruiters" value={stats.recruiters} color="#38bdf8" />
        <StatCard title="Total Candidates" value={stats.candidates} color="#34d399" />
        <StatCard title="Total Submissions" value={stats.submissions} color="#a78bfa" />
        <StatCard title="Companies" value={stats.companies} color="#fb923c" />
      </div>

      <div style={{ background: '#1e293b', borderRadius: '12px', padding: '24px' }}>
        <h2 style={{ color: '#f1f5f9', marginBottom: '16px' }}>Quick Links</h2>
        <p style={{ color: '#64748b' }}>Use the sidebar to navigate to Recruiters, Candidates, Submissions and Analytics.</p>
      </div>
    </div>
  )
}

export default Dashboard