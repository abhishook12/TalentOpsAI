import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const EXAMPLES = [
  'Brooksource', 'Insight Global', 'Java recruiter',
  'IT staffing New York', 'finance recruiter', 'DevOps specialist',
]

const RECENT_KEY = 'talentops_recent_searches'
const MAX_RECENT = 6

function getRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]') } catch { return [] }
}
function addRecent(q) {
  const prev = getRecent().filter(s => s !== q)
  localStorage.setItem(RECENT_KEY, JSON.stringify([q, ...prev].slice(0, MAX_RECENT)))
}

// Highlight matched text
function Highlight({ text, query }) {
  if (!text || !query) return <span>{text || '—'}</span>
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return <span>{text}</span>
  return (
    <span>
      {text.slice(0, idx)}
      <mark style={{ background: 'rgba(24,95,165,0.18)', color: 'var(--accent)', borderRadius: 3, padding: '0 1px' }}>
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </span>
  )
}

// Avatar
const AVATAR_COLORS = ['#1e3a5f', '#064e3b', '#3b1f6e', '#5b2d00', '#1e293b', '#172033', '#1a3a4a', '#4a1942']
function avatarColor(name) {
  let h = 0
  for (let i = 0; i < (name?.length || 0); i++) h = (h + name.charCodeAt(i)) % AVATAR_COLORS.length
  return AVATAR_COLORS[h]
}
function initials(name) {
  if (!name) return '?'
  const p = name.trim().split(' ')
  return (p[0]?.[0] || '') + (p[1]?.[0] || '')
}

// Score badge
function ScoreBadge({ score }) {
  const color = score >= 150 ? '#0F6E56' : score >= 80 ? '#185FA5' : score >= 40 ? '#BA7517' : '#94a3b8'
  const label = score >= 150 ? 'Exact' : score >= 80 ? 'Strong' : score >= 40 ? 'Partial' : 'Fuzzy'
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '3px 7px', borderRadius: 4,
      background: color + '18', color, letterSpacing: '0.03em', whiteSpace: 'nowrap',
    }}>{label}</span>
  )
}

// Result Row
function RecruiterRow({ r, query, focused }) {
  const firstName = r.recruiter_name?.split(' ')[0] || ''
  const company = r.company_name || (() => {
    const at = r.email?.indexOf('@')
    if (at < 0) return ''
    const domain = r.email?.slice(at + 1).split('.')[0] || ''
    return ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol'].includes(domain) ? '' : domain
  })()

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '11px 16px',
      background: focused ? 'var(--main-bg)' : 'transparent',
      borderBottom: '1px solid var(--card-border)',
      transition: 'background 0.1s',
      cursor: 'default',
    }}>
      {/* Avatar */}
      <div style={{
        width: 34, height: 34, borderRadius: '50%',
        background: avatarColor(r.recruiter_name),
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 600, color: '#fff', flexShrink: 0, letterSpacing: '0.03em',
      }}>{initials(r.recruiter_name)}</div>

      {/* Data columns */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.4fr 2fr 1.2fr 1.4fr 1.2fr', gap: 8, minWidth: 0 }}>
        <p style={{ margin: 0, fontSize: 13.5, fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          <Highlight text={firstName} query={query} />
        </p>
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          <Highlight text={r.email} query={query} />
        </p>
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {r.phone || '—'}
        </p>
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          <Highlight text={company || null} query={query} />
        </p>
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {r.location || '—'}
        </p>
      </div>

      {/* Score badge */}
      <div style={{ flexShrink: 0 }}>
        <ScoreBadge score={r.relevance_score} />
      </div>
    </div>
  )
}

// Skeleton loading row
function SkeletonRow() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 16px', borderBottom: '1px solid var(--card-border)' }}>
      <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'var(--card-border)', flexShrink: 0 }} />
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.4fr 2fr 1.2fr 1.4fr 1.2fr', gap: 8 }}>
        {[80, 160, 90, 120, 70].map((w, i) => (
          <div key={i} style={{ height: 12, width: w, borderRadius: 4, background: 'var(--card-border)', animation: 'pulse 1.4s ease-in-out infinite' }} />
        ))}
      </div>
      <div style={{ width: 50, height: 20, borderRadius: 4, background: 'var(--card-border)', animation: 'pulse 1.4s ease-in-out infinite' }} />
    </div>
  )
}

