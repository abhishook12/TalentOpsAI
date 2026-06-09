import { NavLink, useLocation } from 'react-router-dom'
import { clearStoredToken } from '../services/api'

const nav = [
  { to: '/', label: 'Dashboard', icon: 'ti-layout-dashboard' },
  { to: '/recruiters', label: 'Recruiters', icon: 'ti-users' },
  { to: '/companies', label: 'Companies', icon: 'ti-building' },
  { to: '/directory', label: 'States', icon: 'ti-map-2' },
  { to: '/analytics', label: 'Analytics', icon: 'ti-chart-bar' },
  { to: '/upload', label: 'ETL', icon: 'ti-upload' },
  { to: '/ai-search', label: 'AI Search', icon: 'ti-search' },
  { to: '/admin', label: 'Admin Ops', icon: 'ti-shield-lock' },
]

export default function Sidebar() {
  const location = useLocation()

  const logoutSoon = () => {
    localStorage.removeItem('auth_session')
    sessionStorage.removeItem('auth_session')
    clearStoredToken('admin')
    clearStoredToken('app')
    window.location.reload()
  }

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      minHeight: '100dvh',
      background: 'linear-gradient(180deg, #191919 0%, #141414 100%)',
      borderRight: '1px solid var(--sidebar-border)',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      flexShrink: 0,
      zIndex: 20,
    }}>
      <div style={{ padding: '22px 18px 18px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 14,
            background: 'linear-gradient(135deg, #d8d8d8, #8c8c8c)',
            display: 'grid',
            placeItems: 'center',
            color: '#111',
            boxShadow: '0 12px 28px rgba(0,0,0,0.22)',
            flexShrink: 0,
          }}>
            <i className="ti ti-radar" style={{ fontSize: 20 }} />
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ color: '#f3f3f3', fontSize: 18, fontWeight: 900, letterSpacing: '-0.03em', lineHeight: 1.05 }}>REC-INTEL v4.0</div>
            <div style={{ color: 'rgba(255,255,255,0.62)', fontSize: 12, fontWeight: 700, marginTop: 6, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Operational Command
            </div>
          </div>
        </div>
      </div>

      <nav style={{ flex: 1, padding: '14px 12px', overflowY: 'auto' }}>
        {nav.map(({ to, label, icon }) => {
          const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '12px 14px',
                marginBottom: 6,
                borderRadius: 14,
                textDecoration: 'none',
                color: active ? '#ffffff' : 'rgba(255,255,255,0.72)',
                background: active ? 'rgba(255,255,255,0.05)' : 'transparent',
                border: active ? '1px solid rgba(255,255,255,0.08)' : '1px solid transparent',
                borderLeft: active ? '4px solid #d5d5d5' : '4px solid transparent',
                boxShadow: active ? 'inset 0 1px 0 rgba(255,255,255,0.05)' : 'none',
                transition: 'all 0.15s ease',
                fontSize: 13.5,
                fontWeight: active ? 900 : 700,
                letterSpacing: '0.01em',
              }}
            >
              <i className={`ti ${icon}`} style={{ fontSize: 18, opacity: active ? 1 : 0.88 }} />
              <span>{label}</span>
            </NavLink>
          )
        })}
      </nav>

      <div style={{ padding: '12px 14px 18px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <button
          onClick={logoutSoon}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '12px 14px',
            borderRadius: 14,
            border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(255,255,255,0.05)',
            color: '#f3f3f3',
            fontSize: 13.5,
            fontWeight: 800,
            textAlign: 'left',
            cursor: 'pointer',
          }}
        >
          <i className="ti ti-logout" style={{ fontSize: 18 }} />
          Logout
        </button>
      </div>

      <div style={{ padding: '0 14px 16px' }}>
        <div style={{
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 16,
          background: 'rgba(255,255,255,0.05)',
          padding: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}>
          <div style={{
            width: 42,
            height: 42,
            borderRadius: 14,
            background: 'linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0.08))',
            display: 'grid',
            placeItems: 'center',
            color: '#f2f2f2',
            border: '1px solid rgba(255,255,255,0.12)',
          }}>
            <i className="ti ti-shield-check" style={{ fontSize: 20 }} />
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: '#f3f3f3' }}>System Operator</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.62)', marginTop: 2 }}>Terminal 01-A</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
