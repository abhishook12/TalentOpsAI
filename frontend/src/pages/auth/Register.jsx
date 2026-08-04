import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useNavigate, Link } from '@tanstack/react-router'
import { GoogleLogin } from '@react-oauth/google'
import AuthFrame from './AuthFrame'

const formStyles = `
  .auth-form {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .auth-row {
    display: flex;
    gap: 16px;
    width: 100%;
  }

  .auth-row .auth-field {
    flex: 1;
  }

  .auth-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .auth-label {
    font-size: 13px;
    color: #a0a0a0;
  }

  .auth-password-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }

  .auth-input {
    width: 100%;
    height: 44px;
    border-radius: 8px;
    border: 1px solid #333;
    background: #111;
    color: #ffffff;
    padding: 0 16px;
    font-size: 14px;
    outline: none;
    transition: all 0.2s ease;
  }

  .auth-input::placeholder {
    color: #555;
  }

  .auth-input:focus {
    border-color: var(--brand);
    box-shadow: 0 0 0 4px var(--brand-bg);
  }

  .auth-select {
    width: 100%;
    height: 44px;
    border-radius: 8px;
    border: 1px solid #333;
    background: #111;
    color: #ffffff;
    padding: 0 16px;
    font-size: 14px;
    outline: none;
    appearance: none;
    transition: all 0.2s ease;
  }

  .auth-select:focus {
    border-color: var(--brand);
    box-shadow: 0 0 0 4px var(--brand-bg);
  }

  .auth-eye-button {
    position: absolute;
    right: 14px;
    background: transparent;
    border: none;
    color: #666;
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    transition: color 0.2s;
  }

  .auth-eye-button:hover {
    color: #fff;
  }

  .auth-remember {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 13px;
    color: #a0a0a0;
    cursor: pointer;
  }

  .auth-check {
    appearance: none;
    width: 16px;
    height: 16px;
    cursor: pointer;
    background: #111;
    border: 1px solid #444;
    border-radius: 4px;
    position: relative;
    transition: all 0.2s;
    flex-shrink: 0;
  }
  
  .auth-check:checked {
    background: var(--brand);
    border-color: var(--brand);
  }
  
  .auth-check:checked::after {
    content: '';
    position: absolute;
    left: 4px;
    top: 2px;
    width: 4px;
    height: 8px;
    border: solid white;
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }
  
  .auth-check:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px var(--brand-bg);
  }

  .auth-button {
    width: 100%;
    height: 44px;
    border: none;
    border-radius: 8px;
    background: var(--brand);
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 16px;
  }

  .auth-button:hover:not(:disabled) {
    background: var(--brand-strong);
  }

  .auth-button:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .auth-divider {
    display: flex;
    align-items: center;
    text-align: center;
    color: #666;
    font-size: 13px;
    margin: 16px 0;
  }
  
  .auth-divider::before,
  .auth-divider::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid #333;
  }
  
  .auth-divider span {
    padding: 0 16px;
  }

  .auth-mini-link {
    color: var(--brand);
    text-decoration: underline;
    text-underline-offset: 2px;
    font-weight: 500;
    cursor: pointer;
  }
  
  .auth-mini-link:hover {
    color: var(--brand-strong);
  }

  .auth-footer-link {
    color: var(--brand);
    text-decoration: none;
    font-weight: 500;
  }

  .auth-footer-link:hover {
    text-decoration: underline;
  }
  
  .auth-error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    color: #ef4444;
    padding: 12px;
    border-radius: 8px;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
  }
`

