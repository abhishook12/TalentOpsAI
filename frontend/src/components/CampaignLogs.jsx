import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Loader2, CheckCircle2, XCircle, Search, Filter, RefreshCw,
  Mail, AlertCircle, Clock, Send, Eye, MessageSquare
} from 'lucide-react';
import api from '../services/api';

export default function CampaignLogs({ campaignId }) {
  const [filter, setFilter] = useState('all'); // all, delivered, sending, failed, queued
  const [search, setSearch] = useState('');

  const { data: logsData, isLoading: loading, refetch, isFetching } = useQuery({
    queryKey: ['campaign-logs', campaignId],
    queryFn: async () => {
      if (!campaignId) return [];
      const res = await api.get(`/campaigns/${campaignId}/delivery-logs`);
      return res.data.items || [];
    },
    enabled: !!campaignId,
    refetchInterval: 1500 // Poll every 1.5 seconds for real-time live feed
  });

  const logs = logsData || [];

  const filteredLogs = useMemo(() => {
    return logs.filter(log => {
      const statusLower = (log.status || '').toLowerCase();
      if (filter === 'delivered' && !['delivered', 'sent'].includes(statusLower)) return false;
      if (filter === 'sending' && !['sending', 'retrying'].includes(statusLower)) return false;
      if (filter === 'queued' && !['queued', 'pending'].includes(statusLower)) return false;
      if (filter === 'failed' && !['failed', 'bounced'].includes(statusLower)) return false;
      
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchEmail = (log.email || '').toLowerCase().includes(q);
        const matchError = (log.error || '').toLowerCase().includes(q);
        return matchEmail || matchError;
      }
      return true;
    });
  }, [logs, filter, search]);

  const deliveredCount = logs.filter(l => ['delivered', 'sent'].includes((l.status || '').toLowerCase())).length;
  const failedCount = logs.filter(l => ['failed', 'bounced'].includes((l.status || '').toLowerCase())).length;
  const inFlightCount = logs.filter(l => ['sending', 'retrying', 'queued', 'pending'].includes((l.status || '').toLowerCase())).length;

  return (
    <div className="flex flex-col bg-[#111116] rounded-xl border border-[#22222a] overflow-hidden text-white shadow-xl">
      {/* Table Header Bar */}
      <div className="p-4 border-b border-[#22222a] bg-[#141419] flex flex-wrap justify-between items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-[#1a1a22] p-1 rounded-lg border border-[#282834]">
            {[
              { id: 'all', label: `All (${logs.length})` },
              { id: 'delivered', label: `Sent (${deliveredCount})`, color: 'text-emerald-400' },
              { id: 'sending', label: `In-Flight (${inFlightCount})`, color: 'text-cyan-400' },
              { id: 'failed', label: `Failed (${failedCount})`, color: 'text-rose-400' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setFilter(tab.id)}
                className={`px-3 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer ${
                  filter === tab.id
                    ? 'bg-[#262633] text-white shadow-sm'
                    : 'text-[#8e8e99] hover:text-white hover:bg-[#20202a]'
                }`}
              >
                <span className={tab.color || ''}>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#71717a]" />
            <input
              type="text"
              placeholder="Search recipient..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-56 bg-[#181820] border border-[#2b2b38] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-[#52525b] focus:outline-none focus:border-cyan-500 transition"
            />
          </div>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-lg bg-[#181820] hover:bg-[#22222d] text-[#8e8e99] hover:text-white border border-[#2b2b38] transition cursor-pointer"
            title="Refresh logs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Table Body */}
      <div className="overflow-x-auto max-h-[420px] custom-scrollbar">
        {loading && logs.length === 0 ? (
          <div className="py-16 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
            <span className="text-xs text-[#8e8e99]">Connecting to live delivery stream...</span>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="py-16 flex flex-col items-center justify-center text-center p-6 text-[#71717a]">
            <Mail className="w-10 h-10 text-[#3f3f46] mb-2" />
            <div className="text-xs font-semibold text-[#a1a1aa]">No delivery logs recorded yet</div>
            <p className="text-[11px] text-[#71717a] mt-0.5">
              Logs will stream in here in real time as the local Outlook Bridge dispatches emails.
            </p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead className="bg-[#141419]/90 backdrop-blur sticky top-0 border-b border-[#22222a] z-10">
              <tr>
                <th className="py-2.5 px-4 font-bold text-[11px] text-[#8e8e99] uppercase tracking-wider">Recipient</th>
                <th className="py-2.5 px-4 font-bold text-[11px] text-[#8e8e99] uppercase tracking-wider">Status</th>
                <th className="py-2.5 px-4 font-bold text-[11px] text-[#8e8e99] uppercase tracking-wider">Time</th>
                <th className="py-2.5 px-4 font-bold text-[11px] text-[#8e8e99] uppercase tracking-wider">Delivery Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1e26] text-xs">
              {filteredLogs.map((log) => {
                const s = (log.status || '').toLowerCase();
                const isDelivered = ['delivered', 'sent'].includes(s);
                const isFailed = ['failed', 'bounced'].includes(s);
                const isSending = ['sending', 'retrying'].includes(s);
                const isQueued = ['queued', 'pending'].includes(s);

                return (
                  <tr key={log.id} className="hover:bg-[#16161d] transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-mono text-xs text-white font-medium">{log.email}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                        isDelivered
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25'
                          : isFailed
                          ? 'bg-rose-500/15 text-rose-400 border-rose-500/25'
                          : isSending
                          ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/25 animate-pulse'
                          : 'bg-amber-500/15 text-amber-400 border-amber-500/25'
                      }`}>
                        {isDelivered && <CheckCircle2 className="w-3 h-3" />}
                        {isFailed && <XCircle className="w-3 h-3" />}
                        {isSending && <Loader2 className="w-3 h-3 animate-spin" />}
                        {isQueued && <Clock className="w-3 h-3" />}
                        {log.status || 'Queued'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-[#8e8e99] text-xs whitespace-nowrap">
                      {log.last_sent ? new Date(log.last_sent).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      {log.error ? (
                        <span className="text-rose-400 block max-w-sm truncate font-mono text-[11px]" title={log.error}>
                          {log.error} {log.retry_count > 0 && `(Retry ${log.retry_count})`}
                        </span>
                      ) : isDelivered ? (
                        <span className="text-emerald-400/90 text-[11px] font-medium flex items-center gap-1">
                          Sent via Outlook COM Bridge
                        </span>
                      ) : isSending ? (
                        <span className="text-cyan-400/90 text-[11px] font-medium flex items-center gap-1">
                          Transferring to Outlook...
                        </span>
                      ) : (
                        <span className="text-[#52525b] text-[11px]">Queued in dispatch pipeline</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
