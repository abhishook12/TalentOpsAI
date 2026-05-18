import { useEffect, useState, useCallback } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const emptyForm = {
  recruiter_name: '', email: '', phone: '', linkedin: '',
  specialization: '', company_id: '', is_active: true,
}

function Modal({ title, onClose, onSave, form, setForm, saving }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      backdropFilter: 'blur(2px)',
    }}>
      <div style={{
        background: '#fff', borderRadius: 14, width: 500, maxHeight: '90vh',
        overflow: 'auto', boxShadow: '0 24px 60px rgba(0,0,0,0.18)',
        animation: 'fadeUp 0.2s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #f1f5f9' }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a' }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, color: '#94a3b8', cursor: 'pointer', lineHeight: 1 }}>×</button>
        </div>
        <div style={{ padding: '20px 24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          {[
            { key: 'recruiter_name', label: 'Full Name *', span: 2 },
            { key: 'email', label: 'Email *', type: 'email' },
            { key: 'phone', label: 'Phone' },
            { key: 'specialization', label: 'Specialization', span: 2 },
            { key: 'linkedin', label: 'LinkedIn URL', span: 2 },
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
          <div style={{ gridColumn: 'span 2' }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Status</label>
            <select value={form.is_active ? 'active' : 'inactive'} onChange={e => setForm(f => ({ ...f, is_active: e.target.value === 'active' }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none', background: '#fff' }}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '16px 24px', borderTop: '1px solid #f1f5f9' }}>
          <button onClick={onClose} style={{ padding: '9px 18px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 13, cursor: 'pointer', fontWeight: 500 }}>Cancel</button>
          <button onClick={onSave} disabled={saving} style={{ padding: '9px 20px', borderRadius: 8, border: 'none', background: '#185FA5', color: '#fff', fontSize: 13, cursor: saving ? 'not-allowed' : 'pointer', fontWeight: 500, opacity: saving ? 0.7 : 1 }}>
            {saving ? 'Saving...' : 'Save Recruiter'}
          </button>
        </div>
      </div>
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

  const fetchRecruiters = useCallback(() => {
    setLoading(true)
    let url = `${API}/recruiters?limit=500`
    if (filterActive !== '') url += `&is_active=${filterActive}`
    axios.get(url).then(r => { setRecruiters(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [filterActive])

  useEffect(() => { fetchRecruiters() }, [fetchRecruiters])

  const filtered = recruiters.filter(r =>
    !search ||
    r.recruiter_name?.toLowerCase().includes(search.toLowerCase()) ||
    r.email?.toLowerCase().includes(search.toLowerCase()) ||
    r.specialization?.toLowerCase().includes(search.toLowerCase()) ||
    r.company_name?.toLowerCase().includes(search.toLowerCase())
  )

  const openAdd = () => { setForm(emptyForm); setModal('add') }
  const openEdit = (r) => {
    setForm({
      recruiter_name: r.recruiter_name || '', email: r.email || '', phone: r.phone || '',
      linkedin: r.linkedin || '', specialization: r.specialization || '',
      company_id: r.company_id || '', is_active: r.is_active !== false,
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

  return (
    <div className="page-enter">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 3 }}>Recruiters</h1>
          <p style={{ fontSize: 13, color: '#94a3b8' }}>{filtered.length} recruiter{filtered.length !== 1 ? 's' : ''} in database</p>
        </div>
        <button className="btn-primary" onClick={openAdd} id="add-recruiter-btn">
          <i className="ti ti-user-plus" style={{ fontSize: 14 }} /> Add Recruiter
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: '1 1 240px' }}>
          <i className="ti ti-search" style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', fontSize: 14 }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search name, email, specialization, company..."
            style={{ width: '100%', paddingLeft: 34, height: 38, borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13.5, outline: 'none' }} />
        </div>
        <select value={filterActive} onChange={e => setFilterActive(e.target.value)}
          style={{ padding: '0 12px', height: 38, borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13.5, color: filterActive !== '' ? '#0f172a' : '#94a3b8', background: '#fff', outline: 'none', minWidth: 140 }}>
          <option value="">All Status</option>
          <option value="true">Active Only</option>
          <option value="false">Inactive Only</option>
        </select>
        {(search || filterActive !== '') && (
          <button onClick={() => { setSearch(''); setFilterActive('') }}
            style={{ padding: '0 14px', height: 38, borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 13, cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Loading recruiters...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#94a3b8' }}>
            <i className="ti ti-users-off" style={{ fontSize: 32, display: 'block', marginBottom: 10 }} />
            <p style={{ fontSize: 14 }}>No recruiters found</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                {['Name', 'Email', 'Phone', 'Specialization', 'Company', 'Status', ''].map(h => <th key={h}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.recruiter_id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: '50%', background: '#1e3a5f',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 11, color: '#7dd3fc', fontWeight: 600, flexShrink: 0,
                      }}>
                        {r.recruiter_name?.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()}
                      </div>
                      <span style={{ fontWeight: 500, color: '#0f172a', fontSize: 13.5 }}>{r.recruiter_name}</span>
                    </div>
                  </td>
                  <td style={{ color: '#64748b', fontSize: 13 }}>{r.email}</td>
                  <td style={{ color: '#64748b', fontSize: 13 }}>{r.phone || '—'}</td>
                  <td style={{ color: '#64748b', fontSize: 13 }}>{r.specialization || '—'}</td>
                  <td style={{ color: '#64748b', fontSize: 13 }}>{r.company_name || '—'}</td>
                  <td>
                    <button onClick={() => toggleActive(r)} style={{
                      padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 500, cursor: 'pointer', border: 'none',
                      background: r.is_active ? '#dcfce7' : '#fee2e2',
                      color: r.is_active ? '#166534' : '#991b1b',
                    }}>
                      {r.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      <button onClick={() => openEdit(r)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 12, cursor: 'pointer' }}>
                        <i className="ti ti-edit" style={{ fontSize: 13 }} />
                      </button>
                      <button onClick={() => handleDelete(r.recruiter_id)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #fee2e2', background: '#fff', color: '#dc2626', fontSize: 12, cursor: 'pointer' }}>
                        <i className="ti ti-trash" style={{ fontSize: 13 }} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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