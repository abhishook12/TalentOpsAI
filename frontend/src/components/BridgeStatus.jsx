import React, { useState, useEffect } from 'react';
import { Server, CheckCircle, Loader2 } from 'lucide-react';
import api from '../services/api';

export default function BridgeStatus({ onStatusChange }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkHealth = async () => {
    try {
      const res = await api.get('/api/v1/bridge/status');
      setStatus(res.data);
      setError(null);
      if (onStatusChange) onStatusChange(res.data.status === 'online');
    } catch (err) {
      if (err.response?.status === 404) {
        // Fallback if not prefixed
        try {
          const res = await api.get('/bridge/status');
          setStatus(res.data);
          setError(null);
          if (onStatusChange) onStatusChange(res.data.status === 'online');
          setLoading(false);
          return;
        } catch (fallbackErr) {}
      }
      
      setStatus({ status: 'offline', message: 'Bridge unreachable' });
      setError('Bridge unreachable');
      if (onStatusChange) onStatusChange(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  if (loading && !status) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="w-4 h-4 animate-spin" />
        Checking Outlook Bridge...
      </div>
    );
  }

  const isHealthy = status?.status === 'online';

  return (
    <div className={`p-3 rounded-lg border flex flex-col gap-2 ${
      isHealthy ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
    }`}>
      <div className="flex items-center justify-between font-medium">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5" />
          <span>Outlook Bridge: {isHealthy ? 'Online & Healthy' : 'Offline / Error'}</span>
        </div>
        {status?.version && <span className="text-xs opacity-60 font-mono">v{status.version}</span>}
      </div>
      
      {!isHealthy && (
        <div className="text-xs opacity-80 mt-1 pl-7">
          Error: {status?.message || error}
          {!status && <div>Not connected to database.</div>}
        </div>
      )}
      
      {isHealthy && (
        <div className="text-xs opacity-80 pl-7 grid grid-cols-2 gap-2 mt-1">
          <span className="flex items-center gap-1" title="Uptime">
             Uptime: {Math.floor(status.uptime_seconds / 60)}m {status.uptime_seconds % 60}s
          </span>
          <span className="flex items-center gap-1" title="Last Email">
             {status.last_successful_email_at ? `Last Send: ${new Date(status.last_successful_email_at).toLocaleTimeString()}` : 'No emails sent yet'}
          </span>
          <span className="flex items-center gap-1" title="Retries">
             Errors: {status.consecutive_errors}
          </span>
          <span className="flex items-center gap-1" title="Last Heartbeat">
             {status.last_heartbeat ? `Heartbeat: ${new Date(status.last_heartbeat).toLocaleTimeString()}` : 'N/A'}
          </span>
        </div>
      )}
    </div>
  );
}
