import React, { useState, useEffect, useMemo, useRef } from 'react'
import api from '../../services/api'
import { toast } from 'react-hot-toast'
import { 
  ShieldCheck, ShieldAlert, MonitorSmartphone, Smartphone, Monitor, Activity, 
  History, X, Search, Settings, Download, CheckCircle, RefreshCw,
  AlertCircle, Edit2, Copy, FileText, Zap, ShieldX, MapPin, Clock
} from 'lucide-react'
import { formatRelativeTime, formatExactDate, exportToCSV, copyForensics, getSLA, computeRisk } from './deviceLogic'
import DeviceActionModal from './DeviceActionModal'
import DevicePolicyPanel from './DevicePolicyPanel'

// Fake audit log generator for the mock
const generateAuditLogs = (device) => {
  return [
    { id: 1, action: 'Detected', actor: 'System', time: device.first_seen, details: 'First connection established', ip: device.ip_address },
    { id: 2, action: 'Risk Scored', actor: 'Risk Engine', time: device.first_seen, details: `Assigned initial score ${computeRisk(device).score}` },
    ...(device.status !== 'Pending' ? [{ 
      id: 3, action: `Status changed to ${device.status}`, 
      actor: 'admin@talentops.ai', time: device.last_seen, 
      details: 'Manual review completed' 
    }] : [])
  ].sort((a,b) => new Date(b.time) - new Date(a.time))
}

