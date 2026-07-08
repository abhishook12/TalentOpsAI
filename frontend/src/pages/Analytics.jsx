import { useQuery } from '@tanstack/react-query'
import { cloneElement, useEffect, useRef, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, AreaChart, Area, Cell, LabelList,
  PieChart, Pie
} from 'recharts'
import api, { API } from '../services/api'

const CHART_TICK = { fill: 'var(--text-primary)', fontSize: 12, fontWeight: 700 }

const BAR_LABEL_PROPS = { fill: 'var(--text-primary)', fontSize: 12, fontWeight: 700 }

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

function fadeHex(hex, alpha) {
  if (!hex?.startsWith('#') || (hex.length !== 7 && hex.length !== 4)) return hex
  const normalized = hex.length === 4
    ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
    : hex
  const safeAlpha = Math.max(0, Math.min(1, alpha))
  const alphaHex = Math.round(safeAlpha * 255).toString(16).padStart(2, '0')
  return `${normalized}${alphaHex}`
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

function ChartBox({ children, height = 240 }) {
  const containerRef = useRef(null)
  const [size, setSize] = useState({ width: 0, height })

  useEffect(() => {
    const element = containerRef.current
    if (!element || typeof ResizeObserver === 'undefined') {
      setSize({ width: element?.clientWidth || 0, height })
      return undefined
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      const width = Math.max(0, Math.floor(entry?.contentRect?.width || 0))
      const nextHeight = Math.max(height, Math.floor(entry?.contentRect?.height || height))
      setSize({ width, height: nextHeight })
    })

    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height, minHeight: height }}>
      {size.width > 0 ? cloneElement(children, { width: size.width, height: size.height }) : null}
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
  const [selectedStates, setSelectedStates] = useState([])
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState(null)

  const { data: taxonomyData, refetch: refetchTaxonomy } = useQuery({
    queryKey: ['taxonomy-distribution'],
    queryFn: async () => (await api.get('/analytics/taxonomy-distribution')).data,
    staleTime: 60_000,
  })

  const handleTaxonomySync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await api.post('/ai/taxonomy-sync')
      setSyncResult(res.data)
      refetchTaxonomy()
    } catch (e) {
      setSyncResult({ error: e.response?.data?.detail || 'Sync failed' })
    } finally {
      setSyncing(false)
    }
  }

  const { data: analyticsData, isLoading: loading } = useQuery({
    queryKey: ['analytics-dashboard'],
    queryFn: async () => {
      const [v, s, dq] = await Promise.all([
        api.get('/analytics/visit-stats'),
        api.get('/analytics/recruiters-by-state'),
        api.get('/analytics/data-quality')
      ])

      const raw = Array.isArray(s.data) ? s.data : []
      const stateData = raw
        .map((r) => ({ state: r.state, recruiters: Number(r.count) || 0 }))
        .filter((r) => r.state && r.recruiters > 0)
        .sort((a, b) => b.recruiters - a.recruiters)
        .slice(0, 10)
        
      return { visits: v.data, stateData, dq: dq.data }
    }
  })

  const visits = analyticsData?.visits
  const stateData = analyticsData?.stateData || []
  const dq = analyticsData?.dq

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
  const hasStateSelection = selectedStates.length > 0
  const visibleStateData = hasStateSelection
    ? stateData.filter((entry) => selectedStates.includes(entry.state))
    : stateData
  const stateChartMax = visibleStateData.reduce((max, entry) => Math.max(max, entry.recruiters), 0)

  const toggleStateSelection = (stateCode) => {
    if (!stateCode) return
    setSelectedStates((current) => (
      current.includes(stateCode)
        ? current.filter((item) => item !== stateCode)
        : [...current, stateCode]
    ))
  }

  const clearStateSelection = () => setSelectedStates([])

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
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0, lineHeight: 1.1 }}>Advanced Intelligence</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <KPI inline label="Total Visits" value={(visits?.total_visits || 0).toLocaleString()} color="#7C3AED" icon="ti-eye" />
          <KPI inline label="Today" value={(visits?.today || 0).toLocaleString()} sub={todayChange !== null ? `${todayChange > 0 ? '▲' : '▼'} ${Math.abs(todayChange)}%` : null} color="#185FA5" icon="ti-calendar-today" />
          <KPI inline label="Yesterday" value={(visits?.yesterday || 0).toLocaleString()} color="#0F6E56" icon="ti-calendar" />
        </div>
        
        <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', margin: '8px 0 0', lineHeight: 1.1 }}>State Extraction Intelligence</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <KPI inline label="Known State" value={dq?.known_state_count?.toLocaleString()} color="#0F6E56" icon="ti-map-pin-filled" />
          <KPI inline label="Explicit State" value={dq?.explicit_state_count?.toLocaleString()} color="#185FA5" icon="ti-target" />
          <KPI inline label="Inferred State" value={dq?.inferred_state_count?.toLocaleString()} color="#7C3AED" icon="ti-wand" />
          <KPI inline label="Unknown State" value={dq?.unknown_state_count?.toLocaleString()} color="#ef4444" icon="ti-alert-triangle" />
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4, padding: '8px 12px', background: 'rgba(239, 68, 68, 0.05)', borderRadius: 8, border: '1px solid rgba(239, 68, 68, 0.1)' }}>
          <i className="ti ti-info-circle" style={{ marginRight: 4, color: '#ef4444' }} />
          <strong>Unknown State Records:</strong> These records lack any parsable state, location, or company metadata. They cannot be placed into the directory map until updated.
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
            <div style={{ position: 'relative', width: '100%', height: 320 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {stateData.map((entry, i) => {
                    const selected = selectedStates.includes(entry.state)
                    const color = PAGE_COLORS[i % PAGE_COLORS.length]

                    return (
                      <button
                        key={entry.state}
                        type="button"
                        onClick={() => toggleStateSelection(entry.state)}
                        style={{
                          border: `1px solid ${selected ? color : 'var(--card-border)'}`,
                          background: selected ? fadeHex(color, 0.16) : 'var(--card-bg)',
                          color: 'var(--text-primary)',
                          borderRadius: 999,
                          padding: '5px 10px',
                          fontSize: 10.5,
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          cursor: 'pointer',
                          transition: 'all 160ms ease',
                        }}
                        aria-pressed={selected}
                        title={`${STATE_FULL_NAMES[entry.state] || entry.state}: ${entry.recruiters.toLocaleString()} recruiters`}
                      >
                        <span style={{ width: 8, height: 8, borderRadius: 999, background: color, flexShrink: 0 }} />
                        {entry.state}
                      </button>
                    )
                  })}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
                  <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>
                    {hasStateSelection ? `${visibleStateData.length} selected` : 'Click bars or chips to compare states'}
                  </span>
                  {hasStateSelection && (
                    <button
                      type="button"
                      onClick={clearStateSelection}
                      style={{
                        border: '1px solid var(--card-border)',
                        background: 'var(--card-bg)',
                        color: 'var(--text-primary)',
                        borderRadius: 999,
                        padding: '5px 10px',
                        fontSize: 10.5,
                        fontWeight: 700,
                        cursor: 'pointer',
                      }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <ChartBox>
                <BarChart data={visibleStateData} margin={{ top: 34, right: 20, left: 12, bottom: 8 }} barCategoryGap="18%">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" vertical={false} />
                  <XAxis dataKey="state" tick={CHART_TICK} axisLine={false} tickLine={false} interval={0} />
                  <YAxis
                    tick={CHART_TICK}
                    axisLine={false}
                    tickLine={false}
                    width={44}
                    allowDecimals={false}
                    domain={[0, Math.max(5, Math.ceil(stateChartMax * 1.12))]}
                  />
                  <Tooltip content={<StateTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                  <Bar dataKey="recruiters" radius={[3, 3, 0, 0]} maxBarSize={24} onClick={(data) => toggleStateSelection(data?.state)}>
                    <LabelList dataKey="recruiters" position="top" {...BAR_LABEL_PROPS} />
                    {visibleStateData.map((entry) => {
                      const colorIndex = stateData.findIndex((item) => item.state === entry.state)
                      const color = PAGE_COLORS[(colorIndex === -1 ? 0 : colorIndex) % PAGE_COLORS.length]
                      return (
                      <Cell
                        key={entry.state}
                        fill={color}
                        stroke={selectedStates.includes(entry.state) ? color : 'transparent'}
                        strokeWidth={selectedStates.includes(entry.state) ? 1.5 : 0}
                        style={{ cursor: 'pointer' }}
                      />
                      )
                    })}
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
      <SectionCard title="Daily — 7 Days" icon="ti-chart-area-line" compact style={{ minHeight: 0 }}>
        {dailyData.length === 0 ? (
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data</div>
        ) : (
          <div style={{ position: 'relative', width: '100%', height: 240 }}>
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

      <SectionCard title="Weekly — 4 Wks" icon="ti-calendar-week" compact style={{ minHeight: 0 }}>
        {weeklyData.length === 0 ? (
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>No data</div>
        ) : (
          <div style={{ position: 'relative', width: '100%', height: 240 }}>
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
                      <span style={{ color: PAGE_COLORS[i % PAGE_COLORS.length], marginRight: 3 }}>●</span>
                      {p.page}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700 }}>{p.visits.toLocaleString()}</span>
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

      {/* Taxonomy Intelligence Row */}
      {!isEmptyAnalytics && (
        <SectionCard title="Industry Taxonomy Intelligence" icon="ti-category" compact style={{ gridColumn: '1 / -1', minHeight: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' }}>
            {/* Pie Chart */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              {taxonomyData?.distribution?.length > 0 ? (
                <ChartBox height={260}>
                  <PieChart>
                    <Pie
                      data={taxonomyData.distribution.filter(d => d.category !== 'Uncategorized')}
                      dataKey="count"
                      nameKey="category"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      innerRadius={50}
                      paddingAngle={2}
                      label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                      style={{ fontSize: 10 }}
                    >
                      {taxonomyData.distribution.filter(d => d.category !== 'Uncategorized').map((entry, i) => (
                        <Cell key={entry.category} fill={PAGE_COLORS[i % PAGE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip {...customTooltipStyle} />
                  </PieChart>
                </ChartBox>
              ) : (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                  <i className="ti ti-category" style={{ fontSize: 24, display: 'block', marginBottom: 8, color: 'var(--accent)' }} />
                  No taxonomy data yet. Run AI Sync to categorize titles.
                </div>
              )}
            </div>

            {/* Stats + Sync Button */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <KPI inline label="Categorized" value={taxonomyData?.categorized?.toLocaleString() || '0'} color="#0F6E56" icon="ti-check" />
                <KPI inline label="Uncategorized" value={taxonomyData?.uncategorized?.toLocaleString() || '0'} color="#ef4444" icon="ti-alert-triangle" />
                <KPI inline label="Coverage" value={`${taxonomyData?.coverage_pct || 0}%`} color="#534AB7" icon="ti-percentage" />
                <KPI inline label="Total Active" value={taxonomyData?.total?.toLocaleString() || '0'} color="#185FA5" icon="ti-users" />
              </div>

              <div style={{ padding: '14px 16px', background: 'var(--accent-bg)', border: '1px solid rgba(45, 212, 191, 0.15)', borderRadius: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                  <i className="ti ti-sparkles" style={{ color: 'var(--accent)', marginRight: 4 }} />
                  AI Taxonomy Sync
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: 10 }}>
                  Uses Gemini AI to intelligently categorize uncategorized job titles into industry groups (Healthcare, Technology, Finance, etc.).
                </div>
                <button
                  onClick={handleTaxonomySync}
                  disabled={syncing || (taxonomyData?.uncategorized === 0)}
                  style={{
                    padding: '8px 16px', borderRadius: 8, border: 'none',
                    background: syncing ? 'var(--card-border)' : 'var(--accent)',
                    color: '#fff', fontSize: 12, fontWeight: 600,
                    cursor: syncing ? 'not-allowed' : 'pointer',
                    display: 'flex', alignItems: 'center', gap: 6,
                    opacity: (taxonomyData?.uncategorized === 0) ? 0.5 : 1,
                  }}
                >
                  <i className={syncing ? 'ti ti-loader animate-spin' : 'ti ti-wand'} />
                  {syncing ? 'Syncing with Gemini...' : taxonomyData?.uncategorized === 0 ? 'All Titles Categorized' : `Categorize ${taxonomyData?.uncategorized?.toLocaleString()} Titles`}
                </button>
                {syncResult && (
                  <div style={{ marginTop: 8, fontSize: 11, padding: '8px 10px', borderRadius: 6, background: syncResult.error ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)', color: syncResult.error ? '#ef4444' : '#22c55e', border: `1px solid ${syncResult.error ? 'rgba(239,68,68,0.2)' : 'rgba(34,197,94,0.2)'}` }}>
                    {syncResult.error || `✓ ${syncResult.message} — ${syncResult.updated_recruiters} recruiters updated.`}
                  </div>
                )}
              </div>

              {/* Category breakdown list */}
              {taxonomyData?.distribution?.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {taxonomyData.distribution.map((d, i) => {
                    const pct = taxonomyData.total > 0 ? Math.round(d.count / taxonomyData.total * 100) : 0
                    return (
                      <div key={d.category} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
                        <span style={{ width: 8, height: 8, borderRadius: 999, background: d.category === 'Uncategorized' ? '#6b7280' : PAGE_COLORS[i % PAGE_COLORS.length], flexShrink: 0 }} />
                        <span style={{ flex: 1, color: 'var(--text-primary)', fontWeight: 500 }}>{d.category}</span>
                        <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--mono)', fontSize: 10 }}>{d.count.toLocaleString()}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: 10, width: 32, textAlign: 'right' }}>{pct}%</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </SectionCard>
      )}

      {/* Data Health Scorecard Row */}
      {!isEmptyAnalytics && (
        <SectionCard title="Data Health & Completeness" icon="ti-heart-rate" compact style={{ gridColumn: '1 / -1', minHeight: 0 }}>
          <DataHealthScorecard />
        </SectionCard>
      )}

    </div>
  )
}

function DataHealthScorecard() {
  const { data, isLoading } = useQuery({
    queryKey: ['data-health'],
    queryFn: async () => (await api.get('/analytics/data-health')).data,
    staleTime: 60_000,
  })

  if (isLoading) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>Loading health data...</div>
  if (!data || !data.metrics) return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>No data available</div>

  const getScoreColor = (score) => {
    if (score >= 90) return '#0F6E56' // Green
    if (score >= 70) return '#eab308' // Yellow
    return '#ef4444' // Red
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24, alignItems: 'center' }}>
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 140, height: 140, borderRadius: '50%', background: `conic-gradient(${getScoreColor(data.overall_health_score)} ${data.overall_health_score}%, var(--card-border) 0)` }}>
          <div style={{ position: 'absolute', inset: 8, background: 'var(--card-bg)', borderRadius: '50%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: getScoreColor(data.overall_health_score), lineHeight: 1 }}>{data.overall_health_score}%</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginTop: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>Overall Health</div>
          </div>
        </div>
        <div style={{ marginTop: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
          Tracking completeness across <b>{data.total_active?.toLocaleString()}</b> active recruiters.
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {data.metrics.map(m => (
          <div key={m.field} style={{ background: 'var(--bg-default)', padding: '12px 16px', borderRadius: 8, border: '1px solid var(--card-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, alignItems: 'baseline' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{m.field} Coverage</span>
              <div style={{ display: 'flex', gap: 12, alignItems: 'baseline' }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}><span style={{ color: '#ef4444', fontWeight: 600 }}>{m.missing.toLocaleString()}</span> missing</span>
                <span style={{ fontSize: 14, fontWeight: 700, color: getScoreColor(m.health_pct) }}>{m.health_pct}%</span>
              </div>
            </div>
            <div style={{ height: 6, background: 'var(--card-border)', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${m.health_pct}%`, background: getScoreColor(m.health_pct), borderRadius: 99, transition: 'width 1s ease-out' }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

