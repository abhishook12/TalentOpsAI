import { useEffect, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function Candidates() {
  const [candidates, setCandidates] = useState([])

  useEffect(() => {
    axios.get(`${API}/candidates`).then(r => setCandidates(r.data)).catch(() => {})
  }, [])

  return (
    <div>
      <h1 style={{ color: '#f1f5f9', fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>Candidates</h1>
      <div style={{ background: '#1e293b', borderRadius: '12px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#0f172a' }}>
              {['Name', 'Email', 'Visa Status', 'Experience', 'Location', 'Rate/hr'].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', color: '#64748b', fontSize: '13px' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {candidates.map(c => (
              <tr key={c.candidate_id} style={{ borderTop: '1px solid #0f172a' }}>
                <td style={{ padding: '12px 16px', color: '#f1f5f9' }}>{c.candidate_name}</td>
                <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{c.email}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ background: '#1e3a5f', color: '#38bdf8', padding: '2px 10px', borderRadius: '999px', fontSize: '12px' }}>{c.visa_status}</span>
                </td>
                <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{c.experience_years} yrs</td>
                <td style={{ padding: '12px 16px', color: '#94a3b8' }}>{c.location}</td>
                <td style={{ padding: '12px 16px', color: '#34d399' }}>${c.rate_per_hour}/hr</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Candidates