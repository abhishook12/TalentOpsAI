import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { X, User, MapPin, Monitor, Clock, FileText, Activity } from 'lucide-react'
import api from '../../../services/api'

export default function VisitorProfileDrawer({ sessionId, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ['visitor-analytics-session', sessionId],
    queryFn: async () => {
      const res = await api.get(`/admin/visitor-analytics/sessions/${sessionId}`)
      return res.data
    }
  })

  return (
    <div style={{
      position: 'fixed',
      top: 0, right: 0, bottom: 0,
      width: 480,
      background: '#141414',
      borderLeft: '1px solid var(--card-border)',
      zIndex: 100,
      boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ 
        padding: '24px', 
        borderBottom: '1px solid var(--card-border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h2 style={{ margin: 0, fontSize: 18, color: 'var(--text-primary)' }}>Session Details</h2>
        <button 
          onClick={onClose}
          style={{ 
            background: 'transparent', 
            border: 'none', 
            color: 'rgba(255,255,255,0.5)', 
            cursor: 'pointer' 
          }}
        >
          <X size={20} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        {isLoading ? (
          <div style={{ color: 'rgba(255,255,255,0.6)' }}>Loading timeline...</div>
        ) : !data || data.error ? (
          <div style={{ color: '#ef4444' }}>{data?.error || 'Failed to load'}</div>
        ) : (
          <>
            <div style={{ 
              background: 'var(--bg-surface)', 
              borderRadius: 12, 
              padding: 16,
              marginBottom: 32,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
              fontSize: 13
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-primary)' }}>
                <User size={16} style={{ color: '#a78bfa' }}/>
                {data.profile.user_email || 'Anonymous'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'rgba(255,255,255,0.7)' }}>
                <MapPin size={16} style={{ color: '#60a5fa' }}/>
                {data.profile.location} ({data.profile.ip_address})
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'rgba(255,255,255,0.7)' }}>
                <Monitor size={16} style={{ color: '#4ade80' }}/>
                {data.profile.system}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'rgba(255,255,255,0.7)' }}>
                <Clock size={16} style={{ color: '#fb923c' }}/>
                Started {format(new Date(data.profile.started_at), 'MMM d, h:mm:ss a')}
              </div>
            </div>

            <h3 style={{ fontSize: 14, color: 'var(--text-primary)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Timeline</h3>
            
            <div style={{ position: 'relative', paddingLeft: 16, borderLeft: '2px solid rgba(255,255,255,0.1)', marginLeft: 8 }}>
              {data.timeline.length === 0 && <div style={{ color: 'rgba(255,255,255,0.5)' }}>No events recorded.</div>}
              {data.timeline.map((event, idx) => (
                <div key={idx} style={{ position: 'relative', marginBottom: 24 }}>
                  <div style={{ 
                    position: 'absolute', 
                    left: -25, 
                    top: 2, 
                    width: 16, 
                    height: 16, 
                    borderRadius: '50%',
                    background: '#141414',
                    border: `2px solid ${event.type === 'page_view' ? '#60a5fa' : '#a78bfa'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}>
                  </div>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
                    <div style={{ fontWeight: 600, color: event.type === 'page_view' ? '#60a5fa' : '#a78bfa', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                      {event.type === 'page_view' ? <FileText size={14}/> : <Activity size={14}/>}
                      {event.type === 'page_view' ? 'Page View' : 'Action'}
                    </div>
                    <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                      {format(new Date(event.timestamp), 'h:mm:ss a')}
                    </div>
                  </div>
                  
                  <div style={{ color: 'var(--text-primary)', fontSize: 13, background: 'var(--bg-surface)', padding: '8px 12px', borderRadius: 8 }}>
                    {event.type === 'page_view' ? (
                      <>{event.page} <span style={{ color: 'rgba(255,255,255,0.4)' }}>({event.path})</span></>
                    ) : (
                      <>
                        <div style={{ fontWeight: 600 }}>{event.action_type}</div>
                        {event.details && <div style={{ color: 'rgba(255,255,255,0.6)', marginTop: 4, fontFamily: 'monospace', fontSize: 11 }}>{event.details}</div>}
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
