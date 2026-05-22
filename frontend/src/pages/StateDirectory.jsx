import { useState, useEffect } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const STATES = [
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

export default function StateDirectory() {
  const [selectedState, setSelectedState] = useState(null)
  const [companyQuery, setCompanyQuery] = useState('')
  const [debouncedCompany, setDebouncedCompany] = useState('')
  const [recruiters, setRecruiters] = useState([])
  const [loading, setLoading] = useState(false)
  const [totalCount, setTotalCount] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedCompany(companyQuery), 350)
    return () => clearTimeout(t)
  }, [companyQuery])

  useEffect(() => {
    if (!selectedState && !debouncedCompany) {
      setRecruiters([])
      setTotalCount(0)
      return
    }
    setLoading(true)
    let url = `${API}/recruiters/?limit=200&skip=0`
    if (selectedState) url += `&state=${selectedState}`
    if (debouncedCompany) url += `&company=${encodeURIComponent(debouncedCompany)}`

    axios.get(url)
      .then(res => {
        setRecruiters(res.data)
        const count = parseInt(res.headers['x-total-count'] || res.data.length, 10)
        setTotalCount(count)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [selectedState, debouncedCompany])

  const handleLoadMore = () => {
    if (loadingMore) return
    setLoadingMore(true)
    let url = `${API}/recruiters/?limit=200&skip=${recruiters.length}`
    if (selectedState) url += `&state=${selectedState}`
    if (debouncedCompany) url += `&company=${encodeURIComponent(debouncedCompany)}`

    axios.get(url)
      .then(res => {
        setRecruiters(prev => [...prev, ...res.data])
        const count = parseInt(res.headers['x-total-count'] || totalCount, 10)
        setTotalCount(count)
        setLoadingMore(false)
      })
      .catch(() => setLoadingMore(false))
  }

  const selectedName = STATES.find(s => s.abbr === selectedState)?.name || ''

  return (
    <div className="page-enter" style={{ display: 'flex', gap: 28, minHeight: 'calc(100vh - 120px)' }}>
      {/* Left: Selector + Map grid */}
      <div style={{ flex: '0 0 420px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>
            State Directory
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Select a state to browse recruiters by location. Combine with a company name to narrow down.
          </p>
        </div>

        {/* Company Filter */}
        <div style={{
          background: 'var(--card-bg)', border: '1px solid var(--card-border)',
          borderRadius: 10, padding: '0 14px', display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <i className="ti ti-building" style={{ fontSize: 17, color: 'var(--text-muted)' }} />
          <input
            value={companyQuery}
            onChange={e => setCompanyQuery(e.target.value)}
            placeholder="Filter by company name..."
            style={{
              flex: 1, border: 'none', background: 'transparent', outline: 'none',
              fontSize: 14, color: 'var(--text-primary)', padding: '12px 0',
            }}
          />
          {companyQuery && (
            <button onClick={() => setCompanyQuery('')}
              style={{ background: 'none', border: 'none', padding: 4, cursor: 'pointer', color: 'var(--text-muted)', fontSize: 16, lineHeight: 1 }}>
              <i className="ti ti-x" />
            </button>
          )}
        </div>

        {/* State Grid */}
        <div className="card" style={{ padding: 16, flex: 1 }}>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>
            Select a State
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: 6,
          }}>
            {STATES.map(({ abbr, name }) => {
              const isSelected = selectedState === abbr
              return (
                <button
                  key={abbr}
                  title={name}
                  onClick={() => setSelectedState(isSelected ? null : abbr)}
                  style={{
                    padding: '8px 4px',
                    borderRadius: 7,
                    fontSize: 12,
                    fontWeight: isSelected ? 600 : 400,
                    border: isSelected ? '2px solid var(--accent)' : '1px solid var(--card-border)',
                    background: isSelected ? 'var(--accent)' : 'var(--main-bg)',
                    color: isSelected ? '#fff' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    letterSpacing: '0.02em',
                  }}
                  onMouseEnter={e => { if (!isSelected) { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)' } }}
                  onMouseLeave={e => { if (!isSelected) { e.currentTarget.style.borderColor = 'var(--card-border)'; e.currentTarget.style.color = 'var(--text-secondary)' } }}
                >
                  {abbr}
                </button>
              )
            })}
          </div>

          {selectedState && (
            <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                Selected: <strong style={{ color: 'var(--accent)' }}>{selectedName}</strong>
              </span>
              <button onClick={() => setSelectedState(null)}
                style={{ fontSize: 11, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                Clear
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Right: Results */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Header */}
          <div style={{
            padding: '14px 20px', borderBottom: '1px solid var(--card-border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
          }}>
            <div>
              <h2 style={{ margin: 0, fontSize: 15, fontWeight: 500, color: 'var(--text-primary)' }}>
                {selectedState ? `${selectedName} Recruiters` : 'Directory Results'}
              </h2>
              {(selectedState || debouncedCompany) && !loading && (
                <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>
                  {totalCount.toLocaleString()} recruiter{totalCount !== 1 ? 's' : ''} found
                  {debouncedCompany ? ` at "${debouncedCompany}"` : ''}
                </p>
              )}
            </div>
            {selectedState && (
              <span style={{
                fontSize: 13, fontWeight: 600, color: 'var(--accent)',
                background: 'rgba(24,95,165,0.08)', padding: '4px 10px',
                borderRadius: 6, border: '1px solid rgba(24,95,165,0.2)',
              }}>
                {selectedState}
              </span>
            )}
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loading ? (
              <div style={{ padding: 48, textAlign: 'center' }}>
                <i className="ti ti-loader" style={{ fontSize: 28, color: 'var(--accent)', animation: 'spin 1s linear infinite' }} />
                <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>Fetching recruiters...</p>
              </div>
            ) : (!selectedState && !debouncedCompany) ? (
              <div style={{ padding: 64, textAlign: 'center', color: 'var(--text-muted)' }}>
                <i className="ti ti-map-pin" style={{ fontSize: 52, marginBottom: 16, opacity: 0.35, display: 'block' }} />
                <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 6 }}>No state selected</p>
                <p style={{ fontSize: 13 }}>Pick a state from the grid on the left to browse its recruiters.</p>
              </div>
            ) : recruiters.length === 0 ? (
              <div style={{ padding: 64, textAlign: 'center', color: 'var(--text-muted)' }}>
                <i className="ti ti-users-minus" style={{ fontSize: 52, marginBottom: 16, opacity: 0.35, display: 'block' }} />
                <p style={{ fontSize: 14, fontWeight: 500 }}>No recruiters found</p>
                <p style={{ fontSize: 13 }}>Try selecting a different state or clearing the company filter.</p>
              </div>
            ) : (
              <>
                {recruiters.map(r => (
                  <div key={r.recruiter_id} style={{
                    padding: '14px 20px', borderBottom: '1px solid var(--card-border)',
                    transition: 'background 0.15s', cursor: 'default',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--main-bg)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ margin: 0, fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{r.recruiter_name}</p>
                        <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-secondary)' }}>{r.company_name || 'Independent'}</p>
                      </div>
                      {r.location && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap', marginLeft: 12 }}>
                          <i className="ti ti-map-pin" style={{ marginRight: 3 }} />
                          {r.location}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 18px', marginTop: 8 }}>
                      <a href={`mailto:${r.email}`} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>
                        <i className="ti ti-mail" />
                        {r.email}
                      </a>
                      {r.phone && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'var(--text-muted)' }}>
                          <i className="ti ti-phone" />
                          {r.phone}
                        </span>
                      )}
                      {r.specialization && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'var(--text-muted)' }}>
                          <i className="ti ti-tag" />
                          {r.specialization}
                        </span>
                      )}
                    </div>
                  </div>
                ))}

                {recruiters.length < totalCount && (
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
                          Load More ({totalCount - recruiters.length} remaining)
                        </>
                      )}
                    </button>
                  </div>
                )}
              </>
            )}</div>
        </div>
      </div>
    </div>
  )
}
