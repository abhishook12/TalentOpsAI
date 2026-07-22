import React, { useState, useEffect } from 'react'
import { Link as NavLink, useLocation } from '@tanstack/react-router'
import api, { clearStoredToken } from '../services/api'
import { LayoutDashboard, Activity, Users, Map, BarChart2, Search, Eye, Radar, LogOut, ShieldCheck, Settings, UserCircle, HeartPulse, UserCog, Server, Shield } from 'lucide-react'
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
    { to: '/ai-search', label: 'AI Search', icon: Search },
    { isGroupHeader: true, label: 'Account' },
    { to: '/profile', label: 'Profile', icon: UserCircle },
    { to: '/settings', label: 'Settings', icon: Settings },
  ]

  const adminNav = [
    { isGroupHeader: true, label: 'Command Center' },
    { to: '/admin', label: 'Admin Terminal', icon: LayoutDashboard },
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
      background: 'linear-gradient(180deg, #191919 0%, #141414 100%)',
      borderRight: '1px solid var(--sidebar-border)',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      flexShrink: 0,
      zIndex: 20,
      overflow: 'visible',
    }}>
      <div style={{ padding: '22px 18px 18px', borderBottom: '1px solid var(--card-border)' }}>
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
            <ShieldCheck size={20} />
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ color: 'var(--text-primary)', fontSize: 18, fontWeight: 900, letterSpacing: '-0.03em', lineHeight: 1.05 }}>
              {isAdmin ? 'Admin Console' : 'TalentOps AI'}
            </div>
            <div style={{ color: 'rgba(255,255,255,0.62)', fontSize: 12, fontWeight: 700, marginTop: 6, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              {isAdmin ? 'Operations' : 'Recruiter Intel'}
            </div>
          </div>
        </div>
      </div>

      <nav style={{ flex: 1, minHeight: 0, padding: '14px 12px', overflowY: 'auto' }}>
        {nav.map((item, index) => {
          if (item.isGroupHeader) {
            return (
              <div key={`header-${index}`} style={{
                color: 'var(--text-muted)',
                fontSize: 11,
                fontWeight: 800,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                padding: '16px 14px 8px',
                marginTop: 8
              }}>
                {item.label}
              </div>
            )
          }

          const { to, label, icon: Icon, aliases = [] } = item
          const active = to === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(to) || aliases.some((alias) => location.pathname.startsWith(alias))
          
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
              onMouseEnter={(event) => {
                if (active) return
                event.currentTarget.style.background = 'rgba(255,255,255,0.08)'
                event.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'
                event.currentTarget.style.boxShadow = '0 10px 24px rgba(0,0,0,0.16)'
                event.currentTarget.style.transform = 'translateY(-1px)'
                event.currentTarget.style.color = '#ffffff'
              }}
              onMouseLeave={(event) => {
                if (active) return
                event.currentTarget.style.background = 'transparent'
                event.currentTarget.style.borderColor = 'transparent'
                event.currentTarget.style.boxShadow = 'none'
                event.currentTarget.style.transform = 'translateY(0)'
                event.currentTarget.style.color = 'rgba(255,255,255,0.72)'
              }}
            >
              <Icon size={18} strokeWidth={active ? 2.5 : 2} opacity={active ? 1 : 0.88} fill={active ? 'currentColor' : 'none'} />
              <span style={{ flex: 1 }}>{label}</span>
              {item.badge && (
                <div style={{
                  background: 'var(--danger)',
                  color: 'white',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  padding: '2px 6px',
                  borderRadius: '12px',
                  minWidth: '20px',
                  textAlign: 'center',
                  animation: 'pulse-badge 2s infinite'
                }}>
                  {item.badge}
                </div>
              )}
            </NavLink>
          )
        })}
      </nav>

      <div style={{
        padding: '10px 14px 12px',
        borderTop: '1px solid var(--card-border)',
        flexShrink: 0,
      }}>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 14px 16px', marginBottom: 8, borderBottom: '1px solid var(--card-border)' }}>
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="User Avatar" style={{ width: 32, height: 32, borderRadius: '50%', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #d8d8d8, #8c8c8c)', display: 'grid', placeItems: 'center', color: '#111', fontWeight: 800 }}>
                {user.first_name?.[0]}
              </div>
            )}
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
            padding: '12px 14px',
            borderRadius: 14,
            border: 'none',
            background: 'transparent',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: 13.5,
            fontWeight: 700,
            transition: 'all 0.2s',
            textAlign: 'left'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = '#ff6b6b'
            e.currentTarget.style.background = 'rgba(255, 107, 107, 0.08)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = 'rgba(255,255,255,0.6)'
            e.currentTarget.style.background = 'transparent'
          }}
        >
          <LogOut size={18} strokeWidth={2} />
          <span>Sign Out</span>
        </button>
        
        <div style={{
          marginTop: 12,
          paddingTop: 12,
          borderTop: '1px solid var(--card-border)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 4,
          color: 'var(--text-muted)',
          fontSize: 10,
          fontFamily: 'monospace',
          opacity: 0.6
        }}>
          <div>UI: {import.meta.env.VITE_APP_VERSION || 'local'}</div>
          <div>API: {backendVersion}</div>
        </div>
      </div>
    </aside>
  )
}