export default function Register() {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [country, setCountry] = useState('US')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [agreeTerms, setAgreeTerms] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showTermsModal, setShowTermsModal] = useState(false)
  const [showPrivacyModal, setShowPrivacyModal] = useState(false)

  const { register, googleLogin } = useAuth()
  const navigate = useNavigate()

  const getPasswordStrength = () => {
    let score = 0
    if (password.length >= 8) score++
    if (/[A-Z]/.test(password)) score++
    if (/[0-9]/.test(password)) score++
    if (/[^A-Za-z0-9]/.test(password)) score++
    return score
  }

  const strength = getPasswordStrength()
  const strengthColors = ['#ef4444', '#ef4444', '#f59e0b', '#22c55e', '#22c55e']
  const strengthLabels = ['Weak', 'Weak', 'Fair', 'Good', 'Strong']

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    if (strength < 4) {
      setError('Please meet all password requirements.')
      setIsSubmitting(false)
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      setIsSubmitting(false)
      return
    }

    if (!agreeTerms) {
      setError('You must agree to the Terms of Service and Privacy Policy.')
      setIsSubmitting(false)
      return
    }

    try {
      await register({
        first_name: firstName,
        last_name: lastName,
        email,
        company,
        password,
      })
      navigate({ to: '/login' })
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to register account')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('')
    setIsSubmitting(true)
    try {
        await googleLogin(credentialResponse.credential)
        navigate({ to: '/' })
    } catch (err) {
        let errorDetail = err?.response?.data?.detail || 'Google Login failed'
        setError(errorDetail)
    } finally {
        setIsSubmitting(false)
    }
  }

  const handleGoogleError = () => {
    setError('Google Sign-In was unsuccessful. Try again later.')
  }

  return (
    <>
    <style dangerouslySetInnerHTML={{ __html: formStyles }} />
    <AuthFrame
      eyebrow="Create account"
      title="Sign Up for TalentOps"
      subtitle="Enter your details to get started"
      footerText="Already have an account?"
      footerLink="Sign in"
      footerLinkTo="/login"
    >
      {error ? (
        <div className="auth-error">
          <i className="ti ti-alert-circle" />
          {error}
        </div>
      ) : null}

      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'center' }}>
          <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              useOneTap
              theme="outline"
              size="large"
              shape="rectangular"
              width="320"
          />
      </div>

      <div className="auth-divider">
          <span>or register with email</span>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="auth-row">
          <div className="auth-field">
            <label className="auth-label">First name</label>
            <input className="auth-input" type="text" required value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="First name" />
          </div>
          <div className="auth-field">
            <label className="auth-label">Last name</label>
            <input className="auth-input" type="text" required value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Last name" />
          </div>
        </div>

        <div className="auth-field">
          <label className="auth-label">Work Email</label>
          <input className="auth-input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" />
        </div>

        <div className="auth-field">
          <label className="auth-label">Company (Optional)</label>
          <input className="auth-input" type="text" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Acme Corp" />
        </div>

        <div className="auth-field">
          <label className="auth-label">Country</label>
          <select className="auth-select" value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="US">United States</option>
            <option value="CA">Canada</option>
            <option value="UK">United Kingdom</option>
            <option value="AU">Australia</option>
            <option value="OTHER">Other</option>
          </select>
        </div>

        <div className="auth-field">
          <label className="auth-label">Password</label>
          <div className="auth-password-wrap">
            <input className="auth-input" type={showPassword ? 'text' : 'password'} required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a strong password" />
            <button type="button" onClick={() => setShowPassword(!showPassword)} className="auth-eye-button" aria-label="Toggle password visibility">
              <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
            </button>
          </div>

          {password.length > 0 ? (
            <div className="auth-copy-note" style={{ marginTop: 10 }}>
              Strength: <strong style={{ color: strengthColors[strength] }}>{strengthLabels[strength]}</strong>
            </div>
          ) : null}

          <div className="auth-copy-note" style={{ display: 'grid', gap: 4 }}>
            <div style={{ color: password.length >= 8 ? '#67e8a8' : 'rgba(255,255,255,0.46)' }}>
              <i className={`ti ${password.length >= 8 ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: 6 }} />
              At least 8 characters
            </div>
            <div style={{ color: /[A-Z]/.test(password) ? '#67e8a8' : 'rgba(255,255,255,0.46)' }}>
              <i className={`ti ${/[A-Z]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: 6 }} />
              At least 1 uppercase letter
            </div>
            <div style={{ color: /[0-9]/.test(password) ? '#67e8a8' : 'rgba(255,255,255,0.46)' }}>
              <i className={`ti ${/[0-9]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: 6 }} />
              At least 1 number
            </div>
            <div style={{ color: /[^A-Za-z0-9]/.test(password) ? '#67e8a8' : 'rgba(255,255,255,0.46)' }}>
              <i className={`ti ${/[^A-Za-z0-9]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: 6 }} />
              At least 1 special character
            </div>
          </div>
        </div>

        <div className="auth-field">
          <label className="auth-label">Confirm Password</label>
          <input className="auth-input" type={showPassword ? 'text' : 'password'} required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm your password" />
        </div>

        <div className="auth-field">
          <label className="auth-remember" style={{ alignItems: 'flex-start' }}>
            <input
              className="auth-check"
              type="checkbox"
              checked={agreeTerms}
              onChange={(e) => setAgreeTerms(e.target.checked)}
              style={{ marginTop: 2 }}
            />
            <span>
              I agree to the{' '}
              <button type="button" onClick={(e) => { e.preventDefault(); setShowTermsModal(true) }} className="auth-mini-link" style={{ background: 'none', border: 'none', padding: 0 }}>
                Terms of Service
              </button>{' '}
              and{' '}
              <button type="button" onClick={(e) => { e.preventDefault(); setShowPrivacyModal(true) }} className="auth-mini-link" style={{ background: 'none', border: 'none', padding: 0 }}>
                Privacy Policy
              </button>
            </span>
          </label>
        </div>

        <button type="submit" disabled={isSubmitting || !agreeTerms || strength < 4 || password !== confirmPassword} className="auth-button">
          {isSubmitting ? (
            <>
              <i className="ti ti-loader animate-spin" /> Creating account...
            </>
          ) : (
            'Create Account'
          )}
        </button>
      </form>

      <div className="auth-copy-note" style={{ textAlign: 'center', marginTop: 22 }}>
        Need a quick login instead? <Link to="/login" className="auth-footer-link">Sign in</Link>
      </div>

      {(showTermsModal || showPrivacyModal) ? (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 1000, backdropFilter: 'blur(2px)', padding: 20 }}>
          <div style={{ width: 'min(420px, 100%)', background: '#18181b', padding: 24, borderRadius: 14, border: '1px solid #27272a' }}>
            <h2 style={{ margin: '0 0 16px', fontSize: 18, color: 'var(--text-primary)' }}>{showTermsModal ? 'Terms of Service' : 'Privacy Policy'}</h2>
            <p style={{ color: '#a1a1aa', fontSize: 14, lineHeight: 1.6, marginBottom: 24 }}>
              {showTermsModal ? 'Terms of Service — Coming Soon' : 'Privacy Policy — Coming Soon'}
            </p>
            <button onClick={() => { setShowTermsModal(false); setShowPrivacyModal(false) }} style={{ width: '100%', padding: 10, background: '#3b82f6', color: '#ffffff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
              Close
            </button>
          </div>
        </div>
      ) : null}
    </AuthFrame>
    </>
  )
}

