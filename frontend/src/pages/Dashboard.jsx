import { useMemo, useState, useCallback, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useAuth } from '../context/AuthContext'
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
import USHeatmap from '../components/USHeatmap'
import { CompanyIdentity } from '../components/CompanyIdentity'
import { Skeleton, SkeletonRow } from '../components/ui/Skeleton'
import AnimatedNumber from '../components/ui/AnimatedNumber'

const REFRESH_INTERVAL = 60_000 // 60 seconds

function formatCount(value) {
  return typeof value === 'number' ? value.toLocaleString() : '—'
}

function percentText(value) {
  return typeof value === 'number' ? `${value}%` : '—'
}

function formatTime(date) {
  if (!date) return '—'
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function useCachedQuery(key, fetcher, options) {
  return useQuery({
    queryKey: [key],
    queryFn: async () => {
      const data = await fetcher()
      try { localStorage.setItem(`dashboard_${key}`, JSON.stringify(data)) } catch { /* ignore */ }
      return data
    },
    initialData: () => {
      try { 
        const cached = localStorage.getItem(`dashboard_${key}`)
        return cached ? JSON.parse(cached) : undefined 
      } catch { return undefined }
    },
    ...options
  })
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
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

  const { data: dashboardData, isLoading: dashLoading, error: kpisError, isFetching: dashFetching } = useCachedQuery(
    'dashboard-kpis',
    async () => {
      const res = (await api.get('/analytics/dashboard')).data
      setLastUpdated(new Date())
      setRefreshError(null)
      return res
    },
    sharedQueryOpts
  )

  const { data: dataQuality, isLoading: dqLoading, error: dqError, isFetching: dqFetching } = useCachedQuery(
    'dashboard-data-quality',
    async () => (await api.get('/analytics/data-quality')).data,
    sharedQueryOpts
  )

  const { data: ingestionData, isLoading: ingestionLoading, isFetching: ingestionFetching } = useCachedQuery(
    'dashboard-ingestion-summary',
    async () => (await api.get('/analytics/scraper-ingestion-summary')).data,
    sharedQueryOpts
  )

  const { data: visits, isLoading: visitsLoading, error: visitsError, isFetching: visitsFetching } = useCachedQuery(
    'dashboard-visits',
    async () => (await api.get('/analytics/visit-stats')).data,
    sharedQueryOpts
  )

  const { data: topCompanies, isLoading: companiesLoading, error: companiesError, isFetching: companiesFetching } = useCachedQuery(
    'dashboard-top-companies',
    async () => (await api.get('/analytics/companies-search', { params: { state: 'ALL', limit: 6, skip: 0, min_recruiters: 1 } })).data,
    sharedQueryOpts
  )

  const isFetchingAny = dashFetching || dqFetching || visitsFetching || companiesFetching || ingestionFetching

  const handleRefresh = useCallback(async () => {
    if (isManualRefreshing.current || isFetchingAny) return
    isManualRefreshing.current = true
    setRefreshError(null)
    try {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['dashboard-kpis'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-data-quality'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-ingestion-summary'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-visits'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard-top-companies'] }),
        queryClient.invalidateQueries({ queryKey: ['recruiters-by-state'] }),
      ])
      setLastUpdated(new Date())
    } catch (err) {
      setRefreshError(getErrorMessage(err, 'Refresh failed. Previous data preserved.'))
    } finally {
      isManualRefreshing.current = false
    }
  }, [queryClient, isFetchingAny])

  const topPages = Array.isArray(visits?.top_pages) ? visits.top_pages.slice(0, 5) : []

  const totalPages = Number(visits?.total_visits || 0)
  const today = Number(visits?.today || 0)
  const yesterday = Number(visits?.yesterday || 0)

  const metrics = useMemo(() => {
    const newPeopleToday = ingestionData?.metrics_today?.new_people_created || 0
    const enrichedToday = ingestionData?.metrics_today?.existing_people_enriched || 0
    const needsReview = dataQuality?.needs_review_count || 0

    let totalPeople = dashboardData?.recruiters?.total || dataQuality?.total_recruiters || 0
    if (newPeopleToday > 0 && totalPeople > 0) {
      totalPeople = Math.max(totalPeople, totalPeople + newPeopleToday)
    }

    return [
      {
        label: 'Total Talent Profiles',
        value: <AnimatedNumber value={totalPeople} />,
        sublabel: newPeopleToday > 0 ? `+${newPeopleToday} added today` : 'Verified candidate records',
        icon: 'ti-users',
        tone: 'neutral',
      },
      {
        label: 'Added & Enriched Today',
        value: `+${newPeopleToday + enrichedToday}`,
        sublabel: `${ingestionData?.metrics_today?.fields_added || 0} fields updated today`,
        icon: 'ti-sparkles',
        tone: 'success',
      },
      {
        label: 'Records Needing Review',
        value: <AnimatedNumber value={needsReview} />,
        sublabel: needsReview === 0 ? 'Review queue clear' : `${needsReview} records flagged for verification`,
        icon: 'ti-alert-triangle',
        tone: needsReview > 0 ? 'warning' : 'neutral',
      },
    ]
  }, [dataQuality, ingestionData, dashboardData])

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
  ]

  const hasCoreData = Boolean(dashboardData || dataQuality || ingestionData)
  const isFatalError = !hasCoreData && (kpisError || dqError)

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14, minHeight: 0 }}>
      <SectionHeader
        title="Operations"
        subtitle="Talent database status, pipeline activity, and data health."
        action={(
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginRight: 4 }}>
              {isFetchingAny && (
                <span style={{
                  display: 'inline-block', width: 12, height: 12, border: '2px solid var(--text-muted)',
                  borderTopColor: 'var(--text-primary)', borderRadius: '50%',
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
            <PrimaryButton onClick={() => navigate({ to: '/search' })}>
              <i className="ti ti-search" /> Open Search
            </PrimaryButton>
          </div>
        )}
      />

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {/* 🌐 Autonomous WebHarvest Discovery Banner (Admin-Only) */}
      {isAdmin && (
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(20, 184, 166, 0.08) 0%, rgba(13, 148, 136, 0.03) 100%)',
            border: '1px solid rgba(20, 184, 166, 0.25)',
            borderRadius: 8,
            padding: '12px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer'
          }}
          onClick={() => navigate({ to: '/admin/web-harvest' })}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>🌐</span>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                  WebHarvest Autonomous Discovery Engine
                </span>
                <span style={{
                  fontSize: 10, fontWeight: 700,
                  background: 'rgba(34, 197, 94, 0.15)',
                  color: '#4ade80',
                  padding: '2px 8px', borderRadius: 12,
                  border: '1px solid rgba(34, 197, 94, 0.3)'
                }}>
                  ● 24/7 ADMIN BACKGROUND JOB ACTIVE
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                Server-side crawler discovering & harvesting verified talent intelligence directly into the master database.
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Engine Status</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#14b8a6' }}>Autonomous Background Crawl</div>
            </div>
            <button style={{
              background: 'rgba(20, 184, 166, 0.15)',
              border: '1px solid rgba(20, 184, 166, 0.3)',
              color: '#14b8a6',
              borderRadius: 6,
              padding: '6px 12px',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer'
            }}>
              View Admin Harvesting Center →
            </button>
          </div>
        </div>
      )}

      {refreshError && !hasCoreData && (
        <ShellCard style={{ padding: 14, borderColor: 'rgba(196,58,50,0.2)', background: 'rgba(196,58,50,0.05)' }}>
          <div style={{ color: 'var(--danger)', fontSize: 13, fontWeight: 700 }}>{refreshError}</div>
        </ShellCard>
      )}

      {isFatalError && (
        <ShellCard style={{ padding: 14, borderColor: 'rgba(196,58,50,0.2)', background: 'rgba(196,58,50,0.05)' }}>
          <div style={{ color: 'var(--danger)', fontSize: 13, fontWeight: 700 }}>{getErrorMessage(kpisError || dqError, 'Failed to load dashboard data')}</div>
        </ShellCard>
      )}

      {dataQuality?.total_recruiters === 0 ? (
        <div style={{
          padding: 60,
          borderRadius: 6,
          border: '1px dashed var(--card-border)',
          background: 'var(--panel-bg)',
          color: 'var(--text-primary)',
          textAlign: 'center',
          marginTop: 20
        }}>
          <div style={{ width: 64, height: 64, borderRadius: 32, background: 'var(--text-primary)', display: 'inline-grid', placeItems: 'center', color: 'var(--main-bg)', marginBottom: 20 }}>
            <i className="ti ti-database-import" style={{ fontSize: 32 }} />
          </div>
          <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 12 }}>Welcome to TalentOps</h2>
          <p style={{ fontSize: 16, color: 'var(--text-secondary)', maxWidth: 500, margin: '0 auto 32px' }}>
            {isAdmin 
              ? 'Your operational dashboard is completely isolated. To see insights, activity, and analytics, you need to import your first dataset of recruiters or companies.'
              : 'Your operational dashboard is completely isolated. Awaiting an administrator to import the initial dataset before analytics and insights become available.'}
          </p>
          {isAdmin && (
            <PrimaryButton onClick={() => navigate({ to: '/admin' })} style={{ padding: '14px 28px', fontSize: 16 }}>
              <i className="ti ti-upload" /> Import Data
            </PrimaryButton>
          )}
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
            {metrics.map((metric) => (
              <MetricCard
                key={metric.label}
                {...metric}
                value={dqLoading && !dataQuality ? <Skeleton width="60%" height="28px" /> : metric.value}
                sublabel={dqLoading && !dataQuality ? <Skeleton width="40%" height="14px" /> : metric.sublabel}
              />
            ))}
          </div>

          <div style={{ marginTop: '4px', marginBottom: '4px' }}>
            <USHeatmap />
          </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.35fr 0.95fr', gap: 12, minHeight: 0 }}>
        <ShellCard style={{ padding: 18, minHeight: 0 }}>
          <SectionHeader
            title="Data Integrity Health"
            subtitle="Quality metrics, platform signals, and operational alerts from the live backend."
            action={<Badge tone={dataQuality?.needs_review_count > 0 ? 'warning' : 'success'}>Overall: {dataQuality?.needs_review_count > 0 ? 'Attention' : 'Excellent'}</Badge>}
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
            title="System Alerts"
            subtitle="Active system alerts and data validation notifications."
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
            title="Top Companies"
            subtitle="Companies ranked by recruiter coverage."
          />
          {companiesLoading && !topCompanies ? (
            <SkeletonRow rows={4} gap={10} height={52} />
          ) : Array.isArray(topCompanies) && topCompanies.length > 0 ? (
            <div style={{ display: 'grid', gap: 10 }}>
              {topCompanies.map((company, index) => (
                <button
                  key={company.company_id}
                  onClick={() => navigate({ to: '/companies' })}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 12,
                    alignItems: 'center',
                    padding: '12px 14px',
                    borderRadius: 6,
                    border: '1px solid var(--card-border)',
                    background: 'var(--bg-surface)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16, flex: 1, minWidth: 0 }}>
                    <div style={{ 
                      width: 28, 
                      height: 28, 
                      borderRadius: 6, 
                      border: '1px solid var(--card-border)',
                      background: 'var(--bg-base)',
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      fontSize: 12,
                      fontWeight: 700,
                      color: 'var(--text-secondary)',
                      flexShrink: 0
                    }}>
                      {index + 1}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <CompanyIdentity 
                        domain={company.logo_domain || company.website || company.email_pattern} 
                        name={company.company_name} 
                        subtitle={company.website || company.email_pattern || 'Domain unlisted'}
                        interactive={false}
                        style={{ padding: 0 }}
                      />
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
              action={<GhostButton onClick={() => navigate({ to: '/companies' })}>Open companies</GhostButton>}
            />
          )}
        </ShellCard>

        <ShellCard style={{ padding: 18, minHeight: 0 }}>
          <SectionHeader
            title="Top Pages"
            subtitle="Page visitation distribution."
            action={<Badge tone="neutral">{visitsLoading && !visits ? <Skeleton width="50px" height="12px" /> : `${formatCount(totalPages)} views`}</Badge>}
          />
          {visitsLoading && !visits ? (
             <SkeletonRow rows={4} gap={10} height={40} />
          ) : topPages.length ? (
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
      </>
      )}

    </div>
  )
}
