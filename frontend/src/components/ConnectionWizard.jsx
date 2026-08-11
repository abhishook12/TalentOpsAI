import React, { useState } from 'react';
import { X, Mail, ArrowRight } from 'lucide-react';
import api, { API } from '../services/api';
import toast from 'react-hot-toast';

export default function ConnectionWizard({ onClose, onSuccess }) {
  const [step, setStep] = useState('provider'); // provider, smtp_form
  const [provider, setProvider] = useState(null); // 'google', 'microsoft', 'yahoo', 'custom'
  const [isLoading, setIsLoading] = useState(false);
  
  const [smtpData, setSmtpData] = useState({
    email_address: '',
    display_name: '',
    smtp_host: '',
    smtp_port: '587',
    smtp_user: '',
    smtp_pass: ''
  });

  const handleOAuthConnect = (selectedProvider) => {
    setProvider(selectedProvider);
    const token = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
    const endpoint = selectedProvider === 'google' ? 'google/login' : 'oauth/login';
    const w = window.open(`${API}/bridge/${endpoint}?popup=true&token=${token}`, 'Connect Account', 'width=500,height=600');
    
    const messageListener = async (event) => {
      if (event.data === 'oauth_success') {
        window.removeEventListener('message', messageListener);
        toast.success(`Successfully connected ${selectedProvider === 'google' ? 'Google' : 'Microsoft'} account!`);
        onSuccess();
      }
    };
    window.addEventListener('message', messageListener);
  };

  const handleSmtpSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await api.post('/accounts/smtp', {
        email_address: smtpData.email_address,
        display_name: smtpData.display_name,
        smtp_host: smtpData.smtp_host,
        smtp_port: parseInt(smtpData.smtp_port, 10),
        smtp_user: smtpData.smtp_user,
        smtp_pass: smtpData.smtp_pass
      });
      toast.success('Successfully connected SMTP account!');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'SMTP Connection Failed');
    } finally {
      setIsLoading(false);
    }
  };

  const ProviderCard = ({ name, icon, onClick, bgColor, textColor }) => (
    <button 
      type="button"
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '16px 20px',
        background: 'var(--bg-base)',
        border: '1px solid var(--card-border)',
        borderRadius: 12,
        width: '100%',
        cursor: 'pointer',
        transition: 'all 0.2s',
        textAlign: 'left'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--brand)';
        e.currentTarget.style.background = 'var(--bg-hover)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--card-border)';
        e.currentTarget.style.background = 'var(--bg-base)';
      }}
    >
      <div style={{
        width: 40, height: 40, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: bgColor, color: textColor
      }}>
        {icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{name}</div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Connect {name}</div>
      </div>
      <ArrowRight size={18} style={{ color: 'var(--text-secondary)' }} />
    </button>
  );

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--modal-backdrop-bg, rgba(0,0,0,0.5))', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: 'var(--bg-surface)', padding: 32, borderRadius: 12, width: 480, maxWidth: '90%', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: 16, right: 16, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
          <X size={20} />
        </button>
        
        <h2 style={{ margin: '0 0 8px', fontSize: 24, color: 'var(--text-primary)' }}>Connect a Sending Account</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>Choose the email provider you want to connect.</p>
        
        {step === 'provider' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <ProviderCard 
              name="Microsoft Outlook" 
              icon={<Mail size={20} />} 
              bgColor="rgba(0, 120, 212, 0.1)" 
              textColor="#0078d4" 
              onClick={() => handleOAuthConnect('microsoft')} 
            />
            <ProviderCard 
              name="Gmail" 
              icon={<Mail size={20} />} 
              bgColor="rgba(234, 67, 53, 0.1)" 
              textColor="#ea4335" 
              onClick={() => handleOAuthConnect('google')} 
            />
            <ProviderCard 
              name="Yahoo Mail" 
              icon={<Mail size={20} />} 
              bgColor="rgba(96, 1, 210, 0.1)" 
              textColor="#6001d2" 
              onClick={() => {
                setProvider('yahoo');
                setSmtpData(prev => ({ ...prev, smtp_host: 'smtp.mail.yahoo.com' }));
                setStep('smtp_form');
              }} 
            />
            <ProviderCard 
              name="Other SMTP" 
              icon={<Mail size={20} />} 
              bgColor="var(--bg-hover)" 
              textColor="var(--text-primary)" 
              onClick={() => {
                setProvider('custom');
                setStep('smtp_form');
              }} 
            />
          </div>
        )}

        {step === 'smtp_form' && (
          <form onSubmit={handleSmtpSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <button 
              type="button" 
              onClick={() => setStep('provider')} 
              style={{ background: 'none', border: 'none', color: 'var(--brand)', cursor: 'pointer', textAlign: 'left', padding: 0, fontSize: 14, fontWeight: 500 }}
            >
              ← Back to Providers
            </button>
            
            <div style={{ padding: '12px 16px', background: 'var(--brand-bg)', color: 'var(--brand)', borderRadius: 8, fontSize: 14, marginBottom: 8 }}>
              Configure SMTP for <strong>{provider.toUpperCase()}</strong>.
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Email Address</label>
              <input value={smtpData.email_address} onChange={e => setSmtpData({...smtpData, email_address: e.target.value, smtp_user: e.target.value})} placeholder="you@company.com" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)' }} required type="email" />
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Display Name</label>
                <input value={smtpData.display_name} onChange={e => setSmtpData({...smtpData, display_name: e.target.value})} placeholder="John Doe" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)' }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>SMTP Username</label>
                <input value={smtpData.smtp_user} onChange={e => setSmtpData({...smtpData, smtp_user: e.target.value})} style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)' }} required />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 16 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>SMTP Host</label>
                <input value={smtpData.smtp_host} onChange={e => setSmtpData({...smtpData, smtp_host: e.target.value})} placeholder="smtp.example.com" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)' }} required />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Port</label>
                <input value={smtpData.smtp_port} onChange={e => setSmtpData({...smtpData, smtp_port: e.target.value})} placeholder="587" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)' }} required />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>App Password / SMTP Password</label>
              <input type="password" value={smtpData.smtp_pass} onChange={e => setSmtpData({...smtpData, smtp_pass: e.target.value})} placeholder="••••••••" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)' }} required />
              {provider === 'google' && <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>For Gmail, you must use an <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" style={{ color: 'var(--brand)' }}>App Password</a>.</div>}
            </div>

            <button type="submit" disabled={isLoading} className="btn-primary" style={{ padding: 14, fontSize: 15, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              {isLoading ? 'Connecting...' : 'Connect Account'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
