import { useEffect, useState } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const statusColors = {
  submitted: { bg: '#1e3a5f', color: '#38bdf8' },
  interviewing: { bg: '#3b1f6e', color: '#a78bfa' },
  offered: { bg: '#064e3b', color: '#34d399' },
  rejected: { bg: '#450a0a', color: '#f87171' },
  placed: { bg: '#064e3b', color: '#86efac' },
}

function Submissions() {
  const [submissions, setSubmissions] = useState([])

  useEffect(() => {
    axios.get(`${API}/submissions`).then(r => setSubmissions(r.data)).catch(() => {})
  }, [])

  return (
    <div>
      <h1 style={{ color: '#f1f5f9', fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>Submissions</h1>
      <div style={{ background: '#1e293b', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#0f172a' }}>
              {['Job Title', 'Status', 'Submission Date', 'Notes'].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', color: '#64748b', fontSize: '13px' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {submissions.map(s => {
              const sc = statusColors[s.status] || { bg: '#1e293b', color: '#94a3b8' }
              return (
                <tr key={s.submission_id} style={{ borderTop: '1px solid #0f172a' }}>
                  <td style={{ padding: '12px 16px', color: '#f1f5f9' }}>{s.job_title}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ background: sc.bg, color: sc.color, padding: '2px 10px', borderRadius: '999px', fontSize: '12px' }}>{s.status}</span>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{s.submission_date}</td>
                  <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{s.notes || '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Submissions