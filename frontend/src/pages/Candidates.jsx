import { useEffect, useState, useCallback } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const VISA_OPTIONS = ['H1B', 'GC', 'USC', 'OPT', 'CPT', 'TN']
const AVAIL_OPTIONS = ['immediate', '2 weeks', '1 month']

const visaBadgeStyle = {
  H1B:  { background: '#dbeafe', color: '#1e40af' },
  GC:   { background: '#dcfce7', color: '#166534' },
  USC:  { background: '#f0fdf4', color: '#15803d' },
  OPT:  { background: '#fef9c3', color: '#854d0e' },
  CPT:  { background: '#fef3c7', color: '#92400e' },
  TN:   { background: '#f3e8ff', color: '#6b21a8' },
}

const emptyForm = {
  candidate_name: '', email: '', phone: '', linkedin: '',
  visa_status: '', skills: '', experience_years: '', location: '',
  rate_per_hour: '', availability: '', recruiter_id: '',
}

function Modal({ title, onClose, onSave, form, setForm, saving }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      backdropFilter: 'blur(2px)',
    }}>
      <div style={{
        background: '#fff', borderRadius: 14, width: 560, maxHeight: '90vh',
        overflow: 'auto', boxShadow: '0 24px 60px rgba(0,0,0,0.18)',
        animation: 'fadeUp 0.2s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #f1f5f9' }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a' }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, color: '#94a3b8', cursor: 'pointer', lineHeight: 1 }}>×</button>
        </div>
        <div style={{ padding: '20px 24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          {[
            { key: 'candidate_name', label: 'Full Name *', span: 2 },
            { key: 'email', label: 'Email *', type: 'email', span: 2 },
            { key: 'phone', label: 'Phone' },
            { key: 'location', label: 'Location' },
            { key: 'experience_years', label: 'Experience (yrs)', type: 'number' },
            { key: 'rate_per_hour', label: 'Rate/hr ($)', type: 'number' },
            { key: 'linkedin', label: 'LinkedIn URL', span: 2 },
            { key: 'skills', label: 'Skills (comma-separated)', span: 2 },
          ].map(({ key, label, type = 'text', span = 1 }) => (
            <div key={key} style={{ gridColumn: `span ${span}` }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>{label}</label>
              <input
                type={type}
                value={form[key]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none' }}
              />
            </div>
          ))}
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Visa Status</label>
            <select value={form.visa_status} onChange={e => setForm(f => ({ ...f, visa_status: e.target.value }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none', background: '#fff' }}>
              <option value="">Select...</option>
              {VISA_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Availability</label>
            <select value={form.availability} onChange={e => setForm(f => ({ ...f, availability: e.target.value }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none', background: '#fff' }}>
              <option value="">Select...</option>
              {AVAIL_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '16px 24px', borderTop: '1px solid #f1f5f9' }}>
          <button onClick={onClose} style={{ padding: '9px 18px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 13, cursor: 'pointer', fontWeight: 500 }}>Cancel</button>
          <button onClick={onSave} disabled={saving} style={{ padding: '9px 20px', borderRadius: 8, border: 'none', background: '#185FA5', color: '#fff', fontSize: 13, cursor: saving ? 'not-allowed' : 'pointer', fontWeight: 500, opacity: saving ? 0.7 : 1 }}>
            {saving ? 'Saving...' : 'Save Candidate'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Candidates() {
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterVisa, setFilterVisa] = useState('')
  const [filterAvail, setFilterAvail] = useState('')
  const [modal, setModal] = useState(null) // null | 'add' | candidate obj
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [deleteId, setDeleteId] = useState(null)

  const fetchCandidates = useCallback(() => {
    setLoading(true)
    let url = `${API}/candidates?limit=500`
    if (filterVisa) url += `&visa_status=${filterVisa}`
    if (filterAvail) url += `&availability=${encodeURIComponent(filterAvail)}`
    axios.get(url).then(r => { setCandidates(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [filterVisa, filterAvail])

  useEffect(() => { fetchCandidates() }, [fetchCandidates])

  const filtered = candidates.filter(c =>
    !search || c.candidate_name?.toLowerCase().includes(search.toLowerCase()) ||
    c.email?.toLowerCase().includes(search.toLowerCase()) ||
    c.location?.toLowerCase().includes(search.toLowerCase()) ||
    (typeof c.skills === 'string' ? c.skills : (c.skills || []).join(',')).toLowerCase().includes(search.toLowerCase())
  )

  const openAdd = () => { setForm(emptyForm); setModal('add') }
  const openEdit = (c) => {
    setForm({
      candidate_name: c.candidate_name || '', email: c.email || '', phone: c.phone || '',
      linkedin: c.linkedin || '', visa_status: c.visa_status || '',
      skills: Array.isArray(c.skills) ? c.skills.join(', ') : (c.skills || ''),
      experience_years: c.experience_years ?? '', location: c.location || '',
      rate_per_hour: c.rate_per_hour ?? '', availability: c.availability || '',
      recruiter_id: c.recruiter_id || '',
    })
    setModal(c)
  }

  const handleSave = async () => {
    if (!form.candidate_name || !form.email) return alert('Name and email are required.')
    setSaving(true)
    const payload = {
      ...form,
      skills: form.skills ? form.skills.split(',').map(s => s.trim()).filter(Boolean) : [],
      experience_years: form.experience_years ? parseFloat(form.experience_years) : null,
      rate_per_hour: form.rate_per_hour ? parseFloat(form.rate_per_hour) : null,
      recruiter_id: form.recruiter_id ? parseInt(form.recruiter_id) : null,
    }
    try {
      if (modal === 'add') {
        await axios.post(`${API}/candidates/`, payload)
      } else {
        await axios.put(`${API}/candidates/${modal.candidate_id}`, payload)
      }
      setModal(null)
      fetchCandidates()
    } catch (e) {
      alert(e.response?.data?.detail || 'Error saving candidate')
    }
    setSaving(false)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this candidate?')) return
    await axios.delete(`${API}/candidates/${id}`).catch(() => {})
    fetchCandidates()
  }

  const getSkillsArray = (skills) => {
    if (Array.isArray(skills)) return skills
    if (typeof skills === 'string') return skills.split(',').map(s => s.trim()).filter(Boolean)
    return []
  }

  return (
    <div className="page-enter">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 3 }}>Candidates</h1>
          <p style={{ fontSize: 13, color: '#94a3b8' }}>{filtered.length} candidate{filtered.length !== 1 ? 's' : ''} in pipeline</p>
        </div>
        <button className="btn-primary" onClick={openAdd} id="add-candidate-btn">
          <i className="ti ti-user-plus" style={{ fontSize: 14 }} /> Add Candidate
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: '1 1 220px' }}>
          <i className="ti ti-search" style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', fontSize: 14 }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search name, email, skill, location..."
            style={{ width: '100%', paddingLeft: 34, height: 38, borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13.5, outline: 'none' }} />
        </div>
        <select value={filterVisa} onChange={e => setFilterVisa(e.target.value)}
          style={{ padding: '0 12px', height: 38, borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13.5, color: filterVisa ? '#0f172a' : '#94a3b8', background: '#fff', outline: 'none', minWidth: 130 }}>
          <option value="">All Visas</option>
          {VISA_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={filterAvail} onChange={e => setFilterAvail(e.target.value)}
          style={{ padding: '0 12px', height: 38, borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13.5, color: filterAvail ? '#0f172a' : '#94a3b8', background: '#fff', outline: 'none', minWidth: 140 }}>
          <option value="">All Availability</option>
          {AVAIL_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        {(filterVisa || filterAvail || search) && (
          <button onClick={() => { setSearch(''); setFilterVisa(''); setFilterAvail('') }}
            style={{ padding: '0 14px', height: 38, borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 13, cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Loading candidates...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#94a3b8' }}>
            <i className="ti ti-user-off" style={{ fontSize: 32, display: 'block', marginBottom: 10 }} />
            <p style={{ fontSize: 14 }}>No candidates found</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                {['Name', 'Visa', 'Skills', 'Exp', 'Location', 'Rate/hr', 'Availability', ''].map(h => <th key={h}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => {
                const vStyle = visaBadgeStyle[c.visa_status] || { background: '#f1f5f9', color: '#475569' }
                const skills = getSkillsArray(c.skills)
                return (
                  <tr key={c.candidate_id}>
                    <td>
                      <div style={{ fontWeight: 500, color: '#0f172a', fontSize: 13.5 }}>{c.candidate_name}</div>
                      <div style={{ fontSize: 11.5, color: '#94a3b8' }}>{c.email}</div>
                    </td>
                    <td>
                      {c.visa_status && (
                        <span style={{ ...vStyle, padding: '3px 9px', borderRadius: 999, fontSize: 11, fontWeight: 500 }}>
                          {c.visa_status}
                        </span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {skills.slice(0, 3).map(s => (
                          <span key={s} style={{ background: '#f1f5f9', color: '#475569', padding: '2px 7px', borderRadius: 4, fontSize: 11 }}>{s}</span>
                        ))}
                        {skills.length > 3 && <span style={{ fontSize: 11, color: '#94a3b8' }}>+{skills.length - 3}</span>}
                      </div>
                    </td>
                    <td style={{ color: '#64748b', fontSize: 13 }}>{c.experience_years ? `${c.experience_years} yrs` : '—'}</td>
                    <td style={{ color: '#64748b', fontSize: 13 }}>{c.location || '—'}</td>
                    <td style={{ color: '#0F6E56', fontWeight: 500, fontSize: 13 }}>{c.rate_per_hour ? `$${c.rate_per_hour}/hr` : '—'}</td>
                    <td>
                      {c.availability && (
                        <span style={{ background: c.availability === 'immediate' ? '#dcfce7' : '#f0f9ff', color: c.availability === 'immediate' ? '#166534' : '#0369a1', padding: '3px 9px', borderRadius: 999, fontSize: 11, fontWeight: 500 }}>
                          {c.availability}
                        </span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        <button onClick={() => openEdit(c)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 12, cursor: 'pointer' }}>
                          <i className="ti ti-edit" style={{ fontSize: 13 }} />
                        </button>
                        <button onClick={() => handleDelete(c.candidate_id)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #fee2e2', background: '#fff', color: '#dc2626', fontSize: 12, cursor: 'pointer' }}>
                          <i className="ti ti-trash" style={{ fontSize: 13 }} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <Modal
          title={modal === 'add' ? 'Add Candidate' : `Edit — ${modal.candidate_name}`}
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