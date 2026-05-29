import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const pipelineRows = [
  { source: 'LinkedIn Global Dump', type: 'JSON', count: 412083, status: 'Live Sync' },
  { source: 'Apollo Integration v4', type: 'API', count: 82192, status: 'Completed' },
  { source: 'Manpower Group Historical', type: 'CSV', count: 12500, status: 'Completed' },
  { source: 'Crunchbase Pro Export', type: 'JSON', count: 4812, status: 'Schema Mismatch' },
  { source: 'State-Level Directories', type: 'CSV', count: 189420, status: 'Queued' },
]

const marketLeaders = [
  { code: 'KF', name: 'Korn Ferry', count: '8,421 Recruiters Identified' },
  { code: 'SS', name: 'Spencer Stuart', count: '4,102 Recruiters Identified' },
  { code: 'HS', name: 'Heidrick & Struggles', count: '3,890 Recruiters Identified' },
  { code: 'EZ', name: 'Egon Zehnder', count: '2,554 Recruiters Identified' },
]

const trafficSources = [
  { city: 'New York, US', x: 23, y: 36, share: 31 },
  { city: 'London, UK', x: 47, y: 29, share: 19 },
  { city: 'Bengaluru, IN', x: 68, y: 50, share: 23 },
  { city: 'Singapore, SG', x: 75, y: 57, share: 14 },
  { city: 'Sydney, AU', x: 84, y: 76, share: 13 },
]

