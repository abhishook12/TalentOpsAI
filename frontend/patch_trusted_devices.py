import re

with open(r'C:\TalentOpsAI\frontend\src\pages\admin\TrustedDevices.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Active Sessions tab
content = content.replace(
    "{ id: 'Revoked', label: 'Revoked' }",
    "{ id: 'Revoked', label: 'Revoked' },\n    { id: 'Sessions', label: 'Active Sessions' }"
)

# Add states for sessions
state_declarations = """
  const [sessions, setSessions] = useState([])
  const [selectedSessions, setSelectedSessions] = useState([])
  const [loadingSessions, setLoadingSessions] = useState(false)
"""
content = content.replace(
    "const [searchQuery, setSearchQuery] = useState('')",
    "const [searchQuery, setSearchQuery] = useState('')\n" + state_declarations
)

# Fetch sessions when tab changes to 'Sessions'
fetch_logic = """
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
"""
content = content.replace(
    "const updateStatus = async (id, status) => {",
    fetch_logic + "\n  const updateStatus = async (id, status) => {"
)

# Add clear buttons to the top actions
top_actions = """
          <div className="cc-top-actions">
            <button className="cc-ghost-button" onClick={clearPendingDevices} style={{ color: 'var(--warning)' }}>
              Clear Pending
            </button>
            <button className="cc-ghost-button" onClick={clearAllDevices} style={{ color: 'var(--danger)' }}>
              Clear All Devices
            </button>
"""
content = content.replace(
    '<div className="cc-top-actions">',
    top_actions
)

# Render Sessions Table
sessions_table = """
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
"""
# We need to replace the tbody content. Let's find the map.
# Wait, let's inject a new THEAD for sessions too.
table_headers = """
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
"""
content = re.sub(
    r'<thead>\s*<tr>.*?</tr>\s*</thead>',
    table_headers,
    content,
    flags=re.DOTALL
)

# And replace the body.
content = content.replace(
    "{filteredDevices.map(d => (",
    sessions_table + "\n                    filteredDevices.map(d => ("
)
content = content.replace(
    "                    ))}\n                  </tbody>",
    "                    ))}\n                  )}</tbody>"
)

with open(r'C:\TalentOpsAI\frontend\src\pages\admin\TrustedDevices.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("TrustedDevices.jsx patched successfully.")
