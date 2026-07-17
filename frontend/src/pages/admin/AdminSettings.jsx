import { useState, useEffect } from 'react';
import api, { getErrorMessage } from '../../services/api';
import { Save, ShieldCheck, Mail, Globe, Lock, HardDrive, RefreshCw } from 'lucide-react';

export default function AdminSettings() {
  const [activeTab, setActiveTab] = useState('general');
  const [settings, setSettings] = useState({
    general_platformName: 'TalentOps AI',
    general_timezone: 'UTC',
    general_language: 'en-US',
    auth_googleEnabled: true,
    auth_microsoftEnabled: false,
    auth_sessionTimeout: 60,
    email_smtpStatus: 'connected',
    email_defaultSender: 'noreply@talentops.ai',
    sec_rateLimits: 100,
    sec_ipWhitelist: '',
    sys_dataRetentionDays: 365
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/settings');
      if (data && Object.keys(data).length > 0) {
        setSettings(prev => ({ ...prev, ...data }));
      }
    } catch (err) {
      console.error('Settings not loaded from server, using defaults.', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.post('/admin/settings', settings);
      alert('Settings saved successfully!');
    } catch (err) {
      alert(getErrorMessage(err, 'Failed to save settings'));
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const tabs = [
    { id: 'general', label: 'General', icon: Globe },
    { id: 'auth', label: 'Authentication', icon: ShieldCheck },
    { id: 'email', label: 'Email & SMTP', icon: Mail },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'system', label: 'System & Data', icon: HardDrive }
  ];

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1200, margin: '0 auto', color: 'var(--text-primary)', fontFamily: '"Inter", sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, background: 'linear-gradient(90deg, #fff, #aaa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Platform Settings</h1>
          <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: 14 }}>Global configurations for the TalentOps AI platform.</p>
        </div>
        <button 
          onClick={handleSave} 
          disabled={saving || loading}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 24px', borderRadius: 8, background: '#3b82f6', color: 'var(--text-inverse)', border: 'none', fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer', transition: 'all 0.2s', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)' }}
        >
          {saving ? <RefreshCw size={18} className="animate-spin" /> : <Save size={18} />}
          Save Changes
        </button>
      </div>

      <div style={{ display: 'flex', gap: 32 }}>
        {/* Sidebar Tabs */}
        <div style={{ width: 240, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
                background: activeTab === tab.id ? 'rgba(255,255,255,0.08)' : 'transparent',
                color: activeTab === tab.id ? '#fff' : 'var(--text-muted)',
                fontWeight: activeTab === tab.id ? 600 : 500,
                transition: 'all 0.2s',
                textAlign: 'left'
              }}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div style={{ flex: 1, background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: 32, minHeight: 500 }}>
          {loading ? (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 100 }}>Loading settings...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              
              {activeTab === 'general' && (
                <>
                  <h2 style={{ margin: '0 0 16px', fontSize: 20 }}>General Settings</h2>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <label style={{ fontSize: 13, color: 'var(--text-muted)' }}>Platform Name</label>
                    <input value={settings.general_platformName} onChange={e => handleChange('general_platformName', e.target.value)} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-inverse)', outline: 'none' }} />
                  </div>

                  <div style={{ display: 'flex', gap: 16 }}>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <label style={{ fontSize: 13, color: 'var(--text-muted)' }}>Timezone</label>
                      <select value={settings.general_timezone} onChange={e => handleChange('general_timezone', e.target.value)} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-inverse)', outline: 'none' }}>
                        <option value="UTC">UTC</option>
                        <option value="America/New_York">Eastern Time (US & Canada)</option>
                        <option value="America/Los_Angeles">Pacific Time (US & Canada)</option>
                      </select>
                    </div>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <label style={{ fontSize: 13, color: 'var(--text-muted)' }}>Language</label>
                      <select value={settings.general_language} onChange={e => handleChange('general_language', e.target.value)} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-inverse)', outline: 'none' }}>
                        <option value="en-US">English (US)</option>
                        <option value="en-GB">English (UK)</option>
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                      </select>
                    </div>
                  </div>
                </>
              )}

              {activeTab === 'auth' && (
                <>
                  <h2 style={{ margin: '0 0 16px', fontSize: 20 }}>Authentication</h2>
                  
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--card-border)' }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>Google OAuth</div>
                      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Allow users to sign in with their Google accounts.</div>
                    </div>
                    <input type="checkbox" checked={settings.auth_googleEnabled} onChange={e => handleChange('auth_googleEnabled', e.target.checked)} style={{ transform: 'scale(1.2)' }} />
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--card-border)' }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>Microsoft OAuth</div>
                      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Allow users to sign in with Microsoft/Office365.</div>
                    </div>
                    <input type="checkbox" checked={settings.auth_microsoftEnabled} onChange={e => handleChange('auth_microsoftEnabled', e.target.checked)} style={{ transform: 'scale(1.2)' }} />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
                    <label style={{ fontSize: 13, color: 'var(--text-muted)' }}>Session Timeout (Minutes)</label>
                    <input type="number" value={settings.auth_sessionTimeout} onChange={e => handleChange('auth_sessionTimeout', e.target.value)} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-inverse)', width: 200, outline: 'none' }} />
                  </div>
                </>
              )}

              {activeTab === 'email' && (
                <>
                  <h2 style={{ margin: '0 0 16px', fontSize: 20 }}>Email & SMTP</h2>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <label style={{ fontSize: 13, color: 'var(--text-muted)' }}>Default Sender Email</label>
                    <input value={settings.email_defaultSender} onChange={e => handleChange('email_defaultSender', e.target.value)} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-inverse)', outline: 'none' }} />
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 16, background: 'rgba(16, 185, 129, 0.1)', borderRadius: 8, border: '1px solid rgba(16, 185, 129, 0.3)', marginTop: 16 }}>
                    <ShieldCheck size={20} color="#10b981" />
                    <div>
                      <div style={{ fontWeight: 600, color: '#10b981' }}>SMTP Connected</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>The email gateway is functioning normally.</div>
                    </div>
                    <button style={{ marginLeft: 'auto', padding: '6px 12px', background: 'var(--accent-bg)', border: 'none', borderRadius: 6, color: 'var(--text-inverse)', cursor: 'pointer', fontSize: 12 }}>Send Test Email</button>
                  </div>
                </>
              )}

              {activeTab === 'security' && (
                <>
                  <h2 style={{ margin: '0 0 16px', fontSize: 20 }}>Security</h2>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <label style={{ fontSize: 13, color: 'var(--text-muted)' }}>API Rate Limit (Requests / minute)</label>
                    <input type="number" value={settings.sec_rateLimits} onChange={e => handleChange('sec_rateLimits', e.target.value)} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-inverse)', width: 200, outline: 'none' }} />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
                    <label style={{ fontSize: 13, color: 'var(--text-muted)' }}>IP Whitelist (Comma separated)</label>
                    <textarea value={settings.sec_ipWhitelist} onChange={e => handleChange('sec_ipWhitelist', e.target.value)} rows={4} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-inverse)', resize: 'vertical', outline: 'none' }} placeholder="e.g. 192.168.1.1, 10.0.0.0/24" />
                  </div>
                </>
              )}

              {activeTab === 'system' && (
                <>
                  <h2 style={{ margin: '0 0 16px', fontSize: 20 }}>System & Data</h2>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <label style={{ fontSize: 13, color: 'var(--text-muted)' }}>Data Retention (Days)</label>
                    <input type="number" value={settings.sys_dataRetentionDays} onChange={e => handleChange('sys_dataRetentionDays', e.target.value)} style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', color: 'var(--text-inverse)', width: 200, outline: 'none' }} />
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--card-border)', marginTop: 24 }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>Database Backup</div>
                      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Trigger a manual PostgreSQL dump to secure storage.</div>
                    </div>
                    <button style={{ padding: '8px 16px', background: 'var(--accent-bg)', border: 'none', borderRadius: 6, color: 'var(--text-inverse)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>Backup Now</button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
