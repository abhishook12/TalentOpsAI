import React, { useState, useEffect } from 'react'
import api from '../../services/api'

export default function DataIntelligence({ setToast }) {
  const [stats, setStats] = useState(null)
  const [engineState, setEngineState] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    const fetchData = async () => {
      try {
        const res = await api.get('/admin/intelligence-stats')
        if (!alive) return
        setStats(res.data?.metrics || null)
        setEngineState(res.data?.engine_state || null)
      } catch (err) {
        if (alive) setToast({ type: 'error', message: err?.response?.data?.detail || err.message || 'Failed to load Data Intelligence stats' })
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
  }, [setToast])

  if (loading && !stats) {
    return <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>Loading Data Intelligence...</div>
  }

  const statCards = [
    { label: 'Total Recruiters', value: stats?.total_recruiters, color: 'var(--brand)' },
    { label: 'Profiles Processed', value: stats?.total_processed, color: '#ffb020' },
    { label: 'Profiles Enriched', value: stats?.profiles_enriched, color: '#00ff66' },
    { label: 'Duplicates Merged', value: stats?.duplicates_merged, color: '#ff4444' },
    { label: 'Domains Mapped', value: stats?.domains_mapped, color: '#00ccff' },
    { label: 'Logos Assigned', value: stats?.logos_assigned, color: '#a020f0' },
    { label: 'Needs Review', value: stats?.records_needing_review, color: '#ff8c00' },
    { label: 'Avg Completeness', value: stats?.average_completeness != null ? `${stats.average_completeness}%` : null, color: 'var(--text-main)' },
  ]

  return (
    <div style={{
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto',
      animation: 'ccFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards'
    }}>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-bright)' }}>Data Intelligence</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)' }}>Real-time metrics of the Sentinel Engine.</p>
        </div>
        {engineState && (
          <div style={{ padding: '0.5rem 1rem', borderRadius: 8, background: 'var(--card-bg)', border: '1px solid var(--card-border)', fontSize: 13 }}>
            <span style={{ color: 'var(--text-muted)' }}>Engine: </span>
            <span style={{ color: engineState.status === 'Running' ? '#00ff66' : 'var(--text-secondary)', fontWeight: 600 }}>{engineState.status}</span>
            {engineState.current_task && engineState.current_task !== 'No active task' && (
              <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>— {engineState.current_task}</span>
            )}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem' }}>
        {statCards.map((card, i) => (
          <div key={i} className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1rem' }}>
              {card.label}
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 800, color: card.color }}>
              {card.value != null
                ? (typeof card.value === 'string' ? card.value : card.value.toLocaleString())
                : 0}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
