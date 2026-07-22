import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useNavigate, Link, useSearch } from '@tanstack/react-router'
import { GoogleLogin } from '@react-oauth/google'
import AuthFrame from './AuthFrame'
import FullScreenLoader from '../../components/FullScreenLoader'
import api from '../../services/api'
export default function Login() {
  const [capsLockActive, setCapsLockActive] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDeviceBlocked, setIsDeviceBlocked] = useState(false)
  const [deviceStatus, setDeviceStatus] = useState('Pending Approval')
  const [refreshingStatus, setRefreshingStatus] = useState(false)

  const { login, googleLogin } = useAuth()
  const navigate = useNavigate()
  const search = useSearch({ from: '/login' })
  const redirect = decodeURIComponent(search.redirect || '/')

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
      if (!err.response) {
        setError('Cannot connect to the server. Is the backend running?')
      } else {
        let errorDetail = err?.response?.data?.detail || 'Invalid email or password'
        if (Array.isArray(errorDetail)) {
            errorDetail = errorDetail.map(e => e.msg).join(', ')
        } else if (typeof errorDetail === 'object') {
            errorDetail = JSON.stringify(errorDetail)
        }
        if (errorDetail.includes('Access Restricted')) {
          setIsDeviceBlocked(true)
        } else {
          setError(errorDetail)
        }
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const [googleAuthLoading, setGoogleAuthLoading] = useState(false)
  const [googleAuthError, setGoogleAuthError] = useState('')
  const [isSlowNetwork, setIsSlowNetwork] = useState(false)

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('')
    setGoogleAuthError('')
    setGoogleAuthLoading(true)
    setIsSlowNetwork(false)
    
    // Slow network timer (3.5s)
    const slowNetworkTimer = setTimeout(() => {
      setIsSlowNetwork(true)
    }, 3500)

    try {
        await googleLogin(credentialResponse.credential)
        
        // Perform initialization background tasks
        await Promise.all([
          api.get('/auth/me'),
          api.get('/bridge/status'),
          api.get('/admin/dashboard/metrics').catch(() => null),
          new Promise(res => setTimeout(res, 1500)) // smooth UX minimum time
        ])

        clearTimeout(slowNetworkTimer)
        navigate({ to: redirect })
    } catch (err) {
        clearTimeout(slowNetworkTimer)
        let errorDetail = err?.response?.data?.detail || 'Network connection lost or Google Sign-In failed.'
        if (typeof errorDetail === 'string' && errorDetail.includes('Access Restricted')) {
          setIsDeviceBlocked(true)
          setGoogleAuthLoading(false)
        } else {
          setGoogleAuthError(errorDetail)
        }
    }
    // We don't setGoogleAuthLoading(false) on success because navigation will unmount us.
    // We only clear it if there's an error so they can see the error state in the loader.
  }

  const handleGoogleRetry = () => {
    setGoogleAuthError('')
    setGoogleAuthLoading(false)
  }

  const handleGoogleError = () => {
    setError('Google Sign-In was unsuccessful. Try again later.')
  }

  if (googleAuthLoading) {
    return (
      <FullScreenLoader 
        error={googleAuthError} 
        onRetry={handleGoogleRetry} 
        isSlowNetwork={isSlowNetwork} 
      />
    )
  }

  const handleRefreshStatus = async () => {
    setRefreshingStatus(true)
    try {
      const res = await api.get('/auth/device-status')
      if (res.data.status === 'Trusted') {
        // If it's now trusted, they can try logging in again
        setIsDeviceBlocked(false)
        if (email && password) {
          handleSubmit({ preventDefault: () => {} })
        }
      } else if (res.data.status === 'Blocked') {
        setDeviceStatus('Permanently Blocked')
      }
    } catch (e) {
      console.error(e)
    } finally {
      setRefreshingStatus(false)
    }
  }

  const handleSignOut = () => {
    setIsDeviceBlocked(false)
    setEmail('')
    setPassword('')
  }

  if (isDeviceBlocked) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-secondary)', padding: '20px' }}>
        <div style={{ background: 'var(--bg-primary)', padding: '40px', borderRadius: '12px', boxShadow: 'var(--shadow-lg)', maxWidth: '480px', width: '100%', textAlign: 'center', border: '1px solid var(--border)' }}>
          <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'var(--warning-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px' }}>
            <i className="ti ti-shield-lock" style={{ fontSize: '32px', color: 'var(--warning)' }}></i>
          </div>
          <h1 style={{ fontSize: '24px', fontWeight: '600', color: 'var(--text-primary)', margin: '0 0 16px' }}>Device Approval Required</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '15px', lineHeight: '1.6', margin: '0 0 16px' }}>
            Your account was successfully authenticated.
          </p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '15px', lineHeight: '1.6', margin: '0 0 16px' }}>
            However, this device has not yet been approved by your organization's administrator.
          </p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '15px', lineHeight: '1.6', margin: '0 0 24px' }}>
            Your access request has been submitted. Please wait until your device is approved.
          </p>
          
          <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', marginBottom: '32px', border: '1px solid var(--border)' }}>
            <span style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-tertiary)', display: 'block', marginBottom: '4px' }}>Status</span>
            <span style={{ fontSize: '16px', fontWeight: '600', color: deviceStatus === 'Permanently Blocked' ? 'var(--danger)' : 'var(--warning)' }}>
              {deviceStatus}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '16px', flexDirection: 'column' }}>
            <button 
              onClick={handleRefreshStatus} 
              disabled={refreshingStatus}
              className="auth-button"
              style={{ width: '100%' }}
            >
              {refreshingStatus ? <><i className="ti ti-loader animate-spin" /> Checking...</> : 'Refresh Status'}
            </button>
            <button 
              onClick={handleSignOut}
              style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)', padding: '12px', borderRadius: '8px', fontWeight: '500', cursor: 'pointer', transition: 'all 0.2s' }}
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    )
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

