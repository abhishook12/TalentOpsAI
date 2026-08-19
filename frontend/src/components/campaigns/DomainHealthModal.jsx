import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldAlert, CheckCircle2, AlertTriangle, X, RefreshCw, Globe, Server, Key } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function DomainHealthModal({ isOpen, onClose, initialDomain = '' }) {
  const [domain, setDomain] = useState(initialDomain || 'talentops.ai');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);

  if (!isOpen) return null;

  const handleInspect = async () => {
    if (!domain.trim()) {
      toast.error('Please enter a domain to inspect');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/campaigns/inspect-domain-health', { domain });
      if (res.data) {
        setReport(res.data);
        toast.success(`Domain audit complete for ${res.data.domain}`);
      }
    } catch (err) {
      toast.error('Domain inspection failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-700 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Sender Domain Health & Deliverability
              </h2>
              <p className="text-xs text-slate-400">Audit SPF, DKIM, DMARC & MX records to guarantee cold email deliverability.</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search / Run Bar */}
        <div className="p-6 border-b border-slate-800 bg-slate-950/30">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Globe className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="e.g. yourcompany.com or sender@yourcompany.com"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <button
              onClick={handleInspect}
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center gap-2 shadow-md shadow-emerald-600/20 disabled:opacity-50 transition"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              Inspect Domain
            </button>
          </div>
        </div>

        {/* Results Area */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {report ? (
            <>
              {/* Overall Health Banner */}
              <div className={`p-4 rounded-xl border flex items-center justify-between ${
                report.risk_tier === 'low'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : report.risk_tier === 'medium'
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              }`}>
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider">Domain Health Score</div>
                  <div className="text-xl font-bold flex items-center gap-2 mt-0.5">
                    {report.health_score} / 100
                    <span className="text-xs font-normal opacity-90">— {report.status_label}</span>
                  </div>
                </div>
                <div className="text-2xl font-black">{report.health_score}%</div>
              </div>

              {/* Protocol Breakdown Grid */}
              <div className="grid grid-cols-2 gap-3">
                {/* SPF Card */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5 text-cyan-400" />
                      SPF Authentication
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      report.has_spf ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>
                      {report.spf_status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono truncate">
                    {report.spf_record || 'No SPF TXT record found'}
                  </div>
                </div>

                {/* DMARC Card */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                      DMARC Policy
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      report.has_dmarc ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>
                      {report.dmarc_status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono truncate">
                    {report.dmarc_record || 'No _dmarc record detected'}
                  </div>
                </div>

                {/* MX Routing */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <Globe className="w-3.5 h-3.5 text-emerald-400" />
                      MX Routing
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      report.has_mx ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>
                      {report.has_mx ? 'Active' : 'No MX'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">
                    {report.mx_records?.join(', ') || 'None'}
                  </div>
                </div>

                {/* DKIM Selectors */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5 text-amber-400" />
                      DKIM Selectors
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">
                      {report.dkim_selectors_found?.length || 0} Found
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">
                    {report.dkim_selectors_found?.map(d => d.selector).join(', ') || 'Custom selector configured'}
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              {report.recommendations?.length > 0 && (
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
                  <div className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Deliverability Recommendations
                  </div>
                  <ul className="space-y-1.5 text-xs text-slate-300">
                    {report.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-amber-500">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center text-center p-8 text-slate-500">
              <ShieldCheck className="w-10 h-10 text-slate-600 mb-3" />
              <div className="text-sm font-semibold text-slate-300">Verify Your Sending Domain</div>
              <p className="text-xs text-slate-500 max-w-xs mt-1">
                Enter your outreach domain above to perform a live check of SPF, DMARC, DKIM, and MX configurations.
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
