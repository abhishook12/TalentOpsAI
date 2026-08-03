import { toast } from 'react-hot-toast'
import { useEffect, useState, useCallback, memo } from 'react'
import { exportToExcel } from '../services/export'
import api from '../services/api'
import { CompanyIdentity } from '../components/CompanyIdentity'
import { useSessionState } from '../hooks/useSessionState'
import { useRecruiters, usePrefetchRecruiters } from '../hooks/queries/useRecruiters'
import CustomSelect from '../components/ui/CustomSelect'

const emptyForm = {
  recruiter_name: '', email: '', phone: '', linkedin: '',
  specialization: '', location: '', company_id: '',
  email2: '', phone2: '', email3: '', phone3: '', email4: '', phone4: '', notes: ''
}

function Modal({ title, onClose, onSave, form, setForm, saving }) {
  return (
    <div className="modal-backdrop" style={{
      position: 'fixed', inset: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div className="glass-panel modal-enter" style={{
        width: 500, maxHeight: '90vh',
        overflow: 'auto',
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

const getAvatarColor = (name) => {
  const colors = [
    { bg: 'var(--accent-bg)', text: 'var(--accent-strong)', border: 'var(--accent-bg)' }, // Gold
    { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' }, // Amber
    { bg: 'rgba(100, 116, 139, 0.15)', text: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)' }, // Slate
    { bg: 'rgba(20, 184, 166, 0.15)', text: '#2dd4bf', border: 'rgba(20, 184, 166, 0.3)' }, // Teal
    { bg: 'rgba(168, 115, 68, 0.15)', text: '#d99c64', border: 'rgba(168, 115, 68, 0.3)' } // Warm Brown
  ]
  const index = name ? name.charCodeAt(0) % colors.length : 0
  return colors[index]
}

const RecruiterTableRow = memo(function RecruiterTableRow({ r }) {
  // Mock "Last Active" based on completeness to mimic the mockup's data variations
  const mockLastActive = r.completeness_score > 80 ? '2h ago' : r.completeness_score > 50 ? '3h ago' : '1d ago'
  
  const avatarStyle = getAvatarColor(r.recruiter_name)

  return (
    <tr style={{ 
      transition: 'all 0.2s ease', 
      borderBottom: '1px solid var(--card-border)',
      cursor: 'pointer'
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.02)'
      e.currentTarget.style.boxShadow = 'inset 3px 0 0 0 var(--accent)'
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.backgroundColor = 'transparent'
      e.currentTarget.style.boxShadow = 'none'
    }}
    >
      <td style={{ padding: '24px 24px', verticalAlign: 'middle' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{
            width: 44, height: 44, borderRadius: '50%', 
            background: avatarStyle.bg,
            border: `1px solid ${avatarStyle.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 15, color: avatarStyle.text, fontWeight: 600, flexShrink: 0,
            letterSpacing: '0.02em'
          }}>
            {r.recruiter_name?.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ fontWeight: 600, color: '#ffffff', fontSize: 14.5, letterSpacing: '-0.01em' }}>{r.recruiter_name}</div>
              {r.specialization && <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{r.specialization} Recruiter</div>}
              <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{r.email?.toLowerCase()}</div>
          </div>
        </div>
      </td>
      <td style={{ padding: '24px 20px', verticalAlign: 'middle' }}>
        {(() => {
          const emailDomain = r.email ? r.email.split('@')[1].toLowerCase() : null;
          const isFreemail = emailDomain && ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'].includes(emailDomain);
          const fallbackDomain = r.company_domain || (r.company && (r.company.website || r.company.email_pattern)) || (!isFreemail ? emailDomain : null);
          const fallbackName = r.company_name || (!isFreemail && emailDomain ? emailDomain.split('.')[0] : null);
          
          return (
            <CompanyIdentity 
              domain={fallbackDomain} 
              name={fallbackName} 
              metadata={r.city ? `${r.city}, ${r.state}` : fallbackDomain}
              interactive={false}
            />
          );
        })()}
      </td>
      <td style={{ padding: '24px 20px', color: 'var(--text-secondary)', fontSize: 14, verticalAlign: 'middle' }}>
        {r.state || '—'}
      </td>
      <td style={{ padding: '24px 20px', color: 'var(--text-secondary)', fontSize: 14, verticalAlign: 'middle' }}>
        {r.specialization || '—'}
      </td>
      <td style={{ padding: '24px 20px', color: 'var(--text-secondary)', fontSize: 14, textAlign: 'right', verticalAlign: 'middle' }}>
        {mockLastActive}
      </td>
      <td style={{ padding: '24px 20px', textAlign: 'center', verticalAlign: 'middle' }}>
        {r.is_active ? (
          <div style={{ 
            display: 'inline-flex', alignItems: 'center', gap: 6, 
            padding: '6px 12px', background: 'var(--accent-bg)', 
            border: '1px solid var(--accent-bg)',
            borderRadius: 100, fontSize: 12.5, color: 'var(--accent)', fontWeight: 500 
          }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-strong)', boxShadow: '0 0 8px var(--accent-strong)' }} />
            Active
          </div>
        ) : (
          <div style={{ 
            display: 'inline-flex', alignItems: 'center', gap: 6, 
            padding: '6px 12px', background: 'rgba(255,255,255,0.03)', 
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 100, fontSize: 12.5, color: 'var(--text-muted)', fontWeight: 500 
          }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-muted)' }} />
            Inactive
          </div>
        )}
      </td>
      <td style={{ padding: '24px 24px', textAlign: 'right', verticalAlign: 'middle' }}>
        <button 
          className="cc-action-btn"
          style={{ 
            width: 36, height: 36, borderRadius: '50%', background: 'transparent', 
            border: 'none', color: 'var(--text-muted)', cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(139, 92, 246, 0.15)'; e.currentTarget.style.color = '#c4b5fd' }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)' }}
        >
          <i className="ti ti-dots" style={{ fontSize: 18 }} />
        </button>
      </td>
    </tr>
  )
})

export default function Recruiters() {
  // Pagination
  const [page, setPage] = useSessionState('recruiters_page', 1)

  // Advanced Filters
  const [search, setSearch] = useSessionState('recruiters_search', '')
  const [filters, setFilters] = useSessionState('recruiters_filters', {
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

  // React Query Data Fetching
  const { data, isLoading: loading, isFetching, refetch } = useRecruiters(page, debouncedSearch, debouncedFilters)
  const recruiters = data?.results || []
  const totalCount = data?.total_count || 0
  const totalPages = data?.total_pages || 1

  // Prefetch next page
  const prefetchNextPage = usePrefetchRecruiters(page, debouncedSearch, debouncedFilters)
  useEffect(() => {
    if (page < totalPages) {
      prefetchNextPage()
    }
  }, [page, totalPages, prefetchNextPage])

  useEffect(() => {
    const handleApprove = (e) => {
      api.post(`/recruiters/${e.detail}/email/approve`).then(() => refetch())
    }
    const handleReject = (e) => {
      api.post(`/recruiters/${e.detail}/email/reject`).then(() => refetch())
    }
    window.addEventListener('approve-email', handleApprove)
    window.addEventListener('reject-email', handleReject)
    return () => {
      window.removeEventListener('approve-email', handleApprove)
      window.removeEventListener('reject-email', handleReject)
    }
  }, [refetch])


  const exportRecruiters = () => {
    if (totalCount === 0) return toast.error('No recruiters to export');
    
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
    if (!form.recruiter_name || !form.email) return toast.error('Name and email are required.')
    setSaving(true)
    const payload = { ...form, company_id: form.company_id ? parseInt(form.company_id) : null }
    try {
      if (modal === 'add') {
        await api.post(`/recruiters/`, payload)
      } else {
        await api.put(`/recruiters/${modal.recruiter_id}`, payload)
      }
      setModal(null)
      refetch()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error saving recruiter')
    }
    setSaving(false)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this recruiter?')) return
    await api.delete(`/recruiters/${id}`).catch(() => {})
    refetch()
  }

  const toggleActive = async (r) => {
    await api.put(`/recruiters/${r.recruiter_id}`, { is_active: !r.is_active }).catch(() => {})
    refetch()
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
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 6 }}>Recruiters</div>
              <h1 style={{ fontSize: 24, fontWeight: 700, color: '#ffffff', letterSpacing: '-0.02em', marginBottom: 4 }}>Recruiters</h1>
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Manage and explore recruiter records across the database.</p>
            </div>
            
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 8 }}>Updated: {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
              <button onClick={() => refetch()} className="cc-ghost-button" style={{ fontSize: 13 }}>
                  <i className="ti ti-refresh" /> Refresh Data
              </button>
              <button onClick={() => setModal('add')} className="cc-primary-button" style={{ fontSize: 13 }}>
                  <i className="ti ti-plus" /> Add Recruiter
              </button>
            </div>
          </div>
    
          {/* Main Top Filters */}
          <div className="card" style={{ padding: 16, marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ position: 'relative' }}>
              <i className="ti ti-search" style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', fontSize: 16 }} />
              <input value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} placeholder="Search recruiters..."
                style={{ width: '100%', paddingLeft: 44, height: 44, borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13.5, outline: 'none', background: 'var(--main-bg)', color: '#fff' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: 12 }}>
                <CustomSelect 
                  value={filters.state} 
                  onChange={val => updateFilter('state', val)}
                  options={[
                    { value: '', label: 'All States' },
                    { value: 'CA', label: 'California' },
                    { value: 'TX', label: 'Texas' },
                    { value: 'NY', label: 'New York' }
                  ]}
                  style={{ width: 140, height: 36 }}
                />
                <CustomSelect 
                  value={filters.title} 
                  onChange={val => updateFilter('title', val)}
                  options={[
                    { value: '', label: 'All Specialties' },
                    { value: 'Engineering', label: 'Engineering' },
                    { value: 'Product', label: 'Product' },
                    { value: 'Sales', label: 'Sales' }
                  ]}
                  style={{ width: 150, height: 36 }}
                />
                <CustomSelect 
                  value={filters.company} 
                  onChange={val => updateFilter('company', val)}
                  options={[
                    { value: '', label: 'All Companies' },
                    { value: 'Apple', label: 'Apple' },
                    { value: 'Google', label: 'Google' }
                  ]}
                  style={{ width: 150, height: 36 }}
                />
                <CustomSelect 
                  value={filters.status} 
                  onChange={val => updateFilter('status', val)}
                  options={[
                    { value: '', label: 'All Statuses' },
                    { value: 'active', label: 'Active Only' },
                    { value: 'inactive', label: 'Inactive Only' }
                  ]}
                  style={{ width: 140, height: 36 }}
                />
              </div>
              <button onClick={clearFilters} style={{ background: 'none', border: 'none', color: 'var(--accent)', fontSize: 12.5, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 500 }}>
                <i className="ti ti-filter-off" style={{ fontSize: 14 }} /> Clear Filters
              </button>
            </div>
          </div>
    
          {/* Table */}
          <div className="card" style={{ overflow: 'hidden' }}>
            {loading ? (
              <div style={{ padding: 120, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
                  <i className="ti ti-loader" style={{ fontSize: 36, animation: 'spin 1s linear infinite', color: 'var(--accent)' }} />
                  <div style={{ fontWeight: 500 }}>Scanning Talent Database...</div>
              </div>
            ) : recruiters.length === 0 ? (
              <div style={{ padding: '100px 20px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
                  <i className="ti ti-users" style={{ fontSize: 32, color: 'var(--text-muted)' }} />
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 600, color: '#ffffff', marginBottom: 8 }}>No recruiters found</h3>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', maxWidth: 400, margin: '0 auto 24px', lineHeight: 1.5 }}>
                  We couldn't find any recruiters matching your current filters. Try adjusting your search criteria or adding a new recruiter to the system.
                </p>
                <div style={{ display: 'flex', gap: 12 }}>
                  <button onClick={clearFilters} style={{ padding: '10px 20px', border: '1px solid var(--card-border)', background: 'var(--main-bg)', color: 'var(--text-primary)', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500, transition: 'all 0.2s ease' }} onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.05)'} onMouseLeave={e => e.target.style.background = 'var(--main-bg)'}>
                    Clear Filters
                  </button>
                  <button onClick={() => setModal('add')} className="cc-primary-button" style={{ padding: '10px 20px', fontSize: 13, fontWeight: 500 }}>
                    Add Recruiter
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead style={{ position: 'sticky', top: 0, background: 'rgba(15, 15, 35, 0.95)', zIndex: 10 }}>
                    <tr>
                      <th style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', padding: '20px 24px', borderBottom: '1px solid var(--card-border)' }}>Recruiter</th>
                      <th style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', padding: '20px 20px', borderBottom: '1px solid var(--card-border)' }}>Company</th>
                      <th style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', padding: '20px 20px', borderBottom: '1px solid var(--card-border)' }}>State</th>
                      <th style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', padding: '20px 20px', borderBottom: '1px solid var(--card-border)' }}>Specialty</th>
                      <th style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', padding: '20px 20px', borderBottom: '1px solid var(--card-border)', textAlign: 'right' }}>Last Active</th>
                      <th style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', padding: '20px 20px', borderBottom: '1px solid var(--card-border)', textAlign: 'center' }}>Status</th>
                      <th style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', padding: '20px 24px', borderBottom: '1px solid var(--card-border)', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recruiters.map(r => (
                      <RecruiterTableRow key={r.recruiter_id} r={r} toggleActive={toggleActive} openEdit={openEdit} handleDelete={handleDelete} />
                    ))}
                  </tbody>
                </table>
                
                {/* Server-Side Pagination Footer */}
                <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderTop: '1px solid var(--card-border)', background: 'transparent' }}>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} style={{ padding: '6px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: page <= 1 ? 'not-allowed' : 'pointer', opacity: page <= 1 ? 0.5 : 1 }}>
                      <i className="ti ti-chevron-left" />
                    </button>
                    
                    {[...Array(Math.min(5, totalPages))].map((_, i) => {
                      const pNum = i + 1;
                      const active = pNum === page;
                      return (
                        <button key={pNum} onClick={() => setPage(pNum)} style={{ width: 32, height: 32, display: 'grid', placeItems: 'center', borderRadius: 6, fontSize: 13, background: active ? 'var(--accent)' : 'transparent', color: active ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', border: active ? 'none' : '1px solid transparent' }}>
                          {pNum}
                        </button>
                      )
                    })}
                    
                    {totalPages > 5 && <span style={{ color: 'var(--text-muted)', margin: '0 8px' }}>...</span>}
                    {totalPages > 5 && (
                      <button onClick={() => setPage(totalPages)} style={{ width: 32, height: 32, display: 'grid', placeItems: 'center', borderRadius: 6, fontSize: 13, background: 'transparent', color: 'var(--text-secondary)', border: 'none', cursor: 'pointer' }}>
                        {totalPages}
                      </button>
                    )}

                    <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} style={{ padding: '6px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: page >= totalPages ? 'not-allowed' : 'pointer', opacity: page >= totalPages ? 0.5 : 1 }}>
                      <i className="ti ti-chevron-right" />
                    </button>
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
