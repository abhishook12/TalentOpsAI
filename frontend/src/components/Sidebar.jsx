import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import api, { clearStoredToken } from '../services/api'

const nav = [
  { to: '/', label: 'Dashboard', icon: 'ti-layout-dashboard' },
  { to: '/activity', label: 'Activity Log', icon: 'ti-activity' },
  { to: '/recruiters', label: 'Recruiters', icon: 'ti-users' },
  { to: '/directory', label: 'Directory', icon: 'ti-map-2', aliases: ['/states', '/companies'] },
  { to: '/analytics', label: 'Analytics', icon: 'ti-chart-bar' },
  { to: '/ai-search', label: 'AI Search', icon: 'ti-search' },
  { to: '/admin', label: 'Admin Ops', icon: 'ti-shield-lock' },
]

export default function Sidebar() {
  const location = useLocation()
  const [updateStatus, setUpdateStatus] = useState(null)
  const [lastSyncedAt, setLastSyncedAt] = useState(null)

  useEffect(() => {
    let alive = true

    const loadUpdateStatus = async () => {
      try {
        const res = await api.get('/updates/status')
        if (alive) {
          setUpdateStatus(res.data || null)
          setLastSyncedAt(new Date().toISOString())
        }
      } catch {
        if (alive) setUpdateStatus(null)
      }
    }

    loadUpdateStatus()
    const timer = setInterval(loadUpdateStatus, 5 * 60 * 1000)

    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  const updateLabel = useMemo(() => {
    const stamp = lastSyncedAt ? new Date(lastSyncedAt) : updateStatus?.date ? new Date(updateStatus.date) : null
    if (!stamp || Number.isNaN(stamp.getTime())) return 'Updated recently'
    return `Updated ${stamp.toLocaleDateString([], { month: 'short', day: 'numeric' })}`
  }, [lastSyncedAt, updateStatus])

  const updateDetail = useMemo(() => {
    const stamp = lastSyncedAt ? new Date(lastSyncedAt) : updateStatus?.date ? new Date(updateStatus.date) : null
    if (!stamp || Number.isNaN(stamp.getTime())) return 'Click to open the update log'
    return `${stamp.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })} • ${updateStatus?.version || 'Latest build'}`
  }, [lastSyncedAt, updateStatus])

  const openUpdateCenter = () => {
    window.dispatchEvent(new CustomEvent('open-update-center'))
  }

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
      overflow: 'visible',
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
            <div style={{ color: '#f3f3f3', fontSize: 18, fontWeight: 900, letterSpacing: '-0.03em', lineHeight: 1.05 }}>TalentOps AI</div>
            <div style={{ color: 'rgba(255,255,255,0.62)', fontSize: 12, fontWeight: 700, marginTop: 6, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Recruiter Intel
            </div>
          </div>
        </div>
      </div>

      <nav style={{ flex: 1, minHeight: 0, padding: '14px 12px', overflowY: 'auto' }}>
        {nav.map(({ to, label, icon, aliases = [] }) => {
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
            >
              <i className={`ti ${icon}`} style={{ fontSize: 18, opacity: active ? 1 : 0.88 }} />
              <span>{label}</span>
            </NavLink>
          )
        })}
      </nav>

      <div style={{
        padding: '10px 14px 12px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        flexShrink: 0,
      }}>
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

      <div style={{ padding: '0 14px 12px', flexShrink: 0 }}>
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
        <button
          onClick={openUpdateCenter}
          title={updateDetail}
          aria-label="Open update log"
          style={{
            width: '100%',
            marginTop: 10,
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 16,
            background: 'rgba(255,255,255,0.04)',
            color: '#f3f3f3',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          <div style={{
            width: 34,
            height: 34,
            borderRadius: 13,
            display: 'grid',
            placeItems: 'center',
            background: 'rgba(255,255,255,0.08)',
            border: '1px solid rgba(255,255,255,0.10)',
            flexShrink: 0,
          }}>
            <i className="ti ti-refresh" style={{ fontSize: 16, color: '#ffffff' }} />
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: 11, fontWeight: 900, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.58)' }}>
              {updateLabel}
            </div>
            <div style={{ fontSize: 12, fontWeight: 800, marginTop: 2, color: '#f8f8f8' }}>
              Latest change log
            </div>
            <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.62)', marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {updateDetail}
            </div>
          </div>
          <i className="ti ti-chevron-right" style={{ fontSize: 16, color: 'rgba(255,255,255,0.45)', flexShrink: 0 }} />
        </button>
      </div>
    </aside>
  )
}
