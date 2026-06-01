import { useState, useEffect, useRef, useCallback } from 'react'
import api from '../services/api'
import CompanyModal from '../components/CompanyModal'

const US_STATES = [
  { abbr: 'AL', name: 'Alabama' }, { abbr: 'AK', name: 'Alaska' },
  { abbr: 'AZ', name: 'Arizona' }, { abbr: 'AR', name: 'Arkansas' },
  { abbr: 'CA', name: 'California' }, { abbr: 'CO', name: 'Colorado' },
  { abbr: 'CT', name: 'Connecticut' }, { abbr: 'DE', name: 'Delaware' },
  { abbr: 'FL', name: 'Florida' }, { abbr: 'GA', name: 'Georgia' },
  { abbr: 'HI', name: 'Hawaii' }, { abbr: 'ID', name: 'Idaho' },
  { abbr: 'IL', name: 'Illinois' }, { abbr: 'IN', name: 'Indiana' },
  { abbr: 'IA', name: 'Iowa' }, { abbr: 'KS', name: 'Kansas' },
  { abbr: 'KY', name: 'Kentucky' }, { abbr: 'LA', name: 'Louisiana' },
  { abbr: 'ME', name: 'Maine' }, { abbr: 'MD', name: 'Maryland' },
  { abbr: 'MA', name: 'Massachusetts' }, { abbr: 'MI', name: 'Michigan' },
  { abbr: 'MN', name: 'Minnesota' }, { abbr: 'MS', name: 'Mississippi' },
  { abbr: 'MO', name: 'Missouri' }, { abbr: 'MT', name: 'Montana' },
  { abbr: 'NE', name: 'Nebraska' }, { abbr: 'NV', name: 'Nevada' },
  { abbr: 'NH', name: 'New Hampshire' }, { abbr: 'NJ', name: 'New Jersey' },
  { abbr: 'NM', name: 'New Mexico' }, { abbr: 'NY', name: 'New York' },
  { abbr: 'NC', name: 'North Carolina' }, { abbr: 'ND', name: 'North Dakota' },
  { abbr: 'OH', name: 'Ohio' }, { abbr: 'OK', name: 'Oklahoma' },
  { abbr: 'OR', name: 'Oregon' }, { abbr: 'PA', name: 'Pennsylvania' },
  { abbr: 'RI', name: 'Rhode Island' }, { abbr: 'SC', name: 'South Carolina' },
  { abbr: 'SD', name: 'South Dakota' }, { abbr: 'TN', name: 'Tennessee' },
  { abbr: 'TX', name: 'Texas' }, { abbr: 'UT', name: 'Utah' },
  { abbr: 'VT', name: 'Vermont' }, { abbr: 'VA', name: 'Virginia' },
  { abbr: 'WA', name: 'Washington' }, { abbr: 'WV', name: 'West Virginia' },
  { abbr: 'WI', name: 'Wisconsin' }, { abbr: 'WY', name: 'Wyoming' },
]

// Color palette for company avatars
const COLORS = [
  '#1e3a5f','#064e3b','#3b1f6e','#7c2d12','#1e293b',
  '#0f4c75','#1a3a4a','#2d1b69','#1b4332','#3d1f00',
]
function avatarColor(name) {
  let h = 0
  for (let i = 0; i < (name?.length || 0); i++) h = (h + name.charCodeAt(i)) % COLORS.length
  return COLORS[h]
}
function initials(name) {
  if (!name) return '?'
  const p = name.trim().split(/\s+/)
  return (p[0]?.[0] || '') + (p[1]?.[0] || p[0]?.[1] || '')
}

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

function RecruiterBar({ count, max }) {
  const pct = max > 0 ? (count / max) * 100 : 0
  const color = pct > 66 ? '#0F6E56' : pct > 33 ? '#185FA5' : '#94a3b8'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 5, borderRadius: 99, background: 'var(--card-border)', overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: color, borderRadius: 99,
          transition: 'width 0.4s ease',
        }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color, minWidth: 28, textAlign: 'right' }}>{count}</span>
    </div>
  )
}

