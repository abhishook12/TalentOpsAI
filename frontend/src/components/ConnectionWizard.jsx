import React, { useState } from 'react';
import { X, Mail, Server, Lock, User, ArrowRight } from 'lucide-react';
import api, { API } from '../services/api';
import toast from 'react-hot-toast';

export default function ConnectionWizard({ onClose, onSuccess }) {
  const [step, setStep] = useState('email'); // email, oauth_redirect, smtp_form
  const [email, setEmail] = useState('');
  const [provider, setProvider] = useState(null); // 'google', 'microsoft', 'yahoo', 'custom'
  const [isLoading, setIsLoading] = useState(false);
  
  const [smtpData, setSmtpData] = useState({
    display_name: '',
    smtp_host: '',
    smtp_port: '587',
    smtp_user: '',
    smtp_pass: ''
  });

  const handleNext = async (e) => {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      return toast.error('Please enter a valid email address');
    }
    
    setIsLoading(true);
    try {
      const res = await api.post('/accounts/wizard', { email });
      setProvider(res.data.provider);
      
      if (res.data.provider === 'microsoft' || res.data.provider === 'google') {
        setStep('oauth_redirect');
      } else {
        // For Yahoo, Custom, default to SMTP Form for MVP
        setStep('smtp_form');
        setSmtpData(prev => ({
          ...prev,
          smtp_user: email,
          smtp_host: res.data.provider === 'yahoo' ? 'smtp.mail.yahoo.com' : ''
        }));
      }
    } catch (err) {
      toast.error('Failed to detect provider');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthConnect = () => {
    const token = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
    // Use /bridge/google/login for Google, and /bridge/oauth/login for Microsoft
    const endpoint = provider === 'google' ? 'google/login' : 'oauth/login';
    const w = window.open(`${API}/bridge/${endpoint}?popup=true&token=${token}`, 'Connect Account', 'width=500,height=600');
    
    const messageListener = async (event) => {
      if (event.data === 'oauth_success') {
        window.removeEventListener('message', messageListener);
        toast.success(`Successfully connected ${provider === 'google' ? 'Google' : 'Microsoft'} account!`);
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
        email_address: email,
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

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: 'var(--bg-surface)', padding: 32, borderRadius: 12, width: 480, maxWidth: '90%', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: 16, right: 16, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
          <X size={20} />
        </button>
        
        <h2 style={{ margin: '0 0 24px', fontSize: 24, color: 'var(--text-primary)' }}>Connect Sending Account</h2>
        
        {step === 'email' && (
          <form onSubmit={handleNext}>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>Enter the email address you want to send campaigns from. We will automatically detect your provider.</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 24 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Email Address</label>
              <div style={{ position: 'relative' }}>
                <Mail size={18} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                <input 
                  autoFocus
                  type="email" 
                  value={email} 
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com" 
                  style={{ width: '100%', padding: '12px 14px 12px 42px', borderRadius: 8, border: '1px solid var(--card-border)', background: 'var(--bg-base)', color: 'var(--text-primary)', outline: 'none' }} 
                />
              </div>
            </div>
            <button type="submit" disabled={isLoading} className="btn-primary" style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8, padding: 14, fontSize: 15 }}>
              {isLoading ? 'Detecting...' : 'Continue'} <ArrowRight size={18} />
            </button>
          </form>
        )}

        {step === 'oauth_redirect' && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div style={{ width: 64, height: 64, background: provider === 'google' ? 'rgba(234, 67, 53, 0.1)' : 'rgba(0, 120, 212, 0.1)', color: provider === 'google' ? '#ea4335' : '#0078d4', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px' }}>
              <Mail size={32} />
            </div>
            <h3 style={{ margin: '0 0 12px', fontSize: 18 }}>{provider === 'google' ? 'Google Account' : 'Microsoft Account'} Detected</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>Click below to securely authenticate with {provider === 'google' ? 'Google' : 'Microsoft'}.</p>
            <button onClick={handleOAuthConnect} className="btn-primary" style={{ padding: '12px 24px', fontSize: 15, background: provider === 'google' ? '#ea4335' : undefined }}>
              Authenticate with {provider === 'google' ? 'Google' : 'Microsoft'}
            </button>
          </div>
        )}

        {step === 'smtp_form' && (
          <form onSubmit={handleSmtpSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ padding: '12px 16px', background: 'var(--brand-bg)', color: 'var(--brand)', borderRadius: 8, fontSize: 14, marginBottom: 8 }}>
              Provider detected: <strong>{provider.toUpperCase()}</strong>. Please provide your SMTP credentials.
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Display Name</label>
                <input value={smtpData.display_name} onChange={e => setSmtpData({...smtpData, display_name: e.target.value})} placeholder="John Doe" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)' }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>SMTP Username</label>
                <input value={smtpData.smtp_user} onChange={e => setSmtpData({...smtpData, smtp_user: e.target.value})} style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)' }} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 16 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>SMTP Host</label>
                <input value={smtpData.smtp_host} onChange={e => setSmtpData({...smtpData, smtp_host: e.target.value})} placeholder="smtp.example.com" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)' }} required />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Port</label>
                <input value={smtpData.smtp_port} onChange={e => setSmtpData({...smtpData, smtp_port: e.target.value})} placeholder="587" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)' }} required />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>App Password / SMTP Password</label>
              <input type="password" value={smtpData.smtp_pass} onChange={e => setSmtpData({...smtpData, smtp_pass: e.target.value})} placeholder="••••••••" style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--bg-base)' }} required />
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
