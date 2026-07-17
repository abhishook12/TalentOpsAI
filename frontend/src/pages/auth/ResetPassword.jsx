import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, useSearch } from '@tanstack/react-router';

export default function ResetPassword() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { resetPassword } = useAuth();
  const navigate = useNavigate();
  // We assume tanstack router will pass search params, e.g. ?token=...
  const search = useSearch({ strict: false });
  const token = search.token || '';

  const getPasswordStrength = () => {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
  };

  const strength = getPasswordStrength();
  const strengthColors = ['#ef4444', '#ef4444', '#f59e0b', '#22c55e', '#22c55e'];
  const strengthLabels = ['Weak', 'Weak', 'Fair', 'Good', 'Strong'];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setStatus('');
    
    if (!token) {
      setError('Invalid or missing reset token.');
      return;
    }

    if (strength < 4) {
      setError('Please meet all password requirements.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    
    try {
      await resetPassword(token, password);
      setStatus('Password reset successful. Redirecting to login...');
      setTimeout(() => {
        navigate({ to: '/login' });
      }, 2000);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to reset password.');
      setIsSubmitting(false);
    }
  };

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
        border: '1px solid var(--card-border)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)', margin: '0 0 8px 0' }}>New Password</h1>
          <p style={{ color: '#a1a1aa', margin: 0, fontSize: '14px' }}>Create a new password for your account</p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            color: '#ef4444',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <i className="ti ti-alert-circle" />
            {error}
          </div>
        )}

        {status && (
          <div style={{
            background: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.2)',
            color: '#22c55e',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <i className="ti ti-check" />
            {status}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
              New Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a strong password"
                style={{
                  width: '100%',
                  padding: '12px 40px 12px 16px',
                  borderRadius: '8px',
                  border: '1px solid var(--card-border)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '15px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: '#a1a1aa',
                  cursor: 'pointer',
                  padding: '4px'
                }}
              >
                <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
              </button>
            </div>
            
            <div style={{ marginTop: '12px', fontSize: '13px', color: '#a1a1aa', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ color: password.length >= 8 ? '#22c55e' : '#a1a1aa' }}>
                <i className={`ti ${password.length >= 8 ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: '6px' }} />
                At least 8 characters
              </div>
              <div style={{ color: /[A-Z]/.test(password) ? '#22c55e' : '#a1a1aa' }}>
                <i className={`ti ${/[A-Z]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: '6px' }} />
                At least 1 uppercase letter
              </div>
              <div style={{ color: /[0-9]/.test(password) ? '#22c55e' : '#a1a1aa' }}>
                <i className={`ti ${/[0-9]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: '6px' }} />
                At least 1 number
              </div>
              <div style={{ color: /[^A-Za-z0-9]/.test(password) ? '#22c55e' : '#a1a1aa' }}>
                <i className={`ti ${/[^A-Za-z0-9]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: '6px' }} />
                At least 1 special character
              </div>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
              Confirm Password
            </label>
            <input
              type={showPassword ? 'text' : 'password'}
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your password"
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid var(--card-border)',
                background: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                fontSize: '15px',
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting || strength < 4 || password !== confirmPassword}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              background: (isSubmitting || strength < 4 || password !== confirmPassword) ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6',
              color: 'var(--text-primary)',
              fontSize: '15px',
              fontWeight: '600',
              border: 'none',
              cursor: (isSubmitting || strength < 4 || password !== confirmPassword) ? 'not-allowed' : 'pointer',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '8px',
              marginTop: '16px',
              transition: 'background 0.2s'
            }}
          >
            {isSubmitting ? (
              <><i className="ti ti-loader animate-spin" /> Resetting...</>
            ) : (
              'Reset Password'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
