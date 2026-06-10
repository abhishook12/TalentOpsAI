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

const ENHANCED_STATES = [
  ...STATES,
  { abbr: 'Unknown', name: 'Unknown / Missing Data' }
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

function Panel({ title, icon, badge, children, style }) {
  return (
    <div className="card" style={{ padding: 14, borderRadius: 16, minHeight: 0, display: 'flex', flexDirection: 'column', gap: 10, ...style }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <i className={`ti ${icon}`} style={{ color: 'var(--accent)', fontSize: 16 }} />
          <div style={{ fontSize: 13, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</div>
        </div>
        {badge}
      </div>
      {children}
    </div>
  )
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

  const selectedStateName = useMemo(() => ENHANCED_STATES.find(s => s.abbr === selectedState)?.name || '', [selectedState])
  const selectedCompanyName = selectedCompany?.company_name || ''

  const filteredStates = useMemo(() => {
    const q = stateQuery.trim().toLowerCase()
    if (!q) return ENHANCED_STATES
    return ENHANCED_STATES.filter(s => s.abbr.toLowerCase().includes(q) || s.name.toLowerCase().includes(q))
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
    return stateRecruiterCounts.get(String(selectedState).toUpperCase()) ?? 0
  }, [selectedState, stateRecruiterCounts])

  const selectedStateCompanyCount = useMemo(() => {
    if (!selectedState) return null
    return stateCompanyCounts.get(String(selectedState).toUpperCase()) ?? 0
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

  const drawerOpen = Boolean(activeRecruiter)

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
              padding: '6px 12px', borderRadius: 10, fontSize: 13,
              color: 'var(--text-primary)', cursor: 'pointer',
              height: 36, opacity: (!selectedState || !selectedCompanyName || selectedRecruiters.size === 0 || exporting) ? 0.55 : 1,
              fontWeight: 900,
            }}
          >
            <i className="ti ti-checkbox" style={{ fontSize: 16 }} />
            <span>Export Selected</span>
          </button>

          <button
            onClick={exportAllFiltered}
            disabled={!selectedState || !selectedCompanyName || exporting}
            title="Export all recruiters matching the current state/company/search filters"
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'var(--accent)', border: '1px solid rgba(0,0,0,0)',
              padding: '6px 12px', borderRadius: 10, fontSize: 13,
              color: 'var(--text-inverse)', cursor: 'pointer',
              height: 36, opacity: (!selectedState || !selectedCompanyName || exporting) ? 0.55 : 1,
              fontWeight: 900,
            }}
          >
            <i className="ti ti-download" style={{ fontSize: 16 }} />
            <span>Export All Filtered</span>
          </button>
        </div>,
        headerPortalElement
      )}

      <div className="page-enter" style={{ minHeight: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ marginBottom: 2 }}>
          <h1 style={{ fontSize: 22, fontWeight: 950, letterSpacing: '-0.02em', margin: 0 }}>Territory Analytics</h1>
          <p style={{ marginTop: 6, fontSize: 13, color: 'var(--text-muted)' }}>
            State → Company → Recruiters → Export Excel. Everything shown is real data from your database.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: drawerOpen ? '340px 380px 1fr 360px' : '340px 380px 1fr',
          gap: 12,
          minHeight: 0,
          alignItems: 'start',
        }}>
          <Panel
            title="1. Select State"
            icon="ti-map-pin"
            badge={<span className="badge badge-gray">{filteredStates.length}</span>}
            style={{ minHeight: 0 }}
          >
            <input
              value={stateQuery}
              onChange={(e) => setStateQuery(e.target.value)}
              placeholder="Search states…"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none' }}
            />
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto', maxHeight: 'calc(100vh - 260px)' }}>
              {filteredStates.map((s) => {
                const recruitersCount = stateRecruiterCounts.get(s.abbr) ?? 0
                const companiesCount = stateCompanyCounts.get(s.abbr) ?? 0
                const selected = selectedState === s.abbr
                return (
                  <button
                    key={s.abbr}
                    onClick={() => setSelectedState(s.abbr)}
                    style={{
                      textAlign: 'left',
                      borderRadius: 14,
                      border: `1px solid ${selected ? 'rgba(24,95,165,0.35)' : 'var(--card-border)'}`,
                      background: selected ? 'rgba(24,95,165,0.08)' : 'var(--panel-bg)',
                      padding: 12,
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 10,
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 950, color: 'var(--text-primary)' }}>{s.name}</div>
                      <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-muted)' }}>
                        {`${Number(recruitersCount || 0).toLocaleString()} recruiters`}
                        {'  •  '}
                        {`${Number(companiesCount || 0).toLocaleString()} companies`}
                      </div>
                    </div>
                    <div style={{ width: 28, height: 28, borderRadius: 10, border: `1px solid ${selected ? 'rgba(24,95,165,0.35)' : 'var(--card-border)'}`, background: selected ? 'rgba(24,95,165,0.12)' : 'transparent', display: 'grid', placeItems: 'center' }}>
                      {selected ? <i className="ti ti-check" style={{ color: 'var(--accent)' }} /> : <span style={{ fontFamily: 'var(--mono)', fontWeight: 900, color: 'var(--text-muted)' }}>{s.abbr}</span>}
                    </div>
                  </button>
                )
              })}
            </div>
          </Panel>

            <Panel
              title="2. Company"
              icon="ti-building"
              badge={<span className="badge badge-gray">{companiesLoading ? '…' : companies.length}</span>}
              style={{ minHeight: 0 }}
            >
              {!selectedState ? (
                <div style={{ padding: 14, color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.55 }}>
                  <div style={{ fontSize: 13, fontWeight: 950, color: 'var(--text-primary)' }}>Start by selecting a state</div>
                  <div style={{ marginTop: 6 }}>
                    1) Select State → 2) Select Company → 3) Browse Recruiters → 4) Export Excel
                  </div>
                </div>
              ) : null}
              {selectedState === 'Unknown' && (
                <div style={{ padding: '12px 14px', borderRadius: 12, background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: 'var(--text-primary)', fontSize: 12, lineHeight: 1.5, marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 800, color: '#ef4444', marginBottom: 4 }}>
                    <i className="ti ti-alert-triangle" /> Missing Metadata
                  </div>
                  Records in this bucket have absolutely no state, location, or company metadata, so they cannot be placed into a state yet.
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'baseline' }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  <span style={{ fontWeight: 950, color: 'var(--text-primary)' }}>{selectedStateName || selectedState}</span>
                  <span> • {Number(selectedStateCompanyCount || 0).toLocaleString()} companies</span>
                </div>
                <button
                  onClick={() => { setSelectedCompany(null); setPage(1); setRecruiterQuery(''); setSelectedRecruiters(new Map()); setActiveRecruiter(null) }}
                  disabled={!selectedCompany}
                  style={{ background: 'transparent', border: 'none', color: selectedCompany ? 'var(--text-secondary)' : 'var(--text-muted)', cursor: selectedCompany ? 'pointer' : 'not-allowed', fontWeight: 900, fontSize: 12, opacity: selectedCompany ? 1 : 0.6 }}
                  title={selectedCompany ? 'Clear selection' : 'Select a company'}
                >
                  Clear
                </button>
              </div>

              <input
                value={companyQuery}
                onChange={(e) => setCompanyQuery(e.target.value)}
                placeholder={`Search companies in ${selectedState}…`}
                disabled={!selectedState}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none', marginTop: 10 }}
              />

              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto', maxHeight: 'calc(100vh - 310px)' }}>
                {companiesLoading ? (
                  <div style={{ padding: 14, color: 'var(--text-muted)', fontSize: 12 }}>Loading companies…</div>
                ) : companies.length === 0 ? (
                  <div style={{ padding: 14, color: 'var(--text-muted)', fontSize: 12 }}>
                    No Data Available. This state has no companies with linked recruiters yet.
                  </div>
                ) : (
                  [...companies]
                    .sort((a, b) => Number(b.recruiter_count || 0) - Number(a.recruiter_count || 0))
                    .map((c) => {
                      const selected = selectedCompany?.company_id === c.company_id
                      return (
                        <button
                          key={c.company_id}
                          onClick={() => {
                            setSelectedCompany(c)
                            setRecruitersTotal(Number(c.recruiter_count || 0))
                            setPage(1)
                            setSelectedRecruiters(new Map())
                            setActiveRecruiter(null)
                          }}
                          style={{
                            textAlign: 'left',
                            borderRadius: 14,
                            border: `1px solid ${selected ? 'rgba(24,95,165,0.35)' : 'var(--card-border)'}`,
                            background: selected ? 'rgba(24,95,165,0.08)' : 'var(--panel-bg)',
                            padding: 12,
                            cursor: 'pointer',
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: 10,
                            alignItems: 'center',
                          }}
                        >
                          <div style={{ minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                              <div style={{ width: 32, height: 32, borderRadius: 12, background: 'var(--bg-hover)', border: '1px solid var(--card-border)', display: 'grid', placeItems: 'center', fontWeight: 950, fontFamily: 'var(--mono)', color: 'var(--text-secondary)', flexShrink: 0 }}>
                                {(c.company_name || 'C').slice(0, 2).toUpperCase()}
                              </div>
                              <div style={{ minWidth: 0 }}>
                                <div style={{ fontSize: 13, fontWeight: 950, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.company_name || 'Unnamed company'}</div>
                                <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.location || 'Not available'}</div>
                              </div>
                            </div>
                          </div>
                          <div style={{ fontFamily: 'var(--mono)', fontWeight: 950, color: 'var(--text-secondary)' }}>
                            {(Number(c.recruiter_count || 0)).toLocaleString()}
                          </div>
                        </button>
                      )
                    })
                )}
              </div>
            </Panel>

            <Panel
              title="3. Recruiters"
              icon="ti-users"
              badge={<span className="badge badge-gray">{selectedCompanyName ? Number(recruitersTotal || 0).toLocaleString() : '0'}</span>}
              style={{ minHeight: 0 }}
            >
              {!selectedState ? (
                <div style={{ padding: 14, color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.55 }}>
                  Select a state to see companies and recruiters.
                </div>
              ) : null}
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'baseline' }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  <span style={{ fontWeight: 950, color: 'var(--text-primary)' }}>{selectedStateName || selectedState}</span>
                  {selectedCompanyName && <span> • <span style={{ fontWeight: 950, color: 'var(--text-primary)' }}>{selectedCompanyName}</span></span>}
                  {selectedCompanyName && <span> • {recruitersTotal.toLocaleString()} recruiters</span>}
                </div>
                <button
                  onClick={exportCurrentPage}
                  disabled={!selectedCompanyName || recruiters.length === 0 || exporting}
                  title={!selectedCompanyName ? 'Select a company first' : 'Export current page to Excel'}
                  style={{
                    background: 'var(--bg-hover)',
                    border: '1px solid var(--card-border)',
                    color: (!selectedCompanyName || recruiters.length === 0 || exporting) ? 'var(--text-muted)' : 'var(--text-secondary)',
                    padding: '8px 10px',
                    borderRadius: 12,
                    cursor: (!selectedCompanyName || recruiters.length === 0 || exporting) ? 'not-allowed' : 'pointer',
                    fontWeight: 950,
                    fontSize: 12,
                    opacity: (!selectedCompanyName || recruiters.length === 0 || exporting) ? 0.7 : 1,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <i className="ti ti-file-spreadsheet" /> Export Page
                </button>
              </div>

              <input
                value={recruiterQuery}
                onChange={(e) => { setRecruiterQuery(e.target.value); setPage(1) }}
                placeholder={selectedCompanyName ? 'Search recruiters by name, email, company, location…' : 'Select a company to browse recruiters…'}
                disabled={!selectedCompanyName}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none', marginTop: 10, opacity: selectedCompanyName ? 1 : 0.7 }}
              />

              <div style={{ marginTop: 10, minHeight: 0, flex: 1, overflow: 'hidden', borderRadius: 14, border: '1px solid var(--card-border)', background: 'var(--panel-bg)' }}>
                {!selectedCompanyName ? (
                  <div style={{ padding: 18, color: 'var(--text-muted)', fontSize: 12 }}>Select a company to view recruiters.</div>
                ) : recruitersLoading ? (
                  <div style={{ padding: 18, color: 'var(--text-muted)', fontSize: 12 }}>Loading recruiters…</div>
                ) : recruiters.length === 0 ? (
                  <div style={{ padding: 18, color: 'var(--text-muted)', fontSize: 12 }}>No Data Available for this filter.</div>
                ) : (
                  <div style={{ overflow: 'auto', maxHeight: 'calc(100vh - 360px)' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
                      <thead>
                        <tr style={{ background: 'var(--bg-hover)' }}>
                          <th style={{ width: 36, padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>
                            <input
                              type="checkbox"
                              checked={allOnPageSelected}
                              onChange={(e) => selectAllOnPage(e.target.checked)}
                              aria-label="Select all on page"
                            />
                          </th>
                          <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Name</th>
                          <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Email</th>
                          <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Company</th>
                          <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Location</th>
                          <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Phone</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recruiters.map((r) => (
                          <tr
                            key={r.recruiter_id}
                            style={{ borderBottom: '1px solid var(--card-border)', cursor: 'pointer' }}
                            onClick={() => setActiveRecruiter(r)}
                          >
                            <td style={{ padding: '10px 12px' }} onClick={(e) => e.stopPropagation()}>
                              <input
                                type="checkbox"
                                checked={selectedRecruiters.has(r.recruiter_id)}
                                onChange={(e) => toggleRecruiterSelected(r, e.target.checked)}
                                aria-label={`Select ${r.recruiter_name || 'recruiter'}`}
                              />
                            </td>
                            <td style={{ padding: '10px 12px', color: 'var(--text-primary)', fontWeight: 900 }}>
                              {safeText(r.recruiter_name, '')}
                            </td>
                            <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                              {r.email || ''}
                            </td>
                            <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                              {r.company_name || selectedCompanyName || ''}
                            </td>
                            <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                              {r.location || r.state || ''}
                            </td>
                            <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                              {r.phone || ''}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {selectedCompanyName && (
                <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
                    Page {page} / {totalPages} • {pageSize} per page
                    {exporting && <span style={{ marginLeft: 10 }}>Exporting… {exporting.current}/{exporting.total}</span>}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <select
                      value={pageSize}
                      onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
                      style={{ padding: '8px 10px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)' }}
                    >
                      {[50, 100, 200].map((n) => <option key={n} value={n}>{n}/page</option>)}
                    </select>
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page <= 1}
                      style={{ padding: '8px 10px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: page <= 1 ? 'var(--text-muted)' : 'var(--text-secondary)', cursor: page <= 1 ? 'not-allowed' : 'pointer' }}
                    >
                      <i className="ti ti-chevron-left" />
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                      style={{ padding: '8px 10px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: page >= totalPages ? 'var(--text-muted)' : 'var(--text-secondary)', cursor: page >= totalPages ? 'not-allowed' : 'pointer' }}
                    >
                      <i className="ti ti-chevron-right" />
                    </button>
                  </div>
                </div>
              )}
            </Panel>

            {drawerOpen && (
              <div className="card" style={{ padding: 14, borderRadius: 16, minHeight: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', minWidth: 0 }}>
                    <div style={{ width: 42, height: 42, borderRadius: 14, background: 'var(--bg-hover)', border: '1px solid var(--card-border)', display: 'grid', placeItems: 'center', fontWeight: 950, fontFamily: 'var(--mono)', color: 'var(--text-secondary)' }}>
                      {initialsFromName(activeRecruiter?.recruiter_name || '')}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 950, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {safeText(activeRecruiter?.recruiter_name, '') || 'Recruiter'}
                      </div>
                      <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {activeRecruiter?.company_name || selectedCompanyName || 'Independent / Unlisted'}
                      </div>
                    </div>
                  </div>
                  <button onClick={() => setActiveRecruiter(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }} title="Close">
                    <i className="ti ti-x" />
                  </button>
                </div>

                <div style={{ display: 'grid', gap: 10 }}>
                  <div style={{ padding: 12, borderRadius: 14, border: '1px solid var(--card-border)', background: 'var(--panel-bg)' }}>
                    <div style={{ fontSize: 10.5, fontWeight: 950, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Contact</div>
                    <div style={{ marginTop: 8, display: 'grid', gap: 6, fontSize: 12.5 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)' }}>
                        <i className="ti ti-mail" /> {safeText(activeRecruiter?.email, 'Unlisted')}
                      </div>
                      {activeRecruiter?.email2 && <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)' }}><i className="ti ti-mail" /> {activeRecruiter.email2}</div>}
                      {activeRecruiter?.email3 && <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)' }}><i className="ti ti-mail" /> {activeRecruiter.email3}</div>}
                      {activeRecruiter?.email4 && <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)' }}><i className="ti ti-mail" /> {activeRecruiter.email4}</div>}
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)' }}>
                        <i className="ti ti-phone" /> {safeText(activeRecruiter?.phone, 'Unlisted')}
                      </div>
                      {activeRecruiter?.phone2 && <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)' }}><i className="ti ti-phone" /> {activeRecruiter.phone2}</div>}
                      {activeRecruiter?.phone3 && <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)' }}><i className="ti ti-phone" /> {activeRecruiter.phone3}</div>}
                      {activeRecruiter?.phone4 && <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)' }}><i className="ti ti-phone" /> {activeRecruiter.phone4}</div>}
                    </div>
                    <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                      <button
                        onClick={() => { if (activeRecruiter?.email) navigator.clipboard.writeText(activeRecruiter.email); showToast(activeRecruiter?.email ? 'Copied email' : 'No email to copy', activeRecruiter?.email ? 'success' : 'info') }}
                        style={{ flex: 1, padding: '9px 10px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--bg-hover)', color: 'var(--text-secondary)', cursor: 'pointer', fontWeight: 950, fontSize: 12 }}
                      >
                        Copy Email
                      </button>
                      <button
                        onClick={() => { if (activeRecruiter?.phone) navigator.clipboard.writeText(activeRecruiter.phone); showToast(activeRecruiter?.phone ? 'Copied phone' : 'No phone to copy', activeRecruiter?.phone ? 'success' : 'info') }}
                        style={{ flex: 1, padding: '9px 10px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--bg-hover)', color: 'var(--text-secondary)', cursor: 'pointer', fontWeight: 950, fontSize: 12 }}
                      >
                        Copy Phone
                      </button>
                    </div>
                  </div>

                  <div style={{ padding: 12, borderRadius: 14, border: '1px solid var(--card-border)', background: 'var(--panel-bg)' }}>
                    <div style={{ fontSize: 10.5, fontWeight: 950, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Details</div>
                    <div style={{ marginTop: 8, display: 'grid', gap: 6, fontSize: 12.5, color: 'var(--text-secondary)' }}>
                      <div><span style={{ color: 'var(--text-muted)' }}>Location:</span> {safeText(activeRecruiter?.location || activeRecruiter?.state, 'Unlisted')}</div>
                      {activeRecruiter?.state_source && (
                        <div>
                          <span style={{ color: 'var(--text-muted)' }}>State Source:</span> {activeRecruiter.state_source} 
                          <span style={{ marginLeft: 6, color: activeRecruiter.state_confidence === 'high' ? 'var(--success)' : 'var(--warning)' }}>
                            ({activeRecruiter.state_confidence})
                          </span>
                        </div>
                      )}
                      {activeRecruiter?.state_reason && (
                        <div style={{ fontStyle: 'italic', color: 'var(--text-muted)', fontSize: 11 }}>
                          ↳ {activeRecruiter.state_reason}
                        </div>
                      )}
                      <div><span style={{ color: 'var(--text-muted)' }}>Title:</span> {safeText(activeRecruiter?.title, 'Unlisted')}</div>
                      <div><span style={{ color: 'var(--text-muted)' }}>Specialization:</span> {safeText(activeRecruiter?.specialization, 'Unlisted')}</div>
                    </div>
                  </div>

                  <div style={{ padding: 12, borderRadius: 14, border: '1px solid var(--card-border)', background: 'var(--panel-bg)' }}>
                    <div style={{ fontSize: 10.5, fontWeight: 950, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Future</div>
                    <div style={{ marginTop: 8, fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                      LinkedIn, notes, and tags will appear here when implemented.
                    </div>
                  </div>
                </div>
              </div>
            )}
        </div>

        {toast && (
          <div style={{ position: 'fixed', bottom: 18, right: 18, zIndex: 50 }}>
            <div className="card" style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
              <i
                className={toast.type === 'error' ? 'ti ti-alert-triangle' : toast.type === 'success' ? 'ti ti-circle-check' : toast.type === 'info' ? 'ti ti-info-circle' : 'ti ti-info-circle'}
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
