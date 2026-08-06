import React, { useState, useEffect } from 'react'
import { X, Globe, Shield, Clock, Bell, Save } from 'lucide-react'

export default function DevicePolicyPanel({ isOpen, onClose }) {
  const [policy, setPolicy] = useState({
    auto_approve_networks: false,
    trusted_cidr: '',
    require_admin_approval: true,
    allowed_countries: 'US, CA, GB',
    block_outside_geography: true,
    max_devices_per_user: 5,
    default_trust_duration: 90,
    auto_revoke_idle_days: 30,
    notify_on_pending: true
  })

  // Load from local storage
  useEffect(() => {
    const saved = localStorage.getItem('trusted_devices_policy')
    if (saved) {
      try {
        setPolicy(JSON.parse(saved))
      } catch (e) {
        console.error(e)
      }
    }
  }, [])

  const handleSave = () => {
    localStorage.setItem('trusted_devices_policy', JSON.stringify(policy))
    // Simulate API delay
    setTimeout(() => {
      onClose()
    }, 400)
  }

  return (
    <>
      {/* Backdrop */}
      <div 
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`} 
        style={{ backdropFilter: 'blur(4px)' }}
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div 
        className={`fixed top-0 right-0 z-50 h-full w-full max-w-md border-l border-[var(--card-border)] bg-[var(--main-bg)] shadow-2xl transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : 'translate-x-full'} flex flex-col`}
      >
        <div className="flex items-center justify-between border-b border-[var(--card-border)] p-6 bg-[var(--surface-container)]">
          <div>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Access Policy</h2>
            <p className="text-xs text-[var(--text-muted)] mt-1">Configure global trust settings</p>
          </div>
          <button onClick={onClose} className="rounded-full p-2 hover:bg-[var(--surface-container-highest)] text-[var(--text-secondary)]">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          {/* Auto-Approval Section */}
          <section className="space-y-4">
            <h3 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
              <Shield size={16} className="text-[var(--brand)]" /> Network Trust
            </h3>
            
            <label className="flex items-start justify-between cursor-pointer">
              <div>
                <div className="font-semibold text-[var(--text-primary)] text-sm">Auto-approve on trusted networks</div>
                <div className="text-xs text-[var(--text-muted)] mt-1 max-w-[250px]">Automatically skip the queue for devices connecting from known IP ranges.</div>
              </div>
              <input 
                type="checkbox" 
                className="toggle-switch"
                checked={policy.auto_approve_networks}
                onChange={e => setPolicy({...policy, auto_approve_networks: e.target.checked})}
              />
            </label>

            {policy.auto_approve_networks && (
              <div className="pl-4 border-l-2 border-[var(--card-border)] mt-2">
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Trusted CIDR Ranges</label>
                <input 
                  type="text" 
                  value={policy.trusted_cidr}
                  onChange={e => setPolicy({...policy, trusted_cidr: e.target.value})}
                  placeholder="e.g. 192.168.1.0/24"
                  className="w-full bg-[var(--bg-surface)] border border-[var(--card-border)] rounded-md px-3 py-2 text-sm text-[var(--text-primary)]"
                />
              </div>
            )}

            <label className="flex items-start justify-between cursor-pointer">
              <div>
                <div className="font-semibold text-[var(--text-primary)] text-sm">Require admin approval for admins</div>
                <div className="text-xs text-[var(--text-muted)] mt-1 max-w-[250px]">Admins cannot self-approve their own devices.</div>
              </div>
              <input 
                type="checkbox" 
                className="toggle-switch"
                checked={policy.require_admin_approval}
                onChange={e => setPolicy({...policy, require_admin_approval: e.target.checked})}
              />
            </label>
          </section>

          {/* Geography Section */}
          <section className="space-y-4">
            <h3 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
              <Globe size={16} className="text-[var(--brand)]" /> Geography
            </h3>
            
            <label className="flex items-start justify-between cursor-pointer">
              <div>
                <div className="font-semibold text-[var(--text-primary)] text-sm">Block sign-ins outside allowed regions</div>
                <div className="text-xs text-[var(--text-muted)] mt-1 max-w-[250px]">Immediately block pending devices not matching the allowed countries.</div>
              </div>
              <input 
                type="checkbox" 
                className="toggle-switch"
                checked={policy.block_outside_geography}
                onChange={e => setPolicy({...policy, block_outside_geography: e.target.checked})}
              />
            </label>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Allowed Countries (ISO Codes, comma separated)</label>
              <input 
                type="text" 
                value={policy.allowed_countries}
                onChange={e => setPolicy({...policy, allowed_countries: e.target.value})}
                placeholder="US, CA, GB"
                className="w-full bg-[var(--bg-surface)] border border-[var(--card-border)] rounded-md px-3 py-2 text-sm text-[var(--text-primary)]"
              />
            </div>
          </section>

          {/* Limits & Expiry Section */}
          <section className="space-y-4">
            <h3 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
              <Clock size={16} className="text-[var(--brand)]" /> Limits & Expiry
            </h3>
            
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Max Devices per User</label>
                <input 
                  type="number" 
                  value={policy.max_devices_per_user}
                  onChange={e => setPolicy({...policy, max_devices_per_user: parseInt(e.target.value)})}
                  className="w-full bg-[var(--bg-surface)] border border-[var(--card-border)] rounded-md px-3 py-2 text-sm text-[var(--text-primary)]"
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Default Trust (Days)</label>
                <input 
                  type="number" 
                  value={policy.default_trust_duration}
                  onChange={e => setPolicy({...policy, default_trust_duration: parseInt(e.target.value)})}
                  className="w-full bg-[var(--bg-surface)] border border-[var(--card-border)] rounded-md px-3 py-2 text-sm text-[var(--text-primary)]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Auto-revoke Idle Devices (Days)</label>
              <input 
                type="number" 
                value={policy.auto_revoke_idle_days}
                onChange={e => setPolicy({...policy, auto_revoke_idle_days: parseInt(e.target.value)})}
                className="w-full bg-[var(--bg-surface)] border border-[var(--card-border)] rounded-md px-3 py-2 text-sm text-[var(--text-primary)]"
              />
            </div>
          </section>

          {/* Alerts Section */}
          <section className="space-y-4">
            <h3 className="flex items-center gap-2 text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
              <Bell size={16} className="text-[var(--brand)]" /> Alerts
            </h3>
            
            <label className="flex items-start justify-between cursor-pointer">
              <div>
                <div className="font-semibold text-[var(--text-primary)] text-sm">Notify on new pending device</div>
                <div className="text-xs text-[var(--text-muted)] mt-1 max-w-[250px]">Send email to admins when a high-risk device requires approval.</div>
              </div>
              <input 
                type="checkbox" 
                className="toggle-switch"
                checked={policy.notify_on_pending}
                onChange={e => setPolicy({...policy, notify_on_pending: e.target.checked})}
              />
            </label>
          </section>

        </div>

        <div className="border-t border-[var(--card-border)] p-4 bg-[var(--surface-container)] flex gap-3">
          <button 
            onClick={onClose}
            className="flex-1 px-4 py-2 rounded-md font-bold text-sm bg-[var(--surface-container-high)] text-[var(--text-primary)] border border-[var(--card-border)] hover:bg-[var(--surface-container-highest)]"
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            className="flex-1 px-4 py-2 rounded-md font-bold text-sm bg-[var(--text-primary)] text-[var(--main-bg)] flex items-center justify-center gap-2 hover:opacity-90"
          >
            <Save size={16} /> Save Policy
          </button>
        </div>
        
        <style>{`
          .toggle-switch {
            appearance: none;
            width: 40px;
            height: 20px;
            background: var(--surface-container-highest);
            border-radius: 6px;
            position: relative;
            cursor: pointer;
            outline: none;
            transition: background 0.2s;
            flex-shrink: 0;
            border: 1px solid var(--card-border-strong);
          }
          .toggle-switch::after {
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            width: 14px;
            height: 14px;
            background: var(--text-muted);
            border-radius: 50%;
            transition: transform 0.2s, background 0.2s;
          }
          .toggle-switch:checked {
            background: var(--brand);
            border-color: var(--brand);
          }
          .toggle-switch:checked::after {
            transform: translateX(20px);
            background: var(--main-bg);
          }
        `}</style>
      </div>
    </>
  )
}
