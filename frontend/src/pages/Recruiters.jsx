import { useEffect, useState, useCallback, useMemo } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const emptyForm = {
  recruiter_name: '', email: '', phone: '', linkedin: '',
  specialization: '', company_id: '', is_active: true,
  email2: '', phone2: '', notes: ''
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
            { key: 'email2', label: 'Alt Email', type: 'email' },
            { key: 'phone2', label: 'Alt Phone' },
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
  const hasExtra = !!(r.email2 || r.phone2 || r.notes)
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
            <span style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: 13.5 }}>{r.recruiter_name}</span>
          </div>
        </td>
        <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{r.email}</td>
        <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{r.phone || '—'}</td>
        <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{r.specialization || '—'}</td>
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
            {r.email2 && <div style={{ marginBottom: 6 }}><i className="ti ti-mail" style={{ marginRight: 6, color: 'var(--text-muted)' }}/><strong>Alt Email:</strong> {r.email2}</div>}
            {r.phone2 && <div style={{ marginBottom: 6 }}><i className="ti ti-phone" style={{ marginRight: 6, color: 'var(--text-muted)' }}/><strong>Alt Phone:</strong> {r.phone2}</div>}
            {r.notes && <div><i className="ti ti-notes" style={{ marginRight: 6, color: 'var(--text-muted)' }}/><strong>Notes:</strong> {r.notes}</div>}
          </td>
        </tr>
      )}
    </>
  )
}

function LockScreen({ onUnlock }) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (pin === '1012') {
      onUnlock()
    } else {
      setError(true)
      setPin('')
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '60vh' }}>
      <form onSubmit={handleSubmit} className="card page-enter" style={{ padding: 40, width: 360, textAlign: 'center' }}>
        <div style={{ width: 48, height: 48, background: 'var(--accent)', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
          <i className="ti ti-lock" style={{ fontSize: 24, color: '#fff' }} />
        </div>
        <h2 style={{ fontSize: 20, marginBottom: 8, color: 'var(--text-primary)' }}>Recruiters Database</h2>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>Enter your PIN to access this page</p>
        
        <input 
          type="password" 
          value={pin}
          onChange={e => { setPin(e.target.value); setError(false) }}
          placeholder="Enter PIN..."
          style={{ width: '100%', textAlign: 'center', letterSpacing: '0.2em', fontSize: 18, padding: '12px', marginBottom: 12, borderColor: error ? '#ef4444' : 'var(--card-border)' }}
          autoFocus
        />
        {error && <p style={{ color: '#ef4444', fontSize: 12, marginBottom: 12 }}>Incorrect PIN</p>}
        
        <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px' }}>
          Unlock
        </button>
      </form>
    </div>
  )
}

