export default function SessionRow({ session, isOpen, onToggle, index }) {
  const mins = Math.floor(session.total_seconds / 60)
  const secs = session.total_seconds % 60
  const duration = session.total_seconds > 0
    ? (mins > 0 ? `${mins}m ${secs}s` : `${secs}s`)
    : `${session.page_count} pages`
  const browserIcon = session.browser === 'Chrome' ? 'ti-brand-chrome'
    : session.browser === 'Firefox' ? 'ti-brand-firefox'
    : session.browser === 'Edge' ? 'ti-brand-edge'
    : session.browser === 'Safari' ? 'ti-brand-safari'
    : 'ti-browser'

  return (
    <div style={{ flexShrink: 0, background: 'var(--panel-bg)', border: `1px solid ${isOpen ? 'var(--card-border)' : 'var(--card-border)'}`, borderRadius: 10, overflow: 'hidden' }}>
      <div
        onClick={onToggle}
        style={{ padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
      >
        <div style={{ width: 28, height: 28, borderRadius: 7, background: 'var(--card-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <i className={`ti ${browserIcon}`} style={{ fontSize: 14, color: '#38bdf8' }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: session.user_email === 'Anonymous' ? '#94a3b8' : '#e2e8f0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {session.user_email}
          </div>
          <div style={{ fontSize: 10.5, color: '#64748b', marginTop: 2 }}>
            {String(session.session_start).slice(0, 16).replace('T', ' ')} · {session.browser}
          </div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#38bdf8', fontFamily: "'DM Mono', monospace" }}>{duration}</div>
          <div style={{ fontSize: 10, color: '#64748b' }}>{session.page_count} pg</div>
        </div>
        <i className={`ti ${isOpen ? 'ti-chevron-up' : 'ti-chevron-down'}`} style={{ color: '#64748b', fontSize: 12 }} />
      </div>
      {isOpen && (
        <div style={{ borderTop: '1px solid #111c30', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 5 }}>
          <div style={{ fontSize: 10, color: '#475569', fontFamily: "'DM Mono', monospace" }}>{session.ip_address}</div>
          {session.pages.map((p, pi) => (
            <div key={pi} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#94a3b8' }}>
              <span style={{ color: '#475569', minWidth: 16 }}>{pi + 1}.</span>
              <span style={{ flex: 1 }}>{p}</span>
              <span style={{ color: '#64748b', fontFamily: "'DM Mono', monospace" }}>{String(session.timestamps[pi] || '').slice(11, 19)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
