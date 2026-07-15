import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useNavigate, Link } from '@tanstack/react-router'
import AuthFrame from './AuthFrame'

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

  const { register } = useAuth()
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

  return (
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
            <h2 style={{ margin: '0 0 16px', fontSize: 18, color: '#fff' }}>{showTermsModal ? 'Terms of Service' : 'Privacy Policy'}</h2>
            <p style={{ color: '#a1a1aa', fontSize: 14, lineHeight: 1.6, marginBottom: 24 }}>
              {showTermsModal ? 'Terms of Service — Coming Soon' : 'Privacy Policy — Coming Soon'}
            </p>
            <button onClick={() => { setShowTermsModal(false); setShowPrivacyModal(false) }} style={{ width: '100%', padding: 10, background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
              Close
            </button>
          </div>
        </div>
      ) : null}
    </AuthFrame>
  )
}
