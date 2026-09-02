import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import { ShellCard, Badge, GhostButton } from './CommandCenter'
import AnimatedNumber from './ui/AnimatedNumber'

export default function ScoutNodesPanel() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['scout-nodes-telemetry'],
    queryFn: async () => {
      const res = await api.get('/scout/nodes')
      return res.data
    },
    refetchInterval: 6000,
    staleTime: 4000,
  })

  const nodes = data?.nodes || []
  const totalNodes = data?.total_scout_nodes || nodes.length || 0
  const activeConnected = data?.active_connected_nodes || 0
  const streamingNodes = data?.active_nodes_streaming_data || 0

  const statusColors = {
    LIVE_STREAMING: { text: '● LIVE STREAMING', color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
    CONNECTED_IDLE: { text: '● CONNECTED (IDLE)', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
    IDLE_NO_INGESTION: { text: '⚠ NO INGESTION (>5m)', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
    PREVIOUSLY_ACTIVE: { text: '○ HISTORICAL (OFFLINE)', color: '#9ca3af', bg: 'rgba(156,163,175,0.15)' },
    AWAITING_CONNECTION: { text: '○ AWAITING PAIRING', color: '#64748b', bg: 'rgba(100,116,139,0.15)' },
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Summary Header */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 18px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>TOTAL SCOUT NODES</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}><AnimatedNumber value={totalNodes} /></div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Registered User Browsers</div>
        </div>

        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 18px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>ACTIVE CONNECTED</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#10b981' }}><AnimatedNumber value={activeConnected} /></div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Heartbeat &lt; 45s Recency</div>
        </div>

        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 18px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>STREAMING INGESTION</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#3b82f6' }}><AnimatedNumber value={streamingNodes} /></div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Actively pushing discoveries</div>
        </div>

        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 18px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>IDLE / NO INGESTION</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#f59e0b' }}><AnimatedNumber value={Math.max(0, activeConnected - streamingNodes)} /></div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Connected but idle browsing</div>
        </div>
      </div>

      {/* Per-User Scout Node Grid */}
      <div style={{ display: 'grid', gap: 14 }}>
        {nodes.map((node) => {
          const cfg = statusColors[node.node_status] || statusColors.AWAITING_CONNECTION

          return (
            <div
              key={node.scout_id}
              style={{
                background: 'var(--card-bg)',
                border: '1px solid var(--border)',
                borderRadius: 12,
                padding: 18,
                display: 'flex',
                flexDirection: 'column',
                gap: 14,
              }}
            >
              {/* Node Top Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div
                    style={{
                      width: 38,
                      height: 38,
                      borderRadius: 8,
                      background: 'rgba(59, 130, 246, 0.15)',
                      color: '#3b82f6',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 18,
                      fontWeight: 800,
                    }}
                  >
                    🛰️
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)' }}>{node.user_name}</span>
                      <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--mono)' }}>({node.scout_id})</span>
                      <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>• {node.user_email}</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                      Device: <strong>{node.device_name}</strong> • Heartbeat: <strong style={{ color: node.heartbeat_seconds_ago < 60 ? '#10b981' : '#f59e0b' }}>{node.heartbeat_formatted}</strong>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span
                    style={{
                      padding: '4px 10px',
                      borderRadius: 20,
                      fontSize: 11,
                      fontWeight: 800,
                      color: cfg.color,
                      background: cfg.bg,
                      border: `1px solid ${cfg.color}40`,
                    }}
                  >
                    {cfg.text}
                  </span>
                </div>
              </div>

              {/* Node Forensic Telemetry Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, background: 'rgba(0,0,0,0.15)', padding: 12, borderRadius: 8, fontSize: 12 }}>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 11, marginBottom: 2 }}>LAST CAPTURE</div>
                  <div style={{ fontWeight: 700, fontFamily: 'var(--mono)' }}>{node.last_capture_time}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 11, marginBottom: 2 }}>LAST EXTRACTION</div>
                  <div style={{ fontWeight: 700, fontFamily: 'var(--mono)' }}>{node.last_extraction_time}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 11, marginBottom: 2 }}>LAST MASTER DB UPDATE</div>
                  <div style={{ fontWeight: 700, fontFamily: 'var(--mono)', color: '#10b981' }}>{node.last_db_write}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 11, marginBottom: 2 }}>SYNC RESULT</div>
                  <div style={{ fontWeight: 700, color: '#10b981' }}>{node.db_successes} Success / {node.db_failures} Fail</div>
                </div>
              </div>

              {/* Node Discovery Counts Today */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, borderTop: '1px solid var(--border)', paddingTop: 10 }}>
                <div style={{ display: 'flex', gap: 16 }}>
                  <span>Captures: <strong>{node.captures_today}</strong></span>
                  <span>Enriched Today: <strong style={{ color: '#06b6d4' }}>+{node.records_enriched}</strong></span>
                  <span>New People: <strong style={{ color: '#ec4899' }}>+{node.new_records_created}</strong></span>
                  <span>Fields Added: <strong style={{ color: '#10b981' }}>+{node.fields_added}</strong></span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  Last URL: {node.last_page_observed}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
