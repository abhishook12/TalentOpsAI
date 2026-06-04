import { useEffect, useMemo, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { RefreshCw, Loader2 } from 'lucide-react'
import api from '../services/api'

const RUNNING_STEPS = [
  'uploading',
  'analyzing',
  'parsing',
  'mapping',
  'validating',
  'preview_ready',
  'processing',
  'importing',
  'completed',
  'failed',
  'stuck',
  'cancelled',
]

const STEP_LABELS = {
  uploading: 'Uploading',
  analyzing: 'Analyzing',
  parsing: 'Parsing',
  mapping: 'Mapping',
  validating: 'Validating',
  preview_ready: 'Preview Ready',
  processing: 'Processing',
  importing: 'Importing',
  completed: 'Completed',
  failed: 'Failed',
  stuck: 'Stuck',
  cancelled: 'Cancelled',
}

const STEP_PROGRESS = {
  uploading: 5,
  analyzing: 10,
  parsing: 20,
  mapping: 35,
  validating: 60,
  preview_ready: 78,
  processing: 85,
  importing: 90,
  completed: 100,
  failed: 100,
  stuck: 92,
  cancelled: 100,
}

const STATUS_COLORS = {
  uploading: '#4f46e5',
  analyzing: '#0ea5e9',
  parsing: '#38bdf8',
  mapping: '#8b5cf6',
  validating: '#f59e0b',
  preview_ready: '#06b6d4',
  processing: '#0ea5e9',
  importing: '#0ea5e9',
  completed: '#22c55e',
  failed: '#ef4444',
  stuck: '#f59e0b',
  cancelled: '#94a3b8',
}

function formatTimestamp(value) {
  if (!value) return '—'
  try {
    return formatDistanceToNow(new Date(value), { addSuffix: true })
  } catch {
    return value
  }
}

function isRunningStatus(status) {
  return ['uploading', 'analyzing', 'parsing', 'mapping', 'validating', 'preview_ready', 'importing', 'processing', 'queued'].includes(status)
}

function scoreJob(job) {
  if (!job) return -1
  const startedAt = job.started_at ? new Date(job.started_at).getTime() : 0
  const lastUpdate = job.last_heartbeat_at ? new Date(job.last_heartbeat_at).getTime() : startedAt
  const phaseScore = STEP_PROGRESS[job.status] ?? job.progress_percent ?? 0
  return startedAt + lastUpdate / 1000000 + phaseScore / 100000
}

export default function LiveUploadStatusPanel({ compact = false }) {
  const [state, setState] = useState({
    loading: true,
    job: null,
    source: null,
    error: null,
    refreshing: false,
  })

  const fetchJobs = async () => {
    setState((current) => ({ ...current, refreshing: true }))
    try {
      const [legacyActive, smartActive, legacyHistory, smartHistory] = await Promise.all([
        api.get('/upload/jobs/active').then((res) => Array.isArray(res.data) ? res.data : []).catch(() => []),
        api.get('/api/import/jobs/active').then((res) => Array.isArray(res.data) ? res.data : []).catch(() => []),
        api.get('/upload/jobs').then((res) => Array.isArray(res.data) ? res.data : []).catch(() => []),
        api.get('/api/import/history').then((res) => Array.isArray(res.data) ? res.data : []).catch(() => []),
      ])

      const activeJobs = [...legacyActive.map((job) => ({ ...job, _source: 'legacy' })), ...smartActive.map((job) => ({ ...job, _source: 'smart' }))]
        .filter((job) => isRunningStatus(job.status))

      const latestActive = activeJobs.sort((a, b) => scoreJob(b) - scoreJob(a))[0] || null

      const recentJobs = [...legacyHistory.map((job) => ({ ...job, _source: 'legacy' })), ...smartHistory.map((job) => ({ ...job, _source: 'smart' }))]
        .filter(Boolean)
        .sort((a, b) => scoreJob(b) - scoreJob(a))

      const job = latestActive || recentJobs[0] || null
      setState({
        loading: false,
        job,
        source: job?._source || null,
        error: null,
        refreshing: false,
      })
    } catch (error) {
      setState((current) => ({ ...current, loading: false, refreshing: false, error: error?.message || 'Unable to load job status' }))
    }
  }

  useEffect(() => {
    fetchJobs()
    const interval = window.setInterval(fetchJobs, 2500)
    return () => window.clearInterval(interval)
  }, [])

  const display = useMemo(() => {
    const job = state.job
    const status = (job?.status || 'idle').toLowerCase()
    const progress = Number(job?.progress_percent ?? STEP_PROGRESS[status] ?? 0)
    const total = Number(job?.total_rows || 0)
    const processed = Number(job?.processed_rows || 0)
    const imported = Number(job?.inserted_rows || job?.imported_rows || 0)
    const failed = Number(job?.failed_rows || job?.error_rows || job?.error_count || 0)
    const activeStep = (job?.current_step || STEP_LABELS[status] || 'Idle')
    const elapsedMs = job?.started_at ? Date.now() - new Date(job.started_at).getTime() : 0
    const elapsedLabel = elapsedMs > 0 ? `${Math.floor(elapsedMs / 60000)}m ${Math.floor((elapsedMs % 60000) / 1000)}s` : '—'
    const heartbeat = job?.last_heartbeat_at ? new Date(job.last_heartbeat_at).getTime() : 0
    const stuck = Boolean(job && isRunningStatus(status) && heartbeat && Date.now() - heartbeat > 90000) || status === 'stuck'
    const displayStatus = stuck ? 'stuck' : status
    const stepIndex = RUNNING_STEPS.indexOf(displayStatus)
    return {
      job,
      status: displayStatus,
      progress,
      total,
      processed,
      imported,
      failed,
      activeStep,
      elapsedLabel,
      stuck,
      stepIndex,
    }
  }, [state.job])

  const job = display.job
  const running = isRunningStatus(display.status) || display.status === 'stuck'
  const color = STATUS_COLORS[display.status] || '#64748b'

  if (state.loading && !job) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderRadius: 999, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', color: 'var(--text-muted)', fontSize: 12 }}>
        <Loader2 size={14} className="animate-spin" />
        Loading upload status…
      </div>
    )
  }

  if (!job) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderRadius: 999, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', color: 'var(--text-muted)', fontSize: 12 }}>
        <span style={{ width: 8, height: 8, borderRadius: 999, background: '#64748b', display: 'inline-block' }} />
        No active upload
      </div>
    )
  }

  return (
    <div style={{
      background: 'linear-gradient(180deg, rgba(15,23,42,0.95), rgba(15,23,42,0.88))',
      border: '1px solid var(--card-border)',
      borderRadius: 16,
      boxShadow: 'var(--shadow-lg)',
      padding: compact ? 14 : 18,
      color: 'var(--text-primary)',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: 999, background: color, boxShadow: running ? `0 0 0 4px ${color}22` : 'none' }} />
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Live Upload Status
            </div>
          </div>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={job.filename}>
            {job.filename}
          </div>
          <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-muted)' }}>
            {job.job_id?.slice(0, 8)} • {display.status.toUpperCase()} • {display.activeStep}
          </div>
        </div>

        <button
          onClick={fetchJobs}
          title="Refresh Status"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, borderRadius: 10, padding: '8px 12px', border: '1px solid var(--card-border)', background: 'var(--main-bg)', color: 'var(--text-primary)', cursor: 'pointer', fontSize: 12 }}
        >
          <RefreshCw size={14} style={{ animation: state.refreshing ? 'spin 0.9s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      <div style={{ marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
          <span>Progress</span>
          <span>{display.progress}%</span>
        </div>
        <div style={{ height: 8, borderRadius: 999, background: 'rgba(148,163,184,0.16)', overflow: 'hidden' }}>
          <div style={{ width: `${display.progress}%`, height: '100%', background: `linear-gradient(90deg, ${color}, #185FA5)`, borderRadius: 999, transition: 'width 0.3s ease' }} />
        </div>
      </div>

      <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: compact ? 'repeat(2, minmax(0, 1fr))' : 'repeat(4, minmax(0, 1fr))', gap: 10 }}>
        {[
          ['Detected', job.total_rows],
          ['Processed', display.processed],
          ['Imported', display.imported],
          ['Failed', display.failed],
        ].map(([label, value]) => (
          <div key={label} style={{ padding: 10, borderRadius: 12, background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(148,163,184,0.14)' }}>
            <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>{label}</div>
            <div style={{ marginTop: 6, fontSize: 18, fontWeight: 800 }}>{Number(value || 0).toLocaleString()}</div>
          </div>
        ))}
      </div>

      {!compact && (
        <>
          <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
            <div style={{ padding: 12, borderRadius: 12, background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(148,163,184,0.14)' }}>
              <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>Current Step</div>
              <div style={{ marginTop: 6, fontSize: 13, fontWeight: 700 }}>{job.current_step || 'Idle'}</div>
            </div>
            <div style={{ padding: 12, borderRadius: 12, background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(148,163,184,0.14)' }}>
              <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>Elapsed</div>
              <div style={{ marginTop: 6, fontSize: 13, fontWeight: 700 }}>{display.elapsedLabel}</div>
            </div>
          </div>

          <div style={{ marginTop: 14, display: 'grid', gap: 8 }}>
            {RUNNING_STEPS.slice(0, 9).map((step, index) => {
              const active = step === display.status
              const done = display.stepIndex > index || ['completed'].includes(display.status) && index < RUNNING_STEPS.indexOf('completed')
              return (
                <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 10, opacity: active || done ? 1 : 0.45 }}>
                  <span style={{ width: 10, height: 10, borderRadius: 999, background: active ? color : done ? '#22c55e' : 'rgba(148,163,184,0.4)' }} />
                  <span style={{ fontSize: 12, fontWeight: active ? 700 : 500, color: active ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    {STEP_LABELS[step]}
                  </span>
                  {active && <span style={{ fontSize: 11, color: color, fontWeight: 700 }}>Active</span>}
                </div>
              )
            })}
          </div>

          {display.stuck && (
            <div style={{ marginTop: 14, padding: 12, borderRadius: 12, border: '1px solid rgba(245,158,11,0.35)', background: 'rgba(245,158,11,0.08)', color: '#f59e0b', fontSize: 12, lineHeight: 1.5 }}>
              No progress update received recently. The job may still be running, but status updates have stopped.
            </div>
          )}

          {display.status === 'failed' && job.error_message && (
            <div style={{ marginTop: 14, padding: 12, borderRadius: 12, border: '1px solid rgba(239,68,68,0.35)', background: 'rgba(239,68,68,0.08)', color: '#ef4444', fontSize: 12, lineHeight: 1.5 }}>
              <div style={{ fontWeight: 800, marginBottom: 4 }}>Import failed</div>
              <div>{job.error_message}</div>
            </div>
          )}

          <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10, fontSize: 12 }}>
            <div style={{ color: 'var(--text-muted)' }}>
              Started: <span style={{ color: 'var(--text-primary)' }}>{formatTimestamp(job.started_at)}</span>
            </div>
            <div style={{ color: 'var(--text-muted)' }}>
              Last update: <span style={{ color: 'var(--text-primary)' }}>{formatTimestamp(job.last_heartbeat_at || job.updated_at)}</span>
            </div>
          </div>

          <div style={{ marginTop: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              onClick={fetchJobs}
              style={{ border: '1px solid var(--card-border)', background: 'var(--main-bg)', color: 'var(--text-primary)', borderRadius: 10, padding: '8px 12px', cursor: 'pointer', fontSize: 12 }}
            >
              Refresh Status
            </button>
            <button
              disabled
              title="Cancel support coming soon"
              style={{ border: '1px solid rgba(148,163,184,0.2)', background: 'rgba(148,163,184,0.06)', color: 'var(--text-muted)', borderRadius: 10, padding: '8px 12px', cursor: 'not-allowed', fontSize: 12 }}
            >
              Cancel Import
            </button>
          </div>
        </>
      )}
    </div>
  )
}
