import { useState, useRef, useCallback, useEffect } from 'react'
import axios from 'axios'
import JobsHistory from '../components/JobsHistory'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

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

// ─── Logical Field Labels ─────────────────────────────────────────────────────
const FIELD_LABELS = {
  name: 'Name', email: 'Email', email2: 'Alt Email', phone: 'Phone',
  phone2: 'Alt Phone', company: 'Company', location: 'Location', state: 'State',
  linkedin: 'LinkedIn', title: 'Title / Role', specialization: 'Specialization', notes: 'Notes',
}
const ALL_LOGICAL_FIELDS = Object.keys(FIELD_LABELS)

// ─── Smart Upload Zone ────────────────────────────────────────────────────────
function SmartUploadZone() {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)
  const [step, setStep] = useState('idle')       // idle | uploading | analyzing | preview | importing | done | error
  const [progress, setProgress] = useState(0)
  const [analysis, setAnalysis] = useState(null)  // AnalyzeResponse
  const [columnMap, setColumnMap] = useState({})  // editable mapping: logical → original
  const [importResult, setImportResult] = useState(null)
  const [error, setError] = useState(null)
  const [fileName, setFileName] = useState('')
  const [fileRef, setFileRef] = useState(null)    // keep file for re-upload on import
  const [activeJobId, setActiveJobId] = useState(null)
  const [activeJob, setActiveJob] = useState(null)

  const doAnalyze = useCallback(async (file) => {
    if (!file) return
    setFileName(file.name)
    setFileRef(file)
    setStep('uploading')
    setProgress(0)
    setError(null)
    setAnalysis(null)
    setImportResult(null)

    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await axios.post(`${API}/upload/analyze`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 100))
        },
      })
      setAnalysis(res.data)
      setColumnMap(res.data.column_map || {})
      setStep('preview')
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed. Check file format.')
      setStep('error')
    }
  }, [])

  const doImport = useCallback(async () => {
    if (!fileRef) return
    setStep('importing')
    setProgress(0)

    const fd = new FormData()
    fd.append('file', fileRef)
    try {
      const res = await axios.post(`${API}/upload/smart-import-async`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 100))
        },
      })
      setImportResult({ message: 'Job Queued!', job_id: res.data.job_id })
      setActiveJobId(res.data.job_id)
      setStep('tracking')
    } catch (e) {
      setError(e.response?.data?.detail || 'Import failed.')
      setStep('error')
    }
  }, [fileRef])

  const reset = () => {
    setStep('idle'); setProgress(0); setAnalysis(null); setColumnMap({});
    setImportResult(null); setError(null); setFileName(''); setFileRef(null);
    setActiveJobId(null); setActiveJob(null);
    if (inputRef.current) inputRef.current.value = ''
  }

  useEffect(() => {
    let interval;
    if (step === 'tracking' && activeJobId) {
      const poll = async () => {
        try {
          const res = await axios.get(`${API}/upload/jobs/${activeJobId}`);
          setActiveJob(res.data);
          if (res.data.status === 'completed' || res.data.status === 'failed') {
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Failed to poll job status', err);
        }
      };
      poll(); // initial
      interval = setInterval(poll, 1500);
    }
    return () => clearInterval(interval);
  }, [step, activeJobId]);

  const updateMapping = (logical, newCol) => {
    setColumnMap(prev => ({ ...prev, [logical]: newCol }))
  }

  // ── Render ──
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: 'linear-gradient(135deg, #185FA520, #534AB720)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <i className="ti ti-brain" style={{ fontSize: 20, color: '#534AB7' }} />
          </div>
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Smart Upload</h2>
            <p style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
              AI‑assisted column detection • auto‑mapping • validation
            </p>
          </div>
        </div>
        {step !== 'idle' && (
          <button onClick={reset} style={{
            padding: '6px 14px', fontSize: 11, borderRadius: 7,
            background: 'var(--main-bg)', border: '1px solid var(--card-border)',
            color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <i className="ti ti-refresh" style={{ fontSize: 13 }} /> Reset
          </button>
        )}
      </div>

      <div style={{ padding: '20px 24px 24px' }}>
        {/* ── STEP: Idle – Drag & Drop ── */}
        {step === 'idle' && (
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); doAnalyze(e.dataTransfer.files[0]) }}
            style={{
              border: `2px dashed ${dragging ? '#534AB7' : 'var(--card-border)'}`,
              borderRadius: 14, padding: '48px 24px', textAlign: 'center', cursor: 'pointer',
              background: dragging ? 'rgba(83,74,183,0.04)' : 'var(--main-bg)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: 56, height: 56, borderRadius: 16, margin: '0 auto 16px',
              background: 'linear-gradient(135deg, #185FA518, #534AB718)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <i className="ti ti-cloud-upload" style={{ fontSize: 26, color: dragging ? '#534AB7' : 'var(--text-muted)' }} />
            </div>
            <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>
              Drop your recruiter sheet here
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
              or click to browse • Supports .csv, .xlsx, .xls
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
              {['Auto column detection', 'Duplicate check', 'Validation', 'Preview before import'].map(tag => (
                <span key={tag} style={{
                  padding: '4px 10px', fontSize: 10, borderRadius: 20,
                  background: 'rgba(83,74,183,0.08)', color: '#534AB7', fontWeight: 500,
                }}>{tag}</span>
              ))}
            </div>
            <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" style={{ display: 'none' }}
              onChange={e => doAnalyze(e.target.files[0])} />
          </div>
        )}

        {/* ── STEP: Uploading / Analyzing ── */}
        {(step === 'uploading' || step === 'analyzing') && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <div style={{ position: 'relative', width: 64, height: 64, margin: '0 auto 20px' }}>
              <div style={{
                width: 64, height: 64, borderRadius: '50%',
                border: '3px solid var(--card-border)', borderTopColor: '#534AB7',
                animation: 'spin 1s linear infinite',
              }} />
              <i className="ti ti-file-analytics" style={{
                position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                fontSize: 22, color: '#534AB7',
              }} />
            </div>
            <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 6 }}>
              {step === 'uploading' ? 'Uploading file...' : 'Analyzing data...'}
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>{fileName}</p>
            {/* Progress bar */}
            <div style={{ maxWidth: 320, margin: '0 auto', height: 6, background: 'var(--card-border)', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${progress}%`,
                background: 'linear-gradient(90deg, #185FA5, #534AB7)',
                borderRadius: 99, transition: 'width 0.3s ease',
              }} />
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>{progress}%</p>
          </div>
        )}

        {/* ── STEP: Importing ── */}
        {step === 'importing' && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <div style={{ position: 'relative', width: 64, height: 64, margin: '0 auto 20px' }}>
              <div style={{
                width: 64, height: 64, borderRadius: '50%',
                border: '3px solid var(--card-border)', borderTopColor: '#0F6E56',
                animation: 'spin 1s linear infinite',
              }} />
              <i className="ti ti-database-import" style={{
                position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                fontSize: 22, color: '#0F6E56',
              }} />
            </div>
            <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 6 }}>
              Importing to database...
            </p>
            <div style={{ maxWidth: 320, margin: '0 auto', height: 6, background: 'var(--card-border)', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${progress}%`,
                background: 'linear-gradient(90deg, #0F6E56, #185FA5)',
                borderRadius: 99, transition: 'width 0.3s ease',
              }} />
            </div>
          </div>
        )}

        {/* ── STEP: Preview ── */}
        {step === 'preview' && analysis && (
          <div>
            {/* Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 20 }}>
              {[
                { label: 'Total Rows', value: analysis.total_rows, icon: 'ti-table', color: '#185FA5' },
                { label: 'Duplicates', value: analysis.duplicates, icon: 'ti-copy', color: '#BA7517' },
                { label: 'Invalid Emails', value: analysis.invalid_emails, icon: 'ti-mail-off', color: '#C4394A' },
                { label: 'Missing Email', value: analysis.missing_fields, icon: 'ti-alert-triangle', color: '#D97706' },
              ].map(c => (
                <div key={c.label} style={{
                  background: 'var(--main-bg)', border: '1px solid var(--card-border)', borderRadius: 10,
                  padding: '14px 14px', borderLeft: `3px solid ${c.color}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 6 }}>
                    <i className={`ti ${c.icon}`} style={{ fontSize: 13, color: c.color }} />
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.03em' }}>{c.label}</span>
                  </div>
                  <p style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>{c.value?.toLocaleString()}</p>
                </div>
              ))}
            </div>

            {/* Extra info pills */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
              {analysis.invalid_phones > 0 && (
                <span style={{ padding: '4px 10px', fontSize: 11, borderRadius: 20, background: 'rgba(196,57,74,0.1)', color: '#C4394A', fontWeight: 500 }}>
                  <i className="ti ti-phone-off" style={{ fontSize: 12, marginRight: 4 }} />{analysis.invalid_phones} invalid phones
                </span>
              )}
              {(analysis.empty_columns?.length || 0) > 0 && (
                <span style={{ padding: '4px 10px', fontSize: 11, borderRadius: 20, background: 'rgba(186,117,23,0.1)', color: '#BA7517', fontWeight: 500 }}>
                  <i className="ti ti-column-remove" style={{ fontSize: 12, marginRight: 4 }} />{analysis.empty_columns.length} empty columns
                </span>
              )}
              {analysis.corrupted_rows > 0 && (
                <span style={{ padding: '4px 10px', fontSize: 11, borderRadius: 20, background: 'rgba(196,57,74,0.1)', color: '#C4394A', fontWeight: 500 }}>
                  <i className="ti ti-alert-circle" style={{ fontSize: 12, marginRight: 4 }} />{analysis.corrupted_rows} blank rows
                </span>
              )}
            </div>

            {/* Column Mapping Table */}
            <div style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                <i className="ti ti-arrows-exchange" style={{ fontSize: 15, color: '#534AB7' }} />
                Detected Column Mapping
              </h3>
              <div style={{ border: '1px solid var(--card-border)', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{
                  display: 'grid', gridTemplateColumns: '1fr 1fr 40px', gap: 0,
                  padding: '8px 14px', background: 'var(--main-bg)',
                  borderBottom: '1px solid var(--card-border)',
                  fontSize: 10, fontWeight: 600, color: 'var(--text-muted)',
                  textTransform: 'uppercase', letterSpacing: '0.05em',
                }}>
                  <span>Database Field</span>
                  <span>Mapped Column</span>
                  <span></span>
                </div>
                {ALL_LOGICAL_FIELDS.map(logical => {
                  const mapped = columnMap[logical]
                  const headers = analysis.original_headers || []
                  return (
                    <div key={logical} style={{
                      display: 'grid', gridTemplateColumns: '1fr 1fr 40px', gap: 0,
                      padding: '8px 14px', borderBottom: '1px solid var(--card-border)',
                      alignItems: 'center',
                    }}>
                      <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
                        {FIELD_LABELS[logical]}
                      </span>
                      <select
                        value={mapped || ''}
                        onChange={e => updateMapping(logical, e.target.value || undefined)}
                        style={{
                          padding: '5px 8px', fontSize: 12, borderRadius: 6,
                          border: '1px solid var(--card-border)', background: 'var(--card-bg)',
                          color: mapped ? 'var(--text-primary)' : 'var(--text-muted)',
                          cursor: 'pointer', width: '100%',
                        }}
                      >
                        <option value="">— Not mapped —</option>
                        {headers.map(h => (
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                      {mapped ? (
                        <i className="ti ti-circle-check" style={{ fontSize: 16, color: '#0F6E56', textAlign: 'center' }} />
                      ) : (
                        <i className="ti ti-circle-minus" style={{ fontSize: 16, color: 'var(--text-muted)', textAlign: 'center', opacity: 0.4 }} />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Preview Table */}
            <div style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                <i className="ti ti-eye" style={{ fontSize: 15, color: '#185FA5' }} />
                Data Preview
                <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 4 }}>(first 10 rows)</span>
              </h3>
              <div style={{ overflowX: 'auto', border: '1px solid var(--card-border)', borderRadius: 10 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5 }}>
                  <thead>
                    <tr style={{ background: 'var(--main-bg)' }}>
                      <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--card-border)' }}>#</th>
                      {(analysis.original_headers || []).slice(0, 8).map(h => (
                        <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--card-border)', whiteSpace: 'nowrap' }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(analysis.preview || []).map((row, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--card-border)' }}>
                        <td style={{ padding: '7px 10px', color: 'var(--text-muted)', fontWeight: 500 }}>{i + 1}</td>
                        {(analysis.original_headers || []).slice(0, 8).map(h => (
                          <td key={h} style={{ padding: '7px 10px', color: 'var(--text-primary)', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {row[h] || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Import Button */}
            <button onClick={doImport} className="btn-primary" style={{
              width: '100%', justifyContent: 'center', padding: '12px',
              background: 'linear-gradient(135deg, #185FA5, #534AB7)',
              fontSize: 14, fontWeight: 600, borderRadius: 10,
            }}>
              <i className="ti ti-database-import" style={{ fontSize: 16, marginRight: 6 }} />
              Confirm & Import {analysis.total_rows?.toLocaleString()} Rows
            </button>
          </div>
        )}

        {/* ── STEP: Tracking ── */}
        {step === 'tracking' && activeJob && (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            {activeJob.status === 'processing' || activeJob.status === 'queued' ? (
              <div style={{ position: 'relative', width: 64, height: 64, margin: '0 auto 20px' }}>
                <div style={{
                  width: 64, height: 64, borderRadius: '50%',
                  border: '3px solid var(--card-border)', borderTopColor: '#0F6E56',
                  animation: 'spin 1s linear infinite',
                }} />
                <i className="ti ti-loader" style={{
                  position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                  fontSize: 22, color: '#0F6E56',
                }} />
              </div>
            ) : activeJob.status === 'failed' ? (
              <div style={{
                width: 64, height: 64, borderRadius: '50%', margin: '0 auto 16px',
                background: 'rgba(196,57,74,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <i className="ti ti-x" style={{ fontSize: 32, color: '#C4394A' }} />
              </div>
            ) : (
              <div style={{
                width: 64, height: 64, borderRadius: '50%', margin: '0 auto 16px',
                background: 'rgba(15,110,86,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <i className="ti ti-check" style={{ fontSize: 32, color: '#0F6E56' }} />
              </div>
            )}
            
            <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, textTransform: 'capitalize' }}>
              Import {activeJob.status}
            </p>
            
            <div style={{ maxWidth: 360, margin: '0 auto 20px', textAlign: 'left', background: 'var(--main-bg)', padding: 16, borderRadius: 12, border: '1px solid var(--card-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Progress</span>
                <span style={{ fontSize: 13, fontWeight: 600 }}>
                  {activeJob.total_rows > 0 ? Math.round((activeJob.processed_rows / activeJob.total_rows) * 100) : 0}%
                </span>
              </div>
              <div style={{ height: 6, background: 'var(--card-border)', borderRadius: 99, overflow: 'hidden', marginBottom: 16 }}>
                <div style={{
                  height: '100%', width: `${activeJob.total_rows > 0 ? (activeJob.processed_rows / activeJob.total_rows) * 100 : 0}%`,
                  background: activeJob.status === 'failed' ? '#C4394A' : 'linear-gradient(90deg, #0F6E56, #185FA5)',
                  borderRadius: 99, transition: 'width 0.3s ease',
                }} />
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Processed</div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>{activeJob.processed_rows} / {activeJob.total_rows}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Inserted</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: '#0F6E56' }}>{activeJob.inserted_rows}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Skipped (Dupes)</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: '#BA7517' }}>{activeJob.skipped_rows}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Errors</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: '#C4394A' }}>{activeJob.error_count}</div>
                </div>
              </div>
            </div>

            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
              {activeJob.status === 'completed' 
                ? 'Your data has been successfully imported into the database.' 
                : activeJob.status === 'failed'
                  ? 'There was an issue processing the file.'
                  : 'Your file is currently processing. You can safely navigate away.'}
            </p>
            
            {(activeJob.status === 'completed' || activeJob.status === 'failed') && (
              <button onClick={reset} className="btn-primary" style={{
                marginTop: 16, padding: '10px 28px', background: 'var(--main-bg)',
                color: 'var(--text-primary)', border: '1px solid var(--card-border)',
              }}>
                <i className="ti ti-upload" style={{ fontSize: 14, marginRight: 5 }} />Upload Another File
              </button>
            )}
          </div>
        )}

        {/* ── STEP: Error ── */}
        {step === 'error' && (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%', margin: '0 auto 16px',
              background: 'rgba(196,57,74,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <i className="ti ti-alert-circle" style={{ fontSize: 28, color: '#C4394A' }} />
            </div>
            <p style={{ fontSize: 14, fontWeight: 500, color: '#C4394A', marginBottom: 8 }}>
              {error}
            </p>
            <button onClick={reset} style={{
              padding: '8px 20px', fontSize: 12, borderRadius: 8,
              background: 'var(--main-bg)', border: '1px solid var(--card-border)',
              color: 'var(--text-secondary)', cursor: 'pointer',
            }}>
              Try Again
            </button>
          </div>
        )}
      </div>

      {/* Spinner keyframe (inline) */}
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
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
          <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Legacy CSV / Excel Upload</h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Requires exact headers: recruiter_name, email, phone, email2, phone2, linkedin, specialization, notes</p>
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
                <div style={{ marginTop: 12, padding: '12px 16px', background: 'rgba(15,110,86,0.08)', border: '1px solid rgba(15,110,86,0.2)', borderRadius: 8, display: 'flex', gap: 20, alignItems: 'center' }}>
                  <i className="ti ti-circle-check" style={{ color: '#0F6E56', fontSize: 18 }} />
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 500, color: '#0F6E56' }}>Saved {saveResult.inserted} recruiter{saveResult.inserted !== 1 ? 's' : ''}!</p>
                    {saveResult.skipped > 0 && <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{saveResult.skipped} skipped (duplicate email)</p>}
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
  const [tab, setTab] = useState('smart')

  return (
    <div className="page-enter">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: 4 }}>Add Recruiters</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Smart upload with AI column detection, paste & parse, or legacy CSV upload</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: 'var(--main-bg)', padding: 4, borderRadius: 10, width: 'fit-content', border: '1px solid var(--card-border)' }}>
        {[
          { id: 'smart',   label: 'Smart Upload',   icon: 'ti-brain' },
          { id: 'history', label: 'Import History', icon: 'ti-history' },
          { id: 'paste',   label: 'Paste & Parse',  icon: 'ti-clipboard-text' },
          { id: 'csv',     label: 'Legacy Upload',  icon: 'ti-file-spreadsheet' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{
              padding: '7px 16px', borderRadius: 7, fontSize: 13, fontWeight: 500,
              background: tab === t.id ? 'var(--card-bg)' : 'transparent',
              color: tab === t.id ? 'var(--text-primary)' : 'var(--text-muted)',
              border: tab === t.id ? '1px solid var(--card-border)' : '1px solid transparent',
              boxShadow: tab === t.id ? 'var(--shadow)' : 'none',
              display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.15s',
              cursor: 'pointer',
            }}>
            <i className={`ti ${t.icon}`} style={{ fontSize: 14 }} /> {t.label}
          </button>
        ))}
      </div>

      <div style={{ maxWidth: 880 }}>
        {tab === 'smart' && <SmartUploadZone />}
        {tab === 'history' && <JobsHistory />}
        {tab === 'paste' && <PasteParser />}
        {tab === 'csv'   && <LegacyUploadZone />}
      </div>
    </div>
  )
}
