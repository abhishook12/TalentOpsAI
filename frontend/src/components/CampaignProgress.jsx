import React, { useEffect, useState } from 'react';
import { Play, Pause, RefreshCw, CheckCircle, XCircle, Clock, Activity, Loader2 } from 'lucide-react';
import api from '../services/api';

export default function CampaignProgress({ campaignId, onStatusChange }) {
  const [data, setData] = useState({
    status: 'draft',
    total: 0,
    sent: 0,
    failed: 0,
    pending: 0,
    new_logs: []
  });
  const [logs, setLogs] = useState([]);
  const [isConnecting, setIsConnecting] = useState(true);

  useEffect(() => {
    if (!campaignId) return;

    setIsConnecting(true);
    const eventSource = new EventSource(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/campaigns/${campaignId}/progress`);

    eventSource.onmessage = (event) => {
      setIsConnecting(false);
      const parsedData = JSON.parse(event.data);
      setData(parsedData);
      
      if (parsedData.new_logs && parsedData.new_logs.length > 0) {
        setLogs(prev => [...parsedData.new_logs, ...prev].slice(0, 50)); // Keep last 50 logs
      }
      
      if (onStatusChange) {
        onStatusChange(parsedData.status);
      }
      
      if (parsedData.status === 'completed' || parsedData.status === 'failed') {
        eventSource.close();
      }
    };

    eventSource.onerror = (error) => {
      console.error("SSE Error:", error);
      setIsConnecting(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [campaignId]);

  const progressPercent = data.total > 0 ? ((data.sent + data.failed) / data.total) * 100 : 0;
  
  const handleAction = async (action) => {
    try {
      await api.post(`/campaigns/${campaignId}/${action}`);
      // UI will update via SSE
    } catch (e) {
      console.error(`Failed to ${action} campaign`, e);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Metrics Row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl p-4 flex flex-col justify-center">
          <div className="text-[var(--text-muted)] text-sm mb-1 flex items-center gap-1">
            <Activity className="w-4 h-4" /> Total
          </div>
          <div className="text-2xl font-semibold">{data.total}</div>
        </div>
        <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl p-4 flex flex-col justify-center relative overflow-hidden">
          <div className="absolute inset-0 bg-green-500/5 pointer-events-none"></div>
          <div className="text-green-400 text-sm mb-1 flex items-center gap-1">
            <CheckCircle className="w-4 h-4" /> Sent
          </div>
          <div className="text-2xl font-semibold text-green-400">{data.sent}</div>
        </div>
        <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl p-4 flex flex-col justify-center relative overflow-hidden">
          <div className="absolute inset-0 bg-red-500/5 pointer-events-none"></div>
          <div className="text-red-400 text-sm mb-1 flex items-center gap-1">
            <XCircle className="w-4 h-4" /> Failed
          </div>
          <div className="text-2xl font-semibold text-red-400">{data.failed}</div>
        </div>
        <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl p-4 flex flex-col justify-center">
          <div className="text-[var(--text-muted)] text-sm mb-1 flex items-center gap-1">
            <Clock className="w-4 h-4" /> Pending
          </div>
          <div className="text-2xl font-semibold">{data.pending}</div>
        </div>
      </div>

      {/* Progress Bar & Controls */}
      <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl p-4">
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-2">
            <span className="font-medium">Campaign Progress</span>
            {isConnecting && <Loader2 className="w-4 h-4 animate-spin text-[var(--accent)]" />}
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              data.status === 'active' ? 'bg-green-500/20 text-green-400' :
              data.status === 'paused' ? 'bg-yellow-500/20 text-yellow-400' :
              data.status === 'completed' ? 'bg-blue-500/20 text-blue-400' :
              'bg-[var(--card-border)] text-[var(--text-muted)]'
            }`}>
              {data.status.toUpperCase()}
            </span>
          </div>
          <div className="flex gap-2">
            {data.status === 'paused' || data.status === 'draft' ? (
              <button onClick={() => handleAction('start')} className="btn-primary text-sm py-1.5 px-4 flex items-center gap-1">
                <Play className="w-4 h-4" /> Start
              </button>
            ) : data.status === 'active' ? (
              <button onClick={() => handleAction('pause')} className="btn-secondary text-sm py-1.5 px-4 flex items-center gap-1 bg-yellow-500/10 text-yellow-500 border-yellow-500/20 hover:bg-yellow-500/20">
                <Pause className="w-4 h-4" /> Pause
              </button>
            ) : null}
            {data.status === 'paused' && data.sent > 0 && (
              <button onClick={() => handleAction('resume')} className="btn-secondary text-sm py-1.5 px-4 flex items-center gap-1 border-[var(--accent)]/50 text-[var(--accent)]">
                <RefreshCw className="w-4 h-4" /> Resume
              </button>
            )}
          </div>
        </div>
        
        <div className="h-3 bg-[var(--card-bg)] rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-[var(--accent)] to-purple-500 transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-[var(--text-muted)] mt-1.5">
          <span>{Math.round(progressPercent)}% Completed</span>
          <span>{data.sent + data.failed} of {data.total} Processed</span>
        </div>
      </div>

      {/* Live Logs */}
      <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden flex flex-col h-64">
        <div className="px-4 py-2 bg-[var(--card-bg)] border-b border-[var(--card-border)] text-sm font-medium flex items-center justify-between">
          <span>Live Activity Feed</span>
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
        </div>
        <div className="overflow-y-auto p-4 flex-1 space-y-2">
          {logs.length === 0 ? (
            <div className="text-center text-[var(--text-muted)] mt-10 text-sm">No activity yet. Start the campaign to see logs.</div>
          ) : (
            logs.map((log, i) => (
              <div key={`${log.log_id}-${i}`} className="flex items-start gap-3 text-sm py-1 border-b border-[var(--card-border)] last:border-0">
                <div className="text-[var(--text-muted)] text-xs mt-0.5 whitespace-nowrap">
                  {new Date(log.time).toLocaleTimeString()}
                </div>
                <div>
                  {log.status === 'sending' && <Loader2 className="w-4 h-4 animate-spin text-blue-400" />}
                  {log.status === 'delivered' && <CheckCircle className="w-4 h-4 text-green-400" />}
                  {log.status === 'failed' && <XCircle className="w-4 h-4 text-red-400" />}
                </div>
                <div className="flex-1">
                  <span className="font-medium">{log.email}</span>
                  <span className="text-[var(--text-muted)] mx-2">—</span>
                  <span className={`
                    ${log.status === 'delivered' ? 'text-green-400' : ''}
                    ${log.status === 'failed' ? 'text-red-400' : ''}
                    ${log.status === 'sending' ? 'text-blue-400' : ''}
                  `}>
                    {log.status.toUpperCase()}
                  </span>
                  {log.error && (
                    <div className="text-xs text-red-400/80 mt-1">{log.error}</div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
