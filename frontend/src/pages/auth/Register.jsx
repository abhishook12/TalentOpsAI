import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useNavigate, Link } from '@tanstack/react-router'
import { GoogleLogin } from '@react-oauth/google'
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
  const strengthColors = ['#e41937', '#e41937', '#d4d4d8', '#ffffff', '#ffffff']
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
    <AuthFrame
      eyebrow="Create account"
      title="Sign Up for TalentOps"
      subtitle="Enter your details to get started"
      footerText="Already have an account?"
      footerLink="Sign in"
      footerLinkTo="/login"
    >
      {error ? (
        <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-3 py-3 rounded-lg text-sm flex items-center gap-2 mb-4">
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

      <div className="flex items-center text-center text-[#666] text-[13px] my-4 before:content-[''] before:flex-1 before:border-b before:border-[#333] after:content-[''] after:flex-1 after:border-b after:border-[#333]">
          <span className="px-4">or register with email</span>
      </div>

      <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
        <div className="flex gap-4 w-full">
          <div className="flex flex-col gap-1.5 flex-1">
            <label className="text-[13px] text-[#a0a0a0]">First name</label>
            <input className="w-full h-11 rounded-lg border border-[#333] bg-[var(--bg-surface)] text-white px-4 text-sm outline-none transition-all placeholder:text-[#555] focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)]" type="text" required value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="First name" />
          </div>
          <div className="flex flex-col gap-1.5 flex-1">
            <label className="text-[13px] text-[#a0a0a0]">Last name</label>
            <input className="w-full h-11 rounded-lg border border-[#333] bg-[var(--bg-surface)] text-white px-4 text-sm outline-none transition-all placeholder:text-[#555] focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)]" type="text" required value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Last name" />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] text-[#a0a0a0]">Work Email</label>
          <input className="w-full h-11 rounded-lg border border-[#333] bg-[var(--bg-surface)] text-white px-4 text-sm outline-none transition-all placeholder:text-[#555] focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)]" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] text-[#a0a0a0]">Company (Optional)</label>
          <input className="w-full h-11 rounded-lg border border-[#333] bg-[var(--bg-surface)] text-white px-4 text-sm outline-none transition-all placeholder:text-[#555] focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)]" type="text" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Acme Corp" />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] text-[#a0a0a0]">Country</label>
          <select className="w-full h-11 rounded-lg border border-[#333] bg-[var(--bg-surface)] text-white px-4 text-sm outline-none appearance-none transition-all focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)]" value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="US">United States</option>
            <option value="CA">Canada</option>
            <option value="UK">United Kingdom</option>
            <option value="AU">Australia</option>
            <option value="OTHER">Other</option>
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] text-[#a0a0a0]">Password</label>
          <div className="relative flex items-center">
            <input className="w-full h-11 rounded-lg border border-[#333] bg-[var(--bg-surface)] text-white px-4 text-sm outline-none transition-all placeholder:text-[#555] focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)]" type={showPassword ? 'text' : 'password'} required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a strong password" />
            <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3.5 bg-transparent border-none text-[#666] cursor-pointer p-1 flex items-center justify-center text-base transition-colors hover:text-white" aria-label="Toggle password visibility">
              <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
            </button>
          </div>

          {password.length > 0 ? (
            <div className="mt-2 text-[13px]">
              Strength: <strong style={{ color: strengthColors[strength] }}>{strengthLabels[strength]}</strong>
            </div>
          ) : null}

          <div className="grid gap-1 mt-1 text-[13px]">
            <div style={{ color: password.length >= 8 ? '#ffffff' : 'rgba(255,255,255,0.46)' }}>
              <i className={`ti ${password.length >= 8 ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: 6 }} />
              At least 8 characters
            </div>
            <div style={{ color: /[A-Z]/.test(password) ? '#ffffff' : 'rgba(255,255,255,0.46)' }}>
              <i className={`ti ${/[A-Z]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: 6 }} />
              At least 1 uppercase letter
            </div>
            <div style={{ color: /[0-9]/.test(password) ? '#ffffff' : 'rgba(255,255,255,0.46)' }}>
              <i className={`ti ${/[0-9]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: 6 }} />
              At least 1 number
            </div>
            <div style={{ color: /[^A-Za-z0-9]/.test(password) ? '#ffffff' : 'rgba(255,255,255,0.46)' }}>
              <i className={`ti ${/[^A-Za-z0-9]/.test(password) ? 'ti-check' : 'ti-circle'}`} style={{ marginRight: 6 }} />
              At least 1 special character
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] text-[#a0a0a0]">Confirm Password</label>
          <input className="w-full h-11 rounded-lg border border-[#333] bg-[var(--bg-surface)] text-white px-4 text-sm outline-none transition-all placeholder:text-[#555] focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)]" type={showPassword ? 'text' : 'password'} required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm your password" />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="flex items-start gap-2 text-[13px] text-[#a1a1aa] cursor-pointer">
            <input
              className="w-4 h-4 cursor-pointer rounded flex-shrink-0 mt-[2px]"
              type="checkbox"
              checked={agreeTerms}
              onChange={(e) => setAgreeTerms(e.target.checked)}
            />
            <span>
              I agree to the{' '}
              <button type="button" onClick={(e) => { e.preventDefault(); setShowTermsModal(true) }} className="text-[var(--brand)] underline underline-offset-2 font-medium cursor-pointer bg-transparent border-none p-0 hover:text-[var(--brand-strong)]">
                Terms of Service
              </button>{' '}
              and{' '}
              <button type="button" onClick={(e) => { e.preventDefault(); setShowPrivacyModal(true) }} className="text-[var(--brand)] underline underline-offset-2 font-medium cursor-pointer bg-transparent border-none p-0 hover:text-[var(--brand-strong)]">
                Privacy Policy
              </button>
            </span>
          </label>
        </div>

        <button type="submit" disabled={isSubmitting || !agreeTerms || strength < 4 || password !== confirmPassword} className="w-full h-11 border-none rounded-lg bg-[var(--brand)] text-[var(--text-inverse)] text-sm font-semibold cursor-pointer transition-all flex items-center justify-center gap-2 mt-4 hover:not-disabled:bg-[var(--brand-strong)] disabled:opacity-50 disabled:cursor-not-allowed">
          {isSubmitting ? (
            <>
              <i className="ti ti-loader animate-spin" /> Creating account...
            </>
          ) : (
            'Create Account'
          )}
        </button>
      </form>

      <div className="text-center mt-6 text-[13px] text-[#a0a0a0]">
        Need a quick login instead? <Link to="/login" className="text-[var(--brand)] no-underline font-medium hover:underline">Sign in</Link>
      </div>

      {(showTermsModal || showPrivacyModal) ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="register-legal-modal-title"
          onClick={(e) => { if (e.target === e.currentTarget) { setShowTermsModal(false); setShowPrivacyModal(false) } }}
          onKeyDown={(e) => { if (e.key === 'Escape') { setShowTermsModal(false); setShowPrivacyModal(false) } }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', display: 'grid', placeItems: 'center', zIndex: 1000, backdropFilter: 'blur(2px)', padding: 20 }}
        >
          <div style={{ width: 'min(440px, 100%)', background: '#18181b', padding: 24, borderRadius: 8, border: '1px solid #343b35' }}>
            <h2 id="register-legal-modal-title" style={{ margin: '0 0 12px', fontSize: 18, color: 'var(--text-primary)' }}>
              {showTermsModal ? 'Terms of Service' : 'Privacy Policy'}
            </h2>
            <p style={{ color: '#b0b7ae', fontSize: 14, lineHeight: 1.6, marginBottom: 20 }}>
              {showTermsModal
                ? 'TalentOps is provided for authorized enterprise recruiting intelligence and talent pipeline management. Users agree to protect candidate data, comply with applicable outreach regulations, and keep credentials confidential.'
                : 'TalentOps processes recruiter and workspace account data solely to power platform authentication, enrichment workflows, and audit logging. Session tokens are encrypted in transit and never shared with unauthorized third parties.'}
            </p>
            <button
              type="button"
              autoFocus
              onClick={() => { setShowTermsModal(false); setShowPrivacyModal(false) }}
              style={{ width: '100%', minHeight: 44, padding: 10, background: '#e4e4e7', color: '#101211', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </AuthFrame>
    </>
  )
}

