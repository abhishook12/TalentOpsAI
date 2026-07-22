import React from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuth } from '../context/AuthContext'

export default function Maintenance() {
  const { logout } = useAuth()
  const navigate = useNavigate({ from: '/' })

  const handleSignOut = async () => {
    try {
      await logout()
    } finally {
      navigate({ to: '/login' })
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--main-bg)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: 20,
      fontFamily: 'var(--font)',
    }}>
      <div style={{
        maxWidth: 440,
        width: '100%',
        background: 'var(--card-bg)',
        borderRadius: 20,
        border: '1px solid var(--card-border)',
        boxShadow: 'var(--shadow-lg)',
        overflow: 'hidden',
      }}>
        <div style={{ padding: 40, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
          
          <div style={{
            width: 72,
            height: 72,
            background: 'linear-gradient(135deg, rgba(56,189,248,0.1), rgba(59,130,246,0.15))',
            borderRadius: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 24,
            border: '1px solid rgba(56,189,248,0.2)',
            boxShadow: '0 0 40px rgba(56,189,248,0.05)',
          }}>
            <i className="ti ti-terminal-2" style={{ fontSize: 32, color: '#38bdf8' }} />
          </div>

          <h1 style={{
            fontSize: 24,
            fontWeight: 800,
            color: 'var(--text-primary)',
            marginBottom: 10,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            letterSpacing: '-0.02em',
          }}>
            <i className="ti ti-alert-triangle" style={{ color: '#fbbf24', fontSize: 26 }} />
            Development Notice
          </h1>
          
          <p style={{ color: 'var(--text-secondary)', marginBottom: 28, fontSize: 14, lineHeight: 1.6 }}>
            TalentOps AI is currently undergoing major improvements.
          </p>

          <div style={{
            background: 'var(--panel-bg)',
            padding: 20,
            borderRadius: 14,
            border: '1px solid var(--card-border)',
            marginBottom: 32,
            textAlign: 'left',
            width: '100%',
          }}>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.5 }}>
              Access has been temporarily restricted while new features are being developed and tested.
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.5 }}>
              <strong style={{ color: 'var(--text-primary)' }}>Your account has not been deleted.</strong>
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Please contact the administrator if you believe you should have access.
            </p>
          </div>

          <button
            onClick={handleSignOut}
            className="cc-ghost-button"
            style={{ width: '100%', justifyContent: 'center' }}
          >
            <i className="ti ti-logout" />
            Sign Out
          </button>
        </div>
      </div>
    </div>
  )
}
