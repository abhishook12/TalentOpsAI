import { NavLink, useLocation } from 'react-router-dom'

const nav = [
  { to: '/', label: 'Dashboard', icon: 'ti-layout-dashboard' },
  { to: '/recruiters', label: 'Recruiters', icon: 'ti-users' },
  { to: '/directory', label: 'State Directory', icon: 'ti-map-2' },
  { to: '/companies', label: 'Company Directory', icon: 'ti-building-community' },
  { to: '/analytics', label: 'Analytics', icon: 'ti-chart-bar' },
  { to: '/upload', label: 'ETL Upload', icon: 'ti-upload' },
  { to: '/ai-search', label: 'AI Search', icon: 'ti-search', accent: true },
  { to: '/admin', label: 'Admin Terminal', icon: 'ti-terminal-2', admin: true },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      minHeight: '100vh',
      background: '#0d1117',
      borderRight: '1px solid #1e2d3d',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      height: '100vh',
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid #1e2d3d' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32,
            background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 14px rgba(59,130,246,0.3)',
            flexShrink: 0,
          }}>
            <i className="ti ti-bolt" style={{ color: '#fff', fontSize: 16 }} />
          </div>
          <div>
            <div style={{ color: '#e6edf3', fontSize: 13.5, fontWeight: 600, letterSpacing: '-0.01em' }}>TalentOps AI</div>
            <div style={{ color: '#4d5869', fontSize: 10.5, marginTop: 1 }}>Recruitment Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 8px', overflowY: 'auto' }}>
        <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.1em', color: '#2d3f55', padding: '0 8px 8px', textTransform: 'uppercase' }}>
          Navigation
        </div>
        {nav.map(({ to, label, icon, accent, admin }) => {
          const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
          if (admin) {
            return (
              <div key={to} style={{ borderTop: '1px solid #1e2d3d', marginTop: 8, paddingTop: 8 }}>
                <NavLink
                  to={to}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 9,
                    padding: '7px 10px', borderRadius: 7, marginBottom: 1,
                    textDecoration: 'none', fontSize: 13, fontWeight: active ? 500 : 400,
                    color: active ? '#f85149' : '#f85149aa',
                    background: active ? 'rgba(248,81,73,0.12)' : 'transparent',
                    transition: 'all 0.12s ease',
                  }}
                  onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(248,81,73,0.08)' }}
                  onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
                >
                  <i className={`ti ${icon}`} style={{ fontSize: 15, flexShrink: 0 }} aria-hidden="true" />
                  {label}
                  <span style={{ marginLeft: 'auto', fontSize: 9, fontWeight: 700, background: 'rgba(248,81,73,0.15)', color: '#f85149', padding: '2px 6px', borderRadius: 4, letterSpacing: '0.05em' }}>ROOT</span>
                </NavLink>
              </div>
            )
          }
          return (
            <NavLink
              key={to}
              to={to}
              style={{
                display: 'flex', alignItems: 'center', gap: 9,
                padding: '7px 10px', borderRadius: 7, marginBottom: 1,
                textDecoration: 'none', fontSize: 13, fontWeight: active ? 500 : 400,
                color: active ? '#e6edf3' : accent ? '#60a5fa' : '#8b949e',
                background: active ? (accent ? 'rgba(59,130,246,0.18)' : '#1e2d3d') : 'transparent',
                transition: 'all 0.12s ease',
                borderLeft: active ? `2px solid ${accent ? '#3b82f6' : '#3b82f6'}` : '2px solid transparent',
              }}
              onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#e6edf3' } }}
              onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = accent ? '#60a5fa' : '#8b949e' } }}
            >
              <i className={`ti ${icon}`} style={{ fontSize: 15, flexShrink: 0, color: active ? (accent ? '#60a5fa' : '#3b82f6') : 'inherit' }} aria-hidden="true" />
              {label}
              {accent && (
                <span style={{
                  marginLeft: 'auto', fontSize: 9.5, fontWeight: 700,
                  background: 'rgba(59,130,246,0.15)', color: '#60a5fa',
                  padding: '2px 6px', borderRadius: 4, letterSpacing: '0.04em',
                }}>AI</span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: '12px 14px', borderTop: '1px solid #1e2d3d' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, color: '#fff', fontWeight: 600, flexShrink: 0,
          }}>A</div>
          <div>
            <div style={{ color: '#e6edf3', fontSize: 12, fontWeight: 500 }}>Admin</div>
            <div style={{ color: '#4d5869', fontSize: 10.5 }}>TalentOps AI</div>
          </div>
          <div style={{ marginLeft: 'auto', width: 7, height: 7, borderRadius: '50%', background: '#3fb950', boxShadow: '0 0 6px #3fb950' }} title="Online" />
        </div>
      </div>
    </aside>
  )
}
