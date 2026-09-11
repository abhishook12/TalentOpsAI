import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Download, Laptop, ShieldCheck, Zap, Wifi, CheckCircle2, ArrowRight,
  Database, RefreshCw, Layers, Terminal, Sparkles, AlertCircle, HelpCircle,
  Users, Activity, Server, FileText, Check, Shield, Search, Filter,
  ChevronRight, ArrowUpDown, Cpu, Clock, AlertTriangle, ShieldAlert, Award,
  ChevronDown, ChevronUp, ExternalLink, Info, UserCheck, Trash2, Key, Link2
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import AddScoutModal from '../components/AddScoutModal';
import ScoutUserProfileDrawer from '../components/ScoutUserProfileDrawer';
import ScoutNodesPanel from '../components/ScoutNodesPanel';
import ScoutReleaseGovernance from '../components/ScoutReleaseGovernance';

export default function DownloadScout() {
  const { user, isAdmin } = useAuth();
  const [showAddModal, setShowAddModal] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showSetupGuide, setShowSetupGuide] = useState(false);
  const [showSecurityNotice, setShowSecurityNotice] = useState(false);
  const [activeClaim, setActiveClaim] = useState(null);
  const [claimStatus, setClaimStatus] = useState(null);
  const pollIntervalRef = useRef(null);
  const [adminView, setAdminView] = useState('contributors'); // 'companion' | 'contributors' | 'fleet_nodes' | 'governance'
  const currentView = isAdmin ? adminView : 'companion';

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('most_active');
  const [selectedUserId, setSelectedUserId] = useState(null);

  // Pairing code state (Reverse Device Flow)
  const [pairingCodeInput, setPairingCodeInput] = useState('');
  const [pairingLoading, setPairingLoading] = useState(false);
  const [pairingSuccess, setPairingSuccess] = useState(null);
  const [pairingError, setPairingError] = useState('');
  const [disconnectingId, setDisconnectingId] = useState(null);

  // Dynamic Release Info from Authoritative DB Registry
  const [releaseInfo, setReleaseInfo] = useState({
    version: '',
    download_url: '/download/scout/windows',
    size_bytes: 50474851,
    sha256: '',
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

  // Personal Scout Companion Query (for logged-in user)
  const {
    data: myDeviceData,
    isLoading: loadingMyDevice,
    refetch: refetchMyDevice
  } = useQuery({
    queryKey: ['scout-my-device'],
    queryFn: async () => {
      const res = await api.get('/scout/my-device');
      return res.data;
    },
    refetchInterval: 5000,
  });

  // Scout Contributors Telemetry Query (Admin Only)
  const { data: contribData, isLoading, isFetching, isError, refetch } = useQuery({
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
    enabled: !!isAdmin,
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
        version: releaseInfo.version || contribData?.latest_production_version || 'latest',
        source: 'desktop_scout_page'
      });
    } catch (err) {}

    // 3. Initiate browser download of the installer using canonical public endpoint
    const downloadUrl = releaseInfo.download_url || '/download/scout/windows';
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'TalentOpsScoutSetup.exe';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    const verDisplay = releaseInfo.version ? `v${releaseInfo.version}` : (contribData?.latest_production_version ? `v${contribData.latest_production_version}` : '');
    toast.success(`TalentOps Scout ${verDisplay ? verDisplay + ' ' : ''}download initiated!`);
    setTimeout(() => setDownloading(false), 2500);
  };

  const handleVerifyPairingCode = async (e) => {
    if (e) e.preventDefault();
    const cleanCode = pairingCodeInput.trim().toUpperCase();
    if (!cleanCode) {
      toast.error('Please enter the pairing code shown on your Desktop Scout app');
      return;
    }
    setPairingLoading(true);
    setPairingError('');
    setPairingSuccess(null);

    try {
      const res = await api.post('/scout/device-flow/verify', { code: cleanCode });
      if (res?.data?.ok) {
        toast.success(`🎉 Desktop Scout paired successfully!`);
        setPairingSuccess(`Connected: ${res.data.scout_id || 'Device'} linked to ${res.data.user_email || 'your account'}`);
        setPairingCodeInput('');
        refetchMyDevice();
        if (isAdmin) refetch();
      } else {
        setPairingError(res?.data?.detail || 'Failed to verify pairing code');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid or expired pairing code. Please check Desktop Scout.';
      setPairingError(msg);
      toast.error(msg);
    } finally {
      setPairingLoading(false);
    }
  };

  const handleDisconnectDevice = async (deviceId) => {
    if (!window.confirm('Are you sure you want to disconnect this Desktop Scout companion?')) return;
    setDisconnectingId(deviceId);
    try {
      await api.post(`/scout/my-device/${deviceId}/disconnect`);
      toast.success('Device disconnected successfully');
      refetchMyDevice();
      if (isAdmin) refetch();
    } catch (err) {
      toast.error('Failed to disconnect device');
    } finally {
      setDisconnectingId(null);
    }
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
  const latestProdVer = contribData?.latest_production_version || releaseInfo?.version || '';

  const displayVersion = releaseInfo.version ? `v${releaseInfo.version}` : (latestProdVer ? `v${latestProdVer}` : 'Production');
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
              {isAdmin ? 'OFFICIAL DESKTOP ENGINE • FLEET GOVERNANCE' : 'OFFICIAL DESKTOP COMPANION • CONTINUOUS SOURCING'}
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 6px', letterSpacing: '-0.5px' }}>
              {isAdmin ? 'Desktop Scout & Contributors' : 'My Desktop Scout Companion'}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: 0, maxWidth: 840, lineHeight: 1.5 }}>
              {isAdmin
                ? 'Autonomous continuous recruitment intelligence engine for Windows, active device fleet management, and verified candidate pipeline contribution analytics.'
                : 'Connect your personal Windows desktop companion to automatically extract, verify, and stage recruiter contacts directly to your TalentOps account.'}
            </p>
          </div>

          {/* Quick Actions / View Mode Toggle */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {isAdmin && (
              <div style={{
                display: 'flex', background: '#090d16', border: '1px solid #1e293b',
                borderRadius: 8, padding: 3, gap: 2, flexWrap: 'wrap'
              }}>
                <button
                  onClick={() => setAdminView('companion')}
                  style={{
                    padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    background: adminView === 'companion' ? '#1e293b' : 'transparent',
                    color: adminView === 'companion' ? '#38bdf8' : '#94a3b8',
                  }}
                >
                  <Laptop size={13} />
                  <span>My Companion</span>
                </button>
                <button
                  onClick={() => setAdminView('contributors')}
                  style={{
                    padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    background: adminView === 'contributors' ? '#1e293b' : 'transparent',
                    color: adminView === 'contributors' ? '#38bdf8' : '#94a3b8',
                  }}
                >
                  <Users size={13} />
                  <span>Contributors Intelligence</span>
                </button>
                <button
                  onClick={() => setAdminView('fleet_nodes')}
                  style={{
                    padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    background: adminView === 'fleet_nodes' ? '#1e293b' : 'transparent',
                    color: adminView === 'fleet_nodes' ? '#38bdf8' : '#94a3b8',
                  }}
                >
                  <Server size={13} />
                  <span>Device Fleet &amp; Nodes</span>
                </button>
                <button
                  onClick={() => setAdminView('governance')}
                  style={{
                    padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    background: adminView === 'governance' ? '#1e293b' : 'transparent',
                    color: adminView === 'governance' ? '#38bdf8' : '#94a3b8',
                  }}
                >
                  <ShieldCheck size={13} />
                  <span>Release Governance</span>
                </button>
              </div>
            )}

            <button
              onClick={() => {
                refetchMyDevice();
                if (isAdmin) refetch();
              }}
              disabled={isFetching || loadingMyDevice}
              style={{
                padding: '8px 14px', background: '#1e293b', border: '1px solid #334155',
                color: '#f8fafc', borderRadius: 8, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                opacity: isFetching || loadingMyDevice ? 0.6 : 1
              }}
            >
              <RefreshCw size={13} className={isFetching || loadingMyDevice ? 'animate-spin' : ''} />
              <span>{isFetching || loadingMyDevice ? 'Syncing...' : 'Refresh'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* PERSONAL SCOUT COMPANION VIEW (For non-admin users + admin companion tab) */}
      {/* ========================================================================= */}
      {currentView === 'companion' && (
        <div>
          {/* Companion Welcome & Status Banner */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%)',
            border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: 14, padding: '24px 28px',
            marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 20
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                <span style={{
                  background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.35)',
                  padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, letterSpacing: 0.5, display: 'inline-flex', alignItems: 'center', gap: 6
                }}>
                  <Laptop size={12} />
                  PERSONAL SCOUT COMPANION
                </span>
                <span style={{ fontSize: 12, color: '#94a3b8' }}>
                  Account: <b>{user?.email || 'Authenticated User'}</b>
                </span>
              </div>
              <h2 style={{ fontSize: 22, fontWeight: 800, color: '#f8fafc', margin: '0 0 6px 0', letterSpacing: '-0.3px' }}>
                Welcome, {user?.first_name || user?.name || user?.email?.split('@')[0] || 'Recruiter'}!
              </h2>
              <p style={{ color: '#94a3b8', fontSize: 13, margin: 0, maxWidth: 740, lineHeight: 1.5 }}>
                Your Desktop Scout companion operates silently in the background to autonomously capture candidate discoveries while you browse LinkedIn and recruiting boards, continuously enriching your personal talent pipeline.
              </p>
            </div>

            {/* Live Device Status Pill */}
            <div style={{
              background: '#090d16', border: '1px solid #1e293b', borderRadius: 10, padding: '12px 18px',
              display: 'flex', alignItems: 'center', gap: 14
            }}>
              <div style={{
                width: 10, height: 10, borderRadius: '50%',
                background: myDeviceData?.devices?.some(d => d.is_online) ? '#10b981' : '#64748b',
                boxShadow: myDeviceData?.devices?.some(d => d.is_online) ? '0 0 10px #10b981' : 'none'
              }} />
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Companion Status</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: myDeviceData?.devices?.some(d => d.is_online) ? '#34d399' : '#f8fafc' }}>
                  {myDeviceData?.devices?.some(d => d.is_online)
                    ? 'Active & Streaming'
                    : (myDeviceData?.devices?.length > 0 ? 'Device Paired (Standby)' : 'Not Connected')}
                </div>
              </div>
            </div>
          </div>

          {/* 2-Column Action Cards: Download (Left) & Enter Code (Right) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 20, marginBottom: 28 }}>
            {/* CARD 1: DOWNLOAD INSTALLER */}
            <div style={{
              background: '#0f172a', border: '1px solid #1e293b', borderRadius: 14, padding: '24px 26px',
              display: 'flex', flexDirection: 'column', justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 10, background: 'rgba(16, 185, 129, 0.15)',
                    border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981'
                  }}>
                    <Download size={22} />
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', letterSpacing: 0.5 }}>STEP 1: GET DESKTOP COMPANION</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc' }}>TalentOps Scout Setup</div>
                  </div>
                </div>

                <p style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.5, marginBottom: 16 }}>
                  Download and run the official Windows installer. Installs cleanly in 5 seconds into your user profile without needing IT administrator privileges.
                </p>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: '#1e293b', color: '#94a3b8', fontSize: 11, fontWeight: 600 }}>
                    Windows 10/11 64-bit
                  </span>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: '#1e293b', color: '#94a3b8', fontSize: 11, fontWeight: 600 }}>
                    {displayVersion}
                  </span>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: '#1e293b', color: '#94a3b8', fontSize: 11, fontWeight: 600 }}>
                    {displaySize}
                  </span>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: 11, fontWeight: 600 }}>
                    Offline OCR Built-in
                  </span>
                </div>
              </div>

              <div>
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  style={{
                    width: '100%', padding: '13px 20px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.35)', transition: 'all 0.15s ease'
                  }}
                >
                  <Download size={18} />
                  <span>{downloading ? 'Starting Download...' : `Download Scout (${displayVersion})`}</span>
                </button>
              </div>
            </div>

            {/* CARD 2: ENTER PAIRING CODE (REVERSE DEVICE FLOW) */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 22, 44, 0.95) 100%)',
              border: '1px solid rgba(56, 189, 248, 0.35)', borderRadius: 14, padding: '24px 26px',
              display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
              boxShadow: '0 8px 30px rgba(56, 189, 248, 0.1)'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 10, background: 'rgba(56, 189, 248, 0.15)',
                    border: '1px solid rgba(56, 189, 248, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#38bdf8'
                  }}>
                    <Zap size={22} />
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', letterSpacing: 0.5 }}>STEP 2: LINK TO YOUR ACCOUNT</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc' }}>Enter Desktop Pairing Code</div>
                  </div>
                </div>

                <p style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.5, marginBottom: 16 }}>
                  Launch Desktop Scout on your PC. It displays a 4-character pairing code on your screen (e.g. <b>TOS-8492</b>). Enter that code below to connect your device:
                </p>

                <form onSubmit={handleVerifyPairingCode} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <input
                      type="text"
                      placeholder="TOS-____"
                      value={pairingCodeInput}
                      onChange={(e) => {
                        setPairingCodeInput(e.target.value.toUpperCase());
                        setPairingError('');
                      }}
                      maxLength={10}
                      style={{
                        flex: 1, padding: '12px 16px', background: '#090d16', border: '1px solid rgba(56, 189, 248, 0.4)',
                        borderRadius: 10, color: '#38bdf8', fontSize: 18, fontWeight: 800, letterSpacing: 3,
                        fontFamily: 'monospace', textTransform: 'uppercase', textAlign: 'center', outline: 'none'
                      }}
                    />
                    <button
                      type="submit"
                      disabled={pairingLoading || !pairingCodeInput.trim()}
                      style={{
                        padding: '13px 22px', background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                        color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 700,
                        cursor: pairingLoading || !pairingCodeInput.trim() ? 'not-allowed' : 'pointer',
                        display: 'flex', alignItems: 'center', gap: 8, opacity: pairingLoading || !pairingCodeInput.trim() ? 0.6 : 1,
                        boxShadow: '0 4px 15px rgba(2, 132, 199, 0.35)', whiteSpace: 'nowrap'
                      }}
                    >
                      {pairingLoading ? <RefreshCw size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                      <span>{pairingLoading ? 'Linking...' : 'Connect Device'}</span>
                    </button>
                  </div>
                </form>

                {pairingError && (
                  <div style={{
                    background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.35)',
                    borderRadius: 8, padding: '10px 14px', color: '#f87171', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12
                  }}>
                    <AlertCircle size={15} flexShrink={0} />
                    <span>{pairingError}</span>
                  </div>
                )}

                {pairingSuccess && (
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.35)',
                    borderRadius: 8, padding: '10px 14px', color: '#34d399', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12
                  }}>
                    <CheckCircle2 size={15} flexShrink={0} />
                    <span>{pairingSuccess}</span>
                  </div>
                )}
              </div>

              <div style={{ fontSize: 11, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
                <ShieldCheck size={14} color="#10b981" />
                <span>Encrypted end-to-end device token bound strictly to your user profile.</span>
              </div>
            </div>
          </div>

          {/* STEP 3: MY PAIRED COMPANION HARDWARE CARDS */}
          <div style={{ marginBottom: 32 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 17, fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                  My Paired Companions ({myDeviceData?.devices?.length || 0})
                </h3>
                <p style={{ color: '#94a3b8', fontSize: 12, margin: '2px 0 0' }}>
                  Desktop devices bound to your account and reporting continuous recruitment telemetry.
                </p>
              </div>

              <button
                onClick={() => refetchMyDevice()}
                disabled={loadingMyDevice}
                style={{
                  padding: '6px 12px', background: '#1e293b', border: '1px solid #334155',
                  color: '#94a3b8', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 6
                }}
              >
                <RefreshCw size={12} className={loadingMyDevice ? 'animate-spin' : ''} />
                <span>Refresh Status</span>
              </button>
            </div>

            {myDeviceData?.devices && myDeviceData.devices.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
                {myDeviceData.devices.map((dev) => (
                  <div
                    key={dev.device_id}
                    style={{
                      background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12,
                      padding: '18px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{
                            width: 36, height: 36, borderRadius: 8, background: '#1e293b',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', color: dev.is_online ? '#34d399' : '#94a3b8'
                          }}>
                            <Laptop size={18} />
                          </div>
                          <div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
                              {dev.name || 'Windows Desktop'}
                            </div>
                            <div style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>
                              {dev.device_id?.substring(0, 16)}...
                            </div>
                          </div>
                        </div>

                        <span style={{
                          padding: '3px 8px', borderRadius: 12, fontSize: 10, fontWeight: 700,
                          background: dev.is_online ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                          color: dev.is_online ? '#34d399' : '#94a3b8',
                          border: `1px solid ${dev.is_online ? 'rgba(16, 185, 129, 0.3)' : 'rgba(100, 116, 139, 0.3)'}`,
                          display: 'flex', alignItems: 'center', gap: 5
                        }}>
                          <span style={{
                            width: 6, height: 6, borderRadius: '50%',
                            background: dev.is_online ? '#10b981' : '#64748b'
                          }} />
                          {dev.is_online ? 'ONLINE & STREAMING' : 'STANDBY'}
                        </span>
                      </div>

                      <div style={{
                        background: '#090d16', border: '1px solid #1e293b', borderRadius: 8,
                        padding: '10px 14px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16
                      }}>
                        <div>
                          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Version</div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8', fontFamily: 'monospace' }}>
                            v{dev.version || '2.7.0'}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Last Active</div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>
                            {formatTimeAgo(dev.last_seen_at)}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Candidates Added</div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#34d399' }}>
                            {dev.total_accepted || 0}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>Observations</div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>
                            {dev.total_submitted || 0}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => handleDisconnectDevice(dev.device_id)}
                        disabled={disconnectingId === dev.device_id}
                        style={{
                          padding: '6px 12px', background: 'transparent', border: '1px solid rgba(239, 68, 68, 0.3)',
                          color: '#f87171', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                          display: 'flex', alignItems: 'center', gap: 5
                        }}
                      >
                        <Trash2 size={12} />
                        <span>{disconnectingId === dev.device_id ? 'Disconnecting...' : 'Disconnect'}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{
                background: '#0f172a', border: '1px dashed #1e293b', borderRadius: 14,
                padding: '36px 24px', textAlign: 'center'
              }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 12, background: 'rgba(56, 189, 248, 0.1)',
                  border: '1px solid rgba(56, 189, 248, 0.2)', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', color: '#38bdf8', margin: '0 auto 14px'
                }}>
                  <Laptop size={24} />
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc', marginBottom: 6 }}>
                  No Desktop Companion Connected Yet
                </div>
                <p style={{ color: '#94a3b8', fontSize: 13, maxWidth: 520, margin: '0 auto 18px', lineHeight: 1.5 }}>
                  Download the installer above and launch Desktop Scout. Enter the pairing code displayed on your desktop into the box above to link this computer in seconds.
                </p>
                <div style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <button
                    onClick={handleDownload}
                    style={{
                      padding: '8px 16px', background: '#10b981', color: '#fff', border: 'none',
                      borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6
                    }}
                  >
                    <Download size={14} />
                    <span>Download Scout v2.7.0</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Expandable Guides (Setup Guide & Trust Notice) */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
            <button
              onClick={() => setShowSetupGuide(!showSetupGuide)}
              style={{
                padding: '9px 14px', background: '#090d16', color: '#94a3b8',
                border: '1px solid #1e293b', borderRadius: 8, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
              }}
            >
              <Info size={14} />
              <span>{showSetupGuide ? 'Hide 3-Step Setup Guide' : 'View 3-Step Setup Guide'}</span>
              {showSetupGuide ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            <button
              onClick={() => setShowSecurityNotice(!showSecurityNotice)}
              style={{
                padding: '9px 14px', background: '#090d16', color: '#f59e0b',
                border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 8, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
              }}
            >
              <ShieldAlert size={14} />
              <span>{showSecurityNotice ? 'Hide Windows SmartScreen Notice' : 'Windows SmartScreen & Trust Notice'}</span>
              {showSecurityNotice ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>

          {showSetupGuide && (
            <div style={{
              marginBottom: 20, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14
            }}>
              <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', marginBottom: 4 }}>1. Download &amp; Run</div>
                <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                  Run <code>TalentOpsScoutSetup.exe</code>. Installs silently in 5 seconds into your user profile with no administrator prompt needed.
                </div>
              </div>
              <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', marginBottom: 4 }}>2. Note the Pairing Code</div>
                <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                  Scout Desktop launches and displays a bold code (e.g. <code>TOS-8492</code>). Enter that code into the box above.
                </div>
              </div>
              <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#a855f7', marginBottom: 4 }}>3. Autonomous Ingestion</div>
                <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                  Scout minimizes to your system tray. As you browse candidates on LinkedIn, contacts are extracted and synced automatically.
                </div>
              </div>
            </div>
          )}

          {showSecurityNotice && (
            <div style={{
              marginBottom: 20, background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.25)',
              borderRadius: 10, padding: 16
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: '#f59e0b', fontSize: 13, fontWeight: 700 }}>
                <ShieldAlert size={16} />
                <span>Browser Security &amp; Windows SmartScreen Notice</span>
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                <p style={{ margin: '0 0 6px 0', color: '#f8fafc' }}>
                  <b>Why does Chrome, Edge, or Windows show an unrecognized app prompt?</b>
                </p>
                <p style={{ margin: '0 0 6px 0' }}>
                  Newly published binaries undergo a reputation ramp-up period with Microsoft SmartScreen. This is standard for internal enterprise tooling.
                </p>
                <ul style={{ margin: '0 0 8px 18px', padding: 0 }}>
                  <li><b>In Chrome/Edge:</b> Click the download dropdown → Select <b>Keep</b> / <b>Download suspicious file</b>.</li>
                  <li><b>In Windows SmartScreen:</b> Click <b>More info</b> → Select <b>Run anyway</b>.</li>
                  <li><b>Strict Privacy Guardrail:</b> Scout never accesses passwords, cookies, or financial info. Only candidate profile fields are captured.</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* ADMIN VIEW 1: SCOUT USERS & CONTRIBUTORS INTELLIGENCE                     */}
      {/* ========================================================================= */}
      {isAdmin && currentView === 'contributors' && (
        <div>
          {/* Quick Companion Pairing Strip for Admins */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(56, 189, 248, 0.05) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 12, padding: '16px 20px',
            marginBottom: 20, boxShadow: '0 4px 20px rgba(0,0,0,0.18)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
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

              <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
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

                {/* Instant Inline Device Pairing Input */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6, background: '#020617',
                  border: '1px solid #334155', borderRadius: 8, padding: '3px 8px'
                }}>
                  <Key size={14} color="#38bdf8" />
                  <input
                    type="text"
                    placeholder="CODE: TOS-XXXX"
                    value={pairingCodeInput}
                    onChange={(e) => {
                      setPairingCodeInput(e.target.value.toUpperCase());
                      setPairingError('');
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleVerifyPairingCode();
                    }}
                    style={{
                      width: 125, background: 'transparent', border: 'none',
                      color: '#38bdf8', fontFamily: 'monospace', fontWeight: 800,
                      fontSize: 12, outline: 'none'
                    }}
                  />
                  <button
                    onClick={handleVerifyPairingCode}
                    disabled={pairingLoading || !pairingCodeInput.trim()}
                    style={{
                      padding: '5px 12px', background: '#2563eb', color: '#fff',
                      border: 'none', borderRadius: 6, fontSize: 11, fontWeight: 700,
                      cursor: 'pointer', opacity: (pairingLoading || !pairingCodeInput.trim()) ? 0.6 : 1
                    }}
                  >
                    {pairingLoading ? 'Linking...' : 'Connect Device'}
                  </button>
                </div>

                <button
                  onClick={() => setShowAddModal(true)}
                  style={{
                    padding: '9px 14px', background: '#090d16', color: '#94a3b8',
                    border: '1px solid #1e293b', borderRadius: 8, fontSize: 12, fontWeight: 600,
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
                  }}
                >
                  <Zap size={13} />
                  <span>Issue 10m Code</span>
                </button>
              </div>
            </div>

            {(pairingError || pairingSuccess) && (
              <div style={{ marginTop: 12 }}>
                {pairingError && (
                  <div style={{
                    background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)',
                    borderRadius: 8, padding: '8px 14px', color: '#f87171', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8
                  }}>
                    <AlertCircle size={15} flexShrink={0} />
                    <span>{pairingError}</span>
                  </div>
                )}
                {pairingSuccess && (
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)',
                    borderRadius: 8, padding: '8px 14px', color: '#34d399', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8
                  }}>
                    <CheckCircle2 size={15} flexShrink={0} />
                    <span>{pairingSuccess}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Reconnection / Error Banner */}
          {isError && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.35)',
              borderRadius: 8, padding: '12px 18px', marginBottom: 16, display: 'flex',
              alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#f87171', fontSize: 13 }}>
                <AlertCircle size={18} />
                <span>Backend telemetry engine is currently deploying or reconnecting. Telemetry will sync automatically.</span>
              </div>
              <button
                onClick={() => refetch()}
                disabled={isFetching}
                style={{
                  padding: '6px 14px', background: '#1e293b', border: '1px solid #334155',
                  color: '#f8fafc', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer'
                }}
              >
                {isFetching ? 'Syncing...' : 'Retry Connection'}
              </button>
            </div>
          )}

          {/* Navigation Guidance Strip */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12,
            background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.22)',
            borderRadius: 10, padding: '10px 16px', marginBottom: 16, fontSize: 12
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#38bdf8' }}>
              <Users size={16} />
              <span>
                Currently viewing <b>Contributors Intelligence (User Accounts)</b>. To inspect individual physical hardware machines, companion nodes &amp; live streams, switch to <b>Device Fleet &amp; Nodes</b>.
              </span>
            </div>
            <button
              onClick={() => setAdminView('fleet_nodes')}
              style={{
                padding: '5px 14px', background: '#0284c7', color: '#fff',
                border: 'none', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 2px 8px rgba(2, 132, 199, 0.3)'
              }}
            >
              <Laptop size={13} />
              <span>View Device Fleet &amp; Nodes ({summary.total_devices || summary.active_devices || 0})</span>
            </button>
          </div>

          {/* KPI Cards Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 14, marginBottom: 20 }}>
            {[
              { label: 'TOTAL SCOUT USERS', value: totalUsersCount, icon: Users, color: '#38bdf8', sub: 'Registered & active' },
              { label: 'ACTIVE USERS', value: activeUsersCount, icon: Activity, color: '#4ade80', sub: 'Seen last 24h' },
              {
                label: 'ACTIVE DEVICES',
                value: activeDevicesCount,
                icon: Laptop,
                color: '#22c55e',
                sub: `${totalDevicesCount} nodes (Click to view fleet)`,
                clickable: true,
                onClick: () => setAdminView('fleet_nodes')
              },
              { label: 'CONTRIBUTING USERS', value: contributingUsersCount, icon: Sparkles, color: '#a855f7', sub: 'Added / enriched data' },
              { label: 'OFFLINE USERS', value: offlineUsersCount, icon: Clock, color: '#94a3b8', sub: 'No signal > 7d' },
              { label: 'UPDATE REQUIRED', value: updateReqCount, icon: AlertTriangle, color: '#f59e0b', sub: `Prod is v${latestProdVer}` },
              { label: 'REVOKED', value: revokedCount, icon: ShieldAlert, color: '#f43f5e', sub: 'Blocked or quarantined' },
            ].map((card, idx) => {
              const Icon = card.icon;
              return (
                <div
                  key={idx}
                  onClick={card.onClick}
                  style={{
                    background: '#0f172a', border: card.clickable ? '1px solid rgba(34, 197, 94, 0.4)' : '1px solid #1e293b',
                    borderRadius: 12, padding: '16px 18px',
                    display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden',
                    cursor: card.clickable ? 'pointer' : 'default',
                    transition: 'all 0.15s ease',
                  }}
                  title={card.clickable ? 'Click to open Device Fleet & Nodes panel' : undefined}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', letterSpacing: 0.5 }}>{card.label}</span>
                    <Icon size={16} color={card.color} />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: '#f8fafc', lineHeight: 1.1, marginBottom: 4 }}>
                    {card.value.toLocaleString()}
                  </div>
                  <div style={{ fontSize: 11, color: card.clickable ? '#4ade80' : '#64748b', fontWeight: card.clickable ? 600 : 400 }}>
                    {card.sub}
                  </div>
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
                      const versionStr = u.primary_version || u.current_version || latestProdVer || '—';
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
      {isAdmin && currentView === 'fleet_nodes' && (
        <div style={{ marginTop: 8 }}>
          <ScoutNodesPanel />
        </div>
      )}

      {/* ========================================================================= */}
      {/* PRIMARY VIEW 3: RELEASE & ROLLOUT GOVERNANCE                              */}
      {/* ========================================================================= */}
      {isAdmin && currentView === 'governance' && (
        <div style={{ marginTop: 8 }}>
          <ScoutReleaseGovernance
            onReleaseChanged={() => {
              api.get('/scout/updates/latest')
                .then(res => {
                  if (res?.data?.version) setReleaseInfo(prev => ({ ...prev, ...res.data }));
                })
                .catch(() => {});
              refetch();
            }}
          />
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
