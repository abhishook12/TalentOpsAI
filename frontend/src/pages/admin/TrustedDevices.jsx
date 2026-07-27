import { useState, useEffect } from 'react'
import api from '../../services/api'
import { toast } from 'react-hot-toast'
import { ShieldCheck, ShieldAlert, MonitorSmartphone, MapPin, Activity, History, X, Search, ShieldX, Server, Check } from 'lucide-react'

export default function TrustedDevices() {
  const [devices, setDevices] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('Pending') // Default to Pending if it's the most actionable
  const [searchQuery, setSearchQuery] = useState('')

  const [sessions, setSessions] = useState([])
  const [selectedSessions, setSelectedSessions] = useState([])
  const [loadingSessions, setLoadingSessions] = useState(false)

  
  // Audit Modal
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [auditLogs, setAuditLogs] = useState([])
  const [loadingAudit, setLoadingAudit] = useState(false)

  const fetchData = async () => {
    try {
      const [devRes, statRes] = await Promise.all([
        api.get('/admin/devices/'),
        api.get('/admin/devices/stats')
      ])
      setDevices(devRes.data)
      setStats(statRes.data)
    } catch {
      toast.error('Failed to load device data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData()
  }, [])

  
  useEffect(() => {
    if (filter === 'Sessions') {
      fetchSessions()
    }
  }, [filter])

  const fetchSessions = async () => {
    setLoadingSessions(true)
    try {
      const { data } = await api.get('/admin/devices/sessions/active')
      setSessions(data)
    } catch {
      toast.error('Failed to load active sessions')
    } finally {
      setLoadingSessions(false)
    }
  }

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedSessions(sessions.map(s => s.id))
    } else {
      setSelectedSessions([])
    }
  }

  const handleSelectSession = (id) => {
    if (selectedSessions.includes(id)) {
      setSelectedSessions(selectedSessions.filter(sId => sId !== id))
    } else {
      setSelectedSessions([...selectedSessions, id])
    }
  }

  const bulkTerminate = async () => {
    if (!selectedSessions.length) return
    if (!window.confirm(`Are you sure you want to terminate ${selectedSessions.length} session(s)?`)) return
    try {
      await api.post('/admin/devices/sessions/bulk-terminate', { session_ids: selectedSessions })
      toast.success('Sessions terminated successfully')
      setSelectedSessions([])
      fetchSessions()
      fetchData() // Update stats
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to terminate sessions')
    }
  }

  const terminateAll = async () => {
    if (!window.confirm('WARNING: This will log out everyone currently using the platform except you. Proceed?')) return
    try {
      await api.delete('/admin/devices/sessions/all')
      toast.success('All other sessions terminated')
      fetchSessions()
      fetchData()
    } catch {
      toast.error('Failed to terminate sessions')
    }
  }

  const clearExpired = async () => {
    try {
      const { data } = await api.delete('/admin/devices/sessions/expired')
      toast.success(data.message || 'Expired sessions cleared')
      fetchSessions()
      fetchData()
    } catch {
      toast.error('Failed to clear expired sessions')
    }
  }

  const clearAllDevices = async () => {
    if (!window.confirm('WARNING: This will clear ALL trusted devices (except your current one). Users will need to re-verify. Proceed?')) return
    try {
      await api.delete('/admin/devices/all')
      toast.success('All devices cleared')
      fetchData()
    } catch {
      toast.error('Failed to clear devices')
    }
  }

  const clearPendingDevices = async () => {
    if (!window.confirm('Delete all pending device requests?')) return
    try {
      await api.delete('/admin/devices/pending')
      toast.success('Pending devices cleared')
      fetchData()
    } catch {
      toast.error('Failed to clear pending devices')
    }
  }

  const updateStatus = async (id, status) => {
    try {
      await api.put(`/admin/devices/${id}/status`, { status })
      toast.success(`Device status updated to ${status}`)
      fetchData()
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to update status')
    }
  }

  const forceLogout = async (id) => {
    if (!window.confirm('Are you sure you want to terminate all active sessions for this device?')) return
    try {
      const { data } = await api.delete(`/admin/devices/${id}/sessions`)
      toast.success(data.message)
      fetchData()
    } catch {
      toast.error('Failed to force logout')
    }
  }

  const openAuditLog = async (device) => {
    setSelectedDevice(device)
    setLoadingAudit(true)
    try {
      const { data } = await api.get(`/admin/devices/${device.id}/audit`)
      setAuditLogs(data)
    } catch {
      toast.error('Failed to load audit logs')
    } finally {
      setLoadingAudit(false)
    }
  }

  const tabs = [
    { id: 'All', label: 'All Devices' },
    { id: 'Pending', label: 'Pending Approvals' },
    { id: 'Trusted', label: 'Active & Trusted' },
    { id: 'Blocked', label: 'Blocked' },
    { id: 'Revoked', label: 'Revoked' },
    { id: 'Sessions', label: 'Active Sessions' }
  ]

  const filteredDevices = devices.filter(d => {
    if (filter !== 'All' && d.status !== filter) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return (
        d.device_name?.toLowerCase().includes(q) ||
        d.user_email?.toLowerCase().includes(q) ||
        d.ip_address?.toLowerCase().includes(q)
      )
    }
    return true
  })

  return (
    <div className="cc-shell">
      <div className="cc-main">
        <div className="cc-topbar">
          <div className="cc-title-row">
            <div className="cc-title-icon">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h1 className="cc-section-title">Trusted Device Management</h1>
              <p className="cc-section-subtitle">Enterprise Command Center for Session & Access Control</p>
            </div>
          </div>
          
          <div className="cc-top-actions">
            <button className="cc-ghost-button" onClick={clearPendingDevices} style={{ color: 'var(--warning)' }}>
              Clear Pending
            </button>
            <button className="cc-ghost-button" onClick={clearAllDevices} style={{ color: 'var(--danger)' }}>
              Clear All Devices
            </button>

            <div style={{ position: 'relative' }}>
              <Search size={16} style={{ position: 'absolute', left: 12, top: 11, color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search devices, IPs, users..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ paddingLeft: 36, width: 280 }}
              />
            </div>
            <button className="cc-ghost-button" onClick={fetchData}>
              <Activity size={16} /> Refresh
            </button>
          </div>
        </div>

        <div className="cc-page-body">
          {stats && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              <div className="cc-metric">
                <div className="cc-metric-top">
                  <div className="cc-metric-label">Trusted Devices</div>
                  <ShieldCheck className="cc-metric-icon" style={{ color: 'var(--success)' }} />
                </div>
                <div className="cc-metric-value">{stats.trusted}</div>
              </div>
              <div className="cc-metric cc-metric-contrast" style={{ border: stats.pending > 0 ? '1px solid var(--danger)' : '' }}>
                <div className="cc-metric-top">
                  <div className="cc-metric-label" style={{ color: stats.pending > 0 ? 'var(--danger)' : '' }}>Pending Approvals</div>
                  <ShieldAlert className="cc-metric-icon" style={{ color: stats.pending > 0 ? 'var(--danger)' : 'var(--warning)' }} />
                </div>
                <div className="cc-metric-value">{stats.pending}</div>
                {stats.pending > 0 && <div className="cc-metric-sub" style={{ color: 'var(--danger)' }}>Requires immediate action</div>}
              </div>
              <div className="cc-metric">
                <div className="cc-metric-top">
                  <div className="cc-metric-label">Active Sessions</div>
                  <Server className="cc-metric-icon" />
                </div>
                <div className="cc-metric-value">{stats.active_sessions}</div>
              </div>
              <div className="cc-metric">
                <div className="cc-metric-top">
                  <div className="cc-metric-label">Blocked / Revoked</div>
                  <ShieldX className="cc-metric-icon" style={{ color: 'var(--danger)' }} />
                </div>
                <div className="cc-metric-value">{stats.blocked + stats.revoked}</div>
              </div>
            </div>
          )}

          <div className="cc-card" style={{ padding: '0', overflow: 'hidden' }}>
            <div style={{ display: 'flex', borderBottom: '1px solid var(--card-border)', padding: '0 16px', background: 'rgba(0,0,0,0.02)' }}>
              {tabs.map(t => (
                <button
                  key={t.id}
                  onClick={() => setFilter(t.id)}
                  style={{
                    padding: '16px 20px',
                    background: 'transparent',
                    border: 'none',
                    borderBottom: filter === t.id ? '2px solid var(--accent)' : '2px solid transparent',
                    color: filter === t.id ? 'var(--accent)' : 'var(--text-secondary)',
                    fontWeight: filter === t.id ? 800 : 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  {t.label}
                  {t.id === 'Pending' && stats?.pending > 0 && (
                    <span style={{ marginLeft: 8, background: 'var(--danger)', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', animation: 'pulse-badge 2s infinite' }}>{stats.pending}</span>
                  )}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="cc-empty">
                <Activity className="animate-spin" size={32} />
                <div className="cc-empty-title">Loading telemetry...</div>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ minWidth: '1000px' }}>
                  
                  <thead>
                    {filter === 'Sessions' ? (
                      <tr>
                        <th style={{ width: 40 }}><input type="checkbox" onChange={handleSelectAll} checked={sessions.length > 0 && selectedSessions.length === sessions.length} /></th>
                        <th>User</th>
                        <th>Device & Browser</th>
                        <th>IP Address</th>
                        <th>Session Info</th>
                      </tr>
                    ) : (
                      <tr>
                        <th>Device Profile</th>
                        <th>User Account</th>
                        <th>Location & IP</th>
                        <th>Status & Risk</th>
                        <th>Active Sessions</th>
                        <th style={{ width: 100, textAlign: 'right' }}>Actions</th>
                      </tr>
                    )}
                  </thead>

                  <tbody>
                    
                {filter === 'Sessions' ? (
                  loadingSessions ? (
                    <tr><td colSpan="5" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Loading sessions...</td></tr>
                  ) : sessions.length === 0 ? (
                    <tr><td colSpan="5" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>No active sessions found</td></tr>
                  ) : (
                    <>
                      <tr style={{ background: 'var(--bg-surface)' }}>
                        <td colSpan="5" style={{ padding: '8px 20px', borderBottom: '1px solid var(--card-border)' }}>
                          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{selectedSessions.length} selected</span>
                            <button disabled={!selectedSessions.length} onClick={bulkTerminate} className="cc-button" style={{ background: 'var(--danger)', opacity: selectedSessions.length ? 1 : 0.5, border: 'none', padding: '6px 12px', fontSize: 12 }}>Bulk Terminate Selected</button>
                            <button onClick={terminateAll} className="cc-button" style={{ background: 'var(--bg-surface)', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '6px 12px', fontSize: 12 }}>Terminate All Sessions</button>
                            <button onClick={clearExpired} className="cc-ghost-button" style={{ fontSize: 12 }}>Clear Expired</button>
                          </div>
                        </td>
                      </tr>
                      {sessions.map(s => (
                        <tr key={s.id}>
                          <td>
                            <input type="checkbox" checked={selectedSessions.includes(s.id)} onChange={() => handleSelectSession(s.id)} />
                          </td>
                          <td>
                            <div style={{ fontWeight: 600, fontSize: 13 }}>{s.user_name}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.user_email}</div>
                          </td>
                          <td>
                            <div style={{ fontSize: 13 }}>{s.device}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.browser}</div>
                          </td>
                          <td>
                            <div style={{ fontSize: 13, fontFamily: 'var(--mono)' }}>{s.ip_address}</div>
                          </td>
                          <td>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Created: {new Date(s.created_at).toLocaleString()}</div>
                          </td>
                        </tr>
                      ))}
                    </>
                  )
                ) : (

                    filteredDevices.map(d => (
                      <tr key={d.id}>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <div style={{
                              width: 40, height: 40, borderRadius: 10,
                              background: 'var(--panel-bg)', border: '1px solid var(--card-border)',
                              display: 'grid', placeItems: 'center', color: 'var(--text-secondary)'
                            }}>
                              <MonitorSmartphone size={20} />
                            </div>
                            <div>
                              <div style={{ fontWeight: 800, fontSize: '14px' }}>{d.device_name || 'Unknown Device'}</div>
                              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 2 }}>
                                {d.device_type} • {d.browser} {d.browser_version !== 'Unknown' ? d.browser_version : ''}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            {d.avatar_url ? (
                              <img src={d.avatar_url} alt={d.user_name} style={{ width: 32, height: 32, borderRadius: '50%', border: '1px solid var(--card-border)', objectFit: 'cover' }} referrerPolicy="no-referrer" />
                            ) : (
                              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--accent)', display: 'grid', placeItems: 'center', color: '#fff', fontWeight: 'bold' }}>
                                {d.user_name?.charAt(0) || '?'}
                              </div>
                            )}
                            <div>
                              <div style={{ fontWeight: 700, fontSize: '13px', display: 'flex', alignItems: 'center', gap: 6 }}>
                                {d.user_name}
                                {d.auth_provider === 'google' && (
                                  <svg width="14" height="14" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" title="Verified by Google">
                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                                  </svg>
                                )}
                              </div>
                              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{d.user_email}</div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '13px', fontWeight: 600 }}>
                            <MapPin size={14} color="var(--text-muted)" /> {d.location}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: 2, fontFamily: 'var(--mono)' }}>
                            {d.ip_address}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-start' }}>
                            <span className={`cc-badge ${
                              d.status === 'Trusted' ? 'cc-badge-success' :
                              d.status === 'Pending' ? 'cc-badge-warning' :
                              'cc-badge-danger'
                            }`}>
                              {d.status}
                            </span>
                            {d.risk_level && (
                              <span style={{ fontSize: '11px', color: d.risk_level === 'high' ? 'var(--danger)' : 'var(--text-muted)', fontWeight: 700 }}>
                                RISK: {d.risk_level.toUpperCase()}
                              </span>
                            )}
                          </div>
                        </td>
                        <td>
                          {d.active_sessions > 0 ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '13px', color: 'var(--success)', fontWeight: 700 }}>
                              <div className="cc-session-dot" />
                              {d.active_sessions} Active
                            </div>
                          ) : (
                            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>None</div>
                          )}
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: 4 }}>
                            Last: {d.last_login ? new Date(d.last_login).toLocaleDateString() : 'Never'}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            {d.status === 'Pending' && (
                              <>
                                <button onClick={() => updateStatus(d.id, 'Trusted')} className="cc-icon-button" style={{ color: 'var(--success)', borderColor: 'rgba(16, 185, 129, 0.3)', background: 'rgba(16, 185, 129, 0.1)' }} title="Approve">
                                  <Check size={16} />
                                </button>
                                <button onClick={() => updateStatus(d.id, 'Blocked')} className="cc-icon-button" style={{ color: 'var(--danger)', borderColor: 'rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.1)' }} title="Block Permanently">
                                  <ShieldX size={16} />
                                </button>
                              </>
                            )}
                            {d.status === 'Trusted' && (
                              <button onClick={() => updateStatus(d.id, 'Revoked')} className="cc-icon-button" style={{ color: 'var(--warning)', borderColor: 'rgba(245, 158, 11, 0.3)', background: 'rgba(245, 158, 11, 0.1)' }} title="Revoke Access">
                                <ShieldAlert size={16} />
                              </button>
                            )}
                            {d.active_sessions > 0 && (
                              <button onClick={() => forceLogout(d.id)} className="cc-icon-button" title="Force Terminate Sessions">
                                <Activity size={16} color="var(--danger)" />
                              </button>
                            )}
                            <button onClick={() => openAuditLog(d)} className="cc-icon-button" title="View Audit Trail">
                              <History size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {filteredDevices.length === 0 && (
                      <tr>
                        <td colSpan="6">
                          <div className="cc-empty">
                            <div className="cc-empty-icon"><ShieldCheck size={24} /></div>
                            <div className="cc-empty-title">No devices found</div>
                            <div className="cc-empty-desc">There are no devices matching the current filter criteria.</div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {selectedDevice && (
        <div style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, width: '400px',
          background: 'var(--bg-surface)', borderLeft: '1px solid var(--card-border)',
          boxShadow: '-10px 0 30px rgba(0,0,0,0.1)', zIndex: 100, display: 'flex', flexDirection: 'column'
        }}>
          <div style={{ padding: '20px', borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 900 }}>Audit Trail</h3>
              <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>{selectedDevice.device_name}</p>
            </div>
            <button onClick={() => setSelectedDevice(null)} className="cc-icon-button"><X size={18} /></button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            {loadingAudit ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                <Activity className="animate-spin" style={{ margin: '0 auto 12px' }} />
                Loading audit logs...
              </div>
            ) : auditLogs.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px' }}>No audit logs available for this device.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {auditLogs.map(log => (
                  <div key={log.id} className="cc-timeline-item">
                    <div className="cc-timeline-dot"></div>
                    <div>
                      <div className="cc-timeline-title">
                        {log.action.replace(/_/g, ' ').toUpperCase()}
                      </div>
                      <div className="cc-timeline-meta">
                        {new Date(log.timestamp).toLocaleString()} • IP: {log.ip_address || 'Unknown'}
                      </div>
                      <div className="cc-timeline-desc">
                        {log.reason && <div><strong style={{ color: 'var(--text-primary)' }}>Reason:</strong> {log.reason}</div>}
                        {log.status && <div><strong style={{ color: 'var(--text-primary)' }}>Status:</strong> {log.status}</div>}
                        {log.previous_value && log.new_value && (
                          <div style={{ marginTop: 4, fontFamily: 'var(--mono)', fontSize: '11px', background: 'rgba(0,0,0,0.04)', padding: '4px 8px', borderRadius: '4px' }}>
                            {log.previous_value} → {log.new_value}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
