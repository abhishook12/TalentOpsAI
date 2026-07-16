import React, { useState, useEffect } from 'react';
import { Server, Activity, XCircle, CheckCircle, Loader2 } from 'lucide-react';

const BRIDGE_URL = 'http://localhost:1337';

export default function BridgeStatus({ onStatusChange }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${BRIDGE_URL}/health`);
      const data = await res.json();
      setStatus(data);
      setError(null);
      if (onStatusChange) onStatusChange(data.status === 'healthy');
    } catch (err) {
      setStatus({ status: 'unhealthy', error: 'Bridge unreachable' });
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

  const isHealthy = status?.status === 'healthy';

  return (
    <div className={`p-3 rounded-lg border flex flex-col gap-2 ${
      isHealthy ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
    }`}>
      <div className="flex items-center gap-2 font-medium">
        <Server className="w-5 h-5" />
        <span>Outlook Bridge: {isHealthy ? 'Online & Healthy' : 'Offline / Error'}</span>
      </div>
      
      {!isHealthy && (
        <div className="text-xs opacity-80 mt-1 pl-7">
          Error: {status?.error || error}
          {!status?.outlook_running && <div>Outlook is not running.</div>}
          {!status?.mailbox_accessible && <div>Mailbox not accessible.</div>}
        </div>
      )}
      
      {isHealthy && (
        <div className="text-xs opacity-80 pl-7 flex items-center gap-4">
          <span className="flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Outlook Running</span>
          <span className="flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Mailbox Access</span>
        </div>
      )}
    </div>
  );
}
