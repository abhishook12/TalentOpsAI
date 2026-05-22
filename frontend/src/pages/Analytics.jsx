import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, AreaChart, Area, Cell
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

function SectionCard({ title, icon, children, style, compact }) {
  return (
    <div className="card" style={{
      padding: compact ? '8px 10px' : 24,
      display: 'flex',
      flexDirection: 'column',
      minHeight: 0,
      overflow: 'hidden',
      ...style,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: compact ? 6 : 12, flexShrink: 0 }}>
        {icon && <i className={`ti ${icon}`} style={{ fontSize: compact ? 13 : 15, color: 'var(--accent)' }} />}
        <h2 style={{ fontSize: compact ? 11.5 : 13, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>{title}</h2>
      </div>
      <div style={{ flex: 1, minHeight: 0, position: 'relative', display: 'flex', flexDirection: 'column' }}>{children}</div>
    </div>
  )
}

function KPI({ label, value, sub, color, icon, compact, inline }) {
  if (inline) {
    return (
      <div style={{
        background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 6,
        padding: '6px 10px', borderLeft: `3px solid ${color}`,
        display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1,
      }}>
        <i className={`ti ${icon}`} style={{ fontSize: 13, color, flexShrink: 0 }} />
        <div style={{ minWidth: 0 }}>
          <p style={{ color: 'var(--text-muted)', fontSize: 9, fontWeight: 500, lineHeight: 1.1, margin: 0 }}>{label}</p>
          <p style={{ color: 'var(--text-primary)', fontSize: 15, fontWeight: 700, lineHeight: 1.1, margin: 0 }}>{value ?? '—'}</p>
          {sub && <p style={{ fontSize: 9, color: 'var(--text-muted)', margin: 0, lineHeight: 1.1 }}>{sub}</p>}
        </div>
      </div>
    )
  }
  return (
    <div style={{
      background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 8,
      padding: compact ? '10px 12px' : '18px 20px', borderLeft: `3px solid ${color}`,
      display: 'flex', flexDirection: 'column', gap: compact ? 2 : 6, minHeight: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <i className={`ti ${icon}`} style={{ fontSize: compact ? 12 : 14, color }} />
        <p style={{ color: 'var(--text-muted)', fontSize: compact ? 10 : 11, fontWeight: 500, lineHeight: 1.2 }}>{label}</p>
      </div>
      <h3 style={{ color: 'var(--text-primary)', fontSize: compact ? 18 : 26, fontWeight: 700, lineHeight: 1 }}>{value ?? '—'}</h3>
      {sub && <p style={{ fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.2 }}>{sub}</p>}
    </div>
  )
}

function ChartBox({ children }) {
  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
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
  const [visits, setVisits]       = useState(null)
  const [stateData, setStateData] = useState([])
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/analytics/visit-stats`),
      axios.get(`${API}/analytics/companies-count-by-state`),
    ]).then(([v, s]) => {
      setVisits(v.data)

      // Transform { "NC": 45, "TX": 32, ... } → sorted array for chart
      const raw = s.data || {}
      const arr = Object.entries(raw)
        .map(([abbr, count]) => ({ state: abbr, companies: count }))
        .sort((a, b) => b.companies - a.companies)
        .slice(0, 10) // top 10 states — compact chart
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
    <div
      style={{
        flex: 1,
        minHeight: 0,
        height: '100%',
        display: 'grid',
        gridTemplateRows: 'auto minmax(0, 1fr) minmax(0, 1fr)',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: 8,
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      {/* Header + KPI strip */}
      <div style={{ gridColumn: '1 / -1', display: 'flex', flexDirection: 'column', gap: 8, flexShrink: 0 }}>
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0, lineHeight: 1.1 }}>Analytics</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <KPI inline label="Total Visits" value={(visits?.total_visits || 0).toLocaleString()} color="#7C3AED" icon="ti-eye" />
          <KPI inline label="Today" value={(visits?.today || 0).toLocaleString()} sub={todayChange !== null ? `${todayChange > 0 ? '▲' : '▼'} ${Math.abs(todayChange)}%` : null} color="#185FA5" icon="ti-calendar-today" />
          <KPI inline label="Yesterday" value={(visits?.yesterday || 0).toLocaleString()} color="#0F6E56" icon="ti-calendar" />
        </div>
      </div>

      {/* State chart — full width middle row */}
      <SectionCard title="State‑wise Companies Distribution" icon="ti-map" compact style={{ gridColumn: '1 / -1', minHeight: 0 }}>
        {stateData.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 11 }}>No state data yet.</div>
        ) : (
          <div style={{ position: 'relative', flex: 1, minHeight: 0, width: '100%' }}>
            <ChartBox>
              <BarChart data={stateData} margin={{ top: 2, right: 4, left: -10, bottom: 2 }} barCategoryGap="18%">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                <XAxis dataKey="state" tick={{ fill: 'var(--text-secondary)', fontSize: 9, fontWeight: 500 }} axisLine={false} tickLine={false} interval={0} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 9 }} axisLine={false} tickLine={false} width={26} allowDecimals={false} />
                <Tooltip content={<StateTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                <Bar dataKey="companies" radius={[3, 3, 0, 0]} maxBarSize={24}>
                  {stateData.map((entry, i) => (
                    <Cell key={entry.state} fill={PAGE_COLORS[i % PAGE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ChartBox>
          </div>
        )}
      </SectionCard>

      {/* Bottom row: 3 equal panels */}
      <SectionCard title="Daily — 7 Days" icon="ti-chart-area-line" compact style={{ minHeight: 0 }}>
        {dailyData.length === 0 ? (
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data</div>
        ) : (
          <div style={{ position: 'relative', flex: 1, minHeight: 0, width: '100%' }}>
            <ChartBox>
              <AreaChart data={dailyData} margin={{ top: 2, right: 4, left: -10, bottom: 2 }}>
                <defs>
                  <linearGradient id="visitGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#185FA5" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#185FA5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 8 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 8 }} axisLine={false} tickLine={false} width={24} allowDecimals={false} />
                <Tooltip {...customTooltipStyle} />
                <Area type="monotone" dataKey="visits" stroke="#185FA5" strokeWidth={1.5} fill="url(#visitGrad)" dot={false} />
              </AreaChart>
            </ChartBox>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Weekly — 4 Wks" icon="ti-calendar-week" compact style={{ minHeight: 0 }}>
        {weeklyData.length === 0 ? (
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data</div>
        ) : (
          <div style={{ position: 'relative', flex: 1, minHeight: 0, width: '100%' }}>
            <ChartBox>
              <BarChart data={weeklyData} margin={{ top: 2, right: 4, left: -10, bottom: 2 }} maxBarSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                <XAxis dataKey="week" tick={{ fill: 'var(--text-muted)', fontSize: 8 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 8 }} axisLine={false} tickLine={false} width={24} allowDecimals={false} />
                <Tooltip {...customTooltipStyle} />
                <Bar dataKey="visits" fill="#534AB7" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ChartBox>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Top Pages" icon="ti-layout-dashboard" compact style={{ minHeight: 0 }}>
        {topPages.length === 0 ? (
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, overflow: 'hidden', height: '100%' }}>
            {topPages.slice(0, 5).map((p, i) => {
              const max = topPages[0].visits
              const pct = Math.round((p.visits / max) * 100)
              return (
                <div key={p.page} style={{ flexShrink: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 1 }}>
                    <span style={{ fontSize: 9.5, color: 'var(--text-primary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '72%' }}>
                      <span style={{ color: PAGE_COLORS[i % PAGE_COLORS.length], marginRight: 3 }}>●</span>
                      {p.page}
                    </span>
                    <span style={{ fontSize: 9.5, color: 'var(--text-muted)', fontWeight: 500 }}>{p.visits.toLocaleString()}</span>
                  </div>
                  <div style={{ height: 3, background: 'var(--card-border)', borderRadius: 99 }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: PAGE_COLORS[i % PAGE_COLORS.length], borderRadius: 99 }} />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </SectionCard>
    </div>
  )
}