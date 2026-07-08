import re

path = 'C:/TalentOpsAI/frontend/src/pages/AdminTerminal.jsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update state variables
state_target = """  const [visitorLogs, setVisitorLogs] = useState(null)
  const [visitorSummary, setVisitorSummary] = useState(null)
  const [logDays, setLogDays] = useState(7)
  const [expandedSession, setExpandedSession] = useState(null)
  const [loadingLogs, setLoadingLogs] = useState(false)"""

state_replace = """  const [sessions, setSessions] = useState(null)
  const [sessionsSearch, setSessionsSearch] = useState('')
  const [sessionsFilter, setSessionsFilter] = useState('all')
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const sessionsInterval = useRef(null)
  const [visitorSummary, setVisitorSummary] = useState(null)
  const [logDays, setLogDays] = useState(7)
  const [expandedSession, setExpandedSession] = useState(null)
  const [loadingLogs, setLoadingLogs] = useState(false)"""

content = content.replace(state_target, state_replace)

# 2. Add loadSessions function and polling effect
func_target = """  const loadVisitorLogs = async (days = logDays) => {
    setLoadingLogs(true)
    log(`Loading visitor logs for last ${days} days…`)
    try {
      const [logsRes, summRes] = await Promise.all([
        adminAxios.get(`/admin/visitor-logs?days=${days}&limit=300`),
        adminAxios.get(`/admin/visitor-summary?days=${days}`),
      ])
      setVisitorLogs(logsRes.data)
      setVisitorSummary(summRes.data)
      log(`✓ Loaded ${logsRes.data.total} sessions`, 'ok')
    } catch (e) {
      log('✗ Failed to load visitor logs: ' + e.message, 'error')
    }
    setLoadingLogs(false)
  }"""

func_replace = """  const loadVisitorLogs = async (days = logDays) => {
    setLoadingLogs(true)
    try {
      const summRes = await adminAxios.get(`/admin/visitor-summary?days=${days}`)
      setVisitorSummary(summRes.data)
    } catch (e) { log('✗ Failed to load visitor summary', 'error') }
    setLoadingLogs(false)
  }

  const loadSessions = useCallback(async () => {
    try {
      const res = await adminAxios.get(`/admin/active-sessions?days=${logDays}&limit=300&search=${encodeURIComponent(sessionsSearch)}&filter_type=${sessionsFilter}`)
      setSessions(res.data)
    } catch (e) {
      log('✗ Failed to load active sessions: ' + e.message, 'error')
    }
  }, [logDays, sessionsSearch, sessionsFilter, unlocked])

  useEffect(() => {
    if (activeTab === 'logbook' && unlocked) {
      loadVisitorLogs(logDays)
      loadSessions()
      sessionsInterval.current = setInterval(loadSessions, 5000)
    } else {
      if (sessionsInterval.current) clearInterval(sessionsInterval.current)
    }
    return () => { if (sessionsInterval.current) clearInterval(sessionsInterval.current) }
  }, [activeTab, unlocked, loadSessions])"""

content = content.replace(func_target, func_replace)

# 3. Rename "Visitor Log Book" to "Activity Monitor"
content = content.replace("{ id: 'logbook',   icon: 'ti-book',              label: 'Visitor Log Book' }", "{ id: 'logbook',   icon: 'ti-activity',              label: 'Activity Monitor' }")

# 4. Replace UI rendering in "logbook" tab
ui_target_start = "{/* ── VISITOR LOG BOOK TAB ── */}"
ui_target_end = "{/* ── ACTIVITY LOG TAB ── */}"

ui_chunk = content[content.find(ui_target_start):content.find(ui_target_end)]

