import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { Link, useNavigate, useSearch } from '@tanstack/react-router'
import ApprovalProgress from '../../components/auth/ApprovalProgress'
import { useGoogleLogin } from '@react-oauth/google'
import AuthFrame from './AuthFrame'
import AppLoadingOverlay from '../../components/AppLoadingOverlay'
import api from '../../services/api'

const formStyles = `
  .login-form {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .login-title-wrapper {
    margin-bottom: 24px;
    text-align: left;
  }
  
  .login-title {
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 8px 0;
    letter-spacing: -0.01em;
  }

  .login-subtitle {
    font-size: 14px;
    color: #a0a0a0;
    margin: 0;
    line-height: 1.5;
  }

  .login-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .login-label {
    font-size: 13px;
    color: #a0a0a0;
  }

  .login-input-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }

  .login-icon-left {
    position: absolute;
    left: 14px;
    color: #666;
    font-size: 16px;
    pointer-events: none;
  }

  .login-input {
    width: 100%;
    height: 44px;
    border-radius: 8px;
    border: 1px solid #333;
    background: #111;
    color: #ffffff;
    padding: 0 16px 0 40px;
    font-size: 14px;
    outline: none;
    transition: all 0.2s ease;
  }

  .login-input::placeholder {
    color: #555;
  }

  .login-input:focus {
    border-color: #8b5cf6;
    box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.1);
  }
  
  .login-input[aria-invalid="true"] {
    border-color: #ef4444;
  }
  .login-input[aria-invalid="true"]:focus {
    box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.1);
  }

  .login-input-wrap:focus-within .login-icon-left {
    color: #8b5cf6;
  }
  
  .login-validation-msg {
    font-size: 12px;
    color: #ef4444;
    margin-top: 4px;
  }

  .login-eye-button {
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

  .login-eye-button:hover {
    color: #fff;
  }

  .login-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 4px 0 16px 0;
  }

  .login-remember {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #a0a0a0;
    cursor: pointer;
  }

  .login-checkbox {
    appearance: none;
    width: 16px;
    height: 16px;
    cursor: pointer;
    background: #111;
    border: 1px solid #444;
    border-radius: 4px;
    position: relative;
    transition: all 0.2s;
  }
  
  .login-checkbox:checked {
    background: #8b5cf6;
    border-color: #8b5cf6;
  }
  
  .login-checkbox:checked::after {
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
  
  .login-checkbox:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.3);
  }

  .login-forgot {
    font-size: 13px;
    color: #a0a0a0;
    text-decoration: none;
    transition: color 0.2s;
  }
  
  .login-forgot:hover {
    color: #fff;
  }

  .login-button-primary {
    width: 100%;
    height: 44px;
    border: none;
    border-radius: 8px;
    background: #8b5cf6;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .login-button-primary:hover:not(:disabled) {
    background: #a855f7;
  }

  .login-button-primary:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .login-divider {
    display: flex;
    align-items: center;
    text-align: center;
    color: #666;
    font-size: 13px;
    margin: 16px 0;
  }
  
  .login-divider::before,
  .login-divider::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid #333;
  }
  
  .login-divider span {
    padding: 0 16px;
  }

  .login-button-google {
    width: 100%;
    height: 48px;
    border-radius: 12px;
    border: 1px solid var(--border, #e0e0e0);
    background: transparent;
    color: var(--text-primary, #111);
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
  }

  [data-theme="dark"] .login-button-google {
    border-color: #2a2a2a;
    background: #1e1e1e;
    color: #ffffff;
  }

  .login-button-google:hover {
    background: rgba(0, 0, 0, 0.02);
  }

  [data-theme="dark"] .login-button-google:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .login-footer-links {
    margin-top: 32px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .login-link {
    font-size: 13px;
    color: var(--text-secondary, #666666);
    text-decoration: none;
    transition: color 0.2s ease;
  }

  [data-theme="dark"] .login-link {
    color: #a0a0a0;
  }

  .login-link:hover {
    color: var(--text-primary, #111);
    text-decoration: underline;
  }

  [data-theme="dark"] .login-link:hover {
    color: #ffffff;
  }
  
  .login-create-account {
    color: #8b5cf6 !important;
  }
  .login-create-account:hover {
    color: #a855f7 !important;
  }

  .login-error-banner {
    padding: 14px 16px;
    border-radius: 12px;
    margin-bottom: 24px;
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.2);
    color: #ef4444;
    font-size: 14px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    line-height: 1.4;
  }

  [data-theme="dark"] .login-error-banner {
    color: #fca5a5;
  }
`

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [emailTouched, setEmailTouched] = useState(false)
  
  // Splash Screen State
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [authProgress, setAuthProgress] = useState(null)
  const [pendingDeviceId, setPendingDeviceId] = useState(null)
  
  const { login, googleLogin, checkAuthStatus } = useAuth()
  const navigate = useNavigate()
  const search = useSearch({ from: '/login' })
  const redirect = decodeURIComponent(search.redirect || '/')

  const isEmailValid = email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)
  const isFormValid = isEmailValid && password.length >= 4

  const performBackgroundInitialization = async (authFunction) => {
    setError('')
    setIsAuthenticating(true)
    setAuthProgress(null) // Indeterminate start
    
    try {
      const data = await authFunction()
      
      if (data && data.status === 'pending_approval') {
        setIsAuthenticating(false)
        setPendingDeviceId(data.device_id)
        return
      }
      
      setAuthProgress(100)
      
      // Brief animation for premium UX before instant navigation
      await new Promise(res => setTimeout(res, 300))
      
      navigate({ to: redirect })
      
    } catch (err) {
      let errorDetail = err?.response?.data?.detail || err?.message || 'Authentication failed. Please check your credentials.'
      if (Array.isArray(errorDetail)) {
          errorDetail = errorDetail.map(e => e.msg).join(', ')
      } else if (typeof errorDetail === 'object') {
          errorDetail = JSON.stringify(errorDetail)
      }
      
      setError(errorDetail)
      setIsAuthenticating(false)
      setPendingDeviceId(null)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    performBackgroundInitialization(() => login(email, password, true))
  }

  const customGoogleLogin = useGoogleLogin({
    onSuccess: (credentialResponse) => {
      // The useGoogleLogin hook returns an access_token directly, not an ID credential like the component
      // We pass it to our backend just the same (the backend needs to support it or we use the implicit flow)
      // Actually, standard googleLogin in this app uses the id_token from OneTap.
      // We can request the standard oauth flow here.
      performBackgroundInitialization(() => googleLogin(credentialResponse.access_token))
    },
    onError: () => setError('Google Sign-In was unsuccessful. Try again later.'),
  })

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: formStyles }} />
      
      <AppLoadingOverlay isVisible={isAuthenticating} progress={authProgress} />
      
      {pendingDeviceId ? (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '100%', zIndex: 10 }}>
          <ApprovalProgress 
            deviceId={pendingDeviceId} 
            onApproved={() => performBackgroundInitialization(async () => {
              const res = await api.post('/auth/complete-device-approval', null)
              // Populate the auth context before navigating to the dashboard
              await checkAuthStatus(true)
              return res
            })}
          />
        </div>
      ) : (
      <AuthFrame isAuthenticating={isAuthenticating}>
        
        {error && (
          <div className="login-error-banner" role="alert">
            <i className="ti ti-alert-circle" style={{ marginTop: '2px' }} />
            <span>{error}</span>
          </div>
        )}

        <div className="login-title-wrapper">
          <h1 className="login-title">Welcome Back</h1>
          <p className="login-subtitle">Login to access your TalentOps account</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label className="login-label" htmlFor="email-input">Email address</label>
            <div className="login-input-wrap">
              <i className="ti ti-mail login-icon-left" />
              <input
                id="email-input"
                className="login-input"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setEmailTouched(true)}
                placeholder="you@company.com"
                aria-invalid={emailTouched && !isEmailValid ? "true" : "false"}
                aria-describedby={emailTouched && !isEmailValid ? "email-error" : undefined}
              />
            </div>
            {emailTouched && !isEmailValid && (
              <div id="email-error" className="login-validation-msg">Enter a valid email address</div>
            )}
          </div>

          <div className="login-field">
            <label className="login-label" htmlFor="password-input">Password</label>
            <div className="login-input-wrap">
              <i className="ti ti-lock login-icon-left" />
              <input
                id="password-input"
                className="login-input"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
              />
              <button 
                type="button" 
                onClick={() => setShowPassword(!showPassword)} 
                className="login-eye-button" 
                aria-label="Toggle password visibility"
              >
                <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
              </button>
            </div>
          </div>

          <div className="login-actions">
            <label className="login-remember">
              <input type="checkbox" className="login-checkbox" />
              Remember me
            </label>
            <Link to="/forgot-password" className="login-forgot">
              Forgot password?
            </Link>
          </div>

          <button type="submit" className="login-button-primary" disabled={!isFormValid || isAuthenticating}>
            {isAuthenticating ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <i className="ti ti-loader animate-spin" />
                <span>Signing in...</span>
              </div>
            ) : (
              <span>Login to TalentOps</span>
            )}
          </button>
          
          {import.meta.env.DEV && (
          <button type="button" id="atlas-simulate-google" style={{ display: 'none' }} onClick={() => performBackgroundInitialization(() => googleLogin('mock_google_token_atlas_user_' + Date.now()))}>
            ATLAS Mock Google
          </button>
          )}

          <div className="login-divider">
            <span>Or continue with</span>
          </div>

          <button type="button" onClick={() => customGoogleLogin()} disabled={isAuthenticating} className="login-button-google">
            <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>
        </form>

        <div className="login-footer-links" style={{ display: 'flex', gap: 6, justifyContent: 'center', marginTop: 24, fontSize: 13 }}>
          <span style={{ color: '#888' }}>Don't have an account?</span>
          <Link to="/register" className="login-link login-create-account">
            Create an account
          </Link>
        </div>
      </AuthFrame>
      )}
    </>
  )
}
