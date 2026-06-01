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
