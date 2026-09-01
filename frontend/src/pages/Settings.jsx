import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { User, Bell, Lock, Key, Globe, Shield, Smartphone, ArrowRight, Laptop, LogOut, Mail, Server, MoreVertical, ExternalLink, Star, Loader2, Puzzle, Download, CheckCircle, Copy } from 'lucide-react';
import toast from 'react-hot-toast';

import { API } from '../services/api';
import { useSessionState } from '../hooks/useSessionState';
import ConnectionWizard from '../components/ConnectionWizard';

export default function Settings() {
  const { user, checkAuthStatus } = useAuth();
  const { theme: currentTheme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useSessionState('settings_activeTab', 'profile');
  const [accounts, setAccounts] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [showConnectionWizard, setShowConnectionWizard] = useState(false);
  
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
  
  const fetchAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const res = await api.get('/accounts');
      setAccounts(res.data.items || []);
    } catch (err) {
      toast.error('Failed to load connected accounts');
    } finally {
      setLoadingAccounts(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleDeleteAccount = async (id) => {
    if (!window.confirm('Are you sure you want to remove this account?')) return;
    try {
      await api.delete(`/accounts/${id}`);
      toast.success('Account removed');
      fetchAccounts();
    } catch (err) {
      toast.error('Failed to remove account');
    }
  };

  const handleSetDefaultAccount = async (id) => {
    try {
      await api.post(`/accounts/${id}/set-default`);
      toast.success('Default account updated');
      fetchAccounts();
      checkAuthStatus(); // update current user default sender in context
    } catch (err) {
      toast.error('Failed to set default account');
    }
  };

  const handleTestConnection = async (id) => {
    const t = toast.loading('Testing connection...');
    try {
      const res = await api.post(`/accounts/${id}/verify`);
      if (res.data.health_status === 'healthy') {
        toast.success('Connection successful', { id: t });
      } else {
        toast.error('Connection failed', { id: t });
      }
      fetchAccounts();
    } catch (err) {
      toast.error('Connection test failed', { id: t });
      fetchAccounts();
    }
  };

  const handleUpdateDisplayName = async (id, currentName) => {
    const newName = window.prompt("Enter official sender display name (e.g. Abhishek Jadon):", currentName || "");
    if (newName !== null) {
      try {
        await api.put(`/accounts/${id}`, { display_name: newName });
        toast.success("Official sender name updated");
        fetchAccounts();
      } catch {
        toast.error("Failed to update sender name");
      }
    }
  };
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
      checkAuthStatus();
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
    { id: 'profile', label: 'Profile' },
    { id: 'account', label: 'Account' },
    { id: 'appearance', label: 'Appearance' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'security', label: 'Privacy & Security' },
    { id: 'integrations', label: 'API & Integrations' },
    { id: 'extension', label: 'Talent Scout Extension' },
  ];

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 100px', maxWidth: 1200, margin: '0 auto', width: '100%' }}>
      <header style={{ paddingTop: 32, marginBottom: 40 }}>
        <h1 className="page-title" style={{ fontSize: 24, color: 'var(--text-primary)', marginBottom: 24 }}>Settings</h1>
        
        <nav style={{ display: 'flex', gap: 32, borderBottom: '1px solid var(--card-border)' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '0 0 16px',
                background: 'transparent',
                color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                border: 'none',
                borderBottom: activeTab === tab.id ? '2px solid var(--text-primary)' : '2px solid transparent',
                fontWeight: activeTab === tab.id ? 500 : 400,
                fontSize: 14,
                cursor: 'pointer',
                transition: 'all 0.15s',
                marginBottom: -1
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 48 }}>
        <aside>
          {activeTab === 'integrations' ? (
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 16 }}>
                Integrations
              </div>
              <button
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  width: '100%',
                  padding: '10px 16px',
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--card-border)',
                  color: 'var(--text-primary)',
                  borderRadius: 6,
                  fontWeight: 500,
                  fontSize: 13,
                  cursor: 'pointer'
                }}
              >
                <Mail size={16} />
                Sending Accounts
              </button>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 16 }}>
                {tabs.find(t => t.id === activeTab)?.label}
              </div>
              <button
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  width: '100%',
                  padding: '10px 16px',
                  background: 'var(--bg-panel)',
                  border: '1px solid var(--card-border)',
                  color: 'var(--text-primary)',
                  borderRadius: 6,
                  fontWeight: 500,
                  fontSize: 13,
                  cursor: 'pointer'
                }}
              >
                {activeTab === 'profile' && <User size={16} />}
                {activeTab === 'account' && <Lock size={16} />}
                {activeTab === 'appearance' && <Globe size={16} />}
                {activeTab === 'notifications' && <Bell size={16} />}
                {activeTab === 'security' && <Shield size={16} />}
                General
              </button>
            </div>
          )}
        </aside>

        <main style={{ minWidth: 0 }}>
          {activeTab === 'profile' && (
            <form onSubmit={handleSaveProfile} className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              
              <div style={{ background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--card-border)', overflow: 'hidden' }}>
                <div style={{ padding: 24, borderBottom: '1px solid var(--card-border)' }}>
                  <h2 style={{ margin: '0 0 8px', fontSize: 18, color: 'var(--text-primary)', fontWeight: 600 }}>Profile Settings</h2>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Update your personal information and profile picture.</p>
                </div>

                <div style={{ padding: 32 }}>
                  {/* Profile Picture */}
                  <div style={{ display: 'flex', gap: 24, alignItems: 'center', marginBottom: 32 }}>
                    <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'var(--bg-elevated, var(--panel-bg))', display: 'grid', placeItems: 'center', color: 'var(--text-primary)', fontSize: 32, fontWeight: 800, border: '4px solid var(--card-bg)' }}>
                      {user?.first_name?.[0] || user?.email?.[0]?.toUpperCase() || 'A'}
                    </div>
                    <div>
                      <h3 style={{ margin: '0 0 8px', fontSize: 15, color: 'var(--text-primary)', fontWeight: 500 }}>Profile Picture</h3>
                      <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--text-secondary)' }}>JPG, GIF or PNG. Max size of 5MB.</p>
                      <button type="button" style={{ padding: '8px 16px', background: 'var(--text-primary)', color: 'var(--main-bg)', border: 'none', borderRadius: 6, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>Change Avatar</button>
                    </div>
                  </div>

                  {/* Form Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 24, marginBottom: 24 }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>First Name</label>
                      <input value={formData.firstName} onChange={e => setFormData(p => ({...p, firstName: e.target.value}))} style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)', outline: 'none', fontSize: 14 }} />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Last Name</label>
                      <input value={formData.lastName} onChange={e => setFormData(p => ({...p, lastName: e.target.value}))} style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)', outline: 'none', fontSize: 14 }} />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Company</label>
                      <input value={formData.company} onChange={e => setFormData(p => ({...p, company: e.target.value}))} style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)', outline: 'none', fontSize: 14 }} />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Country</label>
                      <input value={formData.country} onChange={e => setFormData(p => ({...p, country: e.target.value}))} style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)', outline: 'none', fontSize: 14 }} />
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '16px 32px', background: 'var(--bg-base)', borderTop: '1px solid var(--card-border)' }}>
                  <button type="submit" disabled={isSaving} style={{ padding: '10px 24px', background: 'var(--text-primary)', color: 'var(--main-bg)', border: 'none', borderRadius: 6, fontWeight: 600, fontSize: 14, cursor: isSaving ? 'not-allowed' : 'pointer', opacity: isSaving ? 0.7 : 1 }}>
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            </form>
          )}

          {activeTab === 'account' && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              
              <div style={{ background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--card-border)', overflow: 'hidden' }}>
                <div style={{ padding: 24, borderBottom: '1px solid var(--card-border)' }}>
                  <h2 style={{ margin: '0 0 8px', fontSize: 18, color: 'var(--text-primary)', fontWeight: 600 }}>Account Settings</h2>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Manage your email address and password.</p>
                </div>

                <div style={{ padding: 32 }}>
                  <div style={{ marginBottom: 32 }}>
                    <h3 style={{ margin: '0 0 8px', fontSize: 15, color: 'var(--text-primary)', fontWeight: 500 }}>Email Address</h3>
                    <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--text-secondary)' }}>The email address associated with your account.</p>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-base)', border: '1px solid var(--card-border)', borderRadius: 6 }}>
                      <div style={{ color: 'var(--text-primary)', fontSize: 14 }}>{user?.email}</div>
                      <button style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 6, color: 'var(--text-secondary)', fontSize: 13, cursor: 'not-allowed', opacity: 0.5 }} disabled>Change Email (Coming Soon)</button>
                    </div>
                  </div>

                  <div>
                    <h3 style={{ margin: '0 0 8px', fontSize: 15, color: 'var(--text-primary)', fontWeight: 500 }}>Change Password</h3>
                    <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--text-secondary)' }}>Update your password to keep your account secure.</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 400 }}>
                      <input type="password" value={passwordData.currentPassword} onChange={e => setPasswordData(p => ({...p, currentPassword: e.target.value}))} placeholder="Current Password" style={{ width: '100%', padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)', outline: 'none', fontSize: 14 }} />
                      <input type="password" value={passwordData.newPassword} onChange={e => setPasswordData(p => ({...p, newPassword: e.target.value}))} placeholder="New Password" style={{ width: '100%', padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)', outline: 'none', fontSize: 14 }} />
                      <button onClick={handleUpdatePassword} disabled={isSaving} style={{ marginTop: 8, padding: '10px 16px', background: 'var(--text-primary)', color: 'var(--main-bg)', border: 'none', borderRadius: 6, fontWeight: 600, fontSize: 13, cursor: isSaving ? 'not-allowed' : 'pointer', width: 'fit-content' }}>
                        {isSaving ? 'Updating...' : 'Update Password'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ background: 'rgba(239, 68, 68, 0.02)', borderRadius: 8, border: '1px solid rgba(239, 68, 68, 0.2)', padding: 24 }}>
                <h3 style={{ margin: '0 0 8px', fontSize: 16, color: '#ef4444', fontWeight: 600 }}>Danger Zone</h3>
                <p style={{ margin: '0 0 20px', fontSize: 13, color: 'var(--text-secondary)' }}>Once you delete your account, there is no going back. Please be certain.</p>
                <button disabled style={{ padding: '8px 16px', background: '#ef4444', color: '#ffffff', border: 'none', borderRadius: 6, fontWeight: 600, fontSize: 13, cursor: 'not-allowed', opacity: 0.5 }}>Delete Account</button>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--card-border)', overflow: 'hidden' }}>
                <div style={{ padding: 24, borderBottom: '1px solid var(--card-border)' }}>
                  <h2 style={{ margin: '0 0 8px', fontSize: 18, color: 'var(--text-primary)', fontWeight: 600 }}>Privacy & Security</h2>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Manage your account security and active sessions.</p>
                </div>
                
                <div style={{ padding: 32 }}>
                  <div style={{ marginBottom: 32 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <h3 style={{ margin: '0 0 4px', fontSize: 15, color: 'var(--text-primary)', fontWeight: 500 }}>Two-Factor Authentication</h3>
                        <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>Add an extra layer of security to your account.</p>
                      </div>
                      <button disabled style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: 6, fontWeight: 500, fontSize: 13, cursor: 'not-allowed', opacity: 0.5 }}>Enable 2FA (Coming Soon)</button>
                    </div>
                  </div>

                  <div>
                    <h3 style={{ margin: '0 0 16px', fontSize: 15, color: 'var(--text-primary)', fontWeight: 500 }}>Active Sessions</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div style={{ padding: 16, background: 'var(--bg-base)', border: '1px solid var(--card-border)', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 16 }}>
                        <div style={{ width: 40, height: 40, borderRadius: 8, background: 'var(--bg-elevated, var(--panel-bg))', color: 'var(--text-primary)', display: 'grid', placeItems: 'center' }}><Laptop size={20} /></div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: 14 }}>Windows / Chrome</div>
                            <span style={{ fontSize: 10, background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', padding: '2px 6px', borderRadius: 4, fontWeight: 800 }}>CURRENT</span>
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>New York, United States &bull; Active now</div>
                        </div>
                      </div>
                      
                      <button disabled style={{ width: '100%', padding: 16, background: 'transparent', border: '1px dashed var(--card-border)', borderRadius: 6, color: 'var(--text-secondary)', cursor: 'not-allowed', fontWeight: 500, fontSize: 13, opacity: 0.5 }}>
                        Log out of all other devices (Coming Soon)
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'appearance' && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--card-border)', overflow: 'hidden' }}>
                <div style={{ padding: 24, borderBottom: '1px solid var(--card-border)' }}>
                  <h2 style={{ margin: '0 0 8px', fontSize: 18, color: 'var(--text-primary)', fontWeight: 600 }}>Appearance</h2>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Customize how the application looks.</p>
                </div>
                
                <div style={{ padding: 32 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
                    {['light', 'dark', 'system'].map(t => (
                      <button 
                        key={t}
                        type="button"
                        onClick={() => setTheme(t)}
                        style={{ 
                          padding: 24, 
                          borderRadius: 8, 
                          border: '2px solid',
                          borderColor: (t === currentTheme || (t === 'system' && !localStorage.getItem('theme'))) ? 'var(--text-primary)' : 'var(--card-border)',
                          background: 'var(--bg-base)',
                          color: 'var(--text-primary)',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          gap: 16,
                          textTransform: 'capitalize',
                          fontWeight: 500,
                          fontSize: 14
                        }}>
                        <div style={{ width: 48, height: 48, borderRadius: '50%', background: (t === currentTheme) ? 'var(--text-primary)' : 'var(--bg-panel)', border: '1px solid var(--card-border)', display: 'grid', placeItems: 'center', color: (t === currentTheme) ? 'var(--main-bg)' : 'var(--text-secondary)' }}>
                          <Globe size={24} />
                        </div>
                        {t} Theme
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              
              {/* Top Panel: Header & Table */}
              <div style={{ background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--card-border)', overflow: 'hidden' }}>
                {/* Header */}
                <div style={{ padding: 24, borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h2 style={{ margin: '0 0 8px', fontSize: 18, color: 'var(--text-primary)', fontWeight: 600 }}>Sending Accounts</h2>
                    <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Connect and manage the email accounts you use to send campaigns.</p>
                  </div>
                  <button onClick={() => setShowConnectionWizard(true)} style={{ padding: '8px 16px', background: 'var(--text-primary)', color: 'var(--bg-base)', borderRadius: 6, fontWeight: 600, fontSize: 13, cursor: 'pointer', border: 'none', display: 'flex', alignItems: 'center', gap: 6 }}>
                    + Connect Account
                  </button>
                </div>

                {/* Table */}
                <div style={{ width: '100%', overflowX: 'auto' }}>
                  {loadingAccounts ? (
                    <div style={{ padding: 48, textAlign: 'center' }}>
                      <Loader2 className="animate-spin" size={32} style={{ color: 'var(--text-secondary)', margin: '0 auto 16px' }} />
                      <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Loading accounts...</p>
                    </div>
                  ) : !loadingAccounts && accounts.length === 0 ? (
                    <div style={{ padding: 48, textAlign: 'center' }}>
                      <Mail size={32} style={{ color: 'var(--text-secondary)', marginBottom: 16 }} />
                      <h3 style={{ margin: '0 0 8px', fontSize: 16, color: 'var(--text-primary)' }}>No accounts connected</h3>
                      <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Connect an email account to start sending campaigns.</p>
                    </div>
                  ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                      <thead>
                        <tr>
                          <th style={{ padding: '12px 24px', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--card-border)' }}>Account</th>
                          <th style={{ padding: '12px 24px', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--card-border)' }}>Provider</th>
                          <th style={{ padding: '12px 24px', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--card-border)' }}>Status</th>
                          <th style={{ padding: '12px 24px', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--card-border)' }}>Default</th>
                          <th style={{ padding: '12px 24px', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid var(--card-border)', textAlign: 'right' }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {accounts.map((acc, idx) => (
                          <tr key={acc.account_id} style={{ borderBottom: idx === accounts.length - 1 ? 'none' : '1px solid var(--card-border)' }}>
                            <td style={{ padding: '16px 24px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-base)', display: 'grid', placeItems: 'center', color: 'var(--text-primary)', fontWeight: 600, fontSize: 14, border: '1px solid var(--card-border)' }}>
                                  {acc.email_address ? acc.email_address[0].toUpperCase() : 'A'}
                                </div>
                                <div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 14 }}>{acc.email_address}</span>
                                    {acc.is_shadow_alias && (
                                      <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.3)', fontWeight: 600 }}>
                                        ⚠️ Shadow Alias
                                      </span>
                                    )}
                                  </div>
                                  <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginTop: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <span>Sender Name: <strong>{acc.display_name || `${formData.firstName} ${formData.lastName}`.trim() || 'Not set'}</strong></span>
                                    <button 
                                      type="button" 
                                      onClick={() => handleUpdateDisplayName(acc.account_id, acc.display_name)}
                                      style={{ background: 'none', border: 'none', color: 'var(--brand)', cursor: 'pointer', fontSize: 11, padding: 0, textDecoration: 'underline' }}>
                                      Edit
                                    </button>
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td style={{ padding: '16px 24px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)', fontSize: 13 }}>
                                {acc.provider === 'microsoft' && <span style={{ color: '#0078d4', fontWeight: 900, fontSize: 14 }}>O</span>}
                                {acc.provider === 'google' && <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" alt="Google" style={{ width: 14, height: 14 }} />}
                                {acc.provider === 'yahoo' && <span style={{ color: '#6001d2', fontWeight: 900, fontSize: 14 }}>Y!</span>}
                                {acc.provider === 'smtp' && <Server size={14} />}
                                {acc.provider === 'microsoft' ? 'Microsoft 365' : acc.provider === 'google' ? 'Gmail' : acc.provider === 'yahoo' ? 'Yahoo Mail' : 'Custom SMTP'}
                              </div>
                            </td>
                            <td style={{ padding: '16px 24px' }}>
                              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: acc.health_status === 'healthy' ? '#10b981' : '#ef4444', fontSize: 13, background: acc.health_status === 'healthy' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', padding: '4px 8px', borderRadius: 12 }}>
                                <div style={{ width: 6, height: 6, borderRadius: '50%', background: acc.health_status === 'healthy' ? '#10b981' : '#ef4444' }} />
                                {acc.health_status === 'healthy' ? 'Connected' : 'Error'}
                              </div>
                            </td>
                            <td style={{ padding: '16px 24px', textAlign: 'center' }}>
                              <Star size={16} style={{ color: acc.is_default ? '#f59e0b' : 'var(--text-tertiary)', fill: acc.is_default ? '#f59e0b' : 'transparent' }} />
                            </td>
                            <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center' }}>
                                <button onClick={() => handleUpdateDisplayName(acc.account_id, acc.display_name)} style={{ padding: '6px 10px', background: 'transparent', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}>Name</button>
                                {!acc.is_default && (
                                  <button onClick={() => handleSetDefaultAccount(acc.account_id)} style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}>Make Default</button>
                                )}
                                <button onClick={() => handleTestConnection(acc.account_id)} style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}>Test</button>
                                <button onClick={() => handleDeleteAccount(acc.account_id)} style={{ padding: '6px 8px', background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                                  <MoreVertical size={16} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Supported Providers */}
              <div style={{ background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--card-border)', padding: 24 }}>
                <h3 style={{ margin: '0 0 8px', fontSize: 16, color: 'var(--text-primary)', fontWeight: 600 }}>Supported Providers</h3>
                <p style={{ margin: '0 0 24px', fontSize: 14, color: 'var(--text-secondary)' }}>Choose a provider to connect your email account.</p>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
                  {[
                    { id: 'microsoft', name: 'Microsoft 365', desc: 'Connect your Outlook or Microsoft 365 account.', icon: <span style={{ color: '#0078d4', fontWeight: 900, fontSize: 20 }}>O</span> },
                    { id: 'google', name: 'Gmail', desc: 'Connect your Gmail or Google Workspace account.', icon: <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" alt="Google" style={{ width: 20, height: 20 }} /> },
                    { id: 'yahoo', name: 'Yahoo Mail', desc: 'Connect your Yahoo Mail account securely.', icon: <span style={{ color: '#6001d2', fontWeight: 900, fontSize: 20 }}>Y!</span> },
                    { id: 'smtp', name: 'Custom SMTP', desc: 'Use custom SMTP settings for any email provider.', icon: <Mail size={20} style={{ color: 'var(--text-secondary)' }} /> }
                  ].map(provider => (
                    <div key={provider.id} style={{ border: '1px solid var(--card-border)', borderRadius: 8, padding: 20, display: 'flex', flexDirection: 'column', height: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                        <div style={{ width: 36, height: 36, background: 'var(--bg-base)', borderRadius: 8, display: 'grid', placeItems: 'center' }}>
                          {provider.icon}
                        </div>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 15 }}>{provider.name}</div>
                      </div>
                      <p style={{ margin: '0 0 20px', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5, flex: 1 }}>{provider.desc}</p>
                      <button onClick={() => setShowConnectionWizard(true)} style={{ width: '100%', padding: '8px', background: 'var(--bg-base)', border: '1px solid var(--card-border)', color: 'var(--text-primary)', borderRadius: 6, fontWeight: 500, fontSize: 13, cursor: 'pointer' }}>
                        Connect
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Security Alert */}
              <div style={{ background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--card-border)', padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ width: 40, height: 40, background: 'rgba(255, 255, 255, 0.05)', borderRadius: '50%', display: 'grid', placeItems: 'center' }}>
                    <Lock size={18} style={{ color: 'var(--text-secondary)' }} />
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-primary)', fontWeight: 500, fontSize: 14, marginBottom: 4 }}>Your credentials are encrypted and stored securely.</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>We never store your password. You can revoke access at any time.</div>
                  </div>
                </div>
                <a href="#" style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', fontSize: 13, textDecoration: 'none' }}>
                  Learn more <ExternalLink size={14} />
                </a>
              </div>

              {showConnectionWizard && (
                <ConnectionWizard 
                  onClose={() => setShowConnectionWizard(false)}
                  onSuccess={() => {
                    setShowConnectionWizard(false);
                    fetchAccounts();
                  }}
                />
              )}
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ background: 'var(--bg-panel)', borderRadius: 8, border: '1px solid var(--card-border)', overflow: 'hidden' }}>
                <div style={{ padding: 24, borderBottom: '1px solid var(--card-border)' }}>
                  <h2 style={{ margin: '0 0 8px', fontSize: 18, color: 'var(--text-primary)', fontWeight: 600 }}>Notifications</h2>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Manage how you receive alerts and updates.</p>
                </div>
                
                <div style={{ padding: 48, textAlign: 'center' }}>
                  <Bell size={32} style={{ color: 'var(--text-secondary)', marginBottom: 16 }} />
                  <h3 style={{ margin: '0 0 8px', fontSize: 16, color: 'var(--text-primary)', fontWeight: 500 }}>Notifications are managed globally</h3>
                  <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>Notification settings are currently managed by your organization administrator.</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'extension' && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              {/* Banner */}
              <div style={{
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(56, 189, 248, 0.08) 100%)',
                border: '1px solid rgba(99, 102, 241, 0.35)', borderRadius: 12, padding: '24px 28px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                    <Puzzle size={22} color="#818cf8" />
                    <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                      Talent Scout Chrome Extension
                    </h2>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 13, margin: 0, lineHeight: 1.5, maxWidth: 520 }}>
                    Automatically capture and enrich recruiter profiles from LinkedIn, Gmail, Outlook, and job sites as you browse the web.
                  </p>
                </div>
                <button
                  onClick={() => {
                    const downloadUrl = 'https://talentopsai-1.onrender.com/recruiters/extension/download';
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = 'talentops-scout-extension.zip';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    toast.success('Extension package downloaded!');
                  }}
                  style={{
                    padding: '10px 22px', background: '#6366f1', color: '#ffffff', border: 'none',
                    borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: 'pointer', display: 'flex',
                    alignItems: 'center', gap: 8, boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)',
                    whiteSpace: 'nowrap'
                  }}
                >
                  <Download size={16} />
                  <span>⚡ 1-Click Download</span>
                </button>
              </div>

              {/* 3 Steps */}
              <div style={{ background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--card-border)', padding: 24 }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 16px' }}>
                  Quick 3-Step Setup
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                  <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, padding: 14 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#818cf8', marginBottom: 4 }}>1. Download ZIP</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Click the button above and unzip the downloaded folder.</div>
                  </div>
                  <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, padding: 14 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8', marginBottom: 4 }}>2. Open Extensions</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Go to <code>chrome://extensions/</code> and enable Developer mode.</div>
                  </div>
                  <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 10, padding: 14 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#4ade80', marginBottom: 4 }}>3. Load & Activate</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Click <b>Load unpacked</b>, select the folder, and enter your activation code.</div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
