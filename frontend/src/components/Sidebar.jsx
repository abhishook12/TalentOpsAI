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
      background: 'var(--sidebar-bg)',
      borderRight: '1px solid var(--sidebar-border)',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      height: '100vh',
      flexShrink: 0,
      transition: 'background 0.3s ease',
    }}>
      {/* Logo */}
      <div style={{
        padding: '24px 20px',
        borderBottom: '1px solid var(--sidebar-border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: 34, height: 34,
            background: 'var(--accent)',
            borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <i className="ti ti-bolt" style={{ color: '#fff', fontSize: 18 }} />
          </div>
          <div>
            <div style={{ color: 'var(--text-primary)', fontSize: 14, fontWeight: 500, letterSpacing: '-0.01em' }}>TalentOps AI</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 11 }}>Recruitment Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 10px' }}>
        <div style={{ fontSize: 10, fontWeight: 500, letterSpacing: '0.08em', color: 'var(--text-secondary)', padding: '0 8px 8px', textTransform: 'uppercase' }}>
          Navigation
        </div>
        {nav.map(({ to, label, icon, accent, admin }) => {
          const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '9px',
                padding: '8px 10px',
                borderRadius: '7px',
                marginBottom: '1px',
                textDecoration: 'none',
                fontSize: '13px',
                fontWeight: active ? 500 : 400,
                color: active ? '#fff' : admin ? '#f87171' : accent ? 'var(--accent-hover)' : 'var(--text-muted)',
                background: active ? (admin ? '#7f1d1d' : 'var(--accent)') : 'transparent',
                transition: 'all 0.12s ease',
                borderTop: admin ? '1px solid var(--sidebar-border)' : 'none',
                marginTop: admin ? '8px' : '0',
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = admin ? '#2d0a0a' : 'var(--bg-hover)' }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
            >
              <i className={`ti ${icon}`} style={{ fontSize: 16, flexShrink: 0 }} aria-hidden="true" />
              {label}
              {accent && (
                <span style={{
                  marginLeft: 'auto', fontSize: 10, fontWeight: 500,
                  background: 'var(--accent-bg)', color: 'var(--accent)',
                  padding: '2px 7px', borderRadius: '4px',
                }}>AI</span>
              )}
              {admin && !active && (
                <span style={{
                  marginLeft: 'auto', fontSize: 9.5, fontWeight: 700,
                  background: 'rgba(239,68,68,0.15)', color: '#f87171',
                  padding: '2px 7px', borderRadius: '4px', letterSpacing: '0.05em',
                }}>ADMIN</span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div style={{
        padding: '14px 18px',
        borderTop: '1px solid var(--sidebar-border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: 30, height: 30, borderRadius: '50%',
            background: 'var(--accent-bg)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, color: 'var(--accent)', fontWeight: 500,
            border: '1px solid var(--accent)',
            flexShrink: 0,
          }}>A</div>
          <div>
            <div style={{ color: 'var(--text-primary)', fontSize: 12, fontWeight: 500 }}>Admin</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 11 }}>Free plan</div>
          </div>
          <i className="ti ti-settings" style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: 15, cursor: 'pointer' }} aria-hidden="true" />
        </div>
      </div>
    </aside>
  )
}

