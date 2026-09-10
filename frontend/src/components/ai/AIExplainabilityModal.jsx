import React, { useState } from 'react'
import { toast } from 'react-hot-toast'
import api from '../../services/api'
import EvidenceBadge from './EvidenceBadge'

/**
 * Deep Explainability Modal ("Why?" Engine)
 * Implements IBM Explainable AI and NIST Trustworthy AI guidelines.
 * Decomposes composite rankings into transparent dimensions and records recruiter feedback.
 */
export default function AIExplainabilityModal({ isOpen, onClose, explanationData, candidateId }) {
  const [submitting, setSubmitting] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [feedbackCategory, setFeedbackCategory] = useState('')
  const [feedbackNotes, setFeedbackNotes] = useState('')

  if (!isOpen || !explanationData) return null

  const {
    candidate_name = 'Candidate',
    overall_score = 88,
    confidence = 0.92,
    confidence_tier = 'High',
    breakdown = {},
    evidence = [],
    provenance = {}
  } = explanationData

  const handleFeedback = async (isPositive) => {
    try {
      setSubmitting(true)
      await api.post('/ai/feedback', {
        entity_type: 'candidate',
        entity_id: String(candidateId || candidate_name),
        is_positive: isPositive,
        feedback_category: feedbackCategory || (isPositive ? 'USEFUL' : 'INCORRECT'),
        user_notes: feedbackNotes || undefined,
        original_data: explanationData
      })
      setFeedbackSent(true)
      toast.success(isPositive ? 'Feedback recorded: Marked useful!' : 'Feedback recorded: AI will adjust future recommendations.')
    } catch (err) {
      console.error('Feedback submission error:', err)
      toast.error('Could not submit feedback.')
    } finally {
      setSubmitting(false)
    }
  }

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
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        animation: 'fadeIn 0.15s ease-out'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          overflowY: 'auto',
          backgroundColor: 'var(--bg-card, #0f172a)',
          border: '1px solid var(--border-ai, rgba(139, 92, 246, 0.35))',
          borderRadius: '12px',
          boxShadow: '0 20px 40px -15px rgba(0, 0, 0, 0.7), 0 0 25px rgba(139, 92, 246, 0.15)',
          padding: '24px',
          color: 'var(--text-primary, #f8fafc)',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border, #1e293b)', paddingBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '14px', color: '#a78bfa' }}>✦</span>
              <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#a78bfa' }}>
                Explainability Engine
              </span>
              <EvidenceBadge status={provenance.profile_status || 'OBSERVED'} confidence={confidence} />
            </div>
            <h2 style={{ fontSize: '20px', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
              Why was {candidate_name} ranked here?
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary, #94a3b8)',
              fontSize: '20px',
              cursor: 'pointer',
              padding: '4px 8px',
              borderRadius: '6px'
            }}
          >
            ✕
          </button>
        </div>

        {/* Overall Score Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08), rgba(56, 189, 248, 0.05))',
            border: '1px solid rgba(139, 92, 246, 0.2)',
            borderRadius: '10px',
            padding: '16px 20px'
          }}
        >
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Overall Calibrated Match Score
            </div>
            <div style={{ fontSize: '28px', fontWeight: 900, color: '#38bdf8', marginTop: '2px' }}>
              {overall_score}<span style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>/100</span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Confidence Tier
            </div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: '#10b981', marginTop: '2px' }}>
              {confidence_tier} ({Math.round(confidence * 100)}%)
            </div>
          </div>
        </div>

        {/* Multidimensional Factor Decomposition */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Multidimensional Score Decomposition
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {Object.entries(breakdown).map(([key, item]) => (
              <div key={key} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 45px', alignItems: 'center', gap: '12px', fontSize: '13px' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{item.label}</span>
                  <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Weight: {item.weight}</span>
                </div>
                <div style={{ height: '8px', backgroundColor: 'var(--border, #1e293b)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${item.score}%`,
                      background: item.score >= 90 ? 'linear-gradient(90deg, #38bdf8, #818cf8)' : 'linear-gradient(90deg, #818cf8, #a78bfa)',
                      borderRadius: '4px',
                      transition: 'width 0.6s ease'
                    }}
                  />
                </div>
                <div style={{ textAlign: 'right', fontWeight: 700, color: '#38bdf8' }}>
                  {item.score}%
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Evidence & Grounding Trail */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)', marginBottom: '10px' }}>
            Concrete Corroborating Evidence
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {evidence.map((fact, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  fontSize: '12px',
                  lineHeight: '1.5',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border, #1e293b)',
                  borderRadius: '6px',
                  padding: '8px 12px'
                }}
              >
                <span style={{ color: '#38bdf8', fontWeight: 800 }}>✓</span>
                <span style={{ color: 'var(--text-secondary)' }}>{fact}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Provenance & Calibrated Data Badges */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)' }}>Attribution:</span>
          <EvidenceBadge status={provenance.email_status || 'VERIFIED'} size="sm" />
          <EvidenceBadge status={provenance.phone_status || 'INFERRED'} size="sm" />
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', marginLeft: 'auto' }}>
            Source: {provenance.source || 'TalentOps Scout Fusion'}
          </span>
        </div>

        {/* Human Recruiter Feedback Loop */}
        <div
          style={{
            borderTop: '1px solid var(--border, #1e293b)',
            paddingTop: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-secondary)' }}>
              Is this score evaluation accurate?
            </span>
            {feedbackSent ? (
              <span style={{ fontSize: '12px', color: '#10b981', fontWeight: 700 }}>
                ✓ Thank you! Evaluation recorded.
              </span>
            ) : (
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  disabled={submitting}
                  onClick={() => handleFeedback(true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '6px 14px',
                    fontSize: '12px',
                    fontWeight: 700,
                    borderRadius: '6px',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    color: '#10b981',
                    cursor: 'pointer'
                  }}
                >
                  👍 Useful
                </button>
                <button
                  disabled={submitting}
                  onClick={() => handleFeedback(false)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '6px 14px',
                    fontSize: '12px',
                    fontWeight: 700,
                    borderRadius: '6px',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    color: '#ef4444',
                    cursor: 'pointer'
                  }}
                >
                  👎 Needs Correction
                </button>
              </div>
            )}
          </div>

          {!feedbackSent && (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
              {['Wrong Seniority', 'Wrong Company', 'Outdated Profile', 'Missing Skills', 'Location Mismatch'].map((reason) => (
                <button
                  key={reason}
                  onClick={() => setFeedbackCategory(reason)}
                  style={{
                    padding: '3px 8px',
                    fontSize: '10px',
                    borderRadius: '4px',
                    border: feedbackCategory === reason ? '1px solid #a78bfa' : '1px solid var(--border, #1e293b)',
                    backgroundColor: feedbackCategory === reason ? 'rgba(167, 139, 250, 0.2)' : 'transparent',
                    color: feedbackCategory === reason ? '#a78bfa' : 'var(--text-secondary)',
                    cursor: 'pointer'
                  }}
                >
                  {reason}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
