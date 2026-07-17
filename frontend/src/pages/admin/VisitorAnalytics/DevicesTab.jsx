import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Monitor, Smartphone } from 'lucide-react'
import api from '../../../services/api'
import { SkeletonRow } from '../../../components/ui/Skeleton'
import { EmptyState } from '../../../components/ui/EmptyState'

export default function DevicesTab() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['visitor-analytics-devices'],
    queryFn: async () => {
      const res = await api.get('/admin/visitor-analytics/sessions')
      return res.data
    },
    refetchInterval: 300000
  })

  if (isLoading) return <div className="glass-card" style={{ padding: 24, borderRadius: 16 }}><SkeletonRow rows={6} gap={16} height={30} /></div>
  if (isError) return <EmptyState icon="ti-alert-circle" title="Failed to load devices data" />

  const sessions = data?.items || []
  if (sessions.length === 0) return <EmptyState icon="ti-device-desktop" title="No device data" description="No visitor data is available yet." />

  const browsers = {}
  const os = {}
  sessions.forEach(s => {
    const b = s.browser || 'Unknown'
    const o = s.os || 'Unknown'
    browsers[b] = (browsers[b] || 0) + 1
    os[o] = (os[o] || 0) + 1
  })

  const sortedBrowsers = Object.entries(browsers).sort((a, b) => b[1] - a[1])
  const sortedOS = Object.entries(os).sort((a, b) => b[1] - a[1])

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
      <div className="glass-card" style={{ padding: 24, borderRadius: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <div style={{ background: 'rgba(167, 139, 250, 0.1)', color: '#a78bfa', padding: 8, borderRadius: 8 }}>
            <Monitor size={20} />
          </div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>Top Browsers</h2>
        </div>
        <div style={{ display: 'grid', gap: 16 }}>
          {sortedBrowsers.map(([browser, count]) => (
            <div key={browser} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 16, borderBottom: '1px solid var(--card-border)' }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{browser}</span>
              <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-secondary)' }}>{count}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="glass-card" style={{ padding: 24, borderRadius: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <div style={{ background: 'rgba(251, 146, 60, 0.1)', color: '#fb923c', padding: 8, borderRadius: 8 }}>
            <Smartphone size={20} />
          </div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>Operating Systems</h2>
        </div>
        <div style={{ display: 'grid', gap: 16 }}>
          {sortedOS.map(([sys, count]) => (
            <div key={sys} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 16, borderBottom: '1px solid var(--card-border)' }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{sys}</span>
              <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-secondary)' }}>{count}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
