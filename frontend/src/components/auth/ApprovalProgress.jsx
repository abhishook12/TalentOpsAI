import React, { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, XCircle, ShieldAlert } from 'lucide-react';
import { API } from '../../services/api';

export default function ApprovalProgress({ deviceId, onApproved }) {
  const [status, setStatus] = useState('pending'); // 'pending', 'approved', 'rejected', 'error'
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!deviceId) return;

    // Connect to SSE stream
    const eventSource = new EventSource(`${API}/auth/status-stream/${deviceId}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.status === 'approved') {
          setStatus('approved');
          eventSource.close();
          // Trigger the onApproved callback instantly for immediate navigation
          onApproved();
        } else if (data.status === 'rejected') {
          setStatus('rejected');
          eventSource.close();
        } else if (data.status === 'error') {
          setStatus('error');
          setErrorMessage(data.message || 'An error occurred');
          eventSource.close();
        }
      } catch (err) {
        console.error('Failed to parse SSE message:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
      // We don't necessarily close it here, EventSource auto-reconnects.
      // But if it's a fatal error, we might want to show a fallback UI.
    };

    return () => {
      eventSource.close();
    };
  }, [deviceId]);

  return (
    <div style={{
      background: 'var(--panel-bg)',
      border: '1px solid var(--card-border)',
      borderRadius: '16px',
      padding: '32px 24px',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px',
      width: '100%',
      maxWidth: '400px',
      margin: '0 auto'
    }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 800, marginBottom: '8px' }}>Authenticating</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: 1.5 }}>
          Your identity has been verified. We are now synchronizing your secure session.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        
        {/* Step 1: Identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <CheckCircle2 size={20} color="var(--success, #10b981)" />
          <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>Google account verified</span>
        </div>

        <div style={{ width: '2px', height: '16px', background: 'var(--card-border)', marginLeft: '9px', marginTop: '-8px', marginBottom: '-8px' }} />

        {/* Step 2: Synchronization */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <CheckCircle2 size={20} color="var(--success, #10b981)" />
          <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>Identity synchronized</span>
        </div>

        <div style={{ width: '2px', height: '16px', background: 'var(--card-border)', marginLeft: '9px', marginTop: '-8px', marginBottom: '-8px' }} />

        {/* Step 3: Admin Approval */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {status === 'pending' ? (
            <Loader2 size={20} color="var(--accent, #c9a84c)" className="animate-spin" />
          ) : status === 'approved' ? (
            <CheckCircle2 size={20} color="var(--success, #10b981)" />
          ) : (
            <XCircle size={20} color="var(--danger, #ef4444)" />
          )}
          <span style={{ 
            fontSize: '14px', 
            fontWeight: 500, 
            color: status === 'pending' ? 'var(--accent, #c9a84c)' : status === 'rejected' ? 'var(--danger, #ef4444)' : 'var(--text-primary)'
          }}>
            {status === 'pending' ? 'Waiting for administrator approval...' : status === 'approved' ? 'Device approved' : 'Access denied by administrator'}
          </span>
        </div>

        {status === 'approved' && (
          <>
            <div style={{ width: '2px', height: '16px', background: 'var(--card-border)', marginLeft: '9px', marginTop: '-8px', marginBottom: '-8px' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Loader2 size={20} color="var(--success, #10b981)" className="animate-spin" />
              <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>Loading your workspace...</span>
            </div>
          </>
        )}

      </div>

      {status === 'rejected' && (
        <div style={{ 
          marginTop: '12px',
          padding: '12px', 
          background: 'rgba(239, 68, 68, 0.1)', 
          border: '1px solid rgba(239, 68, 68, 0.2)', 
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
          color: '#ef4444',
          fontSize: '13px',
          lineHeight: 1.5
        }}>
          <ShieldAlert size={16} style={{ marginTop: '2px', flexShrink: 0 }} />
          Your account or device has been rejected by an administrator. Please contact IT support for further assistance.
        </div>
      )}

      {status === 'error' && (
        <div style={{ color: 'var(--danger)', fontSize: '13px', textAlign: 'center' }}>
          {errorMessage}
        </div>
      )}
    </div>
  );
}