new_ui_chunk = """{/* ── VISITOR LOG BOOK TAB ── */}
        {activeTab === 'logbook' && (
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            {/* Controls */}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 20, flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Search email or session ID..."
                value={sessionsSearch}
                onChange={e => setSessionsSearch(e.target.value)}
                style={{ background: '#0d1829', border: '1px solid #1e3a5f', color: '#e2e8f0', padding: '8px 14px', borderRadius: 8, fontSize: 13, minWidth: 240, outline: 'none' }}
              />
              <select value={sessionsFilter} onChange={e => setSessionsFilter(e.target.value)} style={{ background: '#0d1829', border: '1px solid #1e3a5f', color: '#e2e8f0', padding: '8px 14px', borderRadius: 8, fontSize: 13, outline: 'none' }}>
                <option value="all">All Activity</option>
                <option value="active">Active Now</option>
                <option value="admin">Admin Actions</option>
                <option value="uploads">Uploads (ETL)</option>
                <option value="ai">AI Searches</option>
                <option value="failed">Failed Actions</option>
              </select>
              {[1, 7, 30].map(d => (
                <button key={d} onClick={() => setLogDays(d)} style={{
                  background: logDays === d ? 'linear-gradient(135deg, #0ea5e9, #1d4ed8)' : '#0d1829',
                  border: '1px solid', borderColor: logDays === d ? '#0ea5e9' : '#1e3a5f',
                  color: logDays === d ? '#fff' : '#64748b', padding: '7px 18px', borderRadius: 8,
                  fontSize: 12.5, fontWeight: 500, cursor: 'pointer',
                }}>{d}D</button>
              ))}
              <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                 <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 10px #22c55e', animation: 'pulse-ring 2s infinite' }} />
                 <span style={{ fontSize: 12, color: '#94a3b8' }}>Live Updates</span>
              </div>
            </div>

            {/* Session list */}
            {sessions && (
              <Section title={`Live Activity Monitor (${sessions.total} sessions)`} icon="ti-activity">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 800, overflowY: 'auto' }}>
                  {sessions.sessions.map((s, i) => {
                    const isOpen = expandedSession === s.session_id
                    const mins = Math.floor(s.total_seconds / 60)
                    const secs = s.total_seconds % 60
                    const duration = s.total_seconds > 0
                      ? (mins > 0 ? `${mins}m ${secs}s` : `${secs}s`)
                      : `${s.pages.length} pages`
                    const browserIcon = s.browser === 'Chrome' ? 'ti-brand-chrome'
                      : s.browser === 'Firefox' ? 'ti-brand-firefox'
                      : s.browser === 'Edge' ? 'ti-brand-edge'
                      : s.browser === 'Safari' ? 'ti-brand-safari'
                      : 'ti-browser'
                    return (
                      <div key={i} style={{ background: '#0b1525', border: `1px solid ${isOpen ? '#38bdf8' : s.is_active ? '#22c55e44' : '#111c30'}`, borderRadius: 10, overflow: 'hidden', transition: 'border-color 0.15s' }}>
                        {/* Row header */}
                        <div
                          onClick={() => setExpandedSession(isOpen ? null : s.session_id)}
                          style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer', background: s.is_active ? '#22c55e08' : 'transparent' }}
                        >
                          <div style={{ width: 36, height: 36, borderRadius: 10, background: s.is_active ? '#22c55e22' : '#111c30', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                            <i className={`ti ${browserIcon}`} style={{ fontSize: 18, color: s.is_active ? '#22c55e' : '#38bdf8' }} />
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                               <div style={{ fontSize: 13, fontWeight: 700, color: s.user_email === 'Anonymous' ? '#64748b' : '#f8fafc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                 {s.user_email}
                               </div>
                               {s.is_active && <Badge color="#22c55e">ACTIVE NOW</Badge>}
                               {s.actions.length > 0 && <Badge color="#38bdf8">{s.actions.length} ACTIONS</Badge>}
                               {s.actions.some(a => a.status === 'failed') && <Badge color="#ef4444">ERRORS</Badge>}
                            </div>
                            <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                              Started: {s.start_time.slice(0, 16).replace('T', ' ')} · IP: {s.ip_address} · {s.browser}
                            </div>
                          </div>
                          
                          <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 8 }}>
                            <div style={{ fontSize: 13, fontWeight: 600, color: '#38bdf8', fontFamily: "'DM Mono', monospace" }}>{duration}</div>
                            <div style={{ fontSize: 11, color: '#475569' }}>{s.pages.length} pages</div>
                          </div>
                          <i className={`ti ${isOpen ? 'ti-chevron-up' : 'ti-chevron-down'}`} style={{ color: '#475569', fontSize: 14, flexShrink: 0, marginLeft: 10 }} />
                        </div>

                        {/* Expanded detail */}
                        {isOpen && (
                          <div style={{ borderTop: '1px solid #111c30', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                            
                            {/* Actions Timeline */}
                            {s.actions.length > 0 && (
                                <div>
                                    <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Action Timeline</div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        {s.actions.map((a, ai) => (
                                            <div key={ai} style={{ background: '#111c30', borderLeft: `3px solid ${a.status === 'success' ? '#22c55e' : '#ef4444'}`, padding: '10px 14px', borderRadius: '0 8px 8px 0', display: 'flex', alignItems: 'center', gap: 12 }}>
                                                <i className={`ti ${a.type === 'UPLOAD_ETL' ? 'ti-upload' : a.type === 'AI_SEARCH' ? 'ti-brain' : 'ti-bolt'}`} style={{ color: a.status === 'success' ? '#22c55e' : '#ef4444', fontSize: 16 }} />
                                                <div style={{ flex: 1 }}>
                                                    <div style={{ fontSize: 12.5, fontWeight: 600, color: '#e2e8f0' }}>{a.type}</div>
                                                    <div style={{ fontSize: 11, color: '#94a3b8', fontFamily: "'DM Mono', monospace", marginTop: 2 }}>{a.details}</div>
                                                </div>
                                                <span style={{ fontSize: 11, color: '#64748b', fontFamily: "'DM Mono', monospace" }}>{a.time.slice(11, 19)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Page trail */}
                            <div>
                                <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Page Views</div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                                  {s.pages.map((p, pi) => (
                                    <div key={pi} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                      <span style={{ fontSize: 10, color: '#475569', minWidth: 18, textAlign: 'right', fontFamily: "'DM Mono', monospace" }}>{pi + 1}</span>
                                      <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#1e3a5f', flexShrink: 0 }} />
                                      <span style={{ fontSize: 12, color: '#94a3b8', flex: 1 }}>{p.page}</span>
                                      <span style={{ fontSize: 11, color: '#475569', fontFamily: "'DM Mono', monospace" }}>{p.time.slice(11, 19)}</span>
                                      {p.duration > 0 && (
                                        <span style={{ fontSize: 10.5, color: '#38bdf8', background: '#0d1829', padding: '1px 7px', borderRadius: 99, fontFamily: "'DM Mono', monospace" }}>
                                          {p.duration}s
                                        </span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                            </div>

                          </div>
                        )}
                      </div>
                    )
                  })}
                  {sessions.sessions.length === 0 && (
                    <div style={{ color: '#475569', fontSize: 12.5, textAlign: 'center', padding: 24 }}>No sessions match your filters.</div>
                  )}
                </div>
              </Section>
            )}
          </div>
        )}

        """
content = content.replace(ui_chunk, new_ui_chunk)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated AdminTerminal.jsx successfully.")
