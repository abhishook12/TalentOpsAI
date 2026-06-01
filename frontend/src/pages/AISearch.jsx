import { useEffect, useMemo, useState } from 'react'
import api, { logAction } from '../services/api'

function initials(name) {
  const parts = (name || '').trim().split(' ').filter(Boolean)
  if (!parts.length) return 'NA'
  return ((parts[0][0] || '') + (parts[1]?.[0] || '')).toUpperCase()
}

function matchTypeFor(rec, q) {
  const s = (q || '').trim().toLowerCase()
  if (!s) return 'Fuzzy'
  const name = (rec?.recruiter_name || '').toLowerCase()
  const email = (rec?.email || '').toLowerCase()
  const company = (rec?.company_name || '').toLowerCase()
  if (name === s || email === s || company === s) return 'Exact'
  if (name.startsWith(s) || email.startsWith(s) || company.startsWith(s)) return 'Exact'
  return 'Fuzzy'
}

function safe(v) {
  return v && String(v).trim() ? String(v).trim() : 'Not available'
}

function badgeForMatch(matchType) {
  const exact = matchType === 'Exact'
  return {
    label: exact ? 'EXACT' : 'FUZZY',
    bg: exact ? 'rgba(22, 163, 74, 0.14)' : 'rgba(245, 158, 11, 0.14)',
    fg: exact ? '#2f8f53' : '#b07843',
    border: exact ? 'rgba(22, 163, 74, 0.25)' : 'rgba(245, 158, 11, 0.28)',
  }
}

