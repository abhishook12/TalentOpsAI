import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function UpdateCenter() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [changelog, setChangelog] = useState([]);
  const [hover, setHover] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await api.get('/updates/status');
      setStatus(res.data);
    } catch (e) {
      console.error("Failed to fetch update status", e);
    }
  };

  const fetchChangelog = async () => {
    try {
      const res = await api.get('/updates/changelog');
      setChangelog(res.data);
    } catch (e) {
      console.error("Failed to fetch changelog", e);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll every 5 minutes in case an admin updates a status
    const intv = setInterval(fetchStatus, 300000);
    return () => clearInterval(intv);
  }, []);

  useEffect(() => {
    if (open) fetchChangelog();
  }, [open]);

  if (!status) return null;

  // Determine indicator color based on status
  let color = '#38bdf8'; // Blue: Update Available / Operational (default)
  let icon = 'ti-info-circle';
  
  if (status.status === 'Verified & Operational' || status.status === 'Verified') {
    color = '#22c55e'; // Green
    icon = 'ti-check';
  } else if (status.status === 'Pending Verification') {
    color = '#fbbf24'; // Yellow
    icon = 'ti-alert-triangle';
  } else if (status.status === 'Failed Verification') {
    color = '#ef4444'; // Red
    icon = 'ti-x';
  }

  return (
    <>
      {/* Floating Indicator */}
      <div 
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: 9000,
          display: 'flex',
          alignItems: 'flex-end',
          flexDirection: 'column',
          gap: 8,
        }}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        {hover && (
          <div style={{
            background: 'var(--panel-bg)',
            border: '1px solid var(--card-border)',
            padding: '12px 16px',
            borderRadius: 12,
            boxShadow: 'var(--shadow-lg)',
            fontSize: 12,
            animation: 'fadeUp 0.2s ease',
            color: 'var(--text-secondary)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, marginBottom: 4 }}>
              <span style={{ fontWeight: 800, color: 'var(--text-primary)' }}>Platform Status</span>
              <span style={{ color }}>{status.version}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, marginBottom: 4 }}>
              <span>Last Update:</span>
              <span style={{ color: 'var(--text-primary)' }}>{status.date ? status.date.split('T')[0] : 'Never'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20 }}>
              <span>Status:</span>
              <strong style={{ color }}>{status.status}</strong>
            </div>
          </div>
        )}
        
        <button
          onClick={() => setOpen(true)}
          style={{
            width: 48,
            height: 48,
            borderRadius: 24,
            background: 'var(--card-bg)',
            border: `2px solid ${color}`,
            color: color,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 22,
            cursor: 'pointer',
            boxShadow: `0 4px 12px ${color}33`,
            transition: 'all 0.2s ease',
            transform: hover ? 'scale(1.05)' : 'scale(1)',
          }}
        >
          <i className={`ti ${icon}`} />
        </button>
      </div>

      {/* Update Center Drawer */}
      {open && (
        <>
          <div 
            onClick={() => setOpen(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(10,13,18,0.7)', zIndex: 9001, backdropFilter: 'blur(4px)' }} 
          />
          <div style={{
            position: 'fixed',
            top: 0, right: 0, bottom: 0, width: 440,
            background: 'var(--main-bg)',
            borderLeft: '1px solid var(--card-border)',
            zIndex: 9002,
            boxShadow: 'var(--shadow-xl)',
            display: 'flex',
            flexDirection: 'column',
            animation: 'slideLeft 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
          }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Update & Verification Center</h2>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Official platform changelog & status</div>
              </div>
              <button onClick={() => setOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 20 }}>
                <i className="ti ti-x" />
              </button>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
              
              {/* Current Status Card */}
              <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 16, padding: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>Last Confirmed Update</div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Version:</div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)' }}>{status.version}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Updated:</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {status.date ? new Date(status.date).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Never'}
                    </div>
                  </div>
                </div>
                
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--card-border)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Platform Status:</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 4, background: color, boxShadow: `0 0 8px ${color}` }} />
                    <strong style={{ color }}>{status.status}</strong>
                  </div>
                </div>
              </div>
              
              {/* Changelog */}
              <div>
                <h3 style={{ margin: '0 0 16px 0', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Changelog History</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {changelog.length === 0 && (
                    <div style={{ color: 'var(--text-muted)', fontSize: 13, fontStyle: 'italic' }}>No updates recorded yet.</div>
                  )}
                  {changelog.map((update) => (
                    <div key={update.id} style={{ borderLeft: '2px solid var(--card-border)', paddingLeft: 16, position: 'relative' }}>
                      <div style={{ position: 'absolute', left: -5, top: 4, width: 8, height: 8, borderRadius: 4, background: 'var(--card-border)' }} />
                      
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{update.title} <span style={{ color: 'var(--text-muted)', fontWeight: 500, fontSize: 12, marginLeft: 8 }}>{update.version}</span></div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{new Date(update.date).toLocaleDateString()} · By {update.developer}</div>
                        </div>
                        <div style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 99, background: update.status.includes('Verified') ? 'rgba(34,197,94,0.1)' : update.status.includes('Failed') ? 'rgba(239,68,68,0.1)' : 'rgba(251,191,36,0.1)', color: update.status.includes('Verified') ? '#22c55e' : update.status.includes('Failed') ? '#ef4444' : '#fbbf24' }}>
                          {update.status.toUpperCase()}
                        </div>
                      </div>
                      
                      {update.features && update.features.length > 0 && (
                        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {update.features.map(f => (
                            <div key={f.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
                              {f.status.includes('Verified') ? <i className="ti ti-check" style={{ color: '#22c55e' }} /> : 
                               f.status.includes('Failed') ? <i className="ti ti-x" style={{ color: '#ef4444' }} /> :
                               <i className="ti ti-alert-circle" style={{ color: '#fbbf24' }} />}
                              {f.name}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              
            </div>
          </div>
        </>
      )}
    </>
  );
}
