import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useNavigate, Link, useSearch } from '@tanstack/react-router'
import { GoogleLogin } from '@react-oauth/google'
import AuthFrame from './AuthFrame'

export default function Login() {
  const [capsLockActive, setCapsLockActive] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { login, googleLogin } = useAuth()
  const navigate = useNavigate()
  const search = useSearch({ from: '/login' })
  const redirect = search.redirect || '/'

  const isEmailValid = email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)
  const isFormValid = isEmailValid && password.length >= 4

  const handleKeyUp = (e) => {
    setCapsLockActive(Boolean(e.getModifierState?.('CapsLock')))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await login(email, password, rememberMe)
      navigate({ to: redirect })
    } catch (err) {
      let errorDetail = err?.response?.data?.detail || 'Invalid email or password'
      if (Array.isArray(errorDetail)) {
          errorDetail = errorDetail.map(e => e.msg).join(', ')
      } else if (typeof errorDetail === 'object') {
          errorDetail = JSON.stringify(errorDetail)
      }
      setError(errorDetail)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('')
    setIsSubmitting(true)
    try {
        await googleLogin(credentialResponse.credential)
        navigate({ to: redirect })
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
    <AuthFrame
      eyebrow="Welcome back"
      title="Sign In to TalentOps"
      subtitle="Enter your credentials to access your account"
      footerText="Don't have an account?"
      footerLink="Sign up"
      footerLinkTo="/register"
    >
      {error ? (
        <div className="auth-error">
          <i className="ti ti-alert-circle" />
          {error}
        </div>
      ) : null}



      <form onSubmit={handleSubmit} className="auth-form">
        <div className="auth-field">
          <label className="auth-label">Email Address</label>
          <input
            className="auth-input"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
          />
        </div>

        <div className="auth-field">
          <div className="auth-inline">
            <label className="auth-label">Password</label>
            <Link to="/forgot-password" className="auth-mini-link">
              Forgot password?
            </Link>
          </div>

          <div className="auth-password-wrap">
            <input
              className="auth-input"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyUp={handleKeyUp}
              placeholder="Enter your password"
            />
            <button type="button" onClick={() => setShowPassword(!showPassword)} className="auth-eye-button" aria-label="Toggle password visibility">
              <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
            </button>
          </div>

          {capsLockActive ? (
            <div className="auth-alert">
              <i className="ti ti-alert-triangle" /> Caps Lock is on
            </div>
          ) : null}

          {password && password.length < 8 ? (
            <div className="auth-copy-note">Password must be at least 8 characters</div>
          ) : null}
        </div>

        <div className="auth-inline">
          <label className="auth-remember">
            <input
              className="auth-check"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            Remember me
          </label>
          <span className="auth-copy-note" style={{ marginTop: 0 }}>
            &nbsp;
          </span>
        </div>

        <button type="submit" disabled={isSubmitting || !isFormValid} className="auth-button">
          {isSubmitting ? (
            <>
              <i className="ti ti-loader animate-spin" /> Signing in...
            </>
          ) : (
            'Sign In'
          )}
        </button>
      </form>

      <div className="auth-divider">
        <span>OR CONTINUE WITH</span>
      </div>

      <div className="auth-socials">
        <div className="auth-social-badge">Coming Soon</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 0, overflow: 'hidden', borderRadius: '8px' }}>
          <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              useOneTap
              theme={document.documentElement.getAttribute('data-theme') === 'dark' ? 'filled_black' : 'outline'}
              size="large"
              shape="rectangular"
              text="signin_with"
              width="200"
          />
        </div>
        <button type="button" className="auth-social" disabled>
          <i className="ti ti-brand-windows" /> Microsoft
        </button>
      </div>
    </AuthFrame>
  )
}

