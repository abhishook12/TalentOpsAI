import React, { useState, useEffect } from 'react'
import api from '../../services/api'
import { Activity, Database, CheckCircle, AlertTriangle, XCircle, Search, ShieldAlert, Cpu } from 'lucide-react'

export default function DataQualityCenter() {
  const [metrics, setMetrics] = useState(null)
  const [repairLogs, setRepairLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    const fetchData = async () => {
      try {
        const [metricsRes, logsRes] = await Promise.all([
          api.get('/analytics/quality-metrics'),
          api.get('/analytics/repair-logs?limit=20')
        ])
        
        if (!alive) return
        setMetrics(metricsRes.data)
        setRepairLogs(logsRes.data.logs)
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
    const interval = setInterval(fetchData, 10000)
    return () => {
      alive = false
      clearInterval(interval)
    }
  }, [])

  if (loading && !metrics) {
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

  const overallHealth = metrics?.overall_health || 0
  const healthColor = overallHealth >= 90 ? 'var(--success)' : overallHealth >= 70 ? 'var(--warning)' : 'var(--danger)'

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
              {overallHealth}%
            </div>
          </div>
          <Database size={40} color={healthColor} opacity={0.5} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
        <MetricCard label="Recruiters Completed" value={metrics?.recruiters_completed} icon={CheckCircle} color="var(--success)" />
        <MetricCard label="Companies Completed" value={metrics?.companies_completed} icon={CheckCircle} color="var(--success)" />
        <MetricCard label="Unknown Remaining" value={metrics?.unknown_remaining} icon={Search} color="var(--warning)" />
        <MetricCard label="Duplicates Identified" value={metrics?.duplicates_identified} icon={AlertTriangle} color="var(--warning)" />
        <MetricCard label="Profiles < 50% Quality" value={metrics?.low_quality_profiles} icon={XCircle} color="var(--danger)" />
        <MetricCard label="Avg Repair Confidence" value={`${(metrics?.average_repair_confidence * 100).toFixed(1)}%`} icon={Cpu} color="var(--brand)" />
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <h2 style={{ marginTop: 0, marginBottom: '1.5rem', color: 'var(--text-bright)', fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: 8 }}>
          <ShieldAlert size={20} color="var(--brand)" />
          Recent Auto-Repairs
        </h2>
        
        {repairLogs.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No recent repairs detected. The engine is monitoring.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>Time</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Entity</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Field</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Change</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Confidence</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Source</th>
                </tr>
              </thead>
              <tbody>
                {repairLogs.map(log => (
                  <tr key={log.id} style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
                    <td style={{ padding: '0.75rem 1rem', whiteSpace: 'nowrap' }}>
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', textTransform: 'capitalize' }}>
                      {log.entity_type} #{log.entity_id}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontFamily: 'var(--font-mono)' }}>
                      {log.field_name}
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <span style={{ color: 'var(--danger)', textDecoration: 'line-through', marginRight: '0.5rem' }}>
                        {log.old_value || 'NULL'}
                      </span>
                      <span style={{ color: 'var(--success)' }}>
                        {log.new_value}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 40, height: 4, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{ height: '100%', background: 'var(--success)', width: `${Math.min(100, log.confidence * 100)}%` }} />
                        </div>
                        <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>{(log.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.75rem' }}>
                      <span style={{ background: 'var(--brand-bg)', color: 'var(--brand)', padding: '2px 8px', borderRadius: 12 }}>
                        {log.source}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
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
