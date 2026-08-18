import React, { useState, useEffect, useCallback } from 'react';
import { 
  ShieldCheck, AlertTriangle, XCircle, Mail, Database, 
  Activity, ArrowUpRight, ArrowDownRight, CheckCircle2,
  Trash2, RefreshCw, ChevronRight, BarChart3, Filter,
  Play, Pause, Zap, Clock, Sparkles, Check, Download
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';

export default function MailIntelDashboard() {
  const [stats, setStats] = useState(null);
  const [domains, setDomains] = useState([]);
  const [engineState, setEngineState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sweeping, setSweeping] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, domainsRes, engineRes] = await Promise.all([
        api.get(`/mailintel/stats`),
        api.get(`/mailintel/domains`),
        api.get(`/mailintel/verification-progress`)
      ]);
      
      if (statsRes.data) setStats(statsRes.data);
      if (domainsRes.data) setDomains(domainsRes.data);
      if (engineRes.data) setEngineState(engineRes.data);
    } catch (e) {
      console.error("Error fetching mailintel data", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 8000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRunSweep = async () => {
    setSweeping(true);
    const toastId = toast.loading('Running Global Deliverability Engine & MX Resolution Sweep...');
    try {
      const res = await api.post('/mailintel/sweep');
      toast.success(res.data.message || 'Deliverability sweep completed successfully!', { id: toastId });
      await fetchData();
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || 'Failed to complete deliverability sweep', { id: toastId });
    } finally {
      setSweeping(false);
    }
  };

  const handleExportDeliverability = () => {
    if (!stats) return;
    const reportData = {
      timestamp: new Date().toISOString(),
      deliverability_summary: stats,
      top_domains: domains
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TalentOps_MailIntel_Deliverability_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Deliverability report downloaded successfully!');
  };

  if (loading && !stats) {
    return (
      <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: 12 }}>
        <RefreshCw className="animate-spin" size={24} color="var(--brand)" />
        <span style={{ fontSize: 16, fontWeight: 500 }}>Loading Deliverability Intelligence...</span>
      </div>
    );
  }

  const {
    total = 0,
    total_emails = 0,
    verified = 0,
    likely_valid = 0,
    needs_monitoring = 0,
    invalid = 0,
    missing_emails = 0,
    total_deliverable = 0,
    deliverability_rate = 0,
    average_confidence = 0,
    recent_replied = 0,
    recent_bounced = 0
  } = stats || {};

  return (
    <div style={{
      padding: '2rem 2.5rem',
      maxWidth: '1500px',
      margin: '0 auto',
      animation: 'ccFadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: 20 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 6 }}>
            Campaign Safety & Verification
          </div>
          <h1 style={{ margin: '0 0 0.5rem 0', fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <Mail color="var(--brand)" size={28} />
            MAILINTEL • Deliverability & Verification Engine
          </h1>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 14, maxWidth: 700, lineHeight: 1.5 }}>
            Automated DNS MX resolution, corporate domain verification, and deliverability risk scoring across {total.toLocaleString()} recruiter profiles.
          </p>
        </div>

        {/* Action Controls & Deliverability Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <button 
            onClick={handleRunSweep}
            disabled={sweeping}
            className="cc-primary-button"
            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', fontSize: 13, fontWeight: 600 }}
          >
            {sweeping ? <RefreshCw className="animate-spin" size={16} /> : <Sparkles size={16} />}
            {sweeping ? 'Analyzing Domains...' : 'Run Deliverability Sweep'}
          </button>

          <button 
            onClick={handleExportDeliverability}
            className="cc-ghost-button"
            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', fontSize: 13, fontWeight: 600 }}
          >
            <Download size={16} />
            Export Intel Report
          </button>

          <div style={{ 
            background: 'var(--panel-bg)', 
            padding: '10px 20px', 
            borderRadius: 10, 
            display: 'flex', 
            alignItems: 'center', 
            gap: 16, 
            border: `1px solid var(--card-border)`,
            boxShadow: 'var(--shadow)'
          }}>
            <div>
              <div style={{ fontSize: 10, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.08em', fontWeight: 700, marginBottom: 2 }}>
                Deliverability Rate
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontSize: 24, fontWeight: 800, color: '#10B981', lineHeight: 1 }}>{deliverability_rate}%</span>
                <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(16, 185, 129, 0.15)', color: '#10B981' }}>
                  SAFE
                </span>
              </div>
            </div>
            <ShieldCheck size={32} color="#10B981" opacity={0.8} />
          </div>
        </div>
      </div>

      {/* Deliverability Possibility Matrix Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <MetricCard 
          label="Tier 1: Verified Corporate" 
          value={verified} 
          icon={CheckCircle2} 
          color="#10B981" 
          subtitle="95-100% Delivery Safe" 
        />
        <MetricCard 
          label="Tier 2: Likely Deliverable" 
          value={likely_valid} 
          icon={ShieldCheck} 
          color="#3B82F6" 
          subtitle="75-89% Consumer/Standard" 
        />
        <MetricCard 
          label="Tier 3: Risky / Catch-All" 
          value={needs_monitoring} 
          icon={AlertTriangle} 
          color="#F59E0B" 
          subtitle="Role & Catch-All accounts" 
        />
        <MetricCard 
          label="Tier 4: Undeliverable" 
          value={invalid} 
          icon={XCircle} 
          color="#EF4444" 
          subtitle="Dead MX or disposable" 
        />
        <MetricCard 
          label="Tier 5: Missing / Synthetic" 
          value={missing_emails} 
          icon={Mail} 
          color="var(--text-muted)" 
          subtitle="No email assigned" 
        />
        <MetricCard 
          label="Total Deliverable" 
          value={total_deliverable} 
          icon={Check} 
          color="var(--brand)" 
          subtitle={`Avg Score: ${average_confidence}%`} 
        />
      </div>

      {/* Progress & Live Engine Status Banner */}
      <div className="card" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Zap size={18} color="var(--brand)" />
              Continuous MX Resolution & Handshake Pre-Flight
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>
              100% of candidate profiles validated through asynchronous DNS MX resolution and disposable firewall filters.
            </p>
          </div>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#10B981', background: 'rgba(16, 185, 129, 0.12)', padding: '4px 10px', borderRadius: 999 }}>
            ● Active Multi-Signal Engine
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6, fontWeight: 600 }}>
          <span style={{ color: 'var(--text-secondary)' }}>Deliverability Coverage ({total_deliverable.toLocaleString()} / {total_emails.toLocaleString()} with registered address)</span>
          <span style={{ color: '#10B981' }}>{deliverability_rate}%</span>
        </div>
        <div style={{ width: '100%', height: 8, borderRadius: 4, background: 'var(--bg-elevated)', overflow: 'hidden' }}>
          <div style={{ width: `${deliverability_rate}%`, height: '100%', background: 'linear-gradient(90deg, #10B981, #3B82F6)', borderRadius: 4, transition: 'width 0.6s ease' }} />
        </div>
      </div>

      {/* Domain Deliverability Breakdown Table */}
      <div className="card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <BarChart3 size={18} color="var(--brand)" />
              Enterprise Domain Deliverability & MX Health ({domains.length} major domains)
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>
              Volume, MX deliverability rate, and confidence scores across top employer domains.
            </p>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--table-header-bg, var(--bg-elevated))', borderBottom: '1px solid var(--card-border)' }}>
                <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Corporate Domain</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Total Recruiters</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Deliverability Rate</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Reputation Score</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', textAlign: 'right' }}>MX Status</th>
              </tr>
            </thead>
            <tbody>
              {domains.map((d) => {
                const isSafe = d.success_rate >= 90;
                return (
                  <tr key={d.domain} style={{ borderBottom: '1px solid var(--card-border)', transition: 'background 0.15s ease' }} className="table-row-hover">
                    <td style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      @{d.domain}
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--text-secondary)' }}>
                      {d.total_sent?.toLocaleString() || 0}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 12, fontWeight: 800, color: isSafe ? '#10B981' : '#F59E0B' }}>{d.success_rate}%</span>
                        <div style={{ width: 40, height: 4, borderRadius: 2, background: 'var(--card-border)', overflow: 'hidden' }}>
                          <div style={{ width: `${d.success_rate}%`, height: '100%', background: isSafe ? '#10B981' : '#F59E0B' }} />
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {d.reputation_score}%
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <span style={{ 
                        fontSize: 11, 
                        fontWeight: 700, 
                        padding: '3px 8px', 
                        borderRadius: 4, 
                        background: isSafe ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)', 
                        color: isSafe ? '#10B981' : '#F59E0B' 
                      }}>
                        {isSafe ? 'ACTIVE MX' : 'MONITORED'}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {domains.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No domain records loaded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, icon: Icon, color, subtitle }) {
  return (
    <div className="card" style={{ padding: '1.25rem', position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
          {label}
        </div>
        <Icon size={18} color={color} opacity={0.9} />
      </div>
      <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: 4, letterSpacing: '-0.02em' }}>
        {typeof value === 'number' ? value.toLocaleString() : value ?? '-'}
      </div>
      {subtitle && (
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}
