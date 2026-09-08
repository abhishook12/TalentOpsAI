import React, { useState, useEffect } from 'react';
import { X, Copy, CheckCircle, ExternalLink, ShieldCheck, Laptop, Zap, RefreshCw } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

export default function AddScoutModal({ isOpen, onClose, onActivated }) {
  const [codeData, setCodeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [timeLeft, setTimeLeft] = useState(600); // 10 mins in sec

  const generateCode = async () => {
    setLoading(true);
    try {
      const res = await api.post('/scout/codes/generate', {
        label: `Desktop Scout (${new Date().toLocaleDateString()})`,
        expires_minutes: 10,
      });
      setCodeData(res.data);
      setTimeLeft(res.data.expires_in_seconds || 600);
    } catch (err) {
      toast.error('Failed to generate activation code');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      generateCode();
    } else {
      setCodeData(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || timeLeft <= 0) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [isOpen, timeLeft]);

  if (!isOpen) return null;

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const handleCopyCode = () => {
    if (!codeData?.code) return;
    navigator.clipboard.writeText(codeData.code);
    setCopied(true);
    toast.success('Activation code copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDeepLink = () => {
    if (!codeData?.deep_link) return;
    window.location.href = codeData.deep_link;
    toast.success('Connecting to Desktop Scout...');
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      backgroundColor: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20
    }}>
      <div style={{
        background: '#0f172a', border: '1px solid #1e293b', borderRadius: 16,
        maxWidth: 520, width: '100%', padding: '28px', color: '#f8fafc',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)', position: 'relative'
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 20, right: 20, background: 'transparent',
            border: 'none', color: '#94a3b8', cursor: 'pointer'
          }}
        >
          <X size={20} />
        </button>

        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12,
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)'
          }}>
            <Laptop size={24} color="#fff" />
          </div>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: '#f8fafc' }}>
              Add TalentOps Scout Node
            </h2>
            <p style={{ fontSize: 12, color: '#94a3b8', margin: '2px 0 0' }}>
              Pair this computer to your TalentOps account
            </p>
          </div>
        </div>

        {/* Activation Code Box */}
        <div style={{
          background: '#1e293b', border: '1px solid #334155', borderRadius: 12,
          padding: '18px 20px', marginBottom: 20
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              10-Minute Activation Code
            </span>
            <span style={{
              fontSize: 11, fontWeight: 700,
              color: timeLeft < 60 ? '#ef4444' : '#10b981',
              background: timeLeft < 60 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
              padding: '2px 8px', borderRadius: 10
            }}>
              Expires in {formatTime(timeLeft)}
            </span>
          </div>

          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: '#090d16', border: '1px solid #334155', borderRadius: 8,
            padding: '10px 14px', marginBottom: 12
          }}>
            <span style={{
              fontFamily: 'monospace', fontSize: 20, fontWeight: 800,
              color: '#4ade80', letterSpacing: 2
            }}>
              {loading ? 'GENERATING...' : (codeData?.code || 'TOS-....-....')}
            </span>
            <button
              onClick={handleCopyCode}
              disabled={loading || !codeData?.code}
              style={{
                padding: '6px 14px', background: copied ? '#10b981' : '#3b82f6',
                color: '#fff', border: 'none', borderRadius: 6, fontSize: 12,
                fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
              }}
            >
              {copied ? <CheckCircle size={14} /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={handleDeepLink}
              disabled={loading || !codeData?.code}
              style={{
                flex: 1, padding: '10px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                color: '#fff', border: 'none', borderRadius: 8, fontSize: 13,
                fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center',
                justifyContent: 'center', gap: 6, boxShadow: '0 2px 10px rgba(16, 185, 129, 0.3)'
              }}
            >
              <Zap size={15} />
              <span>Connect This Computer (1-Click)</span>
            </button>

            <button
              onClick={generateCode}
              disabled={loading}
              title="Generate New Code"
              style={{
                padding: '10px 14px', background: '#334155', color: '#94a3b8',
                border: 'none', borderRadius: 8, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* 3-Step Guide */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
            Setup Instructions
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12, color: '#cbd5e1' }}>
            <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#334155', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, flexShrink: 0 }}>1</div>
            <div>Download & install <b>TalentOps Scout Desktop</b> (if not already installed).</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12, color: '#cbd5e1' }}>
            <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#334155', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, flexShrink: 0 }}>2</div>
            <div>Launch Scout. Click <b>Connect Account</b> on the first-run prompt.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12, color: '#cbd5e1' }}>
            <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#334155', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, flexShrink: 0 }}>3</div>
            <div>Paste the 10-minute code or click <b>Connect This Computer</b>.</div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 18px', background: '#1e293b', color: '#94a3b8',
              border: '1px solid #334155', borderRadius: 8, fontSize: 12,
              fontWeight: 600, cursor: 'pointer'
            }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
