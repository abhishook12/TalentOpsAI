import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import { ShellCard, SectionHeader, Badge, PrimaryButton, GhostButton } from './CommandCenter'
import AnimatedNumber from './ui/AnimatedNumber'

export default function LiveIngestionPipeline() {
  const [selectedAudit, setSelectedAudit] = useState(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['live-scraper-ingestion-summary'],
    queryFn: async () => {
      const res = await api.get('/analytics/scraper-ingestion-summary')
      return res.data
    },
    refetchInterval: 5000, // High-speed 5s polling for live telemetry
    staleTime: 3000,
  })

  const metrics = data?.metrics_today || {
    raw_observations_received: 0,
    useful_discoveries: 0,
    staging_records: 0,
    validated_records: 0,
    new_people_created: 0,
    existing_people_enriched: 0,
    fields_added: 0,
    fields_corrected: 0,
    duplicates_ignored: 0,
    rejected_low_confidence: 0,
    companies_discovered: 0,
    jobs_discovered: 0,
    staffing_signals: 0,
    master_db_inserts: 0,
    master_db_updates: 0,
  }

  const timestamps = data?.timestamps || {
    last_scraper_observation: 'None Recorded',
    last_screenshot: 'None Recorded',
    last_staging_write: 'None Recorded',
    last_enrichment: 'None Recorded',
    last_new_record: 'None Recorded',
    last_master_db_update: 'None Recorded',
  }

  const pipelineState = data?.pipeline_state || 'IDLE'
  const statusDetail = data?.status_detail || 'Waiting for browser activity'
  const recentDiffs = data?.recent_enrichment_diffs || []

  // Status badge styling
  const statusConfig = {
    RECEIVING_DATA: { tone: 'success', text: '● LIVE INGESTION: RECEIVING DATA', color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
    PROCESSING: { tone: 'warning', text: '● LIVE INGESTION: BATCH PROCESSING', color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
    IDLE: { tone: 'neutral', text: '● LIVE INGESTION: IDLE', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
    NO_INGESTION_WARNING: { tone: 'danger', text: '⚠ NO INGESTION (>10m)', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  }[pipelineState] || { tone: 'neutral', text: '● LIVE INGESTION: STANDBY', color: '#9ca3af', bg: 'rgba(156,163,175,0.15)' }

  return (
    <ShellCard style={{ padding: 20, minHeight: 0, background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 900, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
              REAL-TIME TELEMETRY
            </span>
            <span
              style={{
                padding: '3px 10px',
                borderRadius: 20,
                fontSize: 11,
                fontWeight: 800,
                color: statusConfig.color,
                background: statusConfig.bg,
                border: `1px solid ${statusConfig.color}40`,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              {statusConfig.text}
            </span>
          </div>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
            Live Scraper & Enrichment Ingestion Pipeline
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-secondary)' }}>
            {statusDetail} • Explicit separation between AI searches, new person creations, and existing master enrichments.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <GhostButton onClick={() => refetch()} style={{ padding: '6px 12px', fontSize: 12 }}>
            <i className="ti ti-refresh" /> Refresh Pipeline
          </GhostButton>
        </div>
      </div>

      {/* 1. Visual 6-Stage Pipeline Flow Banner */}
      <div style={{ background: 'var(--bg-surface, #0f172a)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px', marginBottom: 20, overflowX: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minWidth: 800, gap: 8 }}>
          {/* Stage 1 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>1. BROWSER OBSERVED</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#3b82f6' }}><AnimatedNumber value={metrics.raw_observations_received} /></div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Raw Viewport Frames</div>
          </div>
          <i className="ti ti-arrow-right" style={{ color: 'var(--text-secondary)', fontSize: 16 }} />

          {/* Stage 2 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>2. STAGING BUFFER</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#a855f7' }}><AnimatedNumber value={metrics.staging_records} /></div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Pending Intelligence</div>
          </div>
          <i className="ti ti-arrow-right" style={{ color: 'var(--text-secondary)', fontSize: 16 }} />

          {/* Stage 3 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>3. VALIDATED</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#10b981' }}><AnimatedNumber value={metrics.useful_discoveries} /></div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Grounded Evidence</div>
          </div>
          <i className="ti ti-arrow-right" style={{ color: 'var(--text-secondary)', fontSize: 16 }} />

          {/* Stage 4 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>4. IDENTITY MATCHED</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#f59e0b' }}><AnimatedNumber value={metrics.existing_people_enriched + metrics.new_people_created} /></div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Clustered Persons</div>
          </div>
          <i className="ti ti-arrow-right" style={{ color: 'var(--text-secondary)', fontSize: 16 }} />

          {/* Stage 5 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>5. ENRICHED TODAY</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#06b6d4' }}>+<AnimatedNumber value={metrics.existing_people_enriched} /></div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>{metrics.fields_added} fields added</div>
          </div>
          <i className="ti ti-arrow-right" style={{ color: 'var(--text-secondary)', fontSize: 16 }} />

          {/* Stage 6 */}
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 2 }}>6. MASTER DB INSERTS</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#ec4899' }}>+<AnimatedNumber value={metrics.new_people_created} /></div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>New Canonical People</div>
          </div>
        </div>
      </div>

      {/* 2. Three Column Metric Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
        {/* Column A: Scraper Ingestion Volume */}
        <div style={{ background: 'var(--bg-surface, #0f172a)', border: '1px solid var(--border)', borderRadius: 10, padding: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            📥 Ingestion Volume (Today)
          </div>
          <div style={{ display: 'grid', gap: 8, fontSize: 13 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Raw Observations:</span>
              <span style={{ fontWeight: 700 }}><AnimatedNumber value={metrics.raw_observations_received} /></span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Useful Discoveries:</span>
              <span style={{ fontWeight: 700, color: '#10b981' }}><AnimatedNumber value={metrics.useful_discoveries} /></span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Companies Discovered:</span>
              <span style={{ fontWeight: 700 }}><AnimatedNumber value={metrics.companies_discovered} /></span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Jobs Discovered:</span>
              <span style={{ fontWeight: 700 }}><AnimatedNumber value={metrics.jobs_discovered} /></span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Staffing Signals:</span>
              <span style={{ fontWeight: 700, color: '#a855f7' }}><AnimatedNumber value={metrics.staffing_signals} /></span>
            </div>
          </div>
        </div>

        {/* Column B: Identity & Field Resolution */}
        <div style={{ background: 'var(--bg-surface, #0f172a)', border: '1px solid var(--border)', borderRadius: 10, padding: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            🧬 Identity & Enrichment (Today)
          </div>
          <div style={{ display: 'grid', gap: 8, fontSize: 13 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Existing People Enriched:</span>
              <span style={{ fontWeight: 800, color: '#06b6d4' }}>+<AnimatedNumber value={metrics.existing_people_enriched} /></span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Fields Added Today:</span>
              <span style={{ fontWeight: 800, color: '#10b981' }}>+<AnimatedNumber value={metrics.fields_added} /></span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>New Canonical People:</span>
              <span style={{ fontWeight: 800, color: '#ec4899' }}>+<AnimatedNumber value={metrics.new_people_created} /></span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Duplicates Ignored:</span>
              <span style={{ fontWeight: 700, color: 'var(--text-secondary)' }}><AnimatedNumber value={metrics.duplicates_ignored} /></span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Rejected / Ungrounded:</span>
              <span style={{ fontWeight: 700, color: '#ef4444' }}><AnimatedNumber value={metrics.rejected_low_confidence} /></span>
            </div>
          </div>
        </div>

        {/* Column C: Forensic Live Timestamps */}
        <div style={{ background: 'var(--bg-surface, #0f172a)', border: '1px solid var(--border)', borderRadius: 10, padding: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            ⏱ Live Forensic Timestamps
          </div>
          <div style={{ display: 'grid', gap: 8, fontSize: 13 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Last Observation:</span>
              <span style={{ fontWeight: 700, fontFamily: 'var(--mono)' }}>{timestamps.last_scraper_observation}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Last Screenshot:</span>
              <span style={{ fontWeight: 700, fontFamily: 'var(--mono)' }}>{timestamps.last_screenshot}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Last Staging Write:</span>
              <span style={{ fontWeight: 700, fontFamily: 'var(--mono)' }}>{timestamps.last_staging_write}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Last Enrichment:</span>
              <span style={{ fontWeight: 700, fontFamily: 'var(--mono)', color: '#06b6d4' }}>{timestamps.last_enrichment}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Last Master DB Update:</span>
              <span style={{ fontWeight: 700, fontFamily: 'var(--mono)', color: '#10b981' }}>{timestamps.last_master_db_update}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. "Where Is This Data Going?" Traceable Before/After Enrichment Diffs Table */}
      <div style={{ background: 'var(--bg-surface, #0f172a)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <i className="ti ti-git-compare" style={{ color: '#06b6d4', fontSize: 16 }} />
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
              Traceable Enrichment Stream (Before & After Field Diffs)
            </span>
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            Proving exactly which master database records received field enrichments
          </span>
        </div>

        <div style={{ maxHeight: 280, overflowY: 'auto' }}>
          {recentDiffs.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
              No recent enrichment diffs recorded yet. Browse candidate profiles to watch live field-level mutations.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: 'rgba(0,0,0,0.2)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '8px 14px' }}>Time</th>
                  <th style={{ padding: '8px 14px' }}>Candidate</th>
                  <th style={{ padding: '8px 14px' }}>Company</th>
                  <th style={{ padding: '8px 14px' }}>Decision</th>
                  <th style={{ padding: '8px 14px' }}>Fields Added / Mutated</th>
                  <th style={{ padding: '8px 14px' }}>Capture ID</th>
                  <th style={{ padding: '8px 14px' }}>Master DB</th>
                </tr>
              </thead>
              <tbody>
                {recentDiffs.map((diff, i) => (
                  <tr key={diff.event_id || i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--mono)', color: 'var(--text-secondary)' }}>
                      {diff.timestamp}
                    </td>
                    <td style={{ padding: '10px 14px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {diff.candidate_name}
                    </td>
                    <td style={{ padding: '10px 14px', color: 'var(--text-secondary)' }}>
                      {diff.company_name}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          background:
                            diff.decision === 'ENRICHED'
                              ? 'rgba(6,182,212,0.15)'
                              : diff.decision === 'NEW_DISCOVERY'
                              ? 'rgba(236,72,153,0.15)'
                              : 'rgba(156,163,175,0.15)',
                          color:
                            diff.decision === 'ENRICHED'
                              ? '#06b6d4'
                              : diff.decision === 'NEW_DISCOVERY'
                              ? '#ec4899'
                              : '#9ca3af',
                        }}
                      >
                        {diff.decision}
                      </span>
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {diff.fields_added.map((f, fi) => (
                          <span key={fi} style={{ background: 'rgba(16,185,129,0.12)', color: '#10b981', padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 700 }}>
                            +{f}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--mono)', color: 'var(--text-secondary)' }}>
                      {diff.capture_id}
                    </td>
                    <td style={{ padding: '10px 14px', fontWeight: 700, color: '#10b981' }}>
                      {diff.db_status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </ShellCard>
  )
}
