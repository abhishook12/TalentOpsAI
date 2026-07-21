import React, { useState, useEffect } from 'react';
import { Server, CheckCircle, Loader2 } from 'lucide-react';
import api from '../services/api';
import { Link } from '@tanstack/react-router';
import ConnectOutlookModal from './ConnectOutlookModal';

export default function BridgeStatus({ onStatusChange }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const checkHealth = async () => {
    try {
      const res = await api.get('/health/outlook');
      setStatus(res.data);
      setError(null);
      if (onStatusChange) onStatusChange(res.data.status === 'ok');
    } catch (err) {
      
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

  const isHealthy = status?.status === 'ok';

  return (
    <div className={`p-3 rounded-lg border flex flex-col gap-2 ${
      isHealthy ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
    }`}>
      <div className="flex items-center justify-between font-medium">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5" />
          <span>Outlook Bridge: {isHealthy ? 'Online & Healthy' : 'Offline / Error'}</span>
        </div>
      </div>
      
      <ConnectOutlookModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)}
        onSuccess={checkHealth} 
      />

      {!isHealthy && (
        <div className="flex flex-col gap-2 mt-1 pl-7">
          <div className="text-xs opacity-80">
            Error: {status?.error || status?.message || error || "Bridge unreachable"}
          </div>
          <button 
            id="connect-outlook-btn"
            onClick={() => setIsModalOpen(true)}
            className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-500 rounded text-sm font-medium transition-colors self-start"
          >
            Connect your Outlook
          </button>
        </div>
      )}
      
      {isHealthy && (
        <div className="text-xs opacity-80 pl-7 mt-1">
          {status.message || "Connected (Polling Mode)"}
        </div>
      )}
    </div>
  );
}
