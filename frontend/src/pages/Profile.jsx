import React from 'react'
import { useAuth } from '../context/AuthContext'
import { User, Shield, Key, Mail, Calendar, MapPin, Building, Smartphone, LogOut } from 'lucide-react'

export default function Profile() {
  const { user, logout } = useAuth()

  if (!user) return null

  const isGoogle = user.auth_provider === 'google'

  return (
    <div style={{ padding: 40, maxWidth: 900, margin: '0 auto', color: 'var(--text-inverse)' }}>
      <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 40, letterSpacing: '-0.02em' }}>My Profile</h1>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '300px 1fr',
        gap: 32,
        alignItems: 'start'
      }}>
        {/* Left Column - Card */}
        <div style={{
          background: 'rgba(25, 25, 25, 0.6)',
          border: '1px solid var(--card-border)',
          borderRadius: 24,
          padding: 32,
          textAlign: 'center',
          backdropFilter: 'blur(12px)'
        }}>
          <div style={{
            width: 100, height: 100, borderRadius: 50, background: 'linear-gradient(135deg, #d8d8d8, #8c8c8c)',
            margin: '0 auto 20px', display: 'grid', placeItems: 'center', color: '#111', fontSize: 40, fontWeight: 800,
            backgroundImage: user.avatar_url ? "url(" + user.avatar_url + ")" : 'none',
            backgroundSize: 'cover'
          }}>
            {!user.avatar_url && user.first_name?.[0]}
          </div>
          
          <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>{user.first_name} {user.last_name}</h2>
          <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 14, marginBottom: 24 }}>{user.role || 'Member'}</p>

          <button onClick={logout} style={{
            width: '100%', padding: '12px', borderRadius: 12, border: '1px solid rgba(255,107,107,0.2)',
            background: 'rgba(255,107,107,0.05)', color: '#ff6b6b', fontWeight: 700, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8
          }}>
            <LogOut size={16} /> Sign Out
          </button>
        </div>

        {/* Right Column - Details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          
          {/* Account Details */}
          <div style={{
            background: 'rgba(25, 25, 25, 0.6)',
            border: '1px solid var(--card-border)',
            borderRadius: 24,
            padding: 32,
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8 }}>
              <User size={20} color="var(--accent)" /> Account Details
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              <div>
                <label style={{ display: 'block', color: 'rgba(255,255,255,0.4)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Email Address</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15 }}>
                  <Mail size={16} color="rgba(255,255,255,0.4)" /> {user.email}
                </div>
              </div>
              
              <div>
                <label style={{ display: 'block', color: 'rgba(255,255,255,0.4)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Account Status</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15 }}>
                  <Shield size={16} color="#4ade80" /> Active
                </div>
              </div>

              <div>
                <label style={{ display: 'block', color: 'rgba(255,255,255,0.4)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Company</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15 }}>
                  <Building size={16} color="rgba(255,255,255,0.4)" /> {user.company || 'Not Specified'}
                </div>
              </div>

              <div>
                <label style={{ display: 'block', color: 'rgba(255,255,255,0.4)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Location</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15 }}>
                  <MapPin size={16} color="rgba(255,255,255,0.4)" /> {user.country || 'Not Specified'}
                </div>
              </div>
            </div>
          </div>

          {/* Security */}
          <div style={{
            background: 'rgba(25, 25, 25, 0.6)',
            border: '1px solid var(--card-border)',
            borderRadius: 24,
            padding: 32,
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Key size={20} color="var(--accent)" /> Authentication
            </h3>

            {isGoogle ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 20, background: 'var(--bg-surface)', borderRadius: 16, border: '1px solid var(--card-border)' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>Google Connected</div>
                  <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>You signed in using your Google account. Password resets are managed by Google.</div>
                </div>
                <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" alt="Google" style={{ width: 24, height: 24 }} />
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 20, background: 'var(--bg-surface)', borderRadius: 16, border: '1px solid var(--card-border)' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>Password Authentication</div>
                  <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>You use a local password to sign in.</div>
                </div>
                <button style={{ padding: '8px 16px', borderRadius: 8, background: '#fff', color: '#000', fontWeight: 700, border: 'none', cursor: 'pointer', fontSize: 13 }}>
                  Change Password
                </button>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
