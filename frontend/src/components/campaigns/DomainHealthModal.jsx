import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldAlert, CheckCircle2, AlertTriangle, X, RefreshCw, Globe, Server, Key } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function DomainHealthModal({ isOpen, onClose, initialDomain = '' }) {
  const [domain, setDomain] = useState(initialDomain || 'talentops.ai');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);

  const handleInspect = useCallback(async () => {
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
  }, [domain]);

  useEffect(() => {
    if (isOpen && domain) {
      handleInspect();
    }
  }, [isOpen, domain, handleInspect]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-[#121212] border border-white/15 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-black/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#e41937] to-[#fe063f] flex items-center justify-center shadow-lg shadow-[#e41937]/20">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Sender Domain Health & Deliverability
              </h2>
              <p className="text-xs text-zinc-400">Audit SPF, DKIM, DMARC & MX records to guarantee cold email deliverability.</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-zinc-400 hover:text-white rounded-lg hover:bg-[#18181b] transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search / Run Bar */}
        <div className="p-6 border-b border-white/10 bg-black/30">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Globe className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="e.g. yourcompany.com or sender@yourcompany.com"
                className="w-full bg-black border border-white/10 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-white/30"
              />
            </div>
            <button
              onClick={handleInspect}
              disabled={loading}
              className="px-4 py-2 bg-[#e41937] text-white hover:bg-[#e41937] text-white text-white text-xs font-semibold rounded-lg flex items-center gap-2 shadow-md shadow-[#e41937]/20 disabled:opacity-50 transition"
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
                  ? 'bg-white/10 border-white/30 text-white'
                  : report.risk_tier === 'medium'
                  ? 'bg-white/5 border-white/25 text-zinc-300'
                  : 'bg-[#e41937]/15 border-[#e41937]/40 text-[#fe063f]'
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
                <div className="bg-black border border-white/10 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-zinc-300 flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5 text-[#fe063f]" />
                      SPF Authentication
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      report.has_spf ? 'bg-white/10 text-white border border-white/20' : 'bg-[#e41937]/15 text-[#fe063f] border border-[#e41937]/30'
                    }`}>
                      {report.spf_status}
                    </span>
                  </div>
                  <div className="text-[11px] text-zinc-400 font-mono truncate">
                    {report.spf_record || 'No SPF TXT record found'}
                  </div>
                </div>

                {/* DMARC Card */}
                <div className="bg-black border border-white/10 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-zinc-300 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-[#fe063f]" />
                      DMARC Policy
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      report.has_dmarc ? 'bg-white/10 text-white border border-white/20' : 'bg-[#e41937]/15 text-[#fe063f] border border-[#e41937]/30'
                    }`}>
                      {report.dmarc_status}
                    </span>
                  </div>
                  <div className="text-[11px] text-zinc-400 font-mono truncate">
                    {report.dmarc_record || 'No _dmarc record detected'}
                  </div>
                </div>

                {/* MX Routing */}
                <div className="bg-black border border-white/10 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-zinc-300 flex items-center gap-1.5">
                      <Globe className="w-3.5 h-3.5 text-white" />
                      MX Routing
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      report.has_mx ? 'bg-white/10 text-white border border-white/20' : 'bg-[#e41937]/15 text-[#fe063f] border border-[#e41937]/30'
                    }`}>
                      {report.has_mx ? 'Active' : 'No MX'}
                    </span>
                  </div>
                  <div className="text-[11px] text-zinc-400 truncate">
                    {report.mx_records?.join(', ') || 'None'}
                  </div>
                </div>

                {/* DKIM Selectors */}
                <div className="bg-black border border-white/10 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-zinc-300 flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5 text-[#e41937]" />
                      DKIM Selectors
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#18181b] text-zinc-300">
                      {report.dkim_selectors_found?.length || 0} Found
                    </span>
                  </div>
                  <div className="text-[11px] text-zinc-400 truncate">
                    {report.dkim_selectors_found?.map(d => d.selector).join(', ') || 'Custom selector configured'}
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              {report.recommendations?.length > 0 && (
                <div className="bg-black border border-white/10 rounded-xl p-4 space-y-2">
                  <div className="text-xs font-semibold text-[#e41937] flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Deliverability Recommendations
                  </div>
                  <ul className="space-y-1.5 text-xs text-zinc-300">
                    {report.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-[#e41937]">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center text-center p-8 text-zinc-500">
              <ShieldCheck className="w-10 h-10 text-zinc-500 mb-3" />
              <div className="text-sm font-semibold text-zinc-300">Verify Your Sending Domain</div>
              <p className="text-xs text-zinc-500 max-w-xs mt-1">
                Enter your outreach domain above to perform a live check of SPF, DMARC, DKIM, and MX configurations.
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
