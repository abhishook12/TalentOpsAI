import React, { useEffect, useState } from 'react';
import api from '../services/api';

const DatabaseIntelligenceCenter = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get('/admin/intelligence-stats');
        setStats(response.data);
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
