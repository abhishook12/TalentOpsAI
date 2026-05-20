import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, AreaChart, Area, Cell, PieChart, Pie, Legend
} from 'recharts'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const PAGE_COLORS = ['#185FA5', '#0F6E56', '#534AB7', '#BA7517', '#C4394A', '#1695A3', '#7C3AED', '#D97706']

const STATE_FULL_NAMES = {
  AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',
  DE:'Delaware',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',
  KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',
  MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',
  NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',
  OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',
  TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',
}

const customTooltipStyle = {
  contentStyle: { background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', fontSize: 12 },
  labelStyle: { color: 'var(--text-primary)', fontWeight: 500 },
  itemStyle: { color: 'var(--text-secondary)' },
}

function SectionCard({ title, icon, children, style }) {
  return (
    <div className="card" style={{ padding: 24, ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
        {icon && <i className={`ti ${icon}`} style={{ fontSize: 15, color: 'var(--accent)' }} />}
        <h2 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>{title}</h2>
      </div>
      {children}
    </div>
  )
}

function KPI({ label, value, sub, color, icon }) {
  return (
    <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 10, padding: '18px 20px', borderLeft: `3px solid ${color}`, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <i className={`ti ${icon}`} style={{ fontSize: 14, color }} />
        <p style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 500 }}>{label}</p>
      </div>
      <h3 style={{ color: 'var(--text-primary)', fontSize: 26, fontWeight: 700, lineHeight: 1 }}>{value ?? '—'}</h3>
      {sub && <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</p>}
    </div>
  )
}

function formatDay(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatWeek(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `W of ${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
}

/* Custom tooltip for the state chart */
function StateTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div style={{
      background: 'var(--card-bg)', border: '1px solid var(--card-border)',
      borderRadius: 10, padding: '12px 16px', boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
      minWidth: 180,
    }}>
      <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
        {STATE_FULL_NAMES[d?.state] || d?.state}
      </p>
      <div style={{ display: 'flex', gap: 16 }}>
        <div>
          <p style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Companies</p>
          <p style={{ fontSize: 16, fontWeight: 700, color: '#185FA5' }}>{d?.companies?.toLocaleString()}</p>
        </div>
      </div>
    </div>
  )
}

export default function Analytics() {
  const [dashboard, setDashboard] = useState(null)
  const [visits, setVisits]       = useState(null)
  const [stateData, setStateData] = useState([])
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/analytics/dashboard`),
      axios.get(`${API}/analytics/visit-stats`),
      axios.get(`${API}/analytics/companies-count-by-state`),
    ]).then(([d, v, s]) => {
      setDashboard(d.data)
      setVisits(v.data)

      // Transform { "NC": 45, "TX": 32, ... } → sorted array for chart
      const raw = s.data || {}
      const arr = Object.entries(raw)
        .map(([abbr, count]) => ({ state: abbr, companies: count }))
        .sort((a, b) => b.companies - a.companies)
        .slice(0, 20) // top 20 states for readability
      setStateData(arr)

      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
      <i className="ti ti-chart-bar" style={{ fontSize: 28, display: 'block', marginBottom: 10 }} />
      Loading analytics...
    </div>
  )

  const dailyData = (visits?.daily || []).map(r => ({
    day: formatDay(r.day), visits: r.visits
  }))

  const weeklyData = (visits?.weekly || []).map(r => ({
    week: formatWeek(r.week), visits: r.visits
  }))

  const topPages = (visits?.top_pages || [])

  const todayChange = visits?.yesterday > 0
    ? (((visits.today - visits.yesterday) / visits.yesterday) * 100).toFixed(0)
    : null

  return (
    <div className="page-enter">
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>Analytics</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Recruitment operations intelligence + site usage insights</p>
      </div>

      {/* ── Section 1: Recruiter KPIs ── */}
      <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>Recruiter Overview</p>
      {dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, marginBottom: 28 }}>
          <KPI label="Total Recruiters" value={dashboard.recruiters.total.toLocaleString()} color="#185FA5" icon="ti-users" />
          <KPI label="Active Recruiters" value={dashboard.recruiters.active.toLocaleString()} color="#0F6E56" icon="ti-user-check" />
        </div>
      )}

      {/* ── State‑wise Companies Distribution ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16, marginBottom: 28 }}>
        <SectionCard title="State‑wise Companies Distribution" icon="ti-map">
          {stateData.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)', fontSize: 13 }}>
              <i className="ti ti-map-off" style={{ fontSize: 28, display: 'block', marginBottom: 8 }} />
              No state data available yet.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(300, stateData.length * 32)}>
              <BarChart data={stateData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" horizontal={false} />
                <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis
                  dataKey="state" type="category"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontWeight: 500 }}
                  axisLine={false} tickLine={false} width={50}
                />
                <Tooltip content={<StateTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                <Bar dataKey="companies" radius={[0, 6, 6, 0]} barSize={20}>
                  {stateData.map((entry, i) => (
                    <Cell key={entry.state} fill={PAGE_COLORS[i % PAGE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </SectionCard>
      </div>

      {/* ── Section 2: Site Usage ── */}
      <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>Site Usage & Traffic</p>

      {/* Visit KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 24 }}>
        <KPI
          label="Total Visits (All Time)"
          value={(visits?.total_visits || 0).toLocaleString()}
          color="#7C3AED"
          icon="ti-eye"
        />
        <KPI
          label="Today's Visits"
          value={(visits?.today || 0).toLocaleString()}
          sub={todayChange !== null ? `${todayChange > 0 ? '▲' : '▼'} ${Math.abs(todayChange)}% vs yesterday` : 'No data yet'}
          color="#185FA5"
          icon="ti-calendar-today"
        />
        <KPI
          label="Yesterday's Visits"
          value={(visits?.yesterday || 0).toLocaleString()}
          color="#0F6E56"
          icon="ti-calendar"
        />
      </div>

      {/* Daily Chart */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16, marginBottom: 16 }}>
        <SectionCard title="Daily Visits — Last 7 Days" icon="ti-chart-area-line">
          {dailyData.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)', fontSize: 13 }}>
              <i className="ti ti-chart-dots-2" style={{ fontSize: 28, display: 'block', marginBottom: 8 }} />
              No visit data yet — data will appear as users browse the site.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={dailyData}>
                <defs>
                  <linearGradient id="visitGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#185FA5" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#185FA5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip {...customTooltipStyle} />
                <Area type="monotone" dataKey="visits" stroke="#185FA5" strokeWidth={2} fill="url(#visitGrad)" dot={{ fill: '#185FA5', r: 4 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </SectionCard>
      </div>

      {/* Weekly + Top Pages side-by-side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <SectionCard title="Weekly Visits — Last 4 Weeks" icon="ti-calendar-week">
          {weeklyData.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: 12 }}>
              No weekly data yet.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weeklyData} barSize={32}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                <XAxis dataKey="week" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip {...customTooltipStyle} />
                <Bar dataKey="visits" fill="#534AB7" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </SectionCard>

        <SectionCard title="Most Visited Pages" icon="ti-layout-dashboard">
          {topPages.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: 12 }}>
              No page visit data yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {topPages.map((p, i) => {
                const max = topPages[0].visits
                const pct = Math.round((p.visits / max) * 100)
                return (
                  <div key={p.page}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 500 }}>
                        <span style={{ color: PAGE_COLORS[i % PAGE_COLORS.length], marginRight: 6 }}>●</span>
                        {p.page}
                      </span>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>{p.visits.toLocaleString()}</span>
                    </div>
                    <div style={{ height: 5, background: 'var(--card-border)', borderRadius: 99 }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: PAGE_COLORS[i % PAGE_COLORS.length], borderRadius: 99, transition: 'width 0.6s ease' }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}