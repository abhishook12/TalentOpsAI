import { useState, useRef } from 'react'
import api, { getErrorMessage } from '../services/api'

export default function SmartUploadWizard() {
  const inputRef = useRef()
  const [step, setStep] = useState('idle') // idle, uploading, review, importing, completed, error
  const [jobId, setJobId] = useState(null)
  const [fileName, setFileName] = useState('')
  const [error, setError] = useState(null)
  const [sourceFile, setSourceFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  
  // Analysis state
  const [analysis, setAnalysis] = useState(null)
  const [activeSheetIdx, setActiveSheetIdx] = useState(0)
  
  const reset = () => {
    setStep('idle')
    setJobId(null)
    setError(null)
    setSourceFile(null)
    setAnalysis(null)
    setActiveSheetIdx(0)
    setUploadProgress(0)
    if(inputRef.current) inputRef.current.value = ''
  }

  const handleFileUpload = async (file) => {
    if(!file) return
    setFileName(file.name)
    setSourceFile(file)
    setStep('uploading')
    setUploadProgress(0)
    setError(null)

    const fd = new FormData()
    fd.append('file', file)

    try {
      const res = await api.post('/upload/analyze', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (event) => {
          if (event.total) setUploadProgress(Math.max(0, Math.min(100, Math.round((event.loaded / event.total) * 100))))
        }
      })
      setUploadProgress(100)
      setAnalysis(res.data)
      setStep('review')
    } catch (e) {
      setError(getErrorMessage(e, 'Failed to analyze file'))
      setStep('error')
    }
  }

  const startImport = async () => {
    setStep('importing')
    setError(null)
    try {
      const fd = new FormData()
      fd.append('file', sourceFile)
      
      const res = await api.post('/upload/smart-import-async', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setJobId(res.data.job_id)
      pollCompletion(res.data.job_id)
    } catch (e) {
      setError(getErrorMessage(e, 'Import failed to start'))
      setStep('error')
    }
  }

  const pollCompletion = async (currentJobId) => {
    const fetchStatus = async () => {
      try {
        const res = await api.get(`/upload/jobs/${currentJobId}`)
        const job = res.data
        if (job.status === 'completed' || job.status === 'mapping_failed') {
          if (job.status === 'mapping_failed') {
            setError(job.error_message || 'Import failed to map or insert any rows.')
            setStep('error')
          } else {
            setStep('completed')
          }
          return
        }
        if (job.status === 'failed') {
          let errStr = job.error_message || 'The import failed on the server.'
          if (job.errors && job.errors.length > 0) {
            errStr = job.errors[0]?.reason || errStr
          }
          setError(errStr)
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

  const activeSheet = analysis?.sheets?.[activeSheetIdx]

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
      {/* Header */}
      <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg, #185FA520, #534AB720)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <i className="ti ti-brain" style={{ fontSize: 20, color: '#534AB7' }} />
          </div>
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Adaptive ETL Engine</h2>
            <p style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>Multi-sheet Detection • Auto Mapping • Deduplication</p>
          </div>
        </div>
        {step !== 'idle' && (
           <button onClick={reset} style={{ padding: '6px 14px', fontSize: 11, borderRadius: 7, background: 'var(--main-bg)', border: '1px solid var(--card-border)', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}>
             <i className="ti ti-refresh" style={{ fontSize: 13 }} /> Reset
           </button>
        )}
      </div>

      <div style={{ padding: '20px 24px 24px' }}>
        {step === 'uploading' && (
          <div style={{ marginBottom: 18, padding: '12px 14px', borderRadius: 12, background: 'var(--main-bg)', border: '1px solid var(--card-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-primary)' }}>Uploading & Analyzing</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{uploadProgress}%</div>
            </div>
            <div style={{ height: 8, borderRadius: 999, background: 'rgba(148,163,184,0.18)', overflow: 'hidden' }}>
              <div style={{ width: `${uploadProgress}%`, height: '100%', borderRadius: 999, background: 'linear-gradient(90deg, #534AB7, #185FA5)' }} />
            </div>
            <div style={{ marginTop: 8, fontSize: 11.5, color: 'var(--text-muted)' }}>Parsing sheets and detecting formats...</div>
          </div>
        )}

        {/* STEP 1: IDLE */}
        {step === 'idle' && (
          <div onClick={() => inputRef.current?.click()} style={{ border: '2px dashed var(--card-border)', borderRadius: 14, padding: '48px 24px', textAlign: 'center', cursor: 'pointer', background: 'var(--main-bg)', transition: 'all 0.2s' }}>
            <i className="ti ti-cloud-upload" style={{ fontSize: 32, color: 'var(--text-muted)', marginBottom: 12, display: 'block' }} />
            <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Drop your data file here</p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>Supports .csv, .xlsx, .xls</p>
            <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" style={{ display: 'none' }} onChange={e => handleFileUpload(e.target.files[0])} />
          </div>
        )}

        {/* STEP 2: REVIEW (Multi-sheet) */}
        {step === 'review' && analysis && (
          <div>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12 }}>File Analysis Complete</h3>
            
            <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
              <div style={{ flex: 1, padding: 16, background: 'var(--main-bg)', border: '1px solid var(--card-border)', borderRadius: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Total Sheets</div>
                <div style={{ fontSize: 24, fontWeight: 700 }}>{analysis.sheet_count}</div>
              </div>
              <div style={{ flex: 1, padding: 16, background: 'var(--main-bg)', border: '1px solid var(--card-border)', borderRadius: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Total Rows</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#185FA5' }}>{analysis.total_rows}</div>
              </div>
            </div>

            <div style={{ border: '1px solid var(--card-border)', borderRadius: 10, overflow: 'hidden', marginBottom: 20 }}>
              {/* Sheet Tabs */}
              <div style={{ display: 'flex', borderBottom: '1px solid var(--card-border)', background: 'var(--main-bg)', overflowX: 'auto' }}>
                {analysis.sheets.map((sheet, idx) => (
                  <button 
                    key={idx}
                    onClick={() => setActiveSheetIdx(idx)}
                    style={{
                      padding: '12px 16px',
                      background: activeSheetIdx === idx ? 'var(--card-bg)' : 'transparent',
                      border: 'none',
                      borderBottom: activeSheetIdx === idx ? '2px solid #534AB7' : '2px solid transparent',
                      color: activeSheetIdx === idx ? 'var(--text-primary)' : 'var(--text-muted)',
                      fontWeight: activeSheetIdx === idx ? 600 : 500,
                      fontSize: 13,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {sheet.sheet_name} ({sheet.data_rows} rows)
                  </button>
                ))}
              </div>

              {/* Sheet Content */}
              {activeSheet && (
                <div style={{ padding: 20 }}>
                  <div style={{ display: 'flex', gap: 24, marginBottom: 20 }}>
                    <div>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Detected Format</span>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{activeSheet.detected_format}</span>
                    </div>
                    <div>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Confidence</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: activeSheet.format_confidence === 'high' ? '#0F6E56' : '#BA7517' }}>
                        {activeSheet.format_confidence.toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Blank Rows Skipped</span>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{activeSheet.blank_rows}</span>
                    </div>
                  </div>

                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>Column Mapping Preview</div>
                  <div style={{ overflowX: 'auto', border: '1px solid var(--card-border)', borderRadius: 8 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                      <thead>
                        <tr style={{ background: 'var(--main-bg)', borderBottom: '1px solid var(--card-border)' }}>
                          {Object.keys(activeSheet.column_map).map(logical => (
                            <th key={logical} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', borderRight: '1px solid var(--card-border)' }}>
                              {logical}
                            </th>
                          ))}
                        </tr>
                        <tr style={{ background: 'var(--card-bg)', borderBottom: '1px solid var(--card-border)' }}>
                          {Object.values(activeSheet.column_map).map((header, idx) => (
                            <th key={idx} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#185FA5', borderRight: '1px solid var(--card-border)' }}>
                              {header || <span style={{color: '#aaa'}}>—</span>}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {activeSheet.preview.slice(0, 3).map((row, rowIdx) => (
                          <tr key={rowIdx} style={{ borderBottom: '1px solid var(--card-border)' }}>
                            {Object.values(activeSheet.column_map).map((header, colIdx) => (
                              <td key={colIdx} style={{ padding: '8px 12px', borderRight: '1px solid var(--card-border)' }}>
                                {header && row[header] ? String(row[header]) : ''}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <button onClick={startImport} className="btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px', background: 'linear-gradient(135deg, #185FA5, #534AB7)' }}>
              <i className="ti ti-database-import" style={{ marginRight: 8, fontSize: 18 }} />
              Start Adaptive Import ({analysis.total_rows} Rows)
            </button>
          </div>
        )}

        {/* LOADING STATES */}
        {step === 'importing' && (
           <div style={{ textAlign: 'center', padding: '40px 0' }}>
             <i className="ti ti-loader" style={{ fontSize: 40, color: '#534AB7', animation: 'spin 1s linear infinite', marginBottom: 16, display: 'block' }} />
             <p style={{ fontSize: 16, fontWeight: 500 }}>
               Deduplicating and Committing Database...
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
             <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 24 }}>Your records have been ingested via the Adaptive Engine.</p>
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