export default function AISearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [focused, setFocused] = useState(false)
  const [focusedIdx, setFocusedIdx] = useState(-1)
  const [recent, setRecent] = useState(getRecent())

  const inputRef = useRef()
  const debounceRef = useRef()

  // Debounced search — fires 300ms after user stops typing
  const doSearch = useCallback(async (q) => {
    if (!q.trim()) { setResults(null); setError(null); setLoading(false); return }
    setLoading(true)
    setError(null)
    try {
      const res = await axios.get(`${API}/recruiters/search`, { params: { q: q.trim(), limit: 100 } })
      setResults(res.data)
    } catch (e) {
      setError(e.response?.status === 422 ? 'Query too short.' : 'Could not connect to backend. Please try again.')
      setResults(null)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    clearTimeout(debounceRef.current)
    if (!query.trim()) { setResults(null); setLoading(false); return }
    setLoading(true)
    debounceRef.current = setTimeout(() => doSearch(query), 300)
    return () => clearTimeout(debounceRef.current)
  }, [query, doSearch])

  const handleSelect = (q) => {
    setQuery(q)
    addRecent(q)
    setRecent(getRecent())
    setFocused(false)
    inputRef.current?.blur()
  }

  const handleKeyDown = (e) => {
    const list = results || []
    if (e.key === 'ArrowDown') { e.preventDefault(); setFocusedIdx(i => Math.min(i + 1, list.length - 1)) }
    if (e.key === 'ArrowUp') { e.preventDefault(); setFocusedIdx(i => Math.max(i - 1, -1)) }
    if (e.key === 'Escape') { setFocused(false); inputRef.current?.blur() }
    if (e.key === 'Enter' && query.trim()) {
      addRecent(query.trim())
      setRecent(getRecent())
      setFocused(false)
    }
  }

  const showDropdown = focused && !query.trim() && (recent.length > 0 || EXAMPLES.length > 0)
  const showResults = results !== null && query.trim()

  return (
    <div className="page-enter">
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>AI Search</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Smart ranked search across 12,000+ recruiters — exact matches first, fuzzy matches last</p>
      </div>

      {/* Search Box */}
      <div style={{ position: 'relative', marginBottom: 20 }}>
        <div style={{
          background: 'var(--card-bg)', border: `1.5px solid ${focused ? 'var(--accent)' : 'var(--card-border)'}`,
          borderRadius: 12, padding: '0 16px', display: 'flex', alignItems: 'center', gap: 10,
          boxShadow: focused ? '0 0 0 3px rgba(24,95,165,0.1)' : '0 1px 3px rgba(0,0,0,0.05)',
          transition: 'border-color 0.15s, box-shadow 0.15s',
        }}>
          {loading
            ? <i className="ti ti-loader" style={{ fontSize: 18, color: 'var(--accent)', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
            : <i className="ti ti-search" style={{ fontSize: 18, color: focused ? 'var(--accent)' : 'var(--text-muted)', flexShrink: 0, transition: 'color 0.15s' }} />
          }
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setFocusedIdx(-1) }}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 150)}
            onKeyDown={handleKeyDown}
            placeholder='Search by name, email, company, specialization...'
            autoComplete="off"
            style={{
              flex: 1, border: 'none', background: 'transparent', outline: 'none',
              fontSize: 15, color: 'var(--text-primary)', padding: '14px 0',
            }}
          />
          {query && (
            <button onClick={() => { setQuery(''); setResults(null); inputRef.current?.focus() }}
              style={{ background: 'none', border: 'none', padding: 4, color: 'var(--text-muted)', cursor: 'pointer', fontSize: 18, lineHeight: 1, display: 'flex' }}>
              <i className="ti ti-x" />
            </button>
          )}
        </div>

        {/* Dropdown: recent + quick searches */}
        {showDropdown && (
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 100,
            background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 10,
            boxShadow: '0 8px 24px rgba(0,0,0,0.12)', overflow: 'hidden',
          }}>
            {recent.length > 0 && (
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '10px 14px 6px' }}>Recent Searches</p>
                {recent.map(r => (
                  <div key={r} onClick={() => handleSelect(r)}
                    style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 14px', cursor: 'pointer', transition: 'background 0.1s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--main-bg)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <i className="ti ti-history" style={{ fontSize: 14, color: 'var(--text-muted)' }} />
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{r}</span>
                  </div>
                ))}
              </div>
            )}
            <div style={{ borderTop: recent.length > 0 ? '1px solid var(--card-border)' : 'none' }}>
              <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '10px 14px 6px' }}>Quick Searches</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, padding: '0 14px 12px' }}>
                {EXAMPLES.map(ex => (
                  <button key={ex} onClick={() => handleSelect(ex)}
                    style={{ background: 'var(--main-bg)', border: '1px solid var(--card-border)', borderRadius: 6, padding: '5px 12px', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer' }}>
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {showResults && (
        <div className="card" style={{ overflow: 'hidden' }}>
          {/* Column headers */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', background: 'var(--main-bg)', borderBottom: '1px solid var(--card-border)' }}>
            <div style={{ width: 34, flexShrink: 0 }} />
            <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.4fr 2fr 1.2fr 1.4fr 1.2fr', gap: 8 }}>
              {['First Name', 'Email', 'Phone', 'Company', 'Location'].map(h => (
                <span key={h} style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</span>
              ))}
            </div>
            <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', flexShrink: 0 }}>Match</span>
          </div>

          {/* Loading skeletons */}
          {loading && Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}

          {/* Error */}
          {error && !loading && (
            <div style={{ padding: '40px 20px', textAlign: 'center' }}>
              <i className="ti ti-wifi-off" style={{ fontSize: 28, color: 'var(--text-muted)', display: 'block', marginBottom: 10 }} />
              <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{error}</p>
            </div>
          )}

          {/* Results */}
          {!loading && !error && results.length > 0 && (
            <>
              <div style={{ padding: '8px 16px 6px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {results.length} result{results.length !== 1 ? 's' : ''} for <strong style={{ color: 'var(--text-primary)' }}>"{query}"</strong>
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Sorted by relevance</span>
              </div>
              {results.map((r, i) => (
                <RecruiterRow key={r.recruiter_id} r={r} query={query} focused={i === focusedIdx} />
              ))}
            </>
          )}

          {/* No results */}
          {!loading && !error && results.length === 0 && (
            <div style={{ padding: '52px 20px', textAlign: 'center' }}>
              <i className="ti ti-search-off" style={{ fontSize: 32, color: 'var(--text-muted)', display: 'block', marginBottom: 12 }} />
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 6 }}>No recruiters found for "{query}"</p>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Try a different name, email, company, or keyword</p>
            </div>
          )}
        </div>
      )}

      {/* Empty state — no query yet */}
      {!showResults && !loading && (
        <div style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ width: 56, height: 56, borderRadius: 14, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <i className="ti ti-search" style={{ fontSize: 26, color: '#fff' }} />
          </div>
          <p style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 8 }}>Smart Ranked Search</p>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 340, margin: '0 auto' }}>
            Type a name, email, company, or keyword. Exact matches rank first, fuzzy matches last.
          </p>
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
