import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import * as XLSX from 'xlsx'
import api, { getErrorMessage, logAction } from '../services/api'

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

function initialsFromName(name = '') {
  const parts = String(name).trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function safeText(v, fallback = 'Not available') {
  const s = (v ?? '').toString().trim()
  return s ? s : fallback
}

function createWorkbook(rows) {
  const worksheet = XLSX.utils.json_to_sheet(rows)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Recruiters')
  return workbook
}

export default function StateDirectory() {
  const [selectedState, setSelectedState] = useState(null)
  const [stateQuery, setStateQuery] = useState('')

  const [companyQuery, setCompanyQuery] = useState('')
  const [debouncedCompanyQuery, setDebouncedCompanyQuery] = useState('')
  const [companies, setCompanies] = useState([])
  const [companiesTotal, setCompaniesTotal] = useState(0)
  const [companiesLoading, setCompaniesLoading] = useState(false)
  const [selectedCompany, setSelectedCompany] = useState(null)

  const [recruiterQuery, setRecruiterQuery] = useState('')
  const [debouncedRecruiterQuery, setDebouncedRecruiterQuery] = useState('')
  const [recruiters, setRecruiters] = useState([])
  const [recruitersLoading, setRecruitersLoading] = useState(false)
  const [recruitersTotal, setRecruitersTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(100)

  const [selectedRecruiters, setSelectedRecruiters] = useState(() => new Map())
  const [activeRecruiter, setActiveRecruiter] = useState(null)

  const [exporting, setExporting] = useState(null) // { current, total }
  const exportAbortRef = useRef(null)

  const [stateRecruiterCounts, setStateRecruiterCounts] = useState(() => new Map())
  const [stateCompanyCounts, setStateCompanyCounts] = useState(() => new Map())

  const [toast, setToast] = useState(null)
  const toastTimerRef = useRef(null)

  const [headerPortalElement, setHeaderPortalElement] = useState(null)

  const selectedStateName = useMemo(() => STATES.find(s => s.abbr === selectedState)?.name || '', [selectedState])
  const selectedCompanyName = selectedCompany?.company_name || ''

  const filteredStates = useMemo(() => {
    const q = stateQuery.trim().toLowerCase()
    if (!q) return STATES
    return STATES.filter(s => s.abbr.toLowerCase().includes(q) || s.name.toLowerCase().includes(q))
  }, [stateQuery])

  const totalPages = useMemo(() => {
    if (!recruitersTotal || !pageSize) return 1
    return Math.max(1, Math.ceil(recruitersTotal / pageSize))
  }, [recruitersTotal, pageSize])

  const exportFileNameBase = useMemo(() => {
    const cleanCompany = (selectedCompanyName || 'COMPANY').replace(/[^a-zA-Z0-9]/g, '_').toUpperCase()
    return `recruiters_${selectedState || 'STATE'}_${cleanCompany}`
  }, [selectedState, selectedCompanyName])

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    toastTimerRef.current = setTimeout(() => setToast(null), 2600)
  }

  useEffect(() => {
    setHeaderPortalElement(document.getElementById('header-actions'))
  }, [])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedCompanyQuery(companyQuery), 250)
    return () => clearTimeout(t)
  }, [companyQuery])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedRecruiterQuery(recruiterQuery), 200)
    return () => clearTimeout(t)
  }, [recruiterQuery])

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [rbState, cbState] = await Promise.all([
          api.get('/analytics/recruiters-by-state'),
          api.get('/analytics/companies-count-by-state'),
        ])
        if (!alive) return
        const recruiterCounts = new Map()
        for (const row of rbState.data || []) {
          recruiterCounts.set(String(row.state || '').toUpperCase(), Number(row.count || 0))
        }
        setStateRecruiterCounts(recruiterCounts)
        const companyCounts = new Map(Object.entries(cbState.data || {}).map(([k, v]) => [String(k || '').toUpperCase(), Number(v || 0)]))
        setStateCompanyCounts(companyCounts)
      } catch {
        // Optional enhancement only
      }
    })()
    return () => { alive = false }
  }, [])

  useEffect(() => {
    setSelectedCompany(null)
    setCompanies([])
    setCompaniesTotal(0)
    setCompanyQuery('')
    setDebouncedCompanyQuery('')
    setRecruiterQuery('')
    setDebouncedRecruiterQuery('')
    setRecruiters([])
    setRecruitersTotal(0)
    setPage(1)
    setSelectedRecruiters(new Map())
    setActiveRecruiter(null)
  }, [selectedState])

  useEffect(() => {
    if (selectedState) logAction('SEARCH_STATE', { state: selectedState, context: 'state_directory' })
  }, [selectedState])

  useEffect(() => {
    if (!selectedState) return

    let alive = true
    const controller = new AbortController()

    ;(async () => {
      try {
        setCompaniesLoading(true)
        const { data, headers } = await api.get('/analytics/companies-search', {
          params: {
            state: selectedState,
            q: debouncedCompanyQuery || undefined,
            limit: 200,
            skip: 0,
            min_recruiters: 1,
          },
          signal: controller.signal,
        })
        if (!alive) return
        setCompanies(Array.isArray(data) ? data : [])
        setCompaniesTotal(parseInt(headers?.['x-total-count'] || data?.length || 0, 10))
      } catch (err) {
        if (err?.name === 'CanceledError') return
        showToast(getErrorMessage(err, 'Failed to load companies'), 'error')
      } finally {
        if (alive) setCompaniesLoading(false)
      }
    })()

    return () => {
      alive = false
      controller.abort()
    }
  }, [selectedState, debouncedCompanyQuery])

  useEffect(() => {
    if (!selectedState || !selectedCompanyName) {
      setRecruiters([])
      setRecruitersTotal(0)
      return
    }

    let alive = true
    const controller = new AbortController()

    ;(async () => {
      try {
        setRecruitersLoading(true)
        const { data, headers } = await api.get('/recruiters', {
          params: {
            page,
            limit: pageSize,
            state: selectedState,
            company: selectedCompanyName,
            search: debouncedRecruiterQuery || undefined,
            sort_by: 'created_at',
            sort_desc: true,
          },
          signal: controller.signal,
        })
        if (!alive) return
        const results = Array.isArray(data) ? data : (data?.results || [])
        setRecruiters(results)
        const count = data?.total_count ?? parseInt(headers?.['x-total-count'] || results.length, 10)
        setRecruitersTotal(Number.isFinite(count) ? count : results.length)
      } catch (err) {
        if (err?.name === 'CanceledError') return
        showToast(getErrorMessage(err, 'Failed to load recruiters'), 'error')
      } finally {
        if (alive) setRecruitersLoading(false)
      }
    })()

    return () => {
      alive = false
      controller.abort()
    }
  }, [selectedState, selectedCompanyName, page, pageSize, debouncedRecruiterQuery])

  useEffect(() => {
    if (selectedState && selectedCompanyName) {
      logAction('SEARCH_COMPANY', { state: selectedState, company: selectedCompanyName, context: 'state_directory' })
    }
  }, [selectedState, selectedCompanyName])

  const selectedStateRecruiterCount = useMemo(() => {
    if (!selectedState) return null
    return stateRecruiterCounts.get(String(selectedState).toUpperCase()) ?? null
  }, [selectedState, stateRecruiterCounts])

  const selectedStateCompanyCount = useMemo(() => {
    if (!selectedState) return null
    return stateCompanyCounts.get(String(selectedState).toUpperCase()) ?? null
  }, [selectedState, stateCompanyCounts])

  const toggleRecruiterSelected = (r, checked) => {
    setSelectedRecruiters(prev => {
      const next = new Map(prev)
      if (checked) next.set(r.recruiter_id, r)
      else next.delete(r.recruiter_id)
      return next
    })
  }

  const selectAllOnPage = (checked) => {
    setSelectedRecruiters(prev => {
      const next = new Map(prev)
      for (const r of recruiters) {
        if (!r?.recruiter_id) continue
        if (checked) next.set(r.recruiter_id, r)
        else next.delete(r.recruiter_id)
      }
      return next
    })
  }

  const allOnPageSelected = useMemo(() => {
    if (!recruiters.length) return false
    return recruiters.every(r => selectedRecruiters.has(r.recruiter_id))
  }, [recruiters, selectedRecruiters])

  const exportSelected = () => {
    if (!selectedState || !selectedCompanyName) return showToast('Select a state and company first', 'error')
    if (selectedRecruiters.size === 0) return showToast('No recruiters selected', 'error')

    const rows = Array.from(selectedRecruiters.values()).map(r => ({
      Name: r.recruiter_name || '',
      Email: r.email || '',
      Phone: r.phone || '',
      Company: r.company_name || '',
      Location: r.location || '',
      State: r.state || selectedState || '',
    }))

    logAction('EXPORT_RECRUITERS', {
      state: selectedState,
      company: selectedCompanyName,
      mode: 'selected',
      count: rows.length,
    })
    XLSX.writeFile(createWorkbook(rows), `${exportFileNameBase}_SELECTED.xlsx`)
  }

  const exportCurrentPage = () => {
    if (!selectedState || !selectedCompanyName) return showToast('Select a state and company first', 'error')
    if (recruiters.length === 0) return showToast('No recruiters on this page', 'error')

    const rows = recruiters.map(r => ({
      Name: r.recruiter_name || '',
      Email: r.email || '',
      Phone: r.phone || '',
      Company: r.company_name || '',
      Location: r.location || '',
      State: r.state || selectedState || '',
    }))

    logAction('EXPORT_RECRUITERS', {
      state: selectedState,
      company: selectedCompanyName,
      mode: 'page',
      page,
      page_size: pageSize,
      count: rows.length,
    })
    XLSX.writeFile(createWorkbook(rows), `${exportFileNameBase}_PAGE_${page}.xlsx`)
  }

  const exportAllFiltered = async () => {
    if (!selectedState || !selectedCompanyName) return showToast('Select a state and company first', 'error')
    if (!recruitersTotal) return showToast('No recruiters to export', 'error')

    if (recruitersTotal > 50000) {
      const ok = window.confirm(`This will export ${recruitersTotal.toLocaleString()} recruiters and may take a while. Continue?`)
      if (!ok) return
    }

    if (exportAbortRef.current) exportAbortRef.current.abort()
    const controller = new AbortController()
    exportAbortRef.current = controller

    const batchSize = 500
    const totalBatches = Math.max(1, Math.ceil(recruitersTotal / batchSize))
    setExporting({ current: 0, total: totalBatches })

    try {
      const rows = []
      for (let idx = 0; idx < totalBatches; idx++) {
        const batchPage = idx + 1
        const { data } = await api.get('/recruiters', {
          params: {
            page: batchPage,
            limit: batchSize,
            state: selectedState,
            company: selectedCompanyName,
            search: debouncedRecruiterQuery || undefined,
            sort_by: 'created_at',
            sort_desc: true,
          },
          signal: controller.signal,
        })
        const results = Array.isArray(data) ? data : (data?.results || [])
        for (const r of results) {
          rows.push({
            Name: r.recruiter_name || '',
            Email: r.email || '',
            Phone: r.phone || '',
            Company: r.company_name || '',
            Location: r.location || '',
            State: r.state || selectedState || '',
          })
        }
        setExporting({ current: batchPage, total: totalBatches })
      }

      logAction('EXPORT_RECRUITERS', {
        state: selectedState,
        company: selectedCompanyName,
        mode: 'all_filtered',
        search: debouncedRecruiterQuery || null,
        count: rows.length,
      })
      XLSX.writeFile(createWorkbook(rows), `${exportFileNameBase}_ALL_FILTERED.xlsx`)
      showToast(`Exported ${rows.length.toLocaleString()} recruiters`, 'success')
    } catch (err) {
      if (err?.name === 'CanceledError') showToast('Export canceled', 'info')
      else showToast(getErrorMessage(err, 'Export failed'), 'error')
    } finally {
      setExporting(null)
      exportAbortRef.current = null
    }
  }

  return (
    <>
      {headerPortalElement && createPortal(
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={exportSelected}
            disabled={!selectedState || !selectedCompanyName || selectedRecruiters.size === 0 || exporting}
            title={selectedRecruiters.size === 0 ? 'Select recruiters to export' : 'Export selected recruiters'}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'var(--card-bg)', border: '1px solid var(--card-border)',
              padding: '6px 12px', borderRadius: 8, fontSize: 13,
              color: 'var(--text-primary)', cursor: 'pointer',
              height: 36, opacity: (!selectedState || !selectedCompanyName || selectedRecruiters.size === 0 || exporting) ? 0.55 : 1,
            }}
          >
            <i className="ti ti-checkbox" style={{ fontSize: 16 }} />
            <span style={{ fontWeight: 500 }}>Export Selected</span>
          </button>

          <button
            onClick={exportAllFiltered}
            disabled={!selectedState || !selectedCompanyName || exporting}
            title="Export all recruiters matching the current state/company/search filters"
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'var(--accent)', border: '1px solid rgba(0,0,0,0)',
              padding: '6px 12px', borderRadius: 8, fontSize: 13,
              color: '#031b16', cursor: 'pointer',
              height: 36, opacity: (!selectedState || !selectedCompanyName || exporting) ? 0.55 : 1,
              fontWeight: 650,
            }}
          >
            <i className="ti ti-download" style={{ fontSize: 16 }} />
            <span>Export All Filtered</span>
          </button>
        </div>,
        headerPortalElement
      )}

      <div className="page-enter" style={{ minHeight: 'calc(100vh - 120px)' }}>
        <div style={{ marginBottom: 14 }}>
          <h1 style={{ fontSize: 24, fontWeight: 650, letterSpacing: '-0.02em' }}>Territory Intelligence Center</h1>
          <p style={{ marginTop: 6, fontSize: 13, color: 'var(--text-muted)' }}>
            State → Company → Recruiters → Export Excel. Everything shown is real data from your database.
          </p>
        </div>

        {!selectedState ? (
          <div className="card" style={{ padding: 24, display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 18, alignItems: 'start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <div style={{ width: 40, height: 40, borderRadius: 12, background: 'rgba(45,212,191,0.14)', display: 'grid', placeItems: 'center', border: '1px solid rgba(45,212,191,0.22)' }}>
                  <i className="ti ti-compass" style={{ fontSize: 18, color: 'var(--accent)' }} />
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 650 }}>Start building export lists</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Designed for large recruiter datasets (10k+ / 50k+ / 100k+).</div>
                </div>
              </div>
              <div style={{ display: 'grid', gap: 10 }}>
                {[
                  { n: 1, t: 'Select State', d: 'Pick a state to scope your territory.' },
                  { n: 2, t: 'Select Company', d: 'See companies sorted by recruiter count.' },
                  { n: 3, t: 'Browse Recruiters', d: 'Use instant server-side search + pagination.' },
                  { n: 4, t: 'Export Excel', d: 'Export selected recruiters or all filtered results.' },
                ].map(step => (
                  <div key={step.n} style={{ display: 'flex', gap: 12, padding: 12, borderRadius: 12, border: '1px solid var(--card-border)', background: 'rgba(255,255,255,0.02)' }}>
                    <div style={{ width: 28, height: 28, borderRadius: 10, background: 'rgba(45,212,191,0.12)', border: '1px solid rgba(45,212,191,0.22)', color: 'var(--accent)', display: 'grid', placeItems: 'center', fontWeight: 750, fontSize: 12 }}>
                      {step.n}
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 650 }}>{step.t}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{step.d}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card" style={{ padding: 16, background: 'rgba(20,27,38,0.7)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                Select State
              </div>
              <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: '10px 12px' }}>
                <i className="ti ti-search" style={{ color: 'var(--text-muted)' }} />
                <input
                  value={stateQuery}
                  onChange={e => setStateQuery(e.target.value)}
                  placeholder="Search states..."
                  style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: 13 }}
                />
                {stateQuery && (
                  <button onClick={() => setStateQuery('')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                    <i className="ti ti-x" />
                  </button>
                )}
              </div>

              <div style={{ marginTop: 12, display: 'grid', gap: 8, maxHeight: 420, overflow: 'auto', paddingRight: 6 }}>
                {filteredStates.map(({ abbr, name }) => {
                  const rc = stateRecruiterCounts.get(abbr) ?? null
                  const cc = stateCompanyCounts.get(abbr) ?? null
                  return (
                    <button
                      key={abbr}
                      onClick={() => setSelectedState(abbr)}
                      style={{
                        textAlign: 'left',
                        padding: 12,
                        borderRadius: 12,
                        border: '1px solid var(--card-border)',
                        background: 'rgba(255,255,255,0.02)',
                        cursor: 'pointer',
                        transition: 'transform 0.12s ease, border-color 0.12s ease',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(45,212,191,0.35)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--card-border)'; e.currentTarget.style.transform = 'translateY(0px)' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ width: 36, height: 36, borderRadius: 12, background: 'rgba(45,212,191,0.10)', border: '1px solid rgba(45,212,191,0.18)', display: 'grid', placeItems: 'center', color: 'var(--accent)', fontWeight: 800 }}>
                            {abbr}
                          </div>
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 700 }}>{name}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                              {rc === null ? 'Recruiters: —' : `${rc.toLocaleString()} recruiters`} · {cc === null ? 'Companies: —' : `${cc.toLocaleString()} companies`}
                            </div>
                          </div>
                        </div>
                        <i className="ti ti-chevron-right" style={{ color: 'var(--text-muted)' }} />
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '340px 380px 1fr', gap: 16, alignItems: 'start' }}>
            {/* State column */}
            <div style={{ display: 'grid', gap: 12 }}>
              <div className="card" style={{ padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', gap: 10 }}>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                      1. Select State
                    </div>
                    <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 40, height: 40, borderRadius: 14, background: 'rgba(45,212,191,0.12)', border: '1px solid rgba(45,212,191,0.22)', display: 'grid', placeItems: 'center', fontWeight: 850, color: 'var(--accent)' }}>
                        {selectedState}
                      </div>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 750 }}>{selectedStateName || selectedState}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                          {selectedStateRecruiterCount === null ? 'Recruiters: —' : `${selectedStateRecruiterCount.toLocaleString()} recruiters`} · {selectedStateCompanyCount === null ? 'Companies: —' : `${selectedStateCompanyCount.toLocaleString()} companies`}
                        </div>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedState(null)}
                    style={{ background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 10, padding: '8px 10px', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12 }}
                  >
                    Clear
                  </button>
                </div>

                <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: '10px 12px' }}>
                  <i className="ti ti-search" style={{ color: 'var(--text-muted)' }} />
                  <input
                    value={stateQuery}
                    onChange={e => setStateQuery(e.target.value)}
                    placeholder="Search states..."
                    style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: 13 }}
                  />
                  {stateQuery && (
                    <button onClick={() => setStateQuery('')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                      <i className="ti ti-x" />
                    </button>
                  )}
                </div>
              </div>

              <div className="card" style={{ padding: 10, maxHeight: 'calc(100vh - 320px)', overflow: 'auto' }}>
                <div style={{ display: 'grid', gap: 8, padding: 6 }}>
                  {filteredStates.map(({ abbr, name }) => {
                    const isSelected = selectedState === abbr
                    const rc = stateRecruiterCounts.get(abbr) ?? null
                    return (
                      <button
                        key={abbr}
                        onClick={() => setSelectedState(abbr)}
                        style={{
                          textAlign: 'left',
                          padding: 10,
                          borderRadius: 12,
                          border: isSelected ? '1px solid rgba(45,212,191,0.42)' : '1px solid var(--card-border)',
                          background: isSelected ? 'rgba(45,212,191,0.08)' : 'rgba(255,255,255,0.02)',
                          cursor: 'pointer',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 750 }}>{name}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                              {abbr} · {rc === null ? 'Recruiters: —' : `${rc.toLocaleString()} recruiters`}
                            </div>
                          </div>
                          {isSelected ? <i className="ti ti-circle-check" style={{ color: 'var(--accent)' }} /> : <i className="ti ti-chevron-right" style={{ color: 'var(--text-muted)' }} />}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Company column */}
            <div style={{ display: 'grid', gap: 12 }}>
              <div className="card" style={{ padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                      2. Company
                    </div>
                    <div style={{ marginTop: 6, fontSize: 13, color: 'var(--text-secondary)' }}>
                      {companiesLoading ? 'Loading companies…' : `${companiesTotal.toLocaleString()} companies`}
                    </div>
                  </div>
                  <button disabled title="Coming soon" style={{ background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 10, padding: '8px 10px', cursor: 'not-allowed', color: 'var(--text-muted)', fontSize: 12, opacity: 0.6 }}>
                    Sort
                  </button>
                </div>

                <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: '10px 12px' }}>
                  <i className="ti ti-search" style={{ color: 'var(--text-muted)' }} />
                  <input
                    value={companyQuery}
                    onChange={e => setCompanyQuery(e.target.value)}
                    placeholder={`Search companies in ${selectedState}…`}
                    style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: 13 }}
                  />
                  {companyQuery && (
                    <button onClick={() => setCompanyQuery('')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                      <i className="ti ti-x" />
                    </button>
                  )}
                </div>
              </div>

              <div className="card" style={{ padding: 10, maxHeight: 'calc(100vh - 320px)', overflow: 'auto' }}>
                {companiesLoading ? (
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <i className="ti ti-loader" style={{ fontSize: 22, color: 'var(--accent)', animation: 'spin 1s linear infinite' }} />
                    <div style={{ marginTop: 10, fontSize: 12 }}>Fetching companies…</div>
                  </div>
                ) : companies.length === 0 ? (
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <i className="ti ti-building-skyscraper" style={{ fontSize: 28, opacity: 0.45 }} />
                    <div style={{ marginTop: 10, fontSize: 13, fontWeight: 650 }}>No companies found</div>
                    <div style={{ marginTop: 6, fontSize: 12 }}>Try a different search.</div>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gap: 8, padding: 6 }}>
                    {companies.map(c => {
                      const isSelected = (selectedCompany?.company_id && selectedCompany.company_id === c.company_id) || selectedCompanyName === c.company_name
                      return (
                        <button
                          key={c.company_id ?? c.company_name}
                          onClick={() => { setSelectedCompany(c); setPage(1); setSelectedRecruiters(new Map()); setActiveRecruiter(null) }}
                          style={{
                            textAlign: 'left',
                            padding: 12,
                            borderRadius: 14,
                            border: isSelected ? '1px solid rgba(45,212,191,0.42)' : '1px solid var(--card-border)',
                            background: isSelected ? 'rgba(45,212,191,0.08)' : 'rgba(255,255,255,0.02)',
                            cursor: 'pointer',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontSize: 13, fontWeight: 800, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.company_name || 'Unknown company'}</div>
                              <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-muted)' }}>
                                {Number.isFinite(c.recruiter_count) ? `${c.recruiter_count.toLocaleString()} recruiters` : 'Recruiters: —'}
                                {c.location ? ` · ${c.location}` : ''}
                              </div>
                            </div>
                            {isSelected ? <i className="ti ti-circle-check" style={{ color: 'var(--accent)' }} /> : <i className="ti ti-chevron-right" style={{ color: 'var(--text-muted)' }} />}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Recruiters column (primary) */}
            <div className="card" style={{ overflow: 'hidden', position: 'relative' }}>
              <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    3. Recruiters
                  </div>
                  <div style={{ marginTop: 6, display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
                    <div style={{ fontSize: 15, fontWeight: 850, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {selectedStateName || selectedState} · {selectedCompanyName || 'Select a company'}
                    </div>
                    {selectedCompanyName && (
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {recruitersLoading ? 'Loading…' : `${recruitersTotal.toLocaleString()} recruiters`}
                      </div>
                    )}
                  </div>
                </div>

                <button
                  onClick={exportCurrentPage}
                  disabled={!selectedCompanyName || recruiters.length === 0 || exporting}
                  title="Export the current page"
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--card-border)',
                    borderRadius: 10,
                    padding: '8px 10px',
                    cursor: (!selectedCompanyName || recruiters.length === 0 || exporting) ? 'not-allowed' : 'pointer',
                    color: 'var(--text-secondary)',
                    fontSize: 12,
                    opacity: (!selectedCompanyName || recruiters.length === 0 || exporting) ? 0.55 : 1,
                  }}
                >
                  Export Excel
                </button>
              </div>

              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: '10px 12px' }}>
                  <i className="ti ti-search" style={{ color: 'var(--text-muted)' }} />
                  <input
                    value={recruiterQuery}
                    onChange={e => { setRecruiterQuery(e.target.value); setPage(1) }}
                    placeholder="Search recruiters by name, email, company, or location…"
                    disabled={!selectedCompanyName}
                    style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent', fontSize: 13, opacity: !selectedCompanyName ? 0.7 : 1 }}
                  />
                  {recruiterQuery && (
                    <button onClick={() => { setRecruiterQuery(''); setPage(1) }} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                      <i className="ti ti-x" />
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Rows</div>
                  <select
                    value={pageSize}
                    onChange={e => { setPageSize(parseInt(e.target.value, 10)); setPage(1) }}
                    disabled={!selectedCompanyName}
                    style={{ height: 40, borderRadius: 10, padding: '0 10px', fontSize: 12 }}
                  >
                    {[50, 100, 200].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
              </div>

              <div style={{ overflow: 'auto', height: 'calc(100vh - 380px)' }}>
                {!selectedCompanyName ? (
                  <div style={{ padding: 46, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <i className="ti ti-click" style={{ fontSize: 34, opacity: 0.45 }} />
                    <div style={{ marginTop: 12, fontSize: 14, fontWeight: 650 }}>Select a company to view recruiters</div>
                    <div style={{ marginTop: 6, fontSize: 12 }}>Companies are sorted by recruiter count.</div>
                  </div>
                ) : recruitersLoading ? (
                  <div style={{ padding: 46, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <i className="ti ti-loader" style={{ fontSize: 24, color: 'var(--accent)', animation: 'spin 1s linear infinite' }} />
                    <div style={{ marginTop: 10, fontSize: 12 }}>Fetching recruiters…</div>
                  </div>
                ) : recruiters.length === 0 ? (
                  <div style={{ padding: 46, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <i className="ti ti-users-minus" style={{ fontSize: 34, opacity: 0.45 }} />
                    <div style={{ marginTop: 12, fontSize: 14, fontWeight: 650 }}>No recruiters found</div>
                    <div style={{ marginTop: 6, fontSize: 12 }}>Try clearing your search.</div>
                  </div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0, fontSize: 13 }}>
                    <thead style={{ position: 'sticky', top: 0, zIndex: 2, background: 'var(--card-bg)' }}>
                      <tr>
                        <th style={{ width: 44, padding: '12px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>
                          <input type="checkbox" checked={allOnPageSelected} onChange={e => selectAllOnPage(e.target.checked)} />
                        </th>
                        <th style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Name</th>
                        <th style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Email</th>
                        <th style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Company</th>
                        <th style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Location</th>
                        <th style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Phone</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recruiters.map(r => {
                        const isSelected = selectedRecruiters.has(r.recruiter_id)
                        return (
                          <tr
                            key={r.recruiter_id}
                            onClick={(e) => {
                              if (e.target?.tagName?.toLowerCase() === 'input') return
                              setActiveRecruiter(r)
                            }}
                            style={{ cursor: 'pointer', background: activeRecruiter?.recruiter_id === r.recruiter_id ? 'rgba(45,212,191,0.06)' : 'transparent' }}
                          >
                            <td style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)' }} onClick={(e) => e.stopPropagation()}>
                              <input type="checkbox" checked={isSelected} onChange={e => toggleRecruiterSelected(r, e.target.checked)} />
                            </td>
                            <td style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', fontWeight: 650 }}>
                              {safeText(r.recruiter_name, '')}
                            </td>
                            <td style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', color: 'var(--text-secondary)' }}>
                              {r.email ? (
                                <a href={`mailto:${r.email}`} onClick={(e) => e.stopPropagation()} style={{ color: 'var(--accent)' }}>
                                  {r.email}
                                </a>
                              ) : (
                                <span style={{ color: 'var(--text-muted)' }}>Not available</span>
                              )}
                            </td>
                            <td style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', color: 'var(--text-secondary)' }}>
                              {safeText(r.company_name, '')}
                            </td>
                            <td style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', color: 'var(--text-secondary)' }}>
                              {safeText(r.location, '')}
                            </td>
                            <td style={{ padding: '12px 12px', borderBottom: '1px solid var(--card-border)', color: 'var(--text-secondary)' }}>
                              {r.phone ? r.phone : <span style={{ color: 'var(--text-muted)' }}>Not available</span>}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                )}
              </div>

              <div style={{ padding: '12px 16px', borderTop: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {selectedCompanyName ? (
                    <>
                      Page <strong style={{ color: 'var(--text-primary)' }}>{page}</strong> of <strong style={{ color: 'var(--text-primary)' }}>{totalPages}</strong> · {recruitersTotal.toLocaleString()} total
                    </>
                  ) : (
                    'Select a company to paginate recruiters'
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={!selectedCompanyName || page <= 1 || recruitersLoading}
                    style={{ background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 10, padding: '8px 10px', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12, opacity: (!selectedCompanyName || page <= 1 || recruitersLoading) ? 0.55 : 1 }}
                  >
                    <i className="ti ti-chevron-left" /> Prev
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={!selectedCompanyName || page >= totalPages || recruitersLoading}
                    style={{ background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 10, padding: '8px 10px', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12, opacity: (!selectedCompanyName || page >= totalPages || recruitersLoading) ? 0.55 : 1 }}
                  >
                    Next <i className="ti ti-chevron-right" />
                  </button>
                </div>
              </div>

              {/* Export progress overlay */}
              {exporting && (
                <div style={{ position: 'absolute', inset: 0, background: 'rgba(10,13,18,0.72)', display: 'grid', placeItems: 'center', zIndex: 5 }}>
                  <div className="card" style={{ width: 420, padding: 18 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <i className="ti ti-download" style={{ color: 'var(--accent)', fontSize: 18 }} />
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 800 }}>Exporting All Filtered</div>
                          <div style={{ marginTop: 3, fontSize: 12, color: 'var(--text-muted)' }}>
                            Batch {exporting.current} of {exporting.total}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => exportAbortRef.current?.abort()}
                        style={{ background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 10, padding: '8px 10px', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12 }}
                      >
                        Cancel
                      </button>
                    </div>
                    <div style={{ marginTop: 12, height: 10, borderRadius: 999, background: 'rgba(255,255,255,0.06)', overflow: 'hidden', border: '1px solid var(--card-border)' }}>
                      <div style={{ width: `${Math.min(100, Math.round((exporting.current / exporting.total) * 100))}%`, height: '100%', background: 'rgba(45,212,191,0.85)' }} />
                    </div>
                  </div>
                </div>
              )}

              {/* Recruiter detail drawer */}
              <div style={{
                position: 'absolute',
                top: 0,
                right: 0,
                height: '100%',
                width: 380,
                transform: activeRecruiter ? 'translateX(0)' : 'translateX(390px)',
                transition: 'transform 0.18s ease',
                borderLeft: '1px solid var(--card-border)',
                background: 'rgba(15,19,26,0.92)',
                backdropFilter: 'blur(10px)',
                zIndex: 4,
                display: 'flex',
                flexDirection: 'column',
              }}>
                <div style={{ padding: 16, borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                    <div style={{ width: 42, height: 42, borderRadius: 14, background: 'rgba(45,212,191,0.12)', border: '1px solid rgba(45,212,191,0.22)', display: 'grid', placeItems: 'center', fontWeight: 850, color: 'var(--accent)' }}>
                      {initialsFromName(activeRecruiter?.recruiter_name || '')}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 850, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {activeRecruiter?.recruiter_name || 'Recruiter details'}
                      </div>
                      <div style={{ marginTop: 3, fontSize: 12, color: 'var(--text-muted)' }}>
                        {activeRecruiter?.company_name || '—'}
                      </div>
                    </div>
                  </div>
                  <button onClick={() => setActiveRecruiter(null)} style={{ background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 10, padding: '8px 10px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                    <i className="ti ti-x" />
                  </button>
                </div>

                {!activeRecruiter ? (
                  <div style={{ padding: 22, color: 'var(--text-muted)', textAlign: 'center', flex: 1, display: 'grid', placeItems: 'center' }}>
                    <div>
                      <i className="ti ti-id" style={{ fontSize: 34, opacity: 0.4 }} />
                      <div style={{ marginTop: 10, fontSize: 13, fontWeight: 650 }}>No recruiter selected</div>
                      <div style={{ marginTop: 6, fontSize: 12 }}>Click a recruiter row to view details.</div>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: 16, display: 'grid', gap: 12, overflow: 'auto' }}>
                    <div className="card" style={{ padding: 12, background: 'rgba(20,27,38,0.65)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Contact</div>
                      <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}><i className="ti ti-mail" style={{ marginRight: 6 }} />{safeText(activeRecruiter.email)}</div>
                          <button
                            disabled={!activeRecruiter.email}
                            onClick={async () => {
                              try { await navigator.clipboard.writeText(activeRecruiter.email); showToast('Email copied', 'success') } catch { showToast('Copy failed', 'error') }
                            }}
                            style={{ background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 10, padding: '6px 10px', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12, opacity: activeRecruiter.email ? 1 : 0.55 }}
                          >
                            Copy Email
                          </button>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}><i className="ti ti-phone" style={{ marginRight: 6 }} />{safeText(activeRecruiter.phone)}</div>
                          <button
                            disabled={!activeRecruiter.phone}
                            onClick={async () => {
                              try { await navigator.clipboard.writeText(activeRecruiter.phone); showToast('Phone copied', 'success') } catch { showToast('Copy failed', 'error') }
                            }}
                            style={{ background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 10, padding: '6px 10px', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 12, opacity: activeRecruiter.phone ? 1 : 0.55 }}
                          >
                            Copy Contact
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="card" style={{ padding: 12, background: 'rgba(20,27,38,0.65)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Profile</div>
                      <div style={{ marginTop: 10, display: 'grid', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
                        <div><strong style={{ color: 'var(--text-primary)' }}>Company:</strong> {safeText(activeRecruiter.company_name)}</div>
                        <div><strong style={{ color: 'var(--text-primary)' }}>Location:</strong> {safeText(activeRecruiter.location)}</div>
                        <div><strong style={{ color: 'var(--text-primary)' }}>State:</strong> {safeText(activeRecruiter.state || selectedState)}</div>
                      </div>
                    </div>

                    <div className="card" style={{ padding: 12, background: 'rgba(20,27,38,0.65)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Future</div>
                      <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                        {['LinkedIn', 'Notes', 'Tags'].map(t => (
                          <button key={t} disabled title="Coming soon" style={{ textAlign: 'left', background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 12, padding: 10, cursor: 'not-allowed', color: 'var(--text-muted)', opacity: 0.65 }}>
                            {t} <span style={{ float: 'right' }}>Coming soon</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {toast && (
          <div style={{ position: 'fixed', bottom: 18, right: 18, zIndex: 50 }}>
            <div className="card" style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
              <i
                className={toast.type === 'error' ? 'ti ti-alert-triangle' : toast.type === 'success' ? 'ti ti-circle-check' : 'ti ti-info-circle'}
                style={{ color: toast.type === 'error' ? '#fb7185' : toast.type === 'success' ? '#34d399' : 'var(--text-secondary)' }}
              />
              <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{toast.message}</div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
