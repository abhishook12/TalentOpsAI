import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from '@tanstack/react-router';

export default function Register() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [country, setCountry] = useState('US');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { register } = useAuth();
  const navigate = useNavigate();

  const getPasswordStrength = () => {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score; // 0 to 4
  };

  const strength = getPasswordStrength();
  const strengthColors = ['#ef4444', '#ef4444', '#f59e0b', '#22c55e', '#22c55e'];
  const strengthLabels = ['Weak', 'Weak', 'Fair', 'Good', 'Strong'];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    
    if (strength < 4) {
      setError('Please meet all password requirements.');
      setIsSubmitting(false);
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      setIsSubmitting(false);
      return;
    }

    if (!agreeTerms) {
      setError('You must agree to the Terms of Service and Privacy Policy.');
      setIsSubmitting(false);
      return;
    }

    try {
      await register({
        first_name: firstName,
        last_name: lastName,
        email,
        company,
        password
      });
      // Instead of navigating directly to dashboard, navigate to login or auto-login
      navigate({ to: '/login' });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to register account');
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
        maxWidth: '480px',
        background: 'var(--card-bg, #18181b)',
        borderRadius: '16px',
        padding: '40px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        border: '1px solid rgba(255,255,255,0.05)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{ fontSize: '24px', fontWeight: '700', color: '#fff', margin: '0 0 8px 0' }}>Create an account</h1>
          <p style={{ color: '#a1a1aa', margin: 0, fontSize: '14px' }}>Enter your details to get started</p>
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
          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
                First name
              </label>
              <input
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
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
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
                Last name
              </label>
              <input
                type="text"
                required
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
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
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
              Work Email
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
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
              Company (Optional)
            </label>
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Acme Corp"
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
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
              Country
            </label>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.1)',
                background: 'rgba(255,255,255,0.03)',
                color: '#fff',
                fontSize: '15px',
                outline: 'none',
                transition: 'border-color 0.2s',
                appearance: 'none'
              }}
            >
              <option value="US" style={{ color: '#000' }}>United States</option>
              <option value="CA" style={{ color: '#000' }}>Canada</option>
              <option value="UK" style={{ color: '#000' }}>United Kingdom</option>
              <option value="AU" style={{ color: '#000' }}>Australia</option>
              <option value="OTHER" style={{ color: '#000' }}>Other</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#e4e4e7', marginBottom: '8px' }}>
              Password
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

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <input
              type="checkbox"
              id="terms"
              checked={agreeTerms}
              onChange={(e) => setAgreeTerms(e.target.checked)}
              style={{
                width: '16px',
                height: '16px',
                marginTop: '2px',
                borderRadius: '4px',
                accentColor: '#3b82f6',
                cursor: 'pointer'
              }}
            />
            <label htmlFor="terms" style={{ fontSize: '13px', color: '#a1a1aa', cursor: 'pointer', lineHeight: '1.4' }}>
              I agree to the <a href="#" style={{ color: '#3b82f6', textDecoration: 'none' }}>Terms of Service</a> and <a href="#" style={{ color: '#3b82f6', textDecoration: 'none' }}>Privacy Policy</a>
            </label>
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !agreeTerms || strength < 4 || password !== confirmPassword}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              background: (isSubmitting || !agreeTerms || strength < 4 || password !== confirmPassword) ? 'rgba(59, 130, 246, 0.5)' : '#3b82f6',
              color: '#fff',
              fontSize: '15px',
              fontWeight: '600',
              border: 'none',
              cursor: (isSubmitting || !agreeTerms || strength < 4 || password !== confirmPassword) ? 'not-allowed' : 'pointer',
              opacity: (isSubmitting || !agreeTerms || strength < 4 || password !== confirmPassword) ? 0.7 : 1,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '8px',
              marginTop: '16px',
              transition: 'background 0.2s'
            }}
            onMouseOver={(e) => { if (!isSubmitting) e.target.style.background = '#2563eb' }}
            onMouseOut={(e) => { if (!isSubmitting) e.target.style.background = '#3b82f6' }}
          >
            {isSubmitting ? (
              <i className="ti ti-loader animate-spin" />
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '32px', fontSize: '14px', color: '#a1a1aa' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: '#3b82f6', textDecoration: 'none', fontWeight: '500' }}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
