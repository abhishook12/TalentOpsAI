import { useState, useEffect, useCallback } from 'react'
import {
  Layers,
  Database,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Play,
  Clock,
  UserCheck,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Filter,
  Radio,
} from 'lucide-react'
import api from '../services/api'
import ScoutNodesPanel from '../components/ScoutNodesPanel'

export default function StagingPipeline() {
  const [summary, setSummary] = useState(null)
  const [records, setRecords] = useState([])
  const [reviewQueue, setReviewQueue] = useState([])
  const [distribution, setDistribution] = useState([])
  const [knowledgeStats, setKnowledgeStats] = useState(null)
  const [knowledgeEntities, setKnowledgeEntities] = useState([])
  const [knowledgeSignals, setKnowledgeSignals] = useState([])
  const [knowledgeObservations, setKnowledgeObservations] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [filterStatus, setFilterStatus] = useState('ALL')
  const [activeTab, setActiveTab] = useState('pipeline') // 'pipeline', 'graph', 'review'

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [sumRes, recRes, revRes, distRes, kStats, kEnts, kSigs, kObs] = await Promise.all([
        api.get('/staging/summary'),
        api.get('/staging/records?limit=30' + (filterStatus !== 'ALL' ? `&status=${filterStatus}` : '')),
        api.get('/staging/review-queue?limit=20'),
        api.get('/staging/decision-distribution'),
        api.get('/knowledge/stats').catch(() => ({ data: null })),
        api.get('/knowledge/entities?limit=20').catch(() => ({ data: { entities: [] } })),
        api.get('/knowledge/signals?limit=20').catch(() => ({ data: { signals: [] } })),
        api.get('/knowledge/observations?limit=20').catch(() => ({ data: { observations: [] } })),
      ])

      setSummary(sumRes.data)
      setRecords(recRes.data?.records || [])
      setReviewQueue(revRes.data?.items || [])
      setDistribution(distRes.data?.distribution || [])
      setKnowledgeStats(kStats?.data)
      setKnowledgeEntities(kEnts?.data?.entities || [])
      setKnowledgeSignals(kSigs?.data?.signals || [])
      setKnowledgeObservations(kObs?.data?.observations || [])
    } catch (err) {
      console.error('Failed to load staging data:', err)
    } finally {
      setLoading(false)
    }
  }, [filterStatus])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handleProcessNow = async () => {
    try {
      setProcessing(true)
      await api.post('/staging/process-now')
      await fetchData()
    } catch (err) {
      alert('Error triggering batch processor: ' + (err.response?.data?.detail || err.message))
    } finally {
      setProcessing(false)
    }
  }

  const handleApprove = async (stagingId) => {
    try {
      await api.post(`/staging/review/${stagingId}/approve`)
      await fetchData()
    } catch (err) {
      alert('Error approving item: ' + err.message)
    }
  }

  const handleReject = async (stagingId) => {
    try {
      await api.post(`/staging/review/${stagingId}/reject`)
      await fetchData()
    } catch (err) {
      alert('Error rejecting item: ' + err.message)
    }
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1400, margin: '0 auto', color: 'var(--text-primary)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <div style={{ padding: 8, background: 'rgba(59, 130, 246, 0.15)', borderRadius: 8, color: '#3b82f6' }}>
              <Layers size={24} />
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
              Discovery Staging & Intelligence Pipeline
            </h1>
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 12, background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', fontWeight: 600 }}>
              MEDALLION ARCHITECTURE
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>
            Raw scraper observations &rarr; Staging bucket &rarr; Batch identity resolution &rarr; Master database
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={fetchData}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 8,
              border: '1px solid var(--border)',
              background: 'var(--card-bg)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            Refresh
          </button>

          <button
            onClick={handleProcessNow}
            disabled={processing}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 18px',
              borderRadius: 8,
              border: 'none',
              background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
              color: '#fff',
              cursor: processing ? 'not-allowed' : 'pointer',
              fontSize: 13,
              fontWeight: 600,
              boxShadow: '0 2px 8px rgba(37, 99, 235, 0.3)',
            }}
          >
            <Play size={14} />
            {processing ? 'Processing Batch...' : 'Process Staging Batch'}
          </button>
        </div>
      </div>

      {/* Medallion Architecture Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, marginBottom: 28 }}>
        {/* Bronze: Raw Staging */}
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 20, position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: '#f59e0b' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Bronze Layer
              </div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>Raw Discovery Staging</div>
            </div>
            <div style={{ padding: 6, background: 'rgba(245, 158, 11, 0.15)', borderRadius: 6, color: '#f59e0b' }}>
              <Database size={18} />
            </div>
          </div>
          <div style={{ fontSize: 32, fontWeight: 700, marginBottom: 4 }}>
            {(summary?.pending || 0) + (summary?.batched || 0)}
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Unprocessed scraper observations waiting in buffer
          </div>
        </div>

        {/* Silver: Resolution & Validation */}
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 20, position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: '#3b82f6' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Silver Layer
              </div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>Resolved Entity Clusters</div>
            </div>
            <div style={{ padding: 6, background: 'rgba(59, 130, 246, 0.15)', borderRadius: 6, color: '#3b82f6' }}>
              <UserCheck size={18} />
            </div>
          </div>
          <div style={{ fontSize: 32, fontWeight: 700, marginBottom: 4 }}>
            {summary?.resolved_persons || 0}
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Consolidated individuals resolved across observations
          </div>
        </div>

        {/* Gold: Master Database */}
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 20, position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: '#10b981' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#10b981', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Gold Layer
              </div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>Committed Master Entities</div>
            </div>
            <div style={{ padding: 6, background: 'rgba(16, 185, 129, 0.15)', borderRadius: 6, color: '#10b981' }}>
              <CheckCircle2 size={18} />
            </div>
          </div>
          <div style={{ fontSize: 32, fontWeight: 700, marginBottom: 4 }}>
            {summary?.committed || 0}
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Verified candidates promoted to master directory
          </div>
        </div>
      </div>

      {/* Decision Distribution Bar */}
      <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 20px', marginBottom: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
            DECISION ENGINE METRICS
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Last Batch Run: {summary?.last_processed_at ? new Date(summary.last_processed_at).toLocaleTimeString() : 'Awaiting triggers'}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {distribution.map((d) => {
            const colors = {
              NEW: { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981' },
              ENRICH: { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6' },
              DUPLICATE: { bg: 'rgba(107, 114, 128, 0.15)', text: '#9ca3af' },
              REVIEW: { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b' },
              CONFLICT: { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444' },
              IGNORE: { bg: 'rgba(156, 163, 175, 0.15)', text: '#6b7280' },
            }
            const c = colors[d.decision] || { bg: 'rgba(107, 114, 128, 0.15)', text: '#9ca3af' }
            return (
              <div
                key={d.decision}
                style={{
                  padding: '6px 14px',
                  borderRadius: 8,
                  background: c.bg,
                  color: c.text,
                  fontSize: 13,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <span>{d.decision}</span>
                <span style={{ background: 'rgba(0,0,0,0.2)', padding: '1px 6px', borderRadius: 6, fontSize: 12 }}>
                  {d.count}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
        <button
          onClick={() => setActiveTab('pipeline')}
          style={{
            padding: '10px 18px',
            border: 'none',
            background: 'none',
            color: activeTab === 'pipeline' ? '#3b82f6' : 'var(--text-secondary)',
            fontWeight: activeTab === 'pipeline' ? 600 : 500,
            borderBottom: activeTab === 'pipeline' ? '2px solid #3b82f6' : '2px solid transparent',
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          Recent Staging Records ({records.length})
        </button>

        <button
          onClick={() => setActiveTab('graph')}
          style={{
            padding: '10px 18px',
            border: 'none',
            background: 'none',
            color: activeTab === 'graph' ? '#10b981' : 'var(--text-secondary)',
            fontWeight: activeTab === 'graph' ? 600 : 500,
            borderBottom: activeTab === 'graph' ? '2px solid #10b981' : '2px solid transparent',
            cursor: 'pointer',
            fontSize: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <Sparkles size={14} />
          Knowledge Graph & Signals
        </button>

        <button
          onClick={() => setActiveTab('nodes')}
          style={{
            padding: '10px 18px',
            border: 'none',
            background: 'none',
            color: activeTab === 'nodes' ? '#a855f7' : 'var(--text-secondary)',
            fontWeight: activeTab === 'nodes' ? 600 : 500,
            borderBottom: activeTab === 'nodes' ? '2px solid #a855f7' : '2px solid transparent',
            cursor: 'pointer',
            fontSize: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <Radio size={14} />
          Connected Scout Nodes
        </button>

        <button
          onClick={() => setActiveTab('review')}
          style={{
            padding: '10px 18px',
            border: 'none',
            background: 'none',
            color: activeTab === 'review' ? '#f59e0b' : 'var(--text-secondary)',
            fontWeight: activeTab === 'review' ? 600 : 500,
            borderBottom: activeTab === 'review' ? '2px solid #f59e0b' : '2px solid transparent',
            cursor: 'pointer',
            fontSize: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <span>Human Review Queue</span>
          {reviewQueue.length > 0 && (
            <span
              style={{
                background: '#f59e0b',
                color: '#000',
                padding: '1px 6px',
                borderRadius: 10,
                fontSize: 11,
                fontWeight: 700,
              }}
            >
              {reviewQueue.length}
            </span>
          )}
        </button>
      </div>

      {/* Tab: Recent Records Table */}
      {activeTab === 'pipeline' && (
        <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Staged Observations</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Filter size={14} color="var(--text-secondary)" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                style={{
                  padding: '4px 8px',
                  borderRadius: 6,
                  border: '1px solid var(--border)',
                  background: 'var(--bg)',
                  color: 'var(--text-primary)',
                  fontSize: 12,
                }}
              >
                <option value="ALL">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="batched">Batched</option>
                <option value="committed">Committed</option>
                <option value="review">Review</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'rgba(0,0,0,0.1)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '10px 16px' }}>Status</th>
                <th style={{ padding: '10px 16px' }}>Candidate Name</th>
                <th style={{ padding: '10px 16px' }}>Current Employer</th>
                <th style={{ padding: '10px 16px' }}>Title</th>
                <th style={{ padding: '10px 16px' }}>Decision</th>
                <th style={{ padding: '10px 16px' }}>Confidence</th>
                <th style={{ padding: '10px 16px' }}>Staged At</th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No staged records found in buffer.
                  </td>
                </tr>
              ) : (
                records.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px 16px' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          background:
                            r.processing_status === 'committed'
                              ? 'rgba(16, 185, 129, 0.15)'
                              : r.processing_status === 'review'
                              ? 'rgba(245, 158, 11, 0.15)'
                              : r.processing_status === 'pending'
                              ? 'rgba(59, 130, 246, 0.15)'
                              : 'rgba(107, 114, 128, 0.15)',
                          color:
                            r.processing_status === 'committed'
                              ? '#10b981'
                              : r.processing_status === 'review'
                              ? '#f59e0b'
                              : r.processing_status === 'pending'
                              ? '#3b82f6'
                              : '#9ca3af',
                        }}
                      >
                        {r.processing_status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontWeight: 600 }}>
                      {r.raw_name || 'Anonymous Recruiter'}
                    </td>
                    <td style={{ padding: '12px 16px' }}>{r.raw_company || '—'}</td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>{r.raw_title || '—'}</td>
                    <td style={{ padding: '12px 16px' }}>
                      {r.decision ? (
                        <span style={{ fontWeight: 600, fontSize: 12 }}>{r.decision}</span>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)' }}>Pending Batch</span>
                      )}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      {Math.round((r.identity_confidence || 0) * 100)}%
                    </td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-secondary)', fontSize: 12 }}>
                      {r.created_at ? new Date(r.created_at).toLocaleTimeString() : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Open Knowledge Graph & Signals */}
      {activeTab === 'graph' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Knowledge Graph Metrics Banner */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
            <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 20px' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>TOTAL ENTITIES</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#3b82f6' }}>{knowledgeStats?.total_entities || knowledgeEntities.length}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>Persons, Companies, Jobs, Schools</div>
            </div>
            <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 20px' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>RELATIONSHIPS</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#10b981' }}>{knowledgeStats?.total_relationships || 0}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>Employed By, Posted By, Attended</div>
            </div>
            <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 20px' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>STAFFING & HIRING SIGNALS</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#a855f7' }}>{knowledgeStats?.total_signals || knowledgeSignals.length}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>Hiring Surges, Certifications, Capabilities</div>
            </div>
            <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 20px' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>EXTENSIBLE OBSERVATIONS</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#f59e0b' }}>{knowledgeStats?.total_observations || knowledgeObservations.length}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>Zero-Loss Typed Observation Triples</div>
            </div>
          </div>

          {/* Active Knowledge Entities & Signals Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 20 }}>
            {/* Entities List */}
            <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', fontWeight: 600, fontSize: 14 }}>
                Canonical Knowledge Entities ({knowledgeEntities.length})
              </div>
              <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                {knowledgeEntities.length === 0 ? (
                  <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
                    No knowledge entities extracted yet.
                  </div>
                ) : (
                  knowledgeEntities.map((e) => (
                    <div key={e.id} style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>{e.canonical_name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{e.primary_identifier}</div>
                      </div>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 700,
                          background:
                            e.entity_type === 'PERSON'
                              ? 'rgba(59, 130, 246, 0.15)'
                              : e.entity_type === 'COMPANY'
                              ? 'rgba(16, 185, 129, 0.15)'
                              : e.entity_type === 'JOB'
                              ? 'rgba(168, 85, 247, 0.15)'
                              : 'rgba(245, 158, 11, 0.15)',
                          color:
                            e.entity_type === 'PERSON'
                              ? '#3b82f6'
                              : e.entity_type === 'COMPANY'
                              ? '#10b981'
                              : e.entity_type === 'JOB'
                              ? '#a855f7'
                              : '#f59e0b',
                        }}
                      >
                        {e.entity_type}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Staffing Signals & Capabilities */}
            <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', fontWeight: 600, fontSize: 14 }}>
                Business & Staffing Signals ({knowledgeSignals.length})
              </div>
              <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                {knowledgeSignals.length === 0 ? (
                  <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
                    No active hiring signals or certifications detected.
                  </div>
                ) : (
                  knowledgeSignals.map((s) => (
                    <div key={s.id} style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{s.title}</span>
                        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'rgba(168, 85, 247, 0.15)', color: '#a855f7', fontWeight: 700 }}>
                          {s.signal_type}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{s.description}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Multi-User Connected Scout Nodes Telemetry */}
      {activeTab === 'nodes' && (
        <ScoutNodesPanel />
      )}

      {/* Tab: Review Queue */}
      {activeTab === 'review' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {reviewQueue.length === 0 ? (
            <div style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: 36, textAlign: 'center', color: 'var(--text-secondary)' }}>
              <CheckCircle2 size={32} color="#10b981" style={{ marginBottom: 12 }} />
              <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                Review Queue is Clean
              </div>
              <div>No conflict or ambiguous identity records requiring manual review.</div>
            </div>
          ) : (
            reviewQueue.map((item) => (
              <div
                key={item.staging_id}
                style={{
                  background: 'var(--card-bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 12,
                  padding: 20,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <span style={{ fontWeight: 700, fontSize: 16 }}>{item.raw_name || 'Anonymous Candidate'}</span>
                    <span style={{ padding: '2px 8px', borderRadius: 4, background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', fontSize: 11, fontWeight: 600 }}>
                      {item.decision || 'REVIEW'}
                    </span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>
                    <strong>Reason:</strong> {item.decision_reason || 'Uncertain match threshold'}
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <span>Company: {item.raw_company || '—'}</span>
                    <span>Email: {item.raw_email || '—'}</span>
                    <span>LinkedIn: {item.raw_linkedin ? 'Present' : 'None'}</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    onClick={() => handleReject(item.staging_id)}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 6,
                      border: '1px solid var(--border)',
                      background: 'var(--bg)',
                      color: '#ef4444',
                      cursor: 'pointer',
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => handleApprove(item.staging_id)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: 6,
                      border: 'none',
                      background: '#10b981',
                      color: '#fff',
                      cursor: 'pointer',
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    Approve & Commit
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
