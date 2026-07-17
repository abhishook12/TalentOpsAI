import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import toast from 'react-hot-toast';
import { Monitor, User, Shield, Bell, Blocks, Key, Globe, Smartphone } from 'lucide-react';

export default function Settings() {
  const { user, checkAuth } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');
  
  // Profile state
  const [profileData, setProfileData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    company: user?.company || '',
    country: user?.country || '',
  });

  const [isSaving, setIsSaving] = useState(false);

  const handleProfileSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const res = await api.put('/users/me', profileData);
      checkAuth();
      toast.success('Profile updated successfully');
    } catch (err) {
      toast.error('Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleThemeChange = (newTheme) => {
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return (
    <div style={{ padding: '32px', maxWidth: 1200, margin: '0 auto', width: '100%' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ margin: '0 0 8px', fontSize: 28, fontWeight: 800, color: 'var(--text-primary)' }}>Settings</h1>
        <p style={{ margin: 0, color: 'var(--text-secondary)' }}>Manage your account settings and preferences.</p>
      </div>

      <div style={{ display: 'flex', gap: 32, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Sidebar */}
        <div style={{ width: 250, display: 'flex', flexDirection: 'column', gap: 4, flexShrink: 0 }}>
          {[
            { id: 'profile', icon: User, label: 'Profile Settings' },
            { id: 'account', icon: Key, label: 'Account Settings' },
            { id: 'appearance', icon: Monitor, label: 'Appearance' },
            { id: 'notifications', icon: Bell, label: 'Notifications' },
            { id: 'security', icon: Shield, label: 'Privacy & Security' },
            { id: 'integrations', icon: Blocks, label: 'API / Integrations' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 500,
                background: activeTab === tab.id ? 'var(--accent-bg)' : 'transparent',
                color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-secondary)',
                transition: 'all 0.2s', textAlign: 'left'
              }}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: '1 1 500px', background: 'var(--panel-bg)', borderRadius: 16, border: '1px solid var(--card-border)', padding: 32 }}>
          
          {activeTab === 'profile' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Profile Settings</h2>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 32 }}>
                <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'var(--accent-bg)', color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, fontWeight: 700 }}>
                  {user?.first_name?.[0] || 'U'}{user?.last_name?.[0] || ''}
                </div>
                <div>
                  <button style={{ padding: '8px 16px', background: 'var(--accent)', color: 'var(--text-inverse)', border: 'none', borderRadius: 8, fontWeight: 500, cursor: 'pointer' }}>Change Avatar</button>
                  <p style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--text-muted)' }}>JPG, GIF or PNG. Max size of 800K</p>
                </div>
              </div>

              <form onSubmit={handleProfileSave} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                <div style={{ display: 'flex', gap: 20 }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: 8, fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>First Name</label>
                    <input required value={profileData.first_name} onChange={e => setProfileData({...profileData, first_name: e.target.value})} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: 8, fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>Last Name</label>
                    <input required value={profileData.last_name} onChange={e => setProfileData({...profileData, last_name: e.target.value})} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 20 }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: 8, fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>Company</label>
                    <input value={profileData.company} onChange={e => setProfileData({...profileData, company: e.target.value})} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: 8, fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>Country</label>
                    <input value={profileData.country} onChange={e => setProfileData({...profileData, country: e.target.value})} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                  </div>
                </div>
                <div style={{ marginTop: 12 }}>
                  <button type="submit" disabled={isSaving} style={{ padding: '10px 24px', background: 'var(--accent)', color: 'var(--text-inverse)', border: 'none', borderRadius: 8, fontWeight: 600, cursor: isSaving ? 'not-allowed' : 'pointer', opacity: isSaving ? 0.7 : 1 }}>
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {activeTab === 'appearance' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Appearance</h2>
              <p style={{ margin: '0 0 24px', color: 'var(--text-secondary)' }}>Customize the UI theme of your workspace.</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20 }}>
                {['light', 'dark', 'system'].map(mode => (
                  <button
                    key={mode}
                    onClick={() => handleThemeChange(mode)}
                    style={{
                      padding: 20, borderRadius: 12, border: `2px solid ${theme === mode ? 'var(--accent)' : 'var(--card-border)'}`,
                      background: 'var(--bg-surface)', cursor: 'pointer', textAlign: 'left',
                      display: 'flex', flexDirection: 'column', gap: 12
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-primary)', fontWeight: 600, textTransform: 'capitalize' }}>
                      <Monitor size={18}/>
                      {mode} Mode
                    </div>
                    <div style={{ height: 60, borderRadius: 6, background: mode === 'light' ? '#f8fafc' : mode === 'dark' ? '#141414' : 'var(--bg-primary)', border: '1px solid var(--card-border)', display: 'flex', padding: 8, gap: 8 }}>
                      <div style={{ width: '30%', background: mode === 'light' ? '#e2e8f0' : '#2a2a2a', borderRadius: 4 }}></div>
                      <div style={{ width: '70%', background: mode === 'light' ? '#ffffff' : '#202020', borderRadius: 4 }}></div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'account' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Account Settings</h2>
              
              <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, marginBottom: 24 }}>
                <h3 style={{ margin: '0 0 16px', fontSize: 16, color: 'var(--text-primary)' }}>Email Address</h3>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ color: 'var(--text-secondary)' }}>{user?.email}</div>
                  <button style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 6, color: 'var(--text-primary)', cursor: 'pointer' }}>Change Email</button>
                </div>
              </div>

              <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, marginBottom: 24 }}>
                <h3 style={{ margin: '0 0 16px', fontSize: 16, color: 'var(--text-primary)' }}>Change Password</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <input type="password" placeholder="Current Password" style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                  <input type="password" placeholder="New Password" style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-surface)', color: 'var(--text-primary)', outline: 'none' }} />
                  <button style={{ padding: '8px 16px', background: 'var(--accent-bg)', color: 'var(--accent)', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', width: 'fit-content' }}>Update Password</button>
                </div>
              </div>

              <div style={{ padding: 20, border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 12, background: 'rgba(239, 68, 68, 0.05)' }}>
                <h3 style={{ margin: '0 0 8px', fontSize: 16, color: '#ef4444' }}>Delete Account</h3>
                <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--text-secondary)' }}>Once you delete your account, there is no going back. Please be certain.</p>
                <button style={{ padding: '8px 16px', background: '#ef4444', color: 'var(--text-inverse)', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}>Delete Account</button>
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
                <button style={{ padding: '8px 16px', background: 'var(--accent-bg)', color: 'var(--accent)', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}>Enable 2FA</button>
              </div>

              <h3 style={{ margin: '0 0 16px', fontSize: 16, color: 'var(--text-primary)' }}>Active Sessions</h3>
              <div style={{ border: '1px solid var(--card-border)', borderRadius: 12, overflow: 'hidden' }}>
                <div style={{ padding: 16, borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', gap: 16, background: 'var(--bg-surface)' }}>
                  <Monitor size={24} color="var(--accent)" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>Windows 11 • Chrome (Current)</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>IP: 192.168.1.1 • Last active: Just now</div>
                  </div>
                </div>
                <div style={{ padding: 16, display: 'flex', alignItems: 'center', gap: 16, background: 'var(--bg-surface)' }}>
                  <Smartphone size={24} color="var(--text-muted)" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>iPhone 14 • Safari</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>IP: 192.168.1.5 • Last active: 2 hours ago</div>
                  </div>
                  <button style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 6, color: 'var(--text-primary)', cursor: 'pointer', fontSize: 13 }}>Revoke</button>
                </div>
              </div>
              <div style={{ marginTop: 16, textAlign: 'right' }}>
                <button style={{ padding: '8px 16px', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer' }}>Logout from all other devices</button>
              </div>
            </div>
          )}

          {activeTab === 'integrations' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>API / Integrations</h2>
              
              <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <Globe size={32} color="var(--accent)" />
                  <div>
                    <h3 style={{ margin: '0 0 4px', fontSize: 16, color: 'var(--text-primary)' }}>Google Workspace</h3>
                    <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>Sync calendar and contacts.</p>
                  </div>
                </div>
                <div style={{ padding: '4px 8px', background: 'var(--accent-bg)', color: 'var(--accent)', borderRadius: 4, fontSize: 12, fontWeight: 600 }}>Connected</div>
              </div>

              <div style={{ padding: 20, border: '1px solid var(--card-border)', borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ width: 32, height: 32, background: 'var(--accent)', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-inverse)', fontWeight: 800 }}>M</div>
                  <div>
                    <h3 style={{ margin: '0 0 4px', fontSize: 16, color: 'var(--text-primary)' }}>Microsoft Outlook</h3>
                    <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>Sync Microsoft 365 services.</p>
                  </div>
                </div>
                <button style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--card-border)', borderRadius: 6, color: 'var(--text-primary)', cursor: 'pointer', fontSize: 13 }}>Connect</button>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="animate-fade-in">
              <h2 style={{ margin: '0 0 24px', fontSize: 20, color: 'var(--text-primary)' }}>Notifications</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {[
                  { title: 'Email Notifications', desc: 'Receive daily summary emails.', checked: true },
                  { title: 'Campaign Alerts', desc: 'Get notified when a campaign finishes.', checked: true },
                  { title: 'Security Alerts', desc: 'Important notifications about your account security.', checked: true },
                  { title: 'Product Updates', desc: 'News about product and feature updates.', checked: false }
                ].map((item, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 0', borderBottom: i < 3 ? '1px solid var(--card-border)' : 'none' }}>
                    <div>
                      <div style={{ fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>{item.title}</div>
                      <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{item.desc}</div>
                    </div>
                    <label style={{ position: 'relative', display: 'inline-block', width: 44, height: 24 }}>
                      <input type="checkbox" defaultChecked={item.checked} style={{ opacity: 0, width: 0, height: 0 }} />
                      <span style={{ position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: item.checked ? 'var(--accent)' : 'var(--card-border-strong)', transition: '.4s', borderRadius: 34 }}>
                        <span style={{ position: 'absolute', content: '""', height: 18, width: 18, left: item.checked ? 22 : 3, bottom: 3, backgroundColor: 'white', transition: '.4s', borderRadius: '50%' }}></span>
                      </span>
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

