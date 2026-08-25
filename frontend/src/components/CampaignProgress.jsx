import React, { useEffect, useState, useCallback } from 'react';
import {
  Activity, CheckCircle2, XCircle, Clock, Loader2, AlertTriangle,
  ExternalLink, Pause, Play, Ban, RefreshCw, Send, Check, ShieldAlert
} from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

export default function CampaignProgress({ campaignId, onStatusChange }) {
  const [data, setData] = useState({
    status: 'active',
    total: 0,
    sent: 0,
    failed: 0,
    pending: 0,
    queued: 0,
    sending: 0,
    retrying: 0,
    progress_percent: 0,
    has_auth_error: false
  });
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchProgress = useCallback(async () => {
    if (!campaignId) return;
    try {
      const res = await api.get(`/campaigns/${campaignId}/progress`);
      if (res.data) {
        setData(prev => ({ ...prev, ...res.data }));
        setLoading(false);
        if (onStatusChange) onStatusChange(res.data.status);
      }
    } catch (err) {
      console.warn("Progress fetch fallback polling:", err);
      setLoading(false);
    }
  }, [campaignId, onStatusChange]);

  useEffect(() => {
    fetchProgress();
    // Poll every 1.5s while active/sending
    const timer = setInterval(() => {
      fetchProgress();
    }, 1500);

    return () => clearInterval(timer);
  }, [fetchProgress]);

  const handlePause = async () => {
    setActionLoading(true);
    try {
      await api.post(`/campaigns/${campaignId}/pause`);
      toast.success('Campaign paused');
      fetchProgress();
    } catch {
      toast.error('Failed to pause campaign');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    setActionLoading(true);
    try {
      await api.post(`/campaigns/${campaignId}/resume`);
      toast.success('Campaign resumed');
      fetchProgress();
    } catch {
      toast.error('Failed to resume campaign');
    } finally {
      setActionLoading(false);
    }
  };

  const processed = (data.sent || 0) + (data.failed || 0);
  const percent = data.total > 0 ? Math.min(100, Math.round((processed / data.total) * 100)) : 0;
  const isCompleted = data.status === 'completed' || (data.total > 0 && processed >= data.total);
  const isActive = data.status === 'active' || data.status === 'sending';
  const isPaused = data.status === 'paused';

  return (
    <div className="p-6 bg-[#111116] border border-[#22222a] rounded-xl flex flex-col gap-6 text-white">
      {/* Top Header Strip */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3.5">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center border shadow-md ${
            isCompleted
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
              : isPaused
              ? 'bg-amber-500/15 border-amber-500/30 text-amber-400'
              : 'bg-cyan-500/15 border-cyan-500/30 text-cyan-400'
          }`}>
            {isCompleted ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : isPaused ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="text-base font-extrabold text-white tracking-tight m-0">
                {isCompleted ? 'Campaign Completed' : isPaused ? 'Campaign Paused' : 'Live Delivery in Progress'}
              </h3>
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                isCompleted
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25'
                  : isPaused
                  ? 'bg-amber-500/15 text-amber-400 border-amber-500/25'
                  : 'bg-cyan-500/15 text-cyan-400 border-cyan-500/25 animate-pulse'
              }`}>
                {data.status || 'Active'}
              </span>
            </div>
            <p className="text-xs text-[#8e8e99] mt-0.5 m-0 font-normal">
              {isCompleted
                ? `All ${data.total} recipients have been processed.`
                : isPaused
                ? 'Queue is paused. Resuming will continue remaining recipients.'
                : 'Dispatching emails via local Outlook Bridge with active rate limiting.'}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {isActive && (
            <button
              onClick={handlePause}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#202026] hover:bg-[#282830] text-amber-400 border border-amber-500/20 text-xs font-semibold transition cursor-pointer"
            >
              <Pause className="w-3.5 h-3.5" /> Pause
            </button>
          )}
          {isPaused && (
            <button
              onClick={handleResume}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition cursor-pointer"
            >
              <Play className="w-3.5 h-3.5" /> Resume
            </button>
          )}
          <button
            onClick={fetchProgress}
            className="p-2 rounded-lg bg-[#18181f] hover:bg-[#22222b] text-[#8e8e99] hover:text-white border border-[#272732] transition cursor-pointer"
            title="Refresh Progress"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-[#a1a1aa] uppercase tracking-wider text-[11px]">
            Delivery Progress
          </span>
          <span className="font-extrabold text-white text-sm">
            {percent}% <span className="text-xs font-normal text-[#71717a]">({data.sent} of {data.total} Sent)</span>
          </span>
        </div>
        <div className="w-full h-3 rounded-full bg-[#1c1c24] border border-[#2b2b36] overflow-hidden p-0.5">
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{
              width: `${Math.max(2, percent)}%`,
              background: isCompleted
                ? 'linear-gradient(90deg, #10b981, #34d399)'
                : 'linear-gradient(90deg, #06b6d4, #3b82f6)'
            }}
          />
        </div>
      </div>

      {/* Metric KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Sent Card */}
        <div className="p-3.5 rounded-xl bg-[#141419] border border-[#24242e] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#8e8e99] uppercase tracking-wider">Delivered</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-emerald-400 mt-2">{data.sent}</div>
          <div className="text-[10px] text-[#71717a] mt-0.5">Successfully sent</div>
        </div>

        {/* In-Flight / Sending Card */}
        <div className="p-3.5 rounded-xl bg-[#141419] border border-[#24242e] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#8e8e99] uppercase tracking-wider">In-Flight</span>
            <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
          </div>
          <div className="text-2xl font-black text-cyan-400 mt-2">{data.sending || 0}</div>
          <div className="text-[10px] text-[#71717a] mt-0.5">Currently sending</div>
        </div>

        {/* Queued / Pending Card */}
        <div className="p-3.5 rounded-xl bg-[#141419] border border-[#24242e] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#8e8e99] uppercase tracking-wider">Pending</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-black text-amber-400 mt-2">{data.pending || (data.total - data.sent - data.failed)}</div>
          <div className="text-[10px] text-[#71717a] mt-0.5">Remaining in queue</div>
        </div>

        {/* Failed / Bounced Card */}
        <div className="p-3.5 rounded-xl bg-[#141419] border border-[#24242e] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#8e8e99] uppercase tracking-wider">Failed / Bounced</span>
            <XCircle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-black text-rose-400 mt-2">{data.failed}</div>
          <div className="text-[10px] text-[#71717a] mt-0.5">Quarantined</div>
        </div>
      </div>
    </div>
  );
}
