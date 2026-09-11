import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  X, Laptop, ShieldCheck, Zap, AlertCircle, RefreshCw, CheckCircle2,
  Database, UserCheck, Activity, Award, BarChart3, Globe, History,
  Trash2, RotateCcw, AlertTriangle, Cpu, Terminal
} from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

export default function ScoutUserProfileDrawer({ userId, onClose, onRefreshList }) {
  const [activeTab, setActiveTab] = useState('contributions')
  const [actionLoading, setActionLoading] = useState(null)

  const { data: profile, isLoading, refetch } = useQuery({
    queryKey: ['scout-user-profile', userId],
    queryFn: async () => {
      const res = await api.get(`/scout/users/${userId}`)
      return res.data
    },
    enabled: !!userId,
  })

  if (!userId) return null

  const handleRevokeDevice = async (deviceId) => {
    if (!window.confirm(`Revoke device access for ${deviceId}? This device will immediately lose API connectivity.`)) return
    setActionLoading(deviceId)
    try {
      await api.post(`/scout/installations/${deviceId}/revoke`)
      toast.success(`Device ${deviceId} revoked`)
      refetch()
      if (onRefreshList) onRefreshList()
    } catch (err) {
      toast.error('Failed to revoke device')
    } finally {
      setActionLoading(null)
    }
  }

  const handleEnableDevice = async (deviceId) => {
    setActionLoading(deviceId)
    try {
      await api.post(`/scout/installations/${deviceId}/enable`)
      toast.success(`Device ${deviceId} enabled`)
      refetch()
      if (onRefreshList) onRefreshList()
    } catch (err) {
      toast.error('Failed to enable device')
    } finally {
      setActionLoading(null)
    }
  }

  const handleForceUpdate = async (deviceId) => {
    setActionLoading(deviceId)
    try {
      await api.post(`/scout/installations/${deviceId}/force-update`, { mandatory: true })
      toast.success(`Mandatory update flagged for ${deviceId}`)
      refetch()
    } catch (err) {
      toast.error('Failed to flag update')
    } finally {
      setActionLoading(null)
    }
  }

  const handleResetPairing = async () => {
    if (!window.confirm(`Reset pairing for ${profile?.header?.email}? All current desktop tokens will be invalidated.`)) return
    setActionLoading('pairing')
    try {
      await api.post(`/scout/users/${userId}/reset-pairing`)
      toast.success('Pairing reset successfully')
      refetch()
      if (onRefreshList) onRefreshList()
    } catch (err) {
      toast.error('Failed to reset pairing')
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1050,
      background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)',
      display: 'flex', justifyContent: 'flex-end', animation: 'fadeIn 0.2s ease-out'
    }}>
      <div style={{
        width: '100%', maxWidth: 780, height: '100%', background: '#0b0b0c',
        borderLeft: '1px solid #232326', display: 'flex', flexDirection: 'column',
        boxShadow: '-10px 0 40px rgba(0,0,0,0.8)', overflow: 'hidden'
      }}>
        {/* Drawer Header */}
        <div style={{
          padding: '24px 28px', borderBottom: '1px solid #232326',
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
          background: 'linear-gradient(180deg, rgba(16,185,129,0.05) 0%, rgba(9,13,22,0) 100%)'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
              <h2 style={{ fontSize: 22, fontWeight: 800, color: '#fafafa', margin: 0, letterSpacing: '-0.3px' }}>
                {profile?.header?.name || 'Scout User Profile'}
              </h2>
              {profile?.quality_scores && (
                <span style={{
                  fontSize: 11, fontWeight: 800, padding: '3px 8px', borderRadius: 6,
                  background: profile.quality_scores.overall_score >= 80 ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)',
                  color: profile.quality_scores.overall_score >= 80 ? '#4ade80' : '#fbbf24',
                  border: `1px solid ${profile.quality_scores.overall_score >= 80 ? 'rgba(16,185,129,0.4)' : 'rgba(245,158,11,0.4)'}`
                }}>
                  {profile.quality_scores.tier} • {profile.quality_scores.overall_score}% QUALITY
                </span>
              )}
            </div>

            <div style={{ display: 'flex', gap: 16, fontSize: 13, color: '#a1a1aa' }}>
              <span>{profile?.header?.email}</span>
              <span>•</span>
              <span>Tenant: <strong style={{ color: '#d4d4d8' }}>{profile?.header?.tenant}</strong></span>
              <span>•</span>
              <span>Role: <strong style={{ color: '#d4d4d8' }}>{profile?.header?.role}</strong></span>
            </div>

            <div style={{ display: 'flex', gap: 18, marginTop: 10, fontSize: 11, color: '#71717a' }}>
              <span>Registered: {profile?.header?.account_created}</span>
              <span>First Scout: {profile?.header?.first_scout_registration}</span>
              <span>Last Active: {profile?.header?.last_active}</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <button
              onClick={() => refetch()}
              style={{ padding: '6px 10px', background: '#232326', color: '#a1a1aa', border: '1px solid #27272a', borderRadius: 6, cursor: 'pointer' }}
              title="Refresh Profile"
            >
              <RefreshCw size={14} />
            </button>
            <button
              onClick={onClose}
              style={{ padding: '6px 10px', background: '#232326', color: '#fafafa', border: '1px solid #27272a', borderRadius: 6, cursor: 'pointer' }}
              title="Close Drawer"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: 6, padding: '12px 28px', borderBottom: '1px solid #232326', background: '#0c121e' }}>
          {[
            { id: 'contributions', label: '📊 Contributions', icon: BarChart3 },
            { id: 'quality', label: '🎯 Quality & Impact', icon: Award },
            { id: 'devices', label: `💻 Devices (${profile?.devices?.length || 0})`, icon: Laptop },
            { id: 'sources', label: '🌐 Sources', icon: Globe },
            { id: 'provenance', label: '🔍 Audit Provenance', icon: History },
            { id: 'actions', label: '🛠️ Admin Controls', icon: ShieldCheck },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 700,
                cursor: 'pointer', border: 'none', transition: 'all 0.15s ease',
                background: activeTab === tab.id ? 'rgba(16,185,129,0.18)' : 'transparent',
                color: activeTab === tab.id ? '#10b981' : '#a1a1aa',
                borderBottom: activeTab === tab.id ? '2px solid #10b981' : '2px solid transparent'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Drawer Body Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
          {isLoading ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#a1a1aa' }}>
              <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
              <div>Loading forensic Scout intelligence...</div>
            </div>
          ) : (
            <>
              {/* TAB 1: DATA CONTRIBUTIONS */}
              {activeTab === 'contributions' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  {/* Volume vs Value Banner */}
                  <div style={{
                    padding: '16px 20px', borderRadius: 12, background: 'rgba(212, 212, 216,0.08)',
                    border: '1px solid rgba(212, 212, 216,0.2)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20
                  }}>
                    <div>
                      <div style={{ fontSize: 11, color: '#f4f4f5', fontWeight: 700, textTransform: 'uppercase' }}>
                        Raw Ingestion Volume
                      </div>
                      <div style={{ fontSize: 26, fontWeight: 900, color: '#fafafa', margin: '4px 0' }}>
                        {profile?.contributions?.raw_observations?.toLocaleString() || 0}
                      </div>
                      <div style={{ fontSize: 12, color: '#71717a' }}>
                        Observations streamed from edge desktop companion
                      </div>
                    </div>

                    <div style={{ borderLeft: '1px solid rgba(212, 212, 216,0.2)', paddingLeft: 20 }}>
                      <div style={{ fontSize: 11, color: '#4ade80', fontWeight: 700, textTransform: 'uppercase' }}>
                        Canonical Records Improved
                      </div>
                      <div style={{ fontSize: 26, fontWeight: 900, color: '#4ade80', margin: '4px 0' }}>
                        {profile?.contributions?.canonical_records_improved?.toLocaleString() || 0}
                      </div>
                      <div style={{ fontSize: 12, color: '#71717a' }}>
                        Unique, deduplicated records committed to Master DB
                      </div>
                    </div>
                  </div>

                  {/* Entity Breakdown Cards */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                    {[
                      { label: 'New People', val: profile?.contributions?.people_created, color: '#e4e4e7' },
                      { label: 'People Enriched', val: profile?.contributions?.people_enriched, color: '#4ade80' },
                      { label: 'Companies', val: profile?.contributions?.companies_discovered, color: '#fbbf24' },
                      { label: 'Contacts (Emails/Phones)', val: profile?.contributions?.contacts_discovered, color: '#a1a1aa' },
                    ].map((card, i) => (
                      <div key={i} style={{ padding: '14px 16px', background: '#0e1526', border: '1px solid #232326', borderRadius: 10 }}>
                        <div style={{ fontSize: 11, color: '#71717a', fontWeight: 600 }}>{card.label}</div>
                        <div style={{ fontSize: 20, fontWeight: 800, color: card.color, marginTop: 4 }}>
                          +{card.val || 0}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Specific Fields Discovered */}
                  <div style={{ background: '#0e1526', border: '1px solid #232326', borderRadius: 12, padding: '18px 20px' }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#d4d4d8', marginBottom: 14 }}>
                      Verified Field Discoveries
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>Direct Emails</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#fafafa', marginTop: 2 }}>
                          {profile?.contributions?.emails_discovered || 0}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>Phone Numbers</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#fafafa', marginTop: 2 }}>
                          {profile?.contributions?.phones_discovered || 0}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>LinkedIn Profiles</div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#fafafa', marginTop: 2 }}>
                          {profile?.contributions?.linkedin_profiles || 0}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 14-Day Timeline Preview */}
                  <div style={{ background: '#0e1526', border: '1px solid #232326', borderRadius: 12, padding: '18px 20px' }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#d4d4d8', marginBottom: 12 }}>
                      14-Day Contribution Timeline
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {(profile?.timeline || []).slice(-7).map((t, idx) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #232326', fontSize: 12 }}>
                          <span style={{ color: '#a1a1aa' }}>{t.date}</span>
                          <span style={{ color: '#4ade80', fontWeight: 700 }}>+{t.people} people</span>
                          <span style={{ color: '#e4e4e7' }}>+{t.companies} companies</span>
                          <span style={{ color: '#a1a1aa' }}>+{t.contacts} contacts</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: QUALITY & IMPACT */}
              {activeTab === 'quality' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  {/* Quality Radar Scorecards */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                    {[
                      { label: 'Volume Score', val: profile?.quality_scores?.volume_score, desc: 'Logarithmic scale of useful discoveries' },
                      { label: 'Quality Score', val: profile?.quality_scores?.quality_score, desc: 'Accepted vs rejected ratio' },
                      { label: 'Uniqueness Score', val: profile?.quality_scores?.uniqueness_score, desc: 'Originality vs duplicate ratio' },
                      { label: 'Completeness Score', val: profile?.quality_scores?.completeness_score, desc: 'Average fields populated per lead' },
                      { label: 'Freshness Score', val: profile?.quality_scores?.freshness_score, desc: 'Recency & streaming continuity' },
                      { label: 'Overall Quality Index', val: profile?.quality_scores?.overall_score, desc: 'Weighted composite rating', highlight: true },
                    ].map((q, i) => (
                      <div key={i} style={{
                        padding: '16px 18px', borderRadius: 10,
                        background: q.highlight ? 'rgba(16,185,129,0.12)' : '#0e1526',
                        border: `1px solid ${q.highlight ? 'rgba(16,185,129,0.35)' : '#232326'}`
                      }}>
                        <div style={{ fontSize: 11, color: q.highlight ? '#4ade80' : '#71717a', fontWeight: 700 }}>{q.label}</div>
                        <div style={{ fontSize: 24, fontWeight: 900, color: q.highlight ? '#10b981' : '#fafafa', margin: '4px 0' }}>
                          {q.val || 0}%
                        </div>
                        <div style={{ fontSize: 10, color: '#71717a', lineHeight: 1.4 }}>{q.desc}</div>
                      </div>
                    ))}
                  </div>

                  {/* Downstream Impact Details */}
                  <div style={{ background: '#0e1526', border: '1px solid #232326', borderRadius: 12, padding: '20px' }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#d4d4d8', marginBottom: 16 }}>
                      Canonical Master Database Impact
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>Canonical Entities Created</div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: '#e4e4e7', marginTop: 2 }}>
                          {profile?.data_quality_impact?.canonical_entities_created || 0}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>Existing Entities Enriched</div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: '#4ade80', marginTop: 2 }}>
                          {profile?.data_quality_impact?.existing_entities_enriched || 0}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>Corrections Proposed / Accepted</div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: '#fbbf24', marginTop: 2 }}>
                          {profile?.data_quality_impact?.corrections_accepted || 0}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>Duplicates Prevented</div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: '#a1a1aa', marginTop: 2 }}>
                          {profile?.data_quality_impact?.duplicates_detected || 0}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>Quarantined for Review</div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: '#f59e0b', marginTop: 2 }}>
                          {profile?.data_quality_impact?.quarantined_observations || 0}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 11, color: '#71717a' }}>Low Confidence Rejections</div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: '#ef4444', marginTop: 2 }}>
                          {profile?.data_quality_impact?.rejected_observations || 0}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: DEVICES & INSTALLATIONS */}
              {activeTab === 'devices' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {(profile?.devices || []).length === 0 ? (
                    <div style={{ padding: 30, textAlign: 'center', color: '#71717a' }}>
                      No Scout devices registered for this user yet.
                    </div>
                  ) : (
                    (profile?.devices || []).map((dev, idx) => (
                      <div key={idx} style={{
                        background: '#0e1526', border: '1px solid #232326', borderRadius: 12, padding: '18px 20px',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                      }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                            <Laptop size={16} color={dev.is_active ? '#10b981' : '#ef4444'} />
                            <span style={{ fontSize: 14, fontWeight: 700, color: '#fafafa' }}>
                              {dev.device_name}
                            </span>
                            <span style={{
                              fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
                              background: dev.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                              color: dev.is_active ? '#4ade80' : '#ef4444'
                            }}>
                              {dev.is_active ? 'ACTIVE' : 'REVOKED'}
                            </span>
                            <span style={{ fontSize: 11, color: '#71717a' }}>v{dev.scout_version}</span>
                          </div>

                          <div style={{ fontSize: 11, color: '#71717a', display: 'flex', gap: 14 }}>
                            <span>Device ID: <strong style={{ color: '#a1a1aa' }}>{dev.device_id}</strong></span>
                            <span>OS: <strong style={{ color: '#a1a1aa' }}>{dev.os}</strong></span>
                            <span>Queue: <strong style={{ color: '#a1a1aa' }}>{dev.queue_size} items</strong></span>
                            <span>Last Seen: <strong style={{ color: '#a1a1aa' }}>{dev.last_seen ? dev.last_seen.slice(0, 16).replace('T', ' ') : '—'}</strong></span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: 8 }}>
                          <button
                            onClick={() => handleForceUpdate(dev.device_id)}
                            disabled={actionLoading === dev.device_id}
                            style={{
                              padding: '6px 12px', background: '#232326', color: '#e4e4e7',
                              border: '1px solid #27272a', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer'
                            }}
                          >
                            Force Update
                          </button>
                          {dev.is_active ? (
                            <button
                              onClick={() => handleRevokeDevice(dev.device_id)}
                              disabled={actionLoading === dev.device_id}
                              style={{
                                padding: '6px 12px', background: 'rgba(239,68,68,0.15)', color: '#ef4444',
                                border: '1px solid rgba(239,68,68,0.3)', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer'
                              }}
                            >
                              Revoke
                            </button>
                          ) : (
                            <button
                              onClick={() => handleEnableDevice(dev.device_id)}
                              disabled={actionLoading === dev.device_id}
                              style={{
                                padding: '6px 12px', background: 'rgba(16,185,129,0.15)', color: '#10b981',
                                border: '1px solid rgba(16,185,129,0.3)', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer'
                              }}
                            >
                              Enable
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* TAB 4: SOURCE ATTRIBUTION */}
              {activeTab === 'sources' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div style={{ fontSize: 13, color: '#a1a1aa', marginBottom: 6 }}>
                    Breakdown of verified discoveries across authorized integration sources:
                  </div>
                  {Object.entries(profile?.source_breakdown || {}).map(([src, count], idx) => {
                    let srcColor = '#e4e4e7';
                    let srcBg = 'rgba(228, 228, 231, 0.12)';
                    if (src === 'ZoomInfo') { srcColor = '#f43f5e'; srcBg = 'rgba(244, 63, 94, 0.15)'; }
                    else if (src === 'LinkedIn') { srcColor = '#e4e4e7'; srcBg = 'rgba(228, 228, 231, 0.15)'; }
                    else if (src === 'Apollo') { srcColor = '#eab308'; srcBg = 'rgba(234, 179, 8, 0.15)'; }
                    else if (src === 'Microsoft Teams') { srcColor = '#a1a1aa'; srcBg = 'rgba(161, 161, 170, 0.15)'; }
                    else if (src === 'Google Chat') { srcColor = '#10b981'; srcBg = 'rgba(16, 185, 129, 0.15)'; }
                    return (
                      <div key={idx} style={{
                        padding: '14px 18px', background: '#0e1526', border: '1px solid #232326', borderRadius: 10,
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{
                            padding: '4px 8px', borderRadius: 6, fontSize: 11, fontWeight: 800,
                            background: srcBg, color: srcColor
                          }}>
                            {src}
                          </span>
                          <span style={{ fontSize: 13, color: '#a1a1aa' }}>
                            {src === 'ZoomInfo' ? 'B2B Org & Contact Intelligence' : src === 'LinkedIn' ? 'Candidate Profiles & Recruiter' : src === 'Apollo' ? 'Direct Sourcing & Leads' : 'Collaboration Stream'}
                          </span>
                        </div>
                        <span style={{ fontSize: 16, fontWeight: 900, color: '#10b981' }}>
                          {count} observations
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* TAB 5: AUDIT PROVENANCE */}
              {activeTab === 'provenance' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{ fontSize: 13, color: '#a1a1aa', marginBottom: 6 }}>
                    Forensic provenance audit trail connecting raw edge observations to master database records:
                  </div>
                  {(profile?.provenance_trail || []).map((p, idx) => (
                    <div key={idx} style={{
                      padding: '12px 16px', background: '#0e1526', border: '1px solid #232326', borderRadius: 8,
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12
                    }}>
                      <div>
                        <div style={{ fontWeight: 700, color: '#fafafa', display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span>{p.candidate_name}</span>
                          <span style={{ color: '#a1a1aa' }}>• {p.company_name} ({p.title})</span>
                          {p.canonical_profile_url && (
                            <a
                              href={p.canonical_profile_url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ color: '#38bdf8', fontSize: 11, textDecoration: 'none', fontWeight: 600 }}
                            >
                              [Open ↗]
                            </a>
                          )}
                        </div>
                        <div style={{ fontSize: 11, color: '#71717a', marginTop: 2 }}>
                          {p.source_url} • Capture: {p.capture_id} • {p.timestamp}
                        </div>
                        {p.evidence_checklist && p.evidence_checklist.length > 0 && (
                          <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {p.evidence_checklist.map((chk, ci) => (
                              <span
                                key={ci}
                                style={{
                                  fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                                  background: 'rgba(16,185,129,0.12)', color: '#4ade80', border: '1px solid rgba(16,185,129,0.25)'
                                }}
                              >
                                ✓ {chk}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <span style={{
                          fontSize: 10, fontWeight: 800, padding: '2px 6px', borderRadius: 4,
                          background: p.decision === 'ENRICHED' ? 'rgba(16,185,129,0.15)' : 'rgba(228, 228, 231,0.15)',
                          color: p.decision === 'ENRICHED' ? '#4ade80' : '#e4e4e7'
                        }}>
                          {p.decision}
                        </span>
                        <div style={{ fontSize: 10, color: '#71717a', marginTop: 2 }}>
                          Conf: {p.confidence}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 6: ADMIN CONTROLS */}
              {activeTab === 'actions' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div style={{ padding: '16px 20px', background: '#0e1526', border: '1px solid #232326', borderRadius: 12 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fafafa', marginBottom: 4 }}>
                      Reset User Pairing & Clear Credentials
                    </div>
                    <p style={{ fontSize: 12, color: '#71717a', margin: '0 0 14px' }}>
                      Invalidates all activation codes and revokes all active desktop tokens for this user. The user will be required to enter a fresh 10-minute pairing code to reconnect Scout.
                    </p>
                    <button
                      onClick={handleResetPairing}
                      disabled={actionLoading === 'pairing'}
                      style={{
                        padding: '8px 16px', background: 'rgba(239,68,68,0.15)', color: '#ef4444',
                        border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer'
                      }}
                    >
                      Reset Pairing for {profile?.header?.email}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
