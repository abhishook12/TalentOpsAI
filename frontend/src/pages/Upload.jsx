import { useState, useRef } from 'react'
import JobsHistory from '../components/JobsHistory'
import SmartUploadWizard from '../components/SmartUploadWizard'
import LiveUploadStatusPanel from '../components/LiveUploadStatusPanel'

import api, { getErrorMessage } from '../services/api'

// ─── Regex Parsers (for Paste & Parse) ────────────────────────────────────────
const EMAIL_RE   = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g
const PHONE_RE   = /(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/g
const LINKEDIN_RE = /https?:\/\/(?:www\.)?linkedin\.com\/in\/[^\s,<>"')]+/gi
const NAME_RE    = /\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b/g

function cleanPhone(p) {
  return p.replace(/[^\d+]/g, '').replace(/^1(\d{10})$/, '$1')
}

function parseText(raw) {
  const emails   = [...new Set([...(raw.match(EMAIL_RE) || [])].map(e => e.toLowerCase()))]
  const phones   = [...new Set([...(raw.match(PHONE_RE) || [])].map(cleanPhone).filter(p => p.length >= 10))]
  const linkedins= [...new Set([...(raw.match(LINKEDIN_RE) || [])])]
  const rawNames = [...new Set([...(raw.match(NAME_RE) || [])])]

  const SKIP = new Set(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
    'January', 'February', 'March', 'April', 'June', 'July', 'August', 'September', 'October',
    'November', 'December', 'Hi', 'Dear', 'Hello', 'Please', 'Thank', 'Best', 'Regards',
    'Kind', 'Looking', 'Forward', 'Good', 'Morning', 'Evening', 'Afternoon'])
  const names = rawNames.filter(n => {
    const parts = n.split(' ')
    return parts.length >= 2 && parts.every(p => !SKIP.has(p))
  })

  const recruiters = []
  const used = { emails: new Set(), phones: new Set() }

  emails.forEach((email, i) => {
    if (used.emails.has(email)) return
    used.emails.add(email)

    const nearbyName = names.find(n => {
      const ni = raw.toLowerCase().indexOf(n.toLowerCase())
      const ei = raw.toLowerCase().indexOf(email)
      return Math.abs(ni - ei) < 200
    }) || ''

    const nearbyPhone = phones.find(p => {
      const pi = raw.indexOf(p.slice(0, 6))
      const ei = raw.indexOf(email)
      return Math.abs(pi - ei) < 300 && !used.phones.has(p)
    }) || ''
    if (nearbyPhone) used.phones.add(nearbyPhone)

    const nearbyLinkedin = linkedins.find(l => {
      const li = raw.indexOf(l)
      const ei = raw.indexOf(email)
      return Math.abs(li - ei) < 400
    }) || ''

    recruiters.push({
      id: i,
      recruiter_name: nearbyName,
      email,
      phone: nearbyPhone,
      email2: '',
      phone2: '',
      linkedin: nearbyLinkedin,
      specialization: '',
      notes: '',
      selected: true,
    })
  })

  return recruiters
}


// ─── Legacy CSV Upload Zone ───────────────────────────────────────────────────
function LegacyUploadZone() {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const doUpload = async (file) => {
    if (!file) return
    setUploading(true); setResult(null); setError(null)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await api.post('/upload/recruiters', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setResult(res.data)
    } catch (e) {
      setError(getErrorMessage(e, 'Upload failed. Check file format.'))
    }
    setUploading(false)
  }

  return (
    <div className="card" style={{ padding: 24, marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: '#185FA518', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className="ti ti-file-spreadsheet" style={{ fontSize: 18, color: '#185FA5' }} />
        </div>
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Legacy CSV / Excel Upload</h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Requires exact headers: recruiter_name, email, phone, linkedin, etc.</p>
        </div>
      </div>

      <div onClick={() => inputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); doUpload(e.dataTransfer.files[0]) }}
        style={{
          border: `2px dashed ${dragging ? '#185FA5' : 'var(--card-border)'}`,
          borderRadius: 10, padding: '30px 20px', textAlign: 'center', cursor: 'pointer',
          background: dragging ? '#185FA508' : 'var(--main-bg)', transition: 'all 0.15s', marginBottom: 12,
        }}>
        <i className="ti ti-cloud-upload" style={{ fontSize: 28, color: dragging ? '#185FA5' : 'var(--text-muted)', display: 'block', marginBottom: 8 }} />
        <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', marginBottom: 3 }}>{uploading ? 'Uploading...' : 'Drop file here or click to browse'}</p>
        <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Supports .csv and .xlsx</p>
        <input ref={inputRef} type="file" accept=".csv,.xlsx" style={{ display: 'none' }} onChange={e => doUpload(e.target.files[0])} />
      </div>

      {result && (
        <div style={{ padding: '12px 16px', background: 'rgba(15,110,86,0.08)', border: '1px solid rgba(15,110,86,0.2)', borderRadius: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <i className="ti ti-circle-check" style={{ color: '#0F6E56', fontSize: 16 }} />
            <span style={{ fontSize: 13, fontWeight: 500, color: '#0F6E56' }}>Upload successful!</span>
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            {[['Total Rows', result.total_rows], ['Inserted', result.inserted], ['Skipped', result.duplicates_skipped]].map(([l, v]) => (
              <div key={l} style={{ textAlign: 'center' }}>
                <p style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>{v}</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{l}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {error && (
        <div style={{ padding: '10px 14px', background: 'rgba(196,57,74,0.08)', border: '1px solid rgba(196,57,74,0.2)', borderRadius: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
          <i className="ti ti-alert-circle" style={{ color: '#C4394A', fontSize: 15 }} />
          <span style={{ fontSize: 13, color: '#C4394A' }}>{error}</span>
        </div>
      )}
    </div>
  )
}

// ─── Paste & Parse ────────────────────────────────────────────────────────────
function PasteParser() {
  const [raw, setRaw] = useState('')
  const [parsed, setParsed] = useState(null)
  const [page, setPage] = useState(1)
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState(null)

  const handleParse = () => {
    const results = parseText(raw)
    setParsed(results)
    setSaveResult(null)
    setPage(1)
  }

  const itemsPerPage = 50
  const paginated = parsed ? parsed.slice((page - 1) * itemsPerPage, page * itemsPerPage) : []
  const totalPages = parsed ? Math.ceil(parsed.length / itemsPerPage) : 0

  const toggle = (id) => setParsed(p => p.map(r => r.id === id ? { ...r, selected: !r.selected } : r))
  const updateField = (id, field, val) => setParsed(p => p.map(r => r.id === id ? { ...r, [field]: val } : r))
  const removeSelectedRows = () => {
    setParsed(p => p.filter(r => !r.selected))
    setSaveResult(null)
    setPage(1)
  }

  const handleSave = async () => {
    const toSave = parsed.filter(r => r.selected && r.email)
    if (!toSave.length) return
    setSaving(true)
    let inserted = 0, skipped = 0
    for (const r of toSave) {
      try {
        await api.post('/recruiters/', {
          recruiter_name: r.recruiter_name || r.email.split('@')[0],
          email: r.email,
          phone: r.phone || null,
          email2: r.email2 || null,
          phone2: r.phone2 || null,
          linkedin: r.linkedin || null,
          specialization: r.specialization || null,
          notes: r.notes || null,
        })
        inserted++
      } catch { skipped++ }
    }
    setSaveResult({ inserted, skipped })
    setSaving(false)
  }

  return (
    <div className="card" style={{ padding: 24, marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: '#0F6E5618', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className="ti ti-clipboard-text" style={{ fontSize: 18, color: '#0F6E56' }} />
        </div>
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Paste & Parse</h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Paste any raw text — Teams messages, emails, WhatsApp, notes</p>
        </div>
      </div>

      <textarea
        value={raw}
        onChange={e => { setRaw(e.target.value); setParsed(null); setSaveResult(null) }}
        placeholder={`Paste anything here. Examples:\n\nHi, I'm John Smith from Brooksource.\nEmail: john.smith@brooksource.com\nPhone: 917-654-3210`}
        style={{
          width: '100%', minHeight: 160, padding: '12px 14px', fontSize: 13,
          fontFamily: 'var(--mono)', borderRadius: 8, border: '1px solid var(--card-border)',
          background: 'var(--main-bg)', color: 'var(--text-primary)', resize: 'vertical',
          outline: 'none', marginBottom: 12, lineHeight: 1.6,
        }}
      />

      <button onClick={handleParse} disabled={!raw.trim()}
        className="btn-primary" style={{ marginBottom: parsed ? 20 : 0, opacity: raw.trim() ? 1 : 0.5 }}>
        <i className="ti ti-wand" style={{ fontSize: 14 }} /> Parse Text
      </button>

      {/* Parsed Results Preview */}
      {parsed !== null && (
        <div>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12, paddingTop: 20, borderTop: '1px solid var(--card-border)' }}>
            Detected Contacts ({parsed.length})
          </h3>
          {parsed.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No emails found. Contact must have at least an email address.</p>
          ) : (
            <div>
              <div style={{ overflowX: 'auto', border: '1px solid var(--card-border)', borderRadius: 8, marginBottom: 16 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: 'var(--main-bg)' }}>
                      <th style={{ padding: '8px 10px', textAlign: 'left', borderBottom: '1px solid var(--card-border)' }}>
                        <i className="ti ti-checks" />
                      </th>
                      <th style={{ padding: '8px 10px', textAlign: 'left', borderBottom: '1px solid var(--card-border)', fontWeight: 600 }}>Name</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left', borderBottom: '1px solid var(--card-border)', fontWeight: 600 }}>Email</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left', borderBottom: '1px solid var(--card-border)', fontWeight: 600 }}>Phone</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left', borderBottom: '1px solid var(--card-border)', fontWeight: 600 }}>LinkedIn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginated.map(r => (
                      <tr key={r.id} style={{ borderBottom: '1px solid var(--card-border)', background: r.selected ? 'transparent' : 'var(--main-bg)', opacity: r.selected ? 1 : 0.5 }}>
                        <td style={{ padding: '6px 10px' }}>
                          <input type="checkbox" checked={r.selected} onChange={() => toggle(r.id)} style={{ cursor: 'pointer' }} />
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <input value={r.recruiter_name} onChange={e => updateField(r.id, 'recruiter_name', e.target.value)} style={{ width: 120, padding: '4px 6px', fontSize: 12, border: '1px solid var(--card-border)', borderRadius: 4, background: 'var(--card-bg)' }} />
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <input value={r.email} onChange={e => updateField(r.id, 'email', e.target.value)} style={{ width: 160, padding: '4px 6px', fontSize: 12, border: '1px solid var(--card-border)', borderRadius: 4, background: 'var(--card-bg)' }} />
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <input value={r.phone} onChange={e => updateField(r.id, 'phone', e.target.value)} style={{ width: 100, padding: '4px 6px', fontSize: 12, border: '1px solid var(--card-border)', borderRadius: 4, background: 'var(--card-bg)' }} />
                        </td>
                        <td style={{ padding: '6px 10px' }}>
                          <input value={r.linkedin} onChange={e => updateField(r.id, 'linkedin', e.target.value)} placeholder="https://..." style={{ width: 140, padding: '4px 6px', fontSize: 12, border: '1px solid var(--card-border)', borderRadius: 4, background: 'var(--card-bg)' }} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {totalPages > 1 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, fontSize: 12 }}>
                  <button disabled={page === 1} onClick={() => setPage(p => p - 1)} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', cursor: page === 1 ? 'not-allowed' : 'pointer', opacity: page === 1 ? 0.5 : 1 }}>Prev</button>
                  <span style={{ color: 'var(--text-secondary)' }}>Page {page} of {totalPages}</span>
                  <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', cursor: page === totalPages ? 'not-allowed' : 'pointer', opacity: page === totalPages ? 0.5 : 1 }}>Next</button>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <button onClick={removeSelectedRows} disabled={!parsed.some(r => r.selected)} className="btn-secondary">
                  Remove Selected
                </button>
                <button onClick={handleSave} disabled={saving} className="btn-primary" style={{ background: 'linear-gradient(135deg, #0F6E56, #185FA5)' }}>
                  {saving ? 'Saving...' : `Save ${parsed.filter(r => r.selected).length} Contacts`}
                </button>
                {saveResult && (
                  <span style={{ fontSize: 12, fontWeight: 500, color: '#0F6E56', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <i className="ti ti-check" /> Inserted: {saveResult.inserted} | Skipped: {saveResult.skipped}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main Upload Page ─────────────────────────────────────────────────────────
export default function Upload() {
  const [activeTab, setActiveTab] = useState('smart') // smart, paste, legacy, history

  return (
    <div className="page-container">
      <div style={{ marginBottom: 20 }}>
        <div>
          <h1 className="page-title">ETL Operations</h1>
          <p className="page-subtitle">Ingest, parse, and validate recruiter data from any source in a control-room layout.</p>
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <LiveUploadStatusPanel />
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24, borderBottom: '1px solid var(--card-border)', paddingBottom: 16 }}>
        <button onClick={() => setActiveTab('smart')} className={`btn-${activeTab === 'smart' ? 'primary' : 'secondary'}`}>
          <i className="ti ti-brain" /> Smart Upload (Recommended)
        </button>
        <button onClick={() => setActiveTab('paste')} className={`btn-${activeTab === 'paste' ? 'primary' : 'secondary'}`}>
          <i className="ti ti-clipboard-text" /> Paste & Parse
        </button>
        <button onClick={() => setActiveTab('legacy')} className={`btn-${activeTab === 'legacy' ? 'primary' : 'secondary'}`}>
          <i className="ti ti-file-spreadsheet" /> Legacy Upload
        </button>
        <button onClick={() => setActiveTab('history')} className={`btn-${activeTab === 'history' ? 'primary' : 'secondary'}`}>
          <i className="ti ti-history" /> Import History
        </button>
      </div>

      <div style={{ maxWidth: 1000 }}>
        {activeTab === 'smart' && <SmartUploadWizard />}
        {activeTab === 'paste' && <PasteParser />}
        {activeTab === 'legacy' && <LegacyUploadZone />}
        {activeTab === 'history' && <JobsHistory />}
      </div>
    </div>
  )
}
