import React, { useEffect, useState, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { User, Shield, Key, Mail, Calendar, MapPin, Building, Smartphone, LogOut, Link, Activity, Clock, Camera, UploadCloud, Trash2, Loader2 } from 'lucide-react'
import api, { API as API_BASE_URL, getErrorMessage } from '../services/api'
import toast from 'react-hot-toast'
import ConnectOutlookModal from '../components/ConnectOutlookModal'

export default function Profile() {
  const { user, logout, updateUser } = useAuth()
  const [bridgeStatus, setBridgeStatus] = useState(null)
  const [loadingBridge, setLoadingBridge] = useState(true)
  const [bridgeError, setBridgeError] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [uploadingAvatar, setUploadingAvatar] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  const handleFileSelected = async (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file (.jpg, .png, .webp, etc.)')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Image size must be under 10MB')
      return
    }

    setUploadingAvatar(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await api.post('/auth/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (res.data?.avatar_url) {
        if (updateUser) updateUser({ avatar_url: res.data.avatar_url })
        toast.success('Profile photo updated successfully!')
      }
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to upload photo'))
    } finally {
      setUploadingAvatar(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleRemovePhoto = async () => {
    if (!window.confirm('Remove profile photo and revert to initials?')) return
    setUploadingAvatar(true)
    try {
      await api.delete('/auth/avatar')
      if (updateUser) updateUser({ avatar_url: null })
      toast.success('Profile photo removed')
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to remove photo'))
    } finally {
      setUploadingAvatar(false)
    }
  }

  const fetchBridgeStatus = async () => {
    setBridgeError(false)
    try {
      const res = await api.get('/bridge/status')
      setBridgeStatus(res.data)
    } catch (e) {
      console.error(e)
      setBridgeError(true)
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
      await api.post('/bridge/disconnect')
      fetchBridgeStatus()
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
          borderRadius: 6,
          padding: 32,
          textAlign: 'center',
          backdropFilter: 'blur(12px)'
        }}>
          {/* Avatar Upload Container */}
          <div style={{ position: 'relative', width: 104, height: 104, margin: '0 auto 16px' }}>
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files?.[0]) handleFileSelected(e.dataTransfer.files[0]);
              }}
              style={{
                width: 104,
                height: 104,
                borderRadius: '50%',
                border: isDragging ? '2px dashed #10b981' : '2px solid var(--card-border, #3f3f46)',
                margin: '0 auto',
                display: 'grid',
                placeItems: 'center',
                color: '#111',
                fontSize: 40,
                fontWeight: 800,
                background: user.avatar_url ? `url(${user.avatar_url}) center/cover no-repeat` : 'linear-gradient(135deg, #d8d8d8, #8c8c8c)',
                cursor: 'pointer',
                position: 'relative',
                overflow: 'hidden',
                transition: 'all 0.2s ease',
                boxShadow: isDragging ? '0 0 16px rgba(16, 185, 129, 0.3)' : '0 4px 16px rgba(0,0,0,0.2)'
              }}
              title="Click or drag photo here to upload from PC"
            >
              {!user.avatar_url && user.first_name?.[0]}

              {/* Hover / Loading Overlay */}
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'rgba(0, 0, 0, 0.6)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                  opacity: uploadingAvatar ? 1 : 0,
                  transition: 'opacity 0.2s ease',
                  fontSize: 11,
                  fontWeight: 600,
                  gap: 4
                }}
                onMouseEnter={(e) => { if (!uploadingAvatar) e.currentTarget.style.opacity = '1'; }}
                onMouseLeave={(e) => { if (!uploadingAvatar) e.currentTarget.style.opacity = '0'; }}
              >
                {uploadingAvatar ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <Camera size={20} />
                    <span>Change</span>
                  </>
                )}
              </div>
            </div>

            {/* Camera badge icon */}
            <div
              onClick={() => fileInputRef.current?.click()}
              style={{
                position: 'absolute',
                bottom: 2,
                right: 2,
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: 'var(--brand, #10b981)',
                color: '#000',
                display: 'grid',
                placeItems: 'center',
                cursor: 'pointer',
                boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
                border: '2px solid #18181b'
              }}
              title="Upload photo from PC"
            >
              <Camera size={14} strokeWidth={2.5} />
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileSelected(e.target.files[0]);
            }}
          />

          {/* Action Buttons for Avatar */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginBottom: 20 }}>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingAvatar}
              style={{
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                background: 'var(--bg-surface, #1e1e24)',
                border: '1px solid var(--card-border, #3f3f46)',
                color: 'var(--text-primary, #f4f4f5)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'all 0.15s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'var(--bg-surface, #1e1e24)'}
            >
              <UploadCloud size={14} /> Upload from PC
            </button>
            {user.avatar_url && (
              <button
                onClick={handleRemovePhoto}
                disabled={uploadingAvatar}
                style={{
                  padding: '6px 10px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  background: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  color: '#ef4444',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  transition: 'all 0.15s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)'}
                title="Remove custom photo"
              >
                <Trash2 size={13} />
              </button>
            )}
          </div>
          
          <h2 style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>{user.first_name} {user.last_name}</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 24 }}>{user.role || 'Member'}</p>

          <button 
            onClick={logout} 
            style={{
              width: '100%', padding: '12px', borderRadius: 6, 
              border: '1px solid color-mix(in srgb, var(--danger) 30%, transparent)',
              background: 'color-mix(in srgb, var(--danger) 8%, transparent)', 
              color: 'var(--danger)', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'color-mix(in srgb, var(--danger) 16%, transparent)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'color-mix(in srgb, var(--danger) 8%, transparent)'}
          >
            <LogOut size={16} /> Sign Out
          </button>
        </div>

        {/* Right Column - Details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          
          {/* Account Details */}
          <div style={{
            background: 'rgba(25, 25, 25, 0.6)',
            border: '1px solid var(--card-border)',
            borderRadius: 6,
            padding: 32,
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8 }}>
              <User size={20} color="var(--brand)" /> Account Details
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
                <div style={{ 
                  display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 700,
                  background: 'color-mix(in srgb, var(--success) 10%, transparent)',
                  border: '1px solid color-mix(in srgb, var(--success) 40%, transparent)',
                  color: 'var(--success)',
                  padding: '4px 12px', borderRadius: 6
                }}>
                  <Shield size={14} color="var(--success)" /> Active
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
            borderRadius: 6,
            padding: 32,
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Link size={20} color="var(--brand)" /> Email Bridge & Outlook Connection
            </h3>
            
            <div style={{ background: 'var(--bg-surface)', padding: 24, borderRadius: 6, border: '1px solid var(--card-border)' }}>
              {!loadingBridge && bridgeStatus && bridgeStatus.connected_email ? (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                    <div style={{ width: 48, height: 48, borderRadius: 6, background: bridgeStatus.status === 'online' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(255, 170, 0, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Activity size={24} color={bridgeStatus.status === 'online' ? "#4ade80" : "#ffaa00"} />
                    </div>
                    <div>
                      <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: bridgeStatus.status === 'online' ? '#4ade80' : '#ffaa00' }}>
                        {bridgeStatus.status === 'online' ? 'Bridge Online' : 'Bridge Offline (Account Linked)'}
                      </h4>
                      <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>
                        {bridgeStatus.status === 'online' ? 'Your Outlook account is securely linked and actively syncing.' : 'Your Outlook account is linked, but the local bridge app is currently offline.'}
                      </p>
                    </div>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Connected Email</div>
                      <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Mail size={14} color="var(--text-secondary)" /> {bridgeStatus.connected_email}
                      </div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Last Heartbeat</div>
                      <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Clock size={14} color="var(--text-secondary)" /> {bridgeStatus.last_heartbeat ? new Date(bridgeStatus.last_heartbeat).toLocaleString() : 'Never'}
                      </div>
                    </div>
                  </div>
                  
                  {bridgeStatus.stats && (
                    <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--card-border)', padding: 16, borderRadius: 6, marginBottom: 24 }}>
                      <h5 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Current Queue Statistics</h5>
                      <div style={{ display: 'flex', gap: 24 }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)' }}>{bridgeStatus.stats.pending || 0}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Pending</div>
                        </div>
                        <div style={{ width: 1, background: 'var(--card-border)' }}></div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 24, fontWeight: 800, color: '#4ade80' }}>{bridgeStatus.stats.sent || 0}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Messages Sent</div>
                        </div>
                        <div style={{ width: 1, background: 'var(--card-border)' }}></div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 24, fontWeight: 800, color: '#ff6b6b' }}>{bridgeStatus.stats.failed || 0}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Failed</div>
                        </div>
                      </div>
                    </div>
                  )}
                  
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
                  <h4 style={{ margin: '0 0 8px 0', fontSize: 18, fontWeight: 700 }}>
                    {bridgeError ? 'Failed to check status — please refresh' : 'Outlook Not Connected'}
                  </h4>
                  <p style={{ margin: '0 auto 24px', fontSize: 14, color: 'var(--text-secondary)', maxWidth: 400, lineHeight: 1.5 }}>
                    Connect your Microsoft Outlook account to enable the TalentOps Email Bridge. 
                    Authentication will open in a secure window.
                  </p>
                  <button 
                    onClick={handleConnectOutlook}
                    style={{ padding: '10px 20px', borderRadius: 8, background: '#00A4EF', color: '#fff', fontWeight: 600, border: 'none', cursor: 'pointer' }}
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
            borderRadius: 6,
            padding: 32,
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Key size={20} color="var(--brand)" /> Authentication
            </h3>

            {isGoogle ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 20, background: 'var(--bg-surface)', borderRadius: 6, border: '1px solid var(--card-border)' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>Google Connected</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>You signed in using your Google account. Password resets are managed by Google.</div>
                </div>
                <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" alt="Google" style={{ width: 24, height: 24 }} />
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 20, background: 'var(--bg-surface)', borderRadius: 6, border: '1px solid var(--card-border)' }}>
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

