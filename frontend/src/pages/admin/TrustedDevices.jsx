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
    { id: 'Revoked', label: 'Revoked' }
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
                    <tr>
                      <th>Device & Forensic Data</th>
                      <th>User Identity</th>
                      <th>Location / IP</th>
                      <th>Status & Risk</th>
                      <th>Active Sessions</th>
                      <th>Controls</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDevices.map(d => (
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
                          <div style={{ fontWeight: 700, fontSize: '13px' }}>{d.user_name}</div>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{d.user_email}</div>
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
