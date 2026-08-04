import React, { useState, useEffect } from 'react'
import api from '../../services/api'

export default function DataIntelligence({ setToast }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    const fetchData = async () => {
      try {
        const res = await api.get('/sentinel/stats')
        if (!alive) return
        setStats(res.data)
      } catch (err) {
        if (alive) setToast({ type: 'error', message: err?.response?.data?.detail || err.message || 'Failed to load Data Intelligence stats' })
      } finally {
        if (alive) setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => {
      alive = false
      clearInterval(interval)
    }
  }, [setToast])

  if (loading && !stats) {
    return <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>Loading Data Intelligence...</div>
  }

  const statCards = [
    { label: 'Total Processed', value: stats?.total_processed, color: 'var(--brand)' },
    { label: 'Pending in Queue', value: stats?.total_queued, color: '#ffb020' },
    { label: 'Companies Identified', value: stats?.companies_identified, color: '#00ff66' },
    { label: 'Unknown Companies', value: stats?.unknown_companies, color: '#ff4444' },
    { label: 'Domains Mapped', value: stats?.domains_mapped, color: '#00ccff' },
    { label: 'Profiles Enriched', value: stats?.profiles_enriched, color: '#a020f0' },
    { label: 'Duplicates Merged', value: stats?.duplicate_companies_merged, color: 'var(--text-main)' },
  ]

  return (
    <div style={{
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto',
      animation: 'ccFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards'
    }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-bright)' }}>Data Intelligence</h1>
        <p style={{ margin: 0, color: 'var(--text-muted)' }}>Real-time metrics of the Sentinel Engine.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
        {statCards.map((card, i) => (
          <div key={i} className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1rem' }}>
              {card.label}
            </div>
            <div style={{ fontSize: '2.5rem', fontWeight: 800, color: card.color }}>
              {card.value?.toLocaleString() || 0}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
