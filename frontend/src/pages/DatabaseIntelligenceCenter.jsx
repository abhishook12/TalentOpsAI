import React, { useEffect, useState } from 'react';
import api from '../services/api';

const DatabaseIntelligenceCenter = () => {
  const [stats, setStats] = useState(null);
  const [identityStats, setIdentityStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [identityJobLoading, setIdentityJobLoading] = useState(false);
  const [connectors, setConnectors] = useState([]);
  const [aiQuery, setAiQuery] = useState('Find people in US with verified corporate emails');
  const [aiResult, setAiResult] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [chatText, setChatText] = useState('John Doe - 5716175929 - john.doe@datadog.com - Senior SRE');
  const [chatResult, setChatResult] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [statsRes, idRes, connRes] = await Promise.all([
          api.get('/admin/intelligence-stats'),
          api.get('/analytics/identity-quality'),
          api.get('/intelligence/connectors').catch(() => ({ data: { connectors: [] } }))
        ]);
        setStats(statsRes.data);
        setIdentityStats(idRes.data);
        if (connRes?.data?.connectors) {
          setConnectors(connRes.data.connectors);
        }
        setError(null);
      } catch (err) {
        console.error('Failed to fetch intelligence stats:', err);
        setError('Failed to load database intelligence data.');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000); // Poll every 5s for live updates
    return () => clearInterval(interval);
  }, []);

  const handleRunAiQuery = async () => {
    if (!aiQuery.trim()) return;
    setAiLoading(true);
    try {
      const res = await api.post('/intelligence/query', { query: aiQuery });
      setAiResult(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setAiLoading(false);
    }
  };

  const handleTestChatIngest = async () => {
    if (!chatText.trim()) return;
    setChatLoading(true);
    try {
      const res = await api.post('/intelligence/chat-ingest', {
        text: chatText,
        source_platform: 'MICROSOFT_TEAMS',
        sender_name: 'Recruiter Demo'
      });
      setChatResult(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setChatLoading(false);
    }
  };

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-full bg-[#05060b] text-[#e5e7eb]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-red-500 bg-[#05060b] h-full flex items-center justify-center">
        <p className="text-xl font-semibold bg-red-900/20 px-6 py-4 rounded-xl border border-red-500/20">{error}</p>
      </div>
    );
  }

  const { metrics, engine_state } = stats;

  const progressPercent = metrics.total_recruiters > 0 
    ? Math.min(100, Math.round((metrics.total_processed / metrics.total_recruiters) * 100)) 
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0f1e] via-[#070a12] to-[#05060b] text-[#e5e7eb] p-8 font-sans selection:bg-indigo-500/30">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-white/5 pb-6">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-[var(--text-primary)] mb-2">
              Database Intelligence Center
            </h1>
            <p className="text-sm text-gray-400 font-medium max-w-2xl">
              Enterprise-grade recruiter normalization, enrichment, and deduplication engine. 
              Continuously monitoring and improving data quality across the platform.
            </p>
          </div>
          
          {/* Status Badge */}
          <div className={`px-4 py-2 rounded-full text-sm font-semibold flex items-center gap-2 backdrop-blur-md border shadow-lg ${
            engine_state.status === 'Running' 
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-emerald-500/5' 
              : 'bg-gray-500/10 text-gray-400 border-gray-500/20'
          }`}>
            <span className="relative flex h-2.5 w-2.5">
              {engine_state.status === 'Running' && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              )}
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${engine_state.status === 'Running' ? 'bg-emerald-500' : 'bg-gray-500'}`}></span>
            </span>
            Sentinel Engine: {engine_state.status}
          </div>
        </div>

        {/* Global Progress Bar */}
        <div className="bg-[var(--bg-hover)] border border-[var(--border)] rounded-2xl p-6 backdrop-blur-sm shadow-xl relative overflow-hidden group">
          <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          <div className="flex justify-between items-end mb-4 relative z-10">
            <div>
              <h2 className="text-lg font-semibold text-gray-200">Overall Enrichment Progress</h2>
              <p className="text-xs text-gray-400 mt-1">
                {metrics.total_processed.toLocaleString()} of {metrics.total_recruiters.toLocaleString()} profiles processed
              </p>
            </div>
            <span className="text-3xl font-black text-[var(--text-primary)]">
              {progressPercent}%
            </span>
          </div>
          <div className="w-full bg-gray-900/80 rounded-full h-3 mb-2 overflow-hidden shadow-inner border border-black/50">
            <div 
              className="bg-[var(--text-primary)] h-3 rounded-full transition-all duration-1000 ease-out relative"
              style={{ width: `${progressPercent}%` }}
            >
              <div className="absolute inset-0 bg-white/20 w-full animate-[shimmer_2s_infinite]"></div>
            </div>
          </div>
          {engine_state.status === 'Running' && (
            <p className="text-xs text-indigo-300 font-mono mt-3 flex items-center gap-2">
              <svg className="animate-spin h-3 w-3 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {engine_state.current_task}
            </p>
          )}
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          
          <MetricCard 
            title="Profiles Enriched" 
            value={metrics.profiles_enriched.toLocaleString()} 
            icon="✨"
            gradient="from-blue-500 to-cyan-400"
          />
          <MetricCard 
            title="Duplicates Merged" 
            value={metrics.duplicates_merged.toLocaleString()} 
            icon="🔗"
            gradient="from-emerald-500 to-teal-400"
          />
          <MetricCard 
            title="Domains Mapped" 
            value={metrics.domains_mapped.toLocaleString()} 
            icon="🌐"
            gradient="from-[var(--card-border)] to-[var(--card-border-strong)]"
          />
          <MetricCard 
            title="Logos Assigned" 
            value={metrics.logos_assigned.toLocaleString()} 
            icon="🎨"
            gradient="from-pink-500 to-rose-400"
          />

        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Quality Scores */}
          <div className="col-span-1 lg:col-span-2 bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-md shadow-lg hover:bg-white/[0.03] transition-colors">
            <h3 className="text-lg font-semibold text-gray-200 mb-6 flex items-center gap-2">
              <span className="text-xl">📈</span> Quality Indicators
            </h3>
            
            <div className="space-y-6">
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-sm font-medium text-gray-400">Average Completeness Score</span>
                  <span className="text-xl font-bold text-indigo-400">{metrics.average_completeness}%</span>
                </div>
                <div className="w-full bg-gray-900 rounded-full h-2">
                  <div className="bg-indigo-500 h-2 rounded-full transition-all duration-1000" style={{ width: `${metrics.average_completeness}%` }}></div>
                </div>
              </div>
              
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-sm font-medium text-gray-400">Average Email Confidence</span>
                  <span className="text-xl font-bold text-emerald-400">{metrics.average_email_confidence}%</span>
                </div>
                <div className="w-full bg-gray-900 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full transition-all duration-1000" style={{ width: `${metrics.average_email_confidence}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* Review Queue Alert */}
          <div className="col-span-1 bg-gradient-to-br from-amber-500/10 to-orange-600/10 border border-amber-500/20 rounded-2xl p-6 backdrop-blur-md shadow-lg flex flex-col justify-center items-center text-center relative overflow-hidden group">
            <div className="absolute inset-0 bg-amber-500/5 translate-y-full group-hover:translate-y-0 transition-transform duration-500 ease-out"></div>
            
            <div className="relative z-10">
              <div className="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-4 border border-amber-500/30">
                <span className="text-3xl">⚠️</span>
              </div>
              <h3 className="text-3xl font-black text-amber-400 mb-2">{metrics.records_needing_review.toLocaleString()}</h3>
              <p className="text-sm font-medium text-amber-200/80 mb-4">Records require manual review</p>
              
              <button className="px-6 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 rounded-lg text-sm font-semibold transition-colors border border-amber-500/30">
                Open Review Queue
              </button>
            </div>
          </div>
          
        </div>

        {/* Company Identity Quality Section */}
        {identityStats && (
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-md shadow-lg">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-gray-100 flex items-center gap-2">
                <span>🏢</span> Company Identity Engine
              </h3>
              <button 
                onClick={async () => {
                  setIdentityJobLoading(true);
                  await api.post('/analytics/trigger-identity-job');
                  setTimeout(() => setIdentityJobLoading(false), 2000);
                }}
                disabled={identityJobLoading || identityStats.job_state.status === 'running'}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold rounded-lg shadow-md transition-colors"
              >
                {identityStats.job_state.status === 'running' ? 'Job Running...' : 'Trigger Full Identity Sweep'}
              </button>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800">
                <p className="text-sm text-gray-400">Total Companies</p>
                <p className="text-2xl font-bold text-white mt-1">{identityStats.total_companies.toLocaleString()}</p>
              </div>
              <div className="bg-gray-900/50 p-4 rounded-xl border border-emerald-900/30">
                <p className="text-sm text-gray-400">Verified Logos</p>
                <p className="text-2xl font-bold text-emerald-400 mt-1">{identityStats.verified_companies.toLocaleString()}</p>
              </div>
              <div className="bg-gray-900/50 p-4 rounded-xl border border-rose-900/30">
                <p className="text-sm text-gray-400">Missing/Invalid Logos</p>
                <p className="text-2xl font-bold text-rose-400 mt-1">{(identityStats.missing_logos + identityStats.invalid_logos).toLocaleString()}</p>
              </div>
              <div className="bg-gray-900/50 p-4 rounded-xl border border-amber-900/30">
                <p className="text-sm text-gray-400">Unresolved</p>
                <p className="text-2xl font-bold text-amber-400 mt-1">{identityStats.unresolved_companies.toLocaleString()}</p>
              </div>
            </div>

            {identityStats.job_state.status !== 'idle' && (
              <div className="bg-gray-900/30 p-5 rounded-xl border border-indigo-500/20">
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-medium text-indigo-300">Background Job Status: {identityStats.job_state.status.toUpperCase()}</span>
                  <span className="text-gray-400">{identityStats.job_state.processed} / {identityStats.job_state.total_companies} Processed</span>
                </div>
                <div className="w-full bg-gray-900 rounded-full h-2 mb-3">
                  <div 
                    className="bg-indigo-500 h-2 rounded-full transition-all duration-500" 
                    style={{ width: `${identityStats.job_state.total_companies > 0 ? (identityStats.job_state.processed / identityStats.job_state.total_companies) * 100 : 0}%` }}
                  ></div>
                </div>
                <div className="flex gap-4 text-xs text-gray-400">
                  <span>Resolved: {identityStats.job_state.resolved}</span>
                  <span>Unresolved: {identityStats.job_state.unresolved}</span>
                  <span>Merged: {identityStats.job_state.duplicates_merged}</span>
                  <span>Errors: {identityStats.job_state.errors}</span>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Source Connector Hub */}
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-md shadow-xl">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-emerald-500"></span>
                Source Connector Hub & Orchestration
              </h2>
              <p className="text-xs text-gray-400 mt-1">
                Multi-source data ingestion, reliability weights, and field-level provenance contracts.
              </p>
            </div>
            <span className="text-xs font-mono bg-indigo-500/10 text-indigo-300 px-3 py-1.5 rounded-lg border border-indigo-500/20">
              {connectors.length} Connectors Active
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {connectors.map((c) => (
              <div key={c.connector_key} className="bg-gray-900/50 border border-white/5 rounded-xl p-4 hover:border-indigo-500/30 transition-all">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-semibold text-sm text-gray-200">{c.name}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">
                    {Math.round(c.source_reliability * 100)}% Rel
                  </span>
                </div>
                <div className="text-xs text-gray-400 space-y-1 font-mono">
                  <div>Type: <span className="text-gray-300">{c.auth_type}</span></div>
                  <div>Cost/Query: <span className="text-gray-300">${c.cost_per_query_usd.toFixed(2)}</span></div>
                  <div>RPM Cap: <span className="text-gray-300">{c.rate_limit_rpm}</span></div>
                </div>
                <div className="mt-3 flex flex-wrap gap-1">
                  {(c.supported_data_categories || []).slice(0, 3).map((cat) => (
                    <span key={cat} className="text-[10px] bg-white/5 text-gray-400 px-1.5 py-0.5 rounded">
                      {cat}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Query & Chat Intelligence Ingestion Sandbox */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* AI Natural Language Query */}
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-md shadow-xl space-y-4">
            <div>
              <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
                <span className="text-indigo-400">⚡</span> AI Natural Language Evidence Query
              </h3>
              <p className="text-xs text-gray-400 mt-1">
                Translates recruiting questions into structured SQL queries over multi-source provenance.
              </p>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={aiQuery}
                onChange={(e) => setAiQuery(e.target.value)}
                placeholder="e.g. Find engineers in US with verified email"
                className="flex-1 bg-gray-900/80 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={handleRunAiQuery}
                disabled={aiLoading}
                className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-xl transition-all disabled:opacity-50"
              >
                {aiLoading ? 'Querying...' : 'Run Query'}
              </button>
            </div>

            {aiResult && (
              <div className="bg-gray-900/60 border border-white/5 rounded-xl p-4 space-y-3 font-mono text-xs">
                <div className="flex justify-between text-indigo-300 border-b border-white/5 pb-2">
                  <span>Matches: {aiResult.total_matches}</span>
                  <span>Country Filter: {aiResult.parsed_filters?.country || 'All'}</span>
                </div>
                <div className="text-gray-400">
                  Deliverable Email: {aiResult.parsed_filters?.email_deliverable ? 'YES' : 'ANY'} | Mobile Phone: {aiResult.parsed_filters?.has_mobile_phone ? 'YES' : 'ANY'}
                </div>
                {aiResult.results && aiResult.results.length > 0 ? (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {aiResult.results.slice(0, 5).map((r) => (
                      <div key={r.id} className="p-2 bg-black/40 rounded flex justify-between">
                        <span className="text-gray-200 font-sans">{r.canonical_name} ({r.current_company || 'N/A'})</span>
                        <span className="text-emerald-400">{r.primary_email || r.primary_phone || 'Profile Only'}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 italic">No direct matches found for current filters.</div>
                )}
              </div>
            )}
          </div>

          {/* Unstructured Chat Intelligence Ingestion */}
          <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-md shadow-xl space-y-4">
            <div>
              <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
                <span className="text-emerald-400">💬</span> Chat Intelligence Pipeline Tester
              </h3>
              <p className="text-xs text-gray-400 mt-1">
                Ingests messy Google Chat & Microsoft Teams recruiter notes with zero identity fabrication.
              </p>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={chatText}
                onChange={(e) => setChatText(e.target.value)}
                placeholder="e.g. John - 5716175929 - john@abc.com"
                className="flex-1 bg-gray-900/80 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={handleTestChatIngest}
                disabled={chatLoading}
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm rounded-xl transition-all disabled:opacity-50"
              >
                {chatLoading ? 'Ingesting...' : 'Ingest Note'}
              </button>
            </div>

            {chatResult && (
              <div className="bg-gray-900/60 border border-white/5 rounded-xl p-4 space-y-2 font-mono text-xs">
                <div className="flex justify-between text-emerald-400 border-b border-white/5 pb-2">
                  <span>Status: {chatResult.status}</span>
                  <span>Hash: {chatResult.content_hash?.slice(0, 12)}...</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-gray-300">
                  <div>Name: <span className="text-white font-sans">{chatResult.analysis?.extracted_fields?.name || 'None'}</span></div>
                  <div>Phone: <span className="text-white">{chatResult.analysis?.extracted_fields?.primary_phone || 'None'}</span></div>
                  <div>Email: <span className="text-white">{chatResult.analysis?.extracted_fields?.primary_email || 'None'}</span></div>
                  <div>Company: <span className="text-white">{chatResult.analysis?.extracted_fields?.current_company || 'None'}</span></div>
                </div>
                <div className="text-[11px] text-gray-400">
                  Partial Record: <span className={chatResult.analysis?.is_partial ? 'text-amber-400' : 'text-emerald-400'}>{chatResult.analysis?.is_partial ? 'TRUE (Safe Staging)' : 'FALSE (Complete)'}</span> | Score: {Math.round((chatResult.analysis?.confidence_score || 0) * 100)}%
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

const MetricCard = ({ title, value, icon, gradient }) => (
  <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-md shadow-lg hover:bg-white/[0.04] hover:-translate-y-1 transition-all duration-300 relative overflow-hidden">
    <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${gradient} opacity-5 blur-3xl rounded-full -mr-10 -mt-10`}></div>
    <div className="flex items-start justify-between relative z-10">
      <div>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">{title}</p>
        <h4 className="text-3xl font-black text-gray-100">{value}</h4>
      </div>
      <div className="text-2xl bg-[var(--bg-hover)] p-3 rounded-xl border border-[var(--border)] shadow-inner">
        {icon}
      </div>
    </div>
  </div>
);

export default DatabaseIntelligenceCenter;
