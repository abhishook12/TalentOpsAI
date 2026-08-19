import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck, AlertTriangle, XCircle, CheckCircle2, ShieldAlert,
  ChevronRight, Send, X, ArrowRight, RefreshCw, Mail, Check, AlertCircle,
  Wand2, Sparkles, CheckCheck
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
    deliverability_rate = 0,
    risk_level = 'low',
    can_proceed = true,
    warning_message = '',
    recipients = []
  } = preflightData;

  const filteredRecipients = recipients.filter(r => {
    if (filterTier === 'safe') return r.action === 'send';
    if (filterTier === 'review') return r.action === 'review';
    if (filterTier === 'blocked') return r.action === 'block';
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
        toast.success(`Successfully healed & repaired ${heal_summary.total_healed} emails!`);
      } else {
        toast.info('No additional permutations or typos could be auto-repaired.');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Auto-healing failed');
    } finally {
      setIsHealing(false);
    }
  };

  const getRiskBadge = () => {
    if (risk_level === 'low') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <ShieldCheck className="w-3.5 h-3.5" /> High Deliverability Safe (Score {deliverability_rate}%)
        </span>
      );
    }
    if (risk_level === 'medium') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-3.5 h-3.5" /> Moderate Risk (Score {deliverability_rate}%)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <ShieldAlert className="w-3.5 h-3.5" /> Critical Bounce Risk (Score {deliverability_rate}%)
      </span>
    );
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="w-full max-w-2xl bg-[#141417] border border-[#27272a] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div className="px-6 py-5 border-b border-[#27272a] flex items-center justify-between bg-[#18181b]/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white tracking-tight flex items-center gap-2 m-0">
                  Campaign Deliverability Pre-Flight Gate
                </h2>
                <p className="text-xs text-[#a1a1aa] mt-0.5 m-0">
                  Real-time DNS MX, deep mailbox ping & zero-bounce safety scan
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[#71717a] hover:text-white hover:bg-[#27272a] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body content */}
          <div className="p-6 overflow-y-auto space-y-6 custom-scrollbar">
            {/* Top Score Banner */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-[#1c1c21] border border-[#2c2c34]">
              <div>
                <div className="text-xs font-medium text-[#71717a] uppercase tracking-wider mb-1">
                  Deliverability Gate Verdict
                </div>
                <div>{getRiskBadge()}</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-white tracking-tight">
                  {deliverability_rate}%
                </div>
                <div className="text-[11px] text-[#a1a1aa]">Calculated Safe Ratio</div>
              </div>
            </div>

            {/* Auto-Healer Banner if blocked or risky exist */}
            {(blocked > 0 || risky_review > 0) && (
              <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/40 via-[#1e1b2e] to-[#18181b] border border-purple-500/30 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400 flex-shrink-0">
                    <Wand2 className="w-4 h-4 animate-pulse" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                      Autonomous Email Healer & Permutation Engine
                    </div>
                    <div className="text-[11px] text-[#a1a1aa] truncate">
                      Auto-correct domain typos, hoist alternates & synthesize valid corporate inboxes
                    </div>
                  </div>
                </div>
                <button
                  onClick={handleAutoHeal}
                  disabled={isHealing}
                  className="px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 flex-shrink-0 shadow-lg shadow-purple-950/40 transition-all cursor-pointer"
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
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  filterTier === 'safe'
                    ? 'bg-emerald-500/10 border-emerald-500/40 ring-1 ring-emerald-500/30'
                    : 'bg-[#18181b] border-[#27272a] hover:border-[#3f3f46]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Safe to Send
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                    Tier 1-2
                  </span>
                </div>
                <div className="text-xl font-bold text-white">{safe_to_send}</div>
                <div className="text-[11px] text-[#71717a] mt-0.5">Corporate & MX Verified</div>
              </div>

              {/* Risky */}
              <div
                onClick={() => setFilterTier(filterTier === 'review' ? 'all' : 'review')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  filterTier === 'review'
                    ? 'bg-amber-500/10 border-amber-500/40 ring-1 ring-amber-500/30'
                    : 'bg-[#18181b] border-[#27272a] hover:border-[#3f3f46]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" /> Review / Catch-All
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
                    Tier 3
                  </span>
                </div>
                <div className="text-xl font-bold text-white">{risky_review}</div>
                <div className="text-[11px] text-[#71717a] mt-0.5">Catch-All / Role Inboxes</div>
              </div>

              {/* Blocked */}
              <div
                onClick={() => setFilterTier(filterTier === 'blocked' ? 'all' : 'blocked')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  filterTier === 'blocked'
                    ? 'bg-rose-500/10 border-rose-500/40 ring-1 ring-rose-500/30'
                    : 'bg-[#18181b] border-[#27272a] hover:border-[#3f3f46]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-rose-400 flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5" /> Auto-Blocked
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-mono">
                    Tier 4-5
                  </span>
                </div>
                <div className="text-xl font-bold text-white">{blocked}</div>
                <div className="text-[11px] text-[#71717a] mt-0.5">Dead MX or Missing</div>
              </div>
            </div>

            {/* Catch-all toggle checkbox */}
            {risky_review > 0 && (
              <label className="flex items-center gap-3 p-3.5 rounded-xl bg-[#18181b] border border-[#27272a] cursor-pointer hover:border-[#3f3f46] transition-colors">
                <input
                  type="checkbox"
                  checked={excludeRisky}
                  onChange={(e) => setExcludeRisky(e.target.checked)}
                  className="w-4 h-4 rounded border-[#3f3f46] bg-[#27272a] text-emerald-500 focus:ring-emerald-500/30"
                />
                <div className="text-xs">
                  <span className="font-semibold text-white">Strict Safety Mode: </span>
                  <span className="text-[#a1a1aa]">
                    Exclude {risky_review} risky catch-all addresses from dispatch to guarantee 100% bounce protection.
                  </span>
                </div>
              </label>
            )}

            {/* Content & Spam Risk Assessment Panel */}
            {spamResult && (
              <div className="p-4 rounded-xl bg-[#18181b] border border-[#27272a]">
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className={`w-4 h-4 ${spamResult.is_safe ? 'text-emerald-400' : 'text-amber-400'}`} />
                    <span className="text-xs font-semibold text-white">Content Deliverability & Spam Score</span>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                    spamResult.risk_tier === 'low'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : spamResult.risk_tier === 'medium'
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {spamResult.deliverability_score}/100 Safe ({spamResult.risk_tier.toUpperCase()})
                  </span>
                </div>
                <div className="text-[11px] text-[#a1a1aa] mb-2">{spamResult.summary}</div>
                {spamResult.recommendations?.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-[#27272a]/60 space-y-1">
                    {spamResult.recommendations.map((rec, idx) => (
                      <div key={idx} className="text-[11px] text-amber-300/90 flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-amber-400 flex-shrink-0" />
                        <span>{rec}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Recipient Audit List */}
            <div>
              <div className="flex items-center justify-between mb-2.5">
                <div className="text-xs font-medium text-[#a1a1aa]">
                  Recipient Deliverability Audit ({filteredRecipients.length} shown)
                </div>
                {filterTier !== 'all' && (
                  <button
                    onClick={() => setFilterTier('all')}
                    className="text-[11px] text-emerald-400 hover:underline"
                  >
                    Reset Filter
                  </button>
                )}
              </div>
              <div className="max-h-48 overflow-y-auto rounded-xl border border-[#27272a] bg-[#121215] divide-y divide-[#1e1e24] custom-scrollbar">
                {filteredRecipients.length === 0 ? (
                  <div className="p-4 text-center text-xs text-[#71717a]">No recipients in this category</div>
                ) : (
                  filteredRecipients.map((r, i) => (
                    <div key={i} className="px-3.5 py-2.5 flex items-center justify-between text-xs hover:bg-[#18181c] transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <Mail className="w-3.5 h-3.5 text-[#71717a] flex-shrink-0" />
                        <span className="font-mono text-white truncate">{r.email}</span>
                        {r.name && <span className="text-[#71717a] text-[11px] truncate">({r.name})</span>}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-[11px] text-[#71717a] font-mono">{r.confidence}%</span>
                        {r.action === 'send' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Safe
                          </span>
                        )}
                        {r.action === 'review' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            Catch-All
                          </span>
                        )}
                        {r.action === 'block' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                            Blocked
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
          <div className="px-6 py-4 border-t border-[#27272a] bg-[#18181b]/50 flex items-center justify-between">
            <button
              onClick={onClose}
              disabled={isLaunching}
              className="px-4 py-2 text-xs font-medium text-[#a1a1aa] hover:text-white bg-transparent hover:bg-[#27272a] rounded-lg transition-colors"
            >
              Cancel & Edit Draft
            </button>

            <button
              onClick={() => onConfirmLaunch({ excludeRisky, effectiveSendCount })}
              disabled={!can_proceed || effectiveSendCount === 0 || isLaunching}
              className={`px-5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shadow-lg ${
                can_proceed && effectiveSendCount > 0
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/20 cursor-pointer'
                  : 'bg-[#27272a] text-[#71717a] cursor-not-allowed'
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
