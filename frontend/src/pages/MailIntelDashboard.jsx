import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, AlertTriangle, XCircle, Mail, Database, 
  Activity, ArrowUpRight, ArrowDownRight, CheckCircle2,
  Trash2, RefreshCw, ChevronRight, BarChart3, Filter,
  Play, Pause, Zap, Clock
} from 'lucide-react';

import api from '../services/api';

const StatCard = ({ title, value, subtitle, icon: Icon, colorClass, gradientClass }) => (
  <div className={`relative overflow-hidden rounded-2xl p-6 ${gradientClass} border border-white/5 shadow-xl transition-all hover:scale-[1.02] hover:shadow-2xl`}>
    <div className="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-white/10 rounded-full blur-3xl pointer-events-none" />
    <div className="relative z-10 flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-white/70 mb-1">{title}</p>
        <h3 className="text-3xl font-bold text-white tracking-tight">{value}</h3>
        {subtitle && <p className="text-xs font-medium mt-2 opacity-80">{subtitle}</p>}
      </div>
      <div className={`p-3 rounded-xl bg-white/10 ${colorClass}`}>
        <Icon size={24} />
      </div>
    </div>
  </div>
);

export default function MailIntelDashboard() {
  const [stats, setStats] = useState(null);
  const [domains, setDomains] = useState([]);
  const [engineState, setEngineState] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchEngineState, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
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
    }
    setLoading(false);
  };

  const fetchEngineState = async () => {
    try {
      const res = await api.get(`/mailintel/verification-progress`);
      if (res.data) setEngineState(res.data);
    } catch (e) {
      console.error("Error polling engine state", e);
    }
  };

  const toggleEngine = async (action) => {
    try {
      const endpoint = action === 'start' ? 'start-verification' : 'pause-verification';
      await api.post(`/mailintel/${endpoint}`);
      fetchEngineState();
    } catch (e) {
      console.error(`Failed to ${action} engine`, e);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-gray-400 font-medium">Gathering Intelligence...</p>
        </div>
      </div>
    );
  }

  const engineRunning = engineState?.is_running && !engineState?.is_paused;
  const enginePaused = engineState?.is_running && engineState?.is_paused;
  const totalProcessed = engineState?.total_processed || 0;
  const totalPending = engineState?.total_pending || (stats?.never_checked || 0);
  const totalEmails = totalProcessed + totalPending;
  const progressPercent = totalEmails > 0 ? (totalProcessed / totalEmails) * 100 : 0;

  return (
    <div className="flex-1 min-h-screen bg-[#0A0A0B] text-white p-8">
      {/* Header */}
      <div className="mb-10 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg border" style={{ background: 'var(--brand-bg)', borderColor: 'var(--brand-bg)' }}>
              <Activity size={24} style={{ color: 'var(--brand-strong)' }} />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white">MAILINTEL</h1>
          </div>
          <p className="text-gray-400 text-sm">Enterprise Email Intelligence & Validation Engine</p>
        </div>
        
        <div className="flex gap-4">
          <button onClick={fetchData} className="px-4 py-2 rounded-lg bg-[var(--bg-hover)] border border-[var(--border)] hover:bg-[var(--bg-hover)] text-sm font-medium flex items-center gap-2 transition-colors">
            <RefreshCw size={16} /> Sync Intelligence
          </button>
        </div>
      </div>

      {/* VERIFICATION ENGINE LIVE PANEL */}
      <div className="mb-8 bg-[#121214] border border-[var(--border)] rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-6 relative z-10 gap-4">
          <div>
            <h3 className="text-xl font-bold text-white flex items-center gap-3">
              <Database size={22} style={{ color: 'var(--brand)' }} />
              Active Verification Engine
              {engineRunning && <span className="flex h-3 w-3 rounded-full bg-emerald-500 shadow-[0_0_10px_#10b981] animate-pulse"></span>}
              {enginePaused && <span className="flex h-3 w-3 rounded-full bg-amber-500 shadow-[0_0_10px_#f59e0b]"></span>}
              {!engineState?.is_running && <span className="flex h-3 w-3 rounded-full bg-gray-500"></span>}
            </h3>
            <p className="text-sm text-gray-400 mt-2">
              Processing {totalEmails.toLocaleString()} recruiter records autonomously.
            </p>
            {engineState?.current_domain && engineRunning && (
              <p className="text-sm text-emerald-400 font-medium mt-1 flex items-center gap-2">
                <RefreshCw size={14} className="animate-spin" /> Analyzing @{engineState.current_domain}
              </p>
            )}
          </div>
          
          <div className="flex items-center gap-3">
            <div className="bg-[#0A0A0B] border border-[var(--border)] rounded-xl px-4 py-2 flex flex-col items-end">
              <span className="text-xs text-gray-500 uppercase font-bold tracking-wider">Speed</span>
              <span className="text-lg font-mono text-white flex items-center gap-2">
                <Zap size={14} className="text-yellow-400"/> {Math.round(engineState?.speed_emails_per_hour || 0).toLocaleString()} <span className="text-xs text-gray-500">/hr</span>
              </span>
            </div>
            
            {!engineState?.is_running ? (
              <button onClick={() => toggleEngine('start')} className="h-12 px-6 rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/30 flex items-center gap-2 font-bold transition-all shadow-[0_0_15px_rgba(16,185,129,0.15)] hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]">
                <Play size={18} fill="currentColor" /> Initialize Engine
              </button>
            ) : enginePaused ? (
              <button onClick={() => toggleEngine('start')} className="h-12 px-6 rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/30 flex items-center gap-2 font-bold transition-all">
                <Play size={18} fill="currentColor" /> Resume
              </button>
            ) : (
              <button onClick={() => toggleEngine('pause')} className="h-12 px-6 rounded-xl bg-amber-600/20 text-amber-400 border border-amber-500/30 hover:bg-amber-600/30 flex items-center gap-2 font-bold transition-all">
                <Pause size={18} fill="currentColor" /> Pause Engine
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-2 flex justify-between text-sm">
          <span className="text-gray-400 font-medium">Global Progress</span>
          <span className="font-bold text-white">{progressPercent.toFixed(1)}%</span>
        </div>
        <div className="h-4 w-full bg-[#0A0A0B] rounded-full overflow-hidden relative z-10 border border-white/5 shadow-inner">
          <div 
            className="h-full rounded-full transition-all duration-1000 ease-out relative"
            style={{ 
              width: `${progressPercent}%`,
              background: 'linear-gradient(90deg, var(--brand), var(--brand-strong))',
              boxShadow: '0 0 20px var(--brand-bg)'
            }}
          >
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGcgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMikiIHN0cm9rZS13aWR0aD0iNCI+PHBhdGggZD0iTS0xMCA1MEw1MCAtMTAiLz48L2c+PC9zdmc+')] opacity-20 animate-[slide_2s_linear_infinite]" />
          </div>
        </div>
        
        <div className="flex justify-between items-center mt-3 text-xs font-medium text-gray-500 relative z-10">
          <span>{totalProcessed.toLocaleString()} Processed</span>
          <span>{totalPending.toLocaleString()} Remaining</span>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <StatCard 
          title="Verified Contacts" 
          value={(stats?.verified || 0).toLocaleString()}
          subtitle="90-100% Confidence"
          icon={CheckCircle2} 
          gradientClass="bg-gradient-to-br from-emerald-900/40 to-[#0A0A0B]"
          colorClass="text-emerald-400"
        />
        <StatCard 
          title="Likely Valid" 
          value={(stats?.likely_valid || 0).toLocaleString()}
          subtitle="70-89% Confidence"
          icon={ShieldCheck} 
          gradientClass="bg-gradient-to-br from-blue-900/40 to-[#0A0A0B]"
          colorClass="text-blue-400"
        />
        <StatCard 
          title="Needs Monitoring" 
          value={(stats?.needs_monitoring || 0).toLocaleString()}
          subtitle="50-69% Confidence"
          icon={AlertTriangle} 
          gradientClass="bg-gradient-to-br from-amber-900/40 to-[#0A0A0B]"
          colorClass="text-amber-400"
        />
        <StatCard 
          title="Invalid / Suspicious" 
          value={((stats?.invalid || 0) + (stats?.suspicious || 0)).toLocaleString()}
          subtitle="< 50% Confidence"
          icon={XCircle} 
          gradientClass="bg-gradient-to-br from-red-900/40 to-[#0A0A0B]"
          colorClass="text-red-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Domain Reputation Panel */}
        <div className="lg:col-span-2 rounded-2xl border border-[var(--border)] bg-[#121214] p-6 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 opacity-50" style={{ background: 'linear-gradient(to right, var(--brand), var(--brand-strong), #e0c274)' }} />
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <BarChart3 size={20} style={{ color: 'var(--brand-strong)' }} />
                Domain Reputation Insights
              </h2>
              <p className="text-sm text-gray-400 mt-1">Deliverability rates by enterprise domain</p>
            </div>
          </div>
          
          <div className="overflow-x-auto max-h-[400px] overflow-y-auto custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-[#121214] z-10">
                <tr className="border-b border-[var(--border)] text-xs uppercase tracking-wider text-gray-500 font-semibold">
                  <th className="pb-3 px-4">Domain</th>
                  <th className="pb-3 px-4">Total Sent</th>
                  <th className="pb-3 px-4">Success Rate</th>
                  <th className="pb-3 px-4">Bounce Rate</th>
                  <th className="pb-3 px-4">Reply Rate</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {domains.map((d, i) => (
                  <tr key={d.domain} className="border-b border-white/5 hover:bg-[var(--bg-hover)] transition-colors group">
                    <td className="py-4 px-4 font-medium flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-[10px] text-gray-400">
                        {d.domain.charAt(0).toUpperCase()}
                      </div>
                      {d.domain}
                    </td>
                    <td className="py-4 px-4 text-gray-300">{d.total_sent.toLocaleString()}</td>
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2">
                        <span className={d.success_rate > 90 ? 'text-emerald-400' : 'text-amber-400'}>{d.success_rate}%</span>
                        {d.success_rate > 90 ? <ArrowUpRight size={14} className="text-emerald-400" /> : <ArrowDownRight size={14} className="text-amber-400" />}
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className={d.bounce_rate > 5 ? 'text-red-400' : 'text-gray-400'}>{d.bounce_rate}%</span>
                    </td>
                    <td className="py-4 px-4 font-medium" style={{ color: 'var(--brand)' }}>{d.reply_rate}%</td>
                  </tr>
                ))}
                {domains.length === 0 && (
                  <tr>
                    <td colSpan="5" className="py-8 text-center text-gray-500">No domain intelligence gathered yet. Run campaigns to train the engine.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Intelligence Actions & Logs */}
        <div className="flex flex-col gap-6">
          
          <div className="rounded-2xl border border-[var(--border)] bg-[#121214] p-6 shadow-xl">
             <h3 className="text-sm font-bold text-gray-300 uppercase tracking-widest mb-4 flex items-center gap-2">
               <Clock size={16} /> Recent Batches
             </h3>
             <div className="space-y-3 max-h-[300px] overflow-y-auto custom-scrollbar pr-2">
               {engineState?.batch_log?.slice(0, 5).map((log, idx) => (
                 <div key={idx} className="bg-[#0A0A0B] border border-white/5 p-3 rounded-xl">
                   <div className="flex justify-between items-center mb-1">
                     <span className="text-sm font-bold text-blue-400">@{log.domain}</span>
                     <span className="text-xs text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                   </div>
                   <div className="flex justify-between text-xs text-gray-400">
                     <span>{log.count.toLocaleString()} emails</span>
                     <span>{log.duration_seconds}s</span>
                   </div>
                 </div>
               ))}
               {(!engineState?.batch_log || engineState.batch_log.length === 0) && (
                 <div className="text-center py-6 text-sm text-gray-600">No batches processed yet.</div>
               )}
             </div>
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[#121214] p-6">
             <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Live Activity</h3>
             <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 mb-3">
                <span className="text-sm text-emerald-400 font-medium flex items-center gap-2"><CheckCircle2 size={16}/> Recent Replies</span>
                <span className="text-sm font-bold text-white">{stats?.recent_replied || 0}</span>
             </div>
             <div className="flex items-center justify-between p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <span className="text-sm text-red-400 font-medium flex items-center gap-2"><Trash2 size={16}/> Recent Bounces</span>
                <span className="text-sm font-bold text-white">{stats?.recent_bounced || 0}</span>
             </div>
          </div>
        </div>

      </div>

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes slide {
          from { background-position: 0 0; }
          to { background-position: 40px 0; }
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.02);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}} />
    </div>
  );
}
