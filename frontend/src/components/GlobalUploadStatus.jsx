import React, { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import api from '../services/api'

export default function GlobalUploadStatus() {
  const [activeJob, setActiveJob] = useState(null)

  useEffect(() => {
    let cancelled = false

    const fetchJobs = async () => {
      try {
        const { data: jobs } = await api.get('/upload/jobs')
        if (cancelled) return
        if (Array.isArray(jobs) && jobs.length > 0) {
          const running = jobs.find((j) => j.status === 'processing' || j.status === 'queued')
          setActiveJob(running || null)
        } else {
          setActiveJob(null)
        }
      } catch {
        // Silent: this should never block core UX.
      }
    }

    fetchJobs()
    const interval = window.setInterval(fetchJobs, 3000)
    return () => { cancelled = true; window.clearInterval(interval) }
  }, [])

  if (!activeJob) return null

  const total = Number(activeJob.total_rows || 0)
  const done = Number(activeJob.processed_rows || 0)
  const pct = total > 0 ? Math.max(0, Math.min(100, Math.round((done / total) * 100))) : 0

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
      <div style={{ width: 30, height: 30, borderRadius: 10, background: 'var(--accent-bg)', display: 'grid', placeItems: 'center' }}>
        <RefreshCw className="w-4 h-4" style={{ color: 'var(--accent)', animation: 'spin 0.9s linear infinite' }} />
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12.5, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          Importing {activeJob.file_name || activeJob.filename || `Job ${activeJob.job_id}`}
        </div>
        <div style={{ width: 220, background: 'var(--bg-hover)', border: '1px solid var(--card-border)', borderRadius: 999, height: 8, marginTop: 8, overflow: 'hidden' }}>
          <div style={{ background: 'var(--accent)', height: '100%', width: `${pct}%`, borderRadius: 999, transition: 'width 0.3s ease' }} />
        </div>
        <div style={{ marginTop: 6, fontSize: 11.5, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
          {pct}% • {done.toLocaleString()} / {total.toLocaleString()} rows
        </div>
      </div>
    </div>
  )
}