function statusPill(status) {
  if (status === 'Live Sync') return { bg: 'rgba(22,163,74,0.1)', color: '#166534', icon: 'ti-point-filled' }
  if (status === 'Schema Mismatch') return { bg: 'rgba(220,38,38,0.08)', color: '#b91c1c', icon: 'ti-alert-triangle' }
  if (status === 'Queued') return { bg: 'rgba(180,83,9,0.1)', color: '#92400e', icon: 'ti-clock' }
  return { bg: 'rgba(15,23,42,0.08)', color: '#334155', icon: 'ti-circle-check' }
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('Dashboard')
  const [query, setQuery] = useState('')
  const [toast, setToast] = useState('')
  const [activeTraffic, setActiveTraffic] = useState(trafficSources[0])

  const { data: kpi, isLoading } = useQuery({
    queryKey: ['dashboard-kpi'],
    queryFn: async () => (await axios.get(`${API}/analytics/dashboard`)).data,
  })

  const { data: recruiterStats } = useQuery({
    queryKey: ['dashboard-recruiter-total'],
    queryFn: async () => (await axios.get(`${API}/recruiters?page=1&limit=1`)).data,
  })

  const { data: companyStats } = useQuery({
    queryKey: ['dashboard-company-total'],
    queryFn: async () => (await axios.get(`${API}/companies?page=1&limit=1`)).data,
  })

  const stats = useMemo(() => ([
    { label: 'Total Recruiters', icon: 'ti-users', value: recruiterStats?.total_count?.toLocaleString?.() ?? (isLoading ? '...' : (kpi?.recruiters?.total ?? 0).toLocaleString()), sub: isLoading ? 'Loading' : '~ +12.4% MoM' },
    { label: 'Associated Companies', icon: 'ti-building', value: companyStats?.total_count?.toLocaleString?.() ?? (isLoading ? '...' : (kpi?.companies?.total ?? 0).toLocaleString()), sub: isLoading ? 'Loading' : '~ +3.1% MoM' },
    { label: 'States Active', icon: 'ti-flag', value: '50', sub: 'Full Coverage REACH' },
    { label: 'Data Quality', icon: 'ti-shield-check', value: '99.4%', sub: 'Verified recruiter records' },
  ]), [kpi, isLoading])

  const ping = (msg) => {
    setToast(msg)
    console.log(`[UI Action] ${msg}`)
    setTimeout(() => setToast(''), 1800)
  }

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="card" style={{ padding: 14, borderRadius: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
            <h1 style={{ fontSize: 16, fontWeight: 700, color: '#17191d' }}>Recruiter Intelligence</h1>
            {['Dashboard', 'Staffing Firms'].map((tab) => (
              <button key={tab} onClick={() => { setActiveTab(tab); ping(`${tab} tab selected`) }} style={{
                background: 'transparent',
                borderBottom: activeTab === tab ? '2px solid #16181c' : '2px solid transparent',
                borderRadius: 0,
                color: '#2a3038',
                padding: '8px 2px',
                fontSize: 12,
                fontWeight: 600,
              }}>
                {tab}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => ping('Notifications opened')} title="Notifications" style={{ background: '#f7f7f5', border: '1px solid #d8d8d8', width: 30, height: 30 }}><i className="ti ti-bell" /></button>
            <button onClick={() => ping('Settings opened')} title="Settings" style={{ background: '#f7f7f5', border: '1px solid #d8d8d8', width: 30, height: 30 }}><i className="ti ti-settings" /></button>
            <button onClick={() => navigate('/admin')} title="Profile" style={{ background: '#f7f7f5', border: '1px solid #d8d8d8', width: 30, height: 30 }}><i className="ti ti-user-circle" /></button>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0,1fr))', gap: 10 }}>
        {stats.map((s) => (
          <div key={s.label} className="card" style={{ padding: 12, borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
              <span style={{ fontSize: 10, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.08em', color: '#6f7781' }}>{s.label}</span>
              <i className={`ti ${s.icon}`} style={{ color: '#6f7781' }} />
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#17191d' }}>{s.value}</div>
            <div style={{ fontSize: 11, color: '#6f7781', marginTop: 4 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: 10, display: 'flex', alignItems: 'center', gap: 8, borderRadius: 8 }}>
        <i className="ti ti-search" style={{ color: '#6f7781' }} />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask TalentOps AI..." style={{ flex: 1, border: 'none', background: 'transparent', padding: '8px 4px' }} />
        <kbd style={{ fontSize: 10, border: '1px solid #d8d8d8', borderRadius: 4, padding: '2px 6px', color: '#616975', background: '#f7f7f5' }}>⌘ K</kbd>
        <button className="btn-primary" onClick={() => { ping(`Search submitted: ${query || '(empty)'}`); navigate('/ai-search') }}>Search</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
        <div className="card" style={{ borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 12px', borderBottom: '1px solid #d8d8d8' }}>
            <strong style={{ fontSize: 12 }}>Intelligence Pipeline</strong>
            <button onClick={() => ping('View ETL Logs clicked')} style={{ background: 'transparent', color: '#334155', fontSize: 11 }}>View ETL Logs <i className="ti ti-arrow-right" /></button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Source</th><th>Type</th><th>Recruiter Count</th><th>Processed Status</th>
              </tr>
            </thead>
            <tbody>
              {pipelineRows.map((row) => {
                const s = statusPill(row.status)
                return (
                  <tr key={row.source} onClick={() => ping(`${row.source} clicked`)} style={{ cursor: 'pointer' }}>
                    <td style={{ fontWeight: 600 }}>{row.source}</td>
                    <td><span style={{ border: '1px solid #ddd', borderRadius: 4, fontSize: 10, padding: '2px 6px' }}>{row.type}</span></td>
                    <td>{row.count.toLocaleString()}</td>
                    <td>
                      <span style={{ background: s.bg, color: s.color, padding: '4px 8px', borderRadius: 999, fontSize: 11 }}>
                        <i className={`ti ${s.icon}`} /> {row.status}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'grid', gap: 10 }}>
          <div className="card" style={{ borderRadius: 8, padding: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <strong style={{ fontSize: 12 }}>Market Leaders</strong>
              <span style={{ fontSize: 11, color: '#6f7781' }}>By Count</span>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              {marketLeaders.map((m) => (
                <button key={m.code} onClick={() => ping(`${m.name} selected`)} style={{ display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left', background: '#fff', border: '1px solid #d8d8d8', padding: '8px 7px', borderRadius: 6 }}>
                  <span style={{ width: 22, height: 22, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: '#f3f3f2', borderRadius: 4, fontSize: 10, fontWeight: 700 }}>{m.code}</span>
                  <span style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{m.name}</div>
                    <div style={{ fontSize: 10, color: '#6f7781' }}>{m.count}</div>
                  </span>
                  <i className="ti ti-arrow-up-right" />
                </button>
              ))}
            </div>
            <button onClick={() => ping('Explore Firms Database clicked')} style={{ marginTop: 10, width: '100%', border: '1px solid #d8d8d8', background: '#f7f7f5', padding: '8px', fontSize: 12 }}>Explore Firms Database</button>
          </div>

          <div className="card" style={{ borderRadius: 8, padding: 10 }}>
            <strong style={{ fontSize: 12 }}>State Coverage</strong>
            <div style={{ height: 130, border: '1px solid #d8d8d8', borderRadius: 6, marginTop: 8, position: 'relative', background: 'linear-gradient(180deg, #f8f8f7, #f3f3f1)', overflow: 'hidden' }}>
              <svg viewBox="0 0 800 360" preserveAspectRatio="none" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                <path d="M44 160 L110 130 L170 145 L190 178 L165 210 L100 220 L60 194 Z" fill="#d7d9dc" />
                <path d="M230 145 L270 118 L325 122 L362 150 L332 182 L277 190 L240 175 Z" fill="#d7d9dc" />
                <path d="M370 115 L430 98 L500 116 L560 150 L550 198 L485 216 L420 196 L392 160 Z" fill="#d7d9dc" />
                <path d="M515 220 L555 236 L582 270 L560 305 L520 292 L500 250 Z" fill="#d7d9dc" />
                <path d="M600 175 L655 170 L715 192 L735 226 L692 242 L630 230 L596 203 Z" fill="#d7d9dc" />
              </svg>
              {trafficSources.map((t) => (
                <button
                  key={t.city}
                  onClick={() => { setActiveTraffic(t); ping(`Traffic source: ${t.city}`) }}
                  title={`${t.city} (${t.share}%)`}
                  style={{
                    position: 'absolute',
                    left: `${t.x}%`,
                    top: `${t.y}%`,
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    border: '1px solid #fff',
                    background: '#111827',
                    boxShadow: activeTraffic.city === t.city ? '0 0 0 5px rgba(0,0,0,0.12)' : '0 0 0 2px rgba(0,0,0,0.08)',
                    transform: 'translate(-50%, -50%)',
                    cursor: 'pointer',
                  }}
                />
              ))}
              <div style={{ position: 'absolute', left: 8, bottom: 8, fontSize: 10, color: '#59606a', background: 'rgba(255,255,255,0.75)', border: '1px solid #d8d8d8', borderRadius: 5, padding: '3px 6px' }}>
                {activeTraffic.city} • {activeTraffic.share}% traffic
              </div>
            </div>
            <p style={{ marginTop: 8, fontSize: 11, color: '#3f454f' }}>Live traffic origin map • 50/50 US States Synced</p>
          </div>
        </div>
      </div>

      <footer className="card" style={{ borderRadius: 8, padding: '10px 12px', display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
        <span>Recruiter Intelligence © 2026</span>
        <div style={{ display: 'flex', gap: 14 }}>
          <button onClick={() => ping('System Status clicked')} style={{ background: 'transparent' }}>System Status</button>
          <button onClick={() => ping('Privacy Policy clicked')} style={{ background: 'transparent' }}>Privacy Policy</button>
          <button onClick={() => ping('Terms clicked')} style={{ background: 'transparent' }}>Terms of Service</button>
        </div>
      </footer>

      {toast && (
        <div style={{ position: 'fixed', right: 20, bottom: 20, background: '#17191d', color: '#fff', padding: '10px 12px', borderRadius: 8, fontSize: 12 }}>
          {toast}
        </div>
      )}
    </div>
  )
}
