import React, { useState } from 'react'
import EvidenceBadge from './EvidenceBadge'

/**
 * AI Insight & Evidence Card
 * Displays an intelligence claim with calibrated uncertainty, provenance attribution,
 * and an inline/modal "Why?" explainability trigger.
 */
export default function AIInsightCard({
  title,
  claim,
  confidence = 0.90,
  provenanceStatus = 'OBSERVED',
  source = 'TalentOps Scout',
  evidence = [],
  onExplain,
  category = 'TALENT_SIGNAL'
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card, #121214)',
        border: '1px solid var(--border-ai, rgba(161, 161, 170, 0.25))',
        borderRadius: '10px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        transition: 'all 0.2s ease',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
      }}
    >
      {/* Top row: Category, Provenance Badge, and Source */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#a1a1aa' }}>✦</span>
          <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
            {title || category}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <EvidenceBadge status={provenanceStatus} confidence={confidence} size="sm" />
          <span style={{ fontSize: '10px', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px' }}>
            {source}
          </span>
        </div>
      </div>

      {/* Main Claim */}
      <div style={{ fontSize: '13px', fontWeight: 600, lineHeight: 1.5, color: 'var(--text-primary, #fafafa)' }}>
        {claim}
      </div>

      {/* Expandable Evidence Points */}
      {evidence && evidence.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {(expanded ? evidence : evidence.slice(0, 2)).map((ev, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '6px',
                fontSize: '11px',
                color: 'var(--text-secondary)',
                lineHeight: 1.4
              }}
            >
              <span style={{ color: '#e4e4e7', fontWeight: 700 }}>•</span>
              <span>{ev}</span>
            </div>
          ))}
          {evidence.length > 2 && (
            <button
              onClick={() => setExpanded(!expanded)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#e4e4e7',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                textAlign: 'left',
                padding: '2px 0'
              }}
            >
              {expanded ? '▲ Show less' : `▼ +${evidence.length - 2} more corroborating facts`}
            </button>
          )}
        </div>
      )}

      {/* Action footer */}
      {onExplain && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border, #232326)', paddingTop: '8px' }}>
          <button
            onClick={onExplain}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'rgba(161, 161, 170, 0.1)',
              border: '1px solid rgba(161, 161, 170, 0.25)',
              borderRadius: '6px',
              color: '#d4d4d8',
              fontSize: '11px',
              fontWeight: 700,
              padding: '4px 10px',
              cursor: 'pointer'
            }}
          >
            <span>[Why?]</span>
            <span>Inspect Evidence</span>
          </button>
        </div>
      )}
    </div>
  )
}
