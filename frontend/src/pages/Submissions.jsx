import { useEffect, useState, useCallback } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

const STATUSES = ['submitted', 'interview', 'offer', 'rejected', 'placed', 'withdrawn']

const statusStyle = {
  submitted:  { bg: '#dbeafe', color: '#1e40af' },
  interview:  { bg: '#fef9c3', color: '#854d0e' },
  offer:      { bg: '#dcfce7', color: '#166534' },
  rejected:   { bg: '#fee2e2', color: '#991b1b' },
  placed:     { bg: '#f0fdf4', color: '#15803d' },
  withdrawn:  { bg: '#f1f5f9', color: '#475569' },
}

const emptyForm = {
  candidate_id: '', recruiter_id: '', company_id: '', vendor_id: '',
  job_title: '', status: 'submitted', submission_date: '', notes: '',
}

function Modal({ title, onClose, onSave, form, setForm, saving, candidates, recruiters, companies, vendors }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      backdropFilter: 'blur(2px)',
    }}>
      <div style={{
        background: '#fff', borderRadius: 14, width: 540, maxHeight: '90vh',
        overflow: 'auto', boxShadow: '0 24px 60px rgba(0,0,0,0.18)',
        animation: 'fadeUp 0.2s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #f1f5f9' }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: '#0f172a' }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, color: '#94a3b8', cursor: 'pointer', lineHeight: 1 }}>×</button>
        </div>
        <div style={{ padding: '20px 24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div style={{ gridColumn: 'span 2' }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Candidate *</label>
            <select value={form.candidate_id} onChange={e => setForm(f => ({ ...f, candidate_id: e.target.value }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none', background: '#fff' }}>
              <option value="">Select candidate...</option>
              {candidates.map(c => <option key={c.candidate_id} value={c.candidate_id}>{c.candidate_name} — {c.email}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Recruiter</label>
            <select value={form.recruiter_id} onChange={e => setForm(f => ({ ...f, recruiter_id: e.target.value }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none', background: '#fff' }}>
              <option value="">Select...</option>
              {recruiters.map(r => <option key={r.recruiter_id} value={r.recruiter_id}>{r.recruiter_name}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Company</label>
            <select value={form.company_id} onChange={e => setForm(f => ({ ...f, company_id: e.target.value }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none', background: '#fff' }}>
              <option value="">Select...</option>
              {companies.map(c => <option key={c.company_id} value={c.company_id}>{c.company_name}</option>)}
            </select>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Job Title</label>
            <input value={form.job_title} onChange={e => setForm(f => ({ ...f, job_title: e.target.value }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none' }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Status</label>
            <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none', background: '#fff' }}>
              {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Submission Date</label>
            <input type="date" value={form.submission_date} onChange={e => setForm(f => ({ ...f, submission_date: e.target.value }))}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none' }} />
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 5 }}>Notes</label>
            <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={3}
              style={{ width: '100%', padding: '9px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13.5, outline: 'none', resize: 'vertical', fontFamily: 'inherit' }} />
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '16px 24px', borderTop: '1px solid #f1f5f9' }}>
          <button onClick={onClose} style={{ padding: '9px 18px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 13, cursor: 'pointer', fontWeight: 500 }}>Cancel</button>
          <button onClick={onSave} disabled={saving} style={{ padding: '9px 20px', borderRadius: 8, border: 'none', background: '#185FA5', color: '#fff', fontSize: 13, cursor: saving ? 'not-allowed' : 'pointer', fontWeight: 500, opacity: saving ? 0.7 : 1 }}>
            {saving ? 'Saving...' : 'Save Submission'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Submissions() {
  const [submissions, setSubmissions] = useState([])
  const [candidates, setCandidates] = useState([])
  const [recruiters, setRecruiters] = useState([])
  const [companies, setCompanies] = useState([])
  const [vendors, setVendors] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)

  const fetchAll = useCallback(() => {
    setLoading(true)
    let url = `${API}/submissions?limit=500`
    if (filterStatus) url += `&status=${filterStatus}`
    Promise.all([
      axios.get(url),
      axios.get(`${API}/candidates?limit=500`),
      axios.get(`${API}/recruiters?limit=500`),
      axios.get(`${API}/companies/`),
      axios.get(`${API}/vendors/`),
    ]).then(([s, c, r, co, v]) => {
      setSubmissions(s.data)
      setCandidates(c.data)
      setRecruiters(r.data)
      setCompanies(co.data)
      setVendors(v.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [filterStatus])

  useEffect(() => { fetchAll() }, [fetchAll])

  const filtered = submissions.filter(s =>
    !search ||
    s.candidate_name?.toLowerCase().includes(search.toLowerCase()) ||
    s.job_title?.toLowerCase().includes(search.toLowerCase()) ||
    s.company_name?.toLowerCase().includes(search.toLowerCase()) ||
    s.recruiter_name?.toLowerCase().includes(search.toLowerCase())
  )

  const openAdd = () => { setForm(emptyForm); setModal('add') }
  const openEdit = (s) => {
    setForm({
      candidate_id: s.candidate_id || '', recruiter_id: s.recruiter_id || '',
      company_id: s.company_id || '', vendor_id: s.vendor_id || '',
      job_title: s.job_title || '', status: s.status || 'submitted',
      submission_date: s.submission_date || '', notes: s.notes || '',
    })
    setModal(s)
  }

  const updateStatus = async (id, newStatus) => {
    await axios.put(`${API}/submissions/${id}`, { status: newStatus }).catch(() => {})
    fetchAll()
  }

  const handleSave = async () => {
    if (!form.candidate_id) return alert('Please select a candidate.')
    setSaving(true)
    const payload = {
      ...form,
      candidate_id: parseInt(form.candidate_id),
      recruiter_id: form.recruiter_id ? parseInt(form.recruiter_id) : null,
      company_id: form.company_id ? parseInt(form.company_id) : null,
      vendor_id: form.vendor_id ? parseInt(form.vendor_id) : null,
      submission_date: form.submission_date || null,
    }
    try {
      if (modal === 'add') {
        await axios.post(`${API}/submissions/`, payload)
      } else {
        await axios.put(`${API}/submissions/${modal.submission_id}`, payload)
      }
      setModal(null)
      fetchAll()
    } catch (e) {
      alert(e.response?.data?.detail || 'Error saving submission')
    }
    setSaving(false)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this submission?')) return
    await axios.delete(`${API}/submissions/${id}`).catch(() => {})
    fetchAll()
  }

  const NEXT_STATUS = {
    submitted: 'interview', interview: 'offer', offer: 'placed',
  }

  return (
    <div className="page-enter">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 3 }}>Submissions</h1>
          <p style={{ fontSize: 13, color: '#94a3b8' }}>{filtered.length} submission{filtered.length !== 1 ? 's' : ''} tracked</p>
        </div>
        <button className="btn-primary" onClick={openAdd} id="add-submission-btn">
          <i className="ti ti-plus" style={{ fontSize: 14 }} /> Add Submission
        </button>
      </div>

      {/* Status summary pills */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 18, flexWrap: 'wrap' }}>
        <button onClick={() => setFilterStatus('')}
          style={{ padding: '5px 14px', borderRadius: 999, border: `1.5px solid ${filterStatus === '' ? '#185FA5' : '#e2e8f0'}`, background: filterStatus === '' ? '#185FA5' : '#fff', color: filterStatus === '' ? '#fff' : '#64748b', fontSize: 12, cursor: 'pointer', fontWeight: 500 }}>
          All ({submissions.length})
        </button>
        {STATUSES.map(s => {
          const count = submissions.filter(x => x.status === s).length
          const st = statusStyle[s] || { bg: '#f1f5f9', color: '#475569' }
          return (
            <button key={s} onClick={() => setFilterStatus(s === filterStatus ? '' : s)}
              style={{ padding: '5px 14px', borderRadius: 999, border: `1.5px solid ${filterStatus === s ? st.color : '#e2e8f0'}`, background: filterStatus === s ? st.bg : '#fff', color: filterStatus === s ? st.color : '#64748b', fontSize: 12, cursor: 'pointer', fontWeight: 500 }}>
              {s.charAt(0).toUpperCase() + s.slice(1)} ({count})
            </button>
          )
        })}
      </div>

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: 16, maxWidth: 380 }}>
        <i className="ti ti-search" style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', fontSize: 14 }} />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search candidate, job title, company..."
          style={{ width: '100%', paddingLeft: 34, height: 38, borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13.5, outline: 'none' }} />
      </div>

      {/* Table */}
      <div className="card" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Loading submissions...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#94a3b8' }}>
            <i className="ti ti-file-off" style={{ fontSize: 32, display: 'block', marginBottom: 10 }} />
            <p style={{ fontSize: 14 }}>No submissions found</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                {['Candidate', 'Job Title', 'Company', 'Recruiter', 'Status', 'Date', ''].map(h => <th key={h}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {filtered.map(s => {
                const st = statusStyle[s.status] || { bg: '#f1f5f9', color: '#475569' }
                const next = NEXT_STATUS[s.status]
                return (
                  <tr key={s.submission_id}>
                    <td>
                      <div style={{ fontWeight: 500, color: '#0f172a', fontSize: 13.5 }}>{s.candidate_name || `#${s.candidate_id}`}</div>
                    </td>
                    <td style={{ color: '#64748b', fontSize: 13 }}>{s.job_title || '—'}</td>
                    <td style={{ color: '#64748b', fontSize: 13 }}>{s.company_name || '—'}</td>
                    <td style={{ color: '#64748b', fontSize: 13 }}>{s.recruiter_name || '—'}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ background: st.bg, color: st.color, padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 500 }}>
                          {s.status}
                        </span>
                        {next && (
                          <button onClick={() => updateStatus(s.submission_id, next)}
                            title={`Move to ${next}`}
                            style={{ padding: '3px 8px', borderRadius: 6, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 11, cursor: 'pointer' }}>
                            → {next}
                          </button>
                        )}
                      </div>
                    </td>
                    <td style={{ color: '#94a3b8', fontSize: 12 }}>{s.submission_date || '—'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        <button onClick={() => openEdit(s)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: 12, cursor: 'pointer' }}>
                          <i className="ti ti-edit" style={{ fontSize: 13 }} />
                        </button>
                        <button onClick={() => handleDelete(s.submission_id)} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #fee2e2', background: '#fff', color: '#dc2626', fontSize: 12, cursor: 'pointer' }}>
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
          title={modal === 'add' ? 'Add Submission' : 'Edit Submission'}
          onClose={() => setModal(null)}
          onSave={handleSave}
          form={form}
          setForm={setForm}
          saving={saving}
          candidates={candidates}
          recruiters={recruiters}
          companies={companies}
          vendors={vendors}
        />
      )}
    </div>
  )
}