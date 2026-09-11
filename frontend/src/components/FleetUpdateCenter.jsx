import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  AlertTriangle, CheckCircle, Clock, ShieldAlert, 
  ArrowUpCircle, RefreshCw, Pause, Play, AlertOctagon,
  Sliders, Layers, Server, Cpu
} from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'
import AnimatedNumber from './ui/AnimatedNumber'

export default function FleetUpdateCenter() {
  const queryClient = useQueryClient()
  const [updatingVersion, setUpdatingVersion] = useState(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['scout-fleet-stats'],
    queryFn: async () => {
      const res = await api.get('/scout/fleet/stats')
      return res.data
    },
    refetchInterval: 10000,
    staleTime: 5000,
  })

  const rolloutMutation = useMutation({
    mutationFn: async ({ version, rollout_percentage, is_paused }) => {
      setUpdatingVersion(version)
      const res = await api.post(`/scout/releases/${version}/rollout`, {
        rollout_percentage,
        is_paused,
      })
      return res.data
    },
    onSuccess: (data) => {
      toast.success(`Release v${data.version} updated: ${data.rollout_percentage}% rollout ${data.is_paused ? '(PAUSED)' : '(ACTIVE)'}`)
      queryClient.invalidateQueries(['scout-fleet-stats'])
    },
    onError: (err) => {
      toast.error(`Rollout update failed: ${err.response?.data?.detail || err.message}`)
    },
    onSettled: () => {
      setUpdatingVersion(null)
    }
  })

  const totalDevices = data?.total_devices || 0
  const health = data?.node_health || { healthy: 0, stale: 0, update_available: 0, update_required: 0, failed: 0, offline: 0 }
  const versionDist = data?.version_distribution || []
  const releases = data?.releases || []
  const circuitAlert = data?.circuit_breaker_alert

  const handleRolloutChange = (version, percentage) => {
    rolloutMutation.mutate({ version, rollout_percentage: percentage })
  }

  const handleTogglePause = (version, currentlyPaused) => {
    rolloutMutation.mutate({ version, is_paused: !currentlyPaused })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Circuit Breaker Alert Banner */}
      {circuitAlert && (
        <div 
          style={{
            background: 'linear-gradient(90deg, rgba(239, 68, 68, 0.2) 0%, rgba(185, 28, 28, 0.1) 100%)',
            border: '1px solid #ef4444',
            borderRadius: 10,
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <AlertOctagon size={24} color="#ef4444" />
            <div>
              <div style={{ fontSize: 13, fontWeight: 800, color: '#f87171' }}>
                AUTOMATIC CIRCUIT BREAKER TRIPPED — ROLLOUT AUTO-PAUSED
              </div>
              <div style={{ fontSize: 12, color: '#fca5a5', marginTop: 2 }}>
                {circuitAlert.message}
              </div>
            </div>
          </div>

          <button
            onClick={() => handleTogglePause(circuitAlert.version, true)}
            disabled={rolloutMutation.isPending}
            style={{
              padding: '6px 14px',
              background: '#ef4444',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            Override & Resume Rollout
          </button>
        </div>
      )}

      {/* Fleet Node Health KPI Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12 }}>
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>TOTAL SCOUT NODES</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)' }}><AnimatedNumber value={totalDevices} /></div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>Enrolled Windows Fleet</div>
        </div>

        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>🟢 HEALTHY</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#10b981' }}><AnimatedNumber value={health.healthy} /></div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>Checked in &lt; 10m</div>
        </div>

        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>🔵 UPDATE AVAILABLE</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#e4e4e7' }}><AnimatedNumber value={health.update_available} /></div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>Silent download staged</div>
        </div>

        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>🟡 UPDATE REQUIRED</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#f59e0b' }}><AnimatedNumber value={health.update_required} /></div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>Below minimum floor</div>
        </div>

        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>🔴 UPDATE FAILED / ROLLBACK</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#ef4444' }}><AnimatedNumber value={health.failed} /></div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>Crash/verification failed</div>
        </div>

        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>⚫ STALE / OFFLINE</div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#a1a1aa' }}><AnimatedNumber value={health.stale + health.offline} /></div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>No recent heartbeat</div>
        </div>
      </div>

      {/* Two-Column Section: Version Adoption & Staged Rollouts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: 16 }}>
        {/* Left Column: Version Distribution Progress Meters */}
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <h4 style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              Version Adoption Distribution
            </h4>
            <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--mono)' }}>
              {versionDist.length} Versions Active
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {versionDist.map((item) => {
              const isBelow = item.is_below_minimum
              const barColor = isBelow ? '#ef4444' : (item.percentage > 50 ? '#10b981' : '#d4d4d8')

              return (
                <div key={item.version} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--text-primary)' }}>
                        v{item.version}
                      </span>
                      {isBelow && (
                        <span style={{ fontSize: 10, background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', padding: '1px 6px', borderRadius: 4, fontWeight: 700 }}>
                          &lt; minimum
                        </span>
                      )}
                    </div>
                    <span style={{ fontWeight: 700, color: barColor }}>
                      {item.percentage}% ({item.device_count} nodes)
                    </span>
                  </div>

                  {/* Progress Bar Meter */}
                  <div style={{ width: '100%', height: 8, background: '#232326', borderRadius: 4, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${Math.max(2, item.percentage)}%`,
                        height: '100%',
                        background: barColor,
                        borderRadius: 4,
                        transition: 'width 0.4s ease',
                      }}
                    />
                  </div>
                </div>
              )
            })}

            {versionDist.length === 0 && (
              <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-secondary)', fontSize: 12 }}>
                No version telemetry reported yet.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Release Management & Staged Rollout Controls */}
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div>
              <h4 style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                Release Channels & Staged Rollout Controls
              </h4>
              <p style={{ fontSize: 11, color: 'var(--text-secondary)', margin: '2px 0 0' }}>
                Control distribution cohorts (10%, 25%, 50%, 100%) and automatic circuit breaker pauses.
              </p>
            </div>
            <button
              onClick={() => refetch()}
              style={{
                background: '#232326', border: '1px solid #27272a', color: '#a1a1aa',
                borderRadius: 6, padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11
              }}
            >
              <RefreshCw size={12} />
              <span>Refresh</span>
            </button>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '8px 6px', fontWeight: 600 }}>VERSION</th>
                  <th style={{ padding: '8px 6px', fontWeight: 600 }}>CHANNEL</th>
                  <th style={{ padding: '8px 6px', fontWeight: 600 }}>STATUS</th>
                  <th style={{ padding: '8px 6px', fontWeight: 600 }}>ADOPTION</th>
                  <th style={{ padding: '8px 6px', fontWeight: 600 }}>FAIL RATE</th>
                  <th style={{ padding: '8px 6px', fontWeight: 600 }}>ROLLOUT COHORT</th>
                  <th style={{ padding: '8px 6px', fontWeight: 600 }}>CONTROL</th>
                </tr>
              </thead>
              <tbody>
                {releases.map((rel) => {
                  const isTripped = rel.status === 'CIRCUIT_TRIPPED'
                  const isPaused = rel.is_paused || isTripped
                  const statusColor = isTripped ? '#ef4444' : (isPaused ? '#f59e0b' : (rel.channel === 'stable' ? '#10b981' : '#e4e4e7'))

                  return (
                    <tr key={rel.id || rel.version} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '10px 6px', fontWeight: 800, fontFamily: 'var(--mono)' }}>
                        v{rel.version}
                      </td>
                      <td style={{ padding: '10px 6px' }}>
                        <span style={{ textTransform: 'uppercase', fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#232326', color: '#a1a1aa' }}>
                          {rel.channel}
                        </span>
                      </td>
                      <td style={{ padding: '10px 6px' }}>
                        <span style={{ fontSize: 10, fontWeight: 800, color: statusColor, padding: '2px 6px', borderRadius: 4, background: `${statusColor}15`, border: `1px solid ${statusColor}40` }}>
                          {isTripped ? 'CIRCUIT TRIPPED' : (isPaused ? 'PAUSED' : 'LIVE')}
                        </span>
                      </td>
                      <td style={{ padding: '10px 6px', fontWeight: 700 }}>
                        {rel.adoption_percentage}%
                      </td>
                      <td style={{ padding: '10px 6px' }}>
                        <span style={{ color: rel.failure_rate > 3.0 ? '#ef4444' : '#10b981', fontWeight: 700 }}>
                          {rel.failure_rate}%
                        </span>
                      </td>
                      <td style={{ padding: '10px 6px' }}>
                        <div style={{ display: 'flex', gap: 4 }}>
                          {[10, 25, 50, 100].map((pct) => (
                            <button
                              key={pct}
                              disabled={updatingVersion === rel.version}
                              onClick={() => handleRolloutChange(rel.version, pct)}
                              style={{
                                padding: '2px 6px',
                                fontSize: 10,
                                fontWeight: 700,
                                borderRadius: 4,
                                border: rel.rollout_percentage === pct ? '1px solid #d4d4d8' : '1px solid #27272a',
                                background: rel.rollout_percentage === pct ? '#e4e4e7' : '#0b1120',
                                color: rel.rollout_percentage === pct ? '#fff' : '#a1a1aa',
                                cursor: 'pointer',
                              }}
                            >
                              {pct}%
                            </button>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: '10px 6px' }}>
                        <button
                          disabled={updatingVersion === rel.version}
                          onClick={() => handleTogglePause(rel.version, isPaused)}
                          style={{
                            padding: '3px 8px',
                            fontSize: 11,
                            fontWeight: 700,
                            borderRadius: 6,
                            border: isPaused ? '1px solid #10b981' : '1px solid #f59e0b',
                            background: isPaused ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                            color: isPaused ? '#10b981' : '#f59e0b',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 4,
                          }}
                        >
                          {isPaused ? <Play size={10} /> : <Pause size={10} />}
                          <span>{isPaused ? 'Resume' : 'Pause'}</span>
                        </button>
                      </td>
                    </tr>
                  )
                })}

                {releases.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '18px 0', color: 'var(--text-secondary)' }}>
                      No software releases published yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
