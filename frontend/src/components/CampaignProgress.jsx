import React, { useEffect, useState, useCallback, useRef } from 'react';
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
  const prevStatusRef = useRef(null);
  const isFirstFetchRef = useRef(true);

  const fetchProgress = useCallback(async () => {
    if (!campaignId) return;
    try {
      const res = await api.get(`/campaigns/${campaignId}/progress`);
      if (res.data) {
        setData(prev => ({ ...prev, ...res.data }));
        setLoading(false);
        const newStatus = res.data.status;
        const oldStatus = prevStatusRef.current;
        // Only trigger onStatusChange if status actually changed during active monitoring
        if (onStatusChange && !isFirstFetchRef.current && oldStatus && newStatus !== oldStatus) {
          onStatusChange(newStatus, oldStatus);
        }
        prevStatusRef.current = newStatus;
        isFirstFetchRef.current = false;
      }
    } catch (err) {
      console.warn("Progress fetch fallback polling:", err);
      setLoading(false);
    }
  }, [campaignId, onStatusChange]);

  useEffect(() => {
    fetchProgress();
    // Poll every 1.5s while active/sending, slow down to 10s if terminal
    const isTerminal = ['completed', 'failed', 'cancelled'].includes(data.status);
    const intervalMs = isTerminal ? 10000 : 1500;
    const timer = setInterval(() => {
      fetchProgress();
    }, intervalMs);

    return () => clearInterval(timer);
  }, [fetchProgress, data.status]);

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
    <div className="p-6 bg-[#121212] border border-[#22222a] rounded-xl flex flex-col gap-6 text-white">
      {/* Top Header Strip */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3.5">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center border shadow-md ${
            isCompleted
              ? 'bg-white/10 border-white/30 text-white'
              : isPaused
              ? 'bg-white/10 border-white/25 text-[#e41937]'
              : 'bg-[#e41937]/15 border-[#e41937]/50/30 text-[#fe063f]'
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
                  ? 'bg-white/10 text-white border-white/25'
                  : isPaused
                  ? 'bg-white/10 text-[#e41937] border-white/20'
                  : 'bg-[#e41937]/15 text-[#fe063f] border-[#e41937]/50/25 animate-pulse'
              }`}>
                {data.status || 'Active'}
              </span>
            </div>
            <p className="text-xs text-[#8e8e99] mt-0.5 m-0 font-normal">
              {isCompleted
                ? `All ${data.total} recipients have been processed.`
                : isPaused
                ? 'Queue is paused. Resuming will continue remaining recipients.'
                : 'Dispatching outreach in real-time via high-speed Cloud Direct API.'}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {isActive && (
            <button
              onClick={handlePause}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#202026] hover:bg-[#282830] text-[#e41937] border border-white/15 text-xs font-semibold transition cursor-pointer"
            >
              <Pause className="w-3.5 h-3.5" /> Pause
            </button>
          )}
          {isPaused && (
            <button
              onClick={handleResume}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#e41937] text-white hover:bg-[#e41937] text-white text-white text-xs font-semibold shadow-md shadow-[#e41937]/20 transition cursor-pointer"
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
                ? 'linear-gradient(90deg, #ffffff, #d4d4d8)'
                : 'linear-gradient(90deg, #d4d4d8, #d4d4d8)'
            }}
          />
        </div>
      </div>

      {/* Metric KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Sent Card */}
        <div className="p-3.5 rounded-xl bg-[#141419] border border-[#27272a] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#8e8e99] uppercase tracking-wider">Sent / Delivered</span>
            <CheckCircle2 className="w-4 h-4 text-white" />
          </div>
          <div className="text-2xl font-black text-white mt-2">{data.sent}</div>
          <div className="text-[10px] text-[#71717a] mt-0.5">
            {data.delivered > 0 ? `${data.delivered} verified delivered` : 'Successfully dispatched'}
          </div>
        </div>

        {/* In-Flight / Sending Card */}
        <div className="p-3.5 rounded-xl bg-[#141419] border border-[#27272a] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#8e8e99] uppercase tracking-wider">In-Flight</span>
            <Loader2 className="w-4 h-4 text-[#fe063f] animate-spin" />
          </div>
          <div className="text-2xl font-black text-[#fe063f] mt-2">{data.sending || 0}</div>
          <div className="text-[10px] text-[#71717a] mt-0.5">Currently sending</div>
        </div>

        {/* Queued / Pending Card */}
        <div className="p-3.5 rounded-xl bg-[#141419] border border-[#27272a] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#8e8e99] uppercase tracking-wider">Pending</span>
            <Clock className="w-4 h-4 text-[#e41937]" />
          </div>
          <div className="text-2xl font-black text-[#e41937] mt-2">{data.pending || (data.total - data.sent - data.failed)}</div>
          <div className="text-[10px] text-[#71717a] mt-0.5">Remaining in queue</div>
        </div>

        {/* Failed / Bounced Card */}
        <div className="p-3.5 rounded-xl bg-[#141419] border border-[#27272a] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#8e8e99] uppercase tracking-wider">Bounced / Failed</span>
            <XCircle className="w-4 h-4 text-[#fe063f]" />
          </div>
          <div className="text-2xl font-black text-[#fe063f] mt-2">{data.failed || data.bounced || 0}</div>
          <div className="text-[10px] text-[#fe063f]/80 mt-0.5">
            {data.bounced > 0 ? `${data.bounced} NDR bounces detected` : 'Quarantined'}
          </div>
        </div>
      </div>
    </div>
  );
}
