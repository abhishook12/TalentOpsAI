import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, AreaChart, Area, Cell, LabelList
} from 'recharts'
import api, { API } from '../services/api'

const CHART_TICK = { fill: '#ffffff', fontSize: 12, fontWeight: 700 }

const BAR_LABEL_PROPS = { fill: '#ffffff', fontSize: 12, fontWeight: 700 }

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
          <p style={{ color: 'var(--text-primary)', fontSize: 15, fontWeight: 700, lineHeight: 1.1, margin: 0 }}>{value ?? 'â€”'}</p>
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
      <h3 style={{ color: 'var(--text-primary)', fontSize: compact ? 18 : 26, fontWeight: 700, lineHeight: 1 }}>{value ?? 'â€”'}</h3>
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
          <p style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Recruiters</p>
          <p style={{ fontSize: 16, fontWeight: 700, color: '#185FA5' }}>{d?.recruiters?.toLocaleString()}</p>
        </div>
      </div>
    </div>
  )
}

export default function Analytics() {
  const { data: analyticsData, isLoading: loading } = useQuery({
    queryKey: ['analytics-dashboard'],
    queryFn: async () => {
      const [v, s] = await Promise.all([
        api.get('/analytics/visit-stats'),
        api.get('/analytics/recruiters-by-state'),
      ])

      const raw = Array.isArray(s.data) ? s.data : []
      const stateData = raw
        .map((r) => ({ state: r.state, recruiters: Number(r.count) || 0 }))
        .filter((r) => r.state && r.recruiters > 0)
        .sort((a, b) => b.recruiters - a.recruiters)
        .slice(0, 10)
        
      return { visits: v.data, stateData }
    }
  })

  const visits = analyticsData?.visits
  const stateData = analyticsData?.stateData || []

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

  const isEmptyAnalytics =
    (visits?.total_visits || 0) === 0 &&
    stateData.length === 0 &&
    dailyData.length === 0 &&
    weeklyData.length === 0 &&
    topPages.length === 0

  const hasStateData = stateData.length > 0

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        height: '100%',
        display: 'grid',
        gridTemplateRows: isEmptyAnalytics
          ? 'auto auto'
          : (hasStateData ? 'auto minmax(0, 1fr) minmax(0, 1fr)' : 'auto auto minmax(0, 1fr)'),
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
          <KPI inline label="Today" value={(visits?.today || 0).toLocaleString()} sub={todayChange !== null ? `${todayChange > 0 ? 'â–²' : 'â–¼'} ${Math.abs(todayChange)}%` : null} color="#185FA5" icon="ti-calendar-today" />
          <KPI inline label="Yesterday" value={(visits?.yesterday || 0).toLocaleString()} color="#0F6E56" icon="ti-calendar" />
        </div>
      </div>

      {/* State chart â€” full width middle row */}
      {isEmptyAnalytics ? (
        <SectionCard title="Analytics Setup" icon="ti-info-circle" compact style={{ gridColumn: '1 / -1' }}>
          <div style={{ display: 'grid', placeItems: 'center', height: '100%', padding: 18, textAlign: 'center' }}>
            <div style={{ maxWidth: 640 }}>
              <div style={{ width: 54, height: 54, borderRadius: 16, background: 'var(--accent-bg)', border: '1px solid rgba(45, 212, 191, 0.22)', display: 'grid', placeItems: 'center', margin: '0 auto 10px' }}>
                <i className="ti ti-chart-bar" style={{ fontSize: 18, color: 'var(--accent)' }} />
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>No analytics data yet</div>
              <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                This dashboard only displays real data from your database. Once visit tracking is active and company records include state information, charts will populate automatically.
              </div>
              <div style={{ marginTop: 12, textAlign: 'left', fontSize: 12, color: 'var(--text-secondary)' }}>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>Checklist</div>
                <ul style={{ paddingLeft: 18, margin: 0, lineHeight: 1.65 }}>
                  <li>Confirm the API is reachable from this environment.</li>
                  <li>Generate page visits by browsing the app (visit tracking endpoints must be enabled).</li>
                  <li>Ensure companies have a valid state/region so the “Companies by State” chart can aggregate.</li>
                </ul>
              </div>
              <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>
                API: <span style={{ fontFamily: 'var(--mono)' }}>{API}</span>
              </div>
            </div>
          </div>
        </SectionCard>
      ) : (
        <SectionCard title="State-wise Recruiters Distribution" icon="ti-map" compact style={{ gridColumn: '1 / -1', minHeight: hasStateData ? 0 : 160 }}>
          {stateData.length === 0 ? (
            <div style={{ display: 'grid', placeItems: 'center', height: '100%', textAlign: 'center', color: 'var(--text-muted)', fontSize: 11, padding: 14 }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>No state data yet</div>
                <div style={{ marginTop: 6 }}>
                  This chart needs recruiter records with a populated state field.
                </div>
              </div>
            </div>
          ) : (
            <div style={{ position: 'relative', flex: 1, minHeight: 0, width: '100%' }}>
              <ChartBox>
                <BarChart data={stateData} margin={{ top: 16, right: 8, left: 0, bottom: 4 }} barCategoryGap="18%">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                  <XAxis dataKey="state" tick={CHART_TICK} axisLine={false} tickLine={false} interval={0} />
                  <YAxis tick={CHART_TICK} axisLine={false} tickLine={false} width={36} allowDecimals={false} />
                  <Tooltip content={<StateTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                  <Bar dataKey="recruiters" radius={[3, 3, 0, 0]} maxBarSize={24}>
                    <LabelList dataKey="recruiters" position="top" {...BAR_LABEL_PROPS} />
                    {stateData.map((entry, i) => (
                      <Cell key={entry.state} fill={PAGE_COLORS[i % PAGE_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ChartBox>
            </div>
          )}
        </SectionCard>
      )}

      {/* Bottom row: 3 equal panels */}
      {!isEmptyAnalytics && (
        <>
      <SectionCard title="Daily â€” 7 Days" icon="ti-chart-area-line" compact style={{ minHeight: 0 }}>
        {dailyData.length === 0 ? (
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data</div>
        ) : (
          <div style={{ position: 'relative', flex: 1, minHeight: 0, width: '100%' }}>
            <ChartBox>
              <AreaChart data={dailyData} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                <defs>
                  <linearGradient id="visitGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#185FA5" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#185FA5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                <XAxis dataKey="day" tick={CHART_TICK} axisLine={false} tickLine={false} />
                <YAxis tick={CHART_TICK} axisLine={false} tickLine={false} width={36} allowDecimals={false} />
                <Tooltip {...customTooltipStyle} />
                <Area type="monotone" dataKey="visits" stroke="#185FA5" strokeWidth={1.5} fill="url(#visitGrad)" dot={false} />
              </AreaChart>
            </ChartBox>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Weekly â€” 4 Wks" icon="ti-calendar-week" compact style={{ minHeight: 0 }}>
        {weeklyData.length === 0 ? (
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data</div>
        ) : (
          <div style={{ position: 'relative', flex: 1, minHeight: 0, width: '100%' }}>
            <ChartBox>
              <BarChart data={weeklyData} margin={{ top: 16, right: 8, left: 0, bottom: 4 }} maxBarSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                <XAxis dataKey="week" tick={CHART_TICK} axisLine={false} tickLine={false} />
                <YAxis tick={CHART_TICK} axisLine={false} tickLine={false} width={36} allowDecimals={false} />
                <Tooltip {...customTooltipStyle} />
                <Bar dataKey="visits" fill="#534AB7" radius={[3, 3, 0, 0]}>
                  <LabelList dataKey="visits" position="top" {...BAR_LABEL_PROPS} />
                </Bar>
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
                      <span style={{ color: PAGE_COLORS[i % PAGE_COLORS.length], marginRight: 3 }}>â—</span>
                      {p.page}
                    </span>
                    <span style={{ fontSize: 12, color: '#ffffff', fontWeight: 700 }}>{p.visits.toLocaleString()}</span>
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
        </>
      )}
    </div>
  )
}
