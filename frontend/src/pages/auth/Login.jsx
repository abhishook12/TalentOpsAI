import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { Link, useNavigate, useSearch } from '@tanstack/react-router'
import ApprovalProgress from '../../components/auth/ApprovalProgress'
import { useGoogleLogin } from '@react-oauth/google'
import AuthFrame from './AuthFrame'
import AppLoadingOverlay from '../../components/AppLoadingOverlay'
import api from '../../services/api'

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
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3.5 rounded-xl mb-6 text-sm flex items-start gap-2.5 leading-[1.4]" role="alert">
            <i className="ti ti-alert-circle mt-[2px]" />
            <span>{error}</span>
          </div>
        )}

        <div className="mb-6 text-left">
          <h1 className="text-2xl font-bold text-white m-0 mb-2 tracking-tight">Welcome Back</h1>
          <p className="text-sm text-[#a0a0a0] m-0 leading-relaxed">Login to access your TalentOps account</p>
        </div>

        <div className="w-full flex flex-col gap-4" onKeyDown={(e) => { if (e.key === 'Enter' && isFormValid && !isAuthenticating) handleSubmit(e) }}>
          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] text-[#a0a0a0]" htmlFor="email-input">Email address</label>
            <div className="relative flex items-center group">
              <i className="ti ti-mail absolute left-3.5 text-[#666] text-base pointer-events-none group-focus-within:text-[var(--brand)] transition-colors" />
              <input
                id="email-input"
                className="w-full h-11 rounded-lg border border-[#333] bg-[#111] text-white pl-10 pr-4 text-sm outline-none transition-all placeholder:text-[#555] focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)] aria-[invalid=true]:border-red-500 aria-[invalid=true]:focus:shadow-[0_0_0_4px_rgba(239,68,68,0.1)]"
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
              <div id="email-error" className="text-xs text-red-500 mt-1">Enter a valid email address</div>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] text-[#a0a0a0]" htmlFor="password-input">Password</label>
            <div className="relative flex items-center group">
              <i className="ti ti-lock absolute left-3.5 text-[#666] text-base pointer-events-none group-focus-within:text-[var(--brand)] transition-colors" />
              <input
                id="password-input"
                className="w-full h-11 rounded-lg border border-[#333] bg-[#111] text-white pl-10 pr-10 text-sm outline-none transition-all placeholder:text-[#555] focus:border-[var(--brand)] focus:shadow-[0_0_0_4px_var(--brand-bg)]"
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
                className="absolute right-3.5 bg-transparent border-none text-[#666] cursor-pointer p-1 flex items-center justify-center text-base transition-colors hover:text-white" 
                aria-label="Toggle password visibility"
              >
                <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
              </button>
            </div>
          </div>

          <div className="flex justify-between items-center my-1 mb-4">
            <label className="flex items-center gap-2 text-[13px] text-[#a0a0a0] cursor-pointer">
              <input 
                type="checkbox" 
                className="appearance-none w-4 h-4 cursor-pointer bg-[#111] border border-[#444] rounded flex-shrink-0 relative transition-all checked:bg-[var(--brand)] checked:border-[var(--brand)] focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--brand-bg)] mt-[2px] after:content-[''] after:absolute after:left-[4px] after:top-[1px] after:w-[5px] after:h-[9px] after:border-solid after:border-white after:border-0 after:border-r-2 after:border-b-2 after:rotate-45 after:opacity-0 checked:after:opacity-100"
              />
              Remember me
            </label>
            <Link to="/forgot-password" className="text-[13px] text-[#a0a0a0] no-underline transition-colors hover:text-white">
              Forgot password?
            </Link>
          </div>

          <button type="button" onClick={handleSubmit} className="w-full h-11 border-none rounded-lg bg-[var(--brand)] text-white text-sm font-medium cursor-pointer transition-all flex items-center justify-center hover:not-disabled:bg-[var(--brand-strong)] disabled:opacity-50 disabled:cursor-not-allowed" disabled={!isFormValid || isAuthenticating}>
            {isAuthenticating ? (
              <div className="flex items-center gap-2">
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

          <div className="flex items-center text-center text-[#666] text-[13px] my-4 before:content-[''] before:flex-1 before:border-b before:border-[#333] after:content-[''] after:flex-1 after:border-b after:border-[#333]">
            <span className="px-4">Or continue with</span>
          </div>

          <button type="button" onClick={() => customGoogleLogin()} disabled={isAuthenticating} className="w-full h-12 rounded-xl border border-white/5 dark:border-[#2a2a2a] bg-white/5 dark:bg-[#1e1e1e] text-white text-[15px] font-medium cursor-pointer transition-all flex items-center justify-center gap-3 hover:bg-white/10 dark:hover:bg-white/10">
            <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>
        </div>

        <div className="mt-8 flex flex-col items-center gap-4">
          <div className="flex gap-1.5 text-[13px]">
            <span className="text-[#888]">Don't have an account?</span>
            <Link to="/register" className="text-[var(--brand)] no-underline transition-colors hover:text-[var(--brand-strong)] hover:underline">
              Create an account
            </Link>
          </div>
        </div>
      </AuthFrame>
      )}
    </>
  )
}