function SkeletonRow() {
  return (
    <tr>
      <td style={{ padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 34, height: 34, borderRadius: 8, background: 'var(--card-border)', flexShrink: 0 }} />
          <div style={{ width: 140, height: 13, borderRadius: 4, background: 'var(--card-border)', animation: 'pulse 1.4s ease-in-out infinite' }} />
        </div>
      </td>
      <td><div style={{ width: 80, height: 12, borderRadius: 4, background: 'var(--card-border)', animation: 'pulse 1.4s ease-in-out infinite' }} /></td>
      <td><div style={{ width: 60, height: 12, borderRadius: 4, background: 'var(--card-border)', animation: 'pulse 1.4s ease-in-out infinite' }} /></td>
      <td><div style={{ width: 100, height: 12, borderRadius: 4, background: 'var(--card-border)', animation: 'pulse 1.4s ease-in-out infinite' }} /></td>
      <td><div style={{ width: '90%', height: 8, borderRadius: 4, background: 'var(--card-border)', animation: 'pulse 1.4s ease-in-out infinite' }} /></td>
    </tr>
  )
}

export default function CompanyDirectory() {
  const [query, setQuery]           = useState('')
  const [selectedState, setSelectedState] = useState(null)
  const [companies, setCompanies]   = useState([])
  const [loading, setLoading]       = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [totalCount, setTotalCount] = useState(0)
  const [dbTotalCompanies, setDbTotalCompanies] = useState(0)
  const [error, setError]           = useState(null)
  const [stateSearch, setStateSearch] = useState('')
  const [sortBy, setSortBy]         = useState('recruiters') // 'recruiters' | 'name'
  const debounceRef = useRef()
  const [stateCounts, setStateCounts] = useState({})
  
  const [editingCompany, setEditingCompany] = useState(null)
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    const fetchCounts = async () => {
      try {
        const res = await api.get('/analytics/companies-count-by-state')
        setStateCounts(res.data)
      } catch (err) {
        console.error(err)
      }
    }
    fetchCounts()
  }, [])

  const fetchCompanies = useCallback(async (q, state) => {
    setLoading(true)
    setError(null)
    try {
      const params = { limit: 200, skip: 0 }
      if (q?.trim()) params.q = q.trim()
      if (state) params.state = state
      const res = await api.get('/analytics/companies-search', { params })
      setCompanies(res.data)
      const count = parseInt(res.headers['x-total-count'] || res.data.length, 10)
      setTotalCount(count)
      if (!q && !state) {
        setDbTotalCompanies(count)
      }
    } catch {
      setError('Could not connect to backend.')
      setCompanies([])
      setTotalCount(0)
    }
    setLoading(false)
  }, [])

  const handleLoadMore = async () => {
    if (loadingMore) return
    setLoadingMore(true)
    setError(null)
    try {
      const params = { limit: 200, skip: companies.length }
      if (query?.trim()) params.q = query.trim()
      if (selectedState) params.state = selectedState
      const res = await api.get('/analytics/companies-search', { params })
      setCompanies(prev => [...prev, ...res.data])
      const count = parseInt(res.headers['x-total-count'] || totalCount, 10)
      setTotalCount(count)
    } catch {
      setError('Could not connect to backend.')
    }
    setLoadingMore(false)
  }

  // Initial load + on filter change
  useEffect(() => {
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchCompanies(query, selectedState), 300)
    return () => clearTimeout(debounceRef.current)
  }, [query, selectedState, fetchCompanies])

  const maxRecruiters = Math.max(...companies.map(c => c.recruiter_count), 1)

  const sorted = [...companies].sort((a, b) => {
    if (sortBy === 'name') return a.company_name.localeCompare(b.company_name)
    return b.recruiter_count - a.recruiter_count
  })

  const filteredStates = stateSearch.trim()
    ? US_STATES.filter(s =>
        s.name.toLowerCase().includes(stateSearch.toLowerCase()) ||
        s.abbr.toLowerCase().includes(stateSearch.toLowerCase())
      )
    : US_STATES

  // Compute which states have data
  const activeStateAbbrs = new Set(companies.map(c => c.state_abbr))

  return (
    <div className="page-enter">
      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>
            Company Directory
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Browse staffing companies by state — sorted by recruiter headcount
          </p>
        </div>
        <button className="btn-primary" onClick={() => { setEditingCompany(null); setShowModal(true); }}>
          <i className="ti ti-plus" />
          Add Company
        </button>
      </div>

      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>

        {/* ── Left Panel: State Filter ─────────────────────────── */}
        <div style={{ flex: '0 0 200px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="card" style={{ padding: 14 }}>
            <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
              Filter by State
            </p>

            {/* State search */}
            <div style={{
              background: 'var(--main-bg)', border: '1px solid var(--card-border)',
              borderRadius: 7, padding: '6px 10px', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8,
            }}>
              <i className="ti ti-search" style={{ fontSize: 13, color: 'var(--text-muted)', flexShrink: 0 }} />
              <input
                value={stateSearch}
                onChange={e => setStateSearch(e.target.value)}
                placeholder="Search states..."
                style={{
                  flex: 1, border: 'none', background: 'transparent', outline: 'none',
                  fontSize: 12, color: 'var(--text-primary)', padding: 0,
                }}
              />
            </div>

            {/* All States pill */}
            <button
              onClick={() => setSelectedState(null)}
              style={{
                width: '100%', textAlign: 'left', padding: '7px 10px', borderRadius: 7,
                fontSize: 12, fontWeight: selectedState === null ? 600 : 400,
                border: selectedState === null ? '1.5px solid var(--accent)' : '1.5px solid transparent',
                background: selectedState === null ? 'rgba(24,95,165,0.08)' : 'transparent',
                color: selectedState === null ? 'var(--accent)' : '#ffffff',
                cursor: 'pointer', marginBottom: 4, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                transition: 'all 0.12s',
              }}
            >
              <span>All States</span>
              <span style={{ fontSize: 10, fontWeight: 600, color: selectedState === null ? 'var(--accent)' : 'rgba(255, 255, 255, 0.5)' }}>{dbTotalCompanies || totalCount}</span>
            </button>

            {/* State list */}
            <div style={{ maxHeight: 380, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
              {filteredStates.map(({ abbr, name }) => {
                const isActive = selectedState === abbr
                const count = stateCounts[abbr] || 0
                const hasData  = count > 0
                return (
                  <button
                    key={abbr}
                    onClick={() => setSelectedState(isActive ? null : abbr)}
                    style={{
                      width: '100%', textAlign: 'left', padding: '6px 10px', borderRadius: 6,
                      fontSize: 12, fontWeight: isActive ? 600 : 400,
                      border: isActive ? '1.5px solid var(--accent)' : '1.5px solid transparent',
                      background: isActive ? 'rgba(24,95,165,0.08)' : 'transparent',
                      color: isActive ? 'var(--accent)' : hasData ? '#ffffff' : 'rgba(255, 255, 255, 0.35)',
                      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      transition: 'all 0.1s',
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--main-bg)' }}
                    onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent' }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontWeight: 600, fontSize: 11, minWidth: 24, color: isActive ? 'var(--accent)' : hasData ? 'rgba(255, 255, 255, 0.7)' : 'rgba(255, 255, 255, 0.35)' }}>{abbr}</span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 90, color: isActive ? 'var(--accent)' : hasData ? '#ffffff' : 'rgba(255, 255, 255, 0.35)' }}>{name}</span>
                    </span>
                    {count > 0 && (
                      <span style={{ fontSize: 10, fontWeight: 600, color: isActive ? 'var(--accent)' : 'rgba(255, 255, 255, 0.5)', flexShrink: 0 }}>
                        {count}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* ── Right Panel: Company Table ───────────────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>

          {/* Search bar */}
          <div style={{
            background: 'var(--card-bg)', border: `1.5px solid ${query ? 'var(--accent)' : 'var(--card-border)'}`,
            borderRadius: 10, padding: '0 14px', display: 'flex', alignItems: 'center', gap: 10,
            boxShadow: query ? '0 0 0 3px rgba(24,95,165,0.08)' : '0 1px 3px rgba(0,0,0,0.04)',
            transition: 'border-color 0.15s, box-shadow 0.15s',
          }}>
            {loading
              ? <i className="ti ti-loader" style={{ fontSize: 17, color: 'var(--accent)', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
              : <i className="ti ti-building" style={{ fontSize: 17, color: query ? 'var(--accent)' : 'var(--text-muted)', flexShrink: 0, transition: 'color 0.15s' }} />
            }
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search company name..."
              autoComplete="off"
              style={{
                flex: 1, border: 'none', background: 'transparent', outline: 'none',
                fontSize: 14, color: 'var(--text-primary)', padding: '13px 0',
              }}
            />
            {/* Sort toggle */}
            <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
              {[['recruiters', 'ti-sort-descending-numbers', 'By Recruiters'], ['name', 'ti-sort-ascending-letters', 'A–Z']].map(([val, icon, label]) => (
                <button
                  key={val}
                  onClick={() => setSortBy(val)}
                  title={label}
                  style={{
                    background: sortBy === val ? 'rgba(24,95,165,0.1)' : 'none',
                    border: sortBy === val ? '1px solid rgba(24,95,165,0.25)' : '1px solid transparent',
                    borderRadius: 6, padding: '4px 8px', color: sortBy === val ? 'var(--accent)' : 'var(--text-muted)',
                    fontSize: 14, lineHeight: 1, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                    transition: 'all 0.12s',
                  }}
                >
                  <i className={`ti ${icon}`} />
                  <span style={{ fontSize: 11 }}>{label}</span>
                </button>
              ))}
            </div>
            {query && (
              <button onClick={() => setQuery('')}
                style={{ background: 'none', border: 'none', padding: 4, color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16, lineHeight: 1, display: 'flex' }}>
                <i className="ti ti-x" />
              </button>
            )}
          </div>

          {/* State banner */}
          {selectedState && (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '9px 14px', background: 'rgba(24,95,165,0.06)',
              border: '1px solid rgba(24,95,165,0.18)', borderRadius: 9,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <i className="ti ti-map-pin" style={{ color: 'var(--accent)', fontSize: 15 }} />
                <span style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>
                  {US_STATES.find(s => s.abbr === selectedState)?.name || selectedState}
                </span>
                <span style={{
                  fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 4,
                  background: 'var(--accent)', color: '#fff', letterSpacing: '0.04em',
                }}>{selectedState}</span>
              </div>
              <button onClick={() => setSelectedState(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer', padding: 0 }}>
                Clear ×
              </button>
            </div>
          )}

          {/* Table card */}
          <div className="card" style={{ overflow: 'hidden' }}>
            {/* Table header */}
            <div style={{
              display: 'grid', gridTemplateColumns: '2.5fr 1fr 1fr 1.2fr 2fr',
              padding: '10px 16px', background: 'var(--main-bg)',
              borderBottom: '1px solid var(--card-border)',
            }}>
              {['Company', 'State', 'Industry', 'Location', 'Recruiters'].map(h => (
                <span key={h} style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</span>
              ))}
            </div>

            {/* Loading */}
            {loading && (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <tbody>{Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)}</tbody>
              </table>
            )}

            {/* Error */}
            {error && !loading && (
              <div style={{ padding: '48px 20px', textAlign: 'center' }}>
                <i className="ti ti-wifi-off" style={{ fontSize: 28, color: 'var(--text-muted)', display: 'block', marginBottom: 10 }} />
                <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{error}</p>
              </div>
            )}

            {/* Results */}
            {!loading && !error && (
              <>
                <div style={{ padding: '8px 16px 6px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    <strong style={{ color: 'var(--text-primary)' }}>{totalCount.toLocaleString()}</strong> compan{totalCount !== 1 ? 'ies' : 'y'}
                    {selectedState ? ` in ${selectedState}` : ''}{query ? ` matching "${query}"` : ''}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Loaded recruiters: <strong style={{ color: 'var(--text-primary)' }}>
                      {sorted.reduce((s, c) => s + c.recruiter_count, 0).toLocaleString()}
                    </strong>
                  </span>
                </div>

                {sorted.length === 0 ? (
                  <div style={{ padding: '60px 20px', textAlign: 'center' }}>
                    <i className="ti ti-building-off" style={{ fontSize: 36, color: 'var(--text-muted)', display: 'block', marginBottom: 12, opacity: 0.4 }} />
                    <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 4 }}>No companies found</p>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Try a different state or search term</p>
                  </div>
                ) : (
                  <>
                    {sorted.map((c, idx) => (
                      <div
                        key={c.company_id}
                        style={{
                          display: 'grid', gridTemplateColumns: '2.5fr 1fr 1fr 1.2fr 2fr',
                          padding: '12px 16px', alignItems: 'center',
                          borderBottom: '1px solid var(--card-border)',
                          transition: 'background 0.1s', cursor: 'default',
                          borderLeft: idx === 0 && !query && !selectedState ? '3px solid #eab308' : '3px solid transparent',
                          background: idx === 0 && !query && !selectedState ? 'rgba(234,179,8,0.04)' : 'transparent',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--main-bg)'}
                        onMouseLeave={e => e.currentTarget.style.background = idx === 0 && !query && !selectedState ? 'rgba(234,179,8,0.04)' : 'transparent'}
                      >
                        {/* Company name + avatar */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                          <div style={{
                            width: 34, height: 34, borderRadius: 8, flexShrink: 0,
                            background: avatarColor(c.company_name),
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 12, fontWeight: 700, color: '#fff', letterSpacing: '0.03em',
                          }}>
                            {initials(c.company_name)}
                          </div>
                          <div style={{ minWidth: 0 }}>
                            <p style={{ margin: 0, fontSize: 13.5, fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              <Highlight text={c.company_name} query={query} />
                            </p>
                            {c.website && (
                              <a href={c.website.startsWith('http') ? c.website : `https://${c.website}`}
                                target="_blank" rel="noreferrer"
                                style={{ fontSize: 11, color: 'var(--accent)', textDecoration: 'none', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}
                                onClick={e => e.stopPropagation()}
                              >
                                {c.website.replace(/^https?:\/\//, '').slice(0, 28)}
                              </a>
                            )}
                          </div>
                        </div>

                        {/* State badge */}
                        <div>
                          <span
                            onClick={() => setSelectedState(c.state_abbr === selectedState ? null : c.state_abbr)}
                            style={{
                              fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 5,
                              background: c.state_abbr === selectedState ? 'var(--accent)' : 'rgba(24,95,165,0.08)',
                              color: c.state_abbr === selectedState ? '#fff' : 'var(--accent)',
                              cursor: 'pointer', whiteSpace: 'nowrap',
                              border: '1px solid rgba(24,95,165,0.2)',
                              transition: 'all 0.12s',
                            }}
                          >
                            {c.state_abbr}
                          </span>
                        </div>

                        {/* Industry */}
                        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {c.industry || '—'}
                        </p>

                        {/* Location */}
                        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {c.location || '—'}
                        </p>

                        {/* Recruiter bar */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'space-between' }}>
                          <div style={{ flex: 1 }}>
                            <RecruiterBar count={c.recruiter_count} max={maxRecruiters} />
                          </div>
                          <button
                            onClick={() => { setEditingCompany(c); setShowModal(true); }}
                            title="Edit Company"
                            style={{
                              background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 6,
                              padding: '4px 6px', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex'
                            }}
                            onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent)'; e.currentTarget.style.borderColor = 'var(--accent)'; }}
                            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--card-border)'; }}
                          >
                            <i className="ti ti-pencil" style={{ fontSize: 14 }} />
                          </button>
                        </div>
                      </div>
                    ))}

                    {sorted.length < totalCount && (
                      <div style={{ padding: '18px 20px', textAlign: 'center' }}>
                        <button
                          onClick={handleLoadMore}
                          disabled={loadingMore}
                          style={{
                            padding: '8px 18px',
                            borderRadius: 8,
                            background: 'var(--accent)',
                            color: '#fff',
                            border: 'none',
                            fontSize: 13,
                            fontWeight: 500,
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 6,
                            boxShadow: '0 2px 4px rgba(24,95,165,0.15)',
                            transition: 'opacity 0.15s',
                          }}
                          onMouseEnter={e => e.currentTarget.style.opacity = 0.9}
                          onMouseLeave={e => e.currentTarget.style.opacity = 1}
                        >
                          {loadingMore ? (
                            <>
                              <i className="ti ti-loader" style={{ animation: 'spin 1s linear infinite' }} />
                              Loading more...
                            </>
                          ) : (
                            <>
                              <i className="ti ti-chevron-down" />
                              Load More ({totalCount - sorted.length} remaining)
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {showModal && (
        <CompanyModal
          company={editingCompany}
          onClose={() => setShowModal(false)}
          onSave={(savedCompany) => {
            setShowModal(false);
            if (editingCompany) {
              setCompanies(prev => prev.map(c => c.company_id === savedCompany.company_id ? { ...c, ...savedCompany } : c));
            } else {
              setCompanies(prev => [savedCompany, ...prev]);
            }
          }}
        />
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
      `}</style>
    </div>
  )
}