export default function Recruiters() {
  const [recruiters, setRecruiters] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterActive, setFilterActive] = useState('')
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [page, setPage] = useState(0)
  const [unlocked, setUnlocked] = useState(localStorage.getItem('recruiters_unlocked') === 'true')

  const fetchRecruiters = useCallback(() => {
    setLoading(true)
    let url = `${API}/recruiters?limit=50000`
    if (filterActive !== '') url += `&is_active=${filterActive}`
    axios.get(url).then(r => { setRecruiters(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [filterActive])

  useEffect(() => { fetchRecruiters(); setPage(0) }, [fetchRecruiters])

  const filtered = useMemo(() => {
    if (!search) return recruiters
    const q = search.toLowerCase()
    return recruiters.filter(r =>
      r.recruiter_name?.toLowerCase().includes(q) ||
      r.email?.toLowerCase().includes(q) ||
      r.specialization?.toLowerCase().includes(q) ||
      r.company_name?.toLowerCase().includes(q)
    )
  }, [recruiters, search])

  const openEdit = (r) => {
    setForm({
      recruiter_name: r.recruiter_name || '', email: r.email || '', phone: r.phone || '',
      linkedin: r.linkedin || '', specialization: r.specialization || '',
      company_id: r.company_id || '', is_active: r.is_active !== false,
      email2: r.email2 || '', phone2: r.phone2 || '', notes: r.notes || ''
    })
    setModal(r)
  }

  const handleSave = async () => {
    if (!form.recruiter_name || !form.email) return alert('Name and email are required.')
    setSaving(true)
    const payload = { ...form, company_id: form.company_id ? parseInt(form.company_id) : null }
    try {
      if (modal === 'add') {
        await axios.post(`${API}/recruiters/`, payload)
      } else {
        await axios.put(`${API}/recruiters/${modal.recruiter_id}`, payload)
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
    await axios.delete(`${API}/recruiters/${id}`).catch(() => {})
    fetchRecruiters()
  }

  const toggleActive = async (r) => {
    await axios.put(`${API}/recruiters/${r.recruiter_id}`, { is_active: !r.is_active }).catch(() => {})
    fetchRecruiters()
  }

  const paginated = filtered.slice(page * 100, (page + 1) * 100)

  if (!unlocked) {
    return <LockScreen onUnlock={() => { setUnlocked(true); localStorage.setItem('recruiters_unlocked', 'true') }} />
  }

  return (
    <div className="page-enter">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 3 }}>Recruiters</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{filtered.length} recruiter{filtered.length !== 1 ? 's' : ''} in database</p>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: '1 1 240px' }}>
          <i className="ti ti-search" style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', fontSize: 14 }} />
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(0) }} placeholder="Search name, email, specialization, company..."
            style={{ width: '100%', paddingLeft: 34, height: 38, borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13.5, outline: 'none' }} />
        </div>
        <select value={filterActive} onChange={e => { setFilterActive(e.target.value); setPage(0) }}
          style={{ padding: '0 12px', height: 38, borderRadius: 8, border: '1px solid var(--card-border)', fontSize: 13.5, outline: 'none', minWidth: 140 }}>
          <option value="">All Status</option>
          <option value="true">Active Only</option>
          <option value="false">Inactive Only</option>
        </select>
        {(search || filterActive !== '') && (
          <button onClick={() => { setSearch(''); setFilterActive(''); setPage(0) }}
            style={{ padding: '0 14px', height: 38, borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', fontSize: 13, cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Loading recruiters...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)' }}>
            <i className="ti ti-users-off" style={{ fontSize: 32, display: 'block', marginBottom: 10 }} />
            <p style={{ fontSize: 14 }}>No recruiters found</p>
          </div>
        ) : (
          <div>
            <table>
              <thead>
                <tr>
                  {['Name', 'Email', 'Phone', 'Specialization', 'Company', 'Status', ''].map(h => <th key={h}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {paginated.map(r => (
                  <RecruiterTableRow key={r.recruiter_id} r={r} toggleActive={toggleActive} openEdit={openEdit} handleDelete={handleDelete} />
                ))}
              </tbody>
            </table>
            
            {filtered.length > 100 && (
              <div style={{ padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--card-border)' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Showing {page * 100 + 1} to {Math.min((page + 1) * 100, filtered.length)} of {filtered.length} entries
                </span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button disabled={page === 0} onClick={() => setPage(p => p - 1)} style={{ padding: '6px 12px', border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', borderRadius: 6, fontSize: 12, cursor: page === 0 ? 'not-allowed' : 'pointer', opacity: page === 0 ? 0.5 : 1 }}>Previous</button>
                  <button disabled={(page + 1) * 100 >= filtered.length} onClick={() => setPage(p => p + 1)} style={{ padding: '6px 12px', border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', borderRadius: 6, fontSize: 12, cursor: (page + 1) * 100 >= filtered.length ? 'not-allowed' : 'pointer', opacity: (page + 1) * 100 >= filtered.length ? 0.5 : 1 }}>Next</button>
                </div>
              </div>
            )}
          </div>
        )}
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