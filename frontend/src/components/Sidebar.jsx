import { NavLink, useLocation } from 'react-router-dom'

const nav = [
  { to: '/', label: 'Dashboard', icon: 'ti-layout-dashboard' },
  { to: '/recruiters', label: 'Recruiters', icon: 'ti-users' },
  { to: '/directory', label: 'State Directory', icon: 'ti-map-2' },
  { to: '/companies', label: 'Company Directory', icon: 'ti-building-community' },
  { to: '/analytics', label: 'Analytics', icon: 'ti-chart-bar' },
  { to: '/upload', label: 'ETL Upload', icon: 'ti-upload' },
  { to: '/ai-search', label: 'AI Search', icon: 'ti-search', accent: true },
]

export default function Sidebar() {
  const location = useLocation()
  const adminActive = location.pathname.startsWith('/admin')

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      minHeight: '100vh',
      background: 'linear-gradient(180deg, var(--sidebar-bg), #090f1a 70%)',
      borderRight: '1px solid var(--sidebar-border)',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      height: '100vh',
      flexShrink: 0,
      boxShadow: 'inset -1px 0 0 rgba(255,255,255,0.03)',
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid var(--sidebar-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32,
            background: 'linear-gradient(135deg, var(--accent), #3b82f6)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 14px var(--accent-glow)',
            flexShrink: 0,
          }}>
            <i className="ti ti-bolt" style={{ color: '#fff', fontSize: 16 }} />
          </div>
          <div>
            <div style={{ color: 'var(--text-primary)', fontSize: 13.5, fontWeight: 600, letterSpacing: '-0.01em' }}>TalentOps AI</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 10.5, marginTop: 1 }}>Recruitment Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 8px', overflowY: 'auto' }}>
        <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--text-muted)', padding: '0 8px 8px', textTransform: 'uppercase' }}>
          Navigation
        </div>
        {nav.map(({ to, label, icon, accent }) => {
          const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              style={{
                display: 'flex', alignItems: 'center', gap: 9,
                padding: '7px 10px', borderRadius: 7, marginBottom: 1,
                textDecoration: 'none', fontSize: 13, fontWeight: active ? 500 : 400,
                color: active ? 'var(--text-primary)' : accent ? 'var(--accent-light)' : 'var(--text-secondary)',
                background: active ? (accent ? 'var(--accent-bg)' : 'rgba(255,255,255,0.05)') : 'transparent',
                transition: 'all 0.2s ease',
                borderLeft: active ? `2px solid ${accent ? 'var(--accent)' : '#3b82f6'}` : '2px solid transparent',
              }}
              onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--text-primary)' } }}
              onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = accent ? 'var(--accent-light)' : 'var(--text-secondary)' } }}
            >
              <i className={`ti ${icon}`} style={{ fontSize: 15, flexShrink: 0, color: active ? (accent ? 'var(--accent-light)' : '#3b82f6') : 'inherit' }} aria-hidden="true" />
              {label}
              {accent && (
                <span style={{
                  marginLeft: 'auto', fontSize: 9.5, fontWeight: 700,
                  background: 'var(--accent-bg)', color: 'var(--accent-light)',
                  padding: '2px 6px', borderRadius: 4, letterSpacing: '0.04em',
                }}>AI</span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Admin — opens Admin Terminal */}
      <div style={{ padding: '12px 14px', borderTop: '1px solid var(--sidebar-border)' }}>
        <NavLink
          to="/admin"
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '8px 10px', borderRadius: 8, textDecoration: 'none',
            background: adminActive ? 'var(--accent-bg)' : 'transparent',
            border: adminActive ? '1px solid rgba(34,211,238,0.35)' : '1px solid transparent',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={e => { if (!adminActive) e.currentTarget.style.background = 'rgba(34,211,238,0.08)' }}
          onMouseLeave={e => { if (!adminActive) e.currentTarget.style.background = 'transparent' }}
        >
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: 'linear-gradient(135deg, var(--accent), #3b82f6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', flexShrink: 0,
            boxShadow: adminActive ? '0 0 12px var(--accent-glow)' : 'none',
          }}>
            <i className="ti ti-terminal-2" style={{ fontSize: 15 }} aria-hidden="true" />
          </div>
          <div>
            <div style={{ color: 'var(--text-primary)', fontSize: 12, fontWeight: 500 }}>Admin</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 10.5 }}>Admin Terminal</div>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            {adminActive && (
              <span style={{ fontSize: 9, fontWeight: 700, background: 'var(--accent-bg)', color: 'var(--accent-light)', padding: '2px 6px', borderRadius: 4, letterSpacing: '0.05em' }}>OPEN</span>
            )}
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#3fb950', boxShadow: '0 0 6px #3fb950' }} title="Online" />
          </div>
        </NavLink>
      </div>
    </aside>
  )
}
