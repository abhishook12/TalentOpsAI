import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { API as API_BASE_URL } from '../services/api';

const ConnectOutlookModal = ({ isOpen, onClose, onSuccess }) => {
  const [status, setStatus] = useState('idle'); // idle, connecting, verifying, success, error
  const [errorMessage, setErrorMessage] = useState('');

  // When modal closes, reset state
  useEffect(() => {
    if (!isOpen) {
      setStatus('idle');
      setErrorMessage('');
    }
  }, [isOpen]);

  // Polling mechanism to check if connection was successful
  useEffect(() => {
    let intervalId;
    if (status === 'verifying') {
      intervalId = setInterval(async () => {
        try {
          const res = await api.get('/api/bridge/status');
          if (res.data.status === 'online') {
            setStatus('success');
            clearInterval(intervalId);
            setTimeout(() => {
              if (onSuccess) onSuccess();
              onClose();
            }, 2000);
          }
        } catch (err) {
          // Keep verifying unless we hit a hard failure limit, 
          // but we'll just quietly poll until success or manual close.
          console.error("Error polling status", err);
        }
      }, 1500);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [status, onClose, onSuccess]);

  const handleConnect = () => {
    setStatus('verifying');
    const token = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
    const currentOrigin = window.location.origin;
    
    // Open a popup for OAuth flow
    const authUrl = `${API_BASE_URL}/api/bridge/oauth/login?token=${token}&redirect_uri=${encodeURIComponent(currentOrigin + '/profile?bridge=connected')}&popup=true`;
    
    const popupWidth = 600;
    const popupHeight = 700;
    const left = window.screen.width / 2 - popupWidth / 2;
    const top = window.screen.height / 2 - popupHeight / 2;
    
    const authWindow = window.open(
      authUrl,
      'OutlookAuth',
      `width=${popupWidth},height=${popupHeight},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
    );

    // Monitor if the user manually closes the window before success.
    // After popup closes, keep polling for a grace period to catch
    // late OAuth callbacks before reverting to idle.
    const windowCheckInterval = setInterval(() => {
      if (authWindow && authWindow.closed) {
        clearInterval(windowCheckInterval);
        // Give the polling 8 more seconds to detect online status
        // (OAuth callback may arrive after popup closes)
        setTimeout(() => {
          setStatus((prevStatus) => {
            if (prevStatus === 'verifying') {
              return 'idle'; // Grace period expired, user likely canceled
            }
            return prevStatus;
          });
        }, 8000);
      }
    }, 1000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={status !== 'verifying' ? onClose : undefined}
      />
      
      {/* Modal Box */}
      <div className="relative bg-[var(--surface-container)] border border-[var(--outline)] rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col">
        {/* Header */}
        <div className="px-6 py-5 border-b border-[var(--outline)] flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Connect Outlook</h2>
          {status !== 'verifying' && (
            <button 
              onClick={onClose}
              className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors p-1"
            >
              <i className="ti ti-x text-xl"></i>
            </button>
          )}
        </div>

        {/* Body */}
        <div className="p-6 flex flex-col items-center text-center">
          
          {status === 'idle' && (
            <>
              <div className="w-16 h-16 bg-[#0078D4]/10 border border-[#0078D4]/30 rounded-full flex items-center justify-center mb-4">
                <i className="ti ti-brand-windows text-3xl text-[#0078D4]"></i>
              </div>
              <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">
                Authorize TalentOps
              </h3>
              <p className="text-[var(--text-secondary)] text-sm mb-6 max-w-sm">
                Connect your Microsoft Outlook account to enable the TalentOps AI Email Bridge. A secure popup will open to authenticate.
              </p>
              
              <button 
                id="modal-connect-btn"
                onClick={handleConnect}
                className="w-full bg-[#0078D4] hover:bg-[#006cbd] text-white px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                <i className="ti ti-brand-windows"></i>
                Connect Outlook Account
              </button>
            </>
          )}

          {status === 'verifying' && (
            <div className="py-8 flex flex-col items-center">
              <div className="w-16 h-16 border-4 border-[var(--outline)] border-t-[#0078D4] rounded-full animate-spin mb-6"></div>
              <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">
                Authenticating...
              </h3>
              <p className="text-[var(--text-secondary)] text-sm">
                Please complete the sign-in process in the secure popup window. Waiting for confirmation...
              </p>
            </div>
          )}

          {status === 'success' && (
            <div className="py-8 flex flex-col items-center">
              <div className="w-16 h-16 bg-green-500/20 border border-green-500/30 rounded-full flex items-center justify-center mb-6">
                <i className="ti ti-check text-3xl text-green-500"></i>
              </div>
              <h3 className="text-lg font-medium text-green-500 mb-2">
                Connected Successfully!
              </h3>
              <p className="text-[var(--text-secondary)] text-sm">
                Your Outlook account is now securely linked to TalentOps AI.
              </p>
            </div>
          )}

          {errorMessage && (
             <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-500 rounded-lg text-sm w-full">
               {errorMessage}
             </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConnectOutlookModal;
