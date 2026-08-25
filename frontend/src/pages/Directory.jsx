import { toast } from 'react-hot-toast'
import React, { useEffect, useMemo, useRef, useState, memo, useCallback } from 'react'
import { createPortal } from 'react-dom'
import api, { getErrorMessage } from '../services/api'
import { exportToExcel } from '../services/export'
import { CompanyIdentity } from '../components/CompanyIdentity'
import { OutlookComposeOverlay } from '../components/OutlookComposeOverlay'
import { useSessionState } from '../hooks/useSessionState'
import SaveToTalentPoolModal from '../components/talent_pools/SaveToTalentPoolModal'

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

function stateName(abbr) {
  if (!abbr || abbr === UNKNOWN_STATE) return 'No state mapped'
  return STATES.find((state) => state.abbr === abbr)?.name || abbr || 'Unknown'
}

function stateLabel(abbr) {
  if (!abbr || abbr === UNKNOWN_STATE) return UNKNOWN_STATE
  const name = stateName(abbr)
  return name === abbr ? abbr : `${abbr} - ${name}`
}

const EditableEmail = memo(function EditableEmail({ recruiter, onUpdate }) {
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
          style={{ width: '100%', padding: '4px 6px', borderRadius: 4, border: '1px solid var(--text-primary)', background: 'var(--main-bg)', color: 'var(--text-primary)', outline: 'none' }}
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
})

const RecruiterRow = memo(function RecruiterRow({ recruiter, isSelected, toggleSelection, handleUpdateEmail }) {
  return (
    <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
      <td style={{ padding: '10px 12px' }}>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => toggleSelection(recruiter, e.target.checked)}
        />
      </td>
      <td style={{ padding: '10px 12px', fontWeight: 900, color: 'var(--text-primary)' }}>{recruiter.recruiter_name || ''}</td>
      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
        <EditableEmail 
          recruiter={recruiter} 
          onUpdate={handleUpdateEmail} 
        />
      </td>
      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{recruiter.location || recruiter.state || ''}</td>
      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{recruiter.phone || ''}</td>
    </tr>
  );
})

