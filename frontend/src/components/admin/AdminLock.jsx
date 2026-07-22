import { useState, useRef, useCallback, useEffect } from 'react'
import api from '../../services/api'

export default function AdminLock({ onUnlock, errorMessage }) {
  const [pin, setPin] = useState('')
  const [shake, setShake] = useState(false)
  const [attempts, setAttempts] = useState(0)
  const [verifying, setVerifying] = useState(false)
  const [lockedMsg, setLockedMsg] = useState('')
  const [remember, setRemember] = useState(false)
  const [healthOpen, setHealthOpen] = useState(false)
  const [healthData, setHealthData] = useState(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const pinRef = useRef(pin)
  pinRef.current = pin
  const inputRef = useRef(null)

  const submit = useCallback(async () => {
    if (verifying) return
    if (pinRef.current.length === 0) return
    setVerifying(true)
    setLockedMsg('')
    try {
      await onUnlock(pinRef.current, { remember })
    } catch (e) {
      const status = e?.response?.status
      if (status === 429) {
        setLockedMsg('Too many failed attempts. Please wait before retrying.')
      } else {
        setShake(true)
        setAttempts(a => a + 1)
        setPin('')
        setTimeout(() => setShake(false), 600)
      }
    } finally {
      setVerifying(false)
    }
  }, [onUnlock, remember, verifying])

  const pressKey = useCallback((k) => {
    if (k === 'backspace') setPin(p => p.slice(0, -1))
    else if (k === 'enter') submit()
    else setPin(p => (p.length < 32 ? p + k : p))
  }, [submit])

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Backspace' || e.key === 'Delete') {
        e.preventDefault()
        pressKey('backspace')
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        submit()
        return
      }
      // Allow typing any visible characters for non-numeric admin passwords.
      if (e.key && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        pressKey(e.key)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [pressKey, submit])

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 100000,
      display: 'grid',
      gridTemplateColumns: '1.2fr 1fr',
      background: 'linear-gradient(135deg, #0a0f1e 0%, #070a12 55%, #05060b 100%)',
      color: '#e5e7eb',
      fontFamily: 'var(--font)',
    }}>
      {/* Left brand panel */}
      <div style={{
        padding: 44,
        background: 'radial-gradient(1200px 800px at 30% 20%, rgba(99,102,241,0.22), transparent 55%), radial-gradient(900px 600px at 60% 70%, rgba(59,130,246,0.18), transparent 60%)',
        borderRight: '1px solid var(--card-border)',
        display: 'flex',
        flexDirection: 'column',
        gap: 22,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 52, height: 52, borderRadius: 14, background: 'rgba(99,102,241,0.22)', border: '1px solid rgba(99,102,241,0.28)', display: 'grid', placeItems: 'center' }}>
            <i className="ti ti-terminal-2" style={{ fontSize: 22, color: '#c7d2fe' }} />
          </div>
          <div style={{ fontSize: 34, fontWeight: 900, letterSpacing: '-0.02em' }}>RECRUIT-INTEL</div>
        </div>
        <div style={{ fontSize: 14, color: 'rgba(229,231,235,0.85)' }}>Recruitment Intelligence Platform</div>
        <div style={{ fontSize: 22, lineHeight: 1.55, color: 'rgba(229,231,235,0.62)', maxWidth: 620 }}>
          Manage recruiter intelligence, company data, state directories, ETL operations, analytics, and platform administration within our unified operational command center.
        </div>
        <div style={{ marginTop: 'auto', display: 'flex', gap: 14, alignItems: 'center', opacity: 0.9 }}>
          <div className="card" style={{ padding: 16, borderRadius: 18, width: 220, background: 'var(--bg-surface)', border: '1px solid var(--card-border)' }}>
            <div style={{ fontSize: 10, color: 'rgba(229,231,235,0.65)', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase' }}>ETL Pipeline</div>
            <div style={{ marginTop: 10, height: 6, borderRadius: 999, background: 'var(--bg-surface)', overflow: 'hidden' }}>
              <div style={{ width: '62%', height: '100%', background: 'rgba(99,102,241,0.75)' }} />
            </div>
            <div style={{ marginTop: 10, fontSize: 12, color: 'rgba(229,231,235,0.75)' }}>98.2% Accuracy Rate</div>
          </div>
          <div className="card" style={{ padding: 16, borderRadius: 18, width: 220, background: 'var(--bg-surface)', border: '1px solid var(--card-border)' }}>
            <div style={{ fontSize: 10, color: 'rgba(229,231,235,0.65)', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Active Clusters</div>
            <div style={{ marginTop: 8, fontSize: 26, fontWeight: 900 }}>1,204</div>
            <div style={{ marginTop: 2, fontSize: 12, color: '#34d399' }}>+12%</div>
          </div>
        </div>
      </div>

      {/* Right access panel */}
      <div style={{ display: 'grid', placeItems: 'center', padding: 28 }}>
        <div style={{ position: 'relative', width: 360, animation: shake ? 'shake 0.5s' : 'none' }}>
        <style>{`
          @keyframes shake { 0%,100%{transform:translateX(0)} 20%,60%{transform:translateX(-8px)} 40%,80%{transform:translateX(8px)} }
          @keyframes pulse-ring { 0%{transform:scale(1);opacity:0.4} 100%{transform:scale(1.5);opacity:0} }
          @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        `}</style>

        {/* Glow ring */}
        <div style={{ position: 'absolute', top: -60, left: '50%', transform: 'translateX(-50%)', width: 80, height: 80, borderRadius: '50%', background: '#38bdf822', animation: 'pulse-ring 2s ease-out infinite' }} />

        <div style={{
          background: 'var(--card-bg)', border: '1px solid var(--card-border)',
          borderRadius: 20, padding: '40px 36px', backdropFilter: 'blur(12px)',
          boxShadow: '0 0 60px rgba(56,189,248,0.08), 0 24px 48px rgba(0,0,0,0.5)',
          display: 'flex', flexDirection: 'column', gap: 28, alignItems: 'center',
          position: 'relative',
        }}>
          {/* Icon */}
          <div style={{ position: 'relative' }}>
            <div style={{ width: 64, height: 64, borderRadius: 16, background: 'linear-gradient(135deg, #0ea5e9, #1d4ed8)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 30px rgba(14,165,233,0.4)' }}>
              <i className="ti ti-terminal-2" style={{ color: 'var(--text-primary)', fontSize: 30 }} />
            </div>
            <div style={{ position: 'absolute', top: -4, right: -4, width: 16, height: 16, borderRadius: '50%', background: '#ef4444', border: '2px solid #0d1829', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <i className="ti ti-lock" style={{ color: 'var(--text-primary)', fontSize: 8 }} />
            </div>
          </div>

          {/* Title */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.02em', marginBottom: 6 }}>ADMIN TERMINAL</div>
            <div style={{ fontSize: 12, color: '#475569', fontFamily: "'DM Mono', monospace" }}>
              <span style={{ color: '#38bdf8', animation: 'blink 1.2s step-end infinite' }}>▌</span> Restricted access. Authorisation required.
            </div>
          </div>

          {/* Hidden input to support full keyboard passwords (not just numeric keypad). */}
          <input
            ref={inputRef}
            type="password"
            value={pin}
            onChange={(e) => setPin(String(e.target.value || '').slice(0, 32))}
            autoFocus
            inputMode="text"
            autoComplete="current-password"
            aria-label="Admin password"
            style={{ position: 'absolute', opacity: 0, pointerEvents: 'none' }}
          />

          {/* PIN dots */}
          <div style={{ display: 'flex', gap: 12 }}>
            {[0,1,2,3].map(i => (
              <div key={i} style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid', borderColor: pin.length > i ? '#38bdf8' : '#1e3a5f', background: pin.length > i ? '#38bdf8' : 'transparent', transition: 'all 0.15s', boxShadow: pin.length > i ? '0 0 8px #38bdf8' : 'none' }} />
            ))}
          </div>

          {/* Keypad */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, width: '100%' }}>
            {[
              { key: '1', label: '1' },
              { key: '2', label: '2' },
              { key: '3', label: '3' },
              { key: '4', label: '4' },
              { key: '5', label: '5' },
              { key: '6', label: '6' },
              { key: '7', label: '7' },
              { key: '8', label: '8' },
              { key: '9', label: '9' },
              { key: 'backspace', label: <i className="ti ti-backspace" /> },
              { key: '0', label: '0' },
              { key: 'enter', label: <i className="ti ti-arrow-right" /> },
            ].map((k) => (
              <button
                key={k.key}
                type="button"
                onClick={() => { inputRef.current?.focus(); pressKey(k.key) }}
                disabled={verifying}
                style={{
                  height: 52,
                  borderRadius: 10,
                  fontSize: 18,
                  fontWeight: 600,
                  background: k.key === 'enter' ? 'linear-gradient(135deg, #0ea5e9, #1d4ed8)' : '#111c30',
                  color: k.key === 'enter' ? '#fff' : '#94a3b8',
                  border: '1px solid #1e3a5f',
                  cursor: verifying ? 'not-allowed' : 'pointer',
                  transition: 'all 0.1s',
                  boxShadow: k.key === 'enter' ? '0 0 16px rgba(14,165,233,0.3)' : 'none',
                  opacity: verifying ? 0.7 : 1,
                  display: 'grid',
                  placeItems: 'center',
                }}
                onMouseEnter={(e) => {
                  if (verifying) return
                  e.currentTarget.style.background = k.key === 'enter' ? 'linear-gradient(135deg, #38bdf8, #3b82f6)' : '#1a2840'
                  e.currentTarget.style.color = '#e2e8f0'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = k.key === 'enter' ? 'linear-gradient(135deg, #0ea5e9, #1d4ed8)' : '#111c30'
                  e.currentTarget.style.color = k.key === 'enter' ? '#fff' : '#94a3b8'
                }}
              >
                {k.label}
              </button>
            ))}
          </div>

          <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
            <button
              type="button"
              onClick={() => { setPin(''); setAttempts(0); setLockedMsg('') }}
              style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 12 }}
              title="Emergency Reset (clears PIN input only)"
              disabled={verifying}
            >
              Emergency Reset
            </button>
            <button
              type="button"
              onClick={async () => {
                setHealthOpen(true)
                setHealthLoading(true)
                try {
                  const { data } = await api.get('/health')
                  setHealthData(data)
                } catch {
                  setHealthData({ status: 'degraded', database: 'unknown', detail: 'Cannot reach API' })
                } finally {
                  setHealthLoading(false)
                }
              }}
              style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 12 }}
              title="System Health"
              disabled={verifying}
            >
              System Health
            </button>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#94a3b8', cursor: verifying ? 'not-allowed' : 'pointer', opacity: verifying ? 0.7 : 1 }} title="Remember this admin session on this device">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} disabled={verifying} />
              Remember
            </label>
          </div>

          {verifying && (
            <div style={{ fontSize: 11.5, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}>
              <i className="ti ti-loader" style={{ fontSize: 13, animation: 'spin 0.8s linear infinite' }} />
              Verifying credentials…
            </div>
          )}

          {(lockedMsg || errorMessage || attempts > 0) && (
            <div style={{ fontSize: 11.5, color: lockedMsg ? '#fbbf24' : '#f87171', display: 'flex', alignItems: 'center', gap: 6 }}>
              <i className={`ti ${lockedMsg ? 'ti-alert-circle' : 'ti-alert-triangle'}`} style={{ fontSize: 13 }} />
              {lockedMsg || errorMessage || `Invalid PIN`}
            </div>
          )}
        </div>
      </div>
      </div>

      {healthOpen && (
        <div
          onClick={() => setHealthOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 100001,
            padding: 20,
          }}
        >
          <div
            className="card"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: 520,
              padding: 18,
              borderRadius: 18,
              background: 'var(--card-bg)',
              border: '1px solid var(--card-border)',
              boxShadow: 'var(--shadow-lg)',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: 13, fontWeight: 900, color: 'var(--text-primary)' }}>
                System Health
              </div>
              <button onClick={() => setHealthOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <i className="ti ti-x" />
              </button>
            </div>

            {healthLoading ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
                <i className="ti ti-loader" style={{ animation: 'spin 0.8s linear infinite' }} />
                Checking services…
              </div>
            ) : (
              <div style={{ display: 'grid', gap: 10 }}>
                {[
                  { label: 'API Service', value: healthData?.status || 'unknown', ok: healthData?.status === 'healthy' },
                  { label: 'Database', value: healthData?.database || 'unknown', ok: healthData?.database === 'connected' },
                  { label: 'ETL Service', value: 'No Data Available', ok: null },
                  { label: 'Search Engine', value: 'No Data Available', ok: null },
                ].map((r) => (
                  <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', borderRadius: 14, background: 'var(--panel-bg)', border: '1px solid var(--card-border)' }}>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 800 }}>{r.label}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {r.ok === true && <span className="badge badge-green">Healthy</span>}
                      {r.ok === false && <span className="badge badge-red">Degraded</span>}
                      {r.ok === null && <span className="badge badge-gray">N/A</span>}
                      <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>{String(r.value)}</span>
                    </div>
                  </div>
                ))}
                {healthData?.detail && (
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{healthData.detail}</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
