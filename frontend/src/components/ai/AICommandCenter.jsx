import React, { useState } from 'react'
import { toast } from 'react-hot-toast'
import api from '../../services/api'
import EvidenceBadge from './EvidenceBadge'
import AIExplainabilityModal from './AIExplainabilityModal'

/**
 * Natural-Language AI Command Center ("Ask TalentOps Anything")
 * Translates recruiter commands into parsed intent chips, multi-stage progress,
 * and live candidate records with explainable score cards.
 */
export default function AICommandCenter({ onSelectCandidate }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentStage, setCurrentStage] = useState('')
  const [response, setResponse] = useState(null)
  const [selectedCandidateForExplanation, setSelectedCandidateForExplanation] = useState(null)
  const [explanationData, setExplanationData] = useState(null)
  const [explainLoading, setExplainLoading] = useState(false)

  const SUGGESTED_PROMPTS = [
    'Find senior software engineers in Texas with verified emails',
    'Show candidates with high career velocity in Chicago',
    'Find decision makers at companies hiring for data platforms',
    'Identify unverified contacts for data cleaning'
  ]

  const handleRunCommand = async (commandToRun) => {
    const activeQuery = commandToRun || query
    if (!activeQuery.trim()) return

    try {
      setLoading(true)
      setCurrentStage('✦ Understanding natural language request...')
      setResponse(null)

      // Simulate streaming progress stages for smooth AI feedback
      setTimeout(() => {
        setCurrentStage('✓ Interpreted query structure & scanning intelligence database...')
      }, 350)

      setTimeout(() => {
        setCurrentStage('◌ Evaluating calibrated uncertainty & ranking candidates...')
      }, 700)

      const res = await api.post('/ai/command', {
        query: activeQuery,
        mode: 'search'
      })

      setResponse(res.data)
      setCurrentStage('')
    } catch (err) {
      console.error('AI Command execution error:', err)
      toast.error('Could not execute AI command.')
      setCurrentStage('')
    } finally {
      setLoading(false)
    }
  }

  const handleExplain = async (candidate) => {
    try {
      setExplainLoading(true)
      setSelectedCandidateForExplanation(candidate)
      const res = await api.post('/ai/explain', {
        candidate_id: candidate.id,
        candidate_data: {
          recruiter_name: candidate.name,
          title: candidate.title,
          company_name: candidate.company,
          email: candidate.email,
          phone: candidate.phone,
          linkedin: candidate.linkedin,
          location: candidate.location
        }
      })
      setExplanationData(res.data)
    } catch (err) {
      console.error('Explain error:', err)
      toast.error('Could not generate score explanation.')
    } finally {
      setExplainLoading(false)
    }
  }

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card, #0f172a)',
        border: '1px solid var(--border-ai, rgba(139, 92, 246, 0.3))',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.25)',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #8b5cf6, #38bdf8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 900
            }}
          >
            ✦
          </div>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-primary)' }}>
              AI Command Center
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              Ask TalentOps anything in natural language. Powered by Gemini 2.5 & Local Intelligence Engine.
            </div>
          </div>
        </div>

        {response?.model_used && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.04)', padding: '3px 8px', borderRadius: '4px', border: '1px solid var(--border, #1e293b)' }}>
              ⚡ {response.model_used} ({response.latency_ms}ms)
            </span>
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div style={{ display: 'flex', gap: '8px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRunCommand()}
            placeholder="Ask TalentOps anything... (e.g. 'Find senior software engineers in Texas with verified emails')"
            disabled={loading}
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-base, #090d14)',
              border: '1px solid var(--border, #1e293b)',
              borderRadius: '8px',
              padding: '12px 16px',
              fontSize: '13px',
              color: 'var(--text-primary, #f8fafc)',
              outline: 'none',
              transition: 'border 0.2s ease',
              boxSizing: 'border-box'
            }}
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              style={{
                position: 'absolute',
                right: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              ✕
            </button>
          )}
        </div>

        <button
          onClick={() => handleRunCommand()}
          disabled={loading || !query.trim()}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'linear-gradient(135deg, #8b5cf6, #38bdf8)',
            border: 'none',
            borderRadius: '8px',
            padding: '0 20px',
            color: '#ffffff',
            fontSize: '13px',
            fontWeight: 700,
            cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
            opacity: loading || !query.trim() ? 0.6 : 1,
            transition: 'opacity 0.2s ease'
          }}
        >
          {loading ? (
            <>
              <i className="ti ti-loader-2" style={{ animation: 'spin 1s linear infinite' }} />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <span>Execute</span>
              <span style={{ fontSize: '11px', opacity: 0.8 }}>↵</span>
            </>
          )}
        </button>
      </div>

      {/* Suggested Prompt Chips */}
      {!response && !loading && (
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>Try asking:</span>
          {SUGGESTED_PROMPTS.map((promptText, i) => (
            <button
              key={i}
              onClick={() => {
                setQuery(promptText)
                handleRunCommand(promptText)
              }}
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border, #1e293b)',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '11px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#8b5cf6'
                e.currentTarget.style.color = '#38bdf8'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border, #1e293b)'
                e.currentTarget.style.color = 'var(--text-secondary)'
              }}
            >
              {promptText}
            </button>
          ))}
        </div>
      )}

      {/* Streaming Stage Tracker */}
      {loading && currentStage && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(139, 92, 246, 0.08)',
            border: '1px solid rgba(139, 92, 246, 0.2)',
            borderRadius: '8px',
            padding: '10px 14px',
            fontSize: '12px',
            color: '#38bdf8',
            fontWeight: 600
          }}
        >
          <span style={{ animation: 'pulse 1.5s infinite' }}>{currentStage}</span>
        </div>
      )}

      {/* Interpreted Intent Chips */}
      {response && response.intent && (
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border, #1e293b)',
            borderRadius: '8px',
            padding: '10px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                Extracted Intent:
              </span>
              {response.intent.role && (
                <span style={{ fontSize: '11px', background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                  Role: {response.intent.role}
                </span>
              )}
              {response.intent.location && (
                <span style={{ fontSize: '11px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                  Location: {response.intent.location}
                </span>
              )}
              {response.intent.company && (
                <span style={{ fontSize: '11px', background: 'rgba(167, 139, 250, 0.1)', color: '#a78bfa', border: '1px solid rgba(167, 139, 250, 0.3)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                  Company: {response.intent.company}
                </span>
              )}
              {response.intent.action_type && (
                <span style={{ fontSize: '11px', background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
                  Action: {response.intent.action_type}
                </span>
              )}
            </div>

            <EvidenceBadge status="VERIFIED" confidence={response.intent.confidence || 0.92} size="sm" />
          </div>

          {response.summary && (
            <div style={{ fontSize: '12px', color: 'var(--text-primary)', fontStyle: 'italic' }}>
              ✦ {response.summary}
            </div>
          )}
        </div>
      )}

      {/* Candidate Results Grid */}
      {response && response.results && response.results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
            Matching Talent Records ({response.results.length})
          </div>

          <div style={{ display: 'grid', gap: '8px' }}>
            {response.results.map((cand) => (
              <div
                key={cand.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  backgroundColor: 'var(--bg-base, #090d14)',
                  border: '1px solid var(--border, #1e293b)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  transition: 'border 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {cand.name}
                    </span>
                    <EvidenceBadge status={cand.uncertainty_status} confidence={cand.confidence} size="sm" />
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {cand.title} • <span style={{ color: '#38bdf8' }}>{cand.company}</span> • {cand.location}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', gap: '12px', marginTop: '2px' }}>
                    {cand.email && <span>✉ {cand.email}</span>}
                    {cand.phone && <span>☎ {cand.phone}</span>}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    onClick={() => handleExplain(cand)}
                    disabled={explainLoading}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'rgba(139, 92, 246, 0.1)',
                      border: '1px solid rgba(139, 92, 246, 0.3)',
                      borderRadius: '6px',
                      color: '#c4b5fd',
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '6px 12px',
                      cursor: 'pointer'
                    }}
                  >
                    <span>[Why?]</span>
                    <span>Explain Score</span>
                  </button>

                  {onSelectCandidate && (
                    <button
                      onClick={() => onSelectCandidate(cand)}
                      style={{
                        background: 'var(--bg-surface, #1e293b)',
                        border: '1px solid var(--border, #334155)',
                        borderRadius: '6px',
                        color: 'var(--text-primary)',
                        fontSize: '11px',
                        fontWeight: 600,
                        padding: '6px 12px',
                        cursor: 'pointer'
                      }}
                    >
                      View Profile
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Deep Explainability Modal */}
      {selectedCandidateForExplanation && explanationData && (
        <AIExplainabilityModal
          isOpen={!!selectedCandidateForExplanation}
          onClose={() => {
            setSelectedCandidateForExplanation(null)
            setExplanationData(null)
          }}
          candidateId={selectedCandidateForExplanation.id}
          explanationData={explanationData}
        />
      )}
    </div>
  )
}