export default function Directory() {
  const [companyQuery, setCompanyQuery] = useSessionState('dir_companyQuery', '')
  const [debouncedCompanyQuery, setDebouncedCompanyQuery] = useState('')
  const [companies, setCompanies] = useState([])
  const [companiesLoading, setCompaniesLoading] = useState(false)
  const [selectedCompany, setSelectedCompany] = useSessionState('dir_selectedCompany', null)

  const [companyStates, setCompanyStates] = useState([])
  const [statesLoading, setStatesLoading] = useState(false)
  const [selectedState, setSelectedState] = useSessionState('dir_selectedState', null)
  const [stateQuery, setStateQuery] = useSessionState('dir_stateQuery', '')

  const [recruiterQuery, setRecruiterQuery] = useSessionState('dir_recruiterQuery', '')
  const [debouncedRecruiterQuery, setDebouncedRecruiterQuery] = useState('')
  const [recruiters, setRecruiters] = useState([])
  const [recruitersLoading, setRecruitersLoading] = useState(false)
  const [recruitersTotal, setRecruitersTotal] = useState(0)
  const [page, setPage] = useSessionState('dir_page', 1)
  const [selectedRecruiters, setSelectedRecruiters] = useSessionState('dir_selectedRecruiters', new Map())

  const [isComposeOpen, setIsComposeOpen] = useState(false)
  const [isPoolModalOpen, setIsPoolModalOpen] = useState(false)
  const [toastMsg, setToastMsg] = useState(null)
  const toastRef = useRef(null)

  const setToast = useCallback((t) => {
    if (!t) {
      setToastMsg(null)
      return
    }
    if (t.type === 'error') {
      toast.error(t.message)
    } else if (t.type === 'success') {
      toast.success(t.message)
    } else {
      toast(t.message)
    }
    setToastMsg(t)
  }, [])

  const toggleSelection = useCallback((recruiter, checked) => {
    setSelectedRecruiters((prev) => {
      const next = new Map(prev)
      if (checked) next.set(recruiter.recruiter_id, recruiter)
      else next.delete(recruiter.recruiter_id)
      return next
    })
  }, [setSelectedRecruiters])

  const handleUpdateEmail = useCallback((id, newEmail) => {
    setRecruiters(prev => prev.map(r => r.recruiter_id === id ? { ...r, email: newEmail } : r))
  }, [])

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
            limit: 199,
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
  }, [debouncedCompanyQuery, setToast])

  const prevCompanyRef = useRef(selectedCompany?.company_key)

  useEffect(() => {
    // Only reset state if the company ACTUALLY changed from a previous selection
    if (prevCompanyRef.current !== undefined && prevCompanyRef.current !== selectedCompany?.company_key) {
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
    prevCompanyRef.current = selectedCompany?.company_key

    if (!selectedCompany?.company_key) return

    let alive = true

    ;(async () => {
      setStatesLoading(true)
        try {
          const { data } = await api.get('/analytics/company-states', {
            params: { 
              company_id: selectedCompany.company_id,
              company_key: selectedCompany.company_key 
            },
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
  }, [selectedCompany, setCompanyStates, setDebouncedRecruiterQuery, setPage, setRecruiterQuery, setRecruiters, setRecruitersTotal, setSelectedRecruiters, setSelectedState, setStateQuery, setStatesLoading, setToast])

  const prevStateRef = useRef(selectedState)

  useEffect(() => {
    if (prevStateRef.current !== undefined && prevStateRef.current !== selectedState) {
      setPage(1)
      setSelectedRecruiters(new Map())
    }
    prevStateRef.current = selectedState
  }, [selectedState, setPage, setSelectedRecruiters])

  // Validate selectedState against loaded companyStates
  useEffect(() => {
    if (statesLoading) return
    if (selectedState) {
      if (companyStates.length === 0 || !companyStates.some(s => s.state === selectedState)) {
        setSelectedState(null)
      }
    }
  }, [companyStates, selectedState, setSelectedState, statesLoading])

  useEffect(() => {
    if (!selectedCompany?.company_key) return

    let alive = true
    const controller = new AbortController()

    ;(async () => {
      setRecruitersLoading(true)
      try {
        const { data, headers } = await api.get('/recruiters/', {
          params: {
            page,
            limit: PAGE_SIZE,
            company_id: selectedCompany.company_id,
            company_key: selectedCompany.company_key,
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
  }, [selectedCompany, selectedState, page, debouncedRecruiterQuery, setRecruiters, setRecruitersLoading, setRecruitersTotal, setToast])

  // Clear ghost companies that were removed from the backend
  useEffect(() => {
    if (recruitersLoading) return
    if (selectedCompany && !selectedState && !debouncedRecruiterQuery) {
      if (recruitersTotal === 0) {
        setSelectedCompany(null)
      }
    }
  }, [recruitersTotal, selectedCompany, selectedState, debouncedRecruiterQuery, recruitersLoading, setSelectedCompany])

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

  const exportRows = useMemo(() => recruiters.map((recruiter) => ({
    'Name': recruiter.recruiter_name || '',
    'Email': recruiter.email || '',
    'Company': recruiter.company_name || selectedCompanyName || '',
    'Phone Number': recruiter.phone || '',
    'Designation': recruiter.title || recruiter.specialization || '',
  })), [recruiters, selectedCompanyName])

  const exportCurrentPage = async () => {
    if (!recruiters.length) return showToast('No recruiters on this page', 'error')
    await exportToExcel(exportRows, `${(selectedCompanyName || 'company').replace(/[^a-z0-9]+/gi, '_')}_page.xlsx`)
  }

  const exportSelected = async () => {
    if (!selectedRecruiters.size) return showToast('No recruiters selected', 'error')

    const rows = Array.from(selectedRecruiters.values()).map((recruiter) => ({
      'Name': recruiter.recruiter_name || '',
      'Email': recruiter.email || '',
      'Company': recruiter.company_name || selectedCompanyName || '',
      'Phone Number': recruiter.phone || '',
      'Designation': recruiter.title || recruiter.specialization || '',
    }))

    await exportToExcel(rows, `${(selectedCompanyName || 'company').replace(/[^a-z0-9]+/gi, '_')}_selected.xlsx`)
  }

  const exportEntireCompany = async () => {
    if (!selectedCompany?.company_key) return showToast('No company selected', 'error')
    
    showToast('Exporting entire company...', 'info')
    try {
      let allRecruiters = []
      let currentPage = 1
      let hasMore = true

      while (hasMore) {
        const { data } = await api.get('/recruiters/', {
          params: {
            company_id: selectedCompany.company_id,
            company_key: selectedCompany.company_key,
            limit: 100,
            page: currentPage
          }
        })
        
        if (data && data.results && data.results.length > 0) {
          allRecruiters = allRecruiters.concat(data.results)
          if (data.results.length < 100) {
            hasMore = false
          } else {
            currentPage++
          }
        } else {
          hasMore = false
        }
      }
      
      if (!allRecruiters.length) {
        return showToast('No recruiters found for this company', 'error')
      }

      await exportToExcel(allRecruiters, `${(selectedCompanyName || 'company').replace(/[^a-z0-9]+/gi, '_')}_all.xlsx`)
    } catch (err) {
      showToast('Failed to export: ' + getErrorMessage(err), 'error')
    }
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
    <div className="page-enter" style={{ height: 'calc(100vh - 180px)', minHeight: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
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
          <button className="btn-secondary" onClick={exportCurrentPage} disabled={!recruiters.length}>Export Page</button>
          <button className="btn-primary" onClick={exportEntireCompany} disabled={!selectedCompany?.company_key}>Export Entire Company</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '390px 290px 1fr', gap: 12, flex: 1, minHeight: 0, alignItems: 'stretch' }}>
        <div className="card" style={{ padding: 14, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 13, fontWeight: 900, marginBottom: 10 }}>1. Search Company</div>
          <input
            value={companyQuery}
            onChange={(event) => setCompanyQuery(event.target.value)}
            placeholder="Search company..."
            style={{ width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', caretColor: 'var(--text-primary)' }}
          />
          <div className="custom-scrollbar" style={{ marginTop: 10, flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {companiesLoading ? <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Loading companies...</div> : null}
            {!companiesLoading && companyRows.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No companies match this search.</div>
            ) : null}
            {companyRows.map((company, index) => {
              const active = selectedCompany?.company_key === company.company_key
              const pct = Math.max((company.recruiter_count || 0) / maxCompanies * 100, 4)

              return (
                <button
                  key={company.company_key}
                  onClick={() => selectCompany(company)}
                  style={{
                    textAlign: 'left',
                    padding: '10px 12px',
                    borderRadius: 6,
                    border: active ? '1px solid rgba(24,95,165,0.35)' : '1px solid var(--card-border)',
                    background: active ? 'rgba(24,95,165,0.08)' : 'var(--panel-bg)',
                    cursor: 'pointer',
                    color: 'var(--text-primary)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
                      <div style={{ 
                        width: 26, 
                        height: 26, 
                        borderRadius: 6, 
                        border: '1px solid var(--card-border)',
                        background: 'var(--bg-base)',
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        fontSize: 11,
                        fontWeight: 700,
                        color: 'var(--text-secondary)',
                        flexShrink: 0
                      }}>
                        {index + 1}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <CompanyIdentity 
                          domain={company.logo_domain || company.website || company.email_pattern} 
                          name={company.company_name} 
                          metadata={company.website || company.email_pattern || 'Domain unlisted'}
                          logo_url={company.logo_url}
                          interactive={false}
                          size={40}
                          logoSize={26}
                          style={{ padding: 0 }}
                        />
                      {(company.tags || company.notes || company.linkedin_url) && (
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8, paddingLeft: 40 + 12 }}>
                          {company.linkedin_url && (
                            <a 
                              href={company.linkedin_url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              title="LinkedIn Profile"
                              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 20, height: 20, background: '#0a66c2', color: '#fff', borderRadius: 5, textDecoration: 'none', flexShrink: 0 }}
                            >
                              <i className="ti ti-brand-linkedin" style={{ fontSize: 13 }} />
                            </a>
                          )}
                          {company.notes && (
                            <div title="Has internal notes" style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 6px', background: 'rgba(245, 158, 11, 0.1)', color: '#fbbf24', borderRadius: 4, fontSize: 10, fontWeight: 600 }}>
                              <i className="ti ti-file-description" /> Notes
                            </div>
                          )}
                          {company.tags && (() => {
                            try {
                              const tags = typeof company.tags === 'string' ? JSON.parse(company.tags) : company.tags;
                              if (!Array.isArray(tags)) return null;
                              return tags.slice(0, 3).map((tag, i) => (
                                <div key={i} style={{ display: 'flex', alignItems: 'center', padding: '2px 6px', background: 'rgba(255,255,255,0.04)', color: 'var(--text-secondary)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 4, fontSize: 10, fontWeight: 500, whiteSpace: 'nowrap' }}>
                                  {tag}
                                </div>
                              ))
                            } catch (e) {
                              return null;
                            }
                          })()}
                        </div>
                      )}
                      </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 3, flexShrink: 0 }}>
                      <div style={{ fontFamily: 'var(--mono)', fontWeight: 800, fontSize: 13 }}>{(company.recruiter_count || 0).toLocaleString()}</div>
                      {(() => {
                        const count = company.recruiter_count || 0;
                        if (count >= 500) {
                          return <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 4, background: 'rgba(168,85,247,0.15)', color: '#c084fc', border: '1px solid rgba(168,85,247,0.3)', whiteSpace: 'nowrap' }}>Enterprise</span>;
                        } else if (count >= 50) {
                          return <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 4, background: 'rgba(59,130,246,0.15)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.3)', whiteSpace: 'nowrap' }}>Mid-Market</span>;
                        } else {
                          return <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 4, background: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)', whiteSpace: 'nowrap' }}>Boutique</span>;
                        }
                      })()}
                    </div>
                  </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <div className="card" style={{ padding: 14, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
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
                style={{ width: '100%', padding: '9px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', marginBottom: 8 }}
              />
              <button
                onClick={() => selectState(null)}
                style={{
                  width: '100%',
                  padding: 10,
                  borderRadius: 6,
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
              <div className="custom-scrollbar" style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
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
                        borderRadius: 6,
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
            style={{ width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', caretColor: 'var(--text-primary)' }}
          />

          <div 
            className="custom-scrollbar"
            style={{ 
              flex: 1, 
              minHeight: 0, 
              overflowY: 'auto', 
              overflowX: 'auto', 
              borderRadius: 6, 
              border: '1px solid var(--card-border)', 
              background: 'var(--panel-bg)' 
            }}
          >
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
                <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-hover)' }}>
                  <tr style={{ background: 'var(--bg-hover)' }}>
                    <th style={{ width: 36, padding: '10px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>
                      <input
                        type="checkbox"
                        checked={allOnPageSelected}
                        onChange={(event) => toggleSelectAllOnPage(event.target.checked)}
                      />
                    </th>
                    <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Name</th>
                    <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Email</th>
                    <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Location</th>
                    <th style={{ padding: '10px 12px', borderBottom: '1px solid var(--card-border)', textAlign: 'left' }}>Phone</th>
                  </tr>
                </thead>
                <tbody>
                  {recruiters.map((recruiter) => (
                    <RecruiterRow
                      key={recruiter.recruiter_id}
                      recruiter={recruiter}
                      isSelected={selectedRecruiters.has(recruiter.recruiter_id)}
                      toggleSelection={toggleSelection}
                      handleUpdateEmail={handleUpdateEmail}
                    />
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

      {toastMsg && (
        <div style={{ position: 'fixed', bottom: 18, right: 18, zIndex: 50 }}>
          <div className="card" style={{ padding: '10px 12px' }}>{toastMsg.message}</div>
        </div>
      )}

      {/* Floating Prompt for Bulk Mail & Talent Pool */}
      {selectedCount > 0 && !isComposeOpen && createPortal(
        <div style={{
          position: 'fixed', bottom: '80px', left: '50%', transform: 'translateX(-50%)',
          backgroundColor: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: '8px',
          padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '12px',
          boxShadow: 'var(--shadow-lg, 0 8px 32px rgba(0,0,0,0.2))', zIndex: 99999,
        }}>
          <span style={{ color: 'var(--text-primary)', fontSize: '13px', fontWeight: 600 }}>
            {selectedCount} selected:
          </span>
          <button 
            onClick={async () => {
              const toastId = toast.loading('Exporting selected recruiters to CSV...')
              try {
                const ids = Array.from(selectedRecruiters.keys())
                const res = await api.post('/recruiters/export', { recruiter_ids: ids }, { responseType: 'blob' })
                const url = window.URL.createObjectURL(new Blob([res.data]))
                const link = document.createElement('a')
                link.href = url
                link.setAttribute('download', `selected_recruiters_${ids.length}.csv`)
                document.body.appendChild(link)
                link.click()
                link.remove()
                toast.success(`Exported ${ids.length} recruiters to CSV!`, { id: toastId })
              } catch (e) {
                toast.error('Failed to export CSV', { id: toastId })
              }
            }}
            style={{
              backgroundColor: 'rgba(255,255,255,0.08)', color: 'var(--text-primary)', border: '1px solid var(--card-border)', padding: '6px 14px',
              borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4
            }}
          >
            <i className="ti ti-download" /> Export CSV
          </button>
          <button 
            onClick={() => setIsPoolModalOpen(true)}
            style={{
              backgroundColor: '#f59e0b', color: '#000', border: 'none', padding: '6px 14px',
              borderRadius: '6px', fontSize: '12px', fontWeight: 700, cursor: 'pointer'
            }}
          >
            Save to Talent Pool
          </button>
          <button 
            onClick={() => setIsComposeOpen(true)}
            style={{
              backgroundColor: '#0078d4', color: 'white', border: 'none', padding: '6px 14px',
              borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer'
            }}
          >
            Compose Mail
          </button>
        </div>,
        document.body
      )}

      {isPoolModalOpen && (
        <SaveToTalentPoolModal
          isOpen={isPoolModalOpen}
          onClose={() => setIsPoolModalOpen(false)}
          recruiterIds={Array.from(selectedRecruiters.keys())}
          onSaved={() => showToast('Saved candidates to Talent Pool!', 'success')}
        />
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
