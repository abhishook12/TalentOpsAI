import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ShieldCheck, Zap, Activity, Clock, Server, Power, AlertTriangle, CheckCircle2 } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'
import { ShellCard, Badge } from './CommandCenter'
import AnimatedNumber from './ui/AnimatedNumber'

export default function OperationsConsole() {
  const queryClient = useQueryClient()
  const [toggleLoading, setToggleLoading] = useState(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['fleet-operations-stats'],
    queryFn: async () => {
      const res = await api.get('/scout/operations/stats')
      return res.data
    },
    refetchInterval: 5000,
  })

  const killSwitches = data?.kill_switches || {
    capture_engine_enabled: true,
    sync_enabled: true,
    ai_signals_enabled: true,
  }

  const handleToggleKillSwitch = async (switchName, currentVal) => {
    const nextVal = !currentVal
    const confirmMsg = nextVal
      ? `Enable ${switchName.replace(/_/g, ' ')} across all fleet nodes?`
      : `EMERGENCY ACTION: Remotely pause ${switchName.replace(/_/g, ' ')} across all active Scout nodes?`

    if (!window.confirm(confirmMsg)) return

    setToggleLoading(switchName)
    try {
      await api.post('/scout/operations/killswitch', {
        switch_name: switchName,
        enabled: nextVal,
      })
      toast.success(`${switchName.replace(/_/g, ' ')} is now ${nextVal ? 'ENABLED' : 'PAUSED'}`)
      queryClient.invalidateQueries(['fleet-operations-stats'])
      refetch()
    } catch (err) {
      toast.error('Failed to update kill switch')
    } finally {
      setToggleLoading(null)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* KPI Stats Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
        <ShellCard title="Fleet Queue Backlog">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 26, fontWeight: 800, color: data?.queue_backlog_depth > 50 ? '#f59e0b' : '#e4e4e7' }}>
                <AnimatedNumber value={data?.queue_backlog_depth || 0} />
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                Pending staging observations
              </div>
            </div>
            <div style={{ width: 42, height: 42, borderRadius: 10, background: 'rgba(228, 228, 231, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#e4e4e7' }}>
              <Server size={20} />
            </div>
          </div>
        </ShellCard>

        <ShellCard title="Sync Success Rate">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#10b981' }}>
                {data?.sync_success_rate || 99.1}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                Acknowledged delta packets
              </div>
            </div>
            <div style={{ width: 42, height: 42, borderRadius: 10, background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981' }}>
              <CheckCircle2 size={20} />
            </div>
          </div>
        </ShellCard>

        <ShellCard title="Avg Sync Latency">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#a1a1aa' }}>
                {data?.avg_sync_latency_sec || 1.4}s
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                Edge packet delivery time
              </div>
            </div>
            <div style={{ width: 42, height: 42, borderRadius: 10, background: 'rgba(161, 161, 170, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a1a1aa' }}>
              <Clock size={20} />
            </div>
          </div>
        </ShellCard>

        <ShellCard title="Active Edge Nodes">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#d4d4d8' }}>
                {data?.active_nodes_count || 0} / {data?.total_nodes_count || 0}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                Scout 2.0 instances online
              </div>
            </div>
            <div style={{ width: 42, height: 42, borderRadius: 10, background: 'rgba(212, 212, 216, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d4d4d8' }}>
              <Activity size={20} />
            </div>
          </div>
        </ShellCard>
      </div>

      {/* Remote Kill Switches Card */}
      <div style={{
        background: '#0b1329',
        border: '1px solid #232326',
        borderRadius: 12,
        padding: 20,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Power size={18} color="#ef4444" />
              <h4 style={{ margin: 0, fontSize: 15, fontWeight: 800, color: '#fafafa' }}>
                Fleet Operations & Remote Kill Switches
              </h4>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: 11, color: '#a1a1aa' }}>
              Instantly control remote edge subsystems across all connected user instances without client redeployment.
            </p>
          </div>
          <Badge status={killSwitches.capture_engine_enabled && killSwitches.sync_enabled ? 'success' : 'warning'}>
            {killSwitches.capture_engine_enabled && killSwitches.sync_enabled ? 'OPERATIONAL' : 'THROTTLED'}
          </Badge>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
          {/* Switch 1: Capture Engine */}
          <div style={{
            background: '#070d1e',
            border: `1px solid ${killSwitches.capture_engine_enabled ? '#1e3a8a' : '#7f1d1d'}`,
            borderRadius: 10,
            padding: 16,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div>
              <div style={{ fontWeight: 700, color: '#fafafa', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>Screen Capture Engine</span>
                <span style={{
                  fontSize: 10,
                  padding: '1px 6px',
                  borderRadius: 4,
                  background: killSwitches.capture_engine_enabled ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                  color: killSwitches.capture_engine_enabled ? '#10b981' : '#ef4444',
                  fontWeight: 800,
                }}>
                  {killSwitches.capture_engine_enabled ? 'ENABLED' : 'PAUSED'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#a1a1aa', marginTop: 4 }}>
                Win32 visual window tracking & OCR
              </div>
            </div>
            <button
              disabled={toggleLoading === 'capture_engine_enabled'}
              onClick={() => handleToggleKillSwitch('capture_engine_enabled', killSwitches.capture_engine_enabled)}
              style={{
                padding: '6px 14px',
                borderRadius: 6,
                border: 'none',
                background: killSwitches.capture_engine_enabled ? '#dc2626' : '#16a34a',
                color: '#fff',
                fontSize: 11,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {killSwitches.capture_engine_enabled ? 'Pause Capture' : 'Enable Capture'}
            </button>
          </div>

          {/* Switch 2: Sync & Ingestion */}
          <div style={{
            background: '#070d1e',
            border: `1px solid ${killSwitches.sync_enabled ? '#1e3a8a' : '#7f1d1d'}`,
            borderRadius: 10,
            padding: 16,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div>
              <div style={{ fontWeight: 700, color: '#fafafa', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>Fleet Ingestion Sync</span>
                <span style={{
                  fontSize: 10,
                  padding: '1px 6px',
                  borderRadius: 4,
                  background: killSwitches.sync_enabled ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                  color: killSwitches.sync_enabled ? '#10b981' : '#ef4444',
                  fontWeight: 800,
                }}>
                  {killSwitches.sync_enabled ? 'ENABLED' : 'PAUSED'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#a1a1aa', marginTop: 4 }}>
                Local SQLite buffer queue upload to cloud
              </div>
            </div>
            <button
              disabled={toggleLoading === 'sync_enabled'}
              onClick={() => handleToggleKillSwitch('sync_enabled', killSwitches.sync_enabled)}
              style={{
                padding: '6px 14px',
                borderRadius: 6,
                border: 'none',
                background: killSwitches.sync_enabled ? '#dc2626' : '#16a34a',
                color: '#fff',
                fontSize: 11,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {killSwitches.sync_enabled ? 'Pause Sync' : 'Enable Sync'}
            </button>
          </div>

          {/* Switch 3: AI Signals & Enrichment */}
          <div style={{
            background: '#070d1e',
            border: `1px solid ${killSwitches.ai_signals_enabled ? '#1e3a8a' : '#7f1d1d'}`,
            borderRadius: 10,
            padding: 16,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div>
              <div style={{ fontWeight: 700, color: '#fafafa', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>AI Signals & Delta Inference</span>
                <span style={{
                  fontSize: 10,
                  padding: '1px 6px',
                  borderRadius: 4,
                  background: killSwitches.ai_signals_enabled ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                  color: killSwitches.ai_signals_enabled ? '#10b981' : '#ef4444',
                  fontWeight: 800,
                }}>
                  {killSwitches.ai_signals_enabled ? 'ENABLED' : 'PAUSED'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#a1a1aa', marginTop: 4 }}>
                Intent detection & career velocity scoring
              </div>
            </div>
            <button
              disabled={toggleLoading === 'ai_signals_enabled'}
              onClick={() => handleToggleKillSwitch('ai_signals_enabled', killSwitches.ai_signals_enabled)}
              style={{
                padding: '6px 14px',
                borderRadius: 6,
                border: 'none',
                background: killSwitches.ai_signals_enabled ? '#dc2626' : '#16a34a',
                color: '#fff',
                fontSize: 11,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {killSwitches.ai_signals_enabled ? 'Pause AI' : 'Enable AI'}
            </button>
          </div>
        </div>
      </div>

      {/* Security, DLP & Zero Secrets Architecture Card */}
      <div style={{
        background: 'linear-gradient(135deg, #121214 0%, #1e1b4b 100%)',
        border: '1px solid #312e81',
        borderRadius: 12,
        padding: 18,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 14,
      }}>
        <div style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          background: 'rgba(161, 161, 170, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#a1a1aa',
          flexShrink: 0,
          marginTop: 2,
        }}>
          <ShieldCheck size={20} />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: 13, color: '#e0e7ff' }}>
            Scout 2.0 Enterprise Privacy & Boundary Guardrails
          </div>
          <div style={{ fontSize: 11, color: '#d4d4d8', marginTop: 4, lineHeight: 1.5 }}>
            • <strong>Local Data Loss Prevention (DLP):</strong> Pre-upload regex scanning automatically masks credentials, private keys, and session tokens with <code>[REDACTED_SECRET]</code>.<br />
            • <strong>Scope-Aware Observation:</strong> Connectors strictly respect authorized profile views with zero DOM injection and zero bot automation.<br />
            • <strong>Cryptographic Provenance:</strong> Every observation packet carries a verifiable lineage signature for enterprise defense audits.
          </div>
        </div>
      </div>
    </div>
  )
}
