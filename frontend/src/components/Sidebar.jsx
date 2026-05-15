import { NavLink, useLocation } from 'react-router-dom'

const nav = [
  { to: '/', label: 'Dashboard', icon: 'ti-layout-dashboard' },
  { to: '/recruiters', label: 'Recruiters', icon: 'ti-users' },
  { to: '/candidates', label: 'Candidates', icon: 'ti-user-check' },
  { to: '/submissions', label: 'Submissions', icon: 'ti-file-text' },
  { to: '/analytics', label: 'Analytics', icon: 'ti-chart-bar' },
  { to: '/ai-search', label: 'AI Search', icon: 'ti-search', accent: true },
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
    }}>
      {/* Logo */}
      <div style={{
        padding: '24px 20px',
        borderBottom: '1px solid var(--sidebar-border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: 34, height: 34,
            background: '#185FA5',
            borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <i className="ti ti-bolt" style={{ color: '#fff', fontSize: 18 }} />
          </div>
          <div>
            <div style={{ color: '#f1f5f9', fontSize: 14, fontWeight: 500, letterSpacing: '-0.01em' }}>TalentOps AI</div>
            <div style={{ color: '#475569', fontSize: 11 }}>Recruitment Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 10px' }}>
        <div style={{ fontSize: 10, fontWeight: 500, letterSpacing: '0.08em', color: '#334155', padding: '0 8px 8px', textTransform: 'uppercase' }}>
          Navigation
        </div>
        {nav.map(({ to, label, icon, accent }) => {
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
                color: active ? '#f1f5f9' : accent ? '#7dd3fc' : '#94a3b8',
                background: active ? '#1e293b' : 'transparent',
                transition: 'all 0.12s ease',
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = '#1a2335' }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
            >
              <i className={`ti ${icon}`} style={{ fontSize: 16, flexShrink: 0 }} aria-hidden="true" />
              {label}
              {accent && (
                <span style={{
                  marginLeft: 'auto', fontSize: 10, fontWeight: 500,
                  background: 'rgba(125,211,252,0.12)', color: '#7dd3fc',
                  padding: '2px 7px', borderRadius: '4px',
                }}>AI</span>
              )}
              {active && (
                <span style={{
                  marginLeft: 'auto', width: 5, height: 5,
                  borderRadius: '50%', background: '#185FA5',
                  flexShrink: 0,
                }} />
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
            background: '#1e3a5f',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, color: '#7dd3fc', fontWeight: 500,
            border: '1px solid #1e4976',
            flexShrink: 0,
          }}>A</div>
          <div>
            <div style={{ color: '#e2e8f0', fontSize: 12, fontWeight: 500 }}>Admin</div>
            <div style={{ color: '#475569', fontSize: 11 }}>Free plan</div>
          </div>
          <i className="ti ti-settings" style={{ marginLeft: 'auto', color: '#334155', fontSize: 15, cursor: 'pointer' }} aria-hidden="true" />
        </div>
      </div>
    </aside>
  )
}
