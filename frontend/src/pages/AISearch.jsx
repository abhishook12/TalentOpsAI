import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { API } from '../services/api'

function initials(name) {
  const parts = (name || '').trim().split(' ').filter(Boolean)
  if (!parts.length) return 'NA'
  return ((parts[0][0] || '') + (parts[1]?.[0] || '')).toUpperCase()
}

function matchTypeFor(rec, q) {
  const s = (q || '').trim().toLowerCase()
  if (!s) return 'Fuzzy'
  const name = (rec.recruiter_name || '').toLowerCase()
  const email = (rec.email || '').toLowerCase()
  const company = (rec.company_name || '').toLowerCase()
  if (name === s || email === s || company === s) return 'Exact'
  if (name.startsWith(s) || email.startsWith(s) || company.startsWith(s)) return 'Exact'
  return 'Fuzzy'
}

function safe(v) {
  return v && String(v).trim() ? v : 'Not available'
}

export default function AISearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [showFilters, setShowFilters] = useState(false)
  const [toast, setToast] = useState('')
  const [filterCompany, setFilterCompany] = useState('')
  const [filterLocation, setFilterLocation] = useState('')
  const [filterSpecialization, setFilterSpecialization] = useState('')

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!query.trim()) {
        setResults([])
        setSelectedId(null)
        setLoading(false)
        setError('')
        return
      }
      setLoading(true)
      setError('')
      try {
        const params = { q: query.trim(), limit: 100 }
        if (filterCompany.trim()) params.company = filterCompany.trim()
        if (filterLocation.trim()) params.location = filterLocation.trim()
        if (filterSpecialization.trim()) params.specialization = filterSpecialization.trim()
        const res = await axios.get(`${API}/recruiters/search`, { params })
        const sorted = [...(res.data || [])].sort((a, b) => {
          const ma = matchTypeFor(a, query) === 'Exact' ? 0 : 1
          const mb = matchTypeFor(b, query) === 'Exact' ? 0 : 1
          if (ma !== mb) return ma - mb
          return (b.relevance_score || 0) - (a.relevance_score || 0)
        })
        setResults(sorted)
        // Keep details panel empty until user explicitly clicks a recruiter row.
        setSelectedId(prev => (prev && sorted.some(x => x.recruiter_id === prev) ? prev : null))
      } catch {
        setError('Could not load recruiter search results.')
        setResults([])
        setSelectedId(null)
      } finally {
        setLoading(false)
      }
    }, 260)
    return () => clearTimeout(t)
  }, [query, filterCompany, filterLocation, filterSpecialization])

  const selected = useMemo(
    () => results.find(r => r.recruiter_id === selectedId) || null,
    [results, selectedId]
  )

  const fireSoon = (label) => {
    setToast(`${label}: Coming soon`)
    console.log(`[Coming soon] ${label}`)
    setTimeout(() => setToast(''), 1400)
  }

  return (
    <div className="page-enter" style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: 0, border: '1px solid var(--card-border)', borderRadius: 12, overflow: 'hidden', background: 'var(--panel-bg)', minHeight: 'calc(100vh - 170px)' }}>
      <div style={{ borderRight: '1px solid var(--card-border)', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <h1 style={{ fontSize: 52? 0: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>Smart Search</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Smart ranked search across recruiter records — exact matches first, fuzzy matches last</p>
        </div>

        <div style={{ border: '1px solid var(--card-border)', borderRadius: 10, background: 'var(--card-bg)', padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <i className="ti ti-search" style={{ color: 'var(--text-muted)' }} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search recruiters by name, email, company..."
            style={{ flex: 1, border: 'none', background: 'transparent', padding: 8 }}
          />
          <button
            onClick={() => setShowFilters(v => !v)}
            title="Filters"
            style={{ width: 30, height: 30, border: '1px solid var(--card-border)', background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
          >
            <i className="ti ti-adjustments-horizontal" />
          </button>
          <button
            onClick={() => { setQuery(''); setResults([]); setSelectedId(null) }}
            title="Clear"
            style={{ width: 30, height: 30, border: '1px solid var(--card-border)', background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
          >
            <i className="ti ti-x" />
          </button>
        </div>

        {showFilters && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <input value={filterCompany} onChange={(e) => setFilterCompany(e.target.value)} placeholder="Filter company" />
            <input value={filterLocation} onChange={(e) => setFilterLocation(e.target.value)} placeholder="Filter location" />
            <input value={filterSpecialization} onChange={(e) => setFilterSpecialization(e.target.value)} placeholder="Filter specialization" />
          </div>
        )}

        <div style={{ border: '1px solid var(--card-border)', borderRadius: 10, overflow: 'hidden', flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr 1.5fr 1.5fr 0.9fr', gap: 8, padding: '10px 12px', borderBottom: '1px solid var(--card-border)', background: 'var(--bg-hover)' }}>
            {['Name', 'Email', 'Phone', 'Company', 'Match Type'].map(h => (
              <span key={h} style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</span>
            ))}
          </div>

          <div style={{ overflow: 'auto', flex: 1 }}>
            {loading && (
              <div style={{ padding: 26, color: 'var(--text-muted)', textAlign: 'center' }}>
                <i className="ti ti-loader" style={{ animation: 'spin 0.8s linear infinite' }} /> Loading recruiters...
              </div>
            )}

            {!loading && error && (
              <div style={{ padding: 26, color: '#b91c1c', textAlign: 'center' }}>{error}</div>
            )}

            {!loading && !error && query.trim() && results.length === 0 && (
              <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-muted)' }}>
                <i className="ti ti-search-off" style={{ fontSize: 22, display: 'block', marginBottom: 8 }} />
                No recruiter matches found.
              </div>
            )}

            {!loading && !error && !query.trim() && (
              <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-muted)' }}>
                <i className="ti ti-database-search" style={{ fontSize: 22, display: 'block', marginBottom: 8 }} />
                Start typing to search real recruiter data.
              </div>
            )}

            {!loading && !error && results.map((r) => {
              const isActive = selectedId === r.recruiter_id
              const m = matchTypeFor(r, query)
              return (
                <button
                  key={r.recruiter_id}
                  onClick={() => setSelectedId(r.recruiter_id)}
                  style={{
                    width: '100%',
                    border: 'none',
                    borderBottom: '1px solid var(--card-border)',
                    background: isActive ? 'var(--accent-bg)' : 'var(--card-bg)',
                    textAlign: 'left',
                    padding: 0,
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr 1.5fr 1.5fr 0.9fr', gap: 8, padding: '10px 12px', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ width: 28, height: 28, borderRadius: 6, background: 'var(--text-primary)', color: 'var(--text-inverse)', fontSize: 11, fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                        {initials(r.recruiter_name)}
                      </span>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{safe(r.recruiter_name)}</span>
                    </div>
                    <span style={{ color: 'var(--text-secondary)' }}>{safe(r.email)}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{safe(r.phone)}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{safe(r.company_name)}</span>
                    <span style={{
                      fontSize: 11, fontWeight: 700, padding: '4px 8px', borderRadius: 999,
                      background: m === 'Exact' ? 'rgba(22,163,74,0.14)' : 'rgba(180,83,9,0.14)',
                      color: m === 'Exact' ? '#2f8f53' : '#b07843',
                      width: 'fit-content',
                    }}>
                      {m}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14, background: 'var(--panel-bg)' }}>
        {selected ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ width: 74, height: 74, borderRadius: 12, background: 'var(--text-primary)', color: 'var(--text-inverse)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 28 }}>
                {initials(selected.recruiter_name)}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => fireSoon('Edit')} style={{ width: 36, height: 36, border: '1px solid var(--card-border)', background: 'var(--bg-hover)' }}><i className="ti ti-pencil" /></button>
                <button onClick={() => setSelectedId(null)} style={{ width: 36, height: 36, border: '1px solid var(--card-border)', background: 'var(--bg-hover)' }}><i className="ti ti-x" /></button>
              </div>
            </div>

            <div>
              <h2 style={{ fontSize: 42?0:16, marginBottom: 4, color: 'var(--text-primary)' }}>{safe(selected.recruiter_name)}</h2>
              <p style={{ color: 'var(--accent)', fontWeight: 600 }}>{safe(selected.specialization)}</p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', border: '1px solid var(--card-border)', borderRadius: 8, padding: 10 }}>
              <span style={{ fontSize: 12, fontWeight: 700, padding: '6px 8px', borderRadius: 6, background: matchTypeFor(selected, query) === 'Exact' ? 'rgba(22,163,74,0.14)' : 'rgba(180,83,9,0.14)', color: matchTypeFor(selected, query) === 'Exact' ? '#2f8f53' : '#b07843' }}>
                {matchTypeFor(selected, query).toUpperCase()} MATCH
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Accuracy: Not available</span>
            </div>

            <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: 12 }}>
              <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 10 }}>Contact Intelligence</h3>
              <div style={{ display: 'grid', gap: 9 }}>
                <div><strong style={{ fontSize: 11 }}>Primary Email</strong><div>{safe(selected.email)}</div></div>
                <div><strong style={{ fontSize: 11 }}>Primary Phone</strong><div>{safe(selected.phone)}</div></div>
                <div><strong style={{ fontSize: 11 }}>LinkedIn</strong><div>{safe(selected.linkedin)}</div></div>
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: 12 }}>
              <h3 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 10 }}>Firm Analysis</h3>
              <div style={{ border: '1px solid var(--card-border)', borderRadius: 8, padding: 10, background: 'var(--bg-hover)' }}>
                <div><strong>Company/Firm:</strong> {safe(selected.company_name)}</div>
                <div><strong>Location:</strong> {safe(selected.location)}</div>
                <div style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 12 }}>Engagement score: Not available (coming soon)</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Response time: Not available (coming soon)</div>
              </div>
            </div>

            <div style={{ marginTop: 'auto', display: 'grid', gridTemplateColumns: '1fr 42px 42px', gap: 8 }}>
              <button onClick={() => fireSoon('Share Profile')} style={{ border: '1px solid var(--card-border)', background: '#1c2aee', color: '#fff', fontWeight: 700, borderRadius: 10 }}>Share Profile</button>
              <button onClick={() => fireSoon('Copy')} style={{ border: '1px solid var(--card-border)', background: 'var(--bg-hover)' }}><i className="ti ti-copy" /></button>
              <button onClick={() => fireSoon('Link')} style={{ border: '1px solid var(--card-border)', background: 'var(--bg-hover)' }}><i className="ti ti-link" /></button>
            </div>
          </>
        ) : (
          <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)' }}>
            <i className="ti ti-user-search" style={{ fontSize: 28, display: 'block', marginBottom: 8 }} />
            <p>No recruiter selected</p>
            <p style={{ fontSize: 12 }}>Select a recruiter from search results to view details.</p>
          </div>
        )}
      </div>

      {toast && (
        <div style={{ position: 'fixed', right: 20, bottom: 20, background: 'var(--text-primary)', color: 'var(--text-inverse)', padding: '10px 12px', borderRadius: 8, fontSize: 12, zIndex: 1500 }}>
          {toast}
        </div>
      )}
    </div>
  )
}
