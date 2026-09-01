import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Puzzle, Download, CheckCircle, Copy, ArrowRight, ShieldCheck, Zap, Globe, Sparkles, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ExtensionHub() {
  const [codes, setCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  const fetchCodes = async () => {
    try {
      const res = await api.get('/recruiters/extension/codes');
      setCodes(res.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCodes();
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
      await fetchCodes();
    } catch (e) {
      toast.error('Failed to generate code');
    } finally {
      setGenerating(false);
    }
  };

  const activeCode = codes.find(c => c.is_active)?.code || 'TALENTOPS-ATA086Q6';

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 100px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>
      {/* Header */}
      <header style={{ paddingTop: 32, marginBottom: 32, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              width: 36, height: 36, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)'
            }}>
              <Puzzle size={20} color="#fff" />
            </div>
            <h1 className="page-title" style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Talent Scout Extension
            </h1>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: 0 }}>
            Passively capture and verify recruiters from LinkedIn, Gmail, Outlook, and job sites as you browse.
          </p>
        </div>

        <button
          onClick={handleDownload}
          style={{
            padding: '10px 22px', background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)',
            color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 700, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 8, boxShadow: '0 4px 14px rgba(99, 102, 241, 0.35)',
            transition: 'all 0.2s'
          }}
        >
          <Download size={16} />
          <span>⚡ 1-Click Download Extension</span>
        </button>
      </header>

      {/* Hero Overview Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(56, 189, 248, 0.08) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: 16, padding: '24px 28px',
        display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24, marginBottom: 32, alignItems: 'center'
      }}>
        <div>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(34, 197, 94, 0.15)',
            color: '#4ade80', padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, marginBottom: 12
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
            24/7 Zero-Touch Autonomous Sync
          </div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 8px' }}>
            Work Normally. Your Database Enriches Itself.
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.5, margin: 0 }}>
            Once installed, Talent Scout runs silently in your browser. Whenever you open a candidate profile, read an email signature, or browse job posts, contact details are automatically scored, deduplicated, and synced to TalentOpsAI in real-time.
          </p>
        </div>

        {/* Quick Activation Code Card */}
        <div style={{
          background: '#0f172a', border: '1px solid #334155', borderRadius: 12, padding: '18px 20px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.4)'
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>
            Your Ready Activation Code
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
            <span style={{ fontSize: 11, color: '#64748b' }}>Enter once in extension popup</span>
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

      {/* 3-Step Installation Guide */}
      <div style={{
        background: 'var(--bg-panel)', border: '1px solid var(--card-border)', borderRadius: 16,
        padding: '24px 28px', marginBottom: 32
      }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 20px' }}>
          📦 3-Step Installation Guide (Under 30 Seconds)
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
          {/* Step 1 */}
          <div style={{
            background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 12, padding: 18,
            display: 'flex', flexDirection: 'column', gap: 10
          }}>
            <div style={{
              background: '#6366f1', color: '#fff', width: 28, height: 28, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13
            }}>
              1
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              Download & Unzip
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
              Click the download button above. Right-click <code>talentops-scout-extension.zip</code> and select <b>Extract All</b>.
            </p>
          </div>

          {/* Step 2 */}
          <div style={{
            background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 12, padding: 18,
            display: 'flex', flexDirection: 'column', gap: 10
          }}>
            <div style={{
              background: '#38bdf8', color: '#fff', width: 28, height: 28, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13
            }}>
              2
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              Open Chrome Extensions
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
              In Chrome, type <code>chrome://extensions/</code> in your address bar and enable <b>Developer mode</b> (toggle in top right).
            </p>
          </div>

          {/* Step 3 */}
          <div style={{
            background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 12, padding: 18,
            display: 'flex', flexDirection: 'column', gap: 10
          }}>
            <div style={{
              background: '#4ade80', color: '#090d16', width: 28, height: 28, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13
            }}>
              3
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
              Load Unpacked
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
              Click <b>Load unpacked</b> and select the extracted folder. Open the extension popup, paste your code, and click <b>Activate</b>.
            </p>
          </div>
        </div>
      </div>

      {/* Feature Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {[
          {
            icon: Globe, color: '#60a5fa', title: 'LinkedIn Universal',
            desc: 'Captures individual profiles, search result lists, recruiter cards, and hiring posts automatically.'
          },
          {
            icon: Zap, color: '#f59e0b', title: 'Email Signatures',
            desc: 'Extracts sender contact cards, phone numbers, and direct work emails from Gmail & Outlook Web.'
          },
          {
            icon: ShieldCheck, color: '#4ade80', title: 'Auto-Deduplication',
            desc: 'Cross-checks every lead with your database so duplicates are filtered and missing data is enriched.'
          }
        ].map((feat, i) => (
          <div key={i} style={{
            background: 'var(--bg-panel)', border: '1px solid var(--card-border)', borderRadius: 12, padding: '18px 20px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <feat.icon size={18} color={feat.color} />
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{feat.title}</div>
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
              {feat.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
