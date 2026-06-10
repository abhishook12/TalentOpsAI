import React, { useState, useEffect, useMemo, useCallback } from 'react';
import api from '../services/api';

export default function UpdateCenter() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [changelog, setChangelog] = useState([]);
  const [hover, setHover] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get('/updates/status');
      setStatus(res.data);
      setLastSyncedAt(new Date().toISOString());
      setLoaded(true);
    } catch (e) {
      if (import.meta.env.DEV) {
        console.error("Failed to fetch update status", e);
      }
    }
  }, []);

  const fetchChangelog = useCallback(async () => {
    try {
      const res = await api.get('/updates/changelog');
      setChangelog(res.data);
      setLastSyncedAt(new Date().toISOString());
      setLoaded(true);
    } catch (e) {
      if (import.meta.env.DEV) {
        console.error("Failed to fetch changelog", e);
      }
    }
  }, []);

  useEffect(() => {
    if (!hover && !open) return undefined;

    if (!loaded) {
      fetchStatus();
      fetchChangelog();
    }

    if (!open) return undefined;

    const intv = setInterval(fetchStatus, 300000);
    const changelogIntv = setInterval(fetchChangelog, 600000);
    return () => {
      clearInterval(intv);
      clearInterval(changelogIntv);
    };
  }, [fetchChangelog, fetchStatus, hover, loaded, open]);

  useEffect(() => {
    if (open) fetchChangelog();
  }, [open, fetchChangelog]);

  useEffect(() => {
    const onOpenUpdateCenter = () => setOpen(true);
    window.addEventListener('open-update-center', onOpenUpdateCenter);
    return () => window.removeEventListener('open-update-center', onOpenUpdateCenter);
  }, []);

  const latestUpdate = useMemo(() => {
    if (!status) {
      return null;
    }
    const entry = changelog?.[0];
    if (entry) return entry;
    return {
      version: status.version,
      title: 'Platform Status',
      date: status.date,
      status: status.status,
      features: status.features || [],
    };
  }, [changelog, status]);

  const statusCounts = useMemo(() => {
    const features = status?.features || [];
    return {
      verified: features.filter(f => f.status.includes('Verified')).length,
      pending: features.filter(f => f.status.includes('Pending')).length,
      failed: features.filter(f => f.status.includes('Failed')).length,
      total: features.length,
    };
  }, [status]);

  if (!status) return null;

  const updateTime = lastSyncedAt
    ? new Date(lastSyncedAt).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
    : latestUpdate?.date
      ? new Date(latestUpdate.date).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
      : 'Never';
  const compactSummary = latestUpdate?.features?.length
    ? `${latestUpdate.features.slice(0, 2).map(f => f.name).join(' • ')}${latestUpdate.features.length > 2 ? ` +${latestUpdate.features.length - 2} more` : ''}`
    : 'No detailed updates available yet';
  const briefHeadline = latestUpdate?.title || 'No Data Available';
  const simpleStatus = String(status.status || '').toLowerCase().includes('verified')
    ? 'Ready'
    : String(status.status || '').toLowerCase().includes('pending')
      ? 'Waiting'
      : String(status.status || '').toLowerCase().includes('failed')
        ? 'Needs attention'
        : 'Updated';
  const currentLocalChanges = [
    'Sidebar now shows the latest update badge.',
    'A review panel is now available from Admin Ops.',
    'Phone numbers are normalized safely before save.',
    'Update and review screens now open from clear buttons.',
  ];
  const localRefreshLabel = lastSyncedAt
    ? new Date(lastSyncedAt).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
    : 'Not refreshed yet';

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
        <div style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
        }}>
          {hover && (
            <div style={{
              position: 'absolute',
              bottom: '100%',
              right: 0,
              marginBottom: 12,
              background: 'var(--panel-bg)',
              border: '1px solid var(--card-border)',
              padding: '12px 14px',
              borderRadius: 12,
              boxShadow: 'var(--shadow-lg)',
              fontSize: 12,
              animation: 'fadeUp 0.2s ease',
              color: 'var(--text-secondary)',
              minWidth: 280,
              maxWidth: 320,
              zIndex: 100,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 6, alignItems: 'baseline' }}>
                <span style={{ fontWeight: 800, color: 'var(--text-primary)' }}>Latest Update</span>
                <span style={{ color, fontWeight: 700 }}>{status.version}</span>
              </div>
              <div style={{ fontSize: 12.5, color: 'var(--text-primary)', fontWeight: 700, lineHeight: 1.35 }}>
                {briefHeadline}
              </div>
              <div style={{ marginTop: 4, fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.45 }}>
                {compactSummary}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, marginTop: 10 }}>
                <span>Updated:</span>
                <span style={{ color: 'var(--text-primary)', textAlign: 'right' }}>{updateTime}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, marginTop: 4 }}>
                <span>Status:</span>
                <strong style={{ color, textAlign: 'right' }}>{status.status}</strong>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                <span className="badge badge-blue">Verified {statusCounts.verified}</span>
                <span className="badge badge-amber">Pending {statusCounts.pending}</span>
                <span className="badge badge-red">Failed {statusCounts.failed}</span>
              </div>
            </div>
          )}

          <button
            onClick={() => setOpen(true)}
            aria-label="Open update center"
            title="Open update center"
            style={{
              width: 50,
              height: 50,
              borderRadius: 16,
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
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Updates</h2>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Simple summary of what changed</div>
              </div>
              <button onClick={() => setOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 20 }}>
                <i className="ti ti-x" />
              </button>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 16, padding: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>Current local changes</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 10 }}>What is new right now</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>Last refreshed: {localRefreshLabel}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {currentLocalChanges.map((item) => (
                    <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
                      <i className="ti ti-check" style={{ color: '#22c55e', flexShrink: 0 }} />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 16, padding: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>What changed</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.25 }}>{briefHeadline}</div>
                <div style={{ marginTop: 6, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                  {compactSummary}
                </div>
                <div style={{ marginTop: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <span className="badge badge-blue">{status.version}</span>
                  <span className="badge badge-gray">{updateTime}</span>
                  <span className="badge badge-green">{simpleStatus}</span>
                </div>
              </div>
              
              {/* Current Status Card */}
              <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 16, padding: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>Simple update summary</div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Version</div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)' }}>{status.version}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Last refreshed</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {updateTime}
                    </div>
                  </div>
                </div>
                
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--card-border)' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>What this means</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 4, background: color, boxShadow: `0 0 8px ${color}` }} />
                    <strong style={{ color }}>{simpleStatus}</strong>
                  </div>
                </div>
              </div>
              
              {/* Changelog */}
              <div>
                <h3 style={{ margin: '0 0 16px 0', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>What changed in each update</h3>
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

              <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 16, padding: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>Quick take</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 10 }}>Here’s the short version</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {(latestUpdate?.features?.length ? latestUpdate.features.slice(0, 4).map((f) => String(f?.name || '').replace(/\bindexing\b/gi, 'search speed').replace(/\boptimization\b/gi, 'speed').replace(/\bpagination\b/gi, 'loading')) : ['Small platform update recorded.']).map((item, index) => (
                    <div key={`${index}-${item}`} style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)', fontSize: 13 }}>
                      <i className="ti ti-check" style={{ color: '#22c55e', flexShrink: 0 }} />
                      <span>{item || 'A small change was made.'}</span>
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
