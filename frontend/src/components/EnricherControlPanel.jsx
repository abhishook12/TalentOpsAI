import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import api, { getErrorMessage } from '../services/api'
import { SectionHeader, ShellCard, GhostButton, Badge, PrimaryButton } from './CommandCenter'
import { Skeleton } from './ui/Skeleton'

export default function EnricherControlPanel() {
  const [state, setState] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)

  const fetchStatus = async () => {
    try {
      const res = await api.get('/system/enricher/status')
      setState(res.data)
    } catch (e) {
      console.error("Failed to fetch enricher status:", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleControl = async (action) => {
    setActionLoading(true)
    try {
      const res = await api.post('/system/enricher/control', { action })
      setState(res.data.state)
      toast.success(res.data.message || `Enricher ${action}ed`)
    } catch (e) {
      toast.error(getErrorMessage(e, `Failed to ${action} enricher`))
    } finally {
      setActionLoading(false)
    }
  }

  const getStatusBadge = () => {
    if (!state) return <Skeleton width={60} height={20} />
    switch(state.status) {
      case 'running': return <Badge tone="success">Running 🟢</Badge>
      case 'paused': return <Badge tone="warning">Paused 🟡</Badge>
      case 'stopped': return <Badge tone="danger">Stopped 🔴</Badge>
      default: return <Badge tone="neutral">Unknown</Badge>
    }
  }

  return (
    <ShellCard style={{ padding: 18, minHeight: 0 }}>
      <SectionHeader
        eyebrow="Background Daemon"
        title="Enricher Engine"
        subtitle="Control the massive scale JIT API enricher to find missing phones and locations."
        action={getStatusBadge()}
      />
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <div style={{ padding: 12, borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-surface)' }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Records Scanned</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--text-primary)' }}>
            {loading ? <Skeleton width={40} /> : (state?.records_processed || 0).toLocaleString()}
          </div>
        </div>
        <div style={{ padding: 12, borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-surface)' }}>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Successfully Enriched</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--success)' }}>
            {loading ? <Skeleton width={40} /> : (state?.success_count || 0).toLocaleString()}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        <GhostButton 
          disabled={loading || actionLoading || state?.status === 'running'} 
          onClick={() => handleControl('start')}
          style={{ borderColor: 'rgba(34, 197, 94, 0.3)', color: 'var(--success)' }}
        >
          <i className="ti ti-player-play" /> Start
        </GhostButton>
        <GhostButton 
          disabled={loading || actionLoading || state?.status !== 'running'} 
          onClick={() => handleControl('pause')}
          style={{ borderColor: 'rgba(234, 179, 8, 0.3)', color: 'var(--warning)' }}
        >
          <i className="ti ti-player-pause" /> Pause
        </GhostButton>
        <GhostButton 
          disabled={loading || actionLoading || state?.status === 'stopped'} 
          onClick={() => handleControl('stop')}
          style={{ borderColor: 'rgba(239, 68, 68, 0.3)', color: 'var(--danger)' }}
        >
          <i className="ti ti-player-stop" /> Stop
        </GhostButton>
      </div>
    </ShellCard>
  )
}
