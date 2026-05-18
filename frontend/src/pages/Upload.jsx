import { useState, useRef } from 'react'
import axios from 'axios'

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

function UploadZone({ type, label, icon, color, accept }) {
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
      const res = await axios.post(`${API}/upload/${type}`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed. Check file format.')
    }
    setUploading(false)
  }

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) doUpload(file)
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #e8edf4', borderRadius: 12, padding: 28, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: color + '18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className={`ti ${icon}`} style={{ fontSize: 20, color }} />
        </div>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: '#0f172a' }}>Upload {label}</h2>
          <p style={{ fontSize: 12, color: '#94a3b8' }}>CSV or Excel (.xlsx)</p>
        </div>
      </div>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragging ? color : '#e2e8f0'}`,
          borderRadius: 10, padding: '36px 24px', textAlign: 'center',
          cursor: 'pointer', transition: 'all 0.15s',
          background: dragging ? color + '06' : '#fafafa',
          marginBottom: 16,
        }}>
        <i className="ti ti-cloud-upload" style={{ fontSize: 32, color: dragging ? color : '#cbd5e1', display: 'block', marginBottom: 10 }} />
        <p style={{ fontSize: 14, color: '#64748b', marginBottom: 4 }}>
          {uploading ? 'Uploading...' : 'Drop file here or click to browse'}
        </p>
        <p style={{ fontSize: 12, color: '#94a3b8' }}>Supports .csv and .xlsx</p>
        <input ref={inputRef} type="file" accept={accept} style={{ display: 'none' }} onChange={e => doUpload(e.target.files[0])} />
      </div>

      {/* Result */}
      {result && (
        <div style={{ padding: '14px 16px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <i className="ti ti-circle-check" style={{ color: '#16a34a', fontSize: 18 }} />
            <span style={{ fontSize: 13, fontWeight: 500, color: '#15803d' }}>Upload successful!</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
            {[
              { label: 'Total Rows', value: result.total_rows },
              { label: 'Inserted', value: result.inserted },
              { label: 'Duplicates Skipped', value: result.duplicates_skipped },
            ].map(({ label, value }) => (
              <div key={label} style={{ background: '#fff', borderRadius: 6, padding: '10px 12px', textAlign: 'center' }}>
                <p style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>{value}</p>
                <p style={{ fontSize: 11, color: '#64748b' }}>{label}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div style={{ padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <i className="ti ti-alert-circle" style={{ color: '#dc2626', fontSize: 16 }} />
          <span style={{ fontSize: 13, color: '#991b1b' }}>{error}</span>
        </div>
      )}

      {/* Format guide */}
      <div style={{ marginTop: 16, padding: '12px 14px', background: '#f8fafc', borderRadius: 8, border: '1px solid #f1f5f9' }}>
        <p style={{ fontSize: 11, fontWeight: 500, color: '#64748b', marginBottom: 6 }}>Required columns:</p>
        <p style={{ fontSize: 11, color: '#94a3b8', fontFamily: 'monospace' }}>
          {type === 'candidates'
            ? 'candidate_name, email, phone, visa_status, skills, experience_years, location, rate_per_hour, availability'
            : 'recruiter_name, email, phone, specialization'}
        </p>
      </div>
    </div>
  )
}

export default function Upload() {
  return (
    <div className="page-enter">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, color: '#0f172a', letterSpacing: '-0.02em', marginBottom: 4 }}>ETL Upload</h1>
        <p style={{ fontSize: 13, color: '#94a3b8' }}>Bulk import candidates or recruiters from CSV / Excel files</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <UploadZone
          type="candidates"
          label="Candidates"
          icon="ti-user-check"
          color="#0F6E56"
          accept=".csv,.xlsx"
        />
        <UploadZone
          type="recruiters"
          label="Recruiters"
          icon="ti-users"
          color="#185FA5"
          accept=".csv,.xlsx"
        />
      </div>
    </div>
  )
}
