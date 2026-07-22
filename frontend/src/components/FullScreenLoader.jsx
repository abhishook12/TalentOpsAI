import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';

const MESSAGES = [
  "Signing you in...",
  "Verifying your account...",
  "Loading your workspace...",
  "Connecting your profile...",
  "Checking Outlook Bridge...",
  "Preparing your dashboard...",
  "Almost ready..."
];

export default function FullScreenLoader({ error, onRetry, isSlowNetwork }) {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    if (error) return;
    const interval = setInterval(() => {
      setMessageIndex((prev) => Math.min(prev + 1, MESSAGES.length - 1));
    }, 1200);
    return () => clearInterval(interval);
  }, [error]);

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'var(--main-bg)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      color: 'var(--text-primary)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 40 }}>
        <div style={{
          width: 48,
          height: 48,
          background: 'linear-gradient(135deg, #0ea5e9, #3b82f6)',
          borderRadius: 12,
          display: 'grid',
          placeItems: 'center',
          color: '#fff',
          boxShadow: '0 8px 32px rgba(14, 165, 233, 0.4)'
        }}>
          <span style={{ fontWeight: 900, fontSize: 24, letterSpacing: -1 }}>T</span>
        </div>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em' }}>
          TalentOps <span style={{ color: '#0ea5e9' }}>AI</span>
        </div>
      </div>

      {!error ? (
        <>
          <div style={{ position: 'relative', width: 64, height: 64, marginBottom: 24 }}>
            <Loader2 size={64} color="#0ea5e9" style={{ animation: 'spin 1s linear infinite' }} />
          </div>
          <style>{`
            @keyframes spin {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
          `}</style>
          
          <div style={{
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--text-secondary)',
            height: 24,
            transition: 'opacity 0.3s ease'
          }}>
            {MESSAGES[messageIndex]}
          </div>

          {isSlowNetwork && (
            <div style={{
              marginTop: 24,
              fontSize: 14,
              color: 'var(--warning)',
              maxWidth: 300,
              textAlign: 'center',
              animation: 'fadeIn 0.5s ease'
            }}>
              This is taking a little longer than usual. We're still securely preparing your workspace.
            </div>
          )}
        </>
      ) : (
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <div style={{
            width: 64, height: 64, borderRadius: 32,
            background: 'rgba(239, 68, 68, 0.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 24px',
            color: 'var(--danger)'
          }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </div>
          <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 12 }}>Authentication Failed</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 24, lineHeight: 1.5 }}>
            {error}
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button
              onClick={onRetry}
              style={{
                padding: '10px 24px',
                background: '#0ea5e9',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.href = '/login'}
              style={{
                padding: '10px 24px',
                background: 'rgba(255, 255, 255, 0.1)',
                color: 'var(--text-primary)',
                border: 'none',
                borderRadius: 8,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Return to Login
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
