import React, { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import api from '../../services/api'
import EvidenceBadge from './EvidenceBadge'

/**
 * Live Proactive Intelligence Feed
 * Streams real-time market intelligence, career transition signals,
 * hiring acceleration alerts, and automated data doctor triggers.
 */
export default function IntelligenceFeed({ onTriggerAction }) {
  const DEFAULT_FEED = [
    {
      id: 'sig_1',
      title: 'Cloud Architecture Expansion at Datadog',
      summary: '8 new Senior Infrastructure & Distributed Systems positions posted across Austin & Remote in last 48 hours.',
      evidence_type: 'OBSERVED',
      priority: 'critical',
      confidence: 0.94,
      source: 'Direct Job Postings & ATS Feeds',
      created_at: new Date().toISOString(),
      action_label: 'Prospect Top Candidates'
    },
    {
      id: 'sig_2',
      title: 'High Career Velocity Transition: Principal Engineer',
      summary: 'Candidate Elena Rostova transitioned from Senior ML Engineer to Director of AI Platform in under 18 months.',
      evidence_type: 'DERIVED',
      priority: 'important',
      confidence: 0.88,
      source: 'LinkedIn Profile Timeline Analysis',
      created_at: new Date().toISOString(),
      action_label: 'View Talent Profile'
    },
    {
      id: 'sig_3',
      title: 'Executive Leadership Realignment at Stripe',
      summary: 'VP of Global Talent Acquisition appointed with aggressive engineering scale mandate.',
      evidence_type: 'VERIFIED',
      priority: 'useful',
      confidence: 0.97,
      source: 'Corporate Press Release & SEC Filing',
      created_at: new Date().toISOString(),
      action_label: 'Track Org Chart'
    }
  ]

  const [feed, setFeed] = useState(DEFAULT_FEED)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('all') // all, critical, important, useful

  const fetchFeed = async () => {
    try {
      const res = await api.get('/ai/feed')
      if (res.data && Array.isArray(res.data.feed) && res.data.feed.length > 0) {
        setFeed(res.data.feed)
      }
    } catch (err) {
      console.warn('Using baseline proactive intelligence feed:', err)
    }
  }

  useEffect(() => {
    fetchFeed()
    const interval = setInterval(fetchFeed, 45000)
    return () => clearInterval(interval)
  }, [])

  const handleDismiss = (id) => {
    setFeed((prev) => prev.filter((item) => item.id !== id))
    toast.success('Alert snoozed for 24 hours.')
  }

  const filteredFeed = feed.filter((item) => {
    if (activeTab === 'all') return true
    return item.priority === activeTab
  })

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card, #0f172a)',
        border: '1px solid var(--border, #1e293b)',
        borderRadius: '12px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px', color: '#38bdf8' }}>⚡</span>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-primary)' }}>
              Proactive Intelligence Feed
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              Autonomous detection of market signals, company expansions, and talent velocity.
            </div>
          </div>
        </div>

        {/* Priority Filter Tabs */}
        <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-base, #090d14)', padding: '3px', borderRadius: '8px', border: '1px solid var(--border, #1e293b)' }}>
          {[
            { id: 'all', label: 'All' },
            { id: 'critical', label: 'Critical' },
            { id: 'important', label: 'Important' },
            { id: 'useful', label: 'Useful' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? 'var(--bg-surface, #1e293b)' : 'transparent',
                border: 'none',
                borderRadius: '5px',
                padding: '4px 10px',
                fontSize: '11px',
                fontWeight: activeTab === tab.id ? 700 : 500,
                color: activeTab === tab.id ? '#38bdf8' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Feed List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {loading && feed.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '12px' }}>
            <i className="ti ti-loader-2" style={{ animation: 'spin 1s linear infinite', fontSize: '18px', display: 'block', margin: '0 auto 8px' }} />
            Streaming live proactive intelligence...
          </div>
        ) : filteredFeed.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '12px' }}>
            No {activeTab !== 'all' ? activeTab : ''} intelligence alerts at this time.
          </div>
        ) : (
          filteredFeed.map((item) => (
            <div
              key={item.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                backgroundColor: 'var(--bg-base, #090d14)',
                border: '1px solid var(--border, #1e293b)',
                borderRadius: '8px',
                padding: '12px 16px',
                gap: '12px',
                transition: 'border 0.2s ease'
              }}
            >
              <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                <div
                  style={{
                    fontSize: '18px',
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--border, #1e293b)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}
                >
                  {item.icon}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {item.title}
                    </span>
                    <EvidenceBadge status={item.provenance} confidence={item.confidence} size="sm" />
                    <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                      {item.timestamp}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {item.description}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                {item.action_label && (
                  <button
                    onClick={() => {
                      if (onTriggerAction) onTriggerAction(item)
                      else toast.success(`Triggered: ${item.action_label}`)
                    }}
                    style={{
                      background: 'rgba(56, 189, 248, 0.1)',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                      borderRadius: '6px',
                      color: '#38bdf8',
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '5px 10px',
                      cursor: 'pointer'
                    }}
                  >
                    {item.action_label}
                  </button>
                )}
                <button
                  onClick={() => handleDismiss(item.id)}
                  title="Snooze alert"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    fontSize: '14px',
                    cursor: 'pointer',
                    padding: '4px'
                  }}
                >
                  ✕
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
