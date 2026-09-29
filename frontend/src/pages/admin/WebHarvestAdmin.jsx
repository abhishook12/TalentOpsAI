import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import {
  Globe,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ShieldCheck,
  Server,
  Layers,
  ArrowUpRight,
  Filter,
  Search,
  Activity,
  Radio,
  Clock,
  CloudOff,
  CloudUpload,
  Database,
  TrendingUp
} from 'lucide-react';

export default function WebHarvestAdmin() {
  const [stats, setStats] = useState(null);
  const [multiSourceStats, setMultiSourceStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Offline buffer state
  const [offlineBuffer, setOfflineBuffer] = useState(null);
  const [isFlushing, setIsFlushing] = useState(false);
  const [flushResult, setFlushResult] = useState(null);

  // Demand-Driven Priority Queue State
  const [priorityTargetInput, setPriorityTargetInput] = useState('');
  const [isQueueing, setIsQueueing] = useState(false);

  // Campaign Outreach Bridge State
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [selectedCampaignId, setSelectedCampaignId] = useState('');
  const [isPushingCampaign, setIsPushingCampaign] = useState(false);
  const [campaignFeedback, setCampaignFeedback] = useState(null);

  // Hover state for table rows
  const [hoveredRow, setHoveredRow] = useState(null);

  const fetchTelemetryAndReports = async (silent = false) => {
    if (!silent) setLoading(true);
    else setIsRefreshing(true);

    try {
      const [statsRes, reportsRes, multiRes, bufferRes] = await Promise.all([
        api.get('/api/enrichment/web-harvest-stats').catch(() => ({ data: null })),
        api.get('/api/enrichment/web-harvest-reports?limit=100').catch(() => ({ data: { reports: [] } })),
        api.get('/api/enrichment/multi-source-stats').catch(() => ({ data: null })),
        api.get('/api/enrichment/offline-buffer-status').catch(() => ({ data: null })),
      ]);

      if (statsRes?.data?.web_harvest_engine) {
        setStats(statsRes.data.web_harvest_engine);
      }
      if (Array.isArray(reportsRes?.data?.reports)) {
        setReports(reportsRes.data.reports);
      }
      if (multiRes?.data?.source_breakdown) {
        setMultiSourceStats(multiRes.data);
      }
      if (bufferRes?.data?.offline_buffer) {
        setOfflineBuffer(bufferRes.data.offline_buffer);
      }
    } catch (err) {
      console.error('Error fetching WebHarvest admin data:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleManualFlush = async () => {
    setIsFlushing(true);
    setFlushResult(null);
    try {
      const res = await api.post('/api/enrichment/offline-buffer-flush');
      if (res?.data?.success) {
        setFlushResult(res.data);
        await fetchTelemetryAndReports(true);
      }
    } catch (err) {
      setFlushResult({ success: false, message: 'Flush failed: ' + (err?.response?.data?.detail || err.message) });
    } finally {
      setIsFlushing(false);
      setTimeout(() => setFlushResult(null), 5000);
    }
  };

  const handleQueuePriorityTarget = async (e) => {
    e.preventDefault();
    if (!priorityTargetInput.trim()) return;
    setIsQueueing(true);
    try {
      const res = await api.post('/api/enrichment/priority-queue-target', { company_name: priorityTargetInput.trim() });
      if (res?.data?.success) {
        setPriorityTargetInput('');
        await fetchTelemetryAndReports(true);
      }
    } catch (err) {
      console.error('Failed to queue priority target:', err);
    } finally {
      setIsQueueing(false);
    }
  };


  const handleOpenCampaignModal = async (candidate) => {
    setSelectedCandidate(candidate);
    try {
      const res = await api.get('/campaigns?limit=50');
      const list = res?.data?.items || [];
      setCampaigns(list);
      if (list.length > 0) {
        setSelectedCampaignId(list[0].campaign_id);
      }
    } catch (err) {
      console.error('Error fetching campaigns:', err);
    }
  };

  const handleEnrollInCampaign = async () => {
    if (!selectedCampaignId || !selectedCandidate) return;
    setIsPushingCampaign(true);
    try {
      const res = await api.post('/api/enrichment/push-to-campaign', {
        campaign_id: Number(selectedCampaignId),
        email: selectedCandidate.email,
        name: selectedCandidate.name,
        title: selectedCandidate.title,
        company: selectedCandidate.company,
      });
      if (res?.data?.success) {
        setCampaignFeedback(res.data.message || 'Successfully enrolled recruiter!');
        setTimeout(() => {
          setCampaignFeedback(null);
          setSelectedCandidate(null);
        }, 2500);
      }
    } catch (err) {
      setCampaignFeedback(err?.response?.data?.detail || 'Failed to enroll recruiter.');
    } finally {
      setIsPushingCampaign(false);
    }
  };

  useEffect(() => {
    fetchTelemetryAndReports();
    // Auto-refresh stats every 20 seconds
    const interval = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      fetchTelemetryAndReports(true);
    }, 20000);
    return () => clearInterval(interval);
  }, []);

  const filteredReports = reports.filter((item) => {
    if (filterStatus !== 'ALL') {
      if (filterStatus === 'COMMITTED' && item.processing_status !== 'committed') return false;
      if (filterStatus === 'PENDING' && item.processing_status !== 'pending') return false;
      if (filterStatus === 'REVIEW' && item.processing_status !== 'review') return false;
    }
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const matchName = (item.name || '').toLowerCase().includes(q);
      const matchCompany = (item.company || '').toLowerCase().includes(q);
      const matchEmail = (item.email || '').toLowerCase().includes(q);
      const matchUrl = (item.source_url || '').toLowerCase().includes(q);
      return matchName || matchCompany || matchEmail || matchUrl;
    }
    return true;
  });

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 100px', maxWidth: 1280, margin: '0 auto', width: '100%' }}>
      {/* Header */}
      <header style={{ paddingTop: 32, marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{
              background: 'linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)',
              width: 38, height: 38, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(20, 184, 166, 0.35)'
            }}>
              <Globe size={22} color="#fff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                  WebHarvest Autonomous Discovery Engine
                </h1>
                <span style={{
                  fontSize: 10, fontWeight: 800,
                  background: stats?.is_running ? 'rgba(34, 197, 94, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                  color: stats?.is_running ? '#4ade80' : '#94a3b8',
                  padding: '3px 10px', borderRadius: 20,
                  border: `1px solid ${stats?.is_running ? 'rgba(34, 197, 94, 0.3)' : 'rgba(148, 163, 184, 0.3)'}`
                }}>
                  {stats?.is_running ? '● FULLY AUTONOMOUS 24/7 BACKGROUND WORKER' : '○ IDLE'}
                </span>
              </div>
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, margin: '4px 0 0', maxWidth: 800 }}>
            100% autonomous server-side background worker that continuously searches and crawls corporate team pages and staffing directories. Runs completely hands-free with zero manual input required.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            onClick={() => fetchTelemetryAndReports(true)}
            disabled={isRefreshing}
            style={{
              padding: '9px 14px', background: 'var(--card-bg)', color: 'var(--text-secondary)', border: '1px solid var(--card-border)',
              borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex',
              alignItems: 'center', gap: 6
            }}
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          <div style={{
            padding: '9px 16px', background: 'rgba(20, 184, 166, 0.12)',
            border: '1px solid rgba(20, 184, 166, 0.3)', borderRadius: 8,
            display: 'flex', alignItems: 'center', gap: 8, color: '#14b8a6', fontSize: 12, fontWeight: 700
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%', background: '#14b8a6',
              boxShadow: '0 0 8px #14b8a6', display: 'inline-block'
            }} />
            <span>Autonomous Engine (Zero Manual Input)</span>
          </div>
        </div>
      </header>

      {/* 1. Cycle health ticker */}
      <div style={{ display: 'flex', gap: 20, padding: '10px 18px', background: 'rgba(20,184,166,0.06)', border: '1px solid rgba(20,184,166,0.15)', borderRadius: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: stats?.is_running ? '#22c55e' : '#eab308', boxShadow: stats?.is_running ? '0 0 8px #22c55e' : 'none', display: 'inline-block' }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: stats?.is_running ? '#4ade80' : '#eab308' }}>
            {stats?.is_running ? 'ENGINE RUNNING' : 'ENGINE IDLE'}
          </span>
        </div>
        <span style={{ color: 'var(--card-border)', fontSize: 18 }}>|</span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>{stats?.stats?.harvest_cycles ?? 0}</strong> cycles run
        </span>
        <span style={{ color: 'var(--card-border)', fontSize: 18 }}>|</span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Last cycle: <strong style={{ color: 'var(--text-primary)' }}>
            {stats?.recent_actions?.[0]?.timestamp 
              ? (() => { const diff = Math.floor((Date.now() - new Date(stats.recent_actions[0].timestamp)) / 1000); return diff < 60 ? `${diff}s ago` : `${Math.floor(diff / 60)}m ago`; })()
              : 'Active'
            }
          </strong>
        </span>
        <span style={{ color: 'var(--card-border)', fontSize: 18 }}>|</span>
        {(() => {
          const disc = stats?.stats?.profiles_discovered ?? 0;
          const promoted = stats?.stats?.profiles_promoted ?? 0;
          const rate = disc > 0 ? Math.round((promoted / disc) * 100) : 0;
          const color = rate >= 40 ? '#4ade80' : rate >= 20 ? '#f59e0b' : '#ef4444';
          return (
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Promotion rate: <strong style={{ color }}>{rate}%</strong>
              {rate < 20 && <span style={{ fontSize: 10, color: '#ef4444', marginLeft: 4 }}>(low — check quality gates)</span>}
            </span>
          );
        })()}
        <span style={{ color: 'var(--card-border)', fontSize: 18 }}>|</span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Outreach ready: <strong style={{ color: '#4ade80' }}>
            {reports.filter(r => r.smtp_verification?.smtp_status === 'DELIVERABLE').length}
          </strong>
        </span>
      </div>

      {/* KPI Overview Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 16 }}>
        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Cycles Run</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)' }}>
            {stats?.stats?.harvest_cycles ?? 0}
          </div>
          <span style={{ fontSize: 11, color: '#14b8a6', fontWeight: 600 }}>
            avg {Math.round((stats?.stats?.profiles_discovered ?? 0) / Math.max(stats?.stats?.harvest_cycles ?? 1, 1))} per cycle
          </span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Profiles Discovered</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#4ade80' }}>
            {stats?.stats?.profiles_discovered ?? 0}
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            avg {Math.round((stats?.stats?.profiles_discovered ?? 0) / Math.max(stats?.stats?.harvest_cycles ?? 1, 1))} per cycle
          </span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Staged Intelligence</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#2dd4bf' }}>
            {stats?.stats?.profiles_staged ?? 0}
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            {((stats?.stats?.profiles_staged ?? 0) / Math.max(stats?.stats?.profiles_discovered ?? 1, 1) * 100).toFixed(0)}% pass rate
          </span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Promoted to Catalog</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#38bdf8' }}>
            {stats?.stats?.profiles_promoted ?? 0}
          </div>
          {(() => {
            const disc = stats?.stats?.profiles_discovered ?? 0;
            const promoted = stats?.stats?.profiles_promoted ?? 0;
            const rate = disc > 0 ? Math.round((promoted / disc) * 100) : 0;
            const color = rate >= 40 ? '#4ade80' : rate >= 20 ? '#f59e0b' : '#ef4444';
            return <span style={{ fontSize: 11, color, fontWeight: 600 }}>{rate}% promotion rate</span>;
          })()}
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Domains Audited</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)' }}>
            {stats?.stats?.domains_scraped ?? 0}
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            of {stats?.stats?.domains_queued ?? 0} queued
          </span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Noise Filtered</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#a1a1aa' }}>
            {(stats?.stats?.quality_gate_rejections ?? 0) + (stats?.stats?.dedup_rejections ?? 0)}
          </div>
          {(() => {
            const rejected = (stats?.stats?.quality_gate_rejections ?? 0) + (stats?.stats?.dedup_rejections ?? 0);
            const disc = stats?.stats?.profiles_discovered ?? 0;
            const isLow = disc > 0 && (rejected / disc) < 0.05;
            return (
              <span style={{ fontSize: 11, color: isLow ? '#f59e0b' : 'var(--text-muted)', fontWeight: isLow ? 600 : 400 }}>
                {isLow ? '⚠ Low rejection rate' : 'Rejected at gate'}
              </span>
            );
          })()}
        </div>
      </div>

      {/* Pipeline Funnel */}
      {(stats?.stats?.profiles_discovered ?? 0) > 0 && (() => {
        const disc = stats.stats.profiles_discovered;
        const staged = stats.stats.profiles_staged ?? 0;
        const promoted = stats.stats.profiles_promoted ?? 0;
        const stagedPct = Math.round(staged / disc * 100);
        const promotedPct = Math.round(promoted / disc * 100);
        const geoRejected = stats.stats?.geo_rejections ?? 0;
        const qualityRejected = stats.stats?.quality_gate_rejections ?? 0;
        const dedupRejected = stats.stats?.dedup_rejections ?? 0;
        return (
          <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: '14px 20px', marginBottom: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 10 }}>Pipeline Funnel — Discovery → Staging → Catalog</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
              {/* Discovered bar */}
              <div style={{ flex: disc, background: 'rgba(74,222,128,0.2)', border: '1px solid rgba(74,222,128,0.4)', borderRadius: '6px 0 0 6px', padding: '6px 10px', textAlign: 'center' }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: '#4ade80' }}>{disc}</div>
                <div style={{ fontSize: 9, color: '#4ade80', fontWeight: 700 }}>DISCOVERED</div>
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', padding: '0 4px' }}>→</div>
              {/* Staged */}
              <div style={{ flex: staged, background: 'rgba(45,212,191,0.2)', border: '1px solid rgba(45,212,191,0.4)', padding: '6px 10px', textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: '#2dd4bf' }}>{staged}</div>
                <div style={{ fontSize: 9, color: '#2dd4bf', fontWeight: 700 }}>STAGED ({stagedPct}%)</div>
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', padding: '0 4px' }}>→</div>
              {/* Promoted */}
              <div style={{ flex: promoted, background: 'rgba(56,189,248,0.2)', border: '1px solid rgba(56,189,248,0.4)', borderRadius: '0 6px 6px 0', padding: '6px 10px', textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: '#38bdf8' }}>{promoted}</div>
                <div style={{ fontSize: 9, color: '#38bdf8', fontWeight: 700 }}>PROMOTED ({promotedPct}%)</div>
              </div>
              {/* Drop-off reasons */}
              {(geoRejected + qualityRejected + dedupRejected) > 0 && (
                <div style={{ marginLeft: 16, fontSize: 11, color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)' }}>Drop-offs:</span>
                  {geoRejected > 0 && <span>🌍 Geo gate: {geoRejected}</span>}
                  {qualityRejected > 0 && <span>⚡ Quality gate: {qualityRejected}</span>}
                  {dedupRejected > 0 && <span>🔁 Dedup: {dedupRejected}</span>}
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* Smart Render Watchdog & Offline Buffer Panel — v3 Circuit Breaker */}
      {offlineBuffer && (() => {
        const ob = offlineBuffer;
        const cbState = ob.circuit_state || (ob.render_online ? (ob.render_stable ? 'STABLE' : 'WARMING') : 'OFFLINE');
        const isStable  = cbState === 'STABLE';
        const isWarming = cbState === 'WARMING';
        const isOffline = cbState === 'OFFLINE';
        const isOnline = isStable || isWarming;
        const healthLabel = isStable ? 'STABLE' : isWarming ? 'WARMING' : 'OFFLINE';
        
        const secs = ob.seconds_until_reset ?? 0;
        const hh = Math.floor(secs / 3600);
        const mm = Math.floor((secs % 3600) / 60);
        const ss = secs % 60;
        const countdown = secs > 0
          ? `${hh}h ${String(mm).padStart(2,'0')}m ${String(ss).padStart(2,'0')}s`
          : 'IMMINENT — monthly reset now';
        const pollLabel = (ob.current_poll_interval_sec ?? 30) >= 60
          ? `${Math.floor(ob.current_poll_interval_sec / 60)}m`
          : `${ob.current_poll_interval_sec ?? 30}s`;
        const healthColor = isStable ? '#4ade80' : isWarming ? '#f59e0b' : '#ef4444';
        const borderColor = isStable ? 'rgba(20,184,166,0.3)' : isWarming ? 'rgba(245,158,11,0.4)' : 'rgba(239,68,68,0.3)';
        const bgColor = isStable ? 'rgba(20,184,166,0.05)' : isWarming ? 'rgba(245,158,11,0.06)' : 'rgba(239,68,68,0.07)';

        return (
          <div style={{ background: bgColor, border: `1px solid ${borderColor}`, borderRadius: 14, padding: '14px 20px', marginBottom: 20 }}>
            {/* Header row */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {isStable ? <CloudUpload size={18} color="#14b8a6" /> : isWarming ? <CloudUpload size={18} color="#f59e0b" /> : <CloudOff size={18} color="#ef4444" />}
                <div>
                  <div style={{ fontSize: 12, fontWeight: 800, color: healthColor }}>
                    {isStable
                      ? '● RENDER STABLE — Circuit Closed · Auto-Sync Active'
                      : isWarming
                      ? '◑ RENDER WARMING — Circuit Half-Open · Trial Batches Active'
                      : '⚠ RENDER OFFLINE — Circuit Open · Buffer Mode Active'}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                    {isStable
                      ? `${ob.total_flushed ?? 0} profiles flushed · ${ob.flush_sessions ?? 0} sessions · ${ob.render_uptime_pct ?? 100}% uptime`
                      : isWarming
                      ? `Trial flushing 5 records/cycle · Confirming stability · ${ob.pending_buffered ?? 0} queued`
                      : `${ob.pending_buffered ?? 0} queued · Poll every ${pollLabel} · Next reset ${countdown}`
                    }
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <button
                  onClick={handleManualFlush}
                  disabled={isFlushing || (ob.pending_buffered ?? 0) === 0}
                  style={{
                    padding: '7px 13px', borderRadius: 8, fontSize: 11, fontWeight: 700, cursor: 'pointer',
                    background: (ob.pending_buffered ?? 0) === 0 ? 'rgba(148,163,184,0.08)' : 'rgba(20,184,166,0.15)',
                    color: (ob.pending_buffered ?? 0) === 0 ? '#64748b' : '#14b8a6',
                    border: `1px solid ${(ob.pending_buffered ?? 0) === 0 ? 'rgba(148,163,184,0.15)' : 'rgba(20,184,166,0.3)'}`,
                    display: 'flex', alignItems: 'center', gap: 5
                  }}
                >
                  <Database size={11} />
                  {isFlushing ? 'Flushing...' : 'Force Flush'}
                </button>
              </div>
            </div>

            {/* Metrics row */}
            <div style={{ display: 'flex', gap: 20, marginTop: 14, flexWrap: 'wrap', alignItems: 'flex-start' }}>
              {/* Pending */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: (ob.pending_buffered ?? 0) > 0 ? '#f59e0b' : '#4ade80' }}>
                  {ob.pending_buffered ?? 0}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Pending</div>
              </div>

              {/* In Retry Cooldown */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: (ob.in_retry_cooldown ?? 0) > 0 ? '#a78bfa' : '#52525b' }}>
                  {ob.in_retry_cooldown ?? 0}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>In Backoff</div>
              </div>

              {/* Flushed */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: '#4ade80' }}>
                  {ob.total_flushed ?? 0}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Flushed</div>
              </div>

              {/* DLQ / Failed */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: (ob.total_failed ?? 0) > 0 ? '#f87171' : '#52525b' }}>
                  {ob.total_failed ?? 0}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>DLQ</div>
              </div>

              <div style={{ width: 1, background: 'var(--card-border)', alignSelf: 'stretch' }} />

              {/* Render Health */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 14, fontWeight: 800, color: healthColor }}>{healthLabel}</div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Health</div>
              </div>

              {/* Probe latency */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 14, fontWeight: 800, color: (ob.render_probe_ms ?? 0) > 2000 ? '#f59e0b' : '#94a3b8' }}>
                  {ob.render_probe_ms > 0 ? `${ob.render_probe_ms}ms` : '—'}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Probe RT</div>
              </div>

              {/* Uptime */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 14, fontWeight: 800, color: '#94a3b8' }}>{ob.render_uptime_pct ?? 100}%</div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Uptime</div>
              </div>

              {/* Adaptive poll interval */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 14, fontWeight: 800, color: '#94a3b8' }}>{pollLabel}</div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Poll Rate</div>
              </div>

              {/* DB size */}
              <div style={{ textAlign: 'center', minWidth: 60 }}>
                <div style={{ fontSize: 14, fontWeight: 800, color: '#94a3b8' }}>{ob.buffer_db_size_kb ?? 0} KB</div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Buffer DB</div>
              </div>

              {/* Oct 1 countdown */}
              {!isOnline && secs > 0 && (
                <>
                  <div style={{ width: 1, background: 'var(--card-border)', alignSelf: 'stretch' }} />
                  <div style={{ textAlign: 'center', minWidth: 80 }}>
                    <div style={{ fontSize: 13, fontWeight: 800, color: '#f59e0b', fontVariantNumeric: 'tabular-nums' }}>
                      {countdown}
                    </div>
                    <div style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                      Until Reset (Oct 1)
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Source tier breakdown */}
            {(ob.tier_breakdown ?? []).length > 0 && (
              <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 700, alignSelf: 'center' }}>PRIORITY QUEUE:</span>
                {(ob.tier_breakdown ?? []).map(t => (
                  <span key={t.tier} style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                    background: t.tier === 1 ? 'rgba(251,191,36,0.15)' : t.tier === 2 ? 'rgba(56,189,248,0.12)' : 'rgba(148,163,184,0.1)',
                    color: t.tier === 1 ? '#fbbf24' : t.tier === 2 ? '#38bdf8' : '#94a3b8',
                    border: `1px solid ${t.tier === 1 ? 'rgba(251,191,36,0.3)' : t.tier === 2 ? 'rgba(56,189,248,0.2)' : 'rgba(148,163,184,0.15)'}`,
                  }}>
                    {t.tier === 1 ? '🔴 Tier 1 (Scout)' : t.tier === 2 ? '🟡 Tier 2 (X-Ray)' : '⚪ Tier 3 (Web)'}: {t.count}
                  </span>
                ))}
              </div>
            )}

            {/* Flush feedback */}
            {flushResult && (
              <div style={{ fontSize: 11, fontWeight: 600, marginTop: 8, color: flushResult.success ? '#4ade80' : '#f87171' }}>
                {flushResult.message}
              </div>
            )}
          </div>
        );
      })()}

      {/* Multi-Source Intelligence Ingestion Breakdown — upgraded */}
      <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 14, padding: '16px 20px', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Layers size={16} color="#38bdf8" />
          <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Multi-Source Intelligence Breakdown</span>
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>Total Staged: <strong style={{ color: 'var(--text-primary)' }}>{multiSourceStats?.total_staged_observations ?? 0}</strong></span>
        </div>
        {(() => {
          const total = Math.max(multiSourceStats?.total_staged_observations ?? 1, 1);
          const sources = [
            { label: 'Search X-Ray Dorking', key: 'search_xray', count: multiSourceStats?.source_breakdown?.search_xray ?? 0, color: '#38bdf8', icon: '🔍' },
            { label: 'WebHarvest Spider', key: 'web_harvest', count: multiSourceStats?.source_breakdown?.web_harvest ?? 0, color: '#4ade80', icon: '🕷' },
            { label: 'Email Signature Flywheel', key: 'email_signature', count: multiSourceStats?.source_breakdown?.email_signature_flywheel ?? 0, color: '#c084fc', icon: '✉️' },
            { label: 'ATS Boards', key: 'ats_boards', count: multiSourceStats?.source_breakdown?.ats_job_board ?? 0, color: '#fbbf24', icon: '📋', warnIfZero: true },
          ];
          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {sources.map(src => {
                const pct = Math.round((src.count / total) * 100);
                const isZero = src.count === 0;
                const isDead = isZero && src.warnIfZero;
                return (
                  <div key={src.key} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 13, minWidth: 20 }}>{src.icon}</span>
                    <span style={{ fontSize: 11, fontWeight: 600, color: isDead ? '#ef4444' : 'var(--text-secondary)', minWidth: 180 }}>
                      {src.label}
                      {isDead && <span style={{ fontSize: 9, color: '#ef4444', marginLeft: 6, fontWeight: 800 }}>⚠ INACTIVE</span>}
                    </span>
                    <div style={{ flex: 1, background: 'rgba(255,255,255,0.05)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
                      <div style={{ width: `${Math.max(pct, 0)}%`, height: '100%', background: isDead ? '#374151' : src.color, borderRadius: 4, transition: 'width 0.5s ease' }} />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: isDead ? '#6b7280' : src.color, minWidth: 40, textAlign: 'right' }}>
                      {src.count}
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', minWidth: 36, textAlign: 'right' }}>
                      {isZero ? '—' : `${pct}%`}
                    </span>
                  </div>
                );
              })}
            </div>
          );
        })()}
      </div>

      {/* Demand-Driven Priority Harvest Queue */}
      <div style={{
        background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 14,
        padding: '16px 20px', marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 12
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16 }}>🎯</span>
            <div>
              <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Demand-Driven Priority Harvest Queue
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
                (Instant target prioritization for next autonomous cycle)
              </span>
            </div>
          </div>

          <form onSubmit={handleQueuePriorityTarget} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 2 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', alignSelf: 'center' }}>Quick targets:</span>
              {['Stripe', 'Databricks', 'Snowflake', 'Notion', 'Linear', 'Figma', 'Vercel'].map(co => (
                <button
                  type="button"
                  key={co}
                  onClick={() => setPriorityTargetInput(co)}
                  style={{ fontSize: 11, padding: '3px 8px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-secondary)', cursor: 'pointer', fontWeight: 600 }}
                >
                  {co}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                placeholder="e.g. Stripe, Datadog, Databricks..."
                value={priorityTargetInput}
                onChange={(e) => setPriorityTargetInput(e.target.value)}
                style={{
                  background: 'var(--input-bg, #1c1c1f)', border: '1px solid var(--card-border, #2d2d30)',
                  color: 'var(--text-primary)', padding: '7px 12px', borderRadius: 8, fontSize: 12, outline: 'none', width: 240
                }}
              />
              <button
                type="submit"
                disabled={isQueueing || !priorityTargetInput.trim()}
                style={{
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', color: '#fff',
                  border: 'none', borderRadius: 8, padding: '7px 14px', fontSize: 12, fontWeight: 700,
                  cursor: (isQueueing || !priorityTargetInput.trim()) ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: 6
                }}
              >
                <span>{isQueueing ? 'Queueing...' : '+ Queue Target'}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Queued Targets Pills */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Pending Priority Targets:</span>
          {stats?.priority_targets?.length > 0 ? (
            stats.priority_targets.map((pt, i) => (
              <span key={i} style={{
                background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)',
                color: '#34d399', fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
                display: 'inline-flex', alignItems: 'center', gap: 4
              }}>
                <span>⚡ {pt.company_name}</span>
                <span style={{ fontSize: 9, opacity: 0.7 }}>({pt.domain})</span>
              </span>
            ))
          ) : (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No custom targets queued. Engine is auditing registry & parquet seeds.
            </span>
          )}
        </div>
      </div>

      {/* Live Engine Radar & Autonomous Activity Stream */}
      <div style={{
        background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 16,
        padding: '20px 24px', marginBottom: 28, position: 'relative', overflow: 'hidden'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: stats?.is_running ? '#22c55e' : '#eab308',
              boxShadow: stats?.is_running ? '0 0 10px #22c55e' : 'none'
            }} />
            <h3 style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Live Autonomous Crawler Radar & Telemetry Stream
            </h3>
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 12,
              background: 'rgba(20, 184, 166, 0.12)', color: '#14b8a6', border: '1px solid rgba(20, 184, 166, 0.25)'
            }}>
              {stats?.is_running ? '24/7 ACTIVE BACKGROUND WORKER' : 'INITIALIZING'}
            </span>
          </div>

          <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)', alignItems: 'center' }}>
            {(() => {
              const discovered = stats?.stats?.profiles_discovered ?? 0;
              const cycles = stats?.stats?.harvest_cycles ?? 1;
              const perCycle = cycles > 0 ? (discovered / cycles).toFixed(1) : 0;
              const healthScore = perCycle >= 10 ? 'EXCELLENT' : perCycle >= 5 ? 'GOOD' : perCycle >= 2 ? 'FAIR' : 'LOW';
              const healthColor = perCycle >= 10 ? '#4ade80' : perCycle >= 5 ? '#2dd4bf' : perCycle >= 2 ? '#f59e0b' : '#ef4444';
              return (
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Yield: <strong style={{ color: healthColor }}>{perCycle}/cycle</strong>
                  <span style={{ marginLeft: 6, fontSize: 10, padding: '1px 6px', borderRadius: 4, background: `rgba(${healthColor === '#4ade80' ? '74,222,128' : healthColor === '#2dd4bf' ? '45,212,191' : healthColor === '#f59e0b' ? '245,158,11' : '239,68,68'},0.12)`, color: healthColor }}>{healthScore}</span>
                </div>
              );
            })()}
            <span style={{ color: 'var(--card-border)' }}>|</span>
            <div>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Queued Targets:</span>{' '}
              <strong style={{ color: '#38bdf8' }}>{stats?.stats?.domains_queued ?? 0}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Active Crawled:</span>{' '}
              <strong style={{ color: '#4ade80' }}>{stats?.stats?.domains_scraped ?? 0}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Cooldown:</span>{' '}
              <strong style={{ color: 'var(--text-primary)' }}>{stats?.domains_on_cooldown ?? 0}</strong>
            </div>
          </div>
        </div>

        {/* Action Feed */}
        <div style={{
          background: 'rgba(0, 0, 0, 0.25)', borderRadius: 10, padding: '12px 16px',
          border: '1px solid rgba(255, 255, 255, 0.05)', maxHeight: 220, overflowY: 'auto'
        }}>
          {Array.isArray(stats?.recent_actions) && stats.recent_actions.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {stats.recent_actions.slice(0, 10).map((act, idx) => {
                const text = (act.action || '').toLowerCase();
                let color = 'var(--text-secondary)';
                if (text.includes('xray') || text.includes('dorking')) color = '#38bdf8';
                else if (text.includes('spider')) color = '#4ade80';
                else if (text.includes('completed')) color = '#2dd4bf';
                else if (text.includes('error') || text.includes('failed')) color = '#ef4444';

                return (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12 }}>
                    <span style={{
                      fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace',
                      background: 'rgba(255, 255, 255, 0.04)', padding: '2px 6px', borderRadius: 4, minWidth: 64, textAlign: 'center'
                    }}>
                      {act.timestamp ? new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Recent'}
                    </span>
                    <span style={{ color, fontWeight: idx === 0 ? 600 : 400 }}>
                      {act.action}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 12 }}>
              <Clock size={14} color="#14b8a6" />
              <span>Autonomous engine active — background crawler is executing live scrapes and email permutation probes.</span>
            </div>
          )}
        </div>
      </div>

      {/* Reports & Provenance Section */}
      <div style={{
        background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 16,
        padding: '24px', marginBottom: 28
      }}>
        {/* Controls Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              Live Provenance & Discovery Reports
            </h3>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '4px 0 0' }}>
              Full audit trail: exact source URLs, extraction confidence, and master catalog promotions.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            {/* Search */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, background: 'var(--panel-bg)',
              border: '1px solid var(--card-border)', borderRadius: 8, padding: '6px 12px'
            }}>
              <Search size={14} color="var(--text-muted)" />
              <input
                type="text"
                placeholder="Search name, company, email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  background: 'transparent', border: 'none', color: 'var(--text-primary)',
                  fontSize: 12, outline: 'none', width: 220
                }}
              />
            </div>

            {/* Status Filter */}
            <div style={{ display: 'flex', gap: 4, background: 'var(--panel-bg)', padding: 3, borderRadius: 8, border: '1px solid var(--card-border)' }}>
              {['ALL', 'COMMITTED', 'PENDING'].map((status) => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  style={{
                    padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer',
                    background: filterStatus === status ? 'var(--card-bg)' : 'transparent',
                    color: filterStatus === status ? 'var(--text-primary)' : 'var(--text-muted)'
                  }}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Reports Table */}
        {loading ? (
          <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            ⏳ Loading harvest reports from database...
          </div>
        ) : filteredReports.length === 0 ? (
          <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            🌐 No records matching criteria. The background crawler will populate discoveries automatically.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--card-border)', color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase' }}>
                  <th style={{ padding: '10px 14px' }}>Candidate & Title ({filteredReports.length})</th>
                  <th style={{ padding: '10px 14px' }}>Company & Geo</th>
                  <th style={{ padding: '10px 14px' }}>Contact Intelligence</th>
                  <th style={{ padding: '10px 14px' }}>Provenance & Source URL</th>
                  <th style={{ padding: '10px 14px' }}>Quality / Decision</th>
                  <th style={{ padding: '10px 14px' }}>Discovered</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right' }}>Outreach Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredReports.map((row, idx) => {
                  const isCommitted = row.processing_status === 'committed';
                  const isPending = row.processing_status === 'pending';
                  const badgeColor = isCommitted ? '#4ade80' : isPending ? '#38bdf8' : '#f59e0b';
                  const badgeBg = isCommitted ? 'rgba(34, 197, 94, 0.15)' : isPending ? 'rgba(56, 189, 248, 0.15)' : 'rgba(245, 158, 11, 0.15)';
                  const geo = row.geo_region || 'NA';

                  return (
                    <tr 
                      key={idx} 
                      onMouseEnter={() => setHoveredRow(idx)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={{ 
                        borderBottom: '1px solid var(--card-border)',
                        background: hoveredRow === idx ? 'rgba(255,255,255,0.02)' : 'transparent',
                        transition: 'background 0.2s ease'
                      }}
                    >
                      {/* Candidate Name & Title */}
                      <td style={{ padding: '12px 14px' }}>
                        <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 13 }}>
                          {row.name || '—'}
                        </div>
                        <div style={{ color: row.title ? 'var(--text-secondary)' : 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>
                          {row.title || '—'}
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: 2 }}>
                          {row.discovery_id}
                        </div>
                      </td>

                      {/* Company & Geo */}
                      <td style={{ padding: '12px 14px' }}>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {row.company || 'Direct Agency'}
                        </div>
                        <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                          <span style={{
                            display: 'inline-block', fontSize: 10, background: 'rgba(20, 184, 166, 0.12)',
                            color: '#14b8a6', padding: '1px 6px', borderRadius: 4
                          }}>
                            {row.source_domain}
                          </span>
                          <span style={{
                            display: 'inline-block', fontSize: 10, background: 'rgba(255, 255, 255, 0.1)',
                            color: 'var(--text-secondary)', padding: '1px 6px', borderRadius: 4, fontWeight: 700
                          }}>
                            {geo}
                          </span>
                        </div>
                      </td>

                      {/* Contact Info */}
                      <td style={{ padding: '12px 14px' }}>
                        {row.email ? (
                          <>
                            <div style={{ color: 'var(--text-primary)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                              <span>✉️</span>
                              <span>{row.email}</span>
                            </div>
                            {row.smtp_verification?.smtp_status === 'DELIVERABLE' && (
                              <div style={{
                                display: 'inline-flex', alignItems: 'center', gap: 4,
                                fontSize: 9, fontWeight: 700, color: '#4ade80',
                                background: 'rgba(34, 197, 94, 0.12)', border: '1px solid rgba(34, 197, 94, 0.25)',
                                padding: '1px 6px', borderRadius: 4, marginTop: 3
                              }}>
                                <ShieldCheck size={10} color="#4ade80" />
                                <span>SMTP Handshake 250 OK (Mailbox Active)</span>
                              </div>
                            )}
                            {row.smtp_verification?.smtp_status === 'CATCH_ALL' && (
                              <div style={{
                                display: 'inline-flex', alignItems: 'center', gap: 4,
                                fontSize: 9, fontWeight: 700, color: '#f59e0b',
                                background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.25)',
                                padding: '1px 6px', borderRadius: 4, marginTop: 3
                              }}>
                                <span>● Catch-All Domain (MX Active)</span>
                              </div>
                            )}
                            {row.smtp_verification?.smtp_status === 'MX_VERIFIED' && (
                              <div style={{
                                display: 'inline-flex', alignItems: 'center', gap: 4,
                                fontSize: 9, fontWeight: 700, color: '#38bdf8',
                                background: 'rgba(56, 189, 248, 0.12)', border: '1px solid rgba(56, 189, 248, 0.25)',
                                padding: '1px 6px', borderRadius: 4, marginTop: 3
                              }}>
                                <span>● DNS MX Verified</span>
                              </div>
                            )}
                          </>
                        ) : (
                          <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>No email</div>
                        )}
                        {row.phone && (
                          <div style={{ color: 'var(--text-secondary)', fontSize: 11, marginTop: 2 }}>
                            📞 {row.phone}
                          </div>
                        )}
                        {row.linkedin && (
                          <a
                            href={row.linkedin}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: '#38bdf8', fontSize: 10, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 2, marginTop: 2 }}
                          >
                            LinkedIn <ArrowUpRight size={10} />
                          </a>
                        )}
                      </td>

                      {/* Provenance URL */}
                      <td style={{ padding: '12px 14px', maxWidth: 260 }}>
                        {row.source_url ? (
                          <a
                            href={row.source_url}
                            target="_blank"
                            rel="noreferrer"
                            title={row.source_url}
                            style={{
                              color: 'var(--text-secondary)', textDecoration: 'none', fontSize: 11,
                              display: 'inline-flex', alignItems: 'center', gap: 4,
                              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 240
                            }}
                          >
                            <span>🌐</span>
                            <span style={{ textDecoration: 'underline' }}>{row.source_url.replace('https://', '').replace('http://', '')}</span>
                            <ExternalLink size={10} />
                          </a>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                          Method: {row.discovery_method}
                        </div>
                      </td>

                      {/* Quality & Decision */}
                      <td style={{ padding: '12px 14px', minWidth: 140 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                            background: badgeBg, color: badgeColor, border: `1px solid ${badgeColor}40`
                          }}>
                            {isCommitted ? 'COMMITTED (MASTER DB)' : (row.processing_status || '').toUpperCase()}
                          </span>
                        </div>
                        <div style={{ marginTop: 6 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                            <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>Quality</span>
                            <span style={{ fontSize: 10, fontWeight: 700, color: (row.quality_score ?? 0) >= 80 ? '#4ade80' : (row.quality_score ?? 0) >= 60 ? '#f59e0b' : '#ef4444' }}>
                              {row.quality_score ?? 0}%
                            </span>
                          </div>
                          <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 4, height: 3 }}>
                            <div style={{ width: `${row.quality_score ?? 0}%`, height: '100%', background: (row.quality_score ?? 0) >= 80 ? '#4ade80' : (row.quality_score ?? 0) >= 60 ? '#f59e0b' : '#ef4444', borderRadius: 4 }} />
                          </div>
                        </div>
                      </td>

                      {/* Timestamp */}
                      <td style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: 11 }}>
                        {row.created_at ? new Date(row.created_at).toLocaleDateString() : '—'}
                        <div style={{ fontSize: 10 }}>
                          {row.created_at ? new Date(row.created_at).toLocaleTimeString() : ''}
                        </div>
                      </td>

                      {/* Outreach Action */}
                      <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                        {row.email ? (
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                            {row.smtp_verification?.smtp_status === 'DELIVERABLE' && (
                              <span style={{
                                fontSize: 9, fontWeight: 800, padding: '2px 6px', borderRadius: 4,
                                background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', border: '1px solid rgba(34, 197, 94, 0.3)',
                                textTransform: 'uppercase', letterSpacing: '0.04em'
                              }}>
                                ⚡ OUTREACH READY
                              </span>
                            )}
                            <button
                              onClick={() => handleOpenCampaignModal(row)}
                              style={{
                                padding: '5px 10px',
                                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                color: '#ffffff',
                                border: 'none',
                                borderRadius: 6,
                                fontSize: 11,
                                fontWeight: 700,
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 5,
                                boxShadow: '0 2px 6px rgba(16, 185, 129, 0.25)',
                                whiteSpace: 'nowrap'
                              }}
                            >
                              <span>✉️</span>
                              <span>Push to Campaign</span>
                            </button>
                          </div>
                        ) : (
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>No Contact</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Campaign Selection Modal */}
      {selectedCandidate && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: 20
        }}>
          <div style={{
            background: 'var(--card-bg, #18181b)',
            border: '1px solid var(--card-border, #27272a)',
            borderRadius: 14,
            width: '100%',
            maxWidth: 480,
            padding: 24,
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
            position: 'relative'
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 8px' }}>
              Push Recruiter to Campaign
            </h3>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '0 0 20px' }}>
              Enroll discovered recruiter directly into an active outreach sequence.
            </p>

            <div style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: 8,
              padding: '12px 16px',
              marginBottom: 20
            }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                {selectedCandidate.name || 'Discovered Recruiter'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                {selectedCandidate.title || 'Recruiting Specialist'} • {selectedCandidate.company || 'Direct Agency'}
              </div>
              <div style={{ fontSize: 12, color: '#38bdf8', fontFamily: 'monospace', marginTop: 4 }}>
                ✉️ {selectedCandidate.email}
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Select Target Outreach Campaign:
              </label>
              {campaigns.length > 0 ? (
                <select
                  value={selectedCampaignId}
                  onChange={(e) => setSelectedCampaignId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 8,
                    background: 'var(--panel-bg, #09090b)',
                    border: '1px solid var(--card-border, #27272a)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    outline: 'none'
                  }}
                >
                  {campaigns.map((camp) => (
                    <option key={camp.campaign_id} value={camp.campaign_id}>
                      {camp.name} ({camp.status || 'Active'})
                    </option>
                  ))}
                </select>
              ) : (
                <div style={{ fontSize: 12, color: '#f59e0b', padding: '8px 0' }}>
                  ⚠️ No active campaigns found. Please create a campaign in Campaigns tab first.
                </div>
              )}
            </div>

            {campaignFeedback && (
              <div style={{
                padding: '10px 14px',
                borderRadius: 8,
                fontSize: 12,
                fontWeight: 600,
                marginBottom: 16,
                background: campaignFeedback.includes('Success') || campaignFeedback.includes('enrolled')
                  ? 'rgba(34, 197, 94, 0.15)'
                  : 'rgba(239, 68, 68, 0.15)',
                color: campaignFeedback.includes('Success') || campaignFeedback.includes('enrolled')
                  ? '#4ade80'
                  : '#f87171',
                border: `1px solid ${campaignFeedback.includes('Success') || campaignFeedback.includes('enrolled') ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
              }}>
                {campaignFeedback}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                onClick={() => { setSelectedCandidate(null); setCampaignFeedback(null); }}
                style={{
                  padding: '8px 16px',
                  borderRadius: 8,
                  border: '1px solid var(--card-border, #27272a)',
                  background: 'transparent',
                  color: 'var(--text-secondary)',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleEnrollInCampaign}
                disabled={isPushingCampaign || !selectedCampaignId || campaigns.length === 0}
                style={{
                  padding: '8px 18px',
                  borderRadius: 8,
                  border: 'none',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: '#ffffff',
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: isPushingCampaign || !selectedCampaignId ? 'not-allowed' : 'pointer',
                  boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                {isPushingCampaign ? 'Enrolling...' : 'Enroll in Sequence'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
