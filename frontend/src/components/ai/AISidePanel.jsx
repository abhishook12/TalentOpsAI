import React, { useState, useEffect, useRef } from 'react'
import { toast } from 'react-hot-toast'
import api from '../../services/api'
import EvidenceBadge from './EvidenceBadge'

/**
 * Context-Aware Persistent AI Side Panel
 * Collapsible right-hand intelligence companion injected with current screen context.
 */
export default function AISidePanel({ isOpen, onToggle, currentContext }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'TalentOps AI Copilot active. Context initialized for current workspace. How can I assist your sourcing operations today?'
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
  }, [messages])

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
            text: `🎯 Focused context on ${name} (${title} @ ${company}). You can ask me to draft personalized outreach, explain match score, or forecast career velocity.`
          }
        ])
      }
    }

    const handleOpenCopilot = (e) => {
      if (!isOpen && onToggle) onToggle()
      if (e.detail?.prompt) {
        setTimeout(() => handleSendMessageRef.current?.(e.detail.prompt), 300)
      }
    }

    window.addEventListener('talentops:set-copilot-context', handleSetContext)
    window.addEventListener('talentops:open-copilot', handleOpenCopilot)
    return () => {
      window.removeEventListener('talentops:set-copilot-context', handleSetContext)
      window.removeEventListener('talentops:open-copilot', handleOpenCopilot)
    }
  }, [isOpen, onToggle])

  const handleSendMessage = async (textToSend) => {
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
        mode: 'chat',
        context: { ...currentContext, candidate: activeCandidate }
      })

      const reply = res.data.summary || 'I analyzed your request against the talent intelligence database.'
      setMessages([
        ...newMsgs,
        {
          role: 'assistant',
          text: reply,
          intent: res.data.intent,
          results: res.data.results,
          outreach_draft: res.data.outreach_draft
        }
      ])
    } catch (err) {
      console.error('AI chat error:', err)
      setMessages([...newMsgs, { role: 'assistant', text: 'Encountered a momentary connection pause. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Floating Toggle Pill when panel is closed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          title="Open TalentOps AI Copilot"
          style={{
            position: 'fixed',
            right: '20px',
            bottom: '24px',
            zIndex: 9998,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'linear-gradient(135deg, #a1a1aa, #e4e4e7)',
            border: 'none',
            borderRadius: '30px',
            padding: '10px 18px',
            color: '#fff',
            fontWeight: 800,
            fontSize: '13px',
            boxShadow: '0 8px 24px rgba(161, 161, 170, 0.4)',
            cursor: 'pointer',
            transition: 'transform 0.2s ease'
          }}
          onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.05)')}
          onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
        >
          <span style={{ fontSize: '15px' }}>✦</span>
          <span>AI Copilot</span>
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
            width: '380px',
            backgroundColor: 'var(--bg-card, #121214)',
            borderLeft: '1px solid var(--border-ai, rgba(161, 161, 170, 0.3))',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '-10px 0 30px rgba(0, 0, 0, 0.6)',
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
              borderBottom: '1px solid var(--border, #232326)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '6px',
                  background: 'linear-gradient(135deg, #a1a1aa, #e4e4e7)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontSize: '12px',
                  fontWeight: 900
                }}
              >
                ✦
              </div>
              <span style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-primary)' }}>
                TalentOps Copilot
              </span>
              <EvidenceBadge status="OBSERVED" size="sm" />
            </div>

            <button
              onClick={onToggle}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '18px',
                cursor: 'pointer',
                padding: '4px'
              }}
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
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '6px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, overflow: 'hidden' }}>
              <span style={{ color: activeCandidate ? '#e4e4e7' : '#10b981' }}>●</span>
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
                  color: 'var(--text-secondary)',
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
              gap: '12px'
            }}
          >
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '88%',
                  backgroundColor: m.role === 'user' ? '#a1a1aa' : 'var(--bg-base, #0b0b0c)',
                  color: m.role === 'user' ? '#ffffff' : 'var(--text-primary)',
                  border: m.role === 'user' ? 'none' : '1px solid var(--border, #232326)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  fontSize: '12px',
                  lineHeight: 1.5,
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)'
                }}
              >
                {m.text}

                {/* Optional mini results */}
                {m.results && m.results.length > 0 && (
                  <div style={{ marginTop: '8px', borderTop: '1px solid var(--border, #232326)', paddingTop: '6px' }}>
                    <div style={{ fontSize: '10px', fontWeight: 700, color: '#e4e4e7', textTransform: 'uppercase' }}>
                      Identified Top Candidates:
                    </div>
                    {m.results.slice(0, 3).map((c) => (
                      <div key={c.id} style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        • {c.name} ({c.title})
                      </div>
                    ))}
                  </div>
                )}

                {/* Executive Outreach Draft with Copy action */}
                {m.outreach_draft && (
                  <div
                    style={{
                      marginTop: '10px',
                      background: 'rgba(228, 228, 231, 0.04)',
                      border: '1px solid rgba(228, 228, 231, 0.3)',
                      borderRadius: '6px',
                      padding: '10px 12px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '10px', fontWeight: 800, color: '#e4e4e7', letterSpacing: '0.04em' }}>
                        ✉ EXECUTIVE OUTREACH DRAFT
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(m.outreach_draft)
                          toast.success('Outreach draft copied to clipboard!')
                        }}
                        style={{
                          background: 'rgba(228, 228, 231, 0.15)',
                          border: '1px solid rgba(228, 228, 231, 0.4)',
                          borderRadius: '4px',
                          color: '#e4e4e7',
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
                        color: 'var(--text-primary)',
                        lineHeight: 1.5
                      }}
                    >
                      {m.outreach_draft}
                    </pre>
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
                  color: '#e4e4e7',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <i className="ti ti-loader-2" style={{ animation: 'spin 1s linear infinite' }} />
                <span>Thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompt Suggestions */}
          <div style={{ padding: '8px 16px', display: 'flex', gap: '6px', flexWrap: 'wrap', borderTop: '1px solid var(--border, #232326)' }}>
            {(activeCandidate
              ? [
                  `Draft outreach for ${(activeCandidate.recruiter_name || activeCandidate.name || 'Candidate').split(' ')[0]}`,
                  `Explain match score`,
                  `Analyze career velocity`
                ]
              : ['Find senior ML engineers in Austin', 'Analyze database quality health', 'Show hiring expansion signals']
            ).map((q, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(q)}
                style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border, #232326)',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  fontSize: '10px',
                  color: 'var(--text-secondary)',
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
              placeholder="Ask Copilot..."
              style={{
                flex: 1,
                backgroundColor: 'var(--bg-card, #121214)',
                border: '1px solid var(--border, #232326)',
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '12px',
                color: 'var(--text-primary)',
                outline: 'none'
              }}
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={loading || !input.trim()}
              style={{
                background: 'linear-gradient(135deg, #a1a1aa, #e4e4e7)',
                border: 'none',
                borderRadius: '6px',
                padding: '0 12px',
                color: '#fff',
                fontSize: '12px',
                fontWeight: 700,
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer'
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
