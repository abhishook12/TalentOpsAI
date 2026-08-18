import React, { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'
import { 
  Activity, Database, CheckCircle, AlertTriangle, XCircle, Search, 
  ShieldAlert, Cpu, Play, Download, RefreshCw, Wrench, Sparkles, Filter, Check
} from 'lucide-react'
import toast from 'react-hot-toast'

export default function DataQualityCenter() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  const [anomalies, setAnomalies] = useState([])
  const [loadingAnomalies, setLoadingAnomalies] = useState(false)
  const [filterType, setFilterType] = useState('all')
  const [anomalyPage, setAnomalyPage] = useState(1)
  const [totalAnomalies, setTotalAnomalies] = useState(0)
  
  const [scanning, setScanning] = useState(false)
  const [repairingId, setRepairingId] = useState(null)

  const fetchDashboardData = useCallback(async () => {
    try {
      const res = await api.get('/sentinel/dashboard')
      setData(res.data)
      setError(null)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load Data Quality stats')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchAnomalies = useCallback(async (type, page = 1) => {
    setLoadingAnomalies(true)
    try {
      const limit = 10
      const offset = (page - 1) * limit
      const res = await api.get(`/sentinel/anomalies?filter_type=${type}&limit=${limit}&offset=${offset}`)
      setAnomalies(res.data.records || [])
      setTotalAnomalies(res.data.total_anomalies || 0)
    } catch (err) {
      console.error('Failed to fetch anomalies', err)
    } finally {
      setLoadingAnomalies(false)
    }
  }, [])

  useEffect(() => {
    fetchDashboardData()
    fetchAnomalies(filterType, anomalyPage)
    const interval = setInterval(fetchDashboardData, 6000)
    return () => clearInterval(interval)
  }, [fetchDashboardData, fetchAnomalies, filterType, anomalyPage])

  const handleRunScan = async () => {
    setScanning(true)
    const toastId = toast.loading('Running Sentinel multi-signal quality scan and auto-repair...')
    try {
      const res = await api.post('/sentinel/scan-and-repair', { limit: 500, focus_area: filterType })
      toast.success(res.data.message || 'Scan completed successfully!', { id: toastId })
      await Promise.all([fetchDashboardData(), fetchAnomalies(filterType, anomalyPage)])
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || 'Failed to execute repair scan', { id: toastId })
    } finally {
      setScanning(false)
    }
  }

  const handleQuickRepair = async (recruiterId) => {
    setRepairingId(recruiterId)
    const toastId = toast.loading(`Repairing profile #${recruiterId}...`)
    try {
      const res = await api.post(`/sentinel/quick-repair/${recruiterId}`)
      toast.success(`Profile #${recruiterId} repaired! Score: ${res.data.completeness_score}%`, { id: toastId })
      setAnomalies(prev => prev.filter(r => r.recruiter_id !== recruiterId))
      setTotalAnomalies(prev => Math.max(0, prev - 1))
      fetchDashboardData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || 'Quick repair failed', { id: toastId })
    } finally {
      setRepairingId(null)
    }
  }

  const handleExportReport = async () => {
    const toastId = toast.loading('Generating Forensic Data Quality Report...')
    try {
      const res = await api.get('/sentinel/quality-report')
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `TalentOps_Data_Quality_Report_${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('Report downloaded successfully!', { id: toastId })
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || 'Failed to download report', { id: toastId })
    }
  }

  if (loading && !data) {
    return (
      <div style={{ padding: '3rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'center', height: '60vh' }}>
        <RefreshCw className="animate-spin" size={24} color="var(--brand)" />
        <span style={{ fontSize: 16, fontWeight: 500 }}>Initializing Data Quality Intelligence Engine...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '3rem', color: 'var(--danger)', maxWidth: 600, margin: '40px auto', textAlign: 'center' }}>
        <ShieldAlert size={56} style={{ margin: '0 auto 1.5rem', color: 'var(--danger)' }} />
        <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, color: 'var(--text-primary)' }}>Data Quality Offline</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>{error}</p>
        <button onClick={fetchDashboardData} className="cc-primary-button" style={{ margin: '0 auto', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <RefreshCw size={16} /> Retry Connection
        </button>
      </div>
    )
  }

  const {
    status,
    total_recruiters = 0,
    total_companies = 0,
    unknown_companies = 0,
    missing_emails = 0,
    missing_phones = 0,
    missing_linkedin = 0,
    profiles_below_50 = 0,
    profiles_above_90 = 0,
    avg_completeness = 0,
    health_score = 0,
    email_coverage_pct = 0,
    phone_coverage_pct = 0,
    state_coverage_pct = 0,
    company_coverage_pct = 0,
    linkedin_coverage_pct = 0,
    needs_review_count = 0,
    current_company_name = 'Continuous Monitor',
    current_state = 'All States'
  } = data || {}

  const healthColor = health_score >= 90 ? '#10B981' : health_score >= 70 ? '#F59E0B' : '#EF4444'
  const grade = health_score >= 95 ? 'A+' : health_score >= 90 ? 'A' : health_score >= 80 ? 'B' : health_score >= 70 ? 'C' : 'D'

  return (
    <div style={{
      padding: '2rem 2.5rem',
      maxWidth: '1500px',
      margin: '0 auto',
      animation: 'ccFadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: 20 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 6 }}>
            Security & Governance
          </div>
          <h1 style={{ margin: '0 0 0.5rem 0', fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <Activity color="var(--brand)" size={28} />
            Enterprise Data Quality Center
          </h1>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 14, maxWidth: 650, lineHeight: 1.5 }}>
            Autonomous vulnerability scanning, multi-signal normalization, anomaly quarantining, and data hygiene auditing across {total_recruiters.toLocaleString()} recruiter records.
          </p>
        </div>

        {/* Action Controls & Health Score */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <button 
            onClick={handleRunScan}
            disabled={scanning}
            className="cc-primary-button"
            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', fontSize: 13, fontWeight: 600 }}
          >
            {scanning ? <RefreshCw className="animate-spin" size={16} /> : <Sparkles size={16} />}
            {scanning ? 'Scanning & Repairing...' : 'Run Sentinel Scan'}
          </button>

          <button 
            onClick={handleExportReport}
            className="cc-ghost-button"
            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', fontSize: 13, fontWeight: 600 }}
          >
            <Download size={16} />
            Export Audit Report
          </button>

          <div style={{ 
            background: 'var(--panel-bg)', 
            padding: '10px 20px', 
            borderRadius: 10, 
            display: 'flex', 
            alignItems: 'center', 
            gap: 16, 
            border: `1px solid var(--card-border)`,
            boxShadow: 'var(--shadow)'
          }}>
            <div>
              <div style={{ fontSize: 10, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.08em', fontWeight: 700, marginBottom: 2 }}>
                Database Health
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 24, fontWeight: 800, color: healthColor, lineHeight: 1 }}>{health_score}%</span>
                <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: `${healthColor}20`, color: healthColor }}>
                  GRADE {grade}
                </span>
              </div>
            </div>
            <Database size={32} color={healthColor} opacity={0.8} />
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <MetricCard label="Total Profiles" value={total_recruiters} icon={Database} color="var(--brand)" subtitle="Unified DuckDB store" />
        <MetricCard label="Companies Mapped" value={total_companies} icon={CheckCircle} color="#10B981" subtitle={`${company_coverage_pct}% resolved`} />
        <MetricCard label="Deliverable Emails" value={total_recruiters - missing_emails} icon={CheckCircle} color="#10B981" subtitle={`${email_coverage_pct}% coverage`} />
        <MetricCard label="Pristine Records (>90%)" value={profiles_above_90} icon={CheckCircle} color="#10B981" subtitle="Production ready" />
        <MetricCard label="Sub-50% Quality" value={profiles_below_50} icon={XCircle} color="#EF4444" subtitle="Needs enrichment" />
        <MetricCard label="Needs Review Flags" value={needs_review_count} icon={AlertTriangle} color="#F59E0B" subtitle="Actionable items" />
      </div>

      {/* Field Coverage & Diagnostics Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1.5rem', marginBottom: '2.5rem' }}>
        
        {/* Left: Field-Level Completeness Bars */}
        <div className="card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>Field-Level Data Coverage</h3>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>Multi-attribute completeness across all records</p>
            </div>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Avg: {avg_completeness}%</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <CoverageProgressBar label="State Postal Resolution" pct={state_coverage_pct} color="#10B981" detail="421k resolved" />
            <CoverageProgressBar label="Company Entity Linkage" pct={company_coverage_pct} color="#10B981" detail={`${(total_recruiters - unknown_companies).toLocaleString()} linked`} />
            <CoverageProgressBar label="Corporate & Personal Email" pct={email_coverage_pct} color={email_coverage_pct >= 80 ? '#10B981' : '#F59E0B'} detail={`${(total_recruiters - missing_emails).toLocaleString()} deliverable`} />
            <CoverageProgressBar label="LinkedIn Identity" pct={linkedin_coverage_pct} color="#0078D4" detail={`${(total_recruiters - missing_linkedin).toLocaleString()} verified`} />
            <CoverageProgressBar label="Direct Phone Line" pct={phone_coverage_pct} color="#F59E0B" detail={`${(total_recruiters - missing_phones).toLocaleString()} numbers`} />
          </div>
        </div>

        {/* Right: Sentinel Real-Time Engine State */}
        <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Cpu size={18} color="var(--brand)" />
                Sentinel Autonomous Engine
              </h3>
              <div style={{ 
                background: status === 'Running' || status === 'Active' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)', 
                color: status === 'Running' || status === 'Active' ? '#10B981' : '#F59E0B', 
                padding: '4px 10px', 
                borderRadius: 999, 
                fontSize: 11, 
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: status === 'Running' || status === 'Active' ? '#10B981' : '#F59E0B' }} />
                {status}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ padding: 12, borderRadius: 8, background: 'var(--bg-elevated)', border: '1px solid var(--card-border)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Target Company Scope</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{current_company_name}</div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: 'var(--bg-elevated)', border: '1px solid var(--card-border)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Geographic Focus</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{current_state}</div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Rules Evaluated: 24 active algorithms</span>
            <button 
              onClick={handleRunScan} 
              disabled={scanning}
              style={{ fontSize: 12, color: 'var(--brand)', background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}
            >
              Trigger Full Scan <Play size={12} />
            </button>
          </div>
        </div>
      </div>

      {/* Interactive Anomaly Review Queue */}
      <div className="card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle size={18} color="#F59E0B" />
              Live Anomaly Quarantine & Review Queue ({totalAnomalies.toLocaleString()})
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>
              Identified data discrepancies, unmapped corporate domains, and flagged profiles ready for 1-click repair.
            </p>
          </div>

          {/* Filter Pills */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            {[
              { key: 'all', label: 'All Anomalies' },
              { key: 'low_score', label: 'Quality < 50%' },
              { key: 'missing_email', label: 'Missing Email' },
              { key: 'missing_company', label: 'Unmapped Company' },
              { key: 'needs_review', label: 'Needs Review Flag' }
            ].map(f => (
              <button
                key={f.key}
                onClick={() => { setFilterType(f.key); setAnomalyPage(1); }}
                style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: '1px solid',
                  borderColor: filterType === f.key ? 'var(--brand)' : 'var(--card-border)',
                  background: filterType === f.key ? 'var(--brand-bg)' : 'var(--panel-bg)',
                  color: filterType === f.key ? 'var(--text-primary)' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease'
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Anomalies Table */}
        {loadingAnomalies ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <RefreshCw className="animate-spin" size={18} />
            <span style={{ fontSize: 13 }}>Loading anomalous records...</span>
          </div>
        ) : anomalies.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <CheckCircle size={36} color="#10B981" style={{ margin: '0 auto 12px' }} />
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>No Anomalies Found</div>
            <p style={{ fontSize: 13, margin: 0 }}>All records in this category pass quality threshold validation.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--table-header-bg, var(--bg-elevated))', borderBottom: '1px solid var(--card-border)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Profile / Recruiter</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Company</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>State</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Quality</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Anomaly Reason</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((rec) => {
                  const isRepairing = repairingId === rec.recruiter_id
                  const scoreColor = rec.completeness_score >= 80 ? '#10B981' : rec.completeness_score >= 50 ? '#F59E0B' : '#EF4444'
                  return (
                    <tr key={rec.recruiter_id} style={{ borderBottom: '1px solid var(--card-border)', transition: 'background 0.15s ease' }} className="table-row-hover">
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{rec.recruiter_name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{rec.email || 'No email registered'}</div>
                      </td>
                      <td style={{ padding: '14px 16px', color: 'var(--text-primary)', fontWeight: 500 }}>
                        {rec.company_name}
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 4, background: 'var(--bg-elevated)', border: '1px solid var(--card-border)', color: 'var(--text-primary)' }}>
                          {rec.state || 'UN'}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 12, fontWeight: 800, color: scoreColor }}>{rec.completeness_score}%</span>
                          <div style={{ width: 40, height: 4, borderRadius: 2, background: 'var(--card-border)', overflow: 'hidden' }}>
                            <div style={{ width: `${rec.completeness_score}%`, height: '100%', background: scoreColor }} />
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{ fontSize: 11, color: '#F59E0B', background: 'rgba(245, 158, 11, 0.1)', padding: '3px 8px', borderRadius: 4, fontWeight: 600 }}>
                          {rec.review_reason || rec.repair_reason || 'Incomplete attributes'}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <button
                          onClick={() => handleQuickRepair(rec.recruiter_id)}
                          disabled={isRepairing}
                          className="cc-ghost-button"
                          style={{ fontSize: 12, padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                        >
                          {isRepairing ? <RefreshCw className="animate-spin" size={12} /> : <Wrench size={12} />}
                          {isRepairing ? 'Repairing...' : 'Quick Fix'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalAnomalies > 10 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--card-border)' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Showing {((anomalyPage - 1) * 10) + 1} - {Math.min(anomalyPage * 10, totalAnomalies)} of {totalAnomalies} records
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button 
                onClick={() => setAnomalyPage(p => Math.max(1, p - 1))}
                disabled={anomalyPage === 1}
                className="cc-ghost-button"
                style={{ padding: '6px 12px', fontSize: 12 }}
              >
                Previous
              </button>
              <button 
                onClick={() => setAnomalyPage(p => p + 1)}
                disabled={anomalyPage * 10 >= totalAnomalies}
                className="cc-ghost-button"
                style={{ padding: '6px 12px', fontSize: 12 }}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function MetricCard({ label, value, icon: Icon, color, subtitle }) {
  return (
    <div className="card" style={{ padding: '1.25rem', position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
          {label}
        </div>
        <Icon size={18} color={color} opacity={0.9} />
      </div>
      <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: 4, letterSpacing: '-0.02em' }}>
        {typeof value === 'number' ? value.toLocaleString() : value ?? '-'}
      </div>
      {subtitle && (
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
          {subtitle}
        </div>
      )}
    </div>
  )
}

function CoverageProgressBar({ label, pct, color, detail }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, fontSize: 12 }}>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{label}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{detail}</span>
          <span style={{ fontWeight: 700, color: color }}>{pct}%</span>
        </div>
      </div>
      <div style={{ width: '100%', height: 6, borderRadius: 3, background: 'var(--bg-elevated)', overflow: 'hidden' }}>
        <div style={{ width: `${Math.min(100, pct)}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.4s ease' }} />
      </div>
    </div>
  )
}