export default function TrustedDevices() {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState('Pending')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortOrder, setSortOrder] = useState('highest_risk')

  // Selection
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [mutatingIds, setMutatingIds] = useState(new Set())

  // Modals/Drawers
  const [policyOpen, setPolicyOpen] = useState(false)
  const [auditDevice, setAuditDevice] = useState(null)
  
  // Action Modal
  const [actionModalOpen, setActionModalOpen] = useState(false)
  const [actionType, setActionType] = useState(null) // 'Trusted', 'Blocked', etc.
  const [actionTargets, setActionTargets] = useState([]) // Array of device IDs

  // Inline editing
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const editInputRef = useRef(null)

  const fetchData = async (silent = false) => {
    if (!silent) setLoading(true)
    else setIsRefreshing(true)
    try {
      const { data } = await api.get('/admin/devices/')
      // Fake delay to show skeletons
      await new Promise(r => setTimeout(r, 600))
      
      // Inject mock risk stats into the payload for easy handling if not present
      const processed = data.map(d => ({
        ...d,
        risk: computeRisk(d),
        sla: d.status === 'Pending' ? getSLA(d.first_seen) : null
      }))
      setDevices(processed)
    } catch {
      toast.error('Failed to load device data')
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Auto-focus edit input
  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus()
    }
  }, [editingId])

  // Process data based on active tab, search, sort
  const { filteredDevices, stats } = useMemo(() => {
    const s = {
      total: devices.length,
      pending: 0,
      trusted: 0,
      blocked: 0,
      revoked: 0,
      high_risk: 0,
      active_sessions: 0
    }

    let filtered = devices

    // Accumulate stats
    devices.forEach(d => {
      if (d.status === 'Pending') s.pending++
      if (d.status === 'Trusted') s.trusted++
      if (d.status === 'Blocked') s.blocked++
      if (d.status === 'Revoked') s.revoked++
      if (d.risk.level === 'HIGH') s.high_risk++
      if (d.active_sessions > 0) s.active_sessions += d.active_sessions
    })

    // Filter by tab
    if (activeTab === 'Pending') filtered = filtered.filter(d => d.status === 'Pending')
    if (activeTab === 'Trusted') filtered = filtered.filter(d => d.status === 'Trusted')
    if (activeTab === 'Blocked') filtered = filtered.filter(d => d.status === 'Blocked')
    if (activeTab === 'Revoked') filtered = filtered.filter(d => d.status === 'Revoked')

    // Filter by search
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter(d => 
        (d.device_name || '').toLowerCase().includes(q) ||
        (d.user_name || '').toLowerCase().includes(q) ||
        (d.user_email || '').toLowerCase().includes(q) ||
        (d.ip_address || '').toLowerCase().includes(q) ||
        (d.location || '').toLowerCase().includes(q) ||
        (d.tags || []).some(t => t.toLowerCase().includes(q))
      )
    }

    // Sort
    filtered.sort((a, b) => {
      if (sortOrder === 'highest_risk') return b.risk.score - a.risk.score
      if (sortOrder === 'most_recent') return new Date(b.last_seen) - new Date(a.last_seen)
      if (sortOrder === 'longest_waiting') return new Date(a.first_seen) - new Date(b.first_seen)
      if (sortOrder === 'user_az') return (a.user_name || '').localeCompare(b.user_name || '')
      return 0
    })

    return { filteredDevices: filtered, stats: s }
  }, [devices, activeTab, searchQuery, sortOrder])

  // Actions
  const handleSelectAll = (e) => {
    if (e.target.checked) setSelectedIds(new Set(filteredDevices.map(d => d.id)))
    else setSelectedIds(new Set())
  }

  const toggleSelect = (id) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedIds(next)
  }

  const handleBulkAction = (type) => {
    setActionTargets(Array.from(selectedIds))
    setActionType(type)
    setActionModalOpen(true)
  }

  const handleRowAction = (id, type) => {
    setActionTargets([id])
    setActionType(type)
    setActionModalOpen(true)
  }

  const executeAction = async (payload) => {
    setActionModalOpen(false)
    const newMutating = new Set(mutatingIds)
    actionTargets.forEach(id => newMutating.add(id))
    setMutatingIds(newMutating)

    try {
      await Promise.all(actionTargets.map(async id => {
        if (actionType === 'Terminate') {
          await api.delete(`/admin/devices/${id}/sessions`);
        } else if (actionType === 'ReVerify') {
          await api.put(`/admin/devices/${id}/status`, { status: 'Pending' });
        } else {
          await api.put(`/admin/devices/${id}/status`, { status: actionType });
        }
      }))
      
      // Reload devices from backend to reflect exact state
      await loadDevices();
      
      toast.success(`Successfully updated ${actionTargets.length} device${actionTargets.length > 1 ? 's' : ''}`)
      setSelectedIds(new Set())
    } catch (e) {
      toast.error('Failed to perform action')
    } finally {
      const cleared = new Set(mutatingIds)
      actionTargets.forEach(id => cleared.delete(id))
      setMutatingIds(cleared)
    }
  }

  const saveInlineName = async (id) => {
    if (!editName.trim()) {
      setEditingId(null)
      return
    }
    try {
      setDevices(prev => prev.map(d => d.id === id ? { ...d, device_name: editName } : d))
      setEditingId(null)
      toast.success('Device renamed')
    } catch {
      toast.error('Failed to rename')
    }
  }

  return (
    <div className="td-container">
      <DevicePolicyPanel isOpen={policyOpen} onClose={() => setPolicyOpen(false)} />
      
      <DeviceActionModal 
        isOpen={actionModalOpen}
        onClose={() => setActionModalOpen(false)}
        actionType={actionType}
        count={actionTargets.length}
        onConfirm={executeAction}
      />

      {/* Audit Drawer */}
      <div 
        className={`td-drawer-backdrop ${auditDevice ? 'open' : ''}`}
        onClick={() => setAuditDevice(null)}
      />
      <div className={`td-drawer ${auditDevice ? 'open' : ''}`}>
        {auditDevice && (
          <div className="td-drawer-content">
            <div className="td-drawer-header">
              <div>
                <h2>Audit Log: {auditDevice.device_name}</h2>
                <p>ID: {auditDevice.id}</p>
              </div>
              <button onClick={() => setAuditDevice(null)} className="td-icon-btn"><X size={20}/></button>
            </div>
            <div className="td-drawer-body">
              <div className="td-timeline">
                {generateAuditLogs(auditDevice).map(log => (
                  <div key={log.id} className="td-timeline-item">
                    <div className="td-timeline-dot" />
                    <div className="td-timeline-card">
                      <div className="td-timeline-title">{log.action}</div>
                      <div className="td-timeline-meta">By {log.actor} • {formatExactDate(log.time)}</div>
                      <div className="td-timeline-details">{log.details}</div>
                      {log.ip && <div className="td-timeline-ip">IP: {log.ip}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Top Bar Controls */}
      <div className="td-top-bar">
        <h1 className="td-page-title">Device Security</h1>
        <div className="td-top-actions">
          <div className="td-search-box">
            <Search size={16} className="td-search-icon" />
            <input 
              type="text" 
              placeholder="Search user, device, IP..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="td-search-clear"><X size={14}/></button>
            )}
          </div>
          <button className={`td-btn td-btn-icon ${isRefreshing ? 'spinning' : ''}`} onClick={() => fetchData(true)}>
            <RefreshCw size={16} />
          </button>
          <button className="td-btn td-btn-outline" onClick={() => exportToCSV(filteredDevices)}>
            <Download size={16} /> Export CSV
          </button>
          <button className="td-btn td-btn-primary" onClick={() => setPolicyOpen(true)}>
            <Settings size={16} /> Access Policy
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="td-metrics-grid">
        <MetricCard 
          loading={loading} title="Trusted Devices" 
          val={stats.trusted} icon={ShieldCheck} color="var(--success)" 
        />
        <MetricCard 
          loading={loading} title="Pending Approvals" 
          val={stats.pending} icon={Activity} color="var(--danger)"
          glow={stats.pending > 0}
          subtitle={stats.pending > 0 ? 'Requires immediate action' : 'Queue is clear'}
        />
        <MetricCard 
          loading={loading} title="High-Risk Devices" 
          val={stats.high_risk} icon={ShieldAlert} color="var(--warning)"
          glow={stats.high_risk > 0}
          subtitle={stats.high_risk > 0 ? 'Review signals below' : 'No anomalies detected'}
        />
        <MetricCard 
          loading={loading} title="Active Sessions" 
          val={stats.active_sessions} icon={MonitorSmartphone} color="var(--accent)" 
        />
        <MetricCard 
          loading={loading} title="Blocked/Revoked" 
          val={stats.blocked + stats.revoked} icon={ShieldX} color="var(--text-muted)" 
        />
      </div>

      {/* Tabs */}
      <div className="td-tabs">
        {['All', 'Pending', 'Trusted', 'Blocked', 'Revoked'].map(tab => {
          let count = tab === 'All' ? stats.total : stats[tab.toLowerCase()]
          let isRed = tab === 'Pending' && count > 0
          return (
            <button 
              key={tab}
              className={`td-tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => { setActiveTab(tab); setSelectedIds(new Set()) }}
            >
              {tab}
              <span className={`td-tab-pill ${isRed ? 'red' : ''}`}>{loading ? '...' : count}</span>
            </button>
          )
        })}
      </div>

      {/* Toolbar & Bulk Actions */}
      <div className="td-toolbar-wrapper">
        <div className={`td-bulk-bar ${selectedIds.size > 0 ? 'visible' : ''}`}>
          <div className="td-bulk-count">{selectedIds.size} selected</div>
          <div className="td-bulk-actions">
            {activeTab === 'Pending' && (
              <>
                <button onClick={() => handleBulkAction('Trusted')} className="td-bulk-btn trust"><CheckCircle size={14}/> Trust</button>
                <button onClick={() => handleBulkAction('Blocked')} className="td-bulk-btn block"><ShieldAlert size={14}/> Block</button>
              </>
            )}
            {activeTab === 'Trusted' && (
              <>
                <button onClick={() => handleBulkAction('ReVerify')} className="td-bulk-btn reverify"><Zap size={14}/> Re-verify</button>
                <button onClick={() => handleBulkAction('Revoked')} className="td-bulk-btn revoke"><ShieldAlert size={14}/> Revoke</button>
              </>
            )}
            {(activeTab === 'Blocked' || activeTab === 'Revoked') && (
              <button onClick={() => handleBulkAction('Pending')} className="td-bulk-btn trust"><AlertCircle size={14}/> Restore to Pending</button>
            )}
            <div className="td-bulk-divider" />
            <button onClick={() => handleBulkAction('Terminate')} className="td-bulk-btn block"><X size={14}/> Terminate Sessions</button>
            <button onClick={() => exportToCSV(filteredDevices.filter(d => selectedIds.has(d.id)))} className="td-bulk-btn export"><Download size={14}/> Export</button>
            <button onClick={() => setSelectedIds(new Set())} className="td-bulk-btn clear">Clear</button>
          </div>
        </div>

        <div className={`td-toolbar ${selectedIds.size > 0 ? 'hidden' : ''}`}>
          <div className="td-toolbar-left">
            <label className="td-select-all">
              <input 
                type="checkbox" 
                checked={filteredDevices.length > 0 && selectedIds.size === filteredDevices.length}
                onChange={handleSelectAll}
                disabled={filteredDevices.length === 0}
              />
              Select All Visible
            </label>
          </div>
          <div className="td-toolbar-right">
            <span className="td-sort-label">Sort by:</span>
            <select value={sortOrder} onChange={e => setSortOrder(e.target.value)} className="td-sort-select">
              <option value="highest_risk">Highest Risk First</option>
              <option value="most_recent">Most Recently Seen</option>
              <option value="longest_waiting">Longest Waiting</option>
              <option value="user_az">User A-Z</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="td-table-container">
        {loading ? (
          <div className="td-skeletons">
            {[1,2,3,4,5].map(i => <div key={i} className="td-skeleton-row" />)}
          </div>
        ) : filteredDevices.length === 0 ? (
          <div className="td-empty-state">
            <MonitorSmartphone size={48} className="td-empty-icon" />
            <h3>{searchQuery ? 'No matches found' : 'You are all caught up'}</h3>
            <p>{searchQuery ? `No devices match "${searchQuery}"` : `Nothing is currently marked as ${activeTab}.`}</p>
            {searchQuery && <button onClick={() => setSearchQuery('')} className="td-btn td-btn-outline mt-4">Clear search</button>}
          </div>
        ) : (
          <table className="td-table">
            <thead>
              <tr>
                <th width="40"></th>
                <th>Device</th>
                <th>User / Network</th>
                <th>Risk & SLA</th>
                <th width="120">Activity</th>
                <th width="160" style={{textAlign: 'right'}}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDevices.map(d => {
                const isSelected = selectedIds.has(d.id)
                const isMutating = mutatingIds.has(d.id)
                
                return (
                  <tr key={d.id} className={`${isSelected ? 'selected' : ''} ${isMutating ? 'mutating' : ''}`}>
                    <td className="td-checkbox-cell">
                      <input 
                        type="checkbox" 
                        checked={isSelected} 
                        onChange={() => toggleSelect(d.id)}
                        disabled={isMutating}
                      />
                    </td>
                    <td>
                      <div className="td-device-info">
                        <div className="td-device-icon">
                          {d.device_type === 'phone' ? <Smartphone size={16}/> : d.device_type === 'laptop' ? <Monitor size={16}/> : <MonitorSmartphone size={16}/>}
                        </div>
                        <div>
                          <div className="td-device-name-wrap">
                            {editingId === d.id ? (
                              <input 
                                ref={editInputRef}
                                type="text"
                                className="td-inline-input"
                                value={editName}
                                onChange={e => setEditName(e.target.value)}
                                onBlur={() => saveInlineName(d.id)}
                                onKeyDown={e => { if(e.key === 'Enter') saveInlineName(d.id); if(e.key === 'Escape') setEditingId(null) }}
                              />
                            ) : (
                              <div className="td-device-name" onClick={() => { setEditingId(d.id); setEditName(d.device_name) }}>
                                {d.device_name || 'Unknown Device'} <Edit2 size={12} className="edit-icon" />
                              </div>
                            )}
                          </div>
                          <div className="td-tags">
                            {(d.tags || []).map(t => <span key={t} className="td-tag">{t}</span>)}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="td-user-info">
                        <div className="td-user-name">{d.user_name || d.user_email}</div>
                        <div className="td-user-email">{d.user_email}</div>
                        <div className="td-network">
                          <MapPin size={12} /> {d.location || 'Unknown'} • {d.ip_address}
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="td-risk-cell">
                        <div className="td-risk-pill-wrapper">
                          <span className={`td-risk-pill ${d.risk.level.toLowerCase()}`}>
                            {d.risk.level} • {d.risk.score}
                          </span>
                          <div className="td-risk-popover">
                            <div className="td-rp-title">Why this score?</div>
                            {d.risk.signals.length === 0 ? <div className="td-rp-item">No high-risk signals</div> : null}
                            {d.risk.signals.map((sig, i) => (
                              <div key={i} className="td-rp-item">
                                <span className="td-rp-weight">+{sig.weight}</span> {sig.reason}
                              </div>
                            ))}
                          </div>
                        </div>
                        {d.status === 'Pending' && d.sla && (
                          <div className={`td-sla ${d.sla.overThreshold ? 'red' : ''}`}>
                            <Clock size={12}/> {d.sla.text}
                          </div>
                        )}
                        {d.status === 'Trusted' && d.trust_expires_at && (
                          <div className="td-expiry">Exp: {new Date(d.trust_expires_at).toLocaleDateString()}</div>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="td-activity-cell">
                        <div className="td-active-sessions">
                          {d.active_sessions > 0 ? (
                            <><span className="td-pulse-dot" /> {d.active_sessions} Active</>
                          ) : 'No active sessions'}
                        </div>
                        <div className="td-last-seen" title={formatExactDate(d.last_seen)}>
                          Seen {formatRelativeTime(d.last_seen)}
                        </div>
                      </div>
                    </td>
                    <td className="td-actions-cell">
                      <div className="td-row-actions">
                        {d.status === 'Pending' && (
                          <>
                            <button onClick={() => handleRowAction(d.id, 'Trusted')} className="td-icon-btn trust" title="Trust"><CheckCircle size={16}/></button>
                            <button onClick={() => handleRowAction(d.id, 'Blocked')} className="td-icon-btn block" title="Block"><ShieldAlert size={16}/></button>
                          </>
                        )}
                        {d.status === 'Trusted' && (
                          <>
                            <button onClick={() => handleRowAction(d.id, 'ReVerify')} className="td-icon-btn reverify" title="Re-Verify"><Zap size={16}/></button>
                            <button onClick={() => handleRowAction(d.id, 'Revoked')} className="td-icon-btn revoke" title="Revoke"><ShieldAlert size={16}/></button>
                          </>
                        )}
                        {(d.status === 'Blocked' || d.status === 'Revoked') && (
                          <button onClick={() => handleRowAction(d.id, 'Pending')} className="td-icon-btn trust" title="Restore to Pending"><AlertCircle size={16}/></button>
                        )}
                        
                        <div className="td-action-divider" />
                        
                        {d.active_sessions > 0 && (
                          <button onClick={() => handleRowAction(d.id, 'Terminate')} className="td-icon-btn block" title="Terminate Sessions"><X size={16}/></button>
                        )}
                        <button onClick={() => { copyForensics(d); toast.success('Forensics copied') }} className="td-icon-btn" title="Copy Forensics"><Copy size={16}/></button>
                        <button onClick={() => setAuditDevice(d)} className="td-icon-btn" title="View History"><History size={16}/></button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <style>{`
        /* 
          SELF-CONTAINED SCOPED CSS FOR TRUSTED DEVICES
          Using .td-* prefix to avoid global pollution.
        */
        .td-container {
          padding: 24px;
          max-width: 1400px;
          margin: 0 auto;
          font-family: inherit;
        }

        .td-page-title {
          font-size: 24px;
          font-weight: 800;
          color: var(--text-primary);
          margin: 0;
        }

        .td-top-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
          flex-wrap: wrap;
          gap: 16px;
        }

        .td-top-actions {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        .td-search-box {
          position: relative;
          display: flex;
          align-items: center;
        }
        .td-search-box input {
          background: var(--bg-surface);
          border: 1px solid var(--card-border);
          border-radius: 8px;
          padding: 8px 32px;
          color: var(--text-primary);
          font-size: 13px;
          width: 250px;
          outline: none;
        }
        .td-search-box input:focus {
          border-color: var(--text-muted);
        }
        .td-search-icon {
          position: absolute;
          left: 10px;
          color: var(--text-muted);
        }
        .td-search-clear {
          position: absolute;
          right: 10px;
          color: var(--text-muted);
          background: none;
          border: none;
          cursor: pointer;
        }

        .td-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 700;
          cursor: pointer;
          border: none;
          transition: all 0.2s;
        }
        .td-btn-icon {
          padding: 8px;
          background: var(--surface-container);
          border: 1px solid var(--card-border);
          color: var(--text-primary);
        }
        .td-btn-icon.spinning svg {
          animation: td-spin 1s linear infinite;
        }
        .td-btn-outline {
          background: transparent;
          border: 1px solid var(--card-border-strong);
          color: var(--text-primary);
        }
        .td-btn-outline:hover {
          background: var(--surface-container);
        }
        .td-btn-primary {
          background: var(--text-primary);
          color: var(--main-bg);
        }

        /* Metric Cards */
        .td-metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }
        .td-metric-card {
          background: var(--surface-container);
          border: 1px solid var(--card-border);
          border-radius: 12px;
          padding: 16px;
          position: relative;
          overflow: hidden;
        }
        .td-metric-card.glow {
          box-shadow: 0 0 15px color-mix(in srgb, var(--danger) 30%, transparent);
          border-color: color-mix(in srgb, var(--danger) 50%, transparent);
        }
        .td-metric-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          color: var(--text-muted);
          font-size: 13px;
          font-weight: 700;
        }
        .td-metric-icon {
          padding: 6px;
          border-radius: 8px;
        }
        .td-metric-val {
          font-size: 28px;
          font-weight: 900;
          color: var(--text-primary);
          margin-top: 12px;
        }
        .td-metric-sub {
          font-size: 11px;
          color: var(--text-secondary);
          margin-top: 4px;
        }
        .td-skeleton-num {
          height: 32px;
          width: 60px;
          background: var(--card-border-strong);
          border-radius: 4px;
          margin-top: 12px;
          animation: td-pulse 1.5s infinite;
        }

        /* Tabs */
        .td-tabs {
          display: flex;
          gap: 24px;
          border-bottom: 1px solid var(--card-border);
          margin-bottom: 16px;
          overflow-x: auto;
          scrollbar-width: none;
        }
        .td-tabs::-webkit-scrollbar { display: none; }
        .td-tab {
          background: none;
          border: none;
          padding: 0 0 12px;
          color: var(--text-secondary);
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 8px;
          position: relative;
        }
        .td-tab.active {
          color: var(--text-primary);
        }
        .td-tab.active::after {
          content: '';
          position: absolute;
          bottom: -1px;
          left: 0;
          width: 100%;
          height: 2px;
          background: var(--accent);
          border-radius: 2px 2px 0 0;
        }
        .td-tab-pill {
          background: var(--surface-container-high);
          color: var(--text-primary);
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 12px;
        }
        .td-tab-pill.red {
          background: var(--danger);
          color: white;
        }

        /* Toolbar */
        .td-toolbar-wrapper {
          position: relative;
          height: 48px;
          margin-bottom: 12px;
        }
        .td-toolbar, .td-bulk-bar {
          position: absolute;
          inset: 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: var(--bg-surface);
          border: 1px solid var(--card-border);
          border-radius: 8px;
          padding: 0 16px;
          transition: opacity 0.2s, transform 0.2s;
        }
        .td-toolbar.hidden {
          opacity: 0;
          pointer-events: none;
          transform: translateY(10px);
        }
        .td-bulk-bar {
          background: color-mix(in srgb, var(--accent) 15%, transparent);
          border-color: color-mix(in srgb, var(--accent) 30%, transparent);
          opacity: 0;
          pointer-events: none;
          transform: translateY(-10px);
          z-index: 10;
        }
        .td-bulk-bar.visible {
          opacity: 1;
          pointer-events: auto;
          transform: translateY(0);
        }
        .td-bulk-count {
          font-size: 13px;
          font-weight: 800;
          color: var(--accent);
        }
        .td-bulk-actions {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        .td-bulk-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 16px;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          border: 1px solid transparent;
          background: var(--surface-container);
          color: var(--text-primary);
        }
        .td-bulk-btn:hover { filter: brightness(1.2); }
        .td-bulk-btn.trust { background: color-mix(in srgb, var(--success) 20%, transparent); color: var(--success); }
        .td-bulk-btn.block { background: color-mix(in srgb, var(--danger) 20%, transparent); color: var(--danger); }
        .td-bulk-btn.revoke { background: color-mix(in srgb, var(--warning) 20%, transparent); color: var(--warning); }
        .td-bulk-btn.reverify { background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); }
        .td-bulk-btn.clear { background: transparent; border: 1px solid var(--text-muted); }
        .td-bulk-divider { width: 1px; height: 16px; background: var(--card-border-strong); margin: 0 4px; }

        .td-toolbar-left, .td-toolbar-right {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .td-select-all {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          font-weight: 700;
          color: var(--text-secondary);
          cursor: pointer;
        }
        .td-sort-label { font-size: 12px; color: var(--text-muted); font-weight: 600; }
        .td-sort-select {
          background: transparent;
          border: none;
          color: var(--text-primary);
          font-size: 13px;
          font-weight: 700;
          outline: none;
          cursor: pointer;
        }

        /* Table */
        .td-table-container {
          background: var(--surface-container);
          border: 1px solid var(--card-border);
          border-radius: 12px;
          overflow: hidden;
        }
        .td-table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
        }
        .td-table th {
          padding: 12px 16px;
          font-size: 11px;
          font-weight: 800;
          text-transform: uppercase;
          color: var(--text-muted);
          border-bottom: 1px solid var(--card-border);
          background: var(--surface-container-high);
        }
        .td-table td {
          padding: 12px 16px;
          border-bottom: 1px solid var(--card-border);
          vertical-align: top;
          transition: opacity 0.2s;
        }
        .td-table tr.selected td { background: color-mix(in srgb, var(--accent) 5%, transparent); }
        .td-table tr.mutating td { opacity: 0.4; pointer-events: none; }
        .td-table tr:last-child td { border-bottom: none; }
        
        .td-checkbox-cell { padding-top: 16px !important; }

        .td-device-info { display: flex; gap: 12px; }
        .td-device-icon {
          width: 32px; height: 32px;
          border-radius: 8px;
          background: var(--surface-container-highest);
          display: flex; align-items: center; justify-content: center;
          color: var(--text-secondary);
          flex-shrink: 0;
        }
        .td-device-name-wrap { position: relative; height: 20px; margin-bottom: 4px; }
        .td-device-name {
          font-size: 14px; font-weight: 700; color: var(--text-primary);
          display: flex; align-items: center; gap: 6px; cursor: text;
        }
        .td-device-name .edit-icon { opacity: 0; transition: opacity 0.2s; }
        .td-device-name:hover .edit-icon { opacity: 1; }
        .td-inline-input {
          background: var(--bg-surface); border: 1px solid var(--accent);
          color: var(--text-primary); border-radius: 4px;
          font-size: 13px; font-weight: 700; padding: 2px 6px;
          position: absolute; top: -2px; left: -2px; outline: none; width: 100%;
        }
        .td-tags { display: flex; gap: 4px; flex-wrap: wrap; }
        .td-tag {
          font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px;
          background: var(--surface-container-highest); color: var(--text-muted);
          text-transform: uppercase;
        }

        .td-user-name { font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px; }
        .td-user-email { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
        .td-network { font-size: 11px; color: var(--text-muted); display: flex; align-items: center; gap: 4px; }

        .td-risk-cell { position: relative; }
        .td-risk-pill-wrapper { position: relative; display: inline-block; margin-bottom: 6px; }
        .td-risk-pill {
          font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 12px; cursor: help;
        }
        .td-risk-pill.low { background: color-mix(in srgb, var(--success) 20%, transparent); color: var(--success); }
        .td-risk-pill.med { background: color-mix(in srgb, var(--warning) 20%, transparent); color: var(--warning); }
        .td-risk-pill.high { background: color-mix(in srgb, var(--danger) 20%, transparent); color: var(--danger); }
        
        .td-risk-popover {
          position: absolute; bottom: 100%; left: 0; width: 220px;
          background: var(--surface-container-highest);
          border: 1px solid var(--card-border-strong);
          border-radius: 8px; padding: 12px; margin-bottom: 8px;
          box-shadow: 0 10px 25px rgba(0,0,0,0.5);
          opacity: 0; pointer-events: none; transition: opacity 0.2s; z-index: 10;
        }
        .td-risk-pill-wrapper:hover .td-risk-popover { opacity: 1; }
        .td-rp-title { font-size: 10px; font-weight: 800; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
        .td-rp-item { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; display: flex; gap: 6px; }
        .td-rp-weight { color: var(--danger); font-weight: 700; }

        .td-sla { font-size: 11px; font-weight: 700; color: var(--text-secondary); display: flex; align-items: center; gap: 4px; }
        .td-sla.red { color: var(--danger); }
        .td-expiry { font-size: 11px; font-weight: 700; color: var(--text-muted); }

        .td-activity-cell { font-size: 12px; }
        .td-active-sessions { font-weight: 700; color: var(--text-primary); margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
        .td-pulse-dot { width: 6px; height: 6px; background: var(--success); border-radius: 50%; box-shadow: 0 0 5px var(--success); animation: td-pulse 2s infinite; }
        .td-last-seen { color: var(--text-secondary); }

        .td-row-actions { display: flex; gap: 6px; justify-content: flex-end; align-items: center; }
        .td-icon-btn {
          width: 28px; height: 28px; border-radius: 6px; border: none;
          background: var(--surface-container-highest); color: var(--text-secondary);
          display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s;
        }
        .td-icon-btn:hover { background: var(--card-border-strong); color: var(--text-primary); }
        .td-icon-btn.trust:hover { background: color-mix(in srgb, var(--success) 20%, transparent); color: var(--success); }
        .td-icon-btn.block:hover, .td-icon-btn.revoke:hover { background: color-mix(in srgb, var(--danger) 20%, transparent); color: var(--danger); }
        .td-icon-btn.reverify:hover { background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); }
        .td-action-divider { width: 1px; height: 16px; background: var(--card-border-strong); margin: 0 4px; }

        .td-empty-state { text-align: center; padding: 60px 20px; }
        .td-empty-icon { color: var(--text-muted); margin-bottom: 16px; opacity: 0.5; }
        .td-empty-state h3 { font-size: 16px; font-weight: 800; color: var(--text-primary); margin: 0 0 8px; }
        .td-empty-state p { font-size: 13px; color: var(--text-secondary); margin: 0; }

        .td-skeletons { padding: 16px; display: flex; flex-direction: column; gap: 16px; }
        .td-skeleton-row { height: 48px; background: var(--card-border); border-radius: 8px; animation: td-pulse 1.5s infinite; }

        /* Audit Drawer */
        .td-drawer-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 40; opacity: 0; pointer-events: none; transition: opacity 0.3s; backdrop-filter: blur(4px); }
        .td-drawer-backdrop.open { opacity: 1; pointer-events: auto; }
        .td-drawer { position: fixed; top: 0; right: 0; width: 400px; max-width: 100vw; height: 100vh; background: var(--main-bg); border-left: 1px solid var(--card-border); z-index: 50; transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: -10px 0 30px rgba(0,0,0,0.5); }
        .td-drawer.open { transform: translateX(0); }
        .td-drawer-content { display: flex; flex-direction: column; height: 100%; }
        .td-drawer-header { padding: 24px; border-bottom: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: flex-start; background: var(--surface-container); }
        .td-drawer-header h2 { font-size: 16px; font-weight: 800; color: var(--text-primary); margin: 0 0 4px; }
        .td-drawer-header p { font-size: 12px; color: var(--text-muted); margin: 0; }
        .td-drawer-body { padding: 24px; overflow-y: auto; flex: 1; }
        
        .td-timeline { border-left: 2px solid var(--card-border-strong); margin-left: 10px; padding-left: 20px; }
        .td-timeline-item { position: relative; margin-bottom: 24px; }
        .td-timeline-dot { position: absolute; left: -27px; top: 0; width: 12px; height: 12px; border-radius: 50%; background: var(--text-primary); border: 2px solid var(--main-bg); }
        .td-timeline-card { background: var(--surface-container); border: 1px solid var(--card-border); border-radius: 8px; padding: 12px; }
        .td-timeline-title { font-size: 13px; font-weight: 800; color: var(--text-primary); margin-bottom: 4px; }
        .td-timeline-meta { font-size: 11px; color: var(--text-muted); margin-bottom: 8px; }
        .td-timeline-details { font-size: 12px; color: var(--text-secondary); }
        .td-timeline-ip { font-size: 11px; font-family: monospace; color: var(--text-muted); margin-top: 8px; background: var(--surface-container-highest); padding: 2px 6px; border-radius: 4px; display: inline-block; }

        @keyframes td-pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        @keyframes td-spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}

function MetricCard({ title, val, icon: Icon, color, glow, subtitle, loading }) {
  return (
    <div className={`td-metric-card ${glow ? 'glow' : ''}`}>
      <div className="td-metric-header">
        <span>{title}</span>
        <div className="td-metric-icon" style={{ background: `color-mix(in srgb, ${color} 15%, transparent)`, color }}>
          <Icon size={16} />
        </div>
      </div>
      {loading ? (
        <div className="td-skeleton-num" />
      ) : (
        <>
          <div className="td-metric-val">{val}</div>
          {subtitle && <div className="td-metric-sub">{subtitle}</div>}
        </>
      )}
    </div>
  )
}
