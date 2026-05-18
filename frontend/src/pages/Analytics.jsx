import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend
} from 'recharts'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const COLORS = ['#185FA5', '#0F6E56', '#534AB7', '#BA7517', '#dc2626', '#0891b2']

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
  const [byStatus, setByStatus] = useState([])
  const [byVisa, setByVisa] = useState([])
  const [productivity, setProductivity] = useState([])
  const [trend, setTrend] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/analytics/dashboard`),
      axios.get(`${API}/analytics/submissions-by-status`),
      axios.get(`${API}/analytics/candidates-by-visa`),
      axios.get(`${API}/analytics/recruiter-productivity`),
      axios.get(`${API}/analytics/submissions-trend`),
    ]).then(([d, s, v, p, t]) => {
      setDashboard(d.data)
      setByStatus(s.data)
      setByVisa(v.data)
      setProductivity(p.data)
      setTrend(t.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
      <i className="ti ti-chart-bar" style={{ fontSize: 28, display: 'block', marginBottom: 10 }} />
      Loading analytics...
    </div>
  )

  return (
    <div className="page-enter">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>Analytics</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Recruitment operations intelligence overview</p>
      </div>

      {/* KPI Row */}
      {dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 24 }}>
          <KPI label="Total Recruiters" value={dashboard.recruiters.total} color="#185FA5" />
          <KPI label="Total Candidates" value={dashboard.candidates.total} color="#0F6E56" />
          <KPI label="Total Submissions" value={dashboard.submissions.total} color="#534AB7" />
          <KPI label="Placement Rate" value={`${dashboard.submissions.placement_rate_percent}%`} color="#0F6E56" />
          <KPI label="Duplicate Rate" value={`${dashboard.candidates.duplicate_rate_percent}%`} color="#dc2626" />
        </div>
      )}

      {/* Row 1: Submissions by Status + Candidates by Visa */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <SectionCard title="Submissions by Status">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={byStatus} barSize={32}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
              <XAxis dataKey="status" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...customTooltipStyle} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {byStatus.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>

        <SectionCard title="Candidates by Visa Status">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={byVisa} dataKey="count" nameKey="visa_status" cx="50%" cy="50%"
                outerRadius={85} innerRadius={40}
                label={({ visa_status, percent }) => `${visa_status} ${(percent * 100).toFixed(0)}%`}
                labelLine={{ stroke: 'var(--border-input)' }}>
                {byVisa.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip {...customTooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </SectionCard>
      </div>

      {/* Row 2: Recruiter Productivity + Submissions Trend */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <SectionCard title="Recruiter Productivity">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={productivity} layout="vertical" barSize={14}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" horizontal={false} />
              <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="recruiter" type="category" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} width={110} axisLine={false} tickLine={false} />
              <Tooltip {...customTooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-muted)' }} />
              <Bar dataKey="total_submissions" fill="#185FA5" name="Submissions" radius={[0, 4, 4, 0]} />
              <Bar dataKey="placements" fill="#0F6E56" name="Placements" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>

        <SectionCard title="Submissions Trend">
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip {...customTooltipStyle} />
                <Line type="monotone" dataKey="count" stroke="#534AB7" strokeWidth={2.5}
                  dot={{ fill: '#534AB7', r: 4, strokeWidth: 0 }}
                  activeDot={{ r: 6, strokeWidth: 0 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              <div style={{ textAlign: 'center' }}>
                <i className="ti ti-chart-line" style={{ fontSize: 28, display: 'block', marginBottom: 8 }} />
                Not enough trend data yet
              </div>
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}