import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from '@tanstack/react-router';

export default function Login() {
  const [capsLockActive, setCapsLockActive] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const isEmailValid = email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/);
  const isFormValid = isEmailValid && password.length >= 8;

  const handleKeyUp = (e) => {
    if (e.getModifierState('CapsLock')) {
      setCapsLockActive(true);
    } else {
      setCapsLockActive(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    
    try {
      await login(email, password, rememberMe);
      navigate({ to: '/' });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Invalid email or password');
    } finally {
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
        border: '1px solid rgba(255,255,255,0.05)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ 
            width: '48px', 
            height: '48px', 
            borderRadius: '12px', 
            background: 'linear-gradient(135deg, #3b82f6, #2563eb)', 
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '16px'
          }}>
            <i className="ti ti-brand-graphql" style={{ fontSize: '24px', color: '#fff' }} />
          </div>
          <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#fff', margin: '0 0 8px 0' }}>Welcome back</h1>
          <p style={{ color: '#a1a1aa', margin: 0, fontSize: '14px' }}>Enter your credentials to access your account</p>
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

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.1)',
                background: 'rgba(255,255,255,0.03)',
                color: '#fff',
                fontSize: '15px',
                outline: 'none',
                transition: 'border-color 0.2s'
              }}
              onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
              onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ fontSize: '14px', fontWeight: '500', color: '#e4e4e7' }}>
                Password
              </label>
              <a href="#" style={{ fontSize: '13px', color: '#3b82f6', textDecoration: 'none' }}>Forgot password?</a>
            </div>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyUp={handleKeyUp}
                placeholder="••••••••"
                style={{
                  width: '100%',
                  padding: '12px 40px 12px 16px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(255,255,255,0.03)',
                  color: '#fff',
                  fontSize: '15px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
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
            {capsLockActive && (
              <div style={{ color: '#fbbf24', fontSize: '13px', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <i className="ti ti-alert-triangle" /> Caps Lock is on
              </div>
            )}
            {password && password.length < 8 && (
              <div style={{ color: '#ef4444', fontSize: '13px', marginTop: '8px' }}>
                Password must be at least 8 characters
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="checkbox"
              id="remember"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              style={{
                width: '16px',
                height: '16px',
                borderRadius: '4px',
                accentColor: '#3b82f6',
                cursor: 'pointer'
              }}
            />
            <label htmlFor="remember" style={{ fontSize: '14px', color: '#a1a1aa', cursor: 'pointer' }}>
              Remember for 30 days
            </label>
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !isFormValid}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              background: (!isFormValid || isSubmitting) ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6',
              color: '#fff',
              fontSize: '15px',
              fontWeight: '600',
              border: 'none',
              cursor: (!isFormValid || isSubmitting) ? 'not-allowed' : 'pointer',
              opacity: (!isFormValid || isSubmitting) ? 0.7 : 1,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '8px',
              marginTop: '8px',
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => { if (!isSubmitting && isFormValid) e.target.style.background = '#2563eb' }}
            onMouseOut={(e) => { if (!isSubmitting && isFormValid) e.target.style.background = '#3b82f6' }}
          >
            {isSubmitting ? (
              <><i className="ti ti-loader animate-spin" /> Signing in...</>
            ) : (
              'Sign in'
            )}
          </button>
        </form>

        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          margin: '24px 0',
          color: '#52525b',
          fontSize: '13px'
        }}>
          <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }} />
          <span style={{ padding: '0 12px' }}>OR CONTINUE WITH</span>
          <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }} />
        </div>

        <div style={{ display: 'flex', gap: '12px', position: 'relative' }}>
          <div style={{ 
            position: 'absolute', 
            top: '-10px', 
            right: '-10px', 
            background: '#fbbf24', 
            color: '#000', 
            fontSize: '10px', 
            fontWeight: 'bold', 
            padding: '2px 6px', 
            borderRadius: '12px',
            zIndex: 1
          }}>Coming Soon</div>
          <button disabled style={{
            flex: 1,
            padding: '10px',
            borderRadius: '8px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#a1a1aa',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            opacity: 0.5
          }}>
            <i className="ti ti-brand-google" />
            Google
          </button>
          <button disabled style={{
            flex: 1,
            padding: '10px',
            borderRadius: '8px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#a1a1aa',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            opacity: 0.5
          }}>
            <i className="ti ti-brand-windows" />
            Microsoft
          </button>
        </div>

        <p style={{ textAlign: 'center', marginTop: '32px', fontSize: '14px', color: '#a1a1aa' }}>
          Don't have an account?{' '}
          <Link to="/register" style={{ color: '#3b82f6', textDecoration: 'none', fontWeight: '500' }}>
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
