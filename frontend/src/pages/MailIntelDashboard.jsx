import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, AlertTriangle, XCircle, Mail, Database, 
  Activity, ArrowUpRight, ArrowDownRight, CheckCircle2,
  Trash2, RefreshCw, ChevronRight, BarChart3, Filter
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

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
  const [loading, setLoading] = useState(true);
  const [cleanupAction, setCleanupAction] = useState({ active: false, filter: 'suspicious', count: 0 });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };
      
      const [statsRes, domainsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/mailintel/stats`, { headers }),
        fetch(`${API_BASE_URL}/mailintel/domains`, { headers })
      ]);
      
      if (statsRes.ok) setStats(await statsRes.json());
      if (domainsRes.ok) setDomains(await domainsRes.json());
    } catch (e) {
      console.error("Error fetching mailintel data", e);
    }
    setLoading(false);
  };

  const handleCleanup = async () => {
    try {
      const token = localStorage.getItem('token');
      let payload = {};
      if (cleanupAction.filter === 'suspicious') payload = { confidence_less_than: 40 };
      if (cleanupAction.filter === 'bounced') payload = { hard_bounce_gte: 2 };
      
      const res = await fetch(`${API_BASE_URL}/mailintel/cleanup`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        fetchData();
        setCleanupAction({ ...cleanupAction, active: false });
      }
    } catch(e) {
      console.error(e);
      alert("Cleanup failed.");
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
          <button onClick={fetchData} className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-sm font-medium flex items-center gap-2 transition-colors">
            <RefreshCw size={16} /> Sync Intelligence
          </button>
        </div>
      </div>

      {/* Coverage Progress */}
      <div className="mb-8 bg-[#121214] border border-white/10 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="flex justify-between items-end mb-2 relative z-10">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Database size={18} style={{ color: 'var(--brand)' }} />
              Database Coverage Engine
            </h3>
            <p className="text-sm text-gray-400 mt-1">
              Background workers actively verifying {stats?.total?.toLocaleString()} records
            </p>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold" style={{ color: 'var(--brand)' }}>
              {(((stats?.total - stats?.never_checked) / (stats?.total || 1)) * 100).toFixed(1)}%
            </span>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mt-1">Processed</p>
          </div>
        </div>
        <div className="h-3 w-full bg-white/5 rounded-full overflow-hidden relative z-10">
          <div 
            className="h-full rounded-full transition-all duration-1000 ease-out"
            style={{ 
              width: `${((stats?.total - stats?.never_checked) / (stats?.total || 1)) * 100}%`,
              background: 'linear-gradient(90deg, var(--brand), var(--brand-strong))',
              boxShadow: '0 0 10px var(--brand-bg)'
            }}
          />
        </div>
        <div className="flex justify-between items-center mt-3 text-xs font-medium text-gray-500 relative z-10">
          <span>{(stats?.total - stats?.never_checked)?.toLocaleString()} Verified & Scored</span>
          <span>{stats?.never_checked?.toLocaleString()} Remaining in Queue</span>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <StatCard 
          title="Total Processed" 
          value={stats?.total?.toLocaleString() || 0}
          subtitle={`Avg Confidence: ${stats?.average_confidence || 0}%`}
          icon={Database} 
          gradientClass="bg-gradient-to-br from-blue-900/40 to-[#0A0A0B]"
          colorClass="text-blue-400"
        />
        <StatCard 
          title="Verified Contacts" 
          value={stats?.verified?.toLocaleString() || 0}
          subtitle="95-100% Confidence"
          icon={CheckCircle2} 
          gradientClass="bg-gradient-to-br from-emerald-900/40 to-[#0A0A0B]"
          colorClass="text-emerald-400"
        />
        <StatCard 
          title="Needs Monitoring" 
          value={stats?.needs_monitoring?.toLocaleString() || 0}
          subtitle="60-79% Confidence"
          icon={AlertTriangle} 
          gradientClass="bg-gradient-to-br from-amber-900/40 to-[#0A0A0B]"
          colorClass="text-amber-400"
        />
        <StatCard 
          title="Invalid / Blocked" 
          value={stats?.invalid?.toLocaleString() || 0}
          subtitle="Hard bounced multiple times"
          icon={XCircle} 
          gradientClass="bg-gradient-to-br from-red-900/40 to-[#0A0A0B]"
          colorClass="text-red-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Domain Reputation Panel */}
        <div className="lg:col-span-2 rounded-2xl border border-white/10 bg-[#121214] p-6 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 opacity-50" style={{ background: 'linear-gradient(to right, var(--brand), var(--brand-strong), #e0c274)' }} />
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <BarChart3 size={20} style={{ color: 'var(--brand-strong)' }} />
                Domain Reputation Insights
              </h2>
              <p className="text-sm text-gray-400 mt-1">Real-time deliverability across enterprise domains</p>
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase tracking-wider text-gray-500 font-semibold">
                  <th className="pb-3 px-4">Domain</th>
                  <th className="pb-3 px-4">Total Sent</th>
                  <th className="pb-3 px-4">Success Rate</th>
                  <th className="pb-3 px-4">Bounce Rate</th>
                  <th className="pb-3 px-4">Reply Rate</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {domains.map((d, i) => (
                  <tr key={d.domain} className="border-b border-white/5 hover:bg-white/5 transition-colors group">
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

        {/* Intelligence Actions */}
        <div className="flex flex-col gap-6">
          <div className="rounded-2xl border border-white/10 bg-[#121214] p-6">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-4">
              <Filter size={18} style={{ color: 'var(--brand)' }} />
              Bulk Cleanup Rules
            </h2>
            <p className="text-sm text-gray-400 mb-6">Apply MAILINTEL filters to automatically quarantine hazardous contacts and protect sender reputation.</p>
            
            <div className="space-y-3">
              <button 
                onClick={() => setCleanupAction({ active: true, filter: 'suspicious', count: stats?.suspicious })}
                className="w-full text-left p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 transition-all flex items-center justify-between group"
              >
                <div>
                  <div className="font-medium text-amber-400 text-sm mb-1">Quarantine Low Confidence</div>
                  <div className="text-xs text-gray-500">Moves {stats?.suspicious || 0} emails to Invalid state (Confidence &lt; 40)</div>
                </div>
                <ChevronRight className="text-gray-600 group-hover:text-amber-400 transition-colors" size={18} />
              </button>

              <button 
                onClick={() => setCleanupAction({ active: true, filter: 'bounced', count: 0 })}
                className="w-full text-left p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 transition-all flex items-center justify-between group"
              >
                <div>
                  <div className="font-medium text-red-400 text-sm mb-1">Purge Serial Bouncers</div>
                  <div className="text-xs text-gray-500">Quarantines emails with 2+ hard bounces</div>
                </div>
                <ChevronRight className="text-gray-600 group-hover:text-red-400 transition-colors" size={18} />
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#121214] p-6">
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

      {/* Cleanup Modal */}
      {cleanupAction.active && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#1a1a1d] border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-xl font-bold mb-2">Confirm Action</h3>
            <p className="text-sm text-gray-400 mb-6">
              You are about to execute the <strong>{cleanupAction.filter}</strong> cleanup rule. This will permanently alter the status of targeted emails to protect your sender reputation.
            </p>
            <div className="flex justify-end gap-3">
              <button 
                onClick={() => setCleanupAction({ active: false })}
                className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={handleCleanup}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500 hover:bg-red-600 text-white transition-colors flex items-center gap-2"
              >
                <AlertTriangle size={16} /> Execute Cleanup
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
