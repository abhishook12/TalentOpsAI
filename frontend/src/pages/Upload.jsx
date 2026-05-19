import { useState, useRef } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

// ─── Regex Parsers ────────────────────────────────────────────────────────────
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

  // Skip generic words that match name pattern
  const SKIP = new Set(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
    'January', 'February', 'March', 'April', 'June', 'July', 'August', 'September', 'October',
    'November', 'December', 'Hi', 'Dear', 'Hello', 'Please', 'Thank', 'Best', 'Regards',
    'Kind', 'Looking', 'Forward', 'Good', 'Morning', 'Evening', 'Afternoon'])
  const names = rawNames.filter(n => {
    const parts = n.split(' ')
    return parts.length >= 2 && parts.every(p => !SKIP.has(p))
  })

  // Build recruiter objects — try to pair emails with nearby names
  const recruiters = []
  const lines = raw.split('\n')

  // Try line-by-line grouping
  const used = { emails: new Set(), phones: new Set() }

  emails.forEach((email, i) => {
    if (used.emails.has(email)) return
    used.emails.add(email)

    // Find line containing this email
    const lineIdx = lines.findIndex(l => l.toLowerCase().includes(email))
    const context = lines.slice(Math.max(0, lineIdx - 3), lineIdx + 3).join(' ')

    // Try to find a name near this email
    const nearbyName = names.find(n => {
      const ni = raw.toLowerCase().indexOf(n.toLowerCase())
      const ei = raw.toLowerCase().indexOf(email)
      return Math.abs(ni - ei) < 200
    }) || ''

    // Try to find a phone near this email
    const nearbyPhone = phones.find(p => {
      const pi = raw.indexOf(p.slice(0, 6))
      const ei = raw.indexOf(email)
      return Math.abs(pi - ei) < 300 && !used.phones.has(p)
    }) || ''
    if (nearbyPhone) used.phones.add(nearbyPhone)

    // LinkedIn near email
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

// ─── CSV Upload Zone ──────────────────────────────────────────────────────────
function UploadZone() {
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
      const res = await axios.post(`${API}/upload/recruiters`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed. Check file format.')
    }
    setUploading(false)
  }

  return (
    <div className="card" style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: '#185FA518', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className="ti ti-file-spreadsheet" style={{ fontSize: 18, color: '#185FA5' }} />
        </div>
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>CSV / Excel Upload</h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>recruiter_name, email, phone, email2, phone2, linkedin, specialization, notes</p>
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
        <div style={{ padding: '12px 16px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <i className="ti ti-circle-check" style={{ color: '#16a34a', fontSize: 16 }} />
            <span style={{ fontSize: 13, fontWeight: 500, color: '#15803d' }}>Upload successful!</span>
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
        <div style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
          <i className="ti ti-alert-circle" style={{ color: '#dc2626', fontSize: 15 }} />
          <span style={{ fontSize: 13, color: '#991b1b' }}>{error}</span>
        </div>
      )}
    </div>
  )
}

// ─── Paste & Parse ────────────────────────────────────────────────────────────
function PasteParser() {
  const [raw, setRaw] = useState('')
  const [parsed, setParsed] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState(null)

  const handleParse = () => {
    const results = parseText(raw)
    setParsed(results)
    setSaveResult(null)
  }

  const toggle = (id) => setParsed(p => p.map(r => r.id === id ? { ...r, selected: !r.selected } : r))
  const updateField = (id, field, val) => setParsed(p => p.map(r => r.id === id ? { ...r, [field]: val } : r))

  const handleSave = async () => {
    const toSave = parsed.filter(r => r.selected && r.email)
    if (!toSave.length) return
    setSaving(true)
    let inserted = 0, skipped = 0
    for (const r of toSave) {
      try {
        await axios.post(`${API}/recruiters/`, {
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
    <div className="card" style={{ padding: 24 }}>
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
        placeholder={`Paste anything here. Examples:\n\nHi, I'm John Smith from Brooksource.\nEmail: john.smith@brooksource.com\nPhone: 917-654-3210\n\n--- or ---\n\nSarah Lee | sarah@insightglobal.com | 888-555-2233\nhttps://linkedin.com/in/sarah-lee`}
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
          {parsed.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', background: 'var(--main-bg)', borderRadius: 8 }}>
              <i className="ti ti-search-off" style={{ fontSize: 24, color: 'var(--text-muted)', display: 'block', marginBottom: 8 }} />
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No emails found in the pasted text.</p>
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  Found <strong style={{ color: 'var(--text-primary)' }}>{parsed.length}</strong> contact{parsed.length !== 1 ? 's' : ''} — review and edit before saving
                </p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button onClick={() => setParsed(p => p.map(r => ({ ...r, selected: true })))}
                    style={{ fontSize: 11, padding: '4px 10px', border: '1px solid var(--card-border)', background: 'var(--main-bg)', color: 'var(--text-secondary)', borderRadius: 6, cursor: 'pointer' }}>
                    Select All
                  </button>
                  <button onClick={() => setParsed(p => p.map(r => ({ ...r, selected: false })))}
                    style={{ fontSize: 11, padding: '4px 10px', border: '1px solid var(--card-border)', background: 'var(--main-bg)', color: 'var(--text-secondary)', borderRadius: 6, cursor: 'pointer' }}>
                    Deselect All
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
                {parsed.map(r => (
                  <div key={r.id} style={{
                    border: `1px solid ${r.selected ? 'var(--accent)' : 'var(--card-border)'}`,
                    borderRadius: 10, padding: '14px 16px',
                    background: r.selected ? 'rgba(24,95,165,0.03)' : 'var(--main-bg)',
                    transition: 'all 0.15s',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                      <input type="checkbox" checked={r.selected} onChange={() => toggle(r.id)}
                        style={{ width: 15, height: 15, cursor: 'pointer', accentColor: 'var(--accent)' }} />
                      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)' }}>{r.email}</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                      {[
                        { key: 'recruiter_name', label: 'Full Name', placeholder: 'John Smith' },
                        { key: 'phone', label: 'Phone', placeholder: '9176543210' },
                        { key: 'email2', label: 'Email 2', placeholder: 'personal@gmail.com' },
                        { key: 'phone2', label: 'Phone 2', placeholder: 'alternate number' },
                        { key: 'specialization', label: 'Specialization', placeholder: 'IT Staffing' },
                        { key: 'linkedin', label: 'LinkedIn', placeholder: 'https://linkedin.com/in/...' },
                      ].map(({ key, label, placeholder }) => (
                        <div key={key}>
                          <label style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</label>
                          <input
                            value={r[key]}
                            onChange={e => updateField(r.id, key, e.target.value)}
                            placeholder={placeholder}
                            style={{ width: '100%', padding: '6px 10px', fontSize: 12, borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-primary)' }}
                          />
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <label style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Notes</label>
                      <input
                        value={r.notes}
                        onChange={e => updateField(r.id, 'notes', e.target.value)}
                        placeholder="Any extra info..."
                        style={{ width: '100%', padding: '6px 10px', fontSize: 12, borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-primary)' }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <button onClick={handleSave} disabled={saving || !parsed.some(r => r.selected)}
                className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '11px', opacity: parsed.some(r => r.selected) ? 1 : 0.5 }}>
                <i className="ti ti-database-import" style={{ fontSize: 14 }} />
                {saving ? 'Saving...' : `Save ${parsed.filter(r => r.selected).length} Recruiter${parsed.filter(r => r.selected).length !== 1 ? 's' : ''} to Database`}
              </button>

              {saveResult && (
                <div style={{ marginTop: 12, padding: '12px 16px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, display: 'flex', gap: 20, alignItems: 'center' }}>
                  <i className="ti ti-circle-check" style={{ color: '#16a34a', fontSize: 18 }} />
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 500, color: '#15803d' }}>Saved {saveResult.inserted} recruiter{saveResult.inserted !== 1 ? 's' : ''}!</p>
                    {saveResult.skipped > 0 && <p style={{ fontSize: 12, color: '#6b7280' }}>{saveResult.skipped} skipped (duplicate email)</p>}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function Upload() {
  const [tab, setTab] = useState('paste')

  return (
    <div className="page-enter">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>Add Recruiters</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Paste raw text or upload a CSV / Excel file</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: 'var(--main-bg)', padding: 4, borderRadius: 10, width: 'fit-content', border: '1px solid var(--card-border)' }}>
        {[
          { id: 'paste', label: 'Paste & Parse', icon: 'ti-clipboard-text' },
          { id: 'csv',   label: 'CSV / Excel',   icon: 'ti-file-spreadsheet' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{
              padding: '7px 16px', borderRadius: 7, fontSize: 13, fontWeight: 500,
              background: tab === t.id ? 'var(--card-bg)' : 'transparent',
              color: tab === t.id ? 'var(--text-primary)' : 'var(--text-muted)',
              border: tab === t.id ? '1px solid var(--card-border)' : '1px solid transparent',
              boxShadow: tab === t.id ? 'var(--shadow)' : 'none',
              display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.15s',
            }}>
            <i className={`ti ${t.icon}`} style={{ fontSize: 14 }} /> {t.label}
          </button>
        ))}
      </div>

      <div style={{ maxWidth: 780 }}>
        {tab === 'paste' ? <PasteParser /> : <UploadZone />}
      </div>
    </div>
  )
}
