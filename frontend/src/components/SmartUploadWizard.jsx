import { useState, useRef, useEffect, useCallback } from 'react'
import api, { getErrorMessage, API } from '../services/api'

const FIELD_LABELS = {
  name: 'Name', email: 'Email', phone: 'Phone',
  company: 'Company', location: 'Location', state: 'State',
  linkedin: 'LinkedIn', title: 'Title / Role'
}
const ALL_LOGICAL_FIELDS = Object.keys(FIELD_LABELS)

function safeJsonParse(value) {
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

function buildLegacyPreview(analysis, mapping) {
  const seenEmails = new Set()
  const rows = (analysis.preview || []).map((row, index) => {
    const getValue = (field) => {
      const column = mapping[field]
      if (!column) return ''
      return String(row[column] ?? '').trim()
    }

    const email = getValue('email').toLowerCase()
    const name = getValue('name')
    const company = getValue('company')
    const state = getValue('state')
    const location = getValue('location')
    const phone = getValue('phone')
    const linkedin = getValue('linkedin')
    const issues = []
    let status = 'Ready'

    if (!email) {
      status = 'Error'
      issues.push('Missing email')
    } else if (!email.includes('@')) {
      status = 'Error'
      issues.push('Invalid email format')
    } else if (seenEmails.has(email)) {
      status = 'Duplicate'
      issues.push('Duplicate in file')
    } else {
      seenEmails.add(email)
    }

    if (!name) issues.push('Missing name')
    if (!company) issues.push('Missing company')
    if (!state && !location) issues.push('Missing state/location')

    return {
      row_id: `legacy-${index}`,
      index,
      name,
      email,
      phone,
      company,
      state,
      location,
      linkedin,
      status,
      issues,
    }
  })

  const totalRows = analysis.total_rows || rows.length
  const duplicateRows = analysis.duplicates || 0
  const missingFields = analysis.missing_fields || 0
  const invalidEmails = analysis.invalid_emails || 0
  const invalidPhones = analysis.invalid_phones || 0
  const errorRows = Math.max(missingFields, invalidEmails, invalidPhones)
  const validRows = Math.max(totalRows - duplicateRows - errorRows, 0)

  return {
    job: {
      status: 'preview',
      total_rows: totalRows,
      valid_rows: validRows,
      error_rows: errorRows,
      duplicate_rows: duplicateRows,
    },
    rows,
    pagination: {
      page: 1,
      limit: rows.length || 1,
      total: rows.length,
      pages: 1,
    },
  }
}

export default function SmartUploadWizard() {
  const inputRef = useRef()
  const [step, setStep] = useState('idle') // idle, uploading, mapping, validating, preview, importing, completed, error
  const [jobId, setJobId] = useState(null)
  const [fileName, setFileName] = useState('')
  const [error, setError] = useState(null)
  const [backendFlavor, setBackendFlavor] = useState('auto') // auto, new, legacy
  const [sourceFile, setSourceFile] = useState(null)
  
  // Mapping state
  const [headers, setHeaders] = useState([])
  const [sampleData, setSampleData] = useState([])
  const [columnMap, setColumnMap] = useState({})
  const [confidences, setConfidences] = useState({})
  
  // Preview state
  const [previewData, setPreviewData] = useState(null)
  const [page, setPage] = useState(1)
  
  const reset = () => {
    setStep('idle'); setJobId(null); setError(null); setColumnMap({}); setBackendFlavor('auto'); setSourceFile(null);
    setPreviewData(null); setHeaders([]); setSampleData([]); setConfidences({});
    if(inputRef.current) inputRef.current.value = ''
  }

  const parseWithNewEngine = async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/api/import/parse', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }

  const parseWithLegacyEngine = async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/upload/analyze', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }

  const handleFileUpload = async (file) => {
    if(!file) return
    setFileName(file.name)
    setSourceFile(file)
    setStep('uploading')
    setError(null)

    try {
      const res = await parseWithNewEngine(file)
      setBackendFlavor('new')
      setJobId(res.data.job_id)
      setHeaders(res.data.headers || [])
      setSampleData(res.data.sample_data || [])

      const newMap = {}
      const newConf = {}
      for (const [logical, details] of Object.entries(res.data.mapping_suggestions || {})) {
        newMap[logical] = details.column
        newConf[logical] = details.confidence
      }
      setColumnMap(newMap)
      setConfidences(newConf)
      setStep('mapping')
      return
    } catch (e) {
      console.warn('New smart import endpoint unavailable; falling back to legacy ETL.', e)
    }

    try {
      const res = await parseWithLegacyEngine(file)
      setBackendFlavor('legacy')
      setHeaders(res.data.original_headers || [])
      setSampleData(res.data.preview || [])
      setColumnMap(res.data.column_map || {})
      setConfidences(
        Object.fromEntries(
          Object.keys(res.data.column_map || {}).map((key) => [key, 100])
        )
      )
      setPreviewData(buildLegacyPreview(res.data, res.data.column_map || {}))
      setStep('preview')
    } catch (e) {
      setError(getErrorMessage(e, 'Failed to parse file with both import engines'))
      setStep('error')
    }
  }

  const startValidation = async () => {
    if (backendFlavor === 'legacy') {
      setStep('preview')
      return
    }
    setStep('validating')
    try {
      await api.post(`/api/import/validate/${jobId}`, { mapping: columnMap })
      pollPreview()
    } catch (e) {
      setError(getErrorMessage(e, 'Validation failed'))
      setStep('error')
    }
  }
  
  const pollPreview = async () => {
    const fetchPage = async () => {
      try {
        const res = await api.get(`/api/import/preview/${jobId}?page=${page}&limit=50`)
        if (res.data.job.status === 'validating') {
          setTimeout(fetchPage, 2000)
        } else {
          setPreviewData(res.data)
          setStep('preview')
        }
      } catch (e) {
        console.error(e)
      }
    }
    fetchPage()
  }
  
  useEffect(() => {
    if (step === 'preview') {
      // Re-fetch when page changes
        api.get(`/api/import/preview/${jobId}?page=${page}&limit=50`).then(res => setPreviewData(res.data))
    }
  }, [page, step, jobId])

  const commitImport = async () => {
    if (backendFlavor === 'legacy') {
      setStep('importing')
      setError(null)
      try {
        const fd = new FormData()
        fd.append('file', sourceFile)
        fd.append('mapping', JSON.stringify(columnMap))
        const res = await api.post('/upload/smart-import-async', fd, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        setJobId(res.data.job_id)
        pollLegacyCompletion(res.data.job_id)
      } catch (e) {
        setError(getErrorMessage(e, 'Commit failed'))
        setStep('error')
      }
      return
    }

    setStep('importing')
    try {
      await api.post(`/api/import/commit/${jobId}`)
      pollCompletion()
    } catch (e) {
      setError(getErrorMessage(e, 'Commit failed'))
      setStep('error')
    }
  }
  
  const pollCompletion = async () => {
    const fetchHistory = async () => {
      try {
        const res = await api.get(`/api/import/history`)
        const myJob = res.data.find(j => j.job_id === jobId)
        if (myJob && myJob.status === 'completed') {
          setStep('completed')
        } else if (myJob && myJob.status === 'importing') {
          setTimeout(fetchHistory, 2000)
        } else {
          setStep('completed')
        }
      } catch (e) {
        console.error(e)
      }
    }
    fetchHistory()
  }

  const pollLegacyCompletion = async (legacyJobId) => {
    const fetchStatus = async () => {
      try {
        const res = await api.get(`/upload/jobs/${legacyJobId}`)
        const job = res.data
        if (job.status === 'completed') {
          setStep('completed')
          return
        }
        if (job.status === 'failed') {
          const firstError = Array.isArray(job.errors) && job.errors[0]?.reason
          setError(firstError || 'The import failed on the server.')
          setStep('error')
          return
        }
        setTimeout(fetchStatus, 2000)
      } catch (e) {
        setError(getErrorMessage(e, 'Failed to check import status'))
        setStep('error')
      }
    }
    fetchStatus()
  }

  // --- RENDER HELPERS ---
  const renderStatusChip = (status) => {
    const colors = {
      'Ready': { bg: 'rgba(15,110,86,0.1)', color: '#0F6E56' },
      'Warning': { bg: 'rgba(186,117,23,0.1)', color: '#BA7517' },
      'Duplicate': { bg: 'rgba(186,117,23,0.1)', color: '#BA7517' },
      'Error': { bg: 'rgba(196,57,74,0.1)', color: '#C4394A' },
    }
    const style = colors[status] || { bg: '#eee', color: '#666' }
    return (
      <span style={{ padding: '4px 8px', borderRadius: 12, fontSize: 10, fontWeight: 600, background: style.bg, color: style.color }}>
        {status}
      </span>
    )
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
      {/* Header */}
      <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg, #185FA520, #534AB720)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <i className="ti ti-brain" style={{ fontSize: 20, color: '#534AB7' }} />
          </div>
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Smart Upload Engine</h2>
            <p style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>AI‑assisted column detection • Data Normalization • Duplicate Detection</p>
          </div>
        </div>
        {step !== 'idle' && (
           <button onClick={reset} style={{ padding: '6px 14px', fontSize: 11, borderRadius: 7, background: 'var(--main-bg)', border: '1px solid var(--card-border)', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}>
             <i className="ti ti-refresh" style={{ fontSize: 13 }} /> Reset
           </button>
        )}
      </div>

      <div style={{ padding: '20px 24px 24px' }}>
        
        {/* STEP 1: IDLE */}
        {step === 'idle' && (
          <div onClick={() => inputRef.current?.click()} style={{ border: '2px dashed var(--card-border)', borderRadius: 14, padding: '48px 24px', textAlign: 'center', cursor: 'pointer', background: 'var(--main-bg)', transition: 'all 0.2s' }}>
            <i className="ti ti-cloud-upload" style={{ fontSize: 32, color: 'var(--text-muted)', marginBottom: 12, display: 'block' }} />
            <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Drop your data file here</p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>Supports .csv, .xlsx, .xls (Up to 100k rows)</p>
            <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" style={{ display: 'none' }} onChange={e => handleFileUpload(e.target.files[0])} />
          </div>
        )}

        {/* STEP 2: MAPPING */}
        {step === 'mapping' && (
          <div>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Map Columns</h3>
            <div style={{ border: '1px solid var(--card-border)', borderRadius: 10, overflow: 'hidden', marginBottom: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 2fr 100px', gap: 10, padding: '10px 14px', background: 'var(--main-bg)', borderBottom: '1px solid var(--card-border)', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                <span>Database Field</span>
                <span>File Column</span>
                <span>Confidence</span>
              </div>
              {ALL_LOGICAL_FIELDS.map(logical => (
                <div key={logical} style={{ display: 'grid', gridTemplateColumns: '1.5fr 2fr 100px', gap: 10, padding: '10px 14px', borderBottom: '1px solid var(--card-border)', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{FIELD_LABELS[logical]}</span>
                  <select 
                    value={columnMap[logical] || ''}
                    onChange={e => setColumnMap({...columnMap, [logical]: e.target.value})}
                    style={{ padding: '6px', borderRadius: 6, border: '1px solid var(--card-border)', fontSize: 13, background: 'var(--card-bg)' }}
                  >
                    <option value="">— Skip —</option>
                    {headers.map(h => <option key={h} value={h}>{h}</option>)}
                  </select>
                  <div>
                    {confidences[logical] ? (
                       <span style={{ fontSize: 11, color: confidences[logical] > 80 ? '#0F6E56' : '#BA7517', fontWeight: 600 }}>{confidences[logical]}% Match</span>
                    ) : <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>—</span>}
                  </div>
                </div>
              ))}
            </div>
            
            <button onClick={startValidation} className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px' }}>
              Confirm & Start Validation
            </button>
          </div>
        )}

        {/* STEP 3: PREVIEW & VALIDATION */}
        {step === 'preview' && previewData && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
              <div style={{ padding: 16, background: 'var(--main-bg)', border: '1px solid var(--card-border)', borderRadius: 10, borderLeft: '4px solid #185FA5' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Total Rows</div>
                <div style={{ fontSize: 24, fontWeight: 700 }}>{previewData.job.total_rows}</div>
              </div>
              <div style={{ padding: 16, background: 'var(--main-bg)', border: '1px solid var(--card-border)', borderRadius: 10, borderLeft: '4px solid #0F6E56' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Valid</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#0F6E56' }}>{previewData.job.valid_rows}</div>
              </div>
              <div style={{ padding: 16, background: 'var(--main-bg)', border: '1px solid var(--card-border)', borderRadius: 10, borderLeft: '4px solid #C4394A' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Errors</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#C4394A' }}>{previewData.job.error_rows}</div>
              </div>
              <div style={{ padding: 16, background: 'var(--main-bg)', border: '1px solid var(--card-border)', borderRadius: 10, borderLeft: '4px solid #BA7517' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Duplicates</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#BA7517' }}>{previewData.job.duplicate_rows}</div>
              </div>
            </div>

            <div style={{ border: '1px solid var(--card-border)', borderRadius: 10, overflowX: 'auto', marginBottom: 20 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ background: 'var(--main-bg)', borderBottom: '1px solid var(--card-border)' }}>
                    <th style={{ padding: '10px', textAlign: 'left', fontWeight: 600 }}>Row</th>
                    <th style={{ padding: '10px', textAlign: 'left', fontWeight: 600 }}>Status</th>
                    <th style={{ padding: '10px', textAlign: 'left', fontWeight: 600 }}>Name</th>
                    <th style={{ padding: '10px', textAlign: 'left', fontWeight: 600 }}>Email</th>
                    <th style={{ padding: '10px', textAlign: 'left', fontWeight: 600 }}>Company</th>
                    <th style={{ padding: '10px', textAlign: 'left', fontWeight: 600 }}>State</th>
                    <th style={{ padding: '10px', textAlign: 'left', fontWeight: 600 }}>Issues</th>
                  </tr>
                </thead>
                <tbody>
                  {previewData.rows.map((r, i) => (
                    <tr key={r.row_id} style={{ borderBottom: '1px solid var(--card-border)' }}>
                      <td style={{ padding: '10px' }}>{r.index + 1}</td>
                      <td style={{ padding: '10px' }}>{renderStatusChip(r.status)}</td>
                      <td style={{ padding: '10px' }}>{r.name}</td>
                      <td style={{ padding: '10px' }}>{r.email}</td>
                      <td style={{ padding: '10px' }}>{r.company}</td>
                      <td style={{ padding: '10px' }}>{r.state}</td>
                      <td style={{ padding: '10px', color: '#C4394A', fontSize: 11 }}>{r.issues.join(', ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ padding: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--main-bg)' }}>
                <button disabled={page === 1} onClick={() => setPage(p => p-1)} className="btn-secondary" style={{ padding: '4px 12px' }}>Prev</button>
                <span style={{ fontSize: 12 }}>Page {page} of {previewData.pagination.pages}</span>
                <button disabled={page === previewData.pagination.pages} onClick={() => setPage(p => p+1)} className="btn-secondary" style={{ padding: '4px 12px' }}>Next</button>
              </div>
            </div>

            <button onClick={commitImport} className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px', background: 'linear-gradient(135deg, #185FA5, #534AB7)' }}>
              <i className="ti ti-database-import" style={{ marginRight: 8, fontSize: 18 }} />
              {backendFlavor === 'legacy' ? `Start Import (${previewData.job.total_rows} Rows)` : `Finalize Import (${previewData.job.valid_rows} Rows)`}
            </button>
            <div style={{ textAlign: 'center', marginTop: 12 }}>
              {backendFlavor === 'legacy' ? (
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Rejected row export is not available on the current backend.</span>
              ) : (
                <a href={`${API}/api/import/${jobId}/rejected`} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: 'var(--text-muted)', textDecoration: 'underline' }}>Download Rejected Rows</a>
              )}
            </div>
          </div>
        )}

        {/* LOADING STATES */}
        {(step === 'uploading' || step === 'validating' || step === 'importing') && (
           <div style={{ textAlign: 'center', padding: '40px 0' }}>
             <i className="ti ti-loader" style={{ fontSize: 40, color: '#534AB7', animation: 'spin 1s linear infinite', marginBottom: 16, display: 'block' }} />
             <p style={{ fontSize: 16, fontWeight: 500 }}>
               {step === 'uploading' ? 'Parsing File...' : step === 'validating' ? 'Validating Data (Checking for duplicates & normalizing)...' : 'Committing to Database...'}
             </p>
           </div>
        )}

        {/* COMPLETED */}
        {step === 'completed' && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
             <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(15,110,86,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
               <i className="ti ti-check" style={{ fontSize: 32, color: '#0F6E56' }} />
             </div>
             <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Import Successful!</p>
             <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>Your valid records have been ingested.</p>
             <button onClick={reset} className="btn-secondary" style={{ padding: '8px 24px' }}>Upload Another</button>
          </div>
        )}

        {/* ERROR */}
        {step === 'error' && (
           <div style={{ textAlign: 'center', padding: '40px 0' }}>
             <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(196,57,74,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
               <i className="ti ti-alert-triangle" style={{ fontSize: 32, color: '#C4394A' }} />
             </div>
             <p style={{ fontSize: 16, fontWeight: 500, color: '#C4394A', marginBottom: 16 }}>{error}</p>
             <button onClick={reset} className="btn-secondary" style={{ padding: '8px 24px' }}>Try Again</button>
           </div>
        )}

      </div>
    </div>
  )
}
