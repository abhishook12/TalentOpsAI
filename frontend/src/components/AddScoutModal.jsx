import React, { useState, useEffect, useCallback } from 'react';
import { X, Copy, CheckCircle, ExternalLink, ShieldCheck, Laptop, Zap, RefreshCw, Users } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';

export default function AddScoutModal({ isOpen, onClose, onActivated }) {
  const { user, isAdmin } = useAuth();
  const [codeData, setCodeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [timeLeft, setTimeLeft] = useState(600); // 10 mins in sec
  const [targetEmail, setTargetEmail] = useState('');
  const [usersList, setUsersList] = useState([]);

  useEffect(() => {
    if (isOpen && isAdmin) {
      api.get('/scout/provisionable-users')
        .then(res => setUsersList(res.data?.users || []))
        .catch(() => {});
    }
  }, [isOpen, isAdmin]);

  const generateCode = useCallback(async (overrideEmail = null) => {
    setLoading(true);
    const effEmail = overrideEmail !== null ? overrideEmail : targetEmail;
    try {
      const payload = {
        label: effEmail ? `Admin Force-Provision for ${effEmail}` : `Desktop Scout (${new Date().toLocaleDateString()})`,
        expires_minutes: effEmail ? 1440 : 10,
        max_uses: effEmail ? 10 : 1,
      };
      if (effEmail) {
        payload.target_user_email = effEmail;
      }
      const res = await api.post('/scout/codes/generate', payload);
      setCodeData(res.data);
      setTimeLeft(res.data.expires_in_seconds || (effEmail ? 86400 : 600));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate activation code');
    } finally {
      setLoading(false);
    }
  }, [targetEmail]);

  useEffect(() => {
    if (isOpen) {
      generateCode();
    } else {
      setCodeData(null);
      setTargetEmail('');
    }
  }, [isOpen, generateCode]);

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
        background: '#121214', border: '1px solid #232326', borderRadius: 16,
        maxWidth: 520, width: '100%', padding: '28px', color: '#fafafa',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)', position: 'relative'
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 20, right: 20, background: 'transparent',
            border: 'none', color: '#a1a1aa', cursor: 'pointer'
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
            <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: '#fafafa' }}>
              Add TalentOps Scout Node
            </h2>
            <p style={{ fontSize: 12, color: '#a1a1aa', margin: '2px 0 0' }}>
              Pair this computer to your TalentOps account
            </p>
          </div>
        </div>

        {/* Admin Target User Selector */}
        {isAdmin && (
          <div style={{
            background: 'rgba(228, 228, 231, 0.08)', border: '1px solid rgba(228, 228, 231, 0.25)',
            borderRadius: 10, padding: '12px 14px', marginBottom: 16
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#e4e4e7', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 5 }}>
                <Users size={12} />
                <span>Admin Provisioning Target</span>
              </span>
              <span style={{ fontSize: 10, color: '#a1a1aa' }}>
                {targetEmail ? 'Targeted Account' : 'Self (Your Account)'}
              </span>
            </div>
            <select
              value={targetEmail}
              onChange={(e) => {
                const val = e.target.value;
                setTargetEmail(val);
                generateCode(val);
              }}
              style={{
                width: '100%', background: '#0b0b0c', border: '1px solid #27272a', borderRadius: 6,
                color: targetEmail ? '#e4e4e7' : '#fafafa', padding: '6px 10px', fontSize: 12,
                fontWeight: 600, outline: 'none', cursor: 'pointer'
              }}
            >
              <option value="">Self — {user?.email || 'My Account'}</option>
              {usersList.map(u => (
                <option key={u.id} value={u.email}>
                  {u.name} ({u.email})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Activation Code Box */}
        <div style={{
          background: '#232326', border: '1px solid #27272a', borderRadius: 12,
          padding: '18px 20px', marginBottom: 20
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: 0.5 }}>
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
            background: '#0b0b0c', border: '1px solid #27272a', borderRadius: 8,
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
                padding: '6px 14px', background: copied ? '#10b981' : '#d4d4d8',
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
                padding: '10px 14px', background: '#27272a', color: '#a1a1aa',
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
          <div style={{ fontSize: 11, fontWeight: 700, color: '#71717a', textTransform: 'uppercase' }}>
            Setup Instructions
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12, color: '#d4d4d8' }}>
            <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#27272a', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, flexShrink: 0 }}>1</div>
            <div>Download & install <b>TalentOps Scout Desktop</b> (if not already installed).</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12, color: '#d4d4d8' }}>
            <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#27272a', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, flexShrink: 0 }}>2</div>
            <div>Launch Scout. Click <b>Connect Account</b> on the first-run prompt.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12, color: '#d4d4d8' }}>
            <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#27272a', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800, flexShrink: 0 }}>3</div>
            <div>Paste the 10-minute code or click <b>Connect This Computer</b>.</div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 18px', background: '#232326', color: '#a1a1aa',
              border: '1px solid #27272a', borderRadius: 8, fontSize: 12,
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
