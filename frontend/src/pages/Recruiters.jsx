import { useEffect, useState, useCallback } from 'react'
import { exportToExcel } from '../services/export'
import api from '../services/api'

const emptyForm = {
  recruiter_name: '', email: '', phone: '', linkedin: '',
  specialization: '', location: '', company_id: '',
  email2: '', phone2: '', email3: '', phone3: '', email4: '', phone4: '', notes: ''
}

function Modal({ title, onClose, onSave, form, setForm, saving }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      backdropFilter: 'blur(2px)',
    }}>
      <div style={{
        background: 'var(--card-bg)', borderRadius: 14, width: 500, maxHeight: '90vh',
        overflow: 'auto', boxShadow: '0 24px 60px rgba(0,0,0,0.18)',
        animation: 'fadeUp 0.2s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid var(--card-border)' }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, color: 'var(--text-muted)', cursor: 'pointer', lineHeight: 1 }}>×</button>
        </div>
        <div style={{ padding: '20px 24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          {[
            { key: 'recruiter_name', label: 'Full Name *', span: 2 },
            { key: 'email', label: 'Email *', type: 'email' },
            { key: 'phone', label: 'Phone' },
            { key: 'email2', label: 'Alt Email 2', type: 'email' },
            { key: 'phone2', label: 'Alt Phone 2' },
            { key: 'email3', label: 'Alt Email 3', type: 'email' },
            { key: 'phone3', label: 'Alt Phone 3' },
            { key: 'email4', label: 'Alt Email 4', type: 'email' },
            { key: 'phone4', label: 'Alt Phone 4' },
            { key: 'specialization', label: 'Specialization', span: 2 },
            { key: 'linkedin', label: 'LinkedIn URL', span: 2 },
            { key: 'notes', label: 'Notes', span: 2, type: 'textarea' },
          ].map(({ key, label, type = 'text', span = 1 }) => (
            <div key={key} style={{ gridColumn: `span ${span}` }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 5 }}>{label}</label>
              {type === 'textarea' ? (
                <textarea
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{ width: '100%', padding: '9px 12px', border: '1px solid var(--card-border)', borderRadius: 8, fontSize: 13.5, outline: 'none', resize: 'vertical', minHeight: 60 }}
                />
              ) : (
                <input
                  type={type}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{ width: '100%', padding: '9px 12px', border: '1px solid var(--card-border)', borderRadius: 8, fontSize: 13.5, outline: 'none' }}
                />
              )}
            </div>
          ))}
          <div style={{ gridColumn: 'span 2' }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 5 }}>Status</label>
            <select value={form.is_active ? 'active' : 'inactive'} onChange={e => setForm(f => ({ ...f, is_active: e.target.value === 'active' }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid var(--card-border)', borderRadius: 8, fontSize: 13.5, outline: 'none', background: 'var(--card-bg)' }}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          {form.needs_review && (
            <div style={{ gridColumn: 'span 2', padding: '10px 14px', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#d97706', marginBottom: 4 }}>Needs Manual Review</div>
              <div style={{ fontSize: 12, color: '#b45309' }}>{form.review_reason || 'This record flagged as a possible duplicate during import.'}</div>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '16px 24px', borderTop: '1px solid var(--card-border)' }}>
          <button onClick={onClose} style={{ padding: '9px 18px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', fontSize: 13, cursor: 'pointer', fontWeight: 500 }}>Cancel</button>
          <button onClick={onSave} disabled={saving} className="btn-primary" style={{ padding: '9px 20px', fontSize: 13, cursor: saving ? 'not-allowed' : 'pointer', fontWeight: 500, opacity: saving ? 0.7 : 1 }}>
            {saving ? 'Saving...' : 'Save Recruiter'}
          </button>
        </div>
      </div>
    </div>
  )
}

function RecruiterTableRow({ r, toggleActive, openEdit, handleDelete }) {
  const [expanded, setExpanded] = useState(false)
  const hasExtra = !!((r.structured_emails && r.structured_emails.length > 0) || (r.structured_phones && r.structured_phones.length > 0) || r.notes)
  
  const qcColor = r.needs_review ? '#f59e0b' : (r.completeness_score >= 80 ? '#22c55e' : (r.completeness_score >= 50 ? '#38bdf8' : '#ef4444'))
  
  return (
    <>
      <tr style={{ background: expanded ? 'var(--main-bg)' : 'transparent' }}>
        <td>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {hasExtra ? (
              <button onClick={() => setExpanded(!expanded)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: 'var(--text-muted)' }}>
                <i className={`ti ti-chevron-${expanded ? 'up' : 'down'}`} />
              </button>
            ) : <div style={{ width: 14 }} />}
            <div style={{
              width: 32, height: 32, borderRadius: '50%', background: 'var(--accent-bg)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, color: 'var(--accent)', fontWeight: 600, flexShrink: 0,
            }}>
              {r.recruiter_name?.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()}
            </div>
            <div>
                <div style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: 13.5 }}>{r.recruiter_name}</div>
                <div style={{ fontSize: 10.5, color: qcColor, display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: qcColor }} /> 
                    {r.needs_review ? 'Needs Review' : `${r.completeness_score}% Complete`}
                </div>
            </div>
          </div>
        </td>
        <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
          {r.email_status === 'placeholder' || (r.email && r.email.includes('missing.local')) ? (
            <span style={{ color: 'var(--warning)', fontStyle: 'italic', fontSize: 11 }}>Missing (System Placeholder)</span>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {r.email}
              {r.email_status === 'verified' && <i className="ti ti-rosette-discount-check-filled" style={{ color: '#22c55e', fontSize: 14 }} title="Verified" />}
              {r.email_status === 'likely' && <i className="ti ti-check" style={{ color: '#38bdf8', fontSize: 14 }} title="Likely via MX" />}
              {r.email_status === 'inferred' && <i className="ti ti-wand" style={{ color: '#a855f7', fontSize: 14 }} title="Inferred via Pattern" />}
            </div>
          )}
        </td>
        <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            {r.phone || '—'}
        </td>
        <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            <div>{r.state || '—'}</div>
            {r.normalized_city && <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{r.normalized_city}</div>}
        </td>
        <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{r.company_name || '—'}</td>
        <td>
          <span className={r.is_active ? "badge badge-green" : "badge badge-red"}>
            {r.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td>
          <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
            <button onClick={() => toggleActive(r)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer' }}>
              <i className={r.is_active ? "ti ti-toggle-right" : "ti ti-toggle-left"} style={{ fontSize: 16 }} />
            </button>
            <button onClick={() => openEdit(r)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer' }}>
              <i className="ti ti-edit" style={{ fontSize: 14 }} />
            </button>
            <button onClick={() => handleDelete(r.recruiter_id)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid rgba(239,68,68,0.2)', background: 'var(--card-bg)', color: '#ef4444', fontSize: 12, cursor: 'pointer' }}>
              <i className="ti ti-trash" style={{ fontSize: 14 }} />
            </button>
          </div>
        </td>
      </tr>
      {expanded && hasExtra && (
        <tr>
          <td colSpan="7" style={{ background: 'var(--main-bg)', padding: '12px 16px 12px 64px', borderBottom: '1px solid var(--card-border)', fontSize: 13, color: 'var(--text-secondary)' }}>
            {r.structured_emails?.map((e, idx) => (
              <div key={idx} style={{ marginBottom: 6, display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div>
                  <i className="ti ti-mail" style={{ marginRight: 6, color: 'var(--text-muted)' }}/>
                  <strong>Email ({e.status}):</strong> {e.email} 
                  <span style={{ color: e.confidence_score > 80 ? 'var(--success)' : 'var(--warning)', marginLeft: 4 }}>
                    ({e.confidence_score}% confidence)
                  </span>
                </div>
                {(e.status === 'likely' || e.status === 'inferred') && (
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button onClick={() => window.dispatchEvent(new CustomEvent('approve-email', { detail: r.recruiter_id }))} style={{ padding: '3px 8px', borderRadius: 4, background: 'var(--success)', color: 'white', border: 'none', cursor: 'pointer', fontSize: 11 }}>Approve</button>
                    <button onClick={() => window.dispatchEvent(new CustomEvent('reject-email', { detail: r.recruiter_id }))} style={{ padding: '3px 8px', borderRadius: 4, background: '#ef4444', color: 'white', border: 'none', cursor: 'pointer', fontSize: 11 }}>Reject</button>
                  </div>
                )}
              </div>
            ))}
            {r.structured_phones?.map((p, idx) => (
               <div key={idx} style={{ marginBottom: 6 }}>
                 <i className="ti ti-phone" style={{ marginRight: 6, color: 'var(--text-muted)' }}/>
                 <strong>Phone ({p.phone_type}):</strong> {p.phone_number} {p.belongs_to_person ? '' : '(Company)'}
               </div>
            ))}
            {r.structured_locations?.map((l, idx) => (
               <div key={idx} style={{ marginBottom: 6 }}>
                 <i className="ti ti-map-pin" style={{ marginRight: 6, color: 'var(--text-muted)' }}/>
                 <strong>Location ({l.location_type}):</strong> {l.city}, {l.state} {l.is_fallback ? '(Fallback)' : ''}
               </div>
            ))}
            {r.notes && <div><i className="ti ti-notes" style={{ marginRight: 6, color: 'var(--text-muted)' }}/><strong>Notes:</strong> {r.notes}</div>}
          </td>
        </tr>
      )}
    </>
  )
}

export default function Recruiters() {
  const [recruiters, setRecruiters] = useState([])
  const [loading, setLoading] = useState(true)
  
  // Pagination
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  // Advanced Filters
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({
      state: '', city: '', company: '', title: '',
      has_phone: '', missing_email: '', status: '',
      needs_review: '', state_status: '', email_inference_status: '', sort_by: 'created_at', sort_desc: 'true'
  })
  
  const [debouncedSearch, setDebouncedSearch] = useState(search)
  const [debouncedFilters, setDebouncedFilters] = useState(filters)

  useEffect(() => {
    const t = setTimeout(() => {
        setDebouncedSearch(search)
        setDebouncedFilters(filters)
    }, 350)
    return () => clearTimeout(t)
  }, [search, filters])

  const [showFilters, setShowFilters] = useState(false)

  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)

  const fetchRecruiters = useCallback(() => {
    setLoading(true)
    const params = new URLSearchParams()
    params.append('page', page)
    params.append('limit', 10)
    
    if (debouncedSearch) params.append('search', debouncedSearch)
    if (debouncedFilters.state) params.append('state', debouncedFilters.state)
    if (debouncedFilters.city) params.append('city', debouncedFilters.city)
    if (debouncedFilters.company) params.append('company', debouncedFilters.company)
    if (debouncedFilters.title) params.append('title', debouncedFilters.title)
    
    if (debouncedFilters.has_phone === 'yes') params.append('has_phone', 'true')
    if (debouncedFilters.has_phone === 'no') params.append('has_phone', 'false')
    
    if (debouncedFilters.missing_email === 'yes') params.append('missing_email', 'true')
    if (debouncedFilters.missing_email === 'no') params.append('missing_email', 'false')
    
    if (debouncedFilters.status === 'active') params.append('is_active', 'true')
    if (debouncedFilters.status === 'inactive') params.append('is_active', 'false')
    
    if (debouncedFilters.needs_review === 'yes') params.append('needs_review', 'true')
    if (debouncedFilters.state_status) params.append('state_status', debouncedFilters.state_status)
    if (debouncedFilters.email_inference_status) params.append('email_inference_status', debouncedFilters.email_inference_status)
    
    params.append('sort_by', debouncedFilters.sort_by)
    params.append('sort_desc', debouncedFilters.sort_desc === 'true' ? 'true' : 'false')

    api.get(`/recruiters/?${params.toString()}`).then(r => { 
        setRecruiters(r.data?.results || [])
        setTotalCount(r.data?.total_count || 0)
        setTotalPages(r.data?.total_pages || 1)
        setLoading(false) 
    }).catch(e => {
        console.error(e)
        setLoading(false)
    })
  }, [page, debouncedSearch, debouncedFilters])

  useEffect(() => { fetchRecruiters() }, [fetchRecruiters])

  useEffect(() => {
    const handleApprove = (e) => {
      api.post(`/recruiters/${e.detail}/email/approve`).then(() => fetchRecruiters())
    }
    const handleReject = (e) => {
      api.post(`/recruiters/${e.detail}/email/reject`).then(() => fetchRecruiters())
    }
    window.addEventListener('approve-email', handleApprove)
    window.addEventListener('reject-email', handleReject)
    return () => {
      window.removeEventListener('approve-email', handleApprove)
      window.removeEventListener('reject-email', handleReject)
    }
  }, [fetchRecruiters])


  const exportRecruiters = () => {
    if (totalCount === 0) return alert('No recruiters to export');
    
    const params = new URLSearchParams()
    if (debouncedSearch) params.append('search', debouncedSearch)
    if (debouncedFilters.state) params.append('state', debouncedFilters.state)
    if (debouncedFilters.city) params.append('city', debouncedFilters.city)
    if (debouncedFilters.company) params.append('company', debouncedFilters.company)
    if (debouncedFilters.title) params.append('title', debouncedFilters.title)
    if (debouncedFilters.has_phone === 'yes') params.append('has_phone', 'true')
    if (debouncedFilters.has_phone === 'no') params.append('has_phone', 'false')
    if (debouncedFilters.missing_email === 'yes') params.append('missing_email', 'true')
    if (debouncedFilters.missing_email === 'no') params.append('missing_email', 'false')
    if (debouncedFilters.status === 'active') params.append('is_active', 'true')
    if (debouncedFilters.status === 'inactive') params.append('is_active', 'false')
    if (debouncedFilters.needs_review === 'yes') params.append('needs_review', 'true')
    if (debouncedFilters.state_status) params.append('state_status', debouncedFilters.state_status)

    window.open(`${api.defaults.baseURL}/recruiters/export?${params.toString()}`, '_blank');
  }

  const openEdit = (r) => {
    setForm({
      recruiter_name: r.recruiter_name || '', email: r.email || '', phone: r.phone || '',
      linkedin: r.linkedin || '', specialization: r.specialization || '',
      company_id: r.company_id || '', is_active: r.is_active !== false,
      email2: r.email2 || '', phone2: r.phone2 || '', email3: r.email3 || '', phone3: r.phone3 || '', email4: r.email4 || '', phone4: r.phone4 || '', notes: r.notes || '',
      needs_review: r.needs_review || false, review_reason: r.review_reason || ''
    })
    setModal(r)
  }

  const handleSave = async () => {
    if (!form.recruiter_name || !form.email) return alert('Name and email are required.')
    setSaving(true)
    const payload = { ...form, company_id: form.company_id ? parseInt(form.company_id) : null }
    try {
      if (modal === 'add') {
        await api.post(`/recruiters/`, payload)
      } else {
        await api.put(`/recruiters/${modal.recruiter_id}`, payload)
      }
      setModal(null)
      fetchRecruiters()
    } catch (e) {
      alert(e.response?.data?.detail || 'Error saving recruiter')
    }
    setSaving(false)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this recruiter?')) return
    await api.delete(`/recruiters/${id}`).catch(() => {})
    fetchRecruiters()
  }

  const toggleActive = async (r) => {
    await api.put(`/recruiters/${r.recruiter_id}`, { is_active: !r.is_active }).catch(() => {})
    fetchRecruiters()
  }
  
  const updateFilter = (k, v) => {
      setFilters(prev => ({...prev, [k]: v}))
      setPage(1)
  }
  
  const clearFilters = () => {
      setSearch('')
      setFilters({
          state: '', city: '', company: '', title: '',
          has_phone: '', missing_email: '', status: '', needs_review: '',
          sort_by: 'created_at', sort_desc: 'true'
      })
      setPage(1)
  }

  return (
    <div className="page-enter" style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
      
      {/* Sidebar Filters */}
      {showFilters && (
          <div className="card" style={{ width: 300, flexShrink: 0, padding: 20, animation: 'fadeUp 0.2s ease', position: 'sticky', top: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Advanced Filters</h3>
                  <button onClick={clearFilters} style={{ background: 'none', border: 'none', color: 'var(--accent)', fontSize: 12, cursor: 'pointer', fontWeight: 500 }}>Clear All</button>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>State / Region</label>
                      <input value={filters.state} onChange={e => updateFilter('state', e.target.value.toUpperCase())} placeholder="e.g. NC, TX, CA..." style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }} />
                  </div>
                  
                  <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>City</label>
                      <input value={filters.city} onChange={e => updateFilter('city', e.target.value)} placeholder="e.g. Charlotte..." style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }} />
                  </div>
                  
                  <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Company</label>
                      <input value={filters.company} onChange={e => updateFilter('company', e.target.value)} placeholder="Search company..." style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }} />
                  </div>
                  
                  <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Job Title</label>
                      <input value={filters.title} onChange={e => updateFilter('title', e.target.value)} placeholder="e.g. Technical Recruiter..." style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }} />
                  </div>
                  
                  <div style={{ height: 1, background: 'var(--card-border)' }} />
                  
                  <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Data Quality Checks</label>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          <select value={filters.email_inference_status} onChange={e => updateFilter('email_inference_status', e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }}>
                            <option value="">Any Email Inference Status</option>
                            <option value="inferred">Inferred (Requires Review)</option>
                            <option value="likely">Likely (Requires Review)</option>
                            <option value="verified">Verified / Approved</option>
                            <option value="placeholder">Missing Placeholder</option>
                          </select>
                          <select value={filters.state_status} onChange={e => updateFilter('state_status', e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }}>
                            <option value="">Any State Status</option>
                            <option value="known">State Known / Inferred</option>
                            <option value="unknown">State Unknown / Missing</option>
                          </select>
                          <select value={filters.needs_review} onChange={e => updateFilter('needs_review', e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }}>
                            <option value="">Any Confidence</option>
                            <option value="yes">Needs Manual Review</option>
                          </select>
                          <select value={filters.has_phone} onChange={e => updateFilter('has_phone', e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }}>
                            <option value="">Any Phone Status</option>
                            <option value="yes">Has Phone Number</option>
                            <option value="no">Missing Phone Number</option>
                          </select>
                          <select value={filters.missing_email} onChange={e => updateFilter('missing_email', e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }}>
                            <option value="">Any Email Status</option>
                            <option value="yes">Missing Email</option>
                            <option value="no">Has Email</option>
                          </select>
                      </div>
                  </div>
                  
                  <div style={{ height: 1, background: 'var(--card-border)' }} />
                  
                  <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Sort & Order</label>
                      <div style={{ display: 'flex', gap: 10 }}>
                          <select value={filters.sort_by} onChange={e => updateFilter('sort_by', e.target.value)} style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }}>
                            <option value="created_at">Date Added</option>
                            <option value="name">Name</option>
                            <option value="company">Company</option>
                            <option value="completeness">Data Completeness</option>
                          </select>
                          <select value={filters.sort_desc} onChange={e => updateFilter('sort_desc', e.target.value)} style={{ width: 80, padding: '8px 12px', borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--main-bg)', outline: 'none' }}>
                            <option value="true">Desc</option>
                            <option value="false">Asc</option>
                          </select>
                      </div>
                  </div>
              </div>
          </div>
      )}

      <div style={{ flex: 1, minWidth: 0 }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 3 }}>Recruiter Discovery</h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <p style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 600 }}>{totalCount.toLocaleString()} total matches found</p>
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>— Powered by Unified Data Engine</span>
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={exportRecruiters} style={{ padding: '8px 16px', fontSize: 13, borderRadius: 8, background: 'transparent', border: '1px solid var(--card-border)', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <i className="ti ti-download" style={{ marginRight: 6 }} /> Export Page
              </button>
              <button onClick={() => setModal('add')} className="btn-primary" style={{ padding: '8px 16px', fontSize: 13 }}>
                  <i className="ti ti-plus" style={{ marginRight: 6 }} /> Add Recruiter
              </button>
            </div>
          </div>
    
          {/* Main Top Filters */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: '1 1 240px' }}>
              <i className="ti ti-search" style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', fontSize: 14 }} />
              <input value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} placeholder="Search name, email, specialization, company..."
                style={{ width: '100%', paddingLeft: 40, height: 40, borderRadius: 10, border: '1px solid var(--card-border)', fontSize: 13.5, outline: 'none', background: 'var(--card-bg)' }} />
            </div>
            <select value={filters.status} onChange={e => updateFilter('status', e.target.value)}
              style={{ padding: '0 14px', height: 40, borderRadius: 10, border: '1px solid var(--card-border)', fontSize: 13.5, outline: 'none', minWidth: 140, background: 'var(--card-bg)' }}>
              <option value="">All Status</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive Only</option>
            </select>
            <button onClick={() => setShowFilters(!showFilters)}
                style={{ padding: '0 16px', height: 40, borderRadius: 10, border: `1px solid ${showFilters ? 'var(--accent)' : 'var(--card-border)'}`, background: showFilters ? 'var(--accent-bg)' : 'var(--card-bg)', color: showFilters ? 'var(--accent)' : 'var(--text-primary)', fontSize: 13.5, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 500, transition: 'all 0.2s' }}>
                <i className="ti ti-filter" /> Advanced Filters
            </button>
          </div>
    
          {/* Table */}
          <div className="card" style={{ overflow: 'hidden' }}>
            {loading ? (
              <div style={{ padding: 80, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                  <i className="ti ti-loader" style={{ fontSize: 32, animation: 'spin 1s linear infinite' }} />
                  <div>Querying Database...</div>
              </div>
            ) : recruiters.length === 0 ? (
              <div style={{ padding: 80, textAlign: 'center', color: 'var(--text-muted)' }}>
                <i className="ti ti-search" style={{ fontSize: 40, display: 'block', marginBottom: 14, color: 'var(--card-border)' }} />
                <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>No matches found</p>
                <p style={{ fontSize: 13, marginTop: 4 }}>Try adjusting your advanced filters or search query.</p>
                <button onClick={clearFilters} style={{ marginTop: 16, padding: '8px 16px', border: '1px solid var(--card-border)', background: 'var(--main-bg)', color: 'var(--text-primary)', borderRadius: 8, cursor: 'pointer', fontSize: 13 }}>Clear All Filters</button>
              </div>
            ) : (
              <div>
                <table>
                  <thead>
                    <tr>
                      {['Name', 'Email', 'Phone', 'Location', 'Company', 'Status', ''].map(h => <th key={h}>{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {recruiters.map(r => (
                      <RecruiterTableRow key={r.recruiter_id} r={r} toggleActive={toggleActive} openEdit={openEdit} handleDelete={handleDelete} />
                    ))}
                  </tbody>
                </table>
                
                {/* Server-Side Pagination Footer */}
                <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--card-border)', background: 'var(--main-bg)' }}>
                  <span style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>
                  Showing {(page - 1) * 10 + 1} to {Math.min(page * 10, totalCount)} of <strong style={{ color: 'var(--text-primary)' }}>{totalCount.toLocaleString()}</strong> results
                  </span>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 10 }}>Page {page} of {totalPages}</span>
                    <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} style={{ padding: '7px 14px', border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-primary)', borderRadius: 8, fontSize: 12.5, cursor: page <= 1 ? 'not-allowed' : 'pointer', opacity: page <= 1 ? 0.5 : 1, fontWeight: 500 }}>Previous</button>
                    <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} style={{ padding: '7px 14px', border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-primary)', borderRadius: 8, fontSize: 12.5, cursor: page >= totalPages ? 'not-allowed' : 'pointer', opacity: page >= totalPages ? 0.5 : 1, fontWeight: 500 }}>Next</button>
                  </div>
                </div>
              </div>
            )}
          </div>
      </div>

      {modal && (
        <Modal
          title={modal === 'add' ? 'Add Recruiter' : `Edit — ${modal.recruiter_name}`}
          onClose={() => setModal(null)}
          onSave={handleSave}
          form={form}
          setForm={setForm}
          saving={saving}
        />
      )}
    </div>
  )
}
