import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Link } from '@tanstack/react-router';
import AuthFrame from './AuthFrame';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { forgotPassword } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setStatus('');
    setIsSubmitting(true);
    
    try {
      await forgotPassword(email);
      setStatus('Password reset link sent! Check your email.');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to send reset link.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthFrame isAuthenticating={false}>
      <div className="mb-6 text-left">
        <h1 className="text-2xl font-bold text-white m-0 mb-2 tracking-tight">Reset Password</h1>
        <p className="text-sm text-[#a0a0a0] m-0 leading-relaxed">Enter your email to receive a password reset link</p>
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
          <label className="text-[13px] text-[#a0a0a0]" htmlFor="email-input">Email address</label>
          <div className="relative flex items-center group">
            <i className="ti ti-mail absolute left-3.5 text-[#666] text-base pointer-events-none group-focus-within:text-white transition-colors" />
            <input
              id="email-input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="pl-10"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || !email}
          className="w-full h-11 border-none rounded-lg bg-white text-zinc-950 text-sm font-semibold cursor-pointer transition-all flex items-center justify-center hover:not-disabled:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm mt-2"
        >
          {isSubmitting ? (
            <div className="flex items-center gap-2 text-zinc-950">
              <i className="ti ti-loader animate-spin" />
              <span>Sending link...</span>
            </div>
          ) : (
            <span>Send Reset Link</span>
          )}
        </button>
      </form>

      <div className="mt-8 flex flex-col items-center gap-4">
        <div className="flex gap-1.5 text-[13px]">
          <span className="text-[#888]">Remember your password?</span>
          <Link to="/login" className="text-white no-underline transition-colors hover:underline font-medium">
            Sign in
          </Link>
        </div>
      </div>
    </AuthFrame>
  );
}
