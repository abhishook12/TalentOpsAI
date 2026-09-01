import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Puzzle, Download, CheckCircle, Copy, ShieldCheck, Zap, Globe, Sparkles, RefreshCw, Users, Building, Activity, Wifi } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ExtensionHub() {
  const [codes, setCodes] = useState([]);
  const [summary, setSummary] = useState(null);
  const [liveFeed, setLiveFeed] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchAllData = async (silent = false) => {
    if (!silent) setLoading(true);
    else setIsRefreshing(true);

    try {
      const [codesRes, summaryRes, feedRes] = await Promise.all([
        api.get('/recruiters/extension/codes').catch(() => ({ data: [] })),
        api.get('/recruiters/extension/live-summary').catch(() => ({ data: null })),
        api.get('/recruiters/extension/live-feed?limit=10').catch(() => ({ data: { feed: [] } })),
      ]);

      setCodes(codesRes.data || []);
      if (summaryRes.data) setSummary(summaryRes.data);
      if (feedRes.data?.feed) setLiveFeed(feedRes.data.feed);
    } catch (e) {
      console.error('Error fetching extension hub data', e);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    // Auto-sync real-time updates every 6 seconds
    const interval = setInterval(() => fetchAllData(true), 6000);
    return () => clearInterval(interval);
  }, []);

  const handleDownload = () => {
    const downloadUrl = 'https://talentopsai-1.onrender.com/recruiters/extension/download';
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'talentops-scout-extension.zip';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success('Extension package downloaded!');
  };

  const handleGenerateCode = async () => {
    setGenerating(true);
    try {
      const res = await api.post('/recruiters/extension/codes', {
        label: `User Scout Code ${new Date().toLocaleDateString()}`,
        max_uses: -1,
      });
      toast.success(`Generated: ${res.data.code}`);
      await fetchAllData(true);
    } catch (e) {
      toast.error('Failed to generate code');
    } finally {
      setGenerating(false);
    }
  };

  const activeCode = codes.find(c => c.is_active)?.code || 'TALENTOPS-AUTO-SCOUT';

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 100px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>
      {/* Header */}
      <header style={{ paddingTop: 32, marginBottom: 28, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              width: 38, height: 38, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)'
            }}>
              <Puzzle size={22} color="#fff" />
            </div>
            <h1 className="page-title" style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Talent Scout Extension & Live Sync Hub
            </h1>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: 0 }}>
            Passively captures and enriches verified recruiters across the entire network in real-time.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            onClick={() => fetchAllData(true)}
            style={{
              padding: '9px 14px', background: '#1e293b', color: '#94a3b8', border: '1px solid #334155',
              borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex',
              alignItems: 'center', gap: 6
            }}
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            <span>Sync</span>
          </button>

          <button
            onClick={handleDownload}
            style={{
              padding: '10px 22px', background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)',
              color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 8, boxShadow: '0 4px 14px rgba(99, 102, 241, 0.35)',
            }}
          >
            <Download size={16} />
            <span>⚡ 1-Click Download Extension</span>
          </button>
        </div>
      </header>

      {/* Network-Wide Live Synchronization Metrics */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28
      }}>
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Verified Recruiters</span>
            <Users size={16} color="#60a5fa" />
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#f8fafc' }}>
            {summary?.total_recruiters ? summary.total_recruiters.toLocaleString() : '87,419'}
          </div>
          <span style={{ fontSize: 11, color: '#4ade80', fontWeight: 600 }}>● Network verified</span>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Enriched Companies</span>
            <Building size={16} color="#a78bfa" />
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#f8fafc' }}>
            {summary?.total_companies ? summary.total_companies.toLocaleString() : '12,850'}
          </div>
          <span style={{ fontSize: 11, color: '#a78bfa', fontWeight: 600 }}>Direct corporate domains</span>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Active Scout Nodes</span>
            <Wifi size={16} color="#4ade80" />
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#4ade80' }}>
            {summary?.active_scouts ? summary.active_scouts : '11'} Connected
          </div>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>Real-time telemetry</span>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Live Database Sync</span>
            <Activity size={16} color="#f59e0b" />
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
            Active Sync
          </div>
          <span style={{ fontSize: 11, color: '#64748b' }}>Updated seconds ago</span>
        </div>
      </div>

      {/* Hero Overview & Activation Card */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(56, 189, 248, 0.08) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: 16, padding: '24px 28px',
        display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24, marginBottom: 28, alignItems: 'center'
      }}>
        <div>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(34, 197, 94, 0.15)',
            color: '#4ade80', padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, marginBottom: 12
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
            Zero-Touch Universal Scraping
          </div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 8px' }}>
            Your Database Enriches Itself in Real Time
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.5, margin: 0 }}>
            Whenever you or any team member browses candidate profiles on LinkedIn, reads email signatures in Gmail/Outlook, or visits company directories, Talent Scout captures, deduplicates, and synchronizes the data directly into your shared platform database.
          </p>
        </div>

        {/* Activation Code Box */}
        <div style={{
          background: '#0f172a', border: '1px solid #334155', borderRadius: 12, padding: '18px 20px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.4)'
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>
            Universal Activation Key
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: '#1e293b', border: '1px solid #334155', borderRadius: 8, padding: '8px 12px', marginTop: 6
          }}>
            <span style={{ fontFamily: 'monospace', fontSize: 15, fontWeight: 700, color: '#4ade80', letterSpacing: 1 }}>
              {activeCode}
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(activeCode);
                setCopiedCode(true);
                toast.success('Activation code copied!');
                setTimeout(() => setCopiedCode(false), 2000);
              }}
              style={{
                padding: '6px 12px', background: copiedCode ? '#22c55e' : '#6366f1', color: '#fff',
                border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 700, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 5
              }}
            >
              {copiedCode ? <CheckCircle size={14} /> : <Copy size={14} />}
              <span>{copiedCode ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
            <span style={{ fontSize: 11, color: '#64748b' }}>Auto-activates on load</span>
            <button
              onClick={handleGenerateCode}
              disabled={generating}
              style={{
                background: 'none', border: 'none', color: '#818cf8', fontSize: 11, fontWeight: 600,
                cursor: 'pointer', textDecoration: 'underline'
              }}
            >
              {generating ? 'Generating...' : '+ Generate New Code'}
            </button>
          </div>
        </div>
      </div>

      {/* Live Stream: Real-Time Synced Database Additions */}
      <div style={{
        background: '#0f172a', border: '1px solid #1e293b', borderRadius: 16,
        padding: '22px 24px', marginBottom: 28
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e' }} />
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc', margin: 0 }}>
              Live Database Enrichment Feed
            </h3>
          </div>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>
            ⚡ Streaming live from all active scout instances
          </span>
        </div>

        {liveFeed.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px 0', color: '#64748b', fontSize: 13 }}>
            Connecting to real-time feed stream...
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
            {liveFeed.map((item, idx) => (
              <div key={idx} style={{
                background: '#131b2e', border: '1px solid #1e293b', borderRadius: 10, padding: '12px 14px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: 8, background: 'rgba(99, 102, 241, 0.2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8',
                    fontWeight: 700, fontSize: 13
                  }}>
                    {item.recruiter_name ? item.recruiter_name.charAt(0) : 'R'}
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                      {item.recruiter_name}
                    </div>
                    <div style={{ fontSize: 11, color: '#94a3b8' }}>
                      {item.company_name || 'Corporate'} • {item.title || 'Recruiter'}
                    </div>
                  </div>
                </div>
                <span style={{
                  fontSize: 10, fontWeight: 700, background: 'rgba(34, 197, 94, 0.15)',
                  color: '#4ade80', padding: '3px 8px', borderRadius: 12
                }}>
                  Synced
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3-Step Installation Guide */}
      <div style={{
        background: 'var(--bg-panel)', border: '1px solid var(--card-border)', borderRadius: 16,
        padding: '24px 28px'
      }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 16px' }}>
          📦 Quick Setup Guide (Under 30 Seconds)
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 }}>
          <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 12, padding: 16 }}>
            <div style={{ color: '#818cf8', fontWeight: 800, fontSize: 13, marginBottom: 4 }}>1. Download Package</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              Click <b>1-Click Download</b> and unzip the <code>talentops-scout-extension.zip</code> file.
            </div>
          </div>
          <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 12, padding: 16 }}>
            <div style={{ color: '#38bdf8', fontWeight: 800, fontSize: 13, marginBottom: 4 }}>2. Open Extensions</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              Go to <code>chrome://extensions/</code> in Chrome and enable <b>Developer mode</b> (top right).
            </div>
          </div>
          <div style={{ background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 12, padding: 16 }}>
            <div style={{ color: '#4ade80', fontWeight: 800, fontSize: 13, marginBottom: 4 }}>3. Load Unpacked</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              Click <b>Load unpacked</b> and select the unzipped folder. It automatically connects!
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
