import React from 'react'

/**
 * Calibrated Uncertainty Badge Component.
 * Implements Google PAIR and NIST Trustworthy AI standards for explicit confidence communication:
 * - VERIFIED: High certainty, directly corroborated fact (green)
 * - OBSERVED: Directly extracted from platform DOM/Visual capture (cyan)
 * - INFERRED: Machine learning or heuristic derivation (amber)
 * - DERIVED: Graph or cross-entity deduction (indigo)
 * - UNVERIFIED / UNKNOWN: Data missing or requires human confirmation (slate)
 */
export default function EvidenceBadge({ status = 'OBSERVED', confidence, size = 'sm' }) {
  const normStatus = (status || 'OBSERVED').toUpperCase()
  
  let badgeClass = 'ai-badge-observed'
  let icon = '◐'
  let label = 'Observed'

  if (normStatus.includes('VERIF')) {
    badgeClass = 'ai-badge-verified'
    icon = '●'
    label = 'Verified'
  } else if (normStatus.includes('INFER')) {
    badgeClass = 'ai-badge-inferred'
    icon = '△'
    label = 'Inferred'
  } else if (normStatus.includes('DERIV')) {
    badgeClass = 'ai-badge-derived'
    icon = '✦'
    label = 'Derived'
  } else if (normStatus.includes('UNVER') || normStatus.includes('UNK')) {
    badgeClass = 'ai-badge-unknown'
    icon = '?'
    label = 'Unverified'
  }

  const isSmall = size === 'sm'

  return (
    <span
      className={`ai-badge ${badgeClass}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: isSmall ? '2px 7px' : '4px 10px',
        fontSize: isSmall ? '10px' : '12px',
        fontWeight: 700,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        borderRadius: '9999px',
        lineHeight: 1.2,
      }}
      title={`Calibrated Uncertainty: ${label}${confidence ? ` (${Math.round(confidence * 100)}% confidence)` : ''}`}
    >
      <span style={{ fontSize: isSmall ? '9px' : '11px' }}>{icon}</span>
      <span>{label}</span>
      {confidence != null && (
        <span style={{ opacity: 0.75, fontWeight: 500 }}>
          {Math.round(confidence > 1 ? confidence : confidence * 100)}%
        </span>
      )}
    </span>
  )
}
