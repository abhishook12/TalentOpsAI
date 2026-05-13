import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line, CartesianGrid
} from 'recharts'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const COLORS = ['#38bdf8', '#34d399', '#a78bfa', '#fb923c', '#f87171', '#facc15']

function SectionCard({ title, children }) {
  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '12px',
      padding: '24px',
      marginBottom: '24px'
    }}>
      <h2 style={{ color: '#f1f5f9', fontSize: '16px', fontWeight: '600', marginBottom: '20px' }}>{title}</h2>
      {children}
    </div>
  )
}

function KPI({ label, value, color }) {
  return (
    <div style={{
      background: '#0f172a',
      borderRadius: '10px',
      padding: '20px',
      borderLeft: `4px solid ${color}`,
      flex: 1
    }}>
      <p style={{ color: '#64748b', fontSize: '12px', marginBottom: '6px' }}>{label}</p>
      <h3 style={{ color: '#f1f5f9', fontSize: '28px', fontWeight: 'bold' }}>{value}</h3>
    </div>
  )
}

function Analytics() {
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
    <div style={{ color: '#64748b', padding: '40px', textAlign: 'center' }}>Loading analytics...</div>
  )

  return (
    <div>
      <h1 style={{ color: '#f1f5f9', fontSize: '24px', fontWeight: 'bold', marginBottom: '8px' }}>Analytics</h1>
      <p style={{ color: '#64748b', marginBottom: '28px' }}>Operational intelligence overview</p>

      {/* KPI Row */}
      {dashboard && (
        <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
          <KPI label="Total Recruiters" value={dashboard.recruiters.total} color="#38bdf8" />
          <KPI label="Total Candidates" value={dashboard.candidates.total} color="#34d399" />
          <KPI label="Total Submissions" value={dashboard.submissions.total} color="#a78bfa" />
          <KPI label="Placement Rate" value={`${dashboard.submissions.placement_rate_percent}%`} color="#fb923c" />
          <KPI label="Duplicate Rate" value={`${dashboard.candidates.duplicate_rate_percent}%`} color="#f87171" />
        </div>
      )}

      {/* Row 1: Submissions by Status + Candidates by Visa */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>

        <SectionCard title="Submissions by Status">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={byStatus}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="status" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#f1f5f9' }}
                itemStyle={{ color: '#38bdf8' }}
              />
              <Bar dataKey="count" fill="#38bdf8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>

        <SectionCard title="Candidates by Visa Status">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={byVisa}
                dataKey="count"
                nameKey="visa_status"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label={({ visa_status, percent }) => `${visa_status} ${(percent * 100).toFixed(0)}%`}
              >
                {byVisa.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                itemStyle={{ color: '#f1f5f9' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </SectionCard>

      </div>

      {/* Row 2: Recruiter Productivity + Submissions Trend */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>

        <SectionCard title="Recruiter Productivity">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={productivity} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#0f172a" />
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis dataKey="recruiter" type="category" tick={{ fill: '#94a3b8', fontSize: 11 }} width={100} />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#f1f5f9' }}
              />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: '12px' }} />
              <Bar dataKey="total_submissions" fill="#38bdf8" name="Submissions" radius={[0, 4, 4, 0]} />
              <Bar dataKey="placements" fill="#34d399" name="Placements" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </SectionCard>

        <SectionCard title="Submissions Trend">
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#0f172a" />
                <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                  labelStyle={{ color: '#f1f5f9' }}
                  itemStyle={{ color: '#a78bfa' }}
                />
                <Line type="monotone" dataKey="count" stroke="#a78bfa" strokeWidth={2} dot={{ fill: '#a78bfa' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: '#64748b', textAlign: 'center', padding: '60px 0' }}>
              Not enough trend data yet
            </div>
          )}
        </SectionCard>

      </div>
    </div>
  )
}

export default Analytics