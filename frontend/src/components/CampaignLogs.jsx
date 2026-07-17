import React, { useState, useEffect } from 'react';
import { Loader2, CheckCircle, XCircle, Search, Filter } from 'lucide-react';
import api from '../services/api';

export default function CampaignLogs({ campaignId }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, delivered, failed, retrying
  const [search, setSearch] = useState('');

  useEffect(() => {
    let interval;
    if (campaignId) {
      fetchLogs();
      // Poll every 5s while looking at logs
      interval = setInterval(fetchLogs, 5000);
    }
    return () => clearInterval(interval);
  }, [campaignId]);

  const fetchLogs = async () => {
    try {
      // In a real app we'd have a specific /campaigns/{id}/logs endpoint.
      // We don't have this in the backend yet, but we'll mock the integration
      // or we can just fetch recruiters which have status and last_error
      const res = await api.get(`/campaigns/${campaignId}/recruiters`);
      
      // Transform recruiters to logs format for display
      const items = (Array.isArray(res.data) ? res.data : res.data.items || []).map(r => ({
        id: r.campaign_recruiter_id,
        email: r.recruiter?.email || 'unknown',
        status: r.status.toLowerCase(),
        last_sent: r.last_sent_at,
        error: r.last_error,
        retry_count: r.retry_count || 0
      }));
      
      setLogs(items);
    } catch (e) {
      console.error("Failed to fetch logs", e);
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => {
    if (filter !== 'all' && log.status !== filter) return false;
    if (search && !log.email.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full bg-[var(--bg-surface)] rounded-lg border border-[var(--border)] overflow-hidden">
      <div className="p-3 border-b border-[var(--border)] bg-[var(--card-bg)] flex justify-between items-center gap-4">
        <div className="flex gap-2">
          {['all', 'delivered', 'failed', 'retrying', 'queued'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors capitalize ${
                filter === f 
                  ? 'bg-[var(--accent)] text-white' 
                  : 'bg-[var(--bg-surface)] text-[var(--text-secondary)] border border-[var(--border)] hover:bg-[var(--card-bg)]'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-48 bg-[var(--bg-surface)] border border-[var(--border)] rounded-md pl-8 pr-3 py-1.5 text-xs focus:border-[var(--accent)] outline-none"
          />
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {loading && logs.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--accent)]" />
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-8 text-center text-sm text-[var(--text-muted)]">No logs match your filter.</div>
        ) : (
          <table className="w-full text-left text-sm border-collapse">
            <thead className="bg-[var(--card-bg)] text-[var(--text-muted)] sticky top-0 border-b border-[var(--border)]">
              <tr>
                <th className="py-2 px-4 font-medium text-xs">Recipient Email</th>
                <th className="py-2 px-4 font-medium text-xs">Status</th>
                <th className="py-2 px-4 font-medium text-xs">Timestamp</th>
                <th className="py-2 px-4 font-medium text-xs">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-[var(--card-bg)] group">
                  <td className="py-2.5 px-4 font-mono text-xs text-[var(--text-primary)]">{log.email}</td>
                  <td className="py-2.5 px-4">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium uppercase border ${
                      log.status === 'delivered' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                      log.status === 'failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                      log.status === 'retrying' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                      log.status === 'queued' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                      'bg-[var(--bg-surface)] text-[var(--text-muted)] border-[var(--border)]'
                    }`}>
                      {log.status === 'delivered' && <CheckCircle className="w-3 h-3" />}
                      {log.status === 'failed' && <XCircle className="w-3 h-3" />}
                      {log.status === 'retrying' && <Loader2 className="w-3 h-3 animate-spin" />}
                      {log.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-xs text-[var(--text-secondary)]">
                    {log.last_sent ? new Date(log.last_sent).toLocaleString() : '-'}
                  </td>
                  <td className="py-2.5 px-4 text-xs">
                    {log.error ? (
                      <span className="text-red-400 block max-w-xs truncate" title={log.error}>
                        {log.error} {log.retry_count > 0 && `(Attempt ${log.retry_count})`}
                      </span>
                    ) : (
                      <span className="text-[var(--text-muted)]">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
