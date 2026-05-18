import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const COLORS = ['#185FA5', '#0F6E56', '#534AB7', '#BA7517']

function SectionCard({ title, children }) {
  return (
    <div className="card" style={{ padding: 24 }}>
      <h2 style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 20, letterSpacing: '-0.01em' }}>{title}</h2>
      {children}
    </div>
  )
}

function KPI({ label, value, color }) {
  return (
    <div style={{ background: 'var(--bg-hover)', borderRadius: 10, padding: '16px 18px', borderLeft: `3px solid ${color}` }}>
      <p style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 6, fontWeight: 500 }}>{label}</p>
      <h3 style={{ color: 'var(--text-primary)', fontSize: 24, fontWeight: 600 }}>{value}</h3>
    </div>
  )
}

const customTooltipStyle = {
  contentStyle: { background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: 12 },
  labelStyle: { color: 'var(--text-primary)', fontWeight: 500 },
  itemStyle: { color: 'var(--text-secondary)' },
}

export default function Analytics() {
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get(`${API}/analytics/dashboard`)
      .then(r => {
        setDashboard(r.data)
        setLoading(false)
      }).catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
      <i className="ti ti-chart-bar" style={{ fontSize: 28, display: 'block', marginBottom: 10 }} />
      Loading analytics...
    </div>
  )

  // Dummy chart data for recruiter activity (since backend might lack deep recruiter metrics atm)
  const activityData = [
    { name: 'Active', count: dashboard?.recruiters?.active || 0 },
    { name: 'Inactive', count: (dashboard?.recruiters?.total || 0) - (dashboard?.recruiters?.active || 0) }
  ]

  return (
    <div className="page-enter">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>Analytics</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Recruitment operations intelligence overview</p>
      </div>

      {/* KPI Row */}
      {dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, marginBottom: 24 }}>
          <KPI label="Total Recruiters" value={dashboard.recruiters.total} color="#185FA5" />
          <KPI label="Active Recruiters" value={dashboard.recruiters.active} color="#0F6E56" />
        </div>
      )}

      {/* Row 1: Recruiter Status */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16, marginBottom: 16 }}>
        <SectionCard title="Recruiter Status Breakdown">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={activityData} barSize={40}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...customTooltipStyle} />
              <Bar dataKey="count" fill="#185FA5" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>
      </div>
    </div>
  )
}