import { useState, useRef } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const EXAMPLES = [
  'Brooksource', 'IT staffing New York', 'Java recruiter',
  'Insight Global', 'finance recruiter', 'DevOps specialist',
]

function scoreRecruiter(r, words) {
  let score = 0
  const fields = [
    { val: r.recruiter_name, weight: 10 },
    { val: r.company, weight: 8 },
    { val: r.email, weight: 5 },
    { val: r.specialization, weight: 6 },
    { val: r.location, weight: 4 },
    { val: r.phone, weight: 2 },
  ]
  for (const word of words) {
    if (word.length < 2) continue
    for (const { val, weight } of fields) {
      if (!val) continue
      const v = val.toLowerCase()
      if (v === word) score += weight * 3
      else if (v.startsWith(word)) score += weight * 2
      else if (v.includes(word)) score += weight
    }
  }
  return score
}

function smartSearch(query, candidates, recruiters) {
  const q = query.toLowerCase().trim()
  const words = q.split(/\s+/).filter(w => w.length >= 2)
  if (!words.length) return { candidates: [], recruiters: [], summary: 'Type something to search.' }

  const scored = recruiters
    .map(r => ({ r, score: scoreRecruiter(r, words) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 50)
    .map(({ r }) => r)

  const isRecruiterQuery = q.includes('recruiter') || q.includes('specialist') || q.includes('staffing') || q.includes('hiring')
  let filteredCandidates = []
  if (!isRecruiterQuery) {
    const visa = q.match(/\b(h1b|gc|usc|opt|cpt|tn)\b/i)?.[1]?.toUpperCase()
    const minExp = q.match(/(\d+)\+?\s*year/i) ? parseInt(q.match(/(\d+)\+?\s*year/i)[1]) : null
    const maxRate = q.match(/under\s*\$?(\d+)/i) ? parseInt(q.match(/under\s*\$?(\d+)/i)[1]) : null
    filteredCandidates = candidates.filter(c => {
      if (visa && c.visa_status !== visa) return false
      if (minExp && c.experience_years < minExp) return false
      if (maxRate && c.rate_per_hour > maxRate) return false
      return words.some(w =>
        c.candidate_name?.toLowerCase().includes(w) ||
        c.location?.toLowerCase().includes(w) ||
        (c.skills || []).some(s => s.toLowerCase().includes(w))
      )
    }).slice(0, 30)
  }

  const total = scored.length + filteredCandidates.length
  const summary = total > 0
    ? `Found ${scored.length > 0 ? `${scored.length} recruiter${scored.length !== 1 ? 's' : ''}` : ''}${scored.length > 0 && filteredCandidates.length > 0 ? ' and ' : ''}${filteredCandidates.length > 0 ? `${filteredCandidates.length} candidate${filteredCandidates.length !== 1 ? 's' : ''}` : ''} for "${query}"`
    : `No results for "${query}". Try a different name, company, or keyword.`

  return { candidates: filteredCandidates, recruiters: scored, summary }
}

function initials(name) {
  if (!name) return '?'
  const parts = name.trim().split(' ')
  return (parts[0]?.[0] || '') + (parts[1]?.[0] || '')
}

const avatarColors = ['#1e3a5f', '#064e3b', '#3b1f6e', '#3b1f00', '#1e293b', '#172033', '#1a3a4a']
function avatarColor(name) {
  let h = 0
  for (let i = 0; i < (name?.length || 0); i++) h = (h + name.charCodeAt(i)) % avatarColors.length
  return avatarColors[h]
}

function RecruiterCard({ r }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e8edf4', borderRadius: '10px',
      padding: '14px 16px', display: 'flex', alignItems: 'center', gap: '14px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)', transition: 'box-shadow 0.12s',
    }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)'}
    >
      <div style={{
        width: 38, height: 38, borderRadius: '50%', background: avatarColor(r.recruiter_name),
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 500, color: '#fff', flexShrink: 0,
      }}>{initials(r.recruiter_name)}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 13.5, fontWeight: 500, color: '#0f172a', marginBottom: 2 }}>{r.recruiter_name}</p>
        <p style={{ fontSize: 12, color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {r.email}
          {r.company ? <span style={{ color: '#94a3b8' }}> · {r.company}</span> : null}
        </p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
        {r.phone && <span style={{ fontSize: 11, color: '#94a3b8' }}>{r.phone}</span>}
        {r.specialization && (
          <span style={{ fontSize: 11, background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: '4px' }}>
            {r.specialization.length > 30 ? r.specialization.slice(0, 30) + '…' : r.specialization}
          </span>
        )}
      </div>
    </div>
  )
}

