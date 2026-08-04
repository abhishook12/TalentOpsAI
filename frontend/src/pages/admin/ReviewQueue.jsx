import React, { useState, useEffect } from 'react'
import api from '../../services/api'
import { CompanyIdentity } from '../../components/CompanyIdentity'

export default function ReviewQueue({ setToast }) {
  const [queue, setQueue] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const fetchQueue = async () => {
    setLoading(true)
    try {
      const res = await api.get('/sentinel/review-queue')
      setQueue(res.data.items)
      setTotal(res.data.total)
    } catch (err) {
      setToast({ type: 'error', message: err?.response?.data?.detail || err.message || 'Failed to load review queue' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue()
  }, [])

  const handleAction = async (recruiterId, action) => {
    try {
      await api.post(`/sentinel/review-queue/${recruiterId}/${action}`)
      setToast({ type: 'success', message: `Successfully ${action}d match` })
      setQueue(prev => prev.filter(r => r.recruiter_id !== recruiterId))
      setTotal(prev => prev - 1)
    } catch (err) {
      setToast({ type: 'error', message: `Failed to ${action} match` })
    }
  }

  if (loading && queue.length === 0) {
    return <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>Loading Review Queue...</div>
  }

  return (
    <div style={{
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto',
      animation: 'ccFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards'
    }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-bright)' }}>Manual Review Queue</h1>
        <p style={{ margin: 0, color: 'var(--text-muted)' }}>
          Review low-confidence company matches inferred by the Sentinel Engine. ({total} pending)
        </p>
      </div>

      {queue.length === 0 ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Queue is empty! All matches are highly confident.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {queue.map(item => (
            <div key={item.recruiter_id} className="glass-panel" style={{ padding: '1.5rem', display: 'flex', gap: '2rem', alignItems: 'center' }}>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.25rem' }}>Recruiter</div>
                <div style={{ color: 'var(--text-bright)', fontWeight: 600, fontSize: '1.1rem' }}>{item.recruiter_name}</div>
                <div style={{ color: 'var(--brand)', fontSize: '0.9rem' }}>{item.email}</div>
              </div>
              
              <div style={{ padding: '0 2rem', color: 'var(--text-muted)' }}>
                &rarr;
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.25rem' }}>Suggested Company</div>
                {item.suggested_company ? (
                   <CompanyIdentity 
                     name={item.suggested_company.company_name} 
                     domain={item.suggested_company.website}
                     subtitle={`Confidence: ${item.company_confidence}%`}
                     interactive={false}
                   />
                ) : (
                  <div style={{ color: 'var(--text-muted)' }}>None suggested</div>
                )}
                <div style={{ color: '#ffb020', fontSize: '0.85rem', marginTop: '0.5rem' }}>
                  {item.review_reason}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <button 
                  className="btn-secondary" 
                  style={{ color: '#ff4444', borderColor: 'rgba(255, 68, 68, 0.2)' }}
                  onClick={() => handleAction(item.recruiter_id, 'reject')}
                >
                  Reject
                </button>
                <button 
                  className="btn-primary" 
                  style={{ background: '#00ff66', color: '#000' }}
                  onClick={() => handleAction(item.recruiter_id, 'approve')}
                >
                  Approve
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
