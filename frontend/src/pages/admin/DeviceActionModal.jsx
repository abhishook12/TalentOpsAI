import React, { useState } from 'react'
import { AlertCircle, CheckCircle, ShieldAlert, X, Zap } from 'lucide-react'

const ACTION_CONFIG = {
  Trusted: {
    title: 'Approve device',
    consequence: 'Device signs in without further approval.',
    icon: CheckCircle,
    color: 'var(--brand)',
    requireReason: false,
    showDuration: true,
    showTerminate: false
  },
  Blocked: {
    title: 'Block device',
    consequence: 'Sign-ins refused, existing sessions killed.',
    icon: ShieldAlert,
    color: 'var(--brand-strong)',
    requireReason: true,
    showDuration: false,
    showTerminate: true
  },
  Revoked: {
    title: 'Revoke trust',
    consequence: 'Returns to pending on next sign-in.',
    icon: ShieldAlert,
    color: 'var(--brand)',
    requireReason: true,
    showDuration: false,
    showTerminate: true
  },
  Pending: {
    title: 'Restore to pending',
    consequence: 'Un-blocked, back in the queue for review.',
    icon: AlertCircle,
    color: 'var(--text-primary)',
    requireReason: true,
    showDuration: false,
    showTerminate: false
  },
  ReVerify: {
    title: 'Force re-verification',
    consequence: 'Sessions stay, next sign-in needs MFA.',
    icon: Zap,
    color: 'var(--brand)',
    requireReason: false,
    showDuration: false,
    showTerminate: false
  },
  Terminate: {
    title: 'Terminate sessions',
    consequence: 'Active sessions end, trust status unchanged.',
    icon: X,
    color: 'var(--brand-strong)',
    requireReason: false,
    showDuration: false,
    showTerminate: false
  }
}

const REASON_PRESETS = [
  'Suspected phishing',
  'User offboarded',
  'Device lost/stolen',
  'Unrecognised location',
  'Routine review'
]

export default function DeviceActionModal({ isOpen, onClose, onConfirm, actionType, count = 1 }) {
  const [reason, setReason] = useState('')
  const [duration, setDuration] = useState('90')
  const [terminateSessions, setTerminateSessions] = useState(true)

  if (!isOpen || !actionType) return null

  const config = ACTION_CONFIG[actionType]
  if (!config) return null
  
  const Icon = config.icon

  const handleConfirm = () => {
    onConfirm({
      reason,
      duration: config.showDuration ? parseInt(duration) : null,
      terminateSessions: config.showTerminate ? terminateSessions : false
    })
    setReason('')
  }

  const isValid = !config.requireReason || reason.trim().length > 0

  return (
    <>
      <div 
        className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 animate-in fade-in duration-200"
        style={{ backdropFilter: 'blur(4px)' }}
        onClick={onClose}
      >
        <div 
          className="bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl shadow-2xl max-w-md w-full animate-in zoom-in-95 duration-200"
          onClick={e => e.stopPropagation()}
        >
          <div className="p-6 border-b border-[var(--card-border)] flex items-start gap-4">
            <div className="p-3 rounded-full" style={{ background: `color-mix(in srgb, ${config.color} 15%, transparent)` }}>
              <Icon size={24} style={{ color: config.color }} />
            </div>
            <div className="flex-1 pt-1">
              <h2 className="text-xl font-bold text-[var(--text-primary)]">
                {config.title} {count > 1 ? `(${count} devices)` : ''}
              </h2>
              <p className="text-sm text-[var(--text-secondary)] mt-1">{config.consequence}</p>
            </div>
          </div>

          <div className="p-6 space-y-5 bg-[var(--surface-container)]">
            
            {config.showDuration && (
              <div>
                <label className="block text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">Trust Duration</label>
                <div className="flex gap-2">
                  {['30', '90', '365', 'permanent'].map(val => (
                    <button
                      key={val}
                      onClick={() => setDuration(val)}
                      className={`flex-1 py-1.5 text-xs font-bold rounded-md border transition-colors ${
                        duration === val 
                          ? 'bg-[var(--text-primary)] text-[var(--main-bg)] border-[var(--text-primary)]' 
                          : 'bg-[var(--surface-container-high)] text-[var(--text-secondary)] border-[var(--card-border)] hover:text-[var(--text-primary)]'
                      }`}
                    >
                      {val === 'permanent' ? 'Forever' : `${val} Days`}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {config.showTerminate && (
              <label className="flex items-center gap-3 p-3 rounded-lg border border-[var(--card-border-strong)] bg-[var(--surface-container-highest)] cursor-pointer hover:bg-[var(--surface-container-high)]">
                <input 
                  type="checkbox" 
                  checked={terminateSessions}
                  onChange={e => setTerminateSessions(e.target.checked)}
                  className="w-4 h-4 rounded border-[var(--card-border-strong)] bg-[var(--main-bg)] text-[var(--brand-strong)] focus:ring-[var(--brand-strong)]"
                />
                <span className="text-sm font-semibold text-[var(--text-primary)]">Terminate active sessions immediately</span>
              </label>
            )}

            <div>
              <label className="flex items-center justify-between text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-2">
                Reason {config.requireReason ? <span className="text-[var(--brand-strong)]">*Required</span> : '(Optional)'}
              </label>
              
              <div className="flex flex-wrap gap-2 mb-3">
                {REASON_PRESETS.map(preset => (
                  <button
                    key={preset}
                    onClick={() => setReason(preset)}
                    className="px-2 py-1 text-[11px] font-semibold rounded-full border border-[var(--card-border-strong)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--text-muted)] bg-[var(--surface-container-high)] transition-colors"
                  >
                    {preset}
                  </button>
                ))}
              </div>
              
              <textarea
                value={reason}
                onChange={e => setReason(e.target.value)}
                placeholder="Type additional details here..."
                rows={3}
                className="w-full bg-[var(--bg-surface)] border border-[var(--card-border-strong)] rounded-lg p-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--text-muted)] resize-none"
              />
            </div>
          </div>

          <div className="p-4 border-t border-[var(--card-border)] flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg font-bold text-sm bg-[var(--surface-container)] border border-[var(--card-border)] text-[var(--text-primary)] hover:bg-[var(--surface-container-highest)]"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={!isValid}
              className="flex-1 px-4 py-2 rounded-lg font-bold text-sm transition-all text-white flex justify-center items-center gap-2"
              style={{
                background: isValid ? config.color : 'var(--surface-container-highest)',
                color: isValid ? (config.color === 'var(--text-primary)' ? 'var(--main-bg)' : '#fff') : 'var(--text-muted)',
                opacity: isValid ? 1 : 0.6,
                cursor: isValid ? 'pointer' : 'not-allowed'
              }}
            >
              Confirm {actionType}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
