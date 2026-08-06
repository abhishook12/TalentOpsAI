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
    <div style={{
      background: 'rgba(25, 25, 25, 0.6)',
      border: isHealthy ? '1px solid color-mix(in srgb, var(--success) 30%, transparent)' : '1px solid color-mix(in srgb, var(--danger) 30%, transparent)',
      borderRadius: 6,
      padding: 24,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      backdropFilter: 'blur(12px)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: isHealthy ? 0 : 16 }}>
        <div style={{ 
          width: 48, height: 48, borderRadius: 6, 
          background: isHealthy ? 'rgba(74, 222, 128, 0.1)' : 'rgba(255, 170, 0, 0.1)', 
          display: 'flex', alignItems: 'center', justifyContent: 'center' 
        }}>
          <Database size={24} color={isHealthy ? "#4ade80" : "#ffaa00"} />
        </div>
        <div>
          <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", color: isHealthy ? '#4ade80' : '#ffaa00' }}>
            {isHealthy ? 'Bridge Online & Healthy' : 'Bridge Offline / Error'}
          </h4>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)', fontFamily: "'DM Sans', sans-serif" }}>
            {isHealthy ? 'Local SMTP proxy is running' : 'Unable to connect to bridge'}
          </p>
        </div>
      </div>
      
      <ConnectOutlookModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)}
        onSuccess={checkHealth} 
      />

      {!isHealthy && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 'auto' }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--danger)' }}>
            {status?.error || status?.message || error || "Bridge unreachable"}
          </div>
          <button 
            onClick={() => setIsModalOpen(true)}
            style={{ 
              padding: '10px', borderRadius: 8, 
              border: '1px solid color-mix(in srgb, var(--danger) 30%, transparent)', 
              background: 'color-mix(in srgb, var(--danger) 10%, transparent)', 
              color: 'var(--danger)', fontWeight: 600, cursor: 'pointer', fontFamily: "'DM Sans', sans-serif" 
            }}
          >
            Connect your Outlook
          </button>
        </div>
      )}
    </div>
  );
}
