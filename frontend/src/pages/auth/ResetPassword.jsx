import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, useSearch, Link } from '@tanstack/react-router';
import AuthFrame from './AuthFrame';

export default function ResetPassword() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { resetPassword } = useAuth();
  const navigate = useNavigate();
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
    <AuthFrame isAuthenticating={false}>
      <div className="mb-6 text-left">
        <h1 className="text-2xl font-bold text-white m-0 mb-2 tracking-tight">New Password</h1>
        <p className="text-sm text-[#a0a0a0] m-0 leading-relaxed">Create a new secure password for your account</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-sm mb-4 flex items-center gap-2">
          <i className="ti ti-alert-circle text-base" />
          <span>{error}</span>
        </div>
      )}

      {status && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-3 rounded-lg text-sm mb-4 flex items-center gap-2">
          <i className="ti ti-check text-base" />
          <span>{status}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] text-[#a0a0a0]" htmlFor="new-password">New Password</label>
          <div className="relative flex items-center">
            <input
              id="new-password"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Create a strong password"
              className="pr-10"
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

          <div className="mt-2 text-[12px] flex flex-col gap-1 text-[#888]">
            <div style={{ color: password.length >= 8 ? '#22c55e' : '#888' }}>
              <i className={`ti ${password.length >= 8 ? 'ti-check' : 'ti-circle'} mr-1.5`} />
              At least 8 characters
            </div>
            <div style={{ color: /[A-Z]/.test(password) ? '#22c55e' : '#888' }}>
              <i className={`ti ${/[A-Z]/.test(password) ? 'ti-check' : 'ti-circle'} mr-1.5`} />
              At least 1 uppercase letter
            </div>
            <div style={{ color: /[0-9]/.test(password) ? '#22c55e' : '#888' }}>
              <i className={`ti ${/[0-9]/.test(password) ? 'ti-check' : 'ti-circle'} mr-1.5`} />
              At least 1 number
            </div>
            <div style={{ color: /[^A-Za-z0-9]/.test(password) ? '#22c55e' : '#888' }}>
              <i className={`ti ${/[^A-Za-z0-9]/.test(password) ? 'ti-check' : 'ti-circle'} mr-1.5`} />
              At least 1 special character
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] text-[#a0a0a0]" htmlFor="confirm-password">Confirm Password</label>
          <input
            id="confirm-password"
            type={showPassword ? 'text' : 'password'}
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm your password"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting || strength < 4 || password !== confirmPassword}
          className="w-full h-11 border-none rounded-lg bg-white text-zinc-950 text-sm font-semibold cursor-pointer transition-all flex items-center justify-center hover:not-disabled:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm mt-2"
        >
          {isSubmitting ? (
            <div className="flex items-center gap-2 text-zinc-950">
              <i className="ti ti-loader animate-spin" />
              <span>Resetting...</span>
            </div>
          ) : (
            <span>Reset Password</span>
          )}
        </button>
      </form>

      <div className="mt-8 flex flex-col items-center gap-4">
        <div className="flex gap-1.5 text-[13px]">
          <span className="text-[#888]">Back to</span>
          <Link to="/login" className="text-white no-underline transition-colors hover:underline font-medium">
            Sign in
          </Link>
        </div>
      </div>
    </AuthFrame>
  );
}
