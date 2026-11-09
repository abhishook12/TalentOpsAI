import React, { useState, useEffect, useRef } from 'react';
import { Mail, Laptop, Cloud, Key, Loader2, CheckCircle2, AlertCircle, X, ArrowRight } from 'lucide-react';
import api, { API as API_BASE_URL } from '../services/api';

const ConnectOutlookModal = ({ isOpen, onClose, onSuccess }) => {
  const [activeTab, setActiveTab] = useState('direct'); // 'direct', 'desktop', 'oauth'
  const [status, setStatus] = useState('idle'); // 'idle', 'connecting', 'verifying', 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('');
  const [successInfo, setSuccessInfo] = useState(null);

  // Direct credentials state (universal across all systems)
  const [directEmail, setDirectEmail] = useState('');
  const [directPassword, setDirectPassword] = useState('');
  const [directHost, setDirectHost] = useState('smtp.office365.com');
  const [directPort, setDirectPort] = useState('587');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Local desktop state (Windows 1-click)
  const [desktopEmail, setDesktopEmail] = useState('');

  const windowCheckIntervalRef = useRef(null);

  // Auto-detect server host when typing personal outlook/hotmail addresses
  const handleEmailChange = (val) => {
    setDirectEmail(val);
    const lower = val.toLowerCase();
    if (lower.includes('@outlook.com') || lower.includes('@hotmail.com') || lower.includes('@live.com') || lower.includes('@msn.com')) {
      setDirectHost('smtp-mail.outlook.com');
    } else if (directHost === 'smtp-mail.outlook.com') {
      setDirectHost('smtp.office365.com');
    }
  };

  // Reset state when modal is toggled
  useEffect(() => {
    if (!isOpen) {
      setStatus('idle');
      setErrorMessage('');
      setSuccessInfo(null);
      if (windowCheckIntervalRef.current) {
        clearInterval(windowCheckIntervalRef.current);
      }
    }
  }, [isOpen]);

  // Polling mechanism during OAuth verification
  useEffect(() => {
    let intervalId;
    if (status === 'verifying') {
      intervalId = setInterval(async () => {
        try {
          const res = await api.get('/bridge/status');
          if (res.data?.connected_email || res.data?.status === 'online') {
            setStatus('success');
            setSuccessInfo(res.data?.connected_email || 'Connected');
            clearInterval(intervalId);
            setTimeout(() => {
              if (onSuccess) onSuccess();
              onClose();
            }, 1500);
          }
        } catch (err) {
          console.error("Error polling bridge status:", err);
        }
      }, 1500);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
      if (windowCheckIntervalRef.current) clearInterval(windowCheckIntervalRef.current);
    };
  }, [status, onClose, onSuccess]);

  // Handle direct connect (Universal / Cross-platform)
  const handleDirectConnect = async (e) => {
    if (e) e.preventDefault();
    if (!directEmail || !directPassword) {
      setErrorMessage('Please provide both your email address and password / app password.');
      return;
    }
    setStatus('connecting');
    setErrorMessage('');
    try {
      const res = await api.post('/accounts/connect-local-outlook', {
        email_address: directEmail.trim(),
        password: directPassword.trim(),
        smtp_host: directHost.trim(),
        smtp_port: parseInt(directPort, 10) || 587
      });
      setStatus('success');
      setSuccessInfo(res.data?.email_address || directEmail);
      setTimeout(() => {
        if (onSuccess) onSuccess();
        onClose();
      }, 1500);
    } catch (err) {
      setStatus('idle');
      const msg = err.response?.data?.detail || err.message || 'Failed to authenticate with Outlook mail server.';
      setErrorMessage(msg);
    }
  };

  // Handle 1-Click Local Desktop Outlook
  const handleDesktopConnect = async () => {
    setStatus('connecting');
    setErrorMessage('');
    try {
      const payload = desktopEmail.trim() ? { email_address: desktopEmail.trim() } : {};
      const res = await api.post('/accounts/connect-local-outlook', payload);
      setStatus('success');
      setSuccessInfo(res.data?.email_address || 'Local Desktop Outlook Profile');
      setTimeout(() => {
        if (onSuccess) onSuccess();
        onClose();
      }, 1500);
    } catch (err) {
      setStatus('idle');
      const msg = err.response?.data?.detail || err.message || 'Failed to connect to local Outlook application.';
      setErrorMessage(msg);
    }
  };

  // Handle Cloud OAuth Flow
  const handleOAuthConnect = () => {
    setStatus('verifying');
    setErrorMessage('');
    const token = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
    const currentOrigin = window.location.origin;
    
    const authUrl = `${API_BASE_URL}/bridge/oauth/login?token=${token}&redirect_uri=${encodeURIComponent(currentOrigin + '/profile?bridge=connected')}&popup=true`;
    
    const popupWidth = 600;
    const popupHeight = 700;
    const left = window.screen.width / 2 - popupWidth / 2;
    const top = window.screen.height / 2 - popupHeight / 2;
    
    const authWindow = window.open(
      authUrl,
      'OutlookAuth',
      `width=${popupWidth},height=${popupHeight},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
    );

    if (windowCheckIntervalRef.current) clearInterval(windowCheckIntervalRef.current);
    windowCheckIntervalRef.current = setInterval(() => {
      if (authWindow && authWindow.closed) {
        clearInterval(windowCheckIntervalRef.current);
        setTimeout(() => {
          setStatus((prev) => (prev === 'verifying' ? 'idle' : prev));
        }, 8000);
      }
    }, 1000);
  };

  // Handle Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && status !== 'connecting' && status !== 'verifying') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, status, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div 
        className="absolute inset-0 bg-black/75 backdrop-blur-sm"
        onClick={status !== 'connecting' && status !== 'verifying' ? onClose : undefined}
      />
      
      {/* Modal Box */}
      <div 
        role="dialog"
        aria-modal="true"
        aria-labelledby="connect-outlook-title"
        className="relative glass-panel modal-enter w-full max-w-lg overflow-hidden flex flex-col z-10 border border-[var(--outline)] bg-[var(--bg-surface,#18181b)] shadow-2xl rounded-2xl"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-[var(--outline)] flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#0078d4]/20 border border-[#0078d4]/40 flex items-center justify-center text-[#28a8ea]">
              <Mail size={18} />
            </div>
            <div>
              <h2 id="connect-outlook-title" className="text-base font-semibold text-[var(--text-primary,#ffffff)]">
                Connect Outlook Account
              </h2>
              <p className="text-xs text-[var(--text-secondary,#a1a1aa)]">
                Microsoft 365, Outlook.com, and Corporate Exchange
              </p>
            </div>
          </div>
          {status !== 'connecting' && status !== 'verifying' && (
            <button 
              onClick={onClose}
              className="text-[var(--text-secondary,#a1a1aa)] hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Tab Navigation (Disabled during active connection) */}
        {status !== 'connecting' && status !== 'verifying' && status !== 'success' && (
          <div className="flex border-b border-[var(--outline)] bg-black/20 p-1.5 gap-1.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => { setActiveTab('direct'); setErrorMessage(''); }}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg transition-all ${
                activeTab === 'direct'
                  ? 'bg-white/15 text-white font-semibold shadow-sm'
                  : 'text-[var(--text-secondary,#a1a1aa)] hover:text-white hover:bg-white/5'
              }`}
            >
              <Key size={14} />
              <span>Direct / Any System</span>
            </button>
            <button
              type="button"
              onClick={() => { setActiveTab('desktop'); setErrorMessage(''); }}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg transition-all ${
                activeTab === 'desktop'
                  ? 'bg-white/15 text-white font-semibold shadow-sm'
                  : 'text-[var(--text-secondary,#a1a1aa)] hover:text-white hover:bg-white/5'
              }`}
            >
              <Laptop size={14} />
              <span>1-Click Desktop</span>
            </button>
            <button
              type="button"
              onClick={() => { setActiveTab('oauth'); setErrorMessage(''); }}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg transition-all ${
                activeTab === 'oauth'
                  ? 'bg-white/15 text-white font-semibold shadow-sm'
                  : 'text-[var(--text-secondary,#a1a1aa)] hover:text-white hover:bg-white/5'
              }`}
            >
              <Cloud size={14} />
              <span>Cloud OAuth</span>
            </button>
          </div>
        )}

        {/* Body Content */}
        <div className="p-6">
          
          {/* Active Connecting / Spinner State */}
          {(status === 'connecting' || status === 'verifying') && (
            <div className="py-10 flex flex-col items-center text-center">
              <Loader2 className="w-12 h-12 text-[#28a8ea] animate-spin mb-4" />
              <h3 className="text-base font-semibold text-white mb-1.5">
                {status === 'verifying' ? 'Authenticating with Microsoft...' : 'Verifying Outlook Connection...'}
              </h3>
              <p className="text-xs text-[var(--text-secondary,#a1a1aa)] max-w-sm">
                {status === 'verifying'
                  ? 'Please complete the Microsoft sign-in popup. Detecting authentication confirmation...'
                  : 'Validating credentials with Outlook mail server and synchronizing bridge...'}
              </p>
            </div>
          )}

          {/* Success State */}
          {status === 'success' && (
            <div className="py-10 flex flex-col items-center text-center">
              <div className="w-14 h-14 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mb-4 animate-in zoom-in-90 duration-300">
                <CheckCircle2 size={30} />
              </div>
              <h3 className="text-base font-semibold text-white mb-1.5">
                Outlook Connected Successfully!
              </h3>
              <p className="text-xs text-[var(--text-secondary,#a1a1aa)] max-w-sm">
                Sending account <strong className="text-white">{successInfo}</strong> is linked and active.
              </p>
            </div>
          )}

          {/* Idle / Form State */}
          {status === 'idle' && (
            <>
              {/* TAB 1: DIRECT / ANY SYSTEM (RECOMMENDED) */}
              {activeTab === 'direct' && (
                <form onSubmit={handleDirectConnect} className="space-y-4">
                  <div className="text-xs text-[var(--text-secondary,#a1a1aa)] leading-relaxed bg-[#0078d4]/10 border border-[#0078d4]/20 p-3 rounded-lg">
                    <span className="font-semibold text-[#28a8ea]">Universal Connection:</span> Connects directly via Outlook/Office 365 secure mail gateway. Works seamlessly across any workstation, remote system, Mac, Linux, or PC without Azure AD tenant admin consent blocks.
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[var(--text-secondary,#a1a1aa)]">
                      Outlook or Microsoft 365 Email
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="you@company.com or you@outlook.com"
                      value={directEmail}
                      onChange={(e) => handleEmailChange(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-[var(--outline)] bg-black/40 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[#28a8ea]"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-[var(--text-secondary,#a1a1aa)]">
                        Password or App Password
                      </label>
                      <span className="text-[10px] text-zinc-400">
                        (M365 App Password if 2FA active)
                      </span>
                    </div>
                    <input
                      type="password"
                      required
                      placeholder="••••••••••••"
                      value={directPassword}
                      onChange={(e) => setDirectPassword(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-[var(--outline)] bg-black/40 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[#28a8ea]"
                    />
                  </div>

                  {/* Advanced Settings Toggle */}
                  <div className="pt-1">
                    <button
                      type="button"
                      onClick={() => setShowAdvanced(!showAdvanced)}
                      className="text-[11px] text-[var(--text-secondary,#a1a1aa)] hover:text-white flex items-center gap-1 transition-colors"
                    >
                      <span>{showAdvanced ? '− Hide Server Settings' : '+ Advanced Server Settings'}</span>
                      <span className="text-zinc-500">({directHost}:{directPort})</span>
                    </button>
                    
                    {showAdvanced && (
                      <div className="grid grid-cols-3 gap-2 pt-2.5">
                        <div className="col-span-2 space-y-1">
                          <label className="text-[10px] uppercase font-bold text-zinc-400">SMTP Host</label>
                          <input
                            type="text"
                            value={directHost}
                            onChange={(e) => setDirectHost(e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-md border border-[var(--outline)] bg-black/40 text-xs text-white"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] uppercase font-bold text-zinc-400">Port</label>
                          <input
                            type="text"
                            value={directPort}
                            onChange={(e) => setDirectPort(e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-md border border-[var(--outline)] bg-black/40 text-xs text-white"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <button
                    type="submit"
                    className="w-full mt-2 bg-[#0078d4] hover:bg-[#006cbd] text-white px-4 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#0078d4]/20"
                  >
                    <span>Connect & Verify Account</span>
                    <ArrowRight size={16} />
                  </button>
                </form>
              )}

              {/* TAB 2: 1-CLICK LOCAL DESKTOP OUTLOOK */}
              {activeTab === 'desktop' && (
                <div className="space-y-4">
                  <div className="text-xs text-[var(--text-secondary,#a1a1aa)] leading-relaxed bg-white/5 border border-[var(--outline)] p-3 rounded-lg">
                    <span className="font-semibold text-white">Local Workstation Integration:</span> Auto-detects and connects directly to the Microsoft Outlook desktop client running on this PC. All emails sent will appear in your local Sent Items in real-time.
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[var(--text-secondary,#a1a1aa)]">
                      Target Outlook Email (Optional)
                    </label>
                    <input
                      type="email"
                      placeholder="Leave blank to auto-detect active profile"
                      value={desktopEmail}
                      onChange={(e) => setDesktopEmail(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-[var(--outline)] bg-black/40 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[#28a8ea]"
                    />
                    <p className="text-[11px] text-zinc-400">
                      If you have multiple Outlook profiles, enter the specific email you want to send from.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleDesktopConnect}
                    className="w-full bg-[#0078d4] hover:bg-[#006cbd] text-white px-4 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#0078d4]/20"
                  >
                    <Laptop size={16} />
                    <span>Connect Local Desktop Outlook</span>
                  </button>
                </div>
              )}

              {/* TAB 3: CLOUD OAUTH POPUP */}
              {activeTab === 'oauth' && (
                <div className="space-y-4 text-center py-2">
                  <div className="w-12 h-12 mx-auto rounded-full bg-[#0078d4]/10 border border-[#0078d4]/30 text-[#28a8ea] flex items-center justify-center">
                    <Cloud size={24} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-white mb-1">
                      Microsoft 365 Cloud OAuth
                    </h4>
                    <p className="text-xs text-[var(--text-secondary,#a1a1aa)] max-w-sm mx-auto">
                      Authorize TalentOps via Microsoft's official cloud login popup.
                    </p>
                  </div>

                  <div className="text-left text-[11px] text-zinc-400 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-lg">
                    <strong className="text-amber-300">Note:</strong> If your organization restricts third-party OAuth apps or requires IT admin approval, use the <strong>Direct / Any System</strong> tab for instant connection.
                  </div>

                  <button
                    type="button"
                    onClick={handleOAuthConnect}
                    className="w-full bg-white hover:bg-zinc-200 text-black px-4 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2"
                  >
                    <Cloud size={16} />
                    <span>Sign in with Microsoft</span>
                  </button>
                </div>
              )}
            </>
          )}

          {/* Error Message Alert */}
          {errorMessage && (
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs flex items-start gap-2.5 leading-relaxed animate-in fade-in duration-200">
              <AlertCircle size={16} className="shrink-0 mt-0.5 text-red-400" />
              <div className="flex-1">
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default ConnectOutlookModal;
