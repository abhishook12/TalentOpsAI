import { toast } from 'react-hot-toast'
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import * as XLSX from 'xlsx'
import api, { getErrorMessage } from '../services/api'
import { CompanyLogo } from '../components/CompanyLogo'
import { OutlookComposeOverlay } from '../components/OutlookComposeOverlay'
import { useSessionState } from '../hooks/useSessionState'

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

const PAGE_SIZE = 100
const UNKNOWN_STATE = 'Unknown'

function exportWorkbook(rows, sheetName = 'Recruiters') {
  const worksheet = XLSX.utils.json_to_sheet(rows)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName)
  return workbook
}

function stateName(abbr) {
  if (!abbr || abbr === UNKNOWN_STATE) return 'No state mapped'
  return STATES.find((state) => state.abbr === abbr)?.name || abbr || 'Unknown'
}

function stateLabel(abbr) {
  if (!abbr || abbr === UNKNOWN_STATE) return UNKNOWN_STATE
  const name = stateName(abbr)
  return name === abbr ? abbr : `${abbr} - ${name}`
}

function EditableEmail({ recruiter, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [email, setEmail] = useState(recruiter.email || '');
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (email === recruiter.email) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await api.put(`/recruiters/${recruiter.recruiter_id}`, { email });
      onUpdate(recruiter.recruiter_id, email);
      setEditing(false);
    } catch (e) {
      toast.error('Failed to update email: ' + getErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        <input 
          autoFocus 
          value={email} 
          onChange={e => setEmail(e.target.value)} 
          onKeyDown={e => e.key === 'Enter' && save()}
          onBlur={save}
          disabled={saving}
          style={{ width: '100%', padding: '4px 6px', borderRadius: 4, border: '1px solid var(--accent)', background: 'var(--main-bg)', color: 'var(--text-primary)', outline: 'none' }}
        />
      </div>
    );
  }

  return (
    <div 
      title={recruiter.email} 
      style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', group: 'hover' }}
      onClick={() => setEditing(true)}
    >
      <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: 180, display: 'inline-block' }}>
        {recruiter.email || <span style={{ opacity: 0.5 }}>No email</span>}
      </span>
      <i className="ti ti-pencil" style={{ opacity: 0.3, fontSize: 13 }} />
    </div>
  );
}

