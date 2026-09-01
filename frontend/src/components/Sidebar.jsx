import { useState, useEffect } from 'react'
import { Link as NavLink, useLocation } from '@tanstack/react-router'
import api, { clearStoredToken } from '../services/api'
import { LayoutDashboard, Activity, Users, Map, BarChart2, Search, Eye, Radar, LogOut, ShieldCheck, Settings, UserCircle, HeartPulse, UserCog, Server, Shield, Mail, Puzzle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Sidebar() {
  const location = useLocation()
  const { isAdmin, user } = useAuth()
  const [backendVersion, setBackendVersion] = useState('loading...')
  const [pendingDevicesCount, setPendingDevicesCount] = useState(0)

  useEffect(() => {
    api.get('/version').then(res => setBackendVersion(res.data.version)).catch(() => setBackendVersion('unknown'))
  }, [])

  useEffect(() => {
    if (isAdmin) {
      const fetchPending = async () => {
        try {
          const res = await api.get('/admin/devices/pending/count')
          setPendingDevicesCount(res.data.count)
        } catch (e) {
          console.error('Failed to fetch pending devices', e)
        }
      }
      fetchPending()
      const interval = setInterval(fetchPending, 30000)
      return () => clearInterval(interval)
    }
  }, [isAdmin])

  const logoutSoon = () => {
    localStorage.removeItem('auth_session')
    sessionStorage.removeItem('auth_session')
    clearStoredToken()
    window.location.reload()
  }

  const userNav = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/campaigns', label: 'Campaigns', icon: Radar },
    { to: '/recruiters', label: 'Recruiters', icon: Users },
    { to: '/directory', label: 'Directory', icon: Map, aliases: ['/states', '/companies'] },
    { to: '/analytics', label: 'Analytics', icon: BarChart2 },
    { to: '/search', label: 'AI Search', icon: Search },
    { to: '/extension', label: 'Talent Scout', icon: Puzzle, badge: 'New' },
    { isGroupHeader: true, label: 'Account' },
    { to: '/profile', label: 'Profile', icon: UserCircle },
    { to: '/settings', label: 'Settings', icon: Settings },
  ]

  const adminNav = [
    { isGroupHeader: true, label: 'Command Center' },
    { to: '/admin', label: 'Admin Terminal', icon: LayoutDashboard },
    { to: '/sentinel', label: 'Data Quality Center', icon: HeartPulse },
    { to: '/review-queue', label: 'Review Queue', icon: Search },
    { to: '/mailintel', label: 'MAILINTEL', icon: Mail },
    { to: '/admin/users', label: 'User Management', icon: UserCog },
    { to: '/admin/visitor-analytics', label: 'Visitor Analytics', icon: Eye },
    { 
      to: '/admin/devices', 
      label: 'Trusted Devices', 
      icon: ShieldCheck,
      badge: pendingDevicesCount > 0 ? pendingDevicesCount : null
    },
    { to: '/activity', label: 'Activity Logs', icon: Activity },
    { to: '/admin/extension', label: 'Extension Scout', icon: Puzzle },
    { to: '/admin/jobs', label: 'Background Jobs', icon: Server },
    { to: '/admin/audit-logs', label: 'Audit Logs', icon: Shield },
    { to: '/admin/health', label: 'System Health', icon: HeartPulse },
    { to: '/admin/settings', label: 'Admin Settings', icon: Settings },
  ]

  const nav = isAdmin ? [...userNav, ...adminNav] : userNav

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      height: '100dvh',
      background: 'var(--sidebar-bg)',
      borderRight: '1px solid var(--sidebar-border)',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      flexShrink: 0,
      zIndex: 20,
    }}>
      <div style={{ padding: '32px 24px', flexShrink: 0 }}>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 32 }}>
          <div style={{
            fontSize: 24,
            fontWeight: 700,
            lineHeight: 1,
            letterSpacing: '-0.04em',
            color: 'var(--text-primary)',
            display: 'flex',
            alignItems: 'center',
            gap: 2
          }}>
            <span>T</span><span style={{ fontWeight: 400 }}>O</span>
          </div>
          <div style={{ 
            fontSize: 10, 
            fontWeight: 600, 
            letterSpacing: '0.25em', 
            color: 'var(--text-primary)' 
          }}>
            TALENT OPS
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 600 }}>
            {isAdmin ? 'Admin Console' : 'TalentOps'}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 10, fontWeight: 500, marginTop: 4, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            {isAdmin ? 'OPERATIONS' : 'RECRUITER INTEL'}
          </div>
        </div>
      </div>

      <nav style={{ flex: 1, minHeight: 0, padding: '0 12px 24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {nav.map((item, index) => {
          if (item.isGroupHeader) {
            return (
              <div key={`header-${index}`} style={{
                color: 'var(--text-muted)',
                fontSize: 10,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                padding: '24px 12px 8px',
              }}>
                {item.label}
              </div>
            )
          }

          const { to, label, icon: Icon, aliases = [] } = item
          const active = to === '/'
            ? location.pathname === '/'
            : location.pathname === to || location.pathname.startsWith(to + '/') || aliases.some((alias) => location.pathname === alias || location.pathname.startsWith(alias + '/'))
          
          return (
            <NavLink
              key={to}
              to={to}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '10px 12px',
                borderRadius: 6,
                textDecoration: 'none',
                color: active ? 'var(--sidebar-active-color, var(--text-primary))' : 'var(--text-secondary)',
                background: active ? 'var(--sidebar-active-bg)' : 'transparent',
                fontSize: 13,
                fontWeight: active ? 600 : 400,
                position: 'relative'
              }}
              onMouseEnter={(event) => {
                if (active) return
                event.currentTarget.style.background = 'var(--hover-bg)'
                event.currentTarget.style.color = 'var(--text-primary)'
              }}
              onMouseLeave={(event) => {
                if (active) return
                event.currentTarget.style.background = 'transparent'
                event.currentTarget.style.color = 'var(--text-secondary)'
              }}
            >
              {active && (
                <div style={{
                  position: 'absolute',
                  left: -12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 3,
                  height: 16,
                  background: 'var(--text-primary)',
                  borderRadius: '0 4px 4px 0'
                }} />
              )}
              <Icon size={16} strokeWidth={active ? 2.5 : 2} />
              <span style={{ flex: 1 }}>{label}</span>
              {item.badge && (
                <div style={{
                  background: 'var(--danger)',
                  color: 'white',
                  fontSize: '10px',
                  fontWeight: 600,
                  padding: '2px 6px',
                  borderRadius: '999px',
                }}>
                  {item.badge}
                </div>
              )}
            </NavLink>
          )
        })}
      </nav>

      <div style={{
        padding: '24px 24px',
        flexShrink: 0,
      }}>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="User Avatar" style={{ width: 32, height: 32, borderRadius: '50%', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--card-border)', display: 'grid', placeItems: 'center', color: 'var(--text-primary)', fontWeight: 600, fontSize: 12 }}>
                {user.first_name?.[0]}
              </div>
            )}
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.first_name} {user.last_name}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.email}
              </div>
            </div>
          </div>
        )}

        <button
          onClick={logoutSoon}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '10px 12px',
            borderRadius: 6,
            border: 'none',
            background: 'transparent',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: 13,
            fontWeight: 500,
            transition: 'all 0.15s',
            textAlign: 'left',
            marginLeft: -12
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = 'var(--text-primary)'
            e.currentTarget.style.background = 'var(--hover-bg, #1D1D1D)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--text-muted)'
            e.currentTarget.style.background = 'transparent'
          }}
        >
          <LogOut size={16} strokeWidth={2} />
          <span>Sign Out</span>
        </button>
        
        <div style={{
          marginTop: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          color: 'var(--text-muted)',
          fontSize: 10,
          fontFamily: 'var(--mono)',
          opacity: 0.6
        }}>
          <div>UI: {import.meta.env.VITE_APP_VERSION || 'local'}</div>
          <div>API: {backendVersion}</div>
        </div>
      </div>
    </aside>
  )
}
