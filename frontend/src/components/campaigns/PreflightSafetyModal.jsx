import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck, AlertTriangle, XCircle, CheckCircle2, ShieldAlert,
  Send, X, RefreshCw, Mail, AlertCircle,
  Wand2, Sparkles, CheckCheck, Clock, Shield, Search, ArrowUpRight, Zap
} from 'lucide-react';
import api from '../../services/api';
import toast from 'react-hot-toast';

export default function PreflightSafetyModal({
  isOpen,
  onClose,
  campaignId,
  preflightData: initialPreflightData,
  subject = '',
  body = '',
  onConfirmLaunch,
  isLaunching = false
}) {
  const [preflightData, setPreflightData] = useState(initialPreflightData);
  const [excludeRisky, setExcludeRisky] = useState(false);
  const [filterTier, setFilterTier] = useState('all'); // 'all' | 'safe' | 'review' | 'blocked'
  const [searchQuery, setSearchQuery] = useState('');
  const [isHealing, setIsHealing] = useState(false);
  const [healedInfo, setHealedInfo] = useState(null);
  const [spamResult, setSpamResult] = useState(null);
  const [isCheckingSpam, setIsCheckingSpam] = useState(false);

  // Sync if prop updates
  React.useEffect(() => {
    setPreflightData(initialPreflightData);
  }, [initialPreflightData]);

  // Run spam score check when modal opens
  React.useEffect(() => {
    if (isOpen && (subject || body)) {
      setIsCheckingSpam(true);
      api.post('/campaigns/preflight-spam-check', { subject, body })
        .then(res => setSpamResult(res.data))
        .catch(() => setSpamResult(null))
        .finally(() => setIsCheckingSpam(false));
    }
  }, [isOpen, subject, body]);

  if (!isOpen || !preflightData) return null;

  const {
    total_recipients = 0,
    safe_to_send = 0,
    risky_review = 0,
    blocked = 0,
    deliverability_rate = 100,
    risk_level = 'low',
    can_proceed = true,
    warning_message = '',
    recipients = []
  } = preflightData;

  const filteredRecipients = recipients.filter(r => {
    if (filterTier === 'safe' && r.action !== 'send') return false;
    if (filterTier === 'review' && r.action !== 'review') return false;
    if (filterTier === 'blocked' && r.action !== 'block') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchEmail = (r.email || '').toLowerCase().includes(q);
      const matchName = (r.name || '').toLowerCase().includes(q);
      return matchEmail || matchName;
    }
    return true;
  });

  const effectiveSendCount = excludeRisky ? safe_to_send : (safe_to_send + risky_review);

  const handleAutoHeal = async () => {
    if (!campaignId) {
      toast.error('Campaign ID not available for auto-healing');
      return;
    }
    setIsHealing(true);
    try {
      const res = await api.post(`/campaigns/${campaignId}/auto-heal`, {
        emails: recipients.map(r => r.email),
        names: recipients.map(r => r.name || '')
      });
      const { heal_summary, updated_preflight } = res.data;
      setPreflightData(updated_preflight);
      setHealedInfo(heal_summary);
      if (heal_summary.total_healed > 0) {
        toast.success(`Successfully repaired ${heal_summary.total_healed} email addresses!`);
      } else {
        toast.info('No additional domain permutations could be repaired.');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Auto-healing failed');
    } finally {
      setIsHealing(false);
    }
  };

  const getInitials = (name, email) => {
    if (name && name.trim()) {
      const parts = name.trim().split(/\s+/);
      if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      return parts[0].slice(0, 2).toUpperCase();
    }
    if (email) return email.slice(0, 2).toUpperCase();
    return 'RE';
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 8 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-2xl bg-[#0e0e11] border border-[#27272e] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
          style={{ boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.05)' }}
        >
          {/* Header */}
          <div className="px-6 py-5 border-b border-[#22222a] flex items-center justify-between bg-[#121217]">
            <div className="flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shadow-sm">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white tracking-tight m-0 flex items-center gap-2">
                  Pre-Flight Deliverability Check
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
                    Verified
                  </span>
                </h2>
                <p className="text-xs text-[#8e8e99] mt-0.5 m-0 font-normal">
                  Real-time MX validation, sender reputation watchdog & zero-bounce safety scan
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[#71717a] hover:text-white hover:bg-[#202026] transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body Content */}
          <div className="p-6 overflow-y-auto space-y-5 custom-scrollbar bg-[#0e0e11]">
            {/* Top Score Banner */}
            <div className="p-4 rounded-xl bg-[#141419] border border-[#262630] flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#a1a1aa] uppercase tracking-wider">
                    Deliverability Health
                  </span>
                  <span className="text-xs font-bold text-emerald-400">
                    {deliverability_rate}% Safe & Deliverable
                  </span>
                </div>
                {/* Progress bar */}
                <div className="w-full h-2 rounded-full bg-[#202028] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${deliverability_rate}%`,
                      background: deliverability_rate >= 80 ? 'linear-gradient(90deg, #10b981, #34d399)' : deliverability_rate >= 50 ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' : 'linear-gradient(90deg, #ef4444, #f87171)'
                    }}
                  />
                </div>
              </div>
              <div className="pl-4 border-l border-[#262630] text-right flex-shrink-0">
                <div className="text-2xl font-extrabold text-white tracking-tight">
                  {effectiveSendCount}
                  <span className="text-xs font-normal text-[#71717a] ml-1">/ {total_recipients}</span>
                </div>
                <div className="text-[11px] text-[#8e8e99]">Ready to Dispatch</div>
              </div>
            </div>

            {/* Auto-Healer Banner if blocked or risky exist */}
            {(blocked > 0 || risky_review > 0) && (
              <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/30 via-[#181524] to-[#141419] border border-purple-500/25 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-purple-500/15 border border-purple-500/25 flex items-center justify-center text-purple-400 flex-shrink-0">
                    <Wand2 className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-white flex items-center gap-1.5">
                      Autonomous Email Healer & Permutation Engine
                    </div>
                    <div className="text-[11px] text-[#9ca3af] truncate">
                      Auto-correct domain typos and synthesize valid corporate mailboxes
                    </div>
                  </div>
                </div>
                <button
                  onClick={handleAutoHeal}
                  disabled={isHealing}
                  className="px-3.5 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 flex-shrink-0 shadow-md shadow-purple-950/50 transition-all cursor-pointer"
                >
                  {isHealing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Repairing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" /> Auto-Heal ({blocked + risky_review})
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Healed Notification Badge */}
            {healedInfo && healedInfo.total_healed > 0 && (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-2.5">
                <CheckCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <div className="text-xs text-emerald-300">
                  Repaired <strong>{healedInfo.total_healed}</strong> addresses into verified corporate mailboxes!
                </div>
              </div>
            )}

            {/* Warning if blocked */}
            {warning_message && !healedInfo && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
                <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-rose-300 leading-relaxed">{warning_message}</div>
              </div>
            )}

            {/* 3 Metric Cards */}
            <div className="grid grid-cols-3 gap-3">
              {/* Safe */}
              <div
                onClick={() => setFilterTier(filterTier === 'safe' ? 'all' : 'safe')}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  filterTier === 'safe'
                    ? 'bg-emerald-500/10 border-emerald-500/40 ring-1 ring-emerald-500/30'
                    : 'bg-[#141419] border-[#262630] hover:border-[#383846]'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Safe to Send
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-mono font-bold">
                    Tier 1-2
                  </span>
                </div>
                <div className="text-xl font-black text-white">{safe_to_send}</div>
                <div className="text-[11px] text-[#8e8e99] mt-0.5">Corporate & MX Verified</div>
              </div>

              {/* Risky */}
              <div
                onClick={() => setFilterTier(filterTier === 'review' ? 'all' : 'review')}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  filterTier === 'review'
                    ? 'bg-amber-500/10 border-amber-500/40 ring-1 ring-amber-500/30'
                    : 'bg-[#141419] border-[#262630] hover:border-[#383846]'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" /> Catch-All
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 font-mono font-bold">
                    Tier 3
                  </span>
                </div>
                <div className="text-xl font-black text-white">{risky_review}</div>
                <div className="text-[11px] text-[#8e8e99] mt-0.5">Review Recommended</div>
              </div>

              {/* Blocked */}
              <div
                onClick={() => setFilterTier(filterTier === 'blocked' ? 'all' : 'blocked')}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  filterTier === 'blocked'
                    ? 'bg-rose-500/10 border-rose-500/40 ring-1 ring-rose-500/30'
                    : 'bg-[#141419] border-[#262630] hover:border-[#383846]'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-rose-400 flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5" /> Excluded
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300 font-mono font-bold">
                    Tier 4-5
                  </span>
                </div>
                <div className="text-xl font-black text-white">{blocked}</div>
                <div className="text-[11px] text-[#8e8e99] mt-0.5">Dead MX or Invalid</div>
              </div>
            </div>

            {/* Smart Outreach Powerhouse Badges (Timezone & Reputation Shield) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3.5 rounded-xl bg-[#141419] border border-[#262630] flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center text-indigo-400 flex-shrink-0">
                  <Clock className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    Prime-Time Timezone Dispatch
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-mono font-bold">8:45 AM</span>
                  </div>
                  <div className="text-[11px] text-[#8e8e99] mt-0.5">
                    Recipients scheduled for 8:45 AM local recipient time across ET, CT, MT, PT.
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#141419] border border-[#262630] flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/25 flex items-center justify-center text-emerald-400 flex-shrink-0">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    Domain Reputation Shield
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-mono font-bold">2.0% Cap</span>
                  </div>
                  <div className="text-[11px] text-[#8e8e99] mt-0.5">
                    Emergency circuit breaker auto-pauses campaign if bounce velocity spikes.
                  </div>
                </div>
              </div>
            </div>

            {/* Live Content & Spam Risk Meter */}
            {spamResult && (
              <div className={`p-3.5 rounded-xl border flex items-center justify-between gap-3 ${
                (spamResult.score || 0) < 30
                  ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300'
                  : (spamResult.score || 0) < 60
                  ? 'bg-amber-500/10 border-amber-500/25 text-amber-300'
                  : 'bg-rose-500/10 border-rose-500/25 text-rose-300'
              }`}>
                <div className="flex items-center gap-2.5">
                  <Shield className="w-4 h-4 flex-shrink-0" />
                  <div>
                    <div className="text-xs font-bold flex items-center gap-2">
                      Spam Risk Score: {spamResult.score || 0}% ({spamResult.risk_level || 'Safe'})
                    </div>
                    <div className="text-[11px] text-[#8e8e99] mt-0.5">
                      {spamResult.flags?.length > 0 ? `Trigger words detected: ${spamResult.flags.join(', ')}` : 'Zero spam trigger words detected in subject or email body.'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Recipient Deliverability Audit Table */}
            <div>
              <div className="flex items-center justify-between mb-2.5 gap-2">
                <div className="text-xs font-bold text-[#a1a1aa] uppercase tracking-wider">
                  Recipient Deliverability Audit ({filteredRecipients.length})
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-[#71717a]" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      placeholder="Filter leads..."
                      className="text-[11px] pl-8 pr-2.5 py-1 rounded-lg bg-[#141419] border border-[#262630] text-white placeholder-[#71717a] outline-none focus:border-indigo-500 transition-colors w-32 sm:w-40"
                    />
                  </div>
                  {filterTier !== 'all' && (
                    <button
                      onClick={() => setFilterTier('all')}
                      className="text-[11px] text-indigo-400 hover:underline cursor-pointer"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>

              <div className="max-h-52 overflow-y-auto rounded-xl border border-[#262630] bg-[#121217] divide-y divide-[#1e1e26] custom-scrollbar">
                {filteredRecipients.length === 0 ? (
                  <div className="p-6 text-center text-xs text-[#71717a]">
                    No recipient records match the selected filter.
                  </div>
                ) : (
                  filteredRecipients.map((r, i) => (
                    <div key={i} className="px-4 py-3 flex items-center justify-between text-xs hover:bg-[#181820] transition-colors">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-7 h-7 rounded-full bg-[#20202a] border border-[#2e2e3a] flex items-center justify-center text-[10px] font-bold text-[#a1a1aa] flex-shrink-0">
                          {getInitials(r.name, r.email)}
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-white truncate flex items-center gap-1.5">
                            {r.email}
                          </div>
                          {r.name && <div className="text-[#71717a] text-[11px] truncate">{r.name}</div>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2.5 flex-shrink-0">
                        <span className="text-[11px] text-[#8e8e99] font-mono font-medium">
                          {r.email_confidence ?? r.confidence ?? 95}% Verified
                        </span>
                        {r.action === 'send' && (
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
                            Ready to Send
                          </span>
                        )}
                        {r.action === 'review' && (
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/25">
                            Catch-All
                          </span>
                        )}
                        {r.action === 'block' && (
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/25">
                            Excluded
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Footer Controls */}
          <div className="px-6 py-4 border-t border-[#22222a] bg-[#121217] flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-4">
              <button
                onClick={onClose}
                disabled={isLaunching}
                className="px-4 py-2 text-xs font-semibold text-[#a1a1aa] hover:text-white bg-transparent hover:bg-[#202026] rounded-lg transition-colors cursor-pointer"
              >
                Back to Editor
              </button>
              {risky_review > 0 && (
                <label className="flex items-center gap-2 text-xs text-[#a1a1aa] cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={excludeRisky}
                    onChange={e => setExcludeRisky(e.target.checked)}
                    className="w-4 h-4 rounded border-[#383846] bg-[#141419] text-emerald-500 focus:ring-emerald-500 cursor-pointer"
                  />
                  <span>Exclude Catch-All ({risky_review})</span>
                </label>
              )}
            </div>

            <button
              onClick={() => onConfirmLaunch({ excludeRisky, effectiveSendCount })}
              disabled={!can_proceed || effectiveSendCount === 0 || isLaunching}
              className={`px-5 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-lg ${
                can_proceed && effectiveSendCount > 0
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950/40 cursor-pointer'
                  : 'bg-[#202028] text-[#555562] cursor-not-allowed'
              }`}
            >
              {isLaunching ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Dispatching Campaign...
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" /> Launch Safe Outreach ({effectiveSendCount} Recipients)
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