export default function Directory() {
  const [companyQuery, setCompanyQuery] = useSessionState('dir_companyQuery', '')
  const [debouncedCompanyQuery, setDebouncedCompanyQuery] = useState('')
  const [companies, setCompanies] = useState([])
  const [companiesLoading, setCompaniesLoading] = useState(false)
  const [selectedCompany, setSelectedCompany] = useSessionState('dir_selectedCompany', null)

  const [companyStates, setCompanyStates] = useState([])
  const [statesLoading, setStatesLoading] = useState(false)
  const [selectedState, setSelectedState] = useSessionState('dir_selectedState', null)
  const [stateQuery, setStateQuery] = useState('')

  const [recruiterQuery, setRecruiterQuery] = useSessionState('dir_recruiterQuery', '')
  const [debouncedRecruiterQuery, setDebouncedRecruiterQuery] = useState('')
  const [recruiters, setRecruiters] = useState([])
  const [recruitersLoading, setRecruitersLoading] = useState(false)
  const [recruitersTotal, setRecruitersTotal] = useState(0)
  const [page, setPage] = useSessionState('dir_page', 1)
  const [selectedRecruiters, setSelectedRecruiters] = useSessionState('dir_selectedRecruiters', new Map())

  const [isComposeOpen, setIsComposeOpen] = useState(false)
  const [toast, setToast] = useState(null)
  const toastRef = useRef(null)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedCompanyQuery(companyQuery), 250)
    return () => clearTimeout(timer)
  }, [companyQuery])

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedRecruiterQuery(recruiterQuery), 250)
    return () => clearTimeout(timer)
  }, [recruiterQuery])

  useEffect(() => {
    let alive = true

    ;(async () => {
      setCompaniesLoading(true)
      try {
        const { data } = await api.get('/analytics/companies-search', {
          params: {
            q: debouncedCompanyQuery || undefined,
            limit: 200,
            skip: 0,
            min_recruiters: 1,
          },
        })
        if (!alive) return
        setCompanies(Array.isArray(data) ? data : [])
      } catch (err) {
        if (alive) setToast({ type: 'error', message: getErrorMessage(err, 'Failed to load companies') })
      } finally {
        if (alive) setCompaniesLoading(false)
      }
    })()

    return () => { alive = false }
  }, [debouncedCompanyQuery])

  const prevCompanyRef = useRef(selectedCompany?.company_id)

  useEffect(() => {
    // Only reset state if the company ACTUALLY changed from a previous selection
    if (prevCompanyRef.current !== undefined && prevCompanyRef.current !== selectedCompany?.company_id) {
      setSelectedState(null)
      setStateQuery('')
      setRecruiterQuery('')
      setDebouncedRecruiterQuery('')
      setCompanyStates([])
      setRecruiters([])
      setRecruitersTotal(0)
      setPage(1)
      setSelectedRecruiters(new Map())
    }
    prevCompanyRef.current = selectedCompany?.company_id

    if (!selectedCompany?.company_id) return

    let alive = true

    ;(async () => {
      setStatesLoading(true)
      try {
        const { data } = await api.get('/analytics/company-states', {
          params: { company_id: selectedCompany.company_id },
        })
        if (!alive) return
        setCompanyStates(Array.isArray(data) ? data : [])
      } catch (err) {
        if (alive) setToast({ type: 'error', message: getErrorMessage(err, 'Failed to load states') })
      } finally {
        if (alive) setStatesLoading(false)
      }
    })()

    return () => { alive = false }
  }, [selectedCompany])

  const prevStateRef = useRef(selectedState)

  useEffect(() => {
    if (prevStateRef.current !== undefined && prevStateRef.current !== selectedState) {
      setPage(1)
      setSelectedRecruiters(new Map())
    }
    prevStateRef.current = selectedState
  }, [selectedState])

  useEffect(() => {
    if (!selectedCompany?.company_id) return

    let alive = true
    const controller = new AbortController()

    ;(async () => {
      setRecruitersLoading(true)
      try {
        const { data, headers } = await api.get('/recruiters', {
          params: {
            page,
            limit: PAGE_SIZE,
            company_id: selectedCompany.company_id,
            state: selectedState || undefined,
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
        if (err?.name !== 'CanceledError' && alive) {
          setToast({ type: 'error', message: getErrorMessage(err, 'Failed to load recruiters') })
        }
      } finally {
        if (alive) setRecruitersLoading(false)
      }
    })()

    return () => {
      alive = false
      controller.abort()
    }
  }, [selectedCompany, selectedState, page, debouncedRecruiterQuery])

  const totalPages = Math.max(1, Math.ceil((recruitersTotal || 0) / PAGE_SIZE))
  const selectedCount = selectedRecruiters.size
  const selectedCompanyName = selectedCompany?.company_name || ''
  const maxCompanies = Math.max(...companies.map((company) => company.recruiter_count || 0), 1)

  const companyRows = useMemo(() => {
    const query = debouncedCompanyQuery.trim().toLowerCase()
    const rows = [...companies]
    rows.sort((a, b) => (b.recruiter_count || 0) - (a.recruiter_count || 0))
    return query ? rows.filter((row) => String(row.company_name || '').toLowerCase().includes(query)) : rows
  }, [companies, debouncedCompanyQuery])

  const mappedStates = useMemo(
    () => companyStates.filter((row) => row.state !== UNKNOWN_STATE),
    [companyStates]
  )

  const unknownStateCount = useMemo(
    () => companyStates.find((row) => row.state === UNKNOWN_STATE)?.count || 0,
    [companyStates]
  )

  const mappedRecruiterCount = useMemo(
    () => mappedStates.reduce((sum, row) => sum + (row.count || 0), 0),
    [mappedStates]
  )

  const allStatesCount = selectedCompany?.recruiter_count || mappedRecruiterCount + unknownStateCount

  const filteredStateRows = useMemo(() => {
    const query = stateQuery.trim().toLowerCase()
    const rows = [...companyStates]
    rows.sort((a, b) => {
      if (a.state === UNKNOWN_STATE) return 1
      if (b.state === UNKNOWN_STATE) return -1
      return (b.count || 0) - (a.count || 0) || String(a.state).localeCompare(String(b.state))
    })
    if (!query) return rows
    return rows.filter((row) => {
      const label = stateLabel(row.state).toLowerCase()
      return label.includes(query) || String(row.state || '').toLowerCase().includes(query)
    })
  }, [companyStates, stateQuery])

  const activeFilterLabel = selectedState
    ? stateLabel(selectedState)
    : 'All states'

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    if (toastRef.current) clearTimeout(toastRef.current)
    toastRef.current = setTimeout(() => setToast(null), 2500)
  }

  const selectCompany = (company) => {
    setSelectedCompany(company)
  }

  const selectState = (state) => {
    setSelectedState(state)
  }

  const exportRows = recruiters.map((recruiter) => ({
    Name: recruiter.recruiter_name || '',
    Email: recruiter.email || '',
    Phone: recruiter.phone || '',
    Company: recruiter.company_name || selectedCompanyName || '',
    Location: recruiter.location || '',
    State: recruiter.state || (selectedState === UNKNOWN_STATE ? '' : selectedState) || '',
  }))

  const exportCurrentPage = () => {
    if (!recruiters.length) return showToast('No recruiters on this page', 'error')
    XLSX.writeFile(exportWorkbook(exportRows), `${(selectedCompanyName || 'company').replace(/[^a-z0-9]+/gi, '_')}_page.xlsx`)
  }

  const exportSelected = () => {
    if (!selectedRecruiters.size) return showToast('No recruiters selected', 'error')

    const rows = Array.from(selectedRecruiters.values()).map((recruiter) => ({
      Name: recruiter.recruiter_name || '',
      Email: recruiter.email || '',
      Phone: recruiter.phone || '',
      Company: recruiter.company_name || selectedCompanyName || '',
      Location: recruiter.location || '',
      State: recruiter.state || (selectedState === UNKNOWN_STATE ? '' : selectedState) || '',
    }))

    XLSX.writeFile(exportWorkbook(rows), `${(selectedCompanyName || 'company').replace(/[^a-z0-9]+/gi, '_')}_selected.xlsx`)
  }

  const clearSelectedRecruiters = () => setSelectedRecruiters(new Map())

  const toggleSelectAllOnPage = (checked) => {
    setSelectedRecruiters((prev) => {
      const next = new Map(prev)
      recruiters.forEach((recruiter) => {
        if (checked) next.set(recruiter.recruiter_id, recruiter)
        else next.delete(recruiter.recruiter_id)
      })
      return next
    })
  }

  const allOnPageSelected = recruiters.length > 0 && recruiters.every((recruiter) => selectedRecruiters.has(recruiter.recruiter_id))

  return (
    <div className="page-enter" style={{ minHeight: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 950, margin: 0 }}>Directory</h1>
          <div style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: 13 }}>
            Search a company, pick a state, then browse the recruiters in that location.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-secondary" onClick={clearSelectedRecruiters} disabled={!selectedCount}>Clear Selected</button>
          <button className="btn-secondary" onClick={exportSelected} disabled={!selectedCount}>Export Selected</button>
          <button className="btn-primary" onClick={exportCurrentPage} disabled={!recruiters.length}>Export Page</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '340px 300px 1fr', gap: 12, minHeight: 0, alignItems: 'start' }}>
        <div className="card" style={{ padding: 14, minHeight: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 900, marginBottom: 10 }}>1. Search Company</div>
          <input
            value={companyQuery}
            onChange={(event) => setCompanyQuery(event.target.value)}
            placeholder="Search company..."
            style={{ width: '100%', padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', caretColor: 'var(--text-primary)' }}
          />
          <div style={{ marginTop: 10, maxHeight: 'calc(100vh - 240px)', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {companiesLoading ? <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading companies...</div> : null}
            {!companiesLoading && companyRows.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No companies match this search.</div>
            ) : null}
            {companyRows.map((company) => {
              const active = selectedCompany?.company_id === company.company_id
              const pct = Math.max((company.recruiter_count || 0) / maxCompanies * 100, 4)

              return (
                <button
                  key={company.company_id}
                  onClick={() => selectCompany(company)}
                  style={{
                    textAlign: 'left',
                    padding: 12,
                    borderRadius: 14,
                    border: active ? '1px solid rgba(24,95,165,0.35)' : '1px solid var(--card-border)',
                    background: active ? 'rgba(24,95,165,0.08)' : 'var(--panel-bg)',
                    cursor: 'pointer',
                    color: 'var(--text-primary)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                      <CompanyLogo domain={company.logo_domain || company.website || company.email_pattern} name={company.company_name} size={32} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 900, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{company.company_name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{company.location || 'Location not listed'}</div>
                      </div>
                    </div>
                    <div style={{ fontFamily: 'var(--mono)', fontWeight: 900 }}>{company.recruiter_count || 0}</div>
                  </div>
                  <div style={{ marginTop: 8, height: 5, borderRadius: 99, background: 'var(--card-border)', overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: active ? 'var(--accent)' : '#4f46e5', borderRadius: 99 }} />
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <div className="card" style={{ padding: 14, minHeight: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 900, marginBottom: 10 }}>2. Select State</div>
          {!selectedCompany ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Pick a company first.</div>
          ) : (
            <>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{selectedCompany.company_name}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
                {mappedStates.length} mapped state{mappedStates.length === 1 ? '' : 's'}
                {unknownStateCount ? ` · ${unknownStateCount} unmapped` : ''}
              </div>
              <input
                value={stateQuery}
                onChange={(event) => setStateQuery(event.target.value)}
                placeholder="Filter states..."
                style={{ width: '100%', padding: '9px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', marginBottom: 8 }}
              />
              <button
                onClick={() => selectState(null)}
                style={{
                  width: '100%',
                  padding: 10,
                  borderRadius: 12,
                  marginBottom: 8,
                  border: !selectedState ? '1px solid rgba(24,95,165,0.35)' : '1px solid var(--card-border)',
                  background: !selectedState ? 'rgba(24,95,165,0.08)' : 'var(--panel-bg)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 10,
                }}
              >
                <span><strong>All states</strong></span>
                <span style={{ fontFamily: 'var(--mono)', fontWeight: 900 }}>{allStatesCount}</span>
              </button>
              <div style={{ maxHeight: 'calc(100vh - 320px)', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {statesLoading ? <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading states...</div> : null}
                {!statesLoading && filteredStateRows.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    {stateQuery ? 'No states match this filter.' : 'No state breakdown available for this company.'}
                  </div>
                ) : null}
                {filteredStateRows.map((row) => {
                  const active = selectedState === row.state
                  const isUnknown = row.state === UNKNOWN_STATE

                  return (
                    <button
                      key={row.state}
                      onClick={() => selectState(row.state)}
                      style={{
                        textAlign: 'left',
                        padding: 10,
                        borderRadius: 12,
                        border: active ? '1px solid rgba(24,95,165,0.35)' : '1px solid var(--card-border)',
                        background: active ? 'rgba(24,95,165,0.08)' : 'var(--panel-bg)',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        gap: 10,
                        color: 'var(--text-primary)',
                      }}
                    >
                      <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        <strong>{isUnknown ? UNKNOWN_STATE : row.state}</strong>
                        {!isUnknown ? ` - ${stateName(row.state)}` : ''}
                      </span>
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 900, flexShrink: 0 }}>{row.count}</span>
                    </button>
                  )
                })}
              </div>
            </>
          )}
        </div>

        <div className="card" style={{ padding: 14, minHeight: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 900 }}>3. Recruiters</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                {selectedCompanyName
                  ? `${selectedCompanyName} · ${activeFilterLabel}`
                  : 'Select a company to load recruiters.'}
              </div>
            </div>
            <div style={{ fontSize: 12, fontWeight: 900, color: 'var(--text-muted)' }}>{recruitersTotal.toLocaleString()} recruiters</div>
          </div>

          <input
            value={recruiterQuery}
            onChange={(event) => {
              setRecruiterQuery(event.target.value)
              setPage(1)
            }}
            disabled={!selectedCompany}
            placeholder={selectedCompany ? 'Search recruiters by name, email, company, location...' : 'Select a company first'}
            style={{ width: '100%', padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', caretColor: 'var(--text-primary)' }}
          />

          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', borderRadius: 14, border: '1px solid var(--card-border)', background: 'var(--panel-bg)' }}>
            {!selectedCompany ? (
              <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>Pick a company to see recruiters.</div>
            ) : recruitersLoading ? (
              <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>Loading recruiters...</div>
            ) : recruiters.length === 0 ? (
              <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>
                {debouncedRecruiterQuery
                  ? 'No recruiters match this search.'
                  : selectedState
                    ? `No recruiters found for ${activeFilterLabel}.`
                    : 'No recruiters found for this company.'}
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-hover)' }}>
                    <th style={{ width: 36, padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>
                      <input
                        type="checkbox"
                        checked={allOnPageSelected}
                        onChange={(event) => toggleSelectAllOnPage(event.target.checked)}
                      />
                    </th>
                    <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Name</th>
                    <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Email</th>
                    <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Location</th>
                    <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)' }}>Phone</th>
                  </tr>
                </thead>
                <tbody>
                  {recruiters.map((recruiter) => (
                    <tr key={recruiter.recruiter_id} style={{ borderBottom: '1px solid var(--card-border)' }}>
                      <td style={{ padding: '10px 12px' }}>
                        <input
                          type="checkbox"
                          checked={selectedRecruiters.has(recruiter.recruiter_id)}
                          onChange={(event) => {
                            setSelectedRecruiters((prev) => {
                              const next = new Map(prev)
                              if (event.target.checked) next.set(recruiter.recruiter_id, recruiter)
                              else next.delete(recruiter.recruiter_id)
                              return next
                            })
                          }}
                        />
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 900, color: 'var(--text-primary)' }}>{recruiter.recruiter_name || ''}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                        <EditableEmail 
                          recruiter={recruiter} 
                          onUpdate={(id, newEmail) => {
                            setRecruiters(prev => prev.map(r => r.recruiter_id === id ? { ...r, email: newEmail } : r))
                          }} 
                        />
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{recruiter.location || recruiter.state || ''}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{recruiter.phone || ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {selectedCompany && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, fontSize: 12, color: 'var(--text-muted)' }}>
              <div>
                Page {page} / {totalPages}
                {selectedCount ? ` · ${selectedCount} selected` : ''}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                  disabled={page <= 1 || recruitersLoading}
                  style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', cursor: page <= 1 || recruitersLoading ? 'not-allowed' : 'pointer' }}
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage((currentPage) => Math.min(totalPages, currentPage + 1))}
                  disabled={page >= totalPages || recruitersLoading}
                  style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', cursor: page >= totalPages || recruitersLoading ? 'not-allowed' : 'pointer' }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {toast && (
        <div style={{ position: 'fixed', bottom: 18, right: 18, zIndex: 50 }}>
          <div className="card" style={{ padding: '10px 12px' }}>{toast.message}</div>
        </div>
      )}

      {/* Floating Prompt for Bulk Mail */}
      {selectedCount > 0 && !isComposeOpen && createPortal(
        <div style={{
          position: 'fixed', bottom: '80px', left: '50%', transform: 'translateX(-50%)',
          backgroundColor: '#1e1e1e', border: '1px solid #333', borderRadius: '24px',
          padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 99999,
        }}>
          <span style={{ color: '#e0e0e0', fontSize: '13px', fontWeight: 600 }}>
            Want to send bulk mail to {selectedCount} selected people?
          </span>
          <button 
            onClick={() => setIsComposeOpen(true)}
            style={{
              backgroundColor: '#0078d4', color: 'white', border: 'none', padding: '6px 16px',
              borderRadius: '16px', fontSize: '13px', fontWeight: 600, cursor: 'pointer'
            }}
          >
            Compose
          </button>
        </div>,
        document.body
      )}

      {/* Outlook Compose Overlay */}
      {isComposeOpen && createPortal(
        <OutlookComposeOverlay 
          recipients={Array.from(selectedRecruiters.values())}
          onClose={() => setIsComposeOpen(false)}
          onSend={async (data) => {
            try {
              const res = await fetch('http://localhost:1337/send-bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
              });
              if (!res.ok) throw new Error('Bridge returned an error');
              showToast(`Sent ${data.recipients.length} emails via local Outlook`, 'success');
              setIsComposeOpen(false);
            } catch (err) {
              console.error(err);
              showToast('Error: Is your Local Outlook Bridge running?', 'error');
            }
          }}
        />,
        document.body
      )}
    </div>
  )
}
