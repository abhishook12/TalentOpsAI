import React, { useState, useEffect } from 'react'
import api from '../../services/api'
import { Activity, Database, CheckCircle, AlertTriangle, XCircle, Search, ShieldAlert, Cpu } from 'lucide-react'

export default function DataQualityCenter() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    const fetchData = async () => {
      try {
        const res = await api.get('/sentinel/dashboard')
        if (!alive) return
        setData(res.data)
        setError(null)
      } catch (err) {
        if (alive) {
          setError(err?.response?.data?.detail || err.message || 'Failed to load Data Quality stats')
        }
      } finally {
        if (alive) setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 2000)
    return () => {
      alive = false
      clearInterval(interval)
    }
  }, [])

  if (loading && !data) {
    return <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>Loading Data Quality Center...</div>
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', color: 'var(--danger)' }}>
        <ShieldAlert size={48} style={{ marginBottom: '1rem' }} />
        <h2>Connection Error</h2>
        <p>{error}</p>
      </div>
    )
  }

  const {
    status,
    total_recruiters,
    total_companies,
    unknown_companies,
    missing_emails,
    missing_phones,
    missing_linkedin,
    missing_logos,
    profiles_below_50,
    profiles_above_90,
    avg_confidence,
    avg_completeness,
    companies_completed,
    recruiters_completed,
    current_company_name,
    current_state,
    estimated_completion_hours
  } = data;

  // Calculate Health Score based on completeness and missing core fields
  const healthScore = Math.max(0, 100 - (
    (missing_emails / (total_recruiters || 1)) * 40 +
    (missing_phones / (total_recruiters || 1)) * 20 +
    (missing_linkedin / (total_recruiters || 1)) * 20 +
    (unknown_companies / (total_recruiters || 1)) * 20
  )).toFixed(1);

  const healthColor = healthScore >= 90 ? 'var(--success)' : healthScore >= 70 ? 'var(--warning)' : 'var(--danger)'

  return (
    <div style={{
      padding: '2rem',
      maxWidth: '1400px',
      margin: '0 auto',
      animation: 'ccFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards'
    }}>
      <div style={{ marginBottom: '2.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-bright)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <Activity color="var(--brand)" />
            Data Quality Center
          </h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', maxWidth: 600 }}>
            Continuous vulnerability scanning, auto-repair, and health metrics for the TalentOps database.
          </p>
        </div>
        <div className="glass-panel" style={{ padding: '1rem 2rem', display: 'flex', alignItems: 'center', gap: '1.5rem', border: `1px solid ${healthColor}40` }}>
          <div>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: 4 }}>
              Overall DB Health
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 900, color: healthColor, lineHeight: 1 }}>
              {healthScore}%
            </div>
          </div>
          <Database size={40} color={healthColor} opacity={0.5} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
        <MetricCard label="Companies Audited" value={companies_completed} icon={CheckCircle} color="var(--success)" />
        <MetricCard label="Profiles Audited" value={recruiters_completed} icon={CheckCircle} color="var(--success)" />
        <MetricCard label="Unknown Companies" value={unknown_companies} icon={Search} color="var(--warning)" />
        <MetricCard label="Missing Emails" value={missing_emails} icon={AlertTriangle} color="var(--warning)" />
        <MetricCard label="Profiles < 50% Quality" value={profiles_below_50} icon={XCircle} color="var(--danger)" />
        <MetricCard label="Avg Completeness" value={`${avg_completeness}%`} icon={Cpu} color="var(--brand)" />
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem', borderLeft: status === 'Running' ? '4px solid #22c55e' : '4px solid #f59e0b' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ marginTop: 0, marginBottom: 0, color: 'var(--text-bright)', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={20} color="var(--brand)" style={{ animation: status === 'Running' ? 'pulse 2s infinite' : 'none' }} />
            Phase IV Engine Target
          </h2>
          <div style={{ 
            background: status === 'Running' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', 
            color: status === 'Running' ? '#22c55e' : '#ef4444', 
            padding: '4px 12px', 
            borderRadius: 999, 
            fontSize: '0.875rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 6
          }}>
            {status === 'Running' && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', animation: 'pulse 2s infinite' }} />}
            {status}
          </div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginTop: 24 }}>
          <div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Currently Processing Company</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>{current_company_name}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Location Scope</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>{current_state}</div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.1); }
          100% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}

function MetricCard({ label, value, icon: Icon, color }) {
  return (
    <div className="glass-panel" style={{ padding: '1.25rem', position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
          {label}
        </div>
        <Icon size={20} color={color} opacity={0.8} />
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-bright)' }}>
        {value?.toLocaleString() ?? '-'}
      </div>
    </div>
  )
}
