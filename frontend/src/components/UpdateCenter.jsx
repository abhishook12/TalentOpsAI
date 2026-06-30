import React, { useState, useEffect, useMemo, useCallback } from 'react';
import api from '../services/api';

export default function UpdateCenter() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [changelog, setChangelog] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);
  const fallbackStatus = useMemo(() => ({
    version: 'v4.0-local',
    date: new Date().toISOString(),
    status: 'Local Preview',
    features: [
      { id: 1, name: 'Duplicate review preview available', status: 'Verified' },
      { id: 2, name: 'One person, one entry rule shown', status: 'Verified' },
      { id: 3, name: 'Canonical copy kept for duplicates', status: 'Verified' },
      { id: 4, name: 'Backend fallback still visible on localhost', status: 'Pending Verification' },
    ],
  }), []);

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
    if (!open) return undefined;

    if (!loaded) {
      fetchStatus();
      fetchChangelog();
    }

    const intv = setInterval(fetchStatus, 300000);
    const changelogIntv = setInterval(fetchChangelog, 600000);
    return () => {
      clearInterval(intv);
      clearInterval(changelogIntv);
    };
  }, [open, loaded, fetchStatus, fetchChangelog]);

  useEffect(() => {
    const handleToggle = () => setOpen(o => !o);
    window.addEventListener('toggle-update-center', handleToggle);
    return () => window.removeEventListener('toggle-update-center', handleToggle);
  }, []);

  const activeStatus = status || fallbackStatus;

  const latestUpdate = useMemo(() => {
    if (!activeStatus) {
      return null;
    }
    const entry = changelog?.[0];
    if (entry) return entry;
    return {
      version: activeStatus.version,
      title: 'Platform Status',
      date: activeStatus.date,
      status: activeStatus.status,
      features: activeStatus.features || [],
    };
  }, [activeStatus, changelog]);

  const statusCounts = useMemo(() => {
    const features = status?.features || [];
    return {
      verified: features.filter(f => f.status.includes('Verified')).length,
      pending: features.filter(f => f.status.includes('Pending')).length,
      failed: features.filter(f => f.status.includes('Failed')).length,
      total: features.length,
    };
  }, [activeStatus]);

  const updateTime = lastSyncedAt
    ? new Date(lastSyncedAt).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
    : latestUpdate?.date
      ? new Date(latestUpdate.date).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
      : 'Never';
  const compactSummary = latestUpdate?.features?.length
    ? `${latestUpdate.features.slice(0, 2).map(f => f.name).join(' • ')}${latestUpdate.features.length > 2 ? ` +${latestUpdate.features.length - 2} more` : ''}`
    : 'No detailed updates available yet';
  const briefHeadline = latestUpdate?.title || 'Local duplicate review preview';
  const simpleStatus = String(activeStatus.status || '').toLowerCase().includes('verified')
    ? 'Ready'
    : String(activeStatus.status || '').toLowerCase().includes('pending')
      ? 'Waiting'
      : String(activeStatus.status || '').toLowerCase().includes('failed')
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
  
  if (activeStatus.status === 'Verified & Operational' || activeStatus.status === 'Verified') {
    color = '#22c55e'; // Green
    icon = 'ti-check';
  } else if (activeStatus.status === 'Pending Verification') {
    color = '#fbbf24'; // Yellow
    icon = 'ti-alert-triangle';
  } else if (activeStatus.status === 'Failed Verification') {
    color = '#ef4444'; // Red
    icon = 'ti-x';
  }

  return (
    <>
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
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>Duplicate review preview</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 8 }}>One person, one entry</div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  This localhost preview shows the duplicate rule set without touching the live database.
                  Exact email and phone matches are merged into one canonical entry, while weaker matches stay flagged for review.
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 14 }}>
                  <div style={{ padding: 12, borderRadius: 14, background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.18)' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Auto-merge</div>
                    <div style={{ fontSize: 20, fontWeight: 900, color: '#22c55e', marginTop: 4 }}>Exact</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>Same email or same phone</div>
                  </div>
                  <div style={{ padding: 12, borderRadius: 14, background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.18)' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Review</div>
                    <div style={{ fontSize: 20, fontWeight: 900, color: '#fbbf24', marginTop: 4 }}>Safe</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>Same name + company, inspect first</div>
                  </div>
                </div>
              </div>

              <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 16, padding: 20 }}>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>What changed</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.25 }}>{briefHeadline}</div>
                <div style={{ marginTop: 6, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                  {compactSummary}
                </div>
                <div style={{ marginTop: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <span className="badge badge-blue">{activeStatus.version}</span>
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
                    <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)' }}>{activeStatus.version}</div>
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
                  {(latestUpdate?.features?.length ? latestUpdate.features.slice(0, 4).map((f) => String(f?.name || '').replace(/\bindexing\b/gi, 'search speed').replace(/\boptimization\b/gi, 'speed').replace(/\bpagination\b/gi, 'loading')) : ['Local duplicate review preview is available.']).map((item, index) => (
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
