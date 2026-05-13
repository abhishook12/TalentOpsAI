import { useEffect, useState } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

function Recruiters() {
  const [recruiters, setRecruiters] = useState([])

  useEffect(() => {
    axios.get(`${API}/recruiters`).then(r => setRecruiters(r.data)).catch(() => {})
  }, [])

  return (
    <div>
      <h1 style={{ color: '#f1f5f9', fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>Recruiters</h1>
      <div style={{ background: '#1e293b', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#0f172a' }}>
              {['Name', 'Email', 'Phone', 'Specialization', 'Status'].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', color: '#64748b', fontSize: '13px' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recruiters.map(r => (
              <tr key={r.recruiter_id} style={{ borderTop: '1px solid #0f172a' }}>
                <td style={{ padding: '12px 16px', color: '#f1f5f9' }}>{r.recruiter_name}</td>
                <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{r.email}</td>
                <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{r.phone}</td>
                <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{r.specialization}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ background: r.is_active ? '#064e3b' : '#450a0a', color: r.is_active ? '#34d399' : '#f87171', padding: '2px 10px', borderRadius: '999px', fontSize: '12px' }}>
                    {r.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Recruiters