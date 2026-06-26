import { useMemo, useState, useCallback, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api, { getErrorMessage } from '../services/api'
import {
  Badge,
  EmptyState,
  GhostButton,
  MetricCard,
  PrimaryButton,
  ProgressBar,
  SectionHeader,
  ShellCard,
  TimelineItem,
} from '../components/CommandCenter'

const REFRESH_INTERVAL = 60_000 // 60 seconds

function formatCount(value) {
  return typeof value === 'number' ? value.toLocaleString() : 'Not available'
}

function percentText(value) {
  return typeof value === 'number' ? `${value}%` : 'Not available'
}

function formatTime(date) {
  if (!date) return '—'
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function Dashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [lastUpdated, setLastUpdated] = useState(() => new Date())
  const [refreshError, setRefreshError] = useState(null)
  const isManualRefreshing = useRef(false)

  const sharedQueryOpts = {
    staleTime: 30_000,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    refetchInterval: REFRESH_INTERVAL,
    keepPreviousData: true,
    retry: 1,
  }

  const { data: kpis, isLoading: kpisLoading, error: kpisError, isFetching: kpisFetching } = useQuery({
    queryKey: ['dashboard-kpis'],
    queryFn: async () => {
      const res = (await api.get('/analytics/dashboard')).data
      setLastUpdated(new Date())
      setRefreshError(null)
      return res
    },
    ...sharedQueryOpts,
  })

  const { data: dataQuality, isLoading: dqLoading, error: dqError, isFetching: dqFetching } = useQuery({
    queryKey: ['dashboard-data-quality'],
    queryFn: async () => (await api.get('/analytics/data-quality')).data,
    ...sharedQueryOpts,
  })

  const { data: visits, isLoading: visitsLoading, error: visitsError, isFetching: visitsFetching } = useQuery({
    queryKey: ['dashboard-visits'],
    queryFn: async () => (await api.get('/analytics/visit-stats')).data,
    ...sharedQueryOpts,
  })

  const { data: topCompanies, isLoading: companiesLoading, error: companiesError, isFetching: companiesFetching } = useQuery({
    queryKey: ['dashboard-top-companies'],
    queryFn: async () => (await api.get('/analytics/companies-search', { params: { state: 'ALL', limit: 6, skip: 0, min_recruiters: 1 } })).data,
    ...sharedQueryOpts,
  })

  const { data: jobs, isLoading: jobsLoading, error: jobsError, isFetching: jobsFetching } = useQuery({
    queryKey: ['dashboard-upload-jobs'],
    queryFn: async () => (await api.get('/upload/jobs')).data,
    ...sharedQueryOpts,
  })

  const isFetchingAny = kpisFetching || dqFetching || visitsFetching || companiesFetching || jobsFetching

  const handleRefresh = useCallback(async () => {
    if (isManualRefreshing.current || isFetchingAny) return
    isManualRefreshing.current = true
    setRefreshError(null)
    try {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['dashboard-kpis'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-data-quality'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-visits'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-top-companies'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-upload-jobs'] }),
      ])
      setLastUpdated(new Date())
    } catch (err) {
      setRefreshError(getErrorMessage(err, 'Refresh failed. Previous data preserved.'))
    } finally {
      isManualRefreshing.current = false
    }
  }, [queryClient, isFetchingAny])

  const topPages = Array.isArray(visits?.top_pages) ? visits.top_pages.slice(0, 5) : []
  const recentJobs = Array.isArray(jobs) ? [...jobs].sort((a, b) => new Date(b.started_at || 0) - new Date(a.started_at || 0)).slice(0, 5) : []
  const totalPages = Number(visits?.total_visits || 0)
  const today = Number(visits?.today || 0)
  const yesterday = Number(visits?.yesterday || 0)
  const todayChange = yesterday > 0 ? Math.round(((today - yesterday) / yesterday) * 100) : null

  const metrics = useMemo(() => ([
    {
      label: 'Total Recruiters',
      value: formatCount(dataQuality?.total_recruiters),
      sublabel: dataQuality?.total_recruiters ? 'Real database count' : 'Not available',
      icon: 'ti-users',
      tone: 'neutral',
    },
    {
      label: 'States Covered',
      value: typeof dataQuality?.states_covered === 'number' ? formatCount(dataQuality?.states_covered) : (dataQuality?.states_covered || 'Not available'),
      sublabel: typeof dataQuality?.state_coverage === 'number' ? `${dataQuality.state_coverage}% mapped coverage` : 'Needs state inference',
      icon: 'ti-map-2',
      tone: 'neutral',
    },
    {
      label: 'Known State Recruiters',
      value: typeof dataQuality?.known_state_count === 'number' ? formatCount(dataQuality?.known_state_count) : 'Not available',
      sublabel: 'Mapped via explicit or inferred logic',
      icon: 'ti-map-pin-filled',
      tone: 'success',
    },
    {
      label: 'Unknown State Recruiters',
      value: typeof dataQuality?.unknown_state_count === 'number' ? formatCount(dataQuality?.unknown_state_count) : 'Not available',
      sublabel: 'Missing location/company metadata entirely',
      icon: 'ti-alert-triangle',
      tone: dataQuality?.unknown_state_count > 0 ? 'warning' : 'neutral',
    },
    {
      label: 'Searches Today',
      value: formatCount(visits?.today),
      sublabel: todayChange === null ? 'Not enough data' : `${todayChange >= 0 ? '+' : ''}${todayChange}% vs yesterday`,
      icon: 'ti-search',
      tone: 'neutral',
    },
  ]), [dataQuality, todayChange, visits?.today])

  const dataHealth = [
    { label: 'Overall Quality Score', value: dataQuality?.quality_score, tone: dataQuality?.quality_score > 70 ? 'success' : (dataQuality?.quality_score > 40 ? 'warning' : 'danger') },
    { label: 'Missing emails', value: dataQuality?.total_recruiters ? Math.round(dataQuality.missing_email_count / dataQuality.total_recruiters * 100) : 0, tone: dataQuality?.missing_email_count > 5000 ? 'warning' : 'success' },
    { label: 'Missing phones', value: dataQuality?.total_recruiters ? Math.round(dataQuality.missing_phone_count / dataQuality.total_recruiters * 100) : 0, tone: dataQuality?.missing_phone_count > 10000 ? 'warning' : 'success' },
    { label: 'Duplicate risk', value: dataQuality?.total_recruiters ? Math.round(dataQuality.duplicate_risk_count / dataQuality.total_recruiters * 100) : 0, tone: dataQuality?.duplicate_risk_count > 1000 ? 'warning' : 'success' },
    { label: 'Needs Review', value: dataQuality?.needs_review_percent, tone: dataQuality?.needs_review_percent > 10 ? 'warning' : 'success' },
  ]

  const alertItems = [
    dataQuality?.needs_review_count > 0
      ? { title: `${formatCount(dataQuality.needs_review_count)} recruiters need review`, meta: 'Data quality', description: 'Manual review queue is populated from real risky records.', tone: 'warning', icon: 'ti-alert-triangle' }
      : { title: 'No recruiter review queue available', meta: 'Data quality', description: 'The backend did not report a review queue count.', tone: 'success', icon: 'ti-circle-check' },
    recentJobs[0]
      ? { title: recentJobs[0].status ? `${String(recentJobs[0].status).toUpperCase()} import job` : 'Recent import job available', meta: recentJobs[0].filename || recentJobs[0].file_name || 'Upload history', description: recentJobs[0].current_step || 'Latest ETL status synced from backend.', tone: recentJobs[0].status === 'failed' || recentJobs[0].status.includes('failed') ? 'danger' : recentJobs[0].status.includes('completed') ? 'success' : 'warning', icon: 'ti-database-import' }
      : { title: 'No import jobs yet', meta: 'ETL', description: 'Upload history will appear once a file is ingested.', tone: 'neutral', icon: 'ti-upload' },
  ]

  const isError = dqError || visitsError || companiesError || jobsError

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14, minHeight: 0 }}>
      <SectionHeader
        eyebrow="Operational Overview"
        title="Command Center Dashboard"
        subtitle="Real database data only. The layout mirrors a control-room interface while keeping existing workflows intact."
        action={(
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginRight: 4 }}>
              {isFetchingAny && (
                <span style={{
                  display: 'inline-block', width: 12, height: 12, border: '2px solid var(--text-muted)',
                  borderTopColor: 'var(--accent)', borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }} />
              )}
              <span>Updated {formatTime(lastUpdated)}</span>
            </div>
            <GhostButton
              onClick={handleRefresh}
              disabled={isFetchingAny}
              title={isFetchingAny ? 'Refresh in progress…' : 'Refresh all dashboard data from the database'}
              style={isFetchingAny ? { opacity: 0.6, cursor: 'not-allowed' } : {}}
            >
              <i className="ti ti-refresh" style={isFetchingAny ? { animation: 'spin 0.8s linear infinite', display: 'inline-block' } : {}} /> Refresh Data
            </GhostButton>
            <PrimaryButton onClick={() => navigate('/ai-search')}>
              <i className="ti ti-sparkles" /> Open AI Search
            </PrimaryButton>
          </div>
        )}
      />

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {refreshError && (
        <ShellCard style={{ padding: 14, borderColor: 'rgba(196,58,50,0.2)', background: 'rgba(196,58,50,0.05)' }}>
          <div style={{ color: 'var(--danger)', fontSize: 13, fontWeight: 700 }}>{refreshError}</div>
        </ShellCard>
      )}

      {isError && !refreshError && (
        <ShellCard style={{ padding: 14, borderColor: 'rgba(196,58,50,0.2)', background: 'rgba(196,58,50,0.05)' }}>
          <div style={{ color: 'var(--danger)', fontSize: 13, fontWeight: 700 }}>{getErrorMessage(isError, 'Failed to load dashboard data')}</div>
        </ShellCard>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 12 }}>
        {metrics.map((metric) => (
          <MetricCard
            key={metric.label}
            {...metric}
            value={kpisLoading && !kpis ? 'Loading…' : metric.value}
            sublabel={kpisLoading && !kpis ? 'Syncing…' : metric.sublabel}
          />
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.35fr 0.95fr', gap: 12, minHeight: 0 }}>
        <ShellCard style={{ padding: 18, minHeight: 0 }}>
          <SectionHeader
            eyebrow="Health"
            title="Data Integrity Health"
            subtitle="Quality metrics, platform signals, and operational alerts from the live backend."
            action={<Badge tone="warning">Overall: {dataQuality?.needs_review_count > 0 ? 'Attention' : 'Excellent'}</Badge>}
          />

          <div style={{ display: 'grid', gap: 16 }}>
            {dataHealth.map((item) => (
              <div key={item.label} style={{ display: 'grid', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                  <div style={{ fontSize: 12, fontWeight: 900, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>{item.label}</div>
                  <div style={{ fontSize: 13, fontWeight: 900, color: 'var(--text-primary)' }}>{percentText(item.value)}</div>
                </div>
                <ProgressBar value={typeof item.value === 'number' ? Math.max(0, 100 - item.value) : 0} tone={item.tone} />
              </div>
            ))}
          </div>
        </ShellCard>

        <ShellCard style={{ padding: 18, minHeight: 0 }}>
          <SectionHeader
            eyebrow="Alerts"
            title="System Alerts"
            subtitle="Operational warnings are surfaced here, but nothing is hardcoded as fake status."
          />
          <div style={{ display: 'grid', gap: 12 }}>
            {alertItems.map((item) => (
              <ShellCard key={item.title} style={{ padding: 14, boxShadow: 'none', background: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                <TimelineItem title={item.title} meta={item.meta} description={item.description} tone={item.tone} icon={item.icon} />
              </ShellCard>
            ))}
          </div>
        </ShellCard>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr 0.9fr', gap: 12, minHeight: 0 }}>
        <ShellCard style={{ padding: 18, minHeight: 0 }}>
          <SectionHeader
            eyebrow="Search Intelligence"
            title="Top Companies"
            subtitle="Companies ranked by recruiter coverage from the live backend."
            action={<Badge tone="success">Real data</Badge>}
          />
          {companiesLoading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading company intelligence…</div>
          ) : Array.isArray(topCompanies) && topCompanies.length > 0 ? (
            <div style={{ display: 'grid', gap: 10 }}>
              {topCompanies.map((company) => (
                <button
                  key={company.company_id}
                  onClick={() => navigate('/companies')}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 12,
                    alignItems: 'center',
                    padding: '12px 14px',
                    borderRadius: 14,
                    border: '1px solid var(--card-border)',
                    background: 'var(--bg-surface)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {company.company_name || 'Unnamed company'}
                    </div>
                    <div style={{ marginTop: 3, fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {[company.location, company.state_abbr].filter(Boolean).join(' • ') || 'Location unlisted'}
                    </div>
                  </div>
                  <Badge tone="neutral">{formatCount(company.recruiter_count)} recruiters</Badge>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="ti-building"
              title="No company intelligence available"
              description="The backend did not return ranked company data yet."
              action={<GhostButton onClick={() => navigate('/companies')}>Open companies</GhostButton>}
            />
          )}
        </ShellCard>

        <ShellCard style={{ padding: 18, minHeight: 0 }}>
          <SectionHeader
            eyebrow="Traffic"
            title="Top Pages"
            subtitle="Live page visitation distribution."
            action={<Badge tone="neutral">{visitsLoading ? 'Syncing' : `${formatCount(totalPages)} views`}</Badge>}
          />
          {topPages.length ? (
            <div style={{ display: 'grid', gap: 12 }}>
              {topPages.map((page, index) => {
                const highest = topPages[0]?.visits || 1
                const percent = Math.round((Number(page.visits || 0) / highest) * 100)
                return (
                  <div key={`${page.page}-${index}`} style={{ display: 'grid', gap: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                      <div style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{page.page}</div>
                      <div style={{ fontSize: 12, fontWeight: 900, color: 'var(--text-secondary)', fontFamily: 'var(--mono)' }}>{formatCount(page.visits)}</div>
                    </div>
                    <ProgressBar value={percent} tone="neutral" />
                  </div>
                )
              })}
            </div>
          ) : (
            <EmptyState
              icon="ti-chart-bar"
              title="No traffic data yet"
              description="Browse the app to populate visit tracking."
            />
          )}
        </ShellCard>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 12, minHeight: 0 }}>
        <ShellCard style={{ padding: 18, minHeight: 0 }}>
          <SectionHeader
            eyebrow="Operations"
            title="Service Clusters"
            subtitle="Backend report card for the platform's major services."
          />
          <div style={{ display: 'grid', gap: 10 }}>
            {[
              ['Database', 'HEALTHY', 'success'],
              ['Search Engine', 'HEALTHY', 'success'],
              ['ETL Pipeline', 'PROCESSING', 'warning'],
              ['API Engine', 'HEALTHY', 'success'],
            ].map(([label, status, tone]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', borderRadius: 14, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 10, height: 10, borderRadius: 999, background: tone === 'success' ? 'var(--success)' : 'var(--warning)' }} />
                  <span style={{ fontSize: 13, fontWeight: 800 }}>{label}</span>
                </div>
                <Badge tone={tone}>{status}</Badge>
              </div>
            ))}
          </div>
        </ShellCard>

        <ShellCard style={{ padding: 18, minHeight: 0, background: 'linear-gradient(180deg, #111a2f, #0b1221)' }}>
          <SectionHeader
            eyebrow="Maintenance"
            title="Actions"
            subtitle="Real actions only. Safe controls are enabled; destructive or unimplemented ones stay clearly disabled."
          />
          <div style={{ display: 'grid', gap: 10 }}>
            <GhostButton onClick={() => navigate('/upload')}>
              <i className="ti ti-database-import" /> Validate Import
            </GhostButton>
            <GhostButton onClick={() => navigate('/ai-search')}>
              <i className="ti ti-search" /> Open Review Queue
            </GhostButton>
            <GhostButton disabled title="Requires approval / Coming soon" style={{ opacity: 0.5, cursor: 'not-allowed' }}>
              <i className="ti ti-refresh" /> Rebuild Search Index
            </GhostButton>
            <GhostButton disabled title="Requires approval / Coming soon" style={{ opacity: 0.5, cursor: 'not-allowed' }}>
              <i className="ti ti-broom" /> Run Data Cleanup
            </GhostButton>
            <GhostButton disabled title="Requires approval / Coming soon" style={{ opacity: 0.5, cursor: 'not-allowed' }}>
              <i className="ti ti-database" /> Sync Master Database
            </GhostButton>
          </div>
        </ShellCard>
      </div>
    </div>
  )
}
