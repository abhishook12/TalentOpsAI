import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { User, Bell, Lock, Key, Globe, Shield, Smartphone, ArrowRight, Laptop, LogOut } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Settings() {
  const { user, checkAuth } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  
  const [formData, setFormData] = useState({
    firstName: user?.first_name || '',
    lastName: user?.last_name || '',
    company: user?.company || '',
    country: user?.country || ''
  });

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: ''
  });

  const [isSaving, setIsSaving] = useState(false);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.put('/users/profile', {
        first_name: formData.firstName,
        last_name: formData.lastName,
        company: formData.company,
        country: formData.country
      });
      checkAuth();
      toast.success('Profile updated successfully');
    } catch (err) {
      toast.error('Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdatePassword = async () => {
    if (!passwordData.currentPassword || !passwordData.newPassword) {
      return toast.error("Please fill in both password fields");
    }
    setIsSaving(true);
    try {
      await api.put('/users/profile/password', {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      });
      toast.success('Password updated successfully');
      setPasswordData({ currentPassword: '', newPassword: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update password');
    } finally {
      setIsSaving(false);
    }
  };

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'account', label: 'Account', icon: Lock },
    { id: 'appearance', label: 'Appearance', icon: Globe },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Privacy & Security', icon: Shield },
    { id: 'integrations', label: 'API / Integrations', icon: Key },
  ];

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 32px', maxWidth: 1000, margin: '0 auto', width: '100%' }}>
      <header style={{ padding: '32px 0 24px', borderBottom: '1px solid var(--card-border)' }}>
        <h1 className="page-title" style={{ fontSize: 28, color: 'var(--text-primary)' }}>Settings</h1>
        <p className="page-subtitle">Manage your personal preferences, security, and integrations.</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 40, marginTop: 32 }}>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '12px 16px',
                background: activeTab === tab.id ? 'var(--accent-bg)' : 'transparent',
                color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-secondary)',
                border: 'none',
                borderRadius: 12,
                fontWeight: activeTab === tab.id ? 700 : 500,
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s'
              }}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </nav>

        <main style={{ minWidth: 0 }}>
          {activeTab === 'profile' && (
            <form onSubmit={handleSaveProfile} className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Profile Settings</h2>
              
              <div style={{ padding: 24, border: '1px solid var(--card-border)', borderRadius: 12, marginBottom: 24, display: 'flex', gap: 24, alignItems: 'center' }}>
                <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))', display: 'grid', placeItems: 'center', color: '#ffffff', fontSize: 32, fontWeight: 800 }}>
                  {user?.first_name?.[0] || user?.email?.[0]?.toUpperCase()}
                </div>
                <div>
                  <h3 style={{ margin: '0 0 8px', fontSize: 16, color: 'var(--text-primary)' }}>Profile Picture</h3>
                  <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--text-secondary)' }}>JPG, GIF or PNG. Max size of 5MB.</p>
                  <button type="button" style={{ padding: '8px 16px', background: 'var(--accent)', color: '#ffffff', border: 'none', borderRadius: 8, fontWeight: 500, cursor: 'pointer' }}>Change Avatar</button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>First Name</label>
                  <input value={formData.firstName} onChange={e => setFormData(p => ({...p, firstName: e.target.value}))} style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Last Name</label>
                  <input value={formData.lastName} onChange={e => setFormData(p => ({...p, lastName: e.target.value}))} style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 32 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Company</label>
                  <input value={formData.company} onChange={e => setFormData(p => ({...p, company: e.target.value}))} style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Country</label>
                  <input value={formData.country} onChange={e => setFormData(p => ({...p, country: e.target.value}))} style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 24, borderTop: '1px solid var(--card-border)' }}>
                <button type="submit" disabled={isSaving} style={{ padding: '10px 24px', background: 'var(--accent)', color: '#ffffff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: isSaving ? 'not-allowed' : 'pointer', opacity: isSaving ? 0.7 : 1 }}>
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}

          {activeTab === 'account' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Account Settings</h2>
              
              <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, marginBottom: 24 }}>
                <h3 style={{ margin: '0 0 16px', fontSize: 16, color: 'var(--text-primary)' }}>Email Address</h3>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ color: 'var(--text-secondary)' }}>{user?.email}</div>
                  <button style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 6, color: 'var(--text-primary)', cursor: 'not-allowed', opacity: 0.5 }} disabled>Change Email (Coming Soon)</button>
                </div>
              </div>

              <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, marginBottom: 24 }}>
                <h3 style={{ margin: '0 0 16px', fontSize: 16, color: 'var(--text-primary)' }}>Change Password</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <input type="password" value={passwordData.currentPassword} onChange={e => setPasswordData(p => ({...p, currentPassword: e.target.value}))} placeholder="Current Password" style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                  <input type="password" value={passwordData.newPassword} onChange={e => setPasswordData(p => ({...p, newPassword: e.target.value}))} placeholder="New Password" style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                  <button onClick={handleUpdatePassword} disabled={isSaving} style={{ padding: '8px 16px', background: 'var(--accent-bg)', color: 'var(--accent)', border: 'none', borderRadius: 8, fontWeight: 600, cursor: isSaving ? 'not-allowed' : 'pointer', width: 'fit-content' }}>
                    {isSaving ? 'Updating...' : 'Update Password'}
                  </button>
                </div>
              </div>

              <div style={{ padding: 20, border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 12, background: 'rgba(239, 68, 68, 0.05)' }}>
                <h3 style={{ margin: '0 0 8px', fontSize: 16, color: '#ef4444' }}>Delete Account</h3>
                <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--text-secondary)' }}>Once you delete your account, there is no going back. Please be certain.</p>
                <button disabled style={{ padding: '8px 16px', background: '#ef4444', color: '#ffffff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'not-allowed', opacity: 0.5 }}>Delete Account (Coming Soon)</button>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Privacy & Security</h2>
              
              <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ margin: '0 0 4px', fontSize: 16, color: 'var(--text-primary)' }}>Two-Factor Authentication</h3>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>Add an extra layer of security to your account.</p>
                </div>
                <button disabled style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: 8, fontWeight: 500, cursor: 'not-allowed', opacity: 0.5 }}>Enable 2FA (Coming Soon)</button>
              </div>

              <h3 style={{ margin: '0 0 16px', fontSize: 16, color: 'var(--text-primary)' }}>Active Sessions</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ padding: 16, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 8, background: 'var(--accent-bg)', color: 'var(--accent)', display: 'grid', placeItems: 'center' }}><Laptop size={20} /></div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Windows / Chrome</div>
                      <span style={{ fontSize: 10, background: 'rgba(23,114,69,0.12)', color: 'var(--success)', padding: '2px 6px', borderRadius: 4, fontWeight: 800 }}>CURRENT</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>New York, United States &bull; Active now</div>
                  </div>
                </div>
                
                <button disabled style={{ width: '100%', padding: 16, background: 'transparent', border: '1px dashed var(--card-border)', borderRadius: 12, color: 'var(--text-secondary)', cursor: 'not-allowed', fontWeight: 600, opacity: 0.5 }}>
                  Log out of all other devices (Coming Soon)
                </button>
              </div>
            </div>
          )}

          {activeTab === 'appearance' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Appearance</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>
                {['light', 'dark', 'system'].map(theme => (
                  <button 
                    key={theme}
                    onClick={() => {
                      localStorage.setItem('theme', theme);
                      document.documentElement.setAttribute('data-theme', theme);
                    }}
                    style={{ 
                      padding: 24, 
                      borderRadius: 16, 
                      border: '2px solid',
                      borderColor: localStorage.getItem('theme') === theme ? 'var(--accent)' : 'var(--card-border)',
                      background: 'var(--bg-surface)',
                      color: 'var(--text-primary)',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 12,
                      textTransform: 'capitalize',
                      fontWeight: 600
                    }}>
                    <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--accent-bg)', display: 'grid', placeItems: 'center', color: 'var(--accent)' }}>
                      <Globe size={24} />
                    </div>
                    {theme}
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>API & Integrations</h2>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{ width: 40, height: 40, background: '#f3f4f6', borderRadius: 8, display: 'grid', placeItems: 'center' }}>
                      <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" alt="Google" style={{ width: 24, height: 24 }} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Google Workspace</div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Sync calendar and emails</div>
                    </div>
                  </div>
                  <button disabled style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: 6, fontWeight: 500, cursor: 'not-allowed', opacity: 0.5 }}>Connect (Coming Soon)</button>
                </div>

                <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{ width: 40, height: 40, background: '#0078d4', borderRadius: 8, display: 'grid', placeItems: 'center' }}>
                      <span style={{ color: '#ffffff', fontWeight: 900, fontSize: 18 }}>O</span>
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Microsoft Outlook</div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Office 365 Integration</div>
                    </div>
                  </div>
                  <button disabled style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: 6, fontWeight: 500, cursor: 'not-allowed', opacity: 0.5 }}>Connect (Coming Soon)</button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Notifications</h2>
              <p style={{ color: 'var(--text-secondary)' }}>Notification settings are currently managed globally by your organization administrator.</p>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
