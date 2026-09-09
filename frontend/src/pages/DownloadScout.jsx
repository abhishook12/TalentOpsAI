import React, { useState, useEffect } from 'react';
import {
  Download, Laptop, ShieldCheck, Zap, Wifi, CheckCircle2, ArrowRight,
  Database, RefreshCw, Layers, Terminal, Sparkles, AlertCircle, HelpCircle,
  Users, Activity, Server, FileText, Check, Shield
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';
import AddScoutModal from '../components/AddScoutModal';
import ScoutContributors from './ScoutContributors';
import ScoutNodesPanel from '../components/ScoutNodesPanel';

export default function DownloadScout() {
  const [activeTab, setActiveTab] = useState('overview');
  const [showAddModal, setShowAddModal] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [releaseInfo, setReleaseInfo] = useState({
    version: '',
    download_url: 'https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe',
    size_bytes: 50474851,
    sha256_checksum: '',
    channel: 'production',
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

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await api.post('/scout/download/track', {
        version: releaseInfo.version || '2.0.0',
        source: 'web_download_page'
      });
    } catch (err) {
      // Telemetry error shouldn't block installer download
    }

    const downloadUrl = releaseInfo.download_url || '/scout/updates/download/latest';
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'TalentOpsScoutSetup.exe';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success(`TalentOps Scout v${releaseInfo.version || '2.0.0'} installer download started!`);
    setTimeout(() => setDownloading(false), 2500);
  };

  const displayVersion = releaseInfo.version ? `v${releaseInfo.version}` : 'v2.0.0';
  const displaySize = releaseInfo.size_bytes
    ? `${(releaseInfo.size_bytes / (1024 * 1024)).toFixed(1)} MB`
    : '48.1 MB';

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 100px', maxWidth: activeTab === 'overview' ? 1140 : 1400, margin: '0 auto', width: '100%' }}>
      {/* Top Header & Sub-Navigation Tabs */}
      <header style={{ paddingTop: 32, marginBottom: 24 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)',
          color: '#4ade80', padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700, marginBottom: 12
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
          OFFICIAL PRODUCTION RELEASE • {releaseInfo.channel ? releaseInfo.channel.toUpperCase() : 'PRODUCTION'} CHANNEL
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 8px', letterSpacing: '-0.5px' }}>
              TalentOps Scout Platform
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: 0, maxWidth: 780, lineHeight: 1.5 }}>
              Enterprise desktop client, continuous visual intelligence, fleet management, and verified contributor analytics.
            </p>
          </div>

          {/* Sub-Navigation Tabs Switcher */}
          <div style={{
            display: 'flex', background: '#090d16', border: '1px solid #1e293b',
            borderRadius: 10, padding: 4, gap: 4
          }}>
            {[
              { id: 'overview', label: 'Download & Overview', icon: Download },
              { id: 'contributors', label: 'Scout Contributors', icon: Users },
              { id: 'nodes', label: 'Fleet & Telemetry', icon: Laptop },
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    padding: '7px 14px', borderRadius: 7, fontSize: 12, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                    background: isActive ? '#1e293b' : 'transparent',
                    color: isActive ? '#38bdf8' : '#94a3b8',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <Icon size={14} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Tab 1: Download & Overview */}
      {activeTab === 'overview' && (
        <div>
          {/* Hero Action Card */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(59, 130, 246, 0.08) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 16, padding: '32px 36px',
            display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 32, marginBottom: 36, alignItems: 'center'
          }}>
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, color: '#f8fafc', marginBottom: 10 }}>
                Ready to deploy on your computer
              </div>
              <p style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.6, margin: '0 0 24px' }}>
                The native Windows desktop client replaces legacy browser extensions. No Developer mode, no unpacked folders, and no terminal consoles. Double-click to install and pair with your account in 30 seconds.
              </p>

              <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  style={{
                    padding: '12px 24px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700,
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                    boxShadow: '0 4px 16px rgba(16, 185, 129, 0.4)',
                    opacity: downloading ? 0.7 : 1
                  }}
                >
                  <Download size={18} />
                  <span>{downloading ? 'Downloading...' : `Download ${displayVersion} for Windows`}</span>
                </button>

                <button
                  onClick={() => setShowAddModal(true)}
                  style={{
                    padding: '12px 20px', background: '#1e293b', color: '#38bdf8',
                    border: '1px solid #334155', borderRadius: 10, fontSize: 13, fontWeight: 700,
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8
                  }}
                >
                  <Zap size={16} />
                  <span>Pair Device (10m Code)</span>
                </button>
              </div>

              <div style={{ display: 'flex', gap: 18, marginTop: 18, fontSize: 11, color: '#64748b', flexWrap: 'wrap' }}>
                <span>• Windows 10 / 11 64-bit</span>
                <span>• Production Release: <b>{displayVersion}</b> ({displaySize})</span>
                <span>• Zero Python Required</span>
                {releaseInfo.sha256_checksum && (
                  <span title={releaseInfo.sha256_checksum} style={{ cursor: 'help' }}>
                    • SHA256: {releaseInfo.sha256_checksum.slice(0, 8)}...
                  </span>
                )}
              </div>
            </div>

            {/* Highlight Feature Points */}
            <div style={{
              background: '#090d16', border: '1px solid #1e293b', borderRadius: 12, padding: '20px 22px',
              display: 'flex', flexDirection: 'column', gap: 12
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                Desktop Engine Capabilities
              </div>
              {[
                { title: 'Native Win32 Tracking', desc: 'Sub-millisecond active window detection across Chrome, Edge, and desktop ATS apps.' },
                { title: 'Windows Media OCR', desc: 'Zero dependency on fragile website DOM classes or CSS selectors.' },
                { title: 'System Tray & Edge Dock', desc: 'Operates silently in the tray without any visible command prompt or console.' },
                { title: 'Offline SQLite Buffer Queue', desc: 'Durable offline observation storage with backpressure and jittered replay.' },
                { title: 'Auto-Purge Security', desc: 'Temporary screenshots automatically destroyed within 15-30 seconds.' },
              ].map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <CheckCircle2 size={16} color="#10b981" style={{ flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>{item.title}: </span>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>{item.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 3-Step Setup Walkthrough */}
          <div style={{ marginBottom: 40 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 16px' }}>
              3-Step Instant Setup
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 }}>
              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 22 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, marginBottom: 12 }}>1</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', marginBottom: 6 }}>Download & Install</div>
                <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                  Download <code>TalentOpsScoutSetup.exe</code> ({displayVersion}) and run the installer. Installs cleanly in seconds without admin restrictions.
                </div>
              </div>

              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 22 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, marginBottom: 12 }}>2</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', marginBottom: 6 }}>Pair Your Account</div>
                <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                  Click <b>Pair Device</b> above to generate your single-use 10-minute activation code (e.g. <code>TOS-ABCD-1234</code>) or click 1-Click Connect.
                </div>
              </div>

              <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 22 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(168, 85, 247, 0.15)', color: '#a855f7', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, marginBottom: 12 }}>3</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', marginBottom: 6 }}>Autonomous Ingestion</div>
                <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                  Work normally on LinkedIn, Gmail, or job sites. Scout detects context, extracts verified talent profiles, and streams discoveries to your database.
                </div>
              </div>
            </div>
          </div>

          {/* Migration Notice from Old Extension */}
          <div style={{
            background: '#131b2e', border: '1px solid #1e293b', borderRadius: 14,
            padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ fontSize: 24 }}>🔄</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
                  Migrating from the legacy Chrome Extension?
                </div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                  The old Chrome extension is now deprecated. You can safely uninstall the unpacked folder from Chrome. All historical discoveries and candidate profiles are fully preserved in your central database.
                </div>
              </div>
            </div>
            <button
              onClick={handleDownload}
              style={{
                padding: '8px 18px', background: '#3b82f6', color: '#fff', border: 'none',
                borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap'
              }}
            >
              Upgrade to Desktop {displayVersion}
            </button>
          </div>
        </div>
      )}

      {/* Tab 2: Scout Contributors Intelligence */}
      {activeTab === 'contributors' && (
        <ScoutContributors />
      )}

      {/* Tab 3: Fleet & Telemetry */}
      {activeTab === 'nodes' && (
        <ScoutNodesPanel />
      )}

      {/* Modal */}
      <AddScoutModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
      />
    </div>
  );
}
