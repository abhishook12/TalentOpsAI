import React from 'react'
import EvidenceBadge from './EvidenceBadge'

/**
 * Agentic Action Preview & Approval Gate
 * Strict safety gate requiring explicit human confirmation before committing
 * autonomous modifications, bulk enrichments, or data repairs.
 */
export default function AIActionPreviewModal({
  isOpen,
  onClose,
  onConfirm,
  actionTitle = 'Execute AI Autonomous Operations',
  plannedChanges = [],
  summaryMetrics = { added: 0, updated: 0, merged: 0, flagged: 0 }
}) {
  if (!isOpen) return null

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(5, 8, 15, 0.85)',
        backdropFilter: 'blur(6px)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '85vh',
          overflowY: 'auto',
          backgroundColor: 'var(--bg-card, #121214)',
          border: '1px solid var(--border-ai, rgba(161, 161, 170, 0.4))',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 30px rgba(161, 161, 170, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          gap: '18px'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border, #232326)', paddingBottom: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '12px', color: '#f59e0b' }}>⚠</span>
              <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: '#f59e0b', letterSpacing: '0.08em' }}>
                AI Autonomy Safety Gate (Level 3 Required)
              </span>
              <EvidenceBadge status="INFERRED" confidence={0.95} size="sm" />
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
              {actionTitle}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', fontSize: '20px', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>

        {/* Warning Banner */}
        <div
          style={{
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: '8px',
            padding: '12px 16px',
            fontSize: '12px',
            color: 'var(--text-primary)',
            lineHeight: 1.5
          }}
        >
          <strong>Human Review Mandate:</strong> The AI engine has staged these operations for execution.
          Review the affected records and scope below before signing off. An instant Undo token will be minted upon execution.
        </div>

        {/* Impact Scope Breakdown */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
          <div style={{ background: 'var(--bg-base, #0b0b0c)', border: '1px solid var(--border, #232326)', borderRadius: '6px', padding: '10px', textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Records Added</div>
            <div style={{ fontSize: '18px', fontWeight: 900, color: '#10b981', marginTop: '2px' }}>{summaryMetrics.added || 0}</div>
          </div>
          <div style={{ background: 'var(--bg-base, #0b0b0c)', border: '1px solid var(--border, #232326)', borderRadius: '6px', padding: '10px', textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Updated</div>
            <div style={{ fontSize: '18px', fontWeight: 900, color: '#e4e4e7', marginTop: '2px' }}>{summaryMetrics.updated || 0}</div>
          </div>
          <div style={{ background: 'var(--bg-base, #0b0b0c)', border: '1px solid var(--border, #232326)', borderRadius: '6px', padding: '10px', textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Merged</div>
            <div style={{ fontSize: '18px', fontWeight: 900, color: '#a1a1aa', marginTop: '2px' }}>{summaryMetrics.merged || 0}</div>
          </div>
          <div style={{ background: 'var(--bg-base, #0b0b0c)', border: '1px solid var(--border, #232326)', borderRadius: '6px', padding: '10px', textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Flagged Stale</div>
            <div style={{ fontSize: '18px', fontWeight: 900, color: '#ef4444', marginTop: '2px' }}>{summaryMetrics.flagged || 0}</div>
          </div>
        </div>

        {/* Planned Action List */}
        <div>
          <div style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Operations Staged for Commit:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {(plannedChanges.length > 0 ? plannedChanges : [
              'Enrich contact intelligence for 14 candidates via Scout companion network',
              'Auto-harmonize 8 job titles from "Sr. Dev" to "Senior Software Engineer"',
              'Quarantine 3 bounce-risk email records into Sentinel buffer'
            ]).map((desc, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  backgroundColor: 'var(--bg-base, #0b0b0c)',
                  border: '1px solid var(--border, #232326)',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  fontSize: '12px',
                  color: 'var(--text-primary)'
                }}
              >
                <span style={{ color: '#e4e4e7' }}>✓</span>
                <span>{desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', borderTop: '1px solid var(--border, #232326)', paddingTop: '14px' }}>
          <button
            onClick={onClose}
            style={{
              background: 'var(--bg-base, #0b0b0c)',
              border: '1px solid var(--border, #232326)',
              borderRadius: '6px',
              padding: '8px 16px',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              cursor: 'pointer'
            }}
          >
            Cancel & Abort
          </button>
          <button
            onClick={onConfirm}
            style={{
              background: 'linear-gradient(135deg, #10b981, #e4e4e7)',
              border: 'none',
              borderRadius: '6px',
              padding: '8px 20px',
              fontSize: '12px',
              fontWeight: 700,
              color: '#fff',
              cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(16, 185, 129, 0.3)'
            }}
          >
            ✓ Sign Off & Execute
          </button>
        </div>
      </div>
    </div>
  )
}
