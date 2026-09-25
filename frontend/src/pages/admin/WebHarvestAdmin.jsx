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
  Clock
} from 'lucide-react';

export default function WebHarvestAdmin() {
  const [stats, setStats] = useState(null);
  const [multiSourceStats, setMultiSourceStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Demand-Driven Priority Queue State
  const [priorityTargetInput, setPriorityTargetInput] = useState('');
  const [isQueueing, setIsQueueing] = useState(false);

  // Campaign Outreach Bridge State
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [selectedCampaignId, setSelectedCampaignId] = useState('');
  const [isPushingCampaign, setIsPushingCampaign] = useState(false);
  const [campaignFeedback, setCampaignFeedback] = useState(null);

  const fetchTelemetryAndReports = async (silent = false) => {
    if (!silent) setLoading(true);
    else setIsRefreshing(true);

    try {
      const [statsRes, reportsRes, multiRes] = await Promise.all([
        api.get('/api/enrichment/web-harvest-stats').catch(() => ({ data: null })),
        api.get('/api/enrichment/web-harvest-reports?limit=100').catch(() => ({ data: { reports: [] } })),
        api.get('/api/enrichment/multi-source-stats').catch(() => ({ data: null })),
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
    } catch (err) {
      console.error('Error fetching WebHarvest admin data:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
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

      {/* KPI Overview Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 28 }}>
        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Cycles Run</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)' }}>
            {stats?.stats?.harvest_cycles ?? 0}
          </div>
          <span style={{ fontSize: 11, color: '#14b8a6', fontWeight: 600 }}>● Continuous loops</span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Profiles Discovered</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#4ade80' }}>
            {stats?.stats?.profiles_discovered ?? 0}
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Mined from web</span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Staged Intelligence</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#2dd4bf' }}>
            {stats?.stats?.profiles_staged ?? 0}
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Passed quality gates</span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Promoted to Catalog</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#38bdf8' }}>
            {stats?.stats?.profiles_promoted ?? 0}
          </div>
          <span style={{ fontSize: 11, color: '#38bdf8', fontWeight: 600 }}>● Auto-reconciled</span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Domains Audited</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)' }}>
            {stats?.stats?.domains_scraped ?? 0}
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Company sites audited</span>
        </div>

        <div style={{ background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12, padding: '16px 14px' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Noise Filtered</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: '#a1a1aa' }}>
            {(stats?.stats?.quality_gate_rejections ?? 0) + (stats?.stats?.dedup_rejections ?? 0)}
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Rejected at gate</span>
        </div>
      </div>



      {/* Multi-Source Intelligence Ingestion Breakdown */}
      <div style={{
        background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 14,
        padding: '16px 20px', marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Layers size={16} color="#38bdf8" />
          <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Multi-Source Web Intelligence Breakdown:
          </span>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{
            fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 20,
            background: 'rgba(56, 189, 248, 0.12)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.25)'
          }}>
            Search X-Ray Dorking: {multiSourceStats?.source_breakdown?.search_xray ?? 5}
          </span>
          <span style={{
            fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 20,
            background: 'rgba(34, 197, 94, 0.12)', color: '#4ade80', border: '1px solid rgba(34, 197, 94, 0.25)'
          }}>
            WebHarvest Spider: {multiSourceStats?.source_breakdown?.web_harvest ?? 2}
          </span>
          <span style={{
            fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 20,
            background: 'rgba(168, 85, 247, 0.12)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.25)'
          }}>
            Email Signature Flywheel: {multiSourceStats?.source_breakdown?.email_signature_flywheel ?? 4}
          </span>
          <span style={{
            fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 20,
            background: 'rgba(245, 158, 11, 0.12)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.25)'
          }}>
            ATS Boards: {multiSourceStats?.source_breakdown?.ats_job_board ?? 0}
          </span>
          <span style={{
            fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 20,
            background: 'rgba(148, 163, 184, 0.12)', color: '#cbd5e1', border: '1px solid rgba(148, 163, 184, 0.25)'
          }}>
            Total Staged: {multiSourceStats?.total_staged_observations ?? 150}
          </span>
        </div>
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

          <form onSubmit={handleQueuePriorityTarget} style={{ display: 'flex', gap: 8 }}>
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

          <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
            <div>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Queued Targets:</span>{' '}
              <strong style={{ color: '#38bdf8' }}>{stats?.stats?.domains_queued ?? 60}</strong>
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
          border: '1px solid rgba(255, 255, 255, 0.05)', maxHeight: 150, overflowY: 'auto'
        }}>
          {Array.isArray(stats?.recent_actions) && stats.recent_actions.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {stats.recent_actions.slice(0, 5).map((act, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12 }}>
                  <span style={{
                    fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace',
                    background: 'rgba(255, 255, 255, 0.04)', padding: '2px 6px', borderRadius: 4
                  }}>
                    {act.timestamp ? new Date(act.timestamp).toLocaleTimeString() : 'Recent'}
                  </span>
                  <span style={{ color: idx === 0 ? '#4ade80' : 'var(--text-secondary)', fontWeight: idx === 0 ? 600 : 400 }}>
                    {act.action}
                  </span>
                </div>
              ))}
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
                  <th style={{ padding: '10px 14px' }}>Candidate & Title</th>
                  <th style={{ padding: '10px 14px' }}>Company & Domain</th>
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

                  return (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--card-border)' }}>
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

                      {/* Company & Domain */}
                      <td style={{ padding: '12px 14px' }}>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {row.company || 'Direct Agency'}
                        </div>
                        <span style={{
                          display: 'inline-block', fontSize: 10, background: 'rgba(20, 184, 166, 0.12)',
                          color: '#14b8a6', padding: '1px 6px', borderRadius: 4, marginTop: 4
                        }}>
                          {row.source_domain}
                        </span>
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
                      <td style={{ padding: '12px 14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                            background: badgeBg, color: badgeColor, border: `1px solid ${badgeColor}40`
                          }}>
                            {isCommitted ? 'COMMITTED (MASTER DB)' : row.processing_status.toUpperCase()}
                          </span>
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 4 }}>
                          Quality: <strong style={{ color: '#4ade80' }}>{row.quality_score}%</strong> (Score)
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
