import { useState, useEffect } from 'react'
import { Link as NavLink, useLocation } from '@tanstack/react-router'
import api, { clearStoredToken } from '../services/api'
import { LayoutDashboard, Activity, Users, Map, BarChart2, Search, Eye, Radar, LogOut, ShieldCheck, Settings, UserCircle, HeartPulse, UserCog, Server, Shield, Mail, Layers, Laptop, Globe, MessageSquare } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Sidebar() {
  const location = useLocation()
  const { isAdmin, user } = useAuth()
  const [pendingDevicesCount, setPendingDevicesCount] = useState(0)

  useEffect(() => {
    if (isAdmin) {
      const fetchPending = async () => {
        try {
          const res = await api.get('/admin/devices/pending/count')
          const raw = res?.data
          const resolvedCount = typeof raw === 'number'
            ? raw
            : typeof raw?.count === 'number'
            ? raw.count
            : typeof raw?.data?.count === 'number'
            ? raw.data.count
            : 0
          setPendingDevicesCount(resolvedCount)
        } catch (e) {
          setPendingDevicesCount(0)
        }
      }
      fetchPending()
      const interval = setInterval(() => {
        if (typeof document !== 'undefined' && document.hidden) return;
        fetchPending()
      }, 60000)
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
    { to: '/search', label: 'Search', icon: Search },
    { to: '/download-scout', label: 'Desktop Scout', icon: Laptop, badge: 'v2.14.1', badgeVariant: 'version' },
    { isGroupHeader: true, label: 'Account' },
    { to: '/profile', label: 'Profile', icon: UserCircle },
    { to: '/settings', label: 'Settings', icon: Settings },
  ]

  const adminNav = [
    { isGroupHeader: true, label: 'Administration' },
    { to: '/admin', label: 'Overview', icon: LayoutDashboard },
    { to: '/admin/teams-harvest', label: 'Teams Live Stream', icon: MessageSquare, badge: 'LIVE', badgeVariant: 'teams' },
    { to: '/admin/scout-contributors', label: 'Scout Contributors', icon: Users },
    { to: '/admin/staging', label: 'Staging Pipeline', icon: Layers },
    { to: '/admin/web-harvest', label: 'Web Harvesting', icon: Globe, badge: '24/7', badgeVariant: 'webharvest' },
    { to: '/sentinel', label: 'Data Quality', icon: HeartPulse },
    { to: '/review-queue', label: 'Review Queue', icon: Search },
    { to: '/mailintel', label: 'Mail Intel', icon: Mail },
    { to: '/admin/users', label: 'User Management', icon: UserCog },
    { to: '/admin/visitor-analytics', label: 'Visitor Analytics', icon: Eye },
    { 
      to: '/admin/devices', 
      label: 'Trusted Devices', 
      icon: ShieldCheck,
      badge: pendingDevicesCount > 0 ? pendingDevicesCount : null
    },
    { to: '/activity', label: 'Activity Logs', icon: Activity },
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
      <div style={{ padding: '24px 20px', flexShrink: 0 }}>
        
        <NavLink to="/" style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, textDecoration: 'none', color: 'inherit', cursor: 'pointer' }} title="TalentOps Home">
          <img 
            src="/talentops-logo.png" 
            alt="TalentOps" 
            style={{ 
              width: 34, 
              height: 34, 
              borderRadius: 6, 
              objectFit: 'contain',
              flexShrink: 0,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
            }} 
          />
          <div style={{
            fontSize: 18,
            fontWeight: 600,
            lineHeight: 1.15,
            letterSpacing: '-0.015em',
            color: 'var(--text-primary)',
          }}>
            TalentOps
          </div>
        </NavLink>

        <div style={{ minWidth: 0 }}>
          <div style={{ color: 'var(--text-primary)', fontSize: 13.5, fontWeight: 600 }}>
            {isAdmin ? 'Admin Console' : 'TalentOps Intelligence'}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 500, marginTop: 2, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            {isAdmin ? 'OPERATIONS' : 'RECRUITER WORKSPACE'}
          </div>
        </div>
      </div>

      <nav style={{ flex: 1, minHeight: 0, padding: '0 12px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 3 }}>
        {nav.map((item, index) => {
          if (item.isGroupHeader) {
            return (
              <div key={`header-${index}`} style={{
                color: 'var(--text-muted)',
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                padding: '22px 12px 6px',
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
                minHeight: 38,
                padding: '8px 12px',
                borderRadius: 6,
                textDecoration: 'none',
                outline: 'none',
                boxShadow: 'none',
                border: 'none',
                color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                background: active ? 'var(--sidebar-active-bg)' : 'transparent',
                fontSize: 13.5,
                fontWeight: active ? 600 : 500,
                position: 'relative',
                transition: 'background 0.15s ease, color 0.15s ease'
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
                  left: 0,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 3,
                  height: 20,
                  background: 'var(--brand)',
                  borderRadius: '0 3px 3px 0'
                }} />
              )}
              <Icon size={17} strokeWidth={active ? 2.2 : 1.8} style={{ color: active ? 'var(--brand)' : 'var(--text-secondary)', flexShrink: 0 }} />
              <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</span>
              {item.badge && (
                <div style={{
                  background: item.badgeVariant === 'pending' || item.badgeVariant === 'danger' || (typeof item.badge === 'number' && item.badge > 0)
                    ? 'rgba(230, 184, 117, 0.16)'
                    : 'rgba(184, 213, 160, 0.14)',
                  color: item.badgeVariant === 'pending' || item.badgeVariant === 'danger' || (typeof item.badge === 'number' && item.badge > 0)
                    ? 'var(--warning)'
                    : 'var(--brand)',
                  border: item.badgeVariant === 'pending' || item.badgeVariant === 'danger' || (typeof item.badge === 'number' && item.badge > 0)
                    ? '1px solid rgba(230, 184, 117, 0.35)'
                    : '1px solid rgba(184, 213, 160, 0.35)',
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '2px 7px',
                  borderRadius: '4px',
                  lineHeight: 1.2,
                  flexShrink: 0
                }}>
                  {item.badge}
                </div>
              )}
            </NavLink>
          )
        })}
      </nav>

      <div style={{
        padding: '20px 16px',
        borderTop: '1px solid var(--sidebar-border)',
        flexShrink: 0,
      }}>
        {user && (
          <NavLink
            to="/profile"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              marginBottom: 12,
              padding: '6px 8px',
              borderRadius: 6,
              textDecoration: 'none',
              transition: 'background 0.15s ease',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--hover-bg)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            title="View & Edit Profile"
          >
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="User Avatar" style={{ width: 34, height: 34, borderRadius: '50%', objectFit: 'cover', border: '1px solid var(--card-border)' }} />
            ) : (
              <div style={{ width: 34, height: 34, borderRadius: '50%', background: 'var(--bg-elevated)', border: '1px solid var(--card-border)', display: 'grid', placeItems: 'center', color: 'var(--text-primary)', fontWeight: 600, fontSize: 13 }}>
                {user.first_name?.[0] || 'U'}
              </div>
            )}
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.first_name} {user.last_name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.email}
              </div>
            </div>
          </NavLink>
        )}

        <button
          onClick={logoutSoon}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '8px 8px',
            borderRadius: 6,
            border: 'none',
            background: 'transparent',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: 13.5,
            fontWeight: 500,
            transition: 'all 0.15s ease',
            textAlign: 'left'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = '#ffffff'
            e.currentTarget.style.background = 'var(--hover-bg)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'var(--text-secondary)'
            e.currentTarget.style.background = 'transparent'
          }}
        >
          <LogOut size={17} strokeWidth={1.8} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
