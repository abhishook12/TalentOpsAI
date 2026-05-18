import { useState } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const EXAMPLES = [
  'Brooksource', 'IT staffing New York', 'Java recruiter',
  'Insight Global', 'finance recruiter', 'DevOps specialist',
]

// Extract company hint from email domain: john@brooksource.com → 'brooksource'
function emailDomain(email) {
  if (!email) return ''
  const at = email.indexOf('@')
  if (at < 0) return ''
  const domain = email.slice(at + 1).toLowerCase()
  // strip common personal email domains
  const personal = ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol', 'noemail']
  const company = domain.split('.')[0]
  return personal.includes(company) ? '' : company
}

function scoreRecruiter(r, words, fullQuery) {
  let score = 0
  let wordsMatched = 0
  
  const companyHint = emailDomain(r.email)
  const fields = [
    { val: r.recruiter_name,  weight: 10 },
    { val: r.company_name,    weight: 8  },  
    { val: companyHint,       weight: 8  },  
    { val: r.email,           weight: 3  },
    { val: r.specialization,  weight: 6  },
    { val: r.location,        weight: 4  },
    { val: r.phone,           weight: 2  },
  ]

  let hasFullMatch = false
  if (r.recruiter_name?.toLowerCase().includes(fullQuery)) { score += 200; hasFullMatch = true }
  if (r.company_name?.toLowerCase().includes(fullQuery)) { score += 150; hasFullMatch = true }

  for (const word of words) {
    let wordMatched = false
    let bestWordScore = 0
    for (const { val, weight } of fields) {
      if (!val) continue
      const v = val.toLowerCase()
      if (v === word) {
        bestWordScore = Math.max(bestWordScore, weight * 4)
        wordMatched = true
      } else if (v.startsWith(word)) {
        bestWordScore = Math.max(bestWordScore, weight * 2)
        wordMatched = true
      } else if (v.includes(word)) {
        bestWordScore = Math.max(bestWordScore, weight)
        wordMatched = true
      }
    }
    score += bestWordScore
    if (wordMatched) wordsMatched++
  }

  // Strict filtering: If 2 words (like First Last name), require BOTH words to match somewhere
  if (words.length === 2 && wordsMatched < 2 && !hasFullMatch) return 0
  
  // Strict filtering: If 3+ words, require at least half of the words to match
  if (words.length > 2 && (wordsMatched / words.length) < 0.5 && !hasFullMatch) return 0

  return score
}

function smartSearch(query, recruiters) {
  const q = query.toLowerCase().trim()
  const words = q.split(/\s+/).filter(w => w.length >= 2)
  if (!words.length) return { recruiters: [], summary: 'Type something to search.' }

  const scored = recruiters
    .map(r => ({ r, score: scoreRecruiter(r, words, q) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 100)
    .map(({ r }) => r)

  const summary = scored.length > 0
    ? `Found ${scored.length} recruiter${scored.length !== 1 ? 's' : ''} for "${query}"`
    : `No results for "${query}". Try a different name, company, or keyword.`

  return { recruiters: scored, summary }
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
  const firstName = r.recruiter_name?.split(' ')[0] || ''
  const company = r.company_name || emailDomain(r.email)

  return (
    <div style={{
      background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '10px',
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
      
      <div style={{ flex: 1, minWidth: 0, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, alignItems: 'center' }}>
        <p style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text-primary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {firstName || '—'}
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {r.email || '—'}
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {r.phone || '—'}
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {company || '—'}
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {r.location || 'Location TBA'}
        </p>
      </div>
    </div>
  )
}

export default function AISearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [warming, setWarming] = useState(false)

  // Ping backend on mount to wake up Render free instance
  useState(() => {
    setWarming(true)
    axios.get(`${API}/ping`).finally(() => setWarming(false))
  })

  const handleSearch = async (q = query) => {
    if (!q.trim()) return
    setQuery(q)
    setLoading(true)
    setSearched(true)
    try {
      const recRes = await axios.get(`${API}/recruiters?limit=50000`).catch(() => ({ data: [] }))
      setResults(smartSearch(q, recRes.data))
    } catch {
      setResults({ recruiters: [], summary: 'Could not connect to backend. Please try again in a moment.' })
    }
    setLoading(false)
  }

  return (
    <div className="page-enter">
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>AI Search</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Search 12,000+ recruiters by name, company, location, or keyword</p>
      </div>

      <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '12px', padding: '20px', marginBottom: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <i className="ti ti-search" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 16, color: 'var(--text-muted)' }} aria-hidden="true" />
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
          <p style={{ fontSize: 11, color: 'var(--border-input)', marginBottom: 8 }}>Quick searches:</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {EXAMPLES.map(ex => (
              <button key={ex} onClick={() => handleSearch(ex)}
                style={{ background: 'var(--bg-hover)', border: '1px solid var(--card-border)', borderRadius: '6px', padding: '5px 12px', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer' }}>
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>

      {searched && results && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, padding: '10px 14px', background: 'var(--accent-bg)', border: '1px solid var(--accent)', borderRadius: '8px' }}>
            <i className="ti ti-info-circle" style={{ fontSize: 15, color: 'var(--accent)', flexShrink: 0 }} aria-hidden="true" />
            <p style={{ fontSize: 13, color: 'var(--accent-hover)', margin: 0 }}>{results.summary}</p>
          </div>

          {results.recruiters.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', padding: '0 16px', marginBottom: 12 }}>
                 <div style={{ width: 52 }} /> {/* Avatar spacing */}
                 <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
                   {['First Name', 'Email', 'Phone', 'Company', 'Location'].map(h => (
                     <span key={h} style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</span>
                   ))}
                 </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {results.recruiters.map(r => <RecruiterCard key={r.recruiter_id} r={r} />)}
              </div>
            </div>
          )}

          {results.recruiters.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px 20px', background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '12px' }}>
              <i className="ti ti-search-off" style={{ fontSize: 32, color: 'var(--border-input)', display: 'block', marginBottom: 12 }} aria-hidden="true" />
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 6 }}>No results found</p>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Try a different name, company, or keyword</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
