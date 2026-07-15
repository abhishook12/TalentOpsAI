import { useState, useEffect } from 'react';
import api from '../../services/api';

export default function HealthDashboard() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchHealth = async () => {
    try {
      // Don't set loading true on subsequent fetches to prevent flickering
      const { data } = await api.get('/health/system');
      setHealthData(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error("Failed to load health data", err);
      setError("Unable to connect to health API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  if (loading && !healthData) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-[var(--text-secondary)]">Analyzing system vitals...</p>
        </div>
      </div>
    );
  }

  const getStatusColor = (status) => {
    if (status === 'healthy' || status === 'ok') return 'var(--success, #10b981)';
    if (status === 'warning' || status === 'degraded') return 'var(--warning, #f59e0b)';
    return 'var(--danger, #ef4444)';
  };

  const getStatusIcon = (status) => {
    if (status === 'healthy' || status === 'ok') return 'ti-circle-check-filled text-emerald-500';
    if (status === 'warning' || status === 'degraded') return 'ti-alert-triangle-filled text-amber-500';
    return 'ti-alert-circle-filled text-red-500';
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">
            System Health
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1 flex items-center gap-2">
            <i className="ti ti-activity" /> Live platform diagnostics
            {healthData && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--surface-sunken)] border border-[var(--border-subtle)] ml-2 uppercase font-medium">
                {healthData.environment}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-[var(--text-tertiary)] tabular-nums">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </span>
          <button 
            onClick={fetchHealth}
            className="px-3 py-1.5 bg-[var(--surface-sunken)] hover:bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded-md transition-colors flex items-center gap-2"
          >
            <i className="ti ti-refresh" /> Refresh
          </button>
        </div>
      </header>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg flex items-center gap-3">
          <i className="ti ti-wifi-off text-xl" />
          <div>
            <div className="font-semibold">Connection Lost</div>
            <div className="text-sm opacity-80">{error}</div>
          </div>
        </div>
      )}

      {healthData && (
        <>
          {/* Global Status Banner */}
          <div 
            className="p-6 rounded-xl border flex items-center gap-4"
            style={{ 
              backgroundColor: `color-mix(in srgb, ${getStatusColor(healthData.status)} 10%, transparent)`,
              borderColor: `color-mix(in srgb, ${getStatusColor(healthData.status)} 20%, transparent)`
            }}
          >
            <i className={`ti ${getStatusIcon(healthData.status)} text-4xl drop-shadow-md`} />
            <div>
              <h2 className="text-xl font-bold" style={{ color: getStatusColor(healthData.status) }}>
                Platform Status: {healthData.status.toUpperCase()}
              </h2>
              <p className="text-[var(--text-secondary)]">
                {healthData.status === 'healthy' 
                  ? 'All critical systems are operational and responding within normal parameters.'
                  : 'The system is experiencing degradation. Review component statuses below.'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            
            {/* Database */}
            <div className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <i className="ti ti-database text-blue-500 text-xl" />
                </div>
                <i className={`ti ${getStatusIcon(healthData.components?.database?.status)} text-xl`} />
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-1">Database Engine</h3>
              <p className="text-sm text-[var(--text-secondary)]">SQLite Operational</p>
              <div className="mt-4 pt-4 border-t border-[var(--border-subtle)] text-sm font-medium">
                {healthData.components?.database?.message || healthData.components?.database?.error}
              </div>
            </div>

            {/* Outlook Bridge */}
            <div className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                  <i className="ti ti-mail text-indigo-500 text-xl" />
                </div>
                <i className={`ti ${getStatusIcon(healthData.components?.outlook_bridge?.status)} text-xl`} />
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-1">Outlook Bridge</h3>
              <p className="text-sm text-[var(--text-secondary)]">Windows COM Server</p>
              
              <div className="mt-4 pt-4 border-t border-[var(--border-subtle)] space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--text-secondary)]">Localhost:</span>
                  <span className={healthData.components?.outlook_bridge?.outlook_running ? 'text-emerald-500' : 'text-red-500'}>
                    {healthData.components?.outlook_bridge?.outlook_running ? 'Bound' : 'Offline'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--text-secondary)]">Mailbox:</span>
                  <span className={healthData.components?.outlook_bridge?.mailbox_accessible ? 'text-emerald-500' : 'text-red-500'}>
                    {healthData.components?.outlook_bridge?.mailbox_accessible ? 'Accessible' : 'Blocked'}
                  </span>
                </div>
              </div>
            </div>

            {/* Memory */}
            <div className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                  <i className="ti ti-cpu text-purple-500 text-xl" />
                </div>
                <span className="text-lg font-bold tabular-nums" style={{ color: healthData.components?.memory?.percent > 85 ? 'var(--danger)' : 'var(--text-primary)' }}>
                  {healthData.components?.memory?.percent}%
                </span>
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-1">RAM Usage</h3>
              <p className="text-sm text-[var(--text-secondary)]">System Memory</p>
              
              <div className="mt-4 pt-4 border-t border-[var(--border-subtle)] space-y-2">
                <div className="w-full bg-[var(--surface-sunken)] rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all duration-500"
                    style={{ 
                      width: `${healthData.components?.memory?.percent}%`,
                      backgroundColor: healthData.components?.memory?.percent > 85 ? 'var(--danger)' : 'var(--primary)'
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs text-[var(--text-tertiary)]">
                  <span>{healthData.components?.memory?.available_gb} GB free</span>
                  <span>{healthData.components?.memory?.total_gb} GB total</span>
                </div>
              </div>
            </div>

            {/* Disk */}
            <div className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                  <i className="ti ti-device-floppy text-emerald-500 text-xl" />
                </div>
                <span className="text-lg font-bold tabular-nums" style={{ color: healthData.components?.disk?.percent > 85 ? 'var(--danger)' : 'var(--text-primary)' }}>
                  {healthData.components?.disk?.percent}%
                </span>
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-1">Storage</h3>
              <p className="text-sm text-[var(--text-secondary)]">Local Disk</p>
              
              <div className="mt-4 pt-4 border-t border-[var(--border-subtle)] space-y-2">
                <div className="w-full bg-[var(--surface-sunken)] rounded-full h-2 overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all duration-500"
                    style={{ 
                      width: `${healthData.components?.disk?.percent}%`,
                      backgroundColor: healthData.components?.disk?.percent > 85 ? 'var(--danger)' : 'var(--primary)'
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs text-[var(--text-tertiary)]">
                  <span>{healthData.components?.disk?.free_gb} GB free</span>
                  <span>{healthData.components?.disk?.total_gb} GB total</span>
                </div>
              </div>
            </div>

          </div>
        </>
      )}
    </div>
  );
}
