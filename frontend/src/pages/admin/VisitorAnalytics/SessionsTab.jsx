import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import api from '../../../services/api'
import VisitorProfileDrawer from './VisitorProfileDrawer'
import { Fingerprint, Clock, Activity, AlertCircle } from 'lucide-react'

export default function SessionsTab() {
  const [selectedSession, setSelectedSession] = React.useState(null)
  
  const { data, isLoading } = useQuery({
    queryKey: ['visitor-analytics-sessions'],
    queryFn: async () => {
      const res = await api.get('/admin/visitor-analytics/sessions')
      return res.data
    }
  })

  if (isLoading) return <div style={{ color: 'rgba(255,255,255,0.6)' }}>Loading sessions...</div>

  return (
    <>
      <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 16, border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)' }}>
              <th style={{ padding: '16px 24px', color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>User / ID</th>
              <th style={{ padding: '16px 24px', color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>Location</th>
              <th style={{ padding: '16px 24px', color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>Device</th>
              <th style={{ padding: '16px 24px', color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>Started</th>
              <th style={{ padding: '16px 24px', color: 'rgba(255,255,255,0.5)', fontWeight: 600, textAlign: 'right' }}>Stats</th>
            </tr>
          </thead>
          <tbody>
            {data?.items?.map(s => (
              <tr 
                key={s.session_id} 
                onClick={() => setSelectedSession(s.session_id)}
                style={{ 
                  borderBottom: '1px solid rgba(255,255,255,0.05)', 
                  cursor: 'pointer',
                  transition: 'background 0.15s'
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <td style={{ padding: '16px 24px' }}>
                  <div style={{ color: '#fff', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                    {s.user_email ? s.user_email : <><Fingerprint size={14} style={{ opacity: 0.5 }}/> Anonymous</>}
                  </div>
                  <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 4, fontFamily: 'monospace' }}>
                    {s.session_id.substring(0, 8)}...
                  </div>
                </td>
                <td style={{ padding: '16px 24px', color: 'rgba(255,255,255,0.7)' }}>
                  <div>{s.city}, {s.country}</div>
                  <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 4 }}>{s.ip_address}</div>
                </td>
                <td style={{ padding: '16px 24px', color: 'rgba(255,255,255,0.7)' }}>
                  <div>{s.browser}</div>
                  <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 4 }}>{s.os}</div>
                </td>
                <td style={{ padding: '16px 24px', color: 'rgba(255,255,255,0.7)' }}>
                  {format(new Date(s.started_at), 'MMM d, h:mm a')}
                </td>
                <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, color: 'rgba(255,255,255,0.7)' }}>
                    <div title="Pages" style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Activity size={14}/> {s.total_page_views}</div>
                    <div title="Errors" style={{ display: 'flex', alignItems: 'center', gap: 4, color: s.total_errors > 0 ? '#ef4444' : 'inherit' }}>
                      <AlertCircle size={14}/> {s.total_errors}
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