function iconButtonStyle(disabled = false) {
  return {
    width: 34,
    height: 34,
    borderRadius: 10,
    border: '1px solid var(--card-border)',
    background: 'var(--card-bg)',
    color: 'var(--text-secondary)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'all 0.15s ease',
  }
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

        const res = await api.get('/recruiters/search', { params })
        const sorted = [...(res.data || [])].sort((a, b) => {
          const ma = matchTypeFor(a, query) === 'Exact' ? 0 : 1
          const mb = matchTypeFor(b, query) === 'Exact' ? 0 : 1
          if (ma !== mb) return ma - mb
          return (b.relevance_score || 0) - (a.relevance_score || 0)
        })

        setResults(sorted)
        setSelectedId((prev) => (prev && sorted.some((x) => x.recruiter_id === prev) ? prev : null))

        logAction('SEARCH_RECRUITERS', {
          q: query.trim(),
          company: filterCompany.trim() || null,
          location: filterLocation.trim() || null,
          specialization: filterSpecialization.trim() || null,
          results: Array.isArray(sorted) ? sorted.length : 0,
          context: 'ai_search',
        })
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
    () => results.find((r) => r.recruiter_id === selectedId) || null,
    [results, selectedId]
  )

  const activeFiltersCount = useMemo(() => {
    let n = 0
    if (filterCompany.trim()) n += 1
    if (filterLocation.trim()) n += 1
    if (filterSpecialization.trim()) n += 1
    return n
  }, [filterCompany, filterLocation, filterSpecialization])

  const fireSoon = (label) => {
    setToast(`${label}: Coming soon`)
    console.log(`[Coming soon] ${label}`)
    setTimeout(() => setToast(''), 1400)
  }

  const clearAll = () => {
    setQuery('')
    setResults([])
    setSelectedId(null)
    setError('')
    setLoading(false)
    setFilterCompany('')
    setFilterLocation('')
    setFilterSpecialization('')
    setShowFilters(false)
  }

  const matchTypeForSelected = selected ? matchTypeFor(selected, query) : 'Fuzzy'
  const matchBadge = badgeForMatch(matchTypeForSelected)

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14, height: '100%' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 14,
          padding: '12px 14px',
          border: '1px solid var(--card-border)',
          borderRadius: 14,
          background: 'var(--panel-bg)',
          boxShadow: 'var(--shadow)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 12,
                background: 'var(--accent)',
                color: 'var(--text-inverse)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <i className="ti ti-sparkles" style={{ fontSize: 16 }} />
            </div>
            <div>
              <h1 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>Smart Search</h1>
              <p style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)' }}>
                Ranked recruiter search — exact matches first, fuzzy matches after. No demo data.
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={() => fireSoon('Share')} style={{ ...iconButtonStyle(false), width: 38 }} title="Share (Coming soon)">
            <i className="ti ti-share-2" />
          </button>
          <button onClick={() => fireSoon('Export')} style={{ ...iconButtonStyle(false), width: 38 }} title="Export (Coming soon)">
            <i className="ti ti-download" />
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.65fr 1fr', gap: 14, minHeight: 'calc(100vh - 210px)' }}>
        <div
          style={{
            border: '1px solid var(--card-border)',
            borderRadius: 14,
            background: 'var(--panel-bg)',
            boxShadow: 'var(--shadow)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              padding: 14,
              borderBottom: '1px solid var(--card-border)',
              background: 'linear-gradient(180deg, var(--panel-bg) 0%, rgba(0,0,0,0.00) 100%)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 12px',
                  borderRadius: 12,
                  border: '1px solid var(--card-border)',
                  background: 'var(--card-bg)',
                }}
              >
                <i className="ti ti-search" style={{ color: 'var(--text-muted)' }} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by name, email, company…"
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                  }}
                />
                {loading && (
                  <i className="ti ti-loader-2" style={{ color: 'var(--text-muted)', animation: 'spin 0.8s linear infinite' }} />
                )}
              </div>

              <button
                onClick={() => setShowFilters((v) => !v)}
                title="Filters"
                style={{ ...iconButtonStyle(false), width: 38, position: 'relative' }}
              >
                <i className="ti ti-adjustments-horizontal" />
                {activeFiltersCount > 0 && (
                  <span
                    style={{
                      position: 'absolute',
                      top: -6,
                      right: -6,
                      width: 18,
                      height: 18,
                      borderRadius: 999,
                      background: 'var(--accent)',
                      color: 'var(--text-inverse)',
                      fontSize: 10,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: '2px solid var(--panel-bg)',
                    }}
                  >
                    {activeFiltersCount}
                  </span>
                )}
              </button>

              <button onClick={clearAll} title="Clear" style={{ ...iconButtonStyle(false), width: 38 }}>
                <i className="ti ti-x" />
              </button>
            </div>

            {showFilters && (
              <div
                style={{
                  marginTop: 10,
                  padding: 12,
                  borderRadius: 14,
                  border: '1px solid var(--card-border)',
                  background: 'var(--card-bg)',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: 10,
                }}
              >
                {[
                  { label: 'Company', value: filterCompany, onChange: setFilterCompany, placeholder: 'e.g. Acme Staffing' },
                  { label: 'Location', value: filterLocation, onChange: setFilterLocation, placeholder: 'State (e.g. TX) or name' },
                  { label: 'Specialization', value: filterSpecialization, onChange: setFilterSpecialization, placeholder: 'e.g. Java / Data' },
                ].map((f) => (
                  <div key={f.label}>
                    <div
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        color: 'var(--text-muted)',
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        marginBottom: 6,
                      }}
                    >
                      {f.label}
                    </div>
                    <input
                      value={f.value}
                      onChange={(e) => f.onChange(e.target.value)}
                      placeholder={f.placeholder}
                      style={{
                        width: '100%',
                        padding: '9px 10px',
                        borderRadius: 12,
                        border: '1px solid var(--card-border)',
                        background: 'var(--panel-bg)',
                        color: 'var(--text-primary)',
                        fontSize: 12,
                        outline: 'none',
                      }}
                    />
                  </div>
                ))}

                <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                  <button
                    onClick={() => {
                      setFilterCompany('')
                      setFilterLocation('')
                      setFilterSpecialization('')
                    }}
                    style={{
                      padding: '9px 10px',
                      borderRadius: 12,
                      border: '1px solid var(--card-border)',
                      background: 'transparent',
                      color: 'var(--text-secondary)',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    Reset filters
                  </button>
                  <button
                    onClick={() => setShowFilters(false)}
                    style={{
                      padding: '9px 12px',
                      borderRadius: 12,
                      border: '1px solid var(--card-border)',
                      background: 'var(--accent)',
                      color: 'var(--text-inverse)',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>

          <div style={{ flex: 1, overflow: 'auto' }}>
            {!query.trim() && !loading && !error && (
              <div style={{ height: '100%', display: 'grid', placeItems: 'center', padding: 22, textAlign: 'center', color: 'var(--text-muted)' }}>
                <div>
                  <div
                    style={{
                      width: 52,
                      height: 52,
                      borderRadius: 16,
                      background: 'var(--card-bg)',
                      border: '1px solid var(--card-border)',
                      display: 'grid',
                      placeItems: 'center',
                      margin: '0 auto 10px',
                    }}
                  >
                    <i className="ti ti-search" style={{ fontSize: 18 }} />
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Search recruiters</div>
                  <div style={{ marginTop: 6, fontSize: 12 }}>Start typing a name, email, or company. Results come only from your database.</div>
                </div>
              </div>
            )}

            {!!error && (
              <div style={{ padding: 18, color: 'var(--text-muted)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <i className="ti ti-alert-triangle" style={{ color: 'var(--amber)', fontSize: 16 }} />
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Couldn’t load results</div>
                </div>
                <div style={{ marginTop: 6, fontSize: 12 }}>{error}</div>
                <div style={{ marginTop: 10, fontSize: 11 }}>
                  API: <span style={{ fontFamily: 'var(--mono)' }}>{API}</span>
                </div>
              </div>
            )}

            {query.trim() && !error && (
              <>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderBottom: '1px solid var(--card-border)',
                    background: 'var(--panel-bg)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 3,
                  }}
                >
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {loading ? 'Searching…' : `${results.length} result${results.length === 1 ? '' : 's'}`}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button onClick={() => fireSoon('Columns')} style={iconButtonStyle(false)} title="Columns (Coming soon)">
                      <i className="ti ti-columns-3" />
                    </button>
                    <button onClick={() => fireSoon('Sort')} style={iconButtonStyle(false)} title="Sort (Coming soon)">
                      <i className="ti ti-arrows-sort" />
                    </button>
                  </div>
                </div>

                {results.length === 0 && !loading ? (
                  <div style={{ padding: 20, color: 'var(--text-muted)' }}>
                    <div style={{ fontWeight: 800, color: 'var(--text-primary)' }}>No matches found</div>
                    <div style={{ marginTop: 6, fontSize: 12 }}>Try adjusting filters or refining the query.</div>
                  </div>
                ) : (
                  <div style={{ padding: 0 }}>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1.2fr 1.2fr 0.9fr 1.1fr 0.55fr',
                        gap: 10,
                        padding: '10px 14px',
                        borderBottom: '1px solid var(--card-border)',
                        background: 'var(--main-bg)',
                        position: 'sticky',
                        top: 44,
                        zIndex: 2,
                        fontSize: 10,
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        color: 'var(--text-muted)',
                        fontWeight: 800,
                      }}
                    >
                      <div>Name</div>
                      <div>Email</div>
                      <div>Phone</div>
                      <div>Company</div>
                      <div>Match Type</div>
                    </div>

                    <div>
                      {results.map((r) => {
                        const active = selectedId === r.recruiter_id
                        const mt = matchTypeFor(r, query)
                        const badge = badgeForMatch(mt)
                        return (
                          <button
                            key={r.recruiter_id}
                            onClick={() => setSelectedId(r.recruiter_id)}
                            style={{
                              width: '100%',
                              textAlign: 'left',
                              border: 'none',
                              borderBottom: '1px solid var(--card-border)',
                              background: active ? 'var(--accent-bg)' : 'transparent',
                              padding: 0,
                              cursor: 'pointer',
                            }}
                          >
                            <div
                              style={{
                                display: 'grid',
                                gridTemplateColumns: '1.2fr 1.2fr 0.9fr 1.1fr 0.55fr',
                                gap: 10,
                                padding: '12px 14px',
                                alignItems: 'center',
                                fontSize: 12,
                                color: 'var(--text-secondary)',
                              }}
                            >
                              <div style={{ color: 'var(--text-primary)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div
                                  style={{
                                    width: 28,
                                    height: 28,
                                    borderRadius: 10,
                                    border: '1px solid var(--card-border)',
                                    background: 'var(--card-bg)',
                                    display: 'grid',
                                    placeItems: 'center',
                                    fontSize: 11,
                                    fontWeight: 900,
                                    color: 'var(--text-primary)',
                                  }}
                                >
                                  {initials(r.recruiter_name)}
                                </div>
                                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.recruiter_name)}</span>
                              </div>
                              <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.email)}</div>
                              <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.phone)}</div>
                              <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.company_name)}</div>
                              <div>
                                <span
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    padding: '5px 8px',
                                    borderRadius: 999,
                                    border: `1px solid ${badge.border}`,
                                    background: badge.bg,
                                    color: badge.fg,
                                    fontSize: 10,
                                    fontWeight: 900,
                                    letterSpacing: '0.03em',
                                  }}
                                >
                                  {badge.label}
                                </span>
                              </div>
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <div
          style={{
            border: '1px solid var(--card-border)',
            borderRadius: 14,
            background: 'var(--panel-bg)',
            boxShadow: 'var(--shadow)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ padding: 14, borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-primary)' }}>Recruiter Details</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button onClick={() => (selected ? fireSoon('Copy profile') : null)} style={iconButtonStyle(!selected)} title="Copy (Coming soon)" disabled={!selected}>
                <i className="ti ti-copy" />
              </button>
              <button onClick={() => (selected ? fireSoon('Edit') : null)} style={iconButtonStyle(!selected)} title="Edit (Coming soon)" disabled={!selected}>
                <i className="ti ti-pencil" />
              </button>
              <button onClick={() => setSelectedId(null)} style={iconButtonStyle(!selected)} title="Close" disabled={!selected}>
                <i className="ti ti-x" />
              </button>
            </div>
          </div>

          {!selected ? (
            <div style={{ flex: 1, display: 'grid', placeItems: 'center', padding: 22, textAlign: 'center', color: 'var(--text-muted)' }}>
              <div>
                <div style={{ width: 56, height: 56, borderRadius: 18, border: '1px solid var(--card-border)', background: 'var(--card-bg)', display: 'grid', placeItems: 'center', margin: '0 auto 10px' }}>
                  <i className="ti ti-user-search" style={{ fontSize: 18 }} />
                </div>
                <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)' }}>No recruiter selected</div>
                <div style={{ marginTop: 6, fontSize: 12 }}>Click a row to open the detail panel.</div>
              </div>
            </div>
          ) : (
            <div style={{ flex: 1, overflow: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                  <div style={{ width: 52, height: 52, borderRadius: 16, background: 'var(--text-primary)', color: 'var(--text-inverse)', display: 'grid', placeItems: 'center', fontSize: 18, fontWeight: 900 }}>
                    {initials(selected.recruiter_name)}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 16, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {safe(selected.recruiter_name)}
                    </div>
                    <div style={{ marginTop: 3, fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {selected.specialization && String(selected.specialization).trim() ? String(selected.specialization).trim() : ''}
                    </div>
                  </div>
                </div>

                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '6px 10px', borderRadius: 999, border: `1px solid ${matchBadge.border}`, background: matchBadge.bg, color: matchBadge.fg, fontSize: 10, fontWeight: 900, letterSpacing: '0.03em', whiteSpace: 'nowrap' }}>
                  {matchBadge.label} MATCH
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <button onClick={() => fireSoon('Share profile')} style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--accent)', color: 'var(--text-inverse)', fontSize: 12, fontWeight: 800, cursor: 'pointer' }}>
                  <i className="ti ti-share-2" style={{ marginRight: 8 }} />
                  Share profile
                </button>
                <button onClick={() => fireSoon('Open timeline')} style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', fontSize: 12, fontWeight: 800, cursor: 'pointer' }}>
                  <i className="ti ti-activity" style={{ marginRight: 8 }} />
                  Activity (soon)
                </button>
              </div>

              <div style={{ border: '1px solid var(--card-border)', borderRadius: 14, padding: 12, background: 'var(--card-bg)' }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>Contact info</div>
                <div style={{ display: 'grid', gap: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Email</div>
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(selected.email)}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Phone</div>
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(selected.phone)}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>LinkedIn</div>
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(selected.linkedin)}</div>
                  </div>
                </div>
              </div>

              <div style={{ border: '1px solid var(--card-border)', borderRadius: 14, padding: 12, background: 'var(--card-bg)' }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>Company / firm analysis</div>

                <div style={{ display: 'grid', gap: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Company</div>
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 800, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(selected.company_name)}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Location</div>
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(selected.location)}</div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    {['Engagement score', 'Response time'].map((label) => (
                      <div key={label} style={{ border: '1px dashed var(--card-border)', borderRadius: 12, padding: 10, background: 'var(--panel-bg)' }}>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 800, letterSpacing: '0.04em', textTransform: 'uppercase' }}>{label}</div>
                        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>Not available (coming soon)</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {toast && (
        <div style={{ position: 'fixed', right: 18, bottom: 18, background: 'var(--text-primary)', color: 'var(--text-inverse)', padding: '10px 12px', borderRadius: 12, fontSize: 12, zIndex: 1500, boxShadow: 'var(--shadow-lg)' }}>
          {toast}
        </div>
      )}
    </div>
  )
}
