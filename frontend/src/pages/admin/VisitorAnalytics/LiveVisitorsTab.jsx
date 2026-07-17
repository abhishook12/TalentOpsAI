import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Monitor, MapPin, Clock, Fingerprint } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import api from '../../../services/api'
import VisitorProfileDrawer from './VisitorProfileDrawer'

export default function LiveVisitorsTab() {
  const [selectedSession, setSelectedSession] = React.useState(null)
  
  const { data: activeSessions, isLoading } = useQuery({
    queryKey: ['visitor-analytics-live'],
    queryFn: async () => {
      const res = await api.get('/admin/visitor-analytics/live')
      return res.data
    },
    refetchInterval: 10000
  })

  if (isLoading) return <div style={{ color: 'rgba(255,255,255,0.6)' }}>Loading live visitors...</div>

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
        {activeSessions?.length === 0 && (
          <div style={{ color: 'rgba(255,255,255,0.5)', padding: 20 }}>No active visitors in the last 10 minutes.</div>
        )}
        
        {activeSessions?.map(s => (
          <div 
            key={s.session_id} 
            onClick={() => setSelectedSession(s.session_id)}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--card-border)',
              borderRadius: 16,
              padding: 20,
              cursor: 'pointer',
              transition: 'background 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ 
                  width: 40, height: 40, borderRadius: '50%', background: 'rgba(96, 165, 250, 0.1)', 
                  display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#60a5fa' 
                }}>
                  {s.user_email ? s.user_email[0].toUpperCase() : <Fingerprint size={20} />}
                </div>
                <div>
                  <div style={{ color: 'var(--text-inverse)', fontWeight: 700, fontSize: 14 }}>{s.user_email || 'Anonymous Visitor'}</div>
                  <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>{s.ip_address}</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <div style={{ 
                  background: s.status === 'Active' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(250, 204, 21, 0.1)',
                  color: s.status === 'Active' ? '#4ade80' : '#facc15',
                  padding: '4px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700
                }}>
                  {s.status}
                </div>
                {s.session_score === 'Power User' && (
                  <div style={{ 
                    background: 'rgba(96, 165, 250, 0.1)',
                    color: '#60a5fa',
                    padding: '4px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700
                  }}>
                    {s.session_score}
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>
              {s.current_page && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-inverse)', fontWeight: 600 }}>
                  <Monitor size={14} style={{ opacity: 0.5, color: '#60a5fa' }} /> {s.current_page}
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <MapPin size={14} style={{ opacity: 0.5 }} /> {s.city}, {s.country}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Monitor size={14} style={{ opacity: 0.5 }} /> {s.browser} on {s.os}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Clock size={14} style={{ opacity: 0.5 }} /> Last seen {formatDistanceToNow(new Date(s.last_activity || s.started_at))} ago
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {selectedSession && (
        <VisitorProfileDrawer 
          sessionId={selectedSession} 
          onClose={() => setSelectedSession(null)} 
        />
      )}
    </>
  )
}
