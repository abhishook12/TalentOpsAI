import React, { useState, useEffect, useRef } from 'react'
import { toast } from 'react-hot-toast'
import api from '../../services/api'
import EvidenceBadge from './EvidenceBadge'

/**
 * Enterprise Context-Aware Persistent AI Side Panel
 * Grounded in PostgreSQL, DuckDB Parquet (437k talent pool), and Scout fleet telemetry.
 */
export default function AISidePanel({ isOpen, onToggle, currentContext }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hi. What would you like me to help with?'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeCandidate, setActiveCandidate] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const handleSendMessageRef = useRef(null)

  useEffect(() => {
    const handleSetContext = (e) => {
      if (e.detail) {
        setActiveCandidate(e.detail)
        const name = e.detail.recruiter_name || e.detail.name || 'Candidate'
        const title = e.detail.title || 'Specialist'
        const company = e.detail.company || e.detail.company_name || 'Organization'
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            text: `🎯 Focused context on ${name} (${title} @ ${company}). You can ask me to draft personalized outreach, explain match score, or search similar talent.`
          }
        ])
      }
    }

    const handleOpenCopilot = (e) => {
      if (!isOpen && onToggle) onToggle()
      if (e.detail?.prompt) {
        setTimeout(() => handleSendMessageRef.current?.(e.detail.prompt, 'QUICK_ACTION'), 300)
      }
    }

    window.addEventListener('talentops:set-copilot-context', handleSetContext)
    window.addEventListener('talentops:open-copilot', handleOpenCopilot)
    return () => {
      window.removeEventListener('talentops:set-copilot-context', handleSetContext)
      window.removeEventListener('talentops:open-copilot', handleOpenCopilot)
    }
  }, [isOpen, onToggle])

  const handleSendMessage = async (textToSend, triggerType = 'USER_MESSAGE') => {
    handleSendMessageRef.current = handleSendMessage
    const query = textToSend || input
    if (!query.trim()) return

    const newMsgs = [...messages, { role: 'user', text: query }]
    setMessages(newMsgs)
    setInput('')
    setLoading(true)

    try {
      const res = await api.post('/ai/command', {
        query,
        trigger_type: triggerType,
        mode: 'chat',
        context: { ...currentContext, candidate: activeCandidate },
        history: messages
      })

      const reply = res.data.summary || 'I analyzed your request against the talent intelligence database.'
      setMessages([
        ...newMsgs,
        {
          role: 'assistant',
          text: reply,
          intent: res.data.intent,
          results: res.data.results,
          scout_telemetry: res.data.scout_telemetry,
          campaign_metrics: res.data.campaign_metrics,
          data_quality: res.data.data_quality,
          outreach_draft: res.data.outreach_draft,
          suggested_actions: res.data.suggested_actions,
          source_transparency: res.data.source_transparency,
          active_filters: res.data.active_filters
        }
      ])
    } catch (err) {
      console.error('AI chat error:', err)
      setMessages([
        ...newMsgs,
        {
          role: 'assistant',
          text: 'Encountered a momentary connection pause. Please verify backend availability or try again.'
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  // Route-aware suggested prompts
  const getSuggestedPrompts = () => {
    if (activeCandidate) {
      const name = (activeCandidate.recruiter_name || activeCandidate.name || 'Candidate').split(' ')[0]
      return [
        `Draft outreach for ${name}`,
        'Explain match evidence',
        'Find more talent like this'
      ]
    }
    const path = currentContext?.path || ''
    if (path.includes('/campaign')) {
      return [
        'Check campaign delivery rates',
        'Who replied to my sequences?',
        'Show active outreach campaigns'
      ]
    }
    if (path.includes('/scout')) {
      return [
        'Show Scout fleet health',
        'How many records captured today?',
        'Latest Scout forensic discoveries'
      ]
    }
    if (path.includes('/data-quality') || path.includes('/sentinel')) {
      return [
        'Analyze database quality health',
        'Find duplicate candidates',
        'Show unverified emails'
      ]
    }
    return [
      'Find senior Java developers in Texas',
      'Show Scout fleet health',
      'Analyze database quality health'
    ]
  }

  return (
    <>
      {/* Floating Toggle Pill when panel is closed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          title="Open TalentOps Copilot"
          style={{
            position: 'fixed',
            right: '20px',
            bottom: '24px',
            zIndex: 9998,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'linear-gradient(135deg, #27272a, #3f3f46)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '30px',
            padding: '10px 18px',
            color: '#fff',
            fontWeight: 800,
            fontSize: '13px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
            cursor: 'pointer',
            transition: 'transform 0.2s ease, box-shadow 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.05)')}
          onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
        >
          <span style={{ fontSize: '15px', color: '#10b981' }}>✦</span>
          <span>Copilot</span>
        </button>
      )}

      {/* Persistent Side Panel Drawer */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            right: 0,
            top: 0,
            bottom: 0,
            width: '420px',
            backgroundColor: 'var(--bg-card, #121214)',
            borderLeft: '1px solid var(--border-ai, rgba(255, 255, 255, 0.12))',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '-10px 0 35px rgba(0, 0, 0, 0.7)',
            animation: 'slideInRight 0.2s ease-out'
          }}
        >
          {/* Drawer Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 20px',
              borderBottom: '1px solid var(--border, #232326)',
              backgroundColor: 'rgba(18, 18, 20, 0.95)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '6px',
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontSize: '13px',
                  fontWeight: 900
                }}
              >
                ✦
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-primary, #f4f4f5)' }}>
                  TalentOps Copilot
                </div>
                <div style={{ fontSize: '10px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981' }} />
                  Operational Intelligence Engine
                </div>
              </div>
            </div>

            <button
              onClick={onToggle}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border, #232326)',
                borderRadius: '6px',
                color: 'var(--text-secondary, #a1a1aa)',
                fontSize: '14px',
                cursor: 'pointer',
                padding: '4px 8px',
                lineHeight: 1
              }}
              title="Close Copilot"
            >
              ✕
            </button>
          </div>

          {/* Quick Context Strip */}
          <div
            style={{
              padding: '8px 16px',
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              borderBottom: '1px solid var(--border, #232326)',
              fontSize: '11px',
              color: 'var(--text-secondary, #a1a1aa)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '6px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, overflow: 'hidden' }}>
              <span style={{ color: activeCandidate ? '#38bdf8' : '#10b981' }}>●</span>
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {activeCandidate
                  ? `Focus: ${activeCandidate.recruiter_name || activeCandidate.name} (${activeCandidate.company || activeCandidate.company_name || 'Enterprise'})`
                  : `Workspace: ${currentContext?.name || 'Talent Intelligence Console'}`}
              </span>
            </div>
            {activeCandidate && (
              <button
                onClick={() => setActiveCandidate(null)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid var(--border, #232326)',
                  borderRadius: '4px',
                  color: 'var(--text-secondary, #a1a1aa)',
                  fontSize: '10px',
                  padding: '2px 6px',
                  cursor: 'pointer'
                }}
                title="Clear candidate focus"
              >
                Clear
              </button>
            )}
          </div>

          {/* Chat Message Stream */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px'
            }}
          >
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '92%',
                  backgroundColor: m.role === 'user' ? '#27272a' : 'var(--bg-base, #0b0b0c)',
                  color: m.role === 'user' ? '#ffffff' : 'var(--text-primary, #e4e4e7)',
                  border: m.role === 'user' ? '1px solid rgba(255,255,255,0.1)' : '1px solid var(--border, #232326)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  fontSize: '12px',
                  lineHeight: 1.5,
                  boxShadow: '0 3px 10px rgba(0, 0, 0, 0.3)'
                }}
              >
                {/* Main Text Content */}
                <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>

                {/* ── RICH RESULT: CANDIDATE CARDS ── */}
                {m.results && m.results.length > 0 && (
                  <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ fontSize: '10px', fontWeight: 800, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Identified Talent Matches ({m.results.length})
                    </div>
                    {m.results.map((c, cIdx) => (
                      <div
                        key={c.id || cIdx}
                        style={{
                          background: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '8px',
                          padding: '10px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px'
                        }}
                      >
                        {/* Candidate Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div
                              style={{
                                width: '28px',
                                height: '28px',
                                borderRadius: '50%',
                                background: 'linear-gradient(135deg, #3f3f46, #52525b)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '11px',
                                fontWeight: 800,
                                color: '#fff'
                              }}
                            >
                              {c.name ? c.name.charAt(0).toUpperCase() : 'T'}
                            </div>
                            <div>
                              <div style={{ fontWeight: 800, fontSize: '12px', color: '#f4f4f5' }}>
                                {c.name}
                              </div>
                              <div style={{ fontSize: '11px', color: 'var(--text-secondary, #a1a1aa)' }}>
                                {c.title} • <span style={{ color: '#e4e4e7' }}>{c.company}</span>
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 800,
                                padding: '2px 6px',
                                borderRadius: '4px',
                                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                                color: '#10b981',
                                border: '1px solid rgba(16, 185, 129, 0.3)'
                              }}
                            >
                              {c.match_score || 92}% Match
                            </span>
                            <EvidenceBadge status={c.data_confidence || 'OBSERVED'} size="xs" />
                          </div>
                        </div>

                        {/* Location & Contact */}
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary, #a1a1aa)', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          <span>📍 {c.location || 'US'}</span>
                          {c.email && <span>✉ {c.email}</span>}
                          {c.phone && <span>📞 {c.phone}</span>}
                        </div>

                        {/* Evidence & Skills */}
                        {c.evidence && c.evidence.length > 0 && (
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {c.evidence.map((ev, evI) => (
                              <span
                                key={evI}
                                style={{
                                  fontSize: '9px',
                                  backgroundColor: 'rgba(56, 189, 248, 0.1)',
                                  color: '#38bdf8',
                                  padding: '1px 6px',
                                  borderRadius: '3px',
                                  border: '1px solid rgba(56, 189, 248, 0.2)'
                                }}
                              >
                                {ev}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Action Bar */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px', paddingTop: '6px', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
                          <span style={{ fontSize: '9px', color: '#71717a' }}>
                            {c.source || 'TalentOps Parquet'}
                          </span>

                          <div style={{ display: 'flex', gap: '6px' }}>
                            <button
                              onClick={() => handleSendMessage(`Draft outreach for ${c.name}`)}
                              style={{
                                background: 'rgba(16, 185, 129, 0.15)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                borderRadius: '4px',
                                color: '#10b981',
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: '2px 8px',
                                cursor: 'pointer'
                              }}
                            >
                              ✉ Draft Email
                            </button>
                            {c.email && (
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(c.email)
                                  toast.success(`Copied ${c.email}`)
                                }}
                                style={{
                                  background: 'rgba(255, 255, 255, 0.05)',
                                  border: '1px solid var(--border, #232326)',
                                  borderRadius: '4px',
                                  color: 'var(--text-secondary, #a1a1aa)',
                                  fontSize: '10px',
                                  padding: '2px 6px',
                                  cursor: 'pointer'
                                }}
                                title="Copy Email"
                              >
                                📋
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── RICH RESULT: SCOUT FLEET TELEMETRY ── */}
                {m.scout_telemetry && (
                  <div
                    style={{
                      marginTop: '12px',
                      background: 'rgba(16, 185, 129, 0.04)',
                      border: '1px solid rgba(16, 185, 129, 0.25)',
                      borderRadius: '8px',
                      padding: '12px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '10px', fontWeight: 800, color: '#10b981', letterSpacing: '0.05em' }}>
                        🛰 SCOUT FLEET TELEMETRY
                      </span>
                      <span style={{ fontSize: '10px', color: '#10b981', fontWeight: 700 }}>
                        ● {m.scout_telemetry.fleet_health || 'Operational'}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginBottom: '8px' }}>
                      <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <div style={{ fontSize: '9px', color: '#a1a1aa' }}>Active Devices</div>
                        <div style={{ fontSize: '14px', fontWeight: 800, color: '#fff' }}>{m.scout_telemetry.active_devices || m.scout_telemetry.total_devices}</div>
                      </div>
                      <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <div style={{ fontSize: '9px', color: '#a1a1aa' }}>Discoveries Today</div>
                        <div style={{ fontSize: '14px', fontWeight: 800, color: '#10b981' }}>{m.scout_telemetry.today_discoveries}</div>
                      </div>
                    </div>

                    <div style={{ fontSize: '10px', color: '#71717a' }}>
                      Desktop Scout release: <strong style={{ color: '#e4e4e7' }}>v{m.scout_telemetry.desktop_version}</strong> • Total captures: {m.scout_telemetry.total_discoveries}
                    </div>
                  </div>
                )}

                {/* ── RICH RESULT: CAMPAIGN METRICS ── */}
                {m.campaign_metrics && (
                  <div
                    style={{
                      marginTop: '12px',
                      background: 'rgba(56, 189, 248, 0.04)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: '8px',
                      padding: '12px'
                    }}
                  >
                    <div style={{ fontSize: '10px', fontWeight: 800, color: '#38bdf8', letterSpacing: '0.05em', marginBottom: '8px' }}>
                      📊 CAMPAIGNS ENGINE VITALS
                    </div>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '11px', marginBottom: '8px' }}>
                      <div>Total: <strong style={{ color: '#fff' }}>{m.campaign_metrics.total_campaigns}</strong></div>
                      <div>Active: <strong style={{ color: '#10b981' }}>{m.campaign_metrics.active_campaigns}</strong></div>
                    </div>
                    {m.campaign_metrics.top_campaigns && m.campaign_metrics.top_campaigns.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {m.campaign_metrics.top_campaigns.slice(0, 2).map((cp) => (
                          <div key={cp.campaign_id} style={{ background: 'rgba(0,0,0,0.2)', padding: '6px 8px', borderRadius: '4px', fontSize: '10px' }}>
                            <div style={{ fontWeight: 700, color: '#f4f4f5' }}>{cp.name}</div>
                            <div style={{ color: '#a1a1aa' }}>Recruiters: {cp.total_recruiters} • Sent: {cp.sent_count} • Reply Rate: {cp.reply_rate}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* ── RICH RESULT: DATA QUALITY ── */}
                {m.data_quality && (
                  <div
                    style={{
                      marginTop: '12px',
                      background: 'rgba(245, 158, 11, 0.04)',
                      border: '1px solid rgba(245, 158, 11, 0.25)',
                      borderRadius: '8px',
                      padding: '12px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '10px', fontWeight: 800, color: '#f59e0b', letterSpacing: '0.05em' }}>
                        🛡 SENTINEL DATA QUALITY HEALTH
                      </span>
                      <span style={{ fontSize: '11px', fontWeight: 800, color: '#10b981' }}>
                        {m.data_quality.health_score}/100
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#a1a1aa' }}>
                      Open flags: <strong style={{ color: '#f4f4f5' }}>{m.data_quality.open_issues_count}</strong> across {m.data_quality.total_records_indexed?.toLocaleString()} indexed records.
                    </div>
                  </div>
                )}

                {/* ── RICH RESULT: OUTREACH DRAFT ── */}
                {m.outreach_draft && (
                  <div
                    style={{
                      marginTop: '12px',
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.15)',
                      borderRadius: '8px',
                      padding: '12px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '10px', fontWeight: 800, color: '#f4f4f5', letterSpacing: '0.05em' }}>
                        ✉ EXECUTIVE OUTREACH DRAFT
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(m.outreach_draft)
                          toast.success('Outreach draft copied to clipboard!')
                        }}
                        style={{
                          background: 'rgba(16, 185, 129, 0.15)',
                          border: '1px solid rgba(16, 185, 129, 0.4)',
                          borderRadius: '4px',
                          color: '#10b981',
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '2px 8px',
                          cursor: 'pointer'
                        }}
                      >
                        📋 Copy
                      </button>
                    </div>
                    <pre
                      style={{
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'inherit',
                        fontSize: '11px',
                        color: 'var(--text-primary, #e4e4e7)',
                        lineHeight: 1.5,
                        background: 'rgba(0, 0, 0, 0.25)',
                        padding: '10px',
                        borderRadius: '6px'
                      }}
                    >
                      {m.outreach_draft}
                    </pre>
                  </div>
                )}

                {/* ── FOLLOW-UP ACTION CHIPS ── */}
                {m.suggested_actions && m.suggested_actions.length > 0 && (
                  <div style={{ marginTop: '10px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {m.suggested_actions.map((act, aIdx) => (
                      <button
                        key={aIdx}
                        onClick={() => handleSendMessage(act, 'QUICK_ACTION')}
                        style={{
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid rgba(255, 255, 255, 0.12)',
                          borderRadius: '12px',
                          padding: '3px 9px',
                          fontSize: '10px',
                          color: '#d4d4d8',
                          cursor: 'pointer',
                          transition: 'background 0.15s ease'
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)')}
                      >
                        {act}
                      </button>
                    ))}
                  </div>
                )}

                {/* ── SOURCE TRANSPARENCY BADGE ── */}
                {m.source_transparency && (
                  <div style={{ marginTop: '8px', fontSize: '9px', color: '#71717a', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ color: '#10b981' }}>✦</span>
                    <span>Grounded via: {m.source_transparency}</span>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div
                style={{
                  alignSelf: 'flex-start',
                  backgroundColor: 'var(--bg-base, #0b0b0c)',
                  border: '1px solid var(--border, #232326)',
                  borderRadius: '10px',
                  padding: '8px 14px',
                  fontSize: '11px',
                  color: '#10b981',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <i className="ti ti-loader-2" style={{ animation: 'spin 1s linear infinite' }} />
                <span>Executing grounded intelligence query...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompt Suggestions */}
          <div style={{ padding: '8px 16px', display: 'flex', gap: '6px', flexWrap: 'wrap', borderTop: '1px solid var(--border, #232326)', backgroundColor: 'rgba(18, 18, 20, 0.6)' }}>
            {getSuggestedPrompts().map((q, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(q, 'QUICK_ACTION')}
                style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border, #232326)',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  fontSize: '10px',
                  color: 'var(--text-secondary, #a1a1aa)',
                  cursor: 'pointer'
                }}
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div
            style={{
              padding: '12px 16px',
              borderTop: '1px solid var(--border, #232326)',
              display: 'flex',
              gap: '8px',
              backgroundColor: 'var(--bg-base, #0b0b0c)'
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Ask Copilot (e.g. 'Find Java developers in Texas')..."
              style={{
                flex: 1,
                backgroundColor: 'var(--bg-card, #121214)',
                border: '1px solid var(--border, #232326)',
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '12px',
                color: 'var(--text-primary, #f4f4f5)',
                outline: 'none'
              }}
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={loading || !input.trim()}
              style={{
                background: loading || !input.trim() ? '#27272a' : 'linear-gradient(135deg, #10b981, #059669)',
                border: 'none',
                borderRadius: '6px',
                padding: '0 14px',
                color: '#fff',
                fontSize: '12px',
                fontWeight: 700,
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s ease'
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </>
  )
}
