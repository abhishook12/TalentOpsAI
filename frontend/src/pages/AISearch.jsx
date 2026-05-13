import { useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const EXAMPLE_QUERIES = [
  "Find Java developers with H1B visa",
  "Show me candidates in Austin with 4+ years experience",
  "Find active recruiters specializing in DevOps",
  "Show candidates available immediately under $90/hr",
  "Find Data Engineering specialists",
]

const visaColors = {
  H1B: { bg: '#1e3a5f', color: '#38bdf8' },
  GC:  { bg: '#064e3b', color: '#34d399' },
  USC: { bg: '#3b1f00', color: '#fb923c' },
  OPT: { bg: '#3b1f6e', color: '#a78bfa' },
  CPT: { bg: '#3b1f6e', color: '#c4b5fd' },
  TN:  { bg: '#1e3a5f', color: '#7dd3fc' },
}

function Badge({ text, type }) {
  const style = visaColors[text] || { bg: '#1e293b', color: '#94a3b8' }
  return (
    <span style={{
      background: style.bg,
      color: style.color,
      padding: '2px 10px',
      borderRadius: '999px',
      fontSize: '11px',
      fontWeight: '600'
    }}>{text}</span>
  )
}

function CandidateCard({ c }) {
  return (
    <div style={{
      background: '#0f172a',
      borderRadius: '10px',
      padding: '16px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      borderLeft: '3px solid #38bdf8'
    }}>
      <div>
        <p style={{ color: '#f1f5f9', fontWeight: '600', marginBottom: '4px' }}>{c.candidate_name}</p>
        <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '6px' }}>{c.email} · {c.location}</p>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {c.visa_status && <Badge text={c.visa_status} />}
          {(c.skills || []).slice(0, 3).map(s => (
            <span key={s} style={{ background: '#1e293b', color: '#94a3b8', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>{s}</span>
          ))}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <p style={{ color: '#34d399', fontWeight: '600' }}>${c.rate_per_hour}/hr</p>
        <p style={{ color: '#64748b', fontSize: '12px' }}>{c.experience_years} yrs exp</p>
        <p style={{ color: '#94a3b8', fontSize: '12px', marginTop: '4px' }}>{c.availability}</p>
      </div>
    </div>
  )
}

function RecruiterCard({ r }) {
  return (
    <div style={{
      background: '#0f172a',
      borderRadius: '10px',
      padding: '16px 20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      borderLeft: '3px solid #34d399'
    }}>
      <div>
        <p style={{ color: '#f1f5f9', fontWeight: '600', marginBottom: '4px' }}>{r.recruiter_name}</p>
        <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '6px' }}>{r.email}</p>
        <span style={{ background: '#1e293b', color: '#94a3b8', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>{r.specialization}</span>
      </div>
      <div style={{ textAlign: 'right' }}>
        <span style={{
          background: r.is_active ? '#064e3b' : '#450a0a',
          color: r.is_active ? '#34d399' : '#f87171',
          padding: '3px 10px', borderRadius: '999px', fontSize: '12px'
        }}>
          {r.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>
    </div>
  )
}

// Smart local search — no API key needed
function smartSearch(query, candidates, recruiters) {
  const q = query.toLowerCase()
  const results = { candidates: [], recruiters: [], summary: '' }

  // Visa filter
  const visaMatch = q.match(/\b(h1b|gc|usc|opt|cpt|tn)\b/i)
  const visa = visaMatch ? visaMatch[1].toUpperCase() : null

  // Experience filter
  const expMatch = q.match(/(\d+)\+?\s*year/i)
  const minExp = expMatch ? parseInt(expMatch[1]) : null

  // Rate filter
  const rateMatch = q.match(/under\s*\$?(\d+)/i)
  const maxRate = rateMatch ? parseInt(rateMatch[1]) : null

  // Location filter
  const cities = ['austin', 'chicago', 'new york', 'seattle', 'boston', 'san jose', 'san francisco']
  const cityMatch = cities.find(c => q.includes(c))

  // Skill keywords
  const skillKeywords = ['java', 'python', 'react', 'sql', 'devops', 'data', 'ml', 'cloud', 'node', 'django', 'spring', 'kubernetes', 'docker']
  const matchedSkills = skillKeywords.filter(s => q.includes(s))

  // Availability
  const immediate = q.includes('immediate') || q.includes('available now')

  // Search candidates
  const isRecruiterQuery = q.includes('recruiter') || q.includes('specialist') || q.includes('specializ')

  if (!isRecruiterQuery) {
    results.candidates = candidates.filter(c => {
      let match = true
      if (visa && c.visa_status !== visa) match = false
      if (minExp && c.experience_years < minExp) match = false
      if (maxRate && c.rate_per_hour > maxRate) match = false
      if (cityMatch && !c.location?.toLowerCase().includes(cityMatch)) match = false
      if (immediate && c.availability !== 'immediate') match = false
      if (matchedSkills.length > 0) {
        const hasSkill = matchedSkills.some(skill =>
          (c.skills || []).some(s => s.toLowerCase().includes(skill))
        )
        if (!hasSkill) match = false
      }
      return match
    })
  }

  // Search recruiters
  if (isRecruiterQuery || q.includes('recruiter')) {
    results.recruiters = recruiters.filter(r => {
      let match = true
      if (matchedSkills.length > 0) {
        const hasSkill = matchedSkills.some(skill =>
          r.specialization?.toLowerCase().includes(skill)
        )
        if (!hasSkill) match = false
      }
      return match
    })
  }

  const total = results.candidates.length + results.recruiters.length
  results.summary = total > 0
    ? `Found ${results.candidates.length > 0 ? `${results.candidates.length} candidate${results.candidates.length !== 1 ? 's' : ''}` : ''}${results.candidates.length > 0 && results.recruiters.length > 0 ? ' and ' : ''}${results.recruiters.length > 0 ? `${results.recruiters.length} recruiter${results.recruiters.length !== 1 ? 's' : ''}` : ''} matching your query.`
    : 'No results found. Try different keywords like a skill, visa type, or location.'

  return results
}

function AISearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)

    try {
      const [candRes, recRes] = await Promise.all([
        axios.get(`${API}/candidates?limit=100`),
        axios.get(`${API}/recruiters?limit=100`),
      ])
      const found = smartSearch(query, candRes.data, recRes.data)
      setResults(found)
    } catch {
      setResults({ candidates: [], recruiters: [], summary: 'Could not connect to backend. Make sure the server is running.' })
    }
    setLoading(false)
  }

  return (
    <div>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ color: '#f1f5f9', fontSize: '24px', fontWeight: 'bold', marginBottom: '6px' }}>
          ⚡ AI Search
        </h1>
        <p style={{ color: '#64748b' }}>Search recruiters and candidates using natural language</p>
      </div>

      {/* Search Box */}
      <div style={{
        background: '#1e293b',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '24px'
      }}>
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder='Try: "Find Java developers with H1B visa in Austin"'
            style={{
              flex: 1,
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '12px 16px',
              color: '#f1f5f9',
              fontSize: '14px',
              outline: 'none',
            }}
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            style={{
              background: '#38bdf8',
              color: '#0f172a',
              border: 'none',
              borderRadius: '8px',
              padding: '12px 24px',
              fontWeight: '700',
              fontSize: '14px',
              cursor: 'pointer',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>

        {/* Example queries */}
        <div>
          <p style={{ color: '#475569', fontSize: '12px', marginBottom: '8px' }}>Try these:</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {EXAMPLE_QUERIES.map(q => (
              <button
                key={q}
                onClick={() => { setQuery(q); }}
                style={{
                  background: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  color: '#94a3b8',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results */}
      {searched && results && (
        <div>
          <div style={{
            background: '#1e293b',
            borderRadius: '10px',
            padding: '14px 20px',
            marginBottom: '20px',
            borderLeft: '3px solid #38bdf8'
          }}>
            <p style={{ color: '#94a3b8', fontSize: '14px' }}>
              <span style={{ color: '#38bdf8', fontWeight: '600' }}>AI Result: </span>
              {results.summary}
            </p>
          </div>

          {results.candidates.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h2 style={{ color: '#f1f5f9', fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
                Candidates ({results.candidates.length})
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {results.candidates.map(c => <CandidateCard key={c.candidate_id} c={c} />)}
              </div>
            </div>
          )}

          {results.recruiters.length > 0 && (
            <div>
              <h2 style={{ color: '#f1f5f9', fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
                Recruiters ({results.recruiters.length})
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {results.recruiters.map(r => <RecruiterCard key={r.recruiter_id} r={r} />)}
              </div>
            </div>
          )}

          {results.candidates.length === 0 && results.recruiters.length === 0 && (
            <div style={{
              background: '#1e293b',
              borderRadius: '12px',
              padding: '40px',
              textAlign: 'center'
            }}>
              <p style={{ color: '#64748b', fontSize: '16px' }}>No results found for your query.</p>
              <p style={{ color: '#475569', fontSize: '13px', marginTop: '8px' }}>Try different keywords — skill names, visa types, or locations work best.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default AISearch
