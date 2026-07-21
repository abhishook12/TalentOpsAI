import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { User, Shield, Key, Mail, Calendar, MapPin, Building, Smartphone, LogOut, Link, Activity, Clock } from 'lucide-react'
import { API as API_BASE_URL } from '../services/api'
import ConnectOutlookModal from '../components/ConnectOutlookModal'

export default function Profile() {
  const { user, logout } = useAuth()
  const [bridgeStatus, setBridgeStatus] = useState(null)
  const [loadingBridge, setLoadingBridge] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const fetchBridgeStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/bridge/status`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (res.ok) {
        const data = await res.json()
        setBridgeStatus(data)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingBridge(false)
    }
  }

  useEffect(() => {
    fetchBridgeStatus()
  }, [])

  if (!user) return null

  const isGoogle = user.auth_provider === 'google'

  const handleConnectOutlook = () => {
    setIsModalOpen(true)
  }

  const handleDisconnectOutlook = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/bridge/disconnect`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (res.ok) {
        fetchBridgeStatus()
      }
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-4 lg:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <ConnectOutlookModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)}
        onSuccess={fetchBridgeStatus} 
      />

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
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 24 }}>{user.role || 'Member'}</p>

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
                <label style={{ display: 'block', color: 'var(--text-muted)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Email Address</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15 }}>
                  <Mail size={16} color="var(--text-muted)" /> {user.email}
                </div>
              </div>
              
              <div>
                <label style={{ display: 'block', color: 'var(--text-muted)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Account Status</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15 }}>
                  <Shield size={16} color="#4ade80" /> Active
                </div>
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-muted)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Company</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15 }}>
                  <Building size={16} color="var(--text-muted)" /> {user.company || 'Not Specified'}
                </div>
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-muted)', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 6 }}>Location</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15 }}>
                  <MapPin size={16} color="var(--text-muted)" /> {user.country || 'Not Specified'}
                </div>
              </div>
            </div>
          </div>

          {/* Email Bridge / Outlook Connection */}
          <div style={{
            background: 'rgba(25, 25, 25, 0.6)',
            border: '1px solid var(--card-border)',
            borderRadius: 24,
            padding: 32,
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Link size={20} color="var(--accent)" /> Email Bridge & Outlook Connection
            </h3>
            
            <div style={{ background: 'var(--bg-surface)', padding: 24, borderRadius: 16, border: '1px solid var(--card-border)' }}>
              {!loadingBridge && bridgeStatus && bridgeStatus.status === 'online' ? (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                    <div style={{ width: 48, height: 48, borderRadius: 12, background: 'rgba(74, 222, 128, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Activity size={24} color="#4ade80" />
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#4ade80' }}>Connected to Outlook</h4>
                      <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>Your Outlook account is securely linked and actively syncing.</p>
                    </div>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Connected Email</div>
                      <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Mail size={14} color="var(--text-secondary)" /> {user.email}
                      </div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Last Heartbeat</div>
                      <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Clock size={14} color="var(--text-secondary)" /> {bridgeStatus.last_heartbeat ? new Date(bridgeStatus.last_heartbeat).toLocaleString() : 'Just now'}
                      </div>
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: 12 }}>
                    <button onClick={handleDisconnectOutlook} style={{ flex: 1, padding: '10px', borderRadius: 8, border: '1px solid rgba(255,107,107,0.3)', background: 'transparent', color: '#ff6b6b', fontWeight: 600, cursor: 'pointer' }}>
                      Disconnect Outlook
                    </button>
                    <button onClick={handleConnectOutlook} style={{ flex: 1, padding: '10px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--text-primary)', color: 'var(--main-bg)', fontWeight: 600, cursor: 'pointer' }}>
                      Reconnect Account
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <div style={{ width: 64, height: 64, borderRadius: 32, background: 'rgba(255, 255, 255, 0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                    <Link size={32} color="var(--text-muted)" />
                  </div>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: 18, fontWeight: 700 }}>Outlook Not Connected</h4>
                  <p style={{ margin: '0 auto 24px', fontSize: 14, color: 'var(--text-secondary)', maxWidth: 400, lineHeight: 1.5 }}>
                    Connect your Microsoft Outlook account to enable the TalentOps AI Email Bridge. 
                    Authentication will open in a secure window.
                  </p>
                  <button 
                    onClick={handleConnectOutlook}
                    className="px-6 py-2 bg-[#00A4EF] hover:bg-[#008AC9] text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                  >
                    Connect Outlook Account
                  </button>
                </div>
              )}
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
                  <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>You signed in using your Google account. Password resets are managed by Google.</div>
                </div>
                <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" alt="Google" style={{ width: 24, height: 24 }} />
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 20, background: 'var(--bg-surface)', borderRadius: 16, border: '1px solid var(--card-border)' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>Password Authentication</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>You use a local password to sign in.</div>
                </div>
                <button onClick={() => window.location.href = '/settings'} style={{ padding: '8px 16px', borderRadius: 8, background: 'var(--text-primary)', color: 'var(--main-bg)', fontWeight: 700, border: 'none', cursor: 'pointer', fontSize: 13 }}>
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

