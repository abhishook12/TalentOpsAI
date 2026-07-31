import React, { useState, useEffect } from 'react';
import { Database, Loader2 } from 'lucide-react';
import api from '../services/api';
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
    const interval = setInterval(checkHealth, 5000);
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
    <div className={`p-4 rounded-xl border w-full flex flex-col gap-1 ${
      isHealthy ? 'bg-[#0f2a15] border-green-900/80' : 'bg-[#2a0f0f] border-red-900/80'
    }`}>
      <div className={`flex items-center gap-2 font-bold text-[15px] ${isHealthy ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
        <Database size={18} strokeWidth={2.5} />
        <span>Outlook Bridge: {isHealthy ? 'Online & Healthy' : 'Offline / Error'}</span>
      </div>
      
      <ConnectOutlookModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)}
        onSuccess={checkHealth} 
      />

      {!isHealthy ? (
        <div className="flex flex-col gap-2 mt-1 pl-[26px]">
          <div className="text-sm font-medium text-red-500/80">
            Error: {status?.error || status?.message || error || "Bridge unreachable"}
          </div>
          <button 
            id="connect-outlook-btn"
            onClick={() => setIsModalOpen(true)}
            className="px-3 py-1.5 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 text-red-400 rounded-lg text-sm font-bold transition-colors self-start mt-1"
          >
            Connect your Outlook
          </button>
        </div>
      ) : (
        <div className="text-sm font-medium text-[#22c55e]/80 pl-[26px]">
          Outlook Bridge Connected
        </div>
      )}
    </div>
  );
}
