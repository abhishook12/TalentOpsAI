import React, { useState, useEffect } from 'react'
import api from '../../services/api'

export default function SentinelDashboard({ setToast }) {
  const [health, setHealth] = useState(null)
  const [queue, setQueue] = useState(null)
  const [audit, setAudit] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    const fetchData = async () => {
      try {
        const [hRes, qRes, aRes] = await Promise.all([
          api.get('/sentinel/health'),
          api.get('/sentinel/queue'),
          api.get('/sentinel/audit')
        ])
        if (!alive) return
        setHealth(hRes.data)
        setQueue(qRes.data)
        setAudit(aRes.data)
      } catch (err) {
        if (alive) setToast({ type: 'error', message: err?.response?.data?.detail || err.message || 'Failed to load Sentinel data' })
      } finally {
        if (alive) setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000) // Poll every 5s for live updates
    return () => {
      alive = false
      clearInterval(interval)
    }
  }, [setToast])

  const toggleEngine = async (action) => {
    try {
      await api.post(`/sentinel/toggle?action=${action}`)
      setToast({ type: 'success', message: `Engine ${action}ed` })
    } catch (err) {
      setToast({ type: 'error', message: 'Failed to toggle engine' })
    }
  }

  if (loading && !health) {
    return <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>Loading Sentinel Database Health...</div>
  }

  const progressPct = queue?.total_profiles > 0 
    ? Math.min(100, (queue.profiles_analyzed / queue.total_profiles) * 100).toFixed(1) 
    : 0

  return (
    <div style={{
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto',
      animation: 'ccFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-bright)' }}>SENTINEL</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)' }}>Strategic Enterprise Normalization, Trust, Integrity & Lifecycle Engine</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ 
            padding: '0.5rem 1rem', 
            borderRadius: '100px', 
            fontSize: '0.85rem',
            background: queue?.status === 'Running' ? 'rgba(0,255,100,0.1)' : 'rgba(255,255,255,0.05)',
            color: queue?.status === 'Running' ? '#00ff66' : 'var(--text-muted)',
            border: `1px solid ${queue?.status === 'Running' ? 'rgba(0,255,100,0.2)' : 'rgba(255,255,255,0.1)'}`,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <div style={{
              width: '8px', height: '8px', borderRadius: '50%',
              background: queue?.status === 'Running' ? '#00ff66' : '#666',
              boxShadow: queue?.status === 'Running' ? '0 0 8px #00ff66' : 'none'
            }} />
            Engine: {queue?.status || 'Unknown'}
          </div>
          {queue?.status === 'Running' ? (
            <button className="btn-secondary" onClick={() => toggleEngine('stop')}>Pause Engine</button>
          ) : (
            <button className="btn-primary" onClick={() => toggleEngine('start')}>Start Engine</button>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Overall Health Card */}
        <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1rem' }}>
            Overall Quality Score
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1rem' }}>
            <span style={{ fontSize: '4rem', fontWeight: 800, lineHeight: 1, color: 'var(--accent)' }}>
              {health?.overall_quality_score}
            </span>
            <span style={{ fontSize: '1.5rem', color: 'var(--text-muted)', paddingBottom: '0.5rem' }}>/ 100</span>
          </div>
          <p style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Average completeness and integrity score across {health?.total_profiles.toLocaleString()} recruiter profiles.
          </p>
        </div>

        {/* Engine Progress Card */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1.5rem' }}>
            Engine Progress
          </div>
          
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
              <span style={{ color: 'var(--text-main)' }}>Scanning Database</span>
              <span style={{ color: 'var(--text-muted)' }}>{progressPct}%</span>
            </div>
            <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ 
                width: `${progressPct}%`, 
                height: '100%', 
                background: 'linear-gradient(90deg, var(--accent), #ff00ff)',
                transition: 'width 1s ease'
              }} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Profiles Analyzed</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-bright)' }}>{queue?.profiles_analyzed.toLocaleString()}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Anomalies Repaired</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#00ff66' }}>{queue?.profiles_repaired.toLocaleString()}</div>
            </div>
          </div>
          <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
            &gt; {queue?.current_task_description || 'Idle'}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1.5rem' }}>
        {/* Missing Info Breakdown */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1.5rem 0', fontSize: '1rem', color: 'var(--text-bright)' }}>Missing Information Tracker</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {[
              { label: 'Missing Email', val: health?.missing_breakdown?.email },
              { label: 'Missing Phone', val: health?.missing_breakdown?.phone },
              { label: 'Missing LinkedIn', val: health?.missing_breakdown?.linkedin },
              { label: 'Missing Location', val: health?.missing_breakdown?.location },
              { label: 'Missing Company', val: health?.missing_breakdown?.company }
            ].map(item => (
              <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-main)', fontSize: '0.9rem' }}>{item.label}</span>
                <span style={{ 
                  background: item.val > 0 ? 'rgba(255, 50, 50, 0.1)' : 'rgba(0, 255, 100, 0.1)',
                  color: item.val > 0 ? '#ff4444' : '#00ff66',
                  padding: '0.2rem 0.6rem',
                  borderRadius: '100px',
                  fontSize: '0.8rem',
                  fontWeight: 600
                }}>{item.val?.toLocaleString() || 0}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Audit Log */}
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 1.5rem 0', fontSize: '1rem', color: 'var(--text-bright)' }}>Live Audit Log</h3>
          <div style={{ flex: 1, overflowY: 'auto', maxHeight: '400px', paddingRight: '0.5rem' }}>
            {audit.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>No repairs made yet.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {audit.map(log => (
                  <div key={log.id} style={{ 
                    padding: '1rem', 
                    background: 'rgba(255,255,255,0.02)', 
                    border: '1px solid rgba(255,255,255,0.05)',
                    borderRadius: '8px',
                    fontSize: '0.85rem'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{log.recruiter_name}</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{new Date(log.timestamp + 'Z').toLocaleTimeString()}</span>
                    </div>
                    <div style={{ color: '#00ff66', marginBottom: '0.25rem' }}>Fixed {log.field_changed} ({log.reason})</div>
                    <div style={{ display: 'flex', gap: '0.5rem', color: 'var(--text-muted)', fontFamily: 'var(--mono)', fontSize: '0.8rem' }}>
                      <span style={{ textDecoration: 'line-through', opacity: 0.5 }}>{log.previous_value || 'NULL'}</span>
                      <span>&rarr;</span>
                      <span style={{ color: 'var(--text-bright)' }}>{log.new_value || 'NULL'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
