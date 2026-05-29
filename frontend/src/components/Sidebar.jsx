import { NavLink, useLocation } from 'react-router-dom'

const nav = [
  { to: '/', label: 'Dashboard', icon: 'ti-layout-dashboard' },
  { to: '/recruiters', label: 'Recruiters', icon: 'ti-users' },
  { to: '/companies', label: 'Companies', icon: 'ti-building' },
  { to: '/directory', label: 'States', icon: 'ti-map-2' },
  { to: '/analytics', label: 'Analytics', icon: 'ti-chart-bar' },
  { to: '/upload', label: 'ETL', icon: 'ti-upload' },
  { to: '/ai-search', label: 'AI Search', icon: 'ti-search' },
  { to: '/admin', label: 'Profile', icon: 'ti-user-circle' },
]

export default function Sidebar() {
  const location = useLocation()
  const logoutSoon = () => {
    console.log('[Coming soon] Logout')
    alert('Logout: Coming soon')
  }

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
    }}>
      <div style={{ padding: '20px 16px 14px', borderBottom: '1px solid var(--sidebar-border)' }}>
        <div style={{ color: '#111318', fontSize: 12, fontWeight: 700 }}>Intelligence</div>
        <div style={{ color: 'var(--text-muted)', fontSize: 10, letterSpacing: '0.08em', marginTop: 2 }}>STAFFING SYSTEMS</div>
      </div>

      <nav style={{ flex: 1, padding: '14px 10px', overflowY: 'auto' }}>
        {nav.map(({ to, label, icon }) => {
          const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 10px',
                borderRadius: 8,
                marginBottom: 4,
                textDecoration: 'none',
                fontSize: 13,
                fontWeight: active ? 600 : 500,
                color: active ? '#111318' : '#4b5260',
                background: active ? '#e7e7e5' : 'transparent',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = '#f5f5f3' }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
            >
              <i className={`ti ${icon}`} style={{ fontSize: 14 }} />
              {label}
            </NavLink>
          )
        })}
      </nav>

      <div style={{ padding: '8px 10px 0', borderTop: '1px solid var(--sidebar-border)' }}>
        <button
          onClick={logoutSoon}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '9px 10px',
            borderRadius: 8,
            marginBottom: 8,
            border: '1px solid var(--card-border)',
            background: 'transparent',
            color: 'var(--text-secondary)',
            fontSize: 13,
            fontWeight: 500,
            textAlign: 'left',
          }}
        >
          <i className="ti ti-logout" style={{ fontSize: 14 }} />
          Logout
        </button>
      </div>

      <div style={{ padding: '0 12px 12px' }}>
        <div style={{
          border: '1px solid var(--card-border)',
          borderRadius: 8,
          background: '#fbfbfa',
          padding: '8px 10px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <div style={{
            width: 20,
            height: 20,
            borderRadius: 6,
            background: '#e7e7e5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#1d222a',
            fontSize: 12,
          }}>
            <i className="ti ti-shield-lock" />
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#1b1f25' }}>Admin Ops</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>v2.4.1</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
