import React, { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import api from '../../services/api'
import EvidenceBadge from './EvidenceBadge'

/**
 * AI Autonomy Controls & Governance Console
 * Implements EU AI Act and NIST Trustworthy AI compliance:
 * - 4-level calibrated autonomy slider
 * - Granular agent permission gates (Read / Analyze / Propose / Write / Enrich / Export / Message)
 * - Live AI Audit Log inspector
 */
export default function AIAutonomySettings() {
  const [autonomyLevel, setAutonomyLevel] = useState(3)
  const [permissions, setPermissions] = useState({
    read: true,
    analyze: true,
    propose: true,
    write: false,
    enrich: false,
    export: true,
    message: false
  })
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const AUTONOMY_LEVELS = [
    {
      level: 1,
      title: 'Level 1: Advisory / Assist',
      desc: 'AI provides suggestions and insights only. All candidate modifications, searches, and workflows require 100% manual execution.'
    },
    {
      level: 2,
      title: 'Level 2: Co-Pilot / Prepare',
      desc: 'AI prepares candidate shortlists, drafts outreach templates, and flags duplicates. Requires manual button click to stage or execute.'
    },
    {
      level: 3,
      title: 'Level 3: Supervised / Execute with Approval (Default)',
      desc: 'AI autonomously stages batch actions, enriches records, and identifies data repairs, presenting a Safety Gate diff preview before human sign-off.'
    },
    {
      level: 4,
      title: 'Level 4: High Autonomy / Bounded',
      desc: 'AI autonomously executes non-destructive operations (e.g. data hygiene, auto-merging high-confidence duplicates) within policy bounds.'
    }
  ]

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [prefRes, logRes] = await Promise.all([
          api.get('/ai/preferences'),
          api.get('/ai/audit-logs?limit=15')
        ])
        if (prefRes.data) {
          setAutonomyLevel(prefRes.data.autonomy_level || 3)
          if (prefRes.data.permissions) setPermissions(prefRes.data.permissions)
        }
        if (logRes.data?.logs) {
          setAuditLogs(logRes.data.logs)
        }
      } catch (err) {
        console.error('Failed to load AI autonomy settings:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleSave = async () => {
    try {
      setSaving(true)
      await api.post('/ai/preferences', {
        autonomy_level: autonomyLevel,
        permissions
      })
      toast.success('AI Governance policy saved successfully!')
    } catch (err) {
      console.error('Save preferences error:', err)
      toast.error('Failed to save governance settings.')
    } finally {
      setSaving(false)
    }
  }

  const togglePermission = (key) => {
    setPermissions((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card, #0f172a)',
        border: '1px solid var(--border-ai, rgba(139, 92, 246, 0.3))',
        borderRadius: '12px',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '13px', color: '#10b981' }}>🛡</span>
            <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: '#10b981', letterSpacing: '0.08em' }}>
              Governance & Safety Controls
            </span>
            <EvidenceBadge status="VERIFIED" confidence={1.0} size="sm" />
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
            AI Autonomy Policy & Agent Permission Matrix
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Configure machine agency boundaries in accordance with NIST Trustworthy AI and EU AI Act standards.
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            background: 'linear-gradient(135deg, #10b981, #38bdf8)',
            border: 'none',
            borderRadius: '8px',
            padding: '8px 20px',
            color: '#fff',
            fontSize: '12px',
            fontWeight: 700,
            cursor: saving ? 'not-allowed' : 'pointer'
          }}
        >
          {saving ? 'Saving...' : 'Save Policy'}
        </button>
      </div>

      {/* Autonomy Level Slider Cards */}
      <div>
        <div style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Platform Autonomy Level:
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          {AUTONOMY_LEVELS.map((al) => {
            const isSelected = autonomyLevel === al.level
            return (
              <div
                key={al.level}
                onClick={() => setAutonomyLevel(al.level)}
                style={{
                  backgroundColor: isSelected ? 'rgba(139, 92, 246, 0.12)' : 'var(--bg-base, #090d14)',
                  border: `1px solid ${isSelected ? '#8b5cf6' : 'var(--border, #1e293b)'}`,
                  borderRadius: '8px',
                  padding: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  transition: 'all 0.2s ease',
                  boxShadow: isSelected ? '0 0 15px rgba(139, 92, 246, 0.25)' : 'none'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: 800, color: isSelected ? '#38bdf8' : 'var(--text-primary)' }}>
                    {al.title}
                  </span>
                  {isSelected && <span style={{ color: '#10b981', fontWeight: 900 }}>✓</span>}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {al.desc}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Granular Permission Matrix */}
      <div>
        <div style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          Granular Agent Action Permissions:
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
          {[
            { key: 'read', label: 'Read & Parse Data', desc: 'Allow AI to read talent & company records' },
            { key: 'analyze', label: 'Analyze & Score', desc: 'Allow score decomposition and ranking' },
            { key: 'propose', label: 'Propose Shortlists', desc: 'Allow generating recommendations' },
            { key: 'write', label: 'Direct Database Writes', desc: 'Allow writing changes without confirmation' },
            { key: 'enrich', label: 'Auto-Enrich Contacts', desc: 'Allow background data doctor lookups' },
            { key: 'export', label: 'Export Data', desc: 'Allow AI to export reports and CSVs' },
            { key: 'message', label: 'Autonomous Messaging', desc: 'Allow sending outreach without sign-off' }
          ].map((perm) => (
            <div
              key={perm.key}
              onClick={() => togglePermission(perm.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                backgroundColor: 'var(--bg-base, #090d14)',
                border: `1px solid ${permissions[perm.key] ? 'rgba(56, 189, 248, 0.3)' : 'var(--border, #1e293b)'}`,
                borderRadius: '8px',
                cursor: 'pointer'
              }}
            >
              <div>
                <div style={{ fontSize: '12px', fontWeight: 700, color: permissions[perm.key] ? '#38bdf8' : 'var(--text-primary)' }}>
                  {perm.label}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{perm.desc}</div>
              </div>
              <div
                style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '4px',
                  border: `1px solid ${permissions[perm.key] ? '#38bdf8' : 'var(--border, #1e293b)'}`,
                  backgroundColor: permissions[perm.key] ? '#38bdf8' : 'transparent',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#000',
                  fontSize: '11px',
                  fontWeight: 900
                }}
              >
                {permissions[perm.key] ? '✓' : ''}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Live AI Audit Log */}
      <div>
        <div style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '10px' }}>
          Recent Enterprise AI Invocations & Telemetry:
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '200px', overflowY: 'auto' }}>
          {auditLogs.length === 0 ? (
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', padding: '12px', textAlign: 'center' }}>
              No audit entries recorded yet.
            </div>
          ) : (
            auditLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '140px 180px 120px 80px 80px',
                  gap: '12px',
                  alignItems: 'center',
                  padding: '8px 12px',
                  backgroundColor: 'var(--bg-base, #090d14)',
                  border: '1px solid var(--border, #1e293b)',
                  borderRadius: '6px',
                  fontSize: '11px'
                }}
              >
                <span style={{ color: 'var(--text-secondary)' }}>{log.created_at?.slice(0, 19).replace('T', ' ')}</span>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{log.action_type}</span>
                <span style={{ color: '#38bdf8' }}>{log.model_name}</span>
                <span style={{ color: '#10b981' }}>{log.latency_ms}ms</span>
                <span style={{ color: 'var(--text-secondary)' }}>${(log.cost_usd || 0).toFixed(5)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
