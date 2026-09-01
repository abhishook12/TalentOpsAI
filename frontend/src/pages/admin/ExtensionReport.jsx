import { useState, useEffect, useCallback } from 'react'
import api from '../../services/api'

export default function ExtensionReport() {
  const [days, setDays] = useState(7)
  const [report, setReport] = useState(null)
  const [codes, setCodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [codeLoading, setCodeLoading] = useState(false)
  const [newCodeLabel, setNewCodeLabel] = useState('')
  const [tab, setTab] = useState('overview') // overview | devices | codes
  const [showInstallModal, setShowInstallModal] = useState(false)
  const [copiedCode, setCopiedCode] = useState(false)

  const fetchReport = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get(`/recruiters/extension/report?days=${days}`)
      setReport(res.data)
    } catch (e) {
      console.error('Report fetch error:', e)
    } finally {
      setLoading(false)
    }
  }, [days])

  const fetchCodes = useCallback(async () => {
    try {
      const res = await api.get('/recruiters/extension/codes')
      setCodes(res.data || [])
    } catch (e) {
      console.error('Codes fetch error:', e)
    }
  }, [])

  useEffect(() => { fetchReport() }, [fetchReport])
  useEffect(() => { fetchCodes() }, [fetchCodes])

  const createCode = async () => {
    setCodeLoading(true)
    try {
      await api.post('/recruiters/extension/codes', {
        label: newCodeLabel || `Code ${new Date().toLocaleDateString()}`,
        max_uses: -1,
      })
      setNewCodeLabel('')
      await fetchCodes()
    } catch (e) {
      console.error(e)
    } finally {
      setCodeLoading(false)
    }
  }

  const revokeCode = async (id) => {
    try {
      await api.delete(`/recruiters/extension/codes/${id}`)
      await fetchCodes()
    } catch (e) {
      console.error(e)
    }
  }

  const handleDownloadAndInstall = () => {
    // Trigger download
    const downloadUrl = 'https://talentopsai-1.onrender.com/recruiters/extension/download'
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = 'talentops-scout-extension.zip'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)

    setShowInstallModal(true)
  }

  const activeCode = codes.find(c => c.is_active)?.code || 'TALENTOPS-UUL8MORQ'

  return (
    <div style={{ padding: '24px', maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            🧩 Extension Activity Report
          </h1>
          <p style={{ color: 'var(--text-secondary)', margin: '4px 0 0', fontSize: 13 }}>
            Universal Scout activity from all installed extension instances
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            onClick={handleDownloadAndInstall}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 700,
              background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)',
              color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
              boxShadow: '0 2px 10px rgba(99, 102, 241, 0.35)',
            }}
          >
            <span>⚡ 1-Click Install Extension</span>
          </button>
          <div style={{ display: 'flex', gap: 4, background: 'var(--surface-2)', padding: 3, borderRadius: 8 }}>
            {[7, 14, 30, 90].map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
                style={{
                  padding: '5px 12px', borderRadius: 6, border: 'none', fontSize: 12, fontWeight: 600,
                  background: days === d ? 'var(--brand)' : 'transparent',
                  color: days === d ? '#fff' : 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 1-Click Installation Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(56, 189, 248, 0.08) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: 12, padding: '16px 20px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            fontSize: 24, background: 'rgba(99, 102, 241, 0.2)', width: 44, height: 44,
            borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            📡
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              Add Talent Scout to your Browser
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              Passively enriches your database with verified recruiters from LinkedIn, Gmail, and job sites as you browse.
            </div>
          </div>
        </div>
        <button
          onClick={handleDownloadAndInstall}
          style={{
            padding: '8px 18px', background: 'var(--brand)', color: '#fff', border: 'none',
            borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap',
          }}
        >
          Download & Setup
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 2, borderBottom: '1px solid var(--border)', marginBottom: 24 }}>
        {['overview', 'devices', 'codes'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '8px 18px', border: 'none', background: 'none', fontSize: 13,
              fontWeight: tab === t ? 700 : 400,
              color: tab === t ? 'var(--brand)' : 'var(--text-secondary)',
              borderBottom: tab === t ? '2px solid var(--brand)' : '2px solid transparent',
              cursor: 'pointer', textTransform: 'capitalize',
            }}
          >
            {t === 'codes' ? 'Activation Codes' : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {loading && (
        <div style={{ color: 'var(--text-secondary)', fontSize: 13, textAlign: 'center', padding: 40 }}>
          Loading report...
        </div>
      )}

      {!loading && report && tab === 'overview' && (
        <>
          {/* Totals */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 28 }}>
            {[
              { label: 'Contacts Accepted', val: report.totals.accepted, color: '#22c55e' },
              { label: 'Duplicates Skipped', val: report.totals.duplicates, color: '#f59e0b' },
              { label: 'Total Received', val: report.totals.received, color: '#6366f1' },
            ].map(s => (
              <div key={s.label} style={{
                background: 'var(--surface-1)', borderRadius: 12, padding: '20px 24px',
                border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: s.color }}>
                  {s.val.toLocaleString()}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Daily Breakdown */}
          <div style={{
            background: 'var(--surface-1)', borderRadius: 12, border: '1px solid var(--border)',
            padding: 20, marginBottom: 24,
          }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              Daily Activity
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ color: 'var(--text-secondary)', textAlign: 'left' }}>
                    {['Date', 'Received', 'Accepted', 'Duplicates', 'Active Devices'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', fontWeight: 600, fontSize: 12, borderBottom: '1px solid var(--border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.daily_summary.map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '10px 12px', color: 'var(--text-primary)', fontWeight: 500 }}>{row.day}</td>
                      <td style={{ padding: '10px 12px', color: '#6366f1' }}>{row.received}</td>
                      <td style={{ padding: '10px 12px', color: '#22c55e', fontWeight: 700 }}>{row.accepted}</td>
                      <td style={{ padding: '10px 12px', color: '#f59e0b' }}>{row.duplicates}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{row.active_devices}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Top Source Sites */}
          <div style={{
            background: 'var(--surface-1)', borderRadius: 12, border: '1px solid var(--border)', padding: 20,
          }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              Top Source Sites
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {report.top_source_sites.map((s, i) => (
                <div key={i} style={{
                  background: 'var(--surface-2)', borderRadius: 8, padding: '6px 14px',
                  fontSize: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <img src={`https://logos.hunter.io/${s.site}`} style={{ width: 14, height: 14, borderRadius: 3, objectFit: 'contain' }} alt="" />
                  <span>{s.site}</span>
                  <span style={{ color: '#22c55e', fontWeight: 700 }}>+{s.contacts}</span>
                </div>
              ))}
              {report.top_source_sites.length === 0 && (
                <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>No data yet</span>
              )}
            </div>
          </div>
        </>
      )}

      {!loading && report && tab === 'devices' && (
        <div style={{ background: 'var(--surface-1)', borderRadius: 12, border: '1px solid var(--border)', padding: 20 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
            {report.devices.length} Registered Device{report.devices.length !== 1 ? 's' : ''}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {report.devices.map((d, i) => (
              <div key={i} style={{
                background: 'var(--surface-2)', borderRadius: 10, padding: '14px 18px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                border: '1px solid var(--border)',
              }}>
                <div>
                  <div style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {d.device_id}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3 }}>
                    First seen: {d.first_seen?.slice(0, 19)} · Last active: {d.last_seen?.slice(0, 19)} · v{d.version || '?'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, alignItems: 'center', textAlign: 'right' }}>
                  <div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#22c55e' }}>{(d.total_accepted || 0).toLocaleString()}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>accepted</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#f59e0b' }}>{(d.total_duplicates || 0).toLocaleString()}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>dupes</div>
                  </div>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: d.is_active ? '#22c55e' : '#ef4444',
                  }} />
                </div>
              </div>
            ))}
            {report.devices.length === 0 && (
              <p style={{ color: 'var(--text-secondary)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
                No devices activated yet. Share an activation code below.
              </p>
            )}
          </div>
        </div>
      )}

      {tab === 'codes' && (
        <div>
          {/* Create Code */}
          <div style={{
            background: 'var(--surface-1)', borderRadius: 12, border: '1px solid var(--border)',
            padding: 20, marginBottom: 20,
          }}>
            <h3 style={{ margin: '0 0 14px', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              Create New Activation Code
            </h3>
            <div style={{ display: 'flex', gap: 10 }}>
              <input
                value={newCodeLabel}
                onChange={e => setNewCodeLabel(e.target.value)}
                placeholder='Label (e.g. "Shared with recruiting team")'
                style={{
                  flex: 1, padding: '9px 14px', background: 'var(--surface-2)',
                  border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 13,
                }}
              />
              <button
                onClick={createCode}
                disabled={codeLoading}
                style={{
                  padding: '9px 20px', background: 'var(--brand)', color: '#fff',
                  border: 'none', borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer',
                }}
              >
                {codeLoading ? 'Creating…' : '+ Generate Code'}
              </button>
            </div>
          </div>

          {/* Code list */}
          <div style={{ background: 'var(--surface-1)', borderRadius: 12, border: '1px solid var(--border)', padding: 20 }}>
            <h3 style={{ margin: '0 0 14px', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              Your Activation Codes
            </h3>
            {codes.length === 0 && (
              <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>No codes yet. Generate one above.</p>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {codes.map(c => (
                <div key={c.id} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  background: 'var(--surface-2)', borderRadius: 10, padding: '12px 16px',
                  border: `1px solid ${c.is_active ? 'var(--border)' : '#ef444422'}`,
                  opacity: c.is_active ? 1 : 0.55,
                }}>
                  <div>
                    <div style={{ fontFamily: 'monospace', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: 1 }}>
                      {c.code}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                      {c.label} · Used {c.use_count}/{c.max_uses === -1 ? '∞' : c.max_uses} times
                      {c.expires_at ? ` · Expires ${c.expires_at.slice(0, 10)}` : ''}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => navigator.clipboard.writeText(c.code)}
                      style={{
                        padding: '5px 12px', background: 'var(--surface-1)', border: '1px solid var(--border)',
                        borderRadius: 6, fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer',
                      }}
                    >
                      Copy
                    </button>
                    {c.is_active && (
                      <button
                        onClick={() => revokeCode(c.id)}
                        style={{
                          padding: '5px 12px', background: '#ef444411', border: '1px solid #ef444433',
                          borderRadius: 6, fontSize: 12, color: '#ef4444', cursor: 'pointer',
                        }}
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 1-Click Setup Modal */}
      {showInstallModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: 20,
        }}>
          <div style={{
            background: '#0f172a', border: '1px solid #334155', borderRadius: 16, maxWidth: 520, width: '100%',
            padding: 24, boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#f8fafc' }}>
                  🚀 3-Step Quick Setup Guide
                </h2>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: '#94a3b8' }}>
                  Your extension ZIP package is downloading automatically.
                </p>
              </div>
              <button
                onClick={() => setShowInstallModal(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: 18, cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, margin: '20px 0' }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{
                  background: '#6366f1', color: '#fff', width: 26, height: 26, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12, flexShrink: 0,
                }}>
                  1
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>Unzip the Package</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>Right-click <code>talentops-scout-extension.zip</code> and extract/unzip it.</div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{
                  background: '#38bdf8', color: '#fff', width: 26, height: 26, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12, flexShrink: 0,
                }}>
                  2
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>Open Chrome Extensions</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>Navigate to <code>chrome://extensions/</code> and enable <b>Developer mode</b> (top right).</div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{
                  background: '#4ade80', color: '#090d16', width: 26, height: 26, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12, flexShrink: 0,
                }}>
                  3
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>Load Unpacked</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>Click <b>Load unpacked</b> and select the unzipped folder.</div>
                </div>
              </div>
            </div>

            {/* Activation Code Copy Box */}
            <div style={{
              background: '#1e293b', border: '1px solid #334155', borderRadius: 10, padding: 14,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div>
                <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600 }}>
                  Your Activation Code
                </div>
                <div style={{ fontSize: 14, fontFamily: 'monospace', fontWeight: 700, color: '#4ade80', marginTop: 2 }}>
                  {activeCode}
                </div>
              </div>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(activeCode)
                  setCopiedCode(true)
                  setTimeout(() => setCopiedCode(false), 2000)
                }}
                style={{
                  padding: '6px 14px', background: copiedCode ? '#22c55e' : '#6366f1', color: '#fff',
                  border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 700, cursor: 'pointer',
                }}
              >
                {copiedCode ? '✓ Copied!' : 'Copy Code'}
              </button>
            </div>

            <div style={{ marginTop: 20, textAlign: 'right' }}>
              <button
                onClick={() => setShowInstallModal(false)}
                style={{
                  padding: '9px 20px', background: '#334155', color: '#f8fafc', border: 'none',
                  borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
