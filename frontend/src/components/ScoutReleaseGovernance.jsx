import React, { useState, useEffect } from 'react';
import {
  ShieldCheck, AlertTriangle, Play, Pause, RotateCcw, CheckCircle2,
  Sliders, Settings, RefreshCw, Cpu, Layers, Award, Terminal, ArrowRight,
  ExternalLink, Sparkles, Check, Lock, Laptop
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';

export default function ScoutReleaseGovernance({ onReleaseChanged }) {
  const [releases, setReleases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [remoteConfig, setRemoteConfig] = useState(null);
  const [configSaving, setConfigSaving] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  // 7-Point Safety Checklist
  const [checklist, setChecklist] = useState({
    tests_passed: true,
    security_verified: true,
    signing_verified: true,
    installer_verified: true,
    migration_verified: true,
    rollback_tested: true,
    compatibility_verified: true,
  });
  const [targetRollout, setTargetRollout] = useState(100);
  const [targetMinVersion, setTargetMinVersion] = useState('');
  const [approving, setApproving] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);

  // Fetch Releases & Remote Config
  const fetchData = async () => {
    setLoading(true);
    try {
      const [relRes, cfgRes] = await Promise.all([
        api.get('/scout/releases'),
        api.get('/scout/config'),
      ]);
      setReleases(relRes.data || []);
      setRemoteConfig(cfgRes.data || {});

      // Check if there is a candidate awaiting approval
      const candidate = (relRes.data || []).find(r => !r.is_current && r.status !== 'ROLLED_BACK');
      if (candidate) {
        setSelectedCandidate(candidate);
        setTargetMinVersion(candidate.minimum_version || '1.0.0');
      }
    } catch (err) {
      console.error('Failed to load release governance data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const currentProduction = releases.find(r => r.is_current) || releases[0] || {};

  // Approve Production Release
  const handleApproveProduction = async () => {
    if (!selectedCandidate) return;
    setApproving(true);
    try {
      const res = await api.post(`/scout/releases/${selectedCandidate.version}/approve-production`, {
        checklist,
        rollout_percentage: targetRollout,
        set_minimum_version: targetMinVersion || undefined,
      });
      if (res.data?.status === 'APPROVED') {
        toast.success(`🎉 Scout v${selectedCandidate.version} is now LIVE in Production! All surfaces synchronized.`);
        await fetchData();
        if (onReleaseChanged) onReleaseChanged();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve production release');
    } finally {
      setApproving(false);
    }
  };

  // Rollback Release
  const handleRollback = async (version) => {
    if (!window.confirm(`Are you sure you want to rollback v${version}? This will pause distribution and restore previous stable version.`)) {
      return;
    }
    setRollingBack(true);
    try {
      const res = await api.post(`/scout/releases/${version}/rollback`, {
        reason: 'Manual rollback triggered from Governance Dashboard'
      });
      toast.success(`🚨 Rolled back v${version}. Restored v${res.data?.restored_version} as canonical production.`);
      await fetchData();
      if (onReleaseChanged) onReleaseChanged();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Rollback failed');
    } finally {
      setRollingBack(false);
    }
  };

  // Adjust Rollout Percentage
  const handleAdjustRollout = async (version, pct) => {
    try {
      await api.post(`/scout/releases/${version}/rollout`, { rollout_percentage: pct });
      toast.success(`Rollout cohort updated to ${pct}% for v${version}`);
      await fetchData();
    } catch (err) {
      toast.error('Failed to update rollout percentage');
    }
  };

  // Toggle Pause
  const handleTogglePause = async (version, currentlyPaused) => {
    try {
      await api.post(`/scout/releases/${version}/rollout`, { is_paused: !currentlyPaused });
      toast.success(currentlyPaused ? `Resumed rollout for v${version}` : `Paused rollout for v${version}`);
      await fetchData();
    } catch (err) {
      toast.error('Failed to update rollout pause state');
    }
  };

  // Save Remote Config (Type 3 Changes)
  const handleSaveRemoteConfig = async () => {
    if (!remoteConfig) return;
    setConfigSaving(true);
    try {
      await api.put('/scout/config', {
        config_key: 'global',
        channel: 'stable',
        features: remoteConfig.features,
        config: remoteConfig.config,
      });
      toast.success('Remote configuration saved! Fleet will sync parameters on next heartbeat.');
      await fetchData();
    } catch (err) {
      toast.error('Failed to save remote configuration');
    } finally {
      setConfigSaving(false);
    }
  };

  if (loading && !releases.length) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>
        <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px' }} />
        <div>Loading Scout Release &amp; Rollout Governance...</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* ── TOP HERO: CANONICAL PRODUCTION RELEASE STATUS ───────────────────── */}
      <div style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
        border: '1px solid #3b82f6',
        borderRadius: 12,
        padding: '20px 24px',
        boxShadow: '0 4px 20px rgba(59, 130, 246, 0.15)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 14 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{
                background: '#10b981', color: '#042f2e', fontSize: 10, fontWeight: 900,
                padding: '2px 8px', borderRadius: 4, letterSpacing: '0.5px'
              }}>
                SINGLE SOURCE OF TRUTH
              </span>
              <span style={{ color: '#94a3b8', fontSize: 12 }}>
                Canonical Production Release: <b style={{ color: '#f8fafc', fontSize: 14 }}>v{currentProduction.version || '2.7.0'}</b>
              </span>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', margin: '0 0 6px' }}>
              Platform-Wide Production Synchronization
            </h2>
            <p style={{ color: '#94a3b8', fontSize: 12, margin: 0, maxWidth: 680 }}>
              Website downloads (<code>/scout/updates/download/latest</code>), manifest (<code>/scout/updates/manifest</code>),
              release registry, and fleet auto-updaters are all bound dynamically to this single record.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{
              background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8, padding: '8px 14px', textAlign: 'right'
            }}>
              <div style={{ fontSize: 10, color: '#94a3b8' }}>ROLLOUT PROGRESS</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: currentProduction.is_paused ? '#ef4444' : '#38bdf8' }}>
                {currentProduction.is_paused ? 'PAUSED' : `${currentProduction.rollout_percentage || 100}% FLEET`}
              </div>
            </div>

            <div style={{
              background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8, padding: '8px 14px', textAlign: 'right'
            }}>
              <div style={{ fontSize: 10, color: '#94a3b8' }}>MINIMUM FLOOR</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: '#f59e0b' }}>
                v{currentProduction.minimum_version || '1.0.0'}
              </div>
            </div>

            {currentProduction.version && (
              <button
                onClick={() => handleRollback(currentProduction.version)}
                disabled={rollingBack}
                style={{
                  padding: '8px 14px', background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid #ef4444', color: '#fca5a5', borderRadius: 8,
                  fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
                }}
              >
                <RotateCcw size={14} />
                <span>Emergency Rollback</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── SECTION 2: PRODUCTION RELEASE APPROVAL GATE ──────────────────────── */}
      <div style={{
        background: '#0d131f', border: '1px solid #1e293b', borderRadius: 12, padding: 20
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc', margin: '0 0 4px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <ShieldCheck size={18} color="#10b981" />
              <span>Production Release Approval Gate</span>
            </h3>
            <p style={{ color: '#94a3b8', fontSize: 12, margin: 0 }}>
              Verify safety checklist and formally promote release candidates to active production distribution.
            </p>
          </div>

          {selectedCandidate ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, color: '#94a3b8' }}>Target Candidate:</span>
              <span style={{ background: '#3b82f6', color: '#fff', padding: '3px 10px', borderRadius: 6, fontWeight: 800, fontSize: 13 }}>
                v{selectedCandidate.version}
              </span>
            </div>
          ) : (
            <span style={{ fontSize: 12, color: '#64748b' }}>No pending release candidates</span>
          )}
        </div>

        {selectedCandidate ? (
          <div style={{
            background: '#131c2e', border: '1px solid #1e293b', borderRadius: 10, padding: 18,
            display: 'flex', flexDirection: 'column', gap: 16
          }}>
            {/* Checklist items */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 }}>
              {[
                { key: 'tests_passed', label: '1. Automated Tests Passed (100%)' },
                { key: 'security_verified', label: '2. Cryptographic Security & Zero Passwords' },
                { key: 'signing_verified', label: '3. Authenticode Code-Signed & SHA-256' },
                { key: 'installer_verified', label: '4. Inno Setup & Protocol Handlers' },
                { key: 'migration_verified', label: '5. Schema Migration Verified' },
                { key: 'rollback_tested', label: '6. Snapshot Rollback Tested' },
                { key: 'compatibility_verified', label: '7. API Backward Compatibility' },
              ].map(item => (
                <label
                  key={item.key}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8, fontSize: 12,
                    color: checklist[item.key] ? '#f8fafc' : '#94a3b8', cursor: 'pointer',
                    background: checklist[item.key] ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255,255,255,0.02)',
                    padding: '8px 12px', borderRadius: 6, border: `1px solid ${checklist[item.key] ? '#10b981' : '#334155'}`
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checklist[item.key]}
                    onChange={(e) => setChecklist(prev => ({ ...prev, [item.key]: e.target.checked }))}
                    style={{ accentColor: '#10b981', cursor: 'pointer' }}
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>

            {/* Controls Strip: Rollout % and Min Version */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              flexWrap: 'wrap', gap: 14, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>INITIAL ROLLOUT COHORT</div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {[5, 25, 50, 100].map(pct => (
                      <button
                        key={pct}
                        onClick={() => setTargetRollout(pct)}
                        style={{
                          padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                          border: 'none', cursor: 'pointer',
                          background: targetRollout === pct ? '#3b82f6' : '#1e293b',
                          color: targetRollout === pct ? '#fff' : '#94a3b8'
                        }}
                      >
                        {pct}%
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>MINIMUM SUPPORTED VERSION</div>
                  <input
                    type="text"
                    value={targetMinVersion}
                    onChange={(e) => setTargetMinVersion(e.target.value)}
                    placeholder="e.g. 1.0.0"
                    style={{
                      padding: '4px 10px', background: '#090d16', border: '1px solid #334155',
                      borderRadius: 6, color: '#f8fafc', fontSize: 12, width: 90
                    }}
                  />
                </div>
              </div>

              <button
                onClick={handleApproveProduction}
                disabled={approving || Object.values(checklist).some(v => !v)}
                style={{
                  padding: '10px 24px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 800,
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                  boxShadow: '0 2px 12px rgba(16, 185, 129, 0.35)',
                  opacity: Object.values(checklist).some(v => !v) ? 0.5 : 1
                }}
              >
                <CheckCircle2 size={16} />
                <span>{approving ? 'Promoting...' : `[ Approve Production Release v${selectedCandidate.version} ]`}</span>
              </button>
            </div>
          </div>
        ) : (
          <div style={{ padding: 18, background: '#131c2e', borderRadius: 8, fontSize: 12, color: '#94a3b8' }}>
            Current production release (v{currentProduction.version}) is active and healthy. To release a new Scout version, commit code, build the signed installer, and publish via CI/CD.
          </div>
        )}
      </div>

      {/* ── SECTION 3: RELEASES REGISTRY & ROLLOUT CONTROLS ─────────────────── */}
      <div style={{
        background: '#0d131f', border: '1px solid #1e293b', borderRadius: 12, padding: 20
      }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sliders size={18} color="#38bdf8" />
          <span>Catalog of Published Releases across Channels</span>
        </h3>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #1e293b', color: '#64748b', textAlign: 'left' }}>
                <th style={{ padding: '10px 14px' }}>VERSION</th>
                <th style={{ padding: '10px 14px' }}>CHANNEL</th>
                <th style={{ padding: '10px 14px' }}>STATUS</th>
                <th style={{ padding: '10px 14px' }}>FLEET ROLLOUT</th>
                <th style={{ padding: '10px 14px' }}>ADOPTION</th>
                <th style={{ padding: '10px 14px' }}>FAILURE RATE</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {releases.map(rel => {
                const isCircuit = rel.status === 'CIRCUIT_TRIPPED';
                return (
                  <tr key={rel.id} style={{ borderBottom: '1px solid #131c2e' }}>
                    <td style={{ padding: '12px 14px', fontWeight: 700, color: '#f8fafc' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span>v{rel.version}</span>
                        {rel.is_current && (
                          <span style={{ background: '#10b981', color: '#042f2e', fontSize: 9, fontWeight: 800, padding: '1px 5px', borderRadius: 4 }}>
                            PROD
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>
                        Min: v{rel.minimum_version}
                      </div>
                    </td>

                    <td style={{ padding: '12px 14px', color: '#94a3b8' }}>
                      {rel.channel}
                    </td>

                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700,
                        background: isCircuit ? 'rgba(239, 68, 68, 0.15)' : (rel.is_paused ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)'),
                        color: isCircuit ? '#ef4444' : (rel.is_paused ? '#f59e0b' : '#34d399'),
                      }}>
                        {rel.status}
                      </span>
                    </td>

                    <td style={{ padding: '12px 14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 60, height: 6, background: '#1e293b', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ width: `${rel.rollout_percentage}%`, height: '100%', background: '#38bdf8' }} />
                        </div>
                        <span style={{ color: '#f8fafc', fontWeight: 600 }}>{rel.rollout_percentage}%</span>
                      </div>
                      <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                        {[5, 25, 50, 100].map(pct => (
                          <button
                            key={pct}
                            onClick={() => handleAdjustRollout(rel.version, pct)}
                            style={{
                              padding: '1px 5px', fontSize: 9, borderRadius: 3, border: '1px solid #334155',
                              background: rel.rollout_percentage === pct ? '#38bdf8' : 'transparent',
                              color: rel.rollout_percentage === pct ? '#090d16' : '#94a3b8',
                              cursor: 'pointer'
                            }}
                          >
                            {pct}%
                          </button>
                        ))}
                      </div>
                    </td>

                    <td style={{ padding: '12px 14px', color: '#94a3b8' }}>
                      <span style={{ color: '#f8fafc', fontWeight: 600 }}>{rel.adoption_percentage || 0}%</span>
                      <span style={{ fontSize: 10, color: '#64748b' }}> ({rel.device_count || 0} nodes)</span>
                    </td>

                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        color: (rel.failure_rate || 0) > 5 ? '#ef4444' : '#94a3b8',
                        fontWeight: (rel.failure_rate || 0) > 5 ? 700 : 400
                      }}>
                        {rel.failure_rate || 0}%
                      </span>
                    </td>

                    <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        <button
                          onClick={() => handleTogglePause(rel.version, rel.is_paused)}
                          style={{
                            padding: '4px 8px', background: '#1e293b', border: '1px solid #334155',
                            color: rel.is_paused ? '#34d399' : '#f59e0b', borderRadius: 4, fontSize: 10, fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          {rel.is_paused ? 'Resume' : 'Pause'}
                        </button>
                        {!rel.is_current && (
                          <button
                            onClick={() => setSelectedCandidate(rel)}
                            style={{
                              padding: '4px 8px', background: '#1e293b', border: '1px solid #3b82f6',
                              color: '#60a5fa', borderRadius: 4, fontSize: 10, fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            Set Candidate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── SECTION 4: CENTRALIZED REMOTE CONFIGURATION (TYPE 3 CHANGES) ───── */}
      <div style={{
        background: '#0d131f', border: '1px solid #1e293b', borderRadius: 12, padding: 20
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc', margin: '0 0 4px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Settings size={18} color="#a855f7" />
              <span>Remote Configuration &amp; Feature Flags (Type 3 Changes)</span>
            </h3>
            <p style={{ color: '#94a3b8', fontSize: 12, margin: 0 }}>
              Dynamically adjust Scout runtime parameters (batch sizes, sync intervals, feature toggles) across the fleet without binary updates.
            </p>
          </div>

          <button
            onClick={handleSaveRemoteConfig}
            disabled={configSaving}
            style={{
              padding: '8px 18px', background: '#a855f7', color: '#fff',
              border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 700,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
            }}
          >
            <Sparkles size={14} />
            <span>{configSaving ? 'Saving...' : 'Deploy Remote Config'}</span>
          </button>
        </div>

        {remoteConfig && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
            {/* Feature Flags */}
            <div style={{ background: '#131c2e', border: '1px solid #1e293b', borderRadius: 8, padding: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc', marginBottom: 10 }}>
                Feature Toggles
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {Object.entries(remoteConfig.features || {}).map(([featKey, val]) => (
                  <label key={featKey} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: '#94a3b8' }}>
                    <code>{featKey}</code>
                    <input
                      type="checkbox"
                      checked={Boolean(val)}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setRemoteConfig(prev => ({
                          ...prev,
                          features: { ...prev.features, [featKey]: checked }
                        }));
                      }}
                      style={{ accentColor: '#a855f7', cursor: 'pointer' }}
                    />
                  </label>
                ))}
              </div>
            </div>

            {/* Runtime Parameters */}
            <div style={{ background: '#131c2e', border: '1px solid #1e293b', borderRadius: 8, padding: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc', marginBottom: 10 }}>
                Runtime Parameters
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {Object.entries(remoteConfig.config || {}).map(([cfgKey, val]) => (
                  <div key={cfgKey} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                    <code style={{ color: '#94a3b8' }}>{cfgKey}</code>
                    <input
                      type="number"
                      value={val}
                      onChange={(e) => {
                        const num = Number(e.target.value);
                        setRemoteConfig(prev => ({
                          ...prev,
                          config: { ...prev.config, [cfgKey]: num }
                        }));
                      }}
                      style={{
                        padding: '3px 8px', background: '#090d16', border: '1px solid #334155',
                        borderRadius: 4, color: '#f8fafc', fontSize: 11, width: 80, textAlign: 'right'
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
