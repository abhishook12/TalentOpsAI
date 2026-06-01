import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../services/api'

function Card({ title, icon, action, children, style }) {
  return (
    <div className="card" style={{ padding: 16, borderRadius: 14, display: 'flex', flexDirection: 'column', gap: 10, ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          {icon && <i className={`ti ${icon}`} style={{ color: 'var(--accent)', fontSize: 16 }} />}
          <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.01em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {title}
          </div>
        </div>
        {action}
      </div>
      <div style={{ minHeight: 0 }}>{children}</div>
    </div>
  )
}

function KPI({ label, value, sub, icon, tone = 'default' }) {
  const left = tone === 'good' ? '#22c55e' : tone === 'warn' ? '#f59e0b' : tone === 'bad' ? '#ef4444' : 'var(--card-border)'
  return (
    <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: '12px 14px', borderLeft: `3px solid ${left}` }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <i className={`ti ${icon}`} style={{ color: 'var(--text-muted)', fontSize: 15 }} />
          <div style={{ fontSize: 10.5, fontWeight: 800, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{label}</div>
        </div>
      </div>
      <div style={{ marginTop: 8, fontSize: 22, fontWeight: 900, color: 'var(--text-primary)' }}>{value ?? '—'}</div>
      {sub && <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [toast, setToast] = useState('')

  const { data: kpis, isLoading: kpisLoading, error: kpisError } = useQuery({
    queryKey: ['dashboard-kpis'],
    queryFn: async () => (await api.get('/analytics/dashboard')).data,
  })

  const { data: visits, isLoading: visitsLoading, error: visitsError } = useQuery({
    queryKey: ['dashboard-visits'],
    queryFn: async () => (await api.get('/analytics/visit-stats')).data,
  })

  const { data: topCompanies, isLoading: companiesLoading, error: companiesError } = useQuery({
    queryKey: ['dashboard-top-companies'],
    queryFn: async () => (await api.get('/analytics/companies-search', { params: { state: 'ALL', limit: 6, skip: 0, min_recruiters: 1 } })).data,
  })

  const { data: jobs, isLoading: jobsLoading, error: jobsError } = useQuery({
    queryKey: ['dashboard-upload-jobs'],
    queryFn: async () => (await api.get('/upload/jobs')).data,
  })

  const statBlocks = useMemo(() => {
    const r = kpis?.recruiters || {}
    const c = kpis?.companies || {}
    return [
      { label: 'Total Recruiters', icon: 'ti-users', value: typeof r.total === 'number' ? r.total.toLocaleString() : null, sub: 'From database', tone: (r.total || 0) > 0 ? 'good' : 'default' },
      { label: 'Companies', icon: 'ti-building', value: typeof c.total === 'number' ? c.total.toLocaleString() : null, sub: 'From database', tone: (c.total || 0) > 0 ? 'good' : 'default' },
      { label: 'Email Coverage', icon: 'ti-mail', value: typeof r.email_coverage_percent === 'number' ? `${r.email_coverage_percent}%` : null, sub: typeof r.with_email === 'number' ? `${r.with_email.toLocaleString()} with email` : null, tone: typeof r.email_coverage_percent === 'number' ? (r.email_coverage_percent >= 80 ? 'good' : r.email_coverage_percent >= 50 ? 'warn' : 'bad') : 'default' },
      { label: 'Needs Review', icon: 'ti-alert-circle', value: typeof r.needs_review === 'number' ? r.needs_review.toLocaleString() : null, sub: typeof r.needs_review_percent === 'number' ? `${r.needs_review_percent}% of recruiters` : null, tone: typeof r.needs_review === 'number' ? (r.needs_review === 0 ? 'good' : 'warn') : 'default' },
    ]
  }, [kpis])

  const showToast = (msg) => {
    setToast(msg)
    window.clearTimeout(showToast._t)
    showToast._t = window.setTimeout(() => setToast(''), 1600)
  }

  const topPages = Array.isArray(visits?.top_pages) ? visits.top_pages.slice(0, 6) : []
  const recentJobs = Array.isArray(jobs) ? [...jobs].sort((a, b) => new Date(b.started_at || 0) - new Date(a.started_at || 0)).slice(0, 6) : []

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 900, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>Recruiter Intelligence</h1>
          <div style={{ marginTop: 6, fontSize: 13, color: 'var(--text-muted)' }}>Operational overview using real database data. No demo content.</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-primary" onClick={() => navigate('/ai-search')} style={{ borderRadius: 12, padding: '10px 12px', fontWeight: 900 }}>
            <i className="ti ti-sparkles" /> Smart Search
          </button>
          <button
            onClick={() => showToast('Notifications: not implemented yet')}
            title="Notifications not implemented yet"
            disabled
            style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', color: 'var(--text-muted)', width: 36, height: 36, borderRadius: 12, cursor: 'not-allowed', opacity: 0.7 }}
          >
            <i className="ti ti-bell" />
          </button>
        </div>
      </div>

      {(kpisError || visitsError || companiesError || jobsError) && (
        <div style={{ padding: '10px 12px', borderRadius: 12, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#ef4444' }}>
          {getErrorMessage(kpisError || visitsError || companiesError || jobsError, 'Failed to load dashboard data')}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10 }}>
        {statBlocks.map((s) => (
          <KPI key={s.label} {...s} value={kpisLoading ? '…' : s.value} sub={kpisLoading ? 'Loading…' : s.sub} />
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.35fr 1fr 1fr', gap: 10, minHeight: 0 }}>
        <Card
          title="Top Companies (by recruiters)"
          icon="ti-building-community"
          action={
            <button onClick={() => navigate('/companies')} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12, fontWeight: 800 }}>
              View all <i className="ti ti-arrow-right" />
            </button>
          }
        >
          {companiesLoading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading…</div>
          ) : (Array.isArray(topCompanies) && topCompanies.length > 0) ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {topCompanies.map((c) => (
                <button
                  key={c.company_id}
                  onClick={() => navigate('/companies')}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', cursor: 'pointer', textAlign: 'left' }}
                  title="Open Company Directory"
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.company_name || 'Unnamed company'}</div>
                    <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.location || 'Not available'} • {c.state_abbr || '—'}</div>
                  </div>
                  <div style={{ fontFamily: 'var(--mono)', fontWeight: 900, color: 'var(--text-secondary)' }}>{(c.recruiter_count ?? 0).toLocaleString()} rec</div>
                </button>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              No Data Available. Add companies and link recruiters to see rankings.
            </div>
          )}
        </Card>

        <Card title="Recent Upload Jobs" icon="ti-cloud-upload">
          {jobsLoading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading…</div>
          ) : recentJobs.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {recentJobs.map((j) => (
                <div key={j.job_id} style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{j.file_name || `Job ${j.job_id}`}</div>
                    <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)' }}>{j.status || 'unknown'}</div>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
                    {j.started_at ? new Date(j.started_at).toLocaleDateString() : '—'}
                  </div>
                </div>
              ))}
              <button onClick={() => navigate('/upload')} style={{ background: 'var(--bg-hover)', border: '1px solid var(--card-border)', color: 'var(--text-secondary)', padding: '10px 12px', borderRadius: 12, cursor: 'pointer', fontWeight: 900 }}>
                Open ETL Intelligence Center <i className="ti ti-arrow-right" />
              </button>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              No Data Available. Run an upload to see import history here.
            </div>
          )}
        </Card>

        <Card title="Top Pages (visits)" icon="ti-chart-bar" action={<span className="badge badge-gray">Visits</span>}>
          {visitsLoading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading…</div>
          ) : topPages.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {topPages.map((p, idx) => (
                <div key={`${p.page}-${idx}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', borderRadius: 12, background: 'var(--panel-bg)', border: '1px solid var(--card-border)' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12, fontWeight: 800, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.page}</div>
                  <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--mono)', fontSize: 12 }}>{Number(p.visits || 0).toLocaleString()}</div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              No Data Available. Browse the app to generate visit tracking.
            </div>
          )}
        </Card>
      </div>

      {toast && (
        <div style={{ position: 'fixed', right: 18, bottom: 18, background: 'var(--card-bg)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', padding: '10px 12px', borderRadius: 12, fontSize: 12, boxShadow: 'var(--shadow)' }}>
          {toast}
        </div>
      )}
    </div>
  )
}

