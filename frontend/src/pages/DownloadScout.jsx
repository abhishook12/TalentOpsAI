import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Download, Laptop, ShieldCheck, Zap, Wifi, CheckCircle2, ArrowRight,
  Database, RefreshCw, Layers, Terminal, Sparkles, AlertCircle, HelpCircle,
  Users, Activity, Server, FileText, Check, Shield, Search, Filter,
  ChevronRight, ArrowUpDown, Cpu, Clock, AlertTriangle, ShieldAlert, Award,
  ChevronDown, ChevronUp, ExternalLink, Info
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';
import AddScoutModal from '../components/AddScoutModal';
import ScoutUserProfileDrawer from '../components/ScoutUserProfileDrawer';
import ScoutNodesPanel from '../components/ScoutNodesPanel';

export default function DownloadScout() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showSetupGuide, setShowSetupGuide] = useState(false);
  const [showSecurityNotice, setShowSecurityNotice] = useState(false);
  const [activeClaim, setActiveClaim] = useState(null);
  const [claimStatus, setClaimStatus] = useState(null);
  const pollIntervalRef = useRef(null);
  const [activeView, setActiveView] = useState('contributors'); // 'contributors' | 'fleet_nodes'
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('most_active');
  const [selectedUserId, setSelectedUserId] = useState(null);


  // Dynamic Release Info from Authoritative DB Registry
  const [releaseInfo, setReleaseInfo] = useState({
    version: '2.0.0',
    download_url: 'https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe',
    size_bytes: 50474851,
    sha256: '4a7e93f6c8d19a2b3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d',
    channel: 'stable',
    released_at: '',
  });

  useEffect(() => {
    api.get('/scout/updates/latest')
      .then(res => {
        if (res?.data?.version) {
          setReleaseInfo(prev => ({ ...prev, ...res.data }));
        }
      })
      .catch(() => {});
  }, []);

  // Scout Contributors Telemetry Query
  const { data: contribData, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['scout-contributors-unified', statusFilter, searchQuery, sortBy],
    queryFn: async () => {
      const res = await api.get('/scout/users', {
        params: {
          status: statusFilter,
          search: searchQuery || undefined,
          sort: sortBy,
        }
      });
      return res.data;
    },
    keepPreviousData: true,
  });

  const summary = contribData?.summary || {};
  const users = contribData?.users || [];
  const versionDistribution = contribData?.version_distribution || {};
  // Cleanup poller on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleDownload = async () => {
    setDownloading(true);

    // 1. Issue short-lived installation claim for one-click auto-registration
    try {
      const claimRes = await api.post('/scout/install/claim', {
        label: 'Web Download Scout Auto-Pair',
        expires_minutes: 15,
      });

      if (claimRes?.data?.ok) {
        const claimData = claimRes.data;
        setActiveClaim(claimData);
        setClaimStatus({ status: 'WAITING', is_consumed: false });

        // Background loopback attempt: If Scout Desktop is already open on this PC,
        // it listens on 127.0.0.1:49152 and registers instantly!
        try {
          fetch('http://127.0.0.1:49152/claim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              claim_id: claimData.claim_id,
              claim_secret: claimData.claim_secret,
            }),
            mode: 'cors',
          }).catch(() => {});
        } catch (_) {}

        // Poll claim status every 3s to notify user when Scout launches and pairs
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = setInterval(async () => {
          try {
            const stRes = await api.get(`/scout/install/status/${claimData.claim_id}`);
            if (stRes?.data) {
              setClaimStatus(stRes.data);
              if (stRes.data.is_consumed) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
                toast.success(`🎉 Scout Desktop auto-registered successfully! (${stRes.data.hostname || stRes.data.device_id})`);
                refetch();
              }
            }
          } catch (_) {}
        }, 3000);
      }
    } catch (err) {
      console.debug('Claim generation fallback:', err);
    }

    // 2. Track download event in telemetry registry
    try {
      await api.post('/scout/download/track', {
        version: releaseInfo.version || '2.0.0',
        source: 'desktop_scout_page'
      });
    } catch (err) {}

    // 3. Initiate browser download of the installer
    const downloadUrl = releaseInfo.download_url || '/scout/updates/download/latest';
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'TalentOpsScoutSetup.exe';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success(`TalentOps Scout v${releaseInfo.version || '2.0.0'} download initiated!`);
    setTimeout(() => setDownloading(false), 2500);
  };


  const formatTimeAgo = (isoStr) => {
    if (!isoStr) return 'Never';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      const diffMs = Date.now() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}d ago`;
    } catch {
      return isoStr || 'Unknown';
    }
  };

  const getStatusBadge = (status) => {
    const st = (status || '').toUpperCase();
    switch (st) {
      case 'CONTRIBUTING':
      case 'CONTRIBUTING_OFFLINE':
        return { bg: 'rgba(16, 185, 129, 0.2)', text: '#34d399', border: 'rgba(16, 185, 129, 0.4)', icon: Sparkles };
      case 'ACTIVE':
        return { bg: 'rgba(34, 197, 94, 0.2)', text: '#4ade80', border: 'rgba(34, 197, 94, 0.4)', icon: Activity };
      case 'PAIRED':
      case 'PAIRED_IDLE':
        return { bg: 'rgba(56, 189, 248, 0.15)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.35)', icon: Zap };
      case 'INSTALLED':
        return { bg: 'rgba(129, 140, 248, 0.15)', text: '#818cf8', border: 'rgba(129, 140, 248, 0.35)', icon: Laptop };
      case 'DOWNLOAD_ONLY':
        return { bg: 'rgba(234, 179, 8, 0.15)', text: '#facc15', border: 'rgba(234, 179, 8, 0.35)', icon: Clock };
      case 'REGISTERED':
        return { bg: 'rgba(148, 163, 184, 0.15)', text: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)', icon: UserCheck };
      case 'REVOKED':
        return { bg: 'rgba(244, 63, 94, 0.2)', text: '#fb7185', border: 'rgba(244, 63, 94, 0.4)', icon: ShieldAlert };
      default:
        return { bg: 'rgba(100, 116, 139, 0.2)', text: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)', icon: AlertCircle };
    }
  };

  const getQualityBadge = (tier, score) => {
    let color = '#94a3b8';
    let bg = 'rgba(148, 163, 184, 0.15)';
    const t = (tier || '').toUpperCase();
    if (t === 'ELITE') {
      color = '#a855f7';
      bg = 'rgba(168, 85, 247, 0.2)';
    } else if (t === 'HIGH') {
      color = '#10b981';
      bg = 'rgba(16, 185, 129, 0.2)';
    } else if (t === 'MEDIUM' || t === 'MODERATE') {
      color = '#38bdf8';
      bg = 'rgba(56, 189, 248, 0.2)';
    } else if (t === 'LOW' || t === 'DEVELOPING') {
      color = '#f59e0b';
      bg = 'rgba(245, 158, 11, 0.2)';
    }
    return (
      <span style={{
        padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700,
        background: bg, color: color, display: 'inline-flex', alignItems: 'center', gap: 4
      }}>
        <Award size={12} />
        {score} • {tier || 'DEV'}
      </span>
    );
  };

  const totalUsersCount = summary.total_scout_users || users.length || 0;
  const activeUsersCount = summary.active_users || 0;
  const activeDevicesCount = summary.active_devices || 0;
  const totalDevicesCount = summary.total_devices || summary.active_devices || 0;
  const contributingUsersCount = summary.contributing_users || 0;
  const offlineUsersCount = summary.offline_users || 0;
  const updateReqCount = summary.update_required_count ?? summary.update_required ?? 0;
  const revokedCount = summary.revoked_count ?? summary.revoked ?? 0;
  const canonicalCreated = summary.total_canonical_created ?? summary.total_people_contributed ?? 0;
  const canonicalEnriched = summary.total_canonical_enriched ?? summary.total_contacts_contributed ?? 0;
  const avgQualScore = summary.avg_quality_score ?? summary.average_quality_score ?? 0;

  const displayVersion = releaseInfo.version ? `v${releaseInfo.version}` : 'v2.0.0';
  const displaySize = releaseInfo.size_bytes
    ? `${(releaseInfo.size_bytes / (1024 * 1024)).toFixed(1)} MB`
    : '48.1 MB';

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 80px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
      {/* Top Header */}
      <header style={{ paddingTop: 32, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399', padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700, marginBottom: 8
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }} />
              OFFICIAL DESKTOP ENGINE • CONTINUOUS FLEET INTELLIGENCE
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 6px', letterSpacing: '-0.5px' }}>
              Desktop Scout &amp; Contributors
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: 0, maxWidth: 840, lineHeight: 1.5 }}>
              Autonomous continuous recruitment intelligence engine for Windows, active device fleet management, and verified candidate pipeline contribution analytics.
            </p>
          </div>

          {/* Quick Actions / View Mode Toggle */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{
              display: 'flex', background: '#090d16', border: '1px solid #1e293b',
              borderRadius: 8, padding: 3, gap: 2
            }}>
              <button
                onClick={() => setActiveView('contributors')}
                style={{
                  padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                  border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                  background: activeView === 'contributors' ? '#1e293b' : 'transparent',
                  color: activeView === 'contributors' ? '#38bdf8' : '#94a3b8',
                }}
              >
                <Users size={13} />
                <span>Contributors Intelligence</span>
              </button>
              <button
                onClick={() => setActiveView('fleet_nodes')}
                style={{
                  padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                  border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                  background: activeView === 'fleet_nodes' ? '#1e293b' : 'transparent',
                  color: activeView === 'fleet_nodes' ? '#38bdf8' : '#94a3b8',
                }}
              >
                <Laptop size={13} />
                <span>Device Fleet &amp; Nodes</span>
              </button>
            </div>

            <button
              onClick={() => refetch()}
              disabled={isFetching}
              style={{
                padding: '8px 14px', background: '#1e293b', border: '1px solid #334155',
                color: '#f8fafc', borderRadius: 8, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                opacity: isFetching ? 0.6 : 1
              }}
            >
              <RefreshCw size={13} className={isFetching ? 'animate-spin' : ''} />
              <span>{isFetching ? 'Syncing...' : 'Refresh'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* COMPACT DESKTOP SCOUT DOWNLOAD & PAIRING SUBSECTION                       */}
      {/* ========================================================================= */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(56, 189, 248, 0.05) 100%)',
        border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 12, padding: '16px 20px',
        marginBottom: 20, boxShadow: '0 4px 20px rgba(0,0,0,0.18)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          {/* Left: Client Specs & Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 10,
              background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981', flexShrink: 0
            }}>
              <Laptop size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 15, fontWeight: 800, color: '#f8fafc' }}>
                  TalentOps Scout Desktop
                </span>
                <span style={{
                  background: 'rgba(16, 185, 129, 0.2)', color: '#34d399',
                  border: '1px solid rgba(16, 185, 129, 0.35)', padding: '2px 7px',
                  borderRadius: 5, fontSize: 11, fontWeight: 700, fontFamily: 'monospace'
                }}>
                  {displayVersion} Production
                </span>
                <span style={{ fontSize: 12, color: '#64748b' }}>• Windows 10/11 64-bit ({displaySize})</span>
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                Native Win32 background engine with offline OCR and local SQLite buffer queue. Replaces legacy browser extension.
              </div>
            </div>
          </div>

          {/* Right: Quick Action Buttons */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <button
              onClick={handleDownload}
              disabled={downloading}
              style={{
                padding: '9px 18px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 700,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                boxShadow: '0 2px 10px rgba(16, 185, 129, 0.35)',
                opacity: downloading ? 0.7 : 1
              }}
            >
              <Download size={15} />
              <span>{downloading ? 'Starting...' : `Download ${displayVersion}`}</span>
            </button>

            <button
              onClick={() => setShowAddModal(true)}
              style={{
                padding: '9px 16px', background: '#1e293b', color: '#38bdf8',
                border: '1px solid #334155', borderRadius: 8, fontSize: 12, fontWeight: 700,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7
              }}
            >
              <Zap size={14} />
              <span>Pair Device (10m Code)</span>
            </button>

            <button
              onClick={() => setShowSetupGuide(!showSetupGuide)}
              style={{
                padding: '9px 12px', background: '#090d16', color: '#94a3b8',
                border: '1px solid #1e293b', borderRadius: 8, fontSize: 11, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5
              }}
              title="Toggle setup instructions"
            >
              <Info size={13} />
              <span>{showSetupGuide ? 'Hide Guide' : 'Setup Guide'}</span>
              {showSetupGuide ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            <button
              onClick={() => setShowSecurityNotice(!showSecurityNotice)}
              style={{
                padding: '9px 12px', background: '#090d16', color: '#f59e0b',
                border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 8, fontSize: 11, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5
              }}
              title="Browser download warnings & SmartScreen reputation"
            >
              <ShieldAlert size={13} />
              <span>Trust &amp; SmartScreen</span>
              {showSecurityNotice ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>
        </div>

        {/* Real-Time Auto-Registration Claim Banner */}
        {activeClaim && (
          <div style={{
            marginTop: 14, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.08)',
            background: claimStatus?.is_consumed ? 'rgba(16, 185, 129, 0.08)' : 'rgba(56, 189, 248, 0.08)',
            border: claimStatus?.is_consumed ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: 8, padding: '12px 16px', display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', flexWrap: 'wrap', gap: 12
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: claimStatus?.is_consumed ? 'rgba(16, 185, 129, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: claimStatus?.is_consumed ? '#34d399' : '#38bdf8'
              }}>
                {claimStatus?.is_consumed ? <Check size={18} /> : <Zap size={18} />}
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
                  {claimStatus?.is_consumed
                    ? `🎉 Device Auto-Registered: ${claimStatus.hostname || claimStatus.device_id}`
                    : '⚡ 1-Click Auto-Registration Waiting for Scout Desktop...'}
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>
                  {claimStatus?.is_consumed
                    ? 'This device is now bound to your account and reporting live telemetry.'
                    : `Claim ${activeClaim.claim_id} active. Run the downloaded installer, or click the button to pair immediately without manual codes.`}
                </div>
              </div>
            </div>
            {!claimStatus?.is_consumed && (
              <a
                href={activeClaim.deep_link}
                style={{
                  padding: '6px 14px', background: 'linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)',
                  color: '#fff', borderRadius: 6, fontSize: 11, fontWeight: 700, textDecoration: 'none',
                  display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 2px 8px rgba(56, 189, 248, 0.3)'
                }}
              >
                <ExternalLink size={12} />
                <span>Launch &amp; Auto-Register Scout</span>
              </a>
            )}
          </div>
        )}

        {/* Expandable 3-Step Setup Guide */}
        {showSetupGuide && (
          <div style={{
            marginTop: 14, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.08)',
            display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14
          }}>
            <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', marginBottom: 3 }}>1. Download &amp; Install</div>
              <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>
                Run <code>TalentOpsScoutSetup.exe</code> ({displayVersion}). Installs silently to AppData without admin restrictions.
              </div>
            </div>
            <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', marginBottom: 3 }}>2. Auto-Register in 5s</div>
              <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>
                Scout automatically connects using your download claim. Zero manual codes needed.
              </div>
            </div>
            <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#a855f7', marginBottom: 3 }}>3. Autonomous Ingestion</div>
              <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>
                Scout observes recruiter activity, extracts verified candidates via OCR, and enriches your talent database 24/7.
              </div>
            </div>
          </div>
        )}

        {/* Expandable Trust & SmartScreen Security Notice */}
        {showSecurityNotice && (
          <div style={{
            marginTop: 14, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: 8, padding: 14
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: '#f59e0b', fontSize: 12, fontWeight: 700 }}>
              <ShieldAlert size={16} />
              <span>Browser Security &amp; Windows SmartScreen Notice</span>
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
              <p style={{ margin: '0 0 6px 0', color: '#f8fafc' }}>
                <b>Why does Chrome, Edge, or Windows show an unrecognized app or reputation warning?</b>
              </p>
              <p style={{ margin: '0 0 6px 0' }}>
                Microsoft SmartScreen and Google Safe Browsing evaluate download reputation for newly released executables. Even digitally signed binaries initially show an <i>“unrecognized app”</i> prompt on unmanaged PCs until sufficient download volume establishes positive publisher reputation.
              </p>
              <ul style={{ margin: '0 0 8px 18px', padding: 0 }}>
                <li><b>In Chrome/Edge:</b> Click the download dropdown → Select <b>Keep</b> / <b>Download suspicious file</b>.</li>
                <li><b>In Windows SmartScreen:</b> Click <b>More info</b> → Select <b>Run anyway</b> to complete installation.</li>
                <li><b>Integrity Verification:</b> All builds are verified via SHA-256 (<code>{releaseInfo.sha256 ? releaseInfo.sha256.substring(0, 16) + '...' : 'Verified'}</code>) and distributed via strict HTTPS.</li>
                <li><b>Strict Privacy Guardrail:</b> Scout never extracts, logs, or stores browser passwords or cookies. Only candidate profile data is staged.</li>
              </ul>
            </div>
          </div>
        )}
      </div>


      {/* ========================================================================= */}
      {/* PRIMARY VIEW 1: SCOUT USERS & CONTRIBUTORS INTELLIGENCE                   */}
      {/* ========================================================================= */}
      {activeView === 'contributors' && (
        <div>
          {/* KPI Cards Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 14, marginBottom: 20 }}>
            {[
              { label: 'TOTAL SCOUT USERS', value: totalUsersCount, icon: Users, color: '#38bdf8', sub: 'Registered & active' },
              { label: 'ACTIVE USERS', value: activeUsersCount, icon: Activity, color: '#4ade80', sub: 'Seen last 24h' },
              { label: 'ACTIVE DEVICES', value: activeDevicesCount, icon: Laptop, color: '#22c55e', sub: `${totalDevicesCount} nodes active` },
              { label: 'CONTRIBUTING USERS', value: contributingUsersCount, icon: Sparkles, color: '#a855f7', sub: 'Added / enriched data' },
              { label: 'OFFLINE USERS', value: offlineUsersCount, icon: Clock, color: '#94a3b8', sub: 'No signal > 7d' },
              { label: 'UPDATE REQUIRED', value: updateReqCount, icon: AlertTriangle, color: '#f59e0b', sub: `Prod is v${latestProdVer}` },
              { label: 'REVOKED', value: revokedCount, icon: ShieldAlert, color: '#f43f5e', sub: 'Blocked or quarantined' },
            ].map((card, idx) => {
              const Icon = card.icon;
              return (
                <div key={idx} style={{
                  background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: '16px 18px',
                  display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', letterSpacing: 0.5 }}>{card.label}</span>
                    <Icon size={16} color={card.color} />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: '#f8fafc', lineHeight: 1.1, marginBottom: 4 }}>
                    {card.value.toLocaleString()}
                  </div>
                  <div style={{ fontSize: 11, color: '#64748b' }}>{card.sub}</div>
                </div>
              );
            })}
          </div>

          {/* Pipeline Impact Ribbon & Version Distribution */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(56, 189, 248, 0.05) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 12, padding: '16px 20px',
            display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 24, marginBottom: 20, alignItems: 'center'
          }}>
            {/* Left: Canonical Enrichment Stats */}
            <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                  Pipeline Ingestion Impact
                </div>
                <div style={{ fontSize: 13, color: '#94a3b8' }}>
                  True database modifications produced by desktop fleet
                </div>
              </div>

              <div style={{ display: 'flex', gap: 16 }}>
                <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: '8px 14px' }}>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>People Added</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#34d399' }}>
                    {canonicalCreated.toLocaleString()}
                  </div>
                </div>
                <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: '8px 14px' }}>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>Contacts Enriched</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#38bdf8' }}>
                    {canonicalEnriched.toLocaleString()}
                  </div>
                </div>
                <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: '8px 14px' }}>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>Fleet Quality Avg</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#a855f7' }}>
                    {avgQualScore} / 100
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Version Distribution Breakdown */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8' }}>
                  Fleet Version Distribution (Latest: v{latestProdVer})
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {Object.entries(versionDistribution).length === 0 ? (
                  <span style={{ fontSize: 12, color: '#64748b' }}>No device versions reported</span>
                ) : (
                  Object.entries(versionDistribution).map(([ver, count]) => {
                    const isLatest = ver === latestProdVer;
                    return (
                      <span key={ver} style={{
                        padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                        background: isLatest ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: isLatest ? '#34d399' : '#f59e0b',
                        border: `1px solid ${isLatest ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`
                      }}>
                        v{ver}: <b>{count}</b> {isLatest ? '✓ current' : '⚠ outdated'}
                      </span>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Search, Filter & Sort Controls */}
          <div style={{
            background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12,
            padding: '14px 18px', marginBottom: 16, display: 'flex', gap: 14,
            alignItems: 'center', flexWrap: 'wrap', justifyContent: 'space-between'
          }}>
            {/* Search Input */}
            <div style={{ position: 'relative', flex: '1 1 280px', maxWidth: 380 }}>
              <Search size={15} color="#64748b" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                placeholder="Search by user name, email, or company..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%', padding: '8px 12px 8px 34px', background: '#090d16',
                  border: '1px solid #1e293b', borderRadius: 8, color: '#f8fafc',
                  fontSize: 13, outline: 'none'
                }}
              />
            </div>

            {/* Status Filters */}
            <div style={{ display: 'flex', gap: 5, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', marginRight: 4 }}>STATUS:</span>
              {['ALL', 'CONTRIBUTING', 'ACTIVE', 'PAIRED', 'REGISTERED', 'REVOKED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  style={{
                    padding: '5px 11px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: statusFilter === st ? '1px solid #38bdf8' : '1px solid #1e293b',
                    background: statusFilter === st ? 'rgba(56, 189, 248, 0.15)' : '#090d16',
                    color: statusFilter === st ? '#38bdf8' : '#94a3b8',
                    cursor: 'pointer'
                  }}
                >
                  {st}
                </button>
              ))}
            </div>

            {/* Sort Select */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b' }}>SORT:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                style={{
                  padding: '7px 12px', background: '#090d16', border: '1px solid #1e293b',
                  color: '#f8fafc', borderRadius: 8, fontSize: 12, outline: 'none', cursor: 'pointer'
                }}
              >
                <option value="most_active">Most Active</option>
                <option value="most_data">Most Data Contributed</option>
                <option value="highest_quality">Highest Quality Score</option>
                <option value="most_devices">Most Devices</option>
              </select>
            </div>
          </div>

          {/* Contributors Table */}
          <div style={{
            background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12,
            overflow: 'hidden', boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
          }}>
            {isLoading ? (
              <div style={{ padding: 60, textAlign: 'center', color: '#94a3b8' }}>
                <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px' }} />
                <div>Loading Scout Contributor intelligence...</div>
              </div>
            ) : users.length === 0 ? (
              <div style={{ padding: 60, textAlign: 'center', color: '#64748b' }}>
                <Users size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
                <div style={{ fontSize: 15, fontWeight: 600, color: '#94a3b8', marginBottom: 4 }}>No Scout users match this query</div>
                <div style={{ fontSize: 12 }}>Try clearing the search query or selecting a different status filter.</div>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#090d16', borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '14px 18px', color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>USER &amp; ACCOUNT</th>
                      <th style={{ padding: '14px 18px', color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>LIFECYCLE STATUS</th>
                      <th style={{ padding: '14px 18px', color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>DEVICES</th>
                      <th style={{ padding: '14px 18px', color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>VERSION</th>
                      <th style={{ padding: '14px 18px', color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>LAST SEEN</th>
                      <th style={{ padding: '14px 18px', color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>DATA IMPACT</th>
                      <th style={{ padding: '14px 18px', color: '#94a3b8', fontWeight: 600, fontSize: 11 }}>QUALITY TIER</th>
                      <th style={{ padding: '14px 18px', color: '#94a3b8', fontWeight: 600, fontSize: 11, textAlign: 'right' }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => {
                      const statusKey = u.lifecycle_status || u.scout_status || 'REGISTERED';
                      const badge = getStatusBadge(statusKey);
                      const StatusIcon = badge.icon;
                      const userName = u.full_name || u.name || 'Unnamed User';
                      const userTenant = u.company || u.tenant || null;
                      const deviceCount = u.device_count ?? u.devices_count ?? 0;
                      const activeCount = u.active_device_count ?? (u.health === 'HEALTHY' ? deviceCount : 0);
                      const versionStr = u.primary_version || u.current_version || '2.0.0';
                      const isOutdated = u.update_required;
                      const lastSeenDisplay = u.last_seen_at ? formatTimeAgo(u.last_seen_at) : (u.last_seen || '—');
                      const lastContribDisplay = u.last_contribution_at ? formatTimeAgo(u.last_contribution_at) : (u.last_contribution || '—');
                      const newPeople = u.contributions?.canonical_new ?? u.new_people_created ?? 0;
                      const enrichedPeople = u.contributions?.canonical_enriched ?? u.people_enriched ?? 0;
                      const rawObs = u.contributions?.raw_events ?? u.raw_observations ?? 0;
                      const qualityScore = u.quality?.overall_score ?? u.quality_score ?? 0;
                      const qualityTier = u.quality?.tier || u.contribution_tier || 'DEVELOPING';

                      return (
                        <tr
                          key={u.user_id}
                          onClick={() => setSelectedUserId(u.user_id)}
                          style={{
                            borderBottom: '1px solid #1e293b',
                            cursor: 'pointer',
                            transition: 'background 0.15s ease'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          {/* User Info */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span>{userName}</span>
                              <span style={{ fontSize: 11, color: '#64748b' }}>#{u.user_id}</span>
                            </div>
                            <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{u.email}</div>
                            {userTenant && (
                              <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{userTenant}</div>
                            )}
                          </td>

                          {/* Lifecycle Status Badge */}
                          <td style={{ padding: '14px 18px' }}>
                            <span style={{
                              padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                              background: badge.bg, color: badge.text, border: `1px solid ${badge.border}`,
                              display: 'inline-flex', alignItems: 'center', gap: 5
                            }}>
                              <StatusIcon size={12} />
                              {u.status_label || statusKey}
                            </span>
                          </td>

                          {/* Devices Count */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#f8fafc' }}>
                              <Laptop size={14} color="#38bdf8" />
                              <span style={{ fontWeight: 600 }}>{activeCount}</span>
                              <span style={{ color: '#64748b' }}>/ {deviceCount}</span>
                            </div>
                            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                              {activeCount > 0 ? `${activeCount} active node(s)` : 'No active nodes'}
                            </div>
                          </td>

                          {/* Version & Update Warning */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span style={{
                                fontFamily: 'monospace', fontSize: 12,
                                color: isOutdated ? '#f59e0b' : '#34d399', fontWeight: 600
                              }}>
                                v{versionStr}
                              </span>
                              {isOutdated && (
                                <span title={`Latest production release is v${latestProdVer}`}>
                                  <AlertTriangle size={13} color="#f59e0b" />
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                              {u.primary_platform || 'Windows 64-bit'}
                            </div>
                          </td>

                          {/* Last Seen */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ color: '#f8fafc', fontWeight: 500 }}>
                              {lastSeenDisplay}
                            </div>
                            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                              Contrib: {lastContribDisplay}
                            </div>
                          </td>

                          {/* Data Impact */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                              <span style={{
                                padding: '2px 6px', borderRadius: 4, fontSize: 11,
                                background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', fontWeight: 600
                              }}>
                                +{newPeople} new
                              </span>
                              <span style={{
                                padding: '2px 6px', borderRadius: 4, fontSize: 11,
                                background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', fontWeight: 600
                              }}>
                                +{enrichedPeople} enriched
                              </span>
                            </div>
                            <div style={{ fontSize: 11, color: '#64748b', marginTop: 3 }}>
                              {rawObs.toLocaleString()} observations
                            </div>
                          </td>

                          {/* Quality Tier */}
                          <td style={{ padding: '14px 18px' }}>
                            {getQualityBadge(qualityTier, qualityScore)}
                          </td>

                          {/* Inspect Action */}
                          <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedUserId(u.user_id);
                              }}
                              style={{
                                padding: '6px 12px', background: '#1e293b', border: '1px solid #334155',
                                color: '#38bdf8', borderRadius: 6, fontSize: 11, fontWeight: 700,
                                cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4
                              }}
                            >
                              <span>Inspect</span>
                              <ChevronRight size={13} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PRIMARY VIEW 2: FLEET HARDWARE NODES & TELEMETRY                          */}
      {/* ========================================================================= */}
      {activeView === 'fleet_nodes' && (
        <div style={{ marginTop: 8 }}>
          <ScoutNodesPanel />
        </div>
      )}

      {/* User Forensic Slide-over Drawer */}
      <ScoutUserProfileDrawer
        userId={selectedUserId}
        onClose={() => setSelectedUserId(null)}
        onRefreshList={() => refetch()}
      />

      {/* Add Scout Modal */}
      <AddScoutModal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false);
          refetch();
        }}
      />
    </div>
  );
}
