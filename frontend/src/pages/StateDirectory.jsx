import React, { useState, useEffect, useMemo } from 'react'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import axios from 'axios'
const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const geoUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json"

const STATE_ABBR = {
  "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
  "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
  "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
  "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
  "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
  "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
  "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
  "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
  "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
  "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}

export default function StateDirectory() {
  const [selectedState, setSelectedState] = useState(null)
  const [companyQuery, setCompanyQuery] = useState('')
  const [recruiters, setRecruiters] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Debounce the company search
  const [debouncedCompany, setDebouncedCompany] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setDebouncedCompany(companyQuery), 300)
    return () => clearTimeout(t)
  }, [companyQuery])

  useEffect(() => {
    if (!selectedState && !debouncedCompany) {
      setRecruiters([])
      return
    }

    setLoading(true)
    setError(null)
    const abbr = STATE_ABBR[selectedState] || ''
    
    // We only need to filter by state if one is selected
    // Note: the backend looks for ILIKE '%TX%'. This matches "Austin, TX".
    let url = `${API}/recruiters/?limit=200`
    if (abbr) url += `&location=${abbr}`
    if (debouncedCompany) url += `&company=${debouncedCompany}`

    axios.get(url)
      .then(res => {
        setRecruiters(res.data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [selectedState, debouncedCompany])

  return (
    <div className="page-enter" style={{ display: 'flex', gap: 32, minHeight: 'calc(100vh - 64px)' }}>
      {/* Left side: Controls and Map */}
      <div style={{ flex: '1 1 50%', display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 8 }}>State Directory</h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>Select a state on the map to view recruiters located there. Filter further by company name.</p>
        </div>

        {/* Company Filter */}
        <div style={{
          background: 'var(--card-bg)', border: '1px solid var(--card-border)',
          borderRadius: 12, padding: '0 16px', display: 'flex', alignItems: 'center', gap: 10,
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        }}>
          <i className="ti ti-building" style={{ fontSize: 18, color: 'var(--text-muted)' }} />
          <input
            value={companyQuery}
            onChange={e => setCompanyQuery(e.target.value)}
            placeholder="Filter by company name..."
            style={{
              flex: 1, border: 'none', background: 'transparent', outline: 'none',
              fontSize: 15, color: 'var(--text-primary)', padding: '14px 0',
            }}
          />
        </div>

        {/* US Map */}
        <div className="card" style={{ padding: 16, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <ComposableMap projection="geoAlbersUsa" style={{ width: '100%', height: '100%' }}>
            <Geographies geography={geoUrl}>
              {({ geographies }) =>
                geographies.map(geo => {
                  const stateName = geo.properties.name
                  const isSelected = selectedState === stateName
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      onClick={() => setSelectedState(isSelected ? null : stateName)}
                      style={{
                        default: {
                          fill: isSelected ? 'var(--accent)' : 'var(--main-bg)',
                          stroke: isSelected ? 'var(--accent)' : 'var(--card-border)',
                          strokeWidth: 1,
                          outline: 'none',
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        },
                        hover: {
                          fill: isSelected ? 'var(--accent)' : 'rgba(24,95,165,0.2)',
                          stroke: 'var(--accent)',
                          strokeWidth: 1,
                          outline: 'none',
                          cursor: 'pointer',
                        },
                        pressed: {
                          fill: 'var(--accent)',
                          outline: 'none',
                        }
                      }}
                    />
                  )
                })
              }
            </Geographies>
          </ComposableMap>
        </div>
      </div>

      {/* Right side: Results */}
      <div style={{ flex: '1 1 50%', display: 'flex', flexDirection: 'column' }}>
        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--card-border)', background: 'var(--main-bg)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: 16, fontWeight: 500, margin: 0, color: 'var(--text-primary)' }}>
              {selectedState ? `${selectedState} Recruiters` : 'Select a State'}
            </h2>
            {selectedState && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--card-bg)', padding: '4px 8px', borderRadius: 6, border: '1px solid var(--card-border)' }}>
                {STATE_ABBR[selectedState]}
              </span>
            )}
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loading ? (
              <div style={{ padding: 40, textAlign: 'center' }}>
                <i className="ti ti-loader" style={{ fontSize: 24, color: 'var(--accent)', animation: 'spin 1s linear infinite' }} />
              </div>
            ) : error ? (
              <div style={{ padding: 40, textAlign: 'center', color: '#ef4444' }}>{error}</div>
            ) : (!selectedState && !debouncedCompany) ? (
              <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
                <i className="ti ti-map-2" style={{ fontSize: 48, marginBottom: 16, opacity: 0.5, display: 'block' }} />
                <p>Click on any state to view its directory.</p>
              </div>
            ) : recruiters.length === 0 ? (
              <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
                <i className="ti ti-users-minus" style={{ fontSize: 48, marginBottom: 16, opacity: 0.5, display: 'block' }} />
                <p>No recruiters found matching the selected criteria.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {recruiters.map(r => (
                  <div key={r.recruiter_id} style={{
                    padding: '16px 20px', borderBottom: '1px solid var(--card-border)',
                    display: 'flex', flexDirection: 'column', gap: 6,
                    transition: 'background 0.2s', cursor: 'default'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--main-bg)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 500, color: 'var(--text-primary)' }}>{r.recruiter_name}</h3>
                        <p style={{ margin: '2px 0 0', fontSize: 13, color: 'var(--text-secondary)' }}>{r.company_name || 'Independent'}</p>
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--main-bg)', padding: '2px 6px', borderRadius: 4, border: '1px solid var(--card-border)' }}>
                        {r.location || 'Unknown'}
                      </span>
                    </div>
                    
                    <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)' }}>
                        <i className="ti ti-mail" />
                        <a href={`mailto:${r.email}`} style={{ color: 'var(--accent)', textDecoration: 'none' }}>{r.email}</a>
                      </div>
                      {r.phone && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)' }}>
                          <i className="ti ti-phone" />
                          <span>{r.phone}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
