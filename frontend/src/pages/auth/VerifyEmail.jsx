import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, useSearch, Link } from '@tanstack/react-router';

export default function VerifyEmail() {
  const [status, setStatus] = useState('verifying'); // 'verifying', 'success', 'error'
  const [message, setMessage] = useState('');
  
  const { verifyEmail } = useAuth();
  const navigate = useNavigate();
  // We assume tanstack router will pass search params, e.g. ?token=...
  const search = useSearch({ strict: false });
  const token = search.token || '';

  useEffect(() => {
    const doVerify = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Invalid or missing verification token.');
        return;
      }

      try {
        await verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been successfully verified!');
        setTimeout(() => {
          navigate({ to: '/login' });
        }, 3000);
      } catch (err) {
        setStatus('error');
        setMessage(err?.response?.data?.detail || 'Verification failed. The link may be expired or invalid.');
      }
    };

    doVerify();
  }, [token, verifyEmail, navigate]);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--main-bg, #09090b)',
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '420px',
        background: 'var(--card-bg, #18181b)',
        borderRadius: '16px',
        padding: '40px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        border: '1px solid rgba(255,255,255,0.05)',
        textAlign: 'center'
      }}>
        {status === 'verifying' && (
          <>
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'center' }}>
              <i className="ti ti-loader animate-spin" style={{ fontSize: '48px', color: '#3b82f6' }} />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#fff', margin: '0 0 8px 0' }}>Verifying Email</h1>
            <p style={{ color: '#a1a1aa', margin: 0, fontSize: '14px' }}>Please wait while we verify your email address...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'center' }}>
              <i className="ti ti-circle-check" style={{ fontSize: '48px', color: '#22c55e' }} />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#fff', margin: '0 0 8px 0' }}>Email Verified</h1>
            <p style={{ color: '#a1a1aa', margin: '0 0 24px 0', fontSize: '14px' }}>{message}</p>
            <Link to="/login" style={{
              display: 'inline-block',
              padding: '12px 24px',
              borderRadius: '8px',
              background: '#3b82f6',
              color: '#fff',
              textDecoration: 'none',
              fontWeight: '500',
              transition: 'background 0.2s'
            }}>
              Go to Login
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'center' }}>
              <i className="ti ti-alert-circle" style={{ fontSize: '48px', color: '#ef4444' }} />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#fff', margin: '0 0 8px 0' }}>Verification Failed</h1>
            <p style={{ color: '#a1a1aa', margin: '0 0 24px 0', fontSize: '14px' }}>{message}</p>
            <Link to="/login" style={{
              display: 'inline-block',
              padding: '12px 24px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.1)',
              color: '#fff',
              textDecoration: 'none',
              fontWeight: '500',
              transition: 'background 0.2s'
            }}>
              Return to Login
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
