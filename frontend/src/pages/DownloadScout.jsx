import React, { useState, useEffect } from 'react';
import {
  Download, Laptop, ShieldCheck, Zap, Wifi, CheckCircle2, ArrowRight,
  Database, RefreshCw, Layers, Terminal, Sparkles, AlertCircle, HelpCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';
import AddScoutModal from '../components/AddScoutModal';

export default function DownloadScout() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [releaseInfo, setReleaseInfo] = useState({
    version: '2.0.0',
    download_url: 'https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe',
    size_bytes: 50474851,
  });

  useEffect(() => {
    api.get('/scout/updates/latest')
      .then(res => {
        if (res?.data?.version) {
          setReleaseInfo(res.data);
        }
      })
      .catch(() => {});
  }, []);

  const handleDownload = () => {
    setDownloading(true);
    const downloadUrl = releaseInfo.download_url || '/scout/updates/download/latest';
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'TalentOpsScoutSetup.exe';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success(`TalentOps Scout v${releaseInfo.version} installer download started!`);
    setTimeout(() => setDownloading(false), 2500);
  };

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 100px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>
      {/* Header Banner */}
      <header style={{ paddingTop: 32, marginBottom: 28 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)',
          color: '#4ade80', padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700, marginBottom: 12
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
          OFFICIAL PRODUCTION RELEASE • REPLACES BROWSER EXTENSION
        </div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 10px', letterSpacing: '-0.5px' }}>
          TalentOps Scout Desktop
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 15, margin: 0, maxWidth: 780, lineHeight: 1.5 }}>
          Autonomous continuous intelligence engine for Windows. Operates silently in the background, observes active recruitment workflows, extracts verified leads via native Windows OCR, and enriches candidate pipelines 24/7.
        </p>
      </header>

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
            The new native Windows desktop client replaces the legacy Chrome extension. No Developer mode, no unpacked folders, and no black terminal console. Double-click to install and pair with your account in 30 seconds.
          </p>

          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            <button
              onClick={handleDownload}
              disabled={downloading}
              style={{
                padding: '12px 24px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                boxShadow: '0 4px 16px rgba(16, 185, 129, 0.4)'
              }}
            >
              <Download size={18} />
              <span>{downloading ? 'Downloading...' : 'Download for Windows'}</span>
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

          <div style={{ display: 'flex', gap: 18, marginTop: 18, fontSize: 11, color: '#64748b' }}>
            <span>• Windows 10 / 11 64-bit</span>
            <span>• Version {releaseInfo.version} Production</span>
            <span>• Zero Python Required</span>
          </div>
        </div>

        {/* Highlight Feature Points */}
        <div style={{
          background: '#090d16', border: '1px solid #1e293b', borderRadius: 12, padding: '20px 22px',
          display: 'flex', flexDirection: 'column', gap: 12
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Desktop Advantages
          </div>
          {[
            { title: 'Native Win32 Tracking', desc: 'Sub-millisecond window detection across Chrome, Edge, and desktop ATS apps.' },
            { title: 'Offline Windows Media OCR', desc: 'Zero dependency on fragile website DOM classes or CSS selectors.' },
            { title: 'System Tray & Edge Dock', desc: 'Operates silently in the tray without any visible command prompt or console.' },
            { title: 'Offline SQLite Buffer Queue', desc: 'Retains observations during network disconnects and flushes on restore.' },
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
              Download <code>TalentOpsScoutSetup.exe</code> and run the installer. Installs cleanly in seconds without admin restrictions.
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
        padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between'
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
          Upgrade to Desktop
        </button>
      </div>

      {/* Modal */}
      <AddScoutModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
      />
    </div>
  );
}
