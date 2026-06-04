import React, { useEffect, useState } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import api from '../services/api'

function isRunningStatus(status) {
  return ['queued', 'uploading', 'analyzing', 'parsing', 'mapping', 'validating', 'preview_ready', 'importing', 'processing'].includes(String(status || '').toLowerCase())
}

function jobScore(job) {
  const started = job?.started_at ? new Date(job.started_at).getTime() : 0
  const updated = job?.last_heartbeat_at ? new Date(job.last_heartbeat_at).getTime() : started
  return Math.max(started, updated)
}

export default function GlobalUploadStatus() {
  const [activeJob, setActiveJob] = useState(null)

  useEffect(() => {
    let cancelled = false

    const fetchJobs = async () => {
      try {
        const [legacyActive, smartActive] = await Promise.all([
          api.get('/upload/jobs/active').then((res) => Array.isArray(res.data) ? res.data : []).catch(() => []),
          api.get('/api/import/jobs/active').then((res) => Array.isArray(res.data) ? res.data : []).catch(() => []),
        ])
        if (cancelled) return
        const jobs = [...legacyActive, ...smartActive].filter((job) => isRunningStatus(job.status))
        const latest = jobs.sort((a, b) => jobScore(b) - jobScore(a))
        setActiveJob(latest[0] || null)
      } catch {
        // Silent: this should never block core UX.
      }
    }

    fetchJobs()
    const interval = window.setInterval(fetchJobs, 3000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [])

  if (!activeJob) return null

  const total = Number(activeJob.total_rows || 0)
  const done = Number(activeJob.processed_rows || 0)
  const pct = Number(activeJob.progress_percent || (total > 0 ? Math.max(0, Math.min(100, Math.round((done / total) * 100))) : 0))
  const status = String(activeJob.status || 'idle').toLowerCase()
  const color = status === 'completed' ? '#22c55e' : status === 'failed' ? '#ef4444' : status === 'stuck' ? '#f59e0b' : '#185FA5'

  return (
    <div style={{
      position: 'fixed',
      right: 16,
      bottom: 16,
      zIndex: 50,
      display: 'flex',
      gap: 12,
      alignItems: 'center',
      padding: 14,
      borderRadius: 14,
      background: 'var(--card-bg)',
      border: '1px solid var(--card-border)',
      boxShadow: 'var(--shadow-lg)',
      minWidth: 320,
    }}>
      <div style={{ width: 30, height: 30, borderRadius: 10, background: `${color}18`, display: 'grid', placeItems: 'center' }}>
        {status === 'completed' ? (
          <Loader2 size={14} style={{ color }} />
        ) : (
          <RefreshCw size={14} style={{ color, animation: 'spin 0.9s linear infinite' }} />
        )}
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12.5, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {status === 'completed' ? 'Latest upload completed' : `Importing ${activeJob.file_name || activeJob.filename || `Job ${activeJob.job_id}`}`}
        </div>
        <div style={{ marginTop: 2, fontSize: 11, color: 'var(--text-muted)' }}>
          {activeJob.current_step || activeJob.status}
        </div>
        <div style={{ width: 220, background: 'var(--bg-hover)', border: '1px solid var(--card-border)', borderRadius: 999, height: 8, marginTop: 8, overflow: 'hidden' }}>
          <div style={{ background: `linear-gradient(90deg, ${color}, #185FA5)`, height: '100%', width: `${pct}%`, borderRadius: 999, transition: 'width 0.3s ease' }} />
        </div>
        <div style={{ marginTop: 6, fontSize: 11.5, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
          {pct}% • {done.toLocaleString()} / {total.toLocaleString()} rows
        </div>
      </div>
    </div>
  )
}
