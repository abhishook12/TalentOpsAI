import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Users, Activity, Clock, MousePointerClick } from 'lucide-react'
import api from '../../../services/api'

export default function OverviewTab() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['visitor-analytics-overview'],
    queryFn: async () => {
      const res = await api.get('/admin/visitor-analytics/overview')
      return res.data
    },
    refetchInterval: 30000
  })

  if (isLoading) return <div style={{ color: 'rgba(255,255,255,0.6)' }}>Loading overview...</div>
  if (!stats) return null

  const formatSecs = (s) => {
    if (!s) return '0s'
    const m = Math.floor(s / 60)
    return m > 0 ? `${m}m ${s % 60}s` : `${s}s`
  }

  const kpis = [
    { label: 'Visitors Today', value: stats.visitors_today, icon: Users, color: '#4ade80' },
    { label: 'Active Now', value: stats.active_now, icon: Activity, color: '#60a5fa' },
    { label: 'Unique Users', value: stats.unique_users, icon: Users, color: '#a78bfa' },
    { label: 'Returning Users', value: stats.returning_users, icon: MousePointerClick, color: '#f472b6' },
    { label: 'Avg Session', value: formatSecs(stats.avg_session_duration_sec), icon: Clock, color: '#fb923c' },
    { label: 'Bounce Rate', value: `${stats.bounce_rate}%`, icon: MousePointerClick, color: '#f87171' },
    { label: 'Avg Pages / Session', value: stats.avg_pages_per_session, icon: MousePointerClick, color: '#2dd4bf' },
    { label: 'Total Sessions (30d)', value: stats.total_sessions, icon: Activity, color: '#94a3b8' }
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
      {kpis.map((kpi, idx) => {
        const Icon = kpi.icon
        return (
          <div key={idx} style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 16,
            padding: 20,
            display: 'flex',
            flexDirection: 'column',
            gap: 12
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ 
                background: `color-mix(in srgb, ${kpi.color} 15%, transparent)`, 
                color: kpi.color, 
                padding: 8, 
                borderRadius: 8 
              }}>
                <Icon size={18} />
              </div>
              <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13, fontWeight: 600 }}>{kpi.label}</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
              {kpi.value}
            </div>
          </div>
        )
      })}
    </div>
  )
}
