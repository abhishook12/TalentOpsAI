import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Globe, MapPin } from 'lucide-react'
import api from '../../../services/api'
import { SkeletonRow } from '../../../components/ui/Skeleton'
import { EmptyState } from '../../../components/ui/EmptyState'

export default function GeographyTab() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['visitor-analytics-geography'],
    queryFn: async () => {
      const res = await api.get('/admin/visitor-analytics/sessions') // Reuse sessions endpoint for geography
      return res.data
    },
    refetchInterval: 300000
  })

  if (isLoading) return <div className="glass-card" style={{ padding: 24, borderRadius: 16 }}><SkeletonRow rows={6} gap={16} height={30} /></div>
  if (isError) return <EmptyState icon="ti-alert-circle" title="Failed to load geography data" />

  const sessions = data?.items || []
  if (sessions.length === 0) return <EmptyState icon="ti-world" title="No geographical data" description="No visitor data is available yet to map." />

  const countries = {}
  sessions.forEach(s => {
    const key = s.country || 'Unknown'
    countries[key] = (countries[key] || 0) + 1
  })

  const sortedCountries = Object.entries(countries).sort((a, b) => b[1] - a[1])

  return (
    <div className="glass-card" style={{ padding: 24, borderRadius: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div style={{ background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', padding: 8, borderRadius: 8 }}>
          <Globe size={20} />
        </div>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>Traffic by Geography</h2>
      </div>

      <div style={{ display: 'grid', gap: 16 }}>
        {sortedCountries.map(([country, count]) => (
          <div key={country} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 16, borderBottom: '1px solid var(--card-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <MapPin size={16} style={{ color: 'var(--text-muted)' }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{country}</span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-secondary)' }}>{count} sessions</div>
          </div>
        ))}
      </div>
    </div>
  )
}