function CandidateCard({ c }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e8edf4', borderRadius: '10px',
      padding: '14px 16px', display: 'flex', alignItems: 'center', gap: '14px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <div style={{
        width: 38, height: 38, borderRadius: '50%', background: '#1e3a5f',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 500, color: '#7dd3fc', flexShrink: 0,
      }}>{initials(c.candidate_name)}</div>
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: 13.5, fontWeight: 500, color: '#0f172a', marginBottom: 2 }}>{c.candidate_name}</p>
        <p style={{ fontSize: 12, color: '#64748b' }}>{c.email} · {c.location}</p>
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 5 }}>
          {c.visa_status && <span style={{ fontSize: 11, background: '#dbeafe', color: '#1e40af', padding: '2px 8px', borderRadius: '999px' }}>{c.visa_status}</span>}
          {(c.skills || []).slice(0, 3).map(s => (
            <span key={s} style={{ fontSize: 11, background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: '4px' }}>{s}</span>
          ))}
        </div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: '#0F6E56' }}>${c.rate_per_hour}/hr</p>
        <p style={{ fontSize: 11, color: '#94a3b8' }}>{c.experience_years} yrs exp</p>
      </div>
    </div>
  )
}

export default function AISearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (q = query) => {
    if (!q.trim()) return
    setQuery(q)
    setLoading(true)
    setSearched(true)
    try {
      const [candRes, recRes] = await Promise.all([
        axios.get(`${API}/candidates?limit=500`).catch(() => ({ data: [] })),
        axios.get(`${API}/recruiters?limit=50000`).catch(() => ({ data: [] })),
      ])
      setResults(smartSearch(q, candRes.data, recRes.data))
    } catch {
      setResults({ candidates: [], recruiters: [], summary: 'Could not connect to backend.' })
    }
    setLoading(false)
  }

  return (
    <div className="page-enter">
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 4 }}>AI Search</h1>
        <p style={{ fontSize: 13, color: '#94a3b8' }}>Search 12,000+ recruiters by name, company, location, or keyword</p>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e8edf4', borderRadius: '12px', padding: '20px', marginBottom: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <i className="ti ti-search" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: '#94a3b8' }} aria-hidden="true" />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder='Try "Brooksource", "IT staffing NY", "finance recruiter"...'
              style={{ width: '100%', paddingLeft: 38 }}
            />
          </div>
          <button className="btn-primary" onClick={() => handleSearch()} disabled={loading} style={{ opacity: loading ? 0.7 : 1 }}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
        <div>
          <p style={{ fontSize: 11, color: '#cbd5e1', marginBottom: 8 }}>Quick searches:</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {EXAMPLES.map(ex => (
              <button key={ex} onClick={() => handleSearch(ex)}
                style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '5px 12px', color: '#64748b', fontSize: 12, cursor: 'pointer' }}>
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>

      {searched && results && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, padding: '10px 14px', background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '8px' }}>
            <i className="ti ti-info-circle" style={{ fontSize: 15, color: '#0284c7', flexShrink: 0 }} aria-hidden="true" />
            <p style={{ fontSize: 13, color: '#0369a1', margin: 0 }}>{results.summary}</p>
          </div>

          {results.recruiters.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <p style={{ fontSize: 12, fontWeight: 500, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
                Recruiters · {results.recruiters.length} results
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {results.recruiters.map(r => <RecruiterCard key={r.recruiter_id} r={r} />)}
              </div>
            </div>
          )}

          {results.candidates.length > 0 && (
            <div>
              <p style={{ fontSize: 12, fontWeight: 500, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
                Candidates · {results.candidates.length} results
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {results.candidates.map(c => <CandidateCard key={c.candidate_id} c={c} />)}
              </div>
            </div>
          )}

          {results.recruiters.length === 0 && results.candidates.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px 20px', background: '#fff', border: '1px solid #e8edf4', borderRadius: '12px' }}>
              <i className="ti ti-search-off" style={{ fontSize: 32, color: '#cbd5e1', display: 'block', marginBottom: 12 }} aria-hidden="true" />
              <p style={{ fontSize: 14, color: '#64748b', marginBottom: 6 }}>No results found</p>
              <p style={{ fontSize: 12, color: '#94a3b8' }}>Try a different name, company, or keyword</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
