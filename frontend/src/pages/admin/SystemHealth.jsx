import { useState, useEffect } from 'react';
import api from '../../services/api';
import { HeartPulse, Database, Server, Cpu, HardDrive, RefreshCw } from 'lucide-react';

export default function SystemHealth() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/health');
      setHealth(data);
    } catch (err) {
      console.error('Failed to load health metrics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !health) {
    return <div style={{ padding: 40, color: 'var(--text-muted)', textAlign: 'center' }}>Loading system vitals...</div>;
  }

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1200, margin: '0 auto', color: 'var(--text-primary)', fontFamily: '"Inter", sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, background: 'linear-gradient(90deg, #fff, #aaa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>System Health</h1>
          <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', fontSize: 14 }}>Real-time infrastructure and database performance metrics.</p>
        </div>
        <button onClick={fetchHealth} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderRadius: 8, background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid var(--card-border)', cursor: 'pointer', transition: 'all 0.2s' }}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 24, marginBottom: 32 }}>
        
        {/* API Status */}
        <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <Server size={20} color="#3b82f6" />
            <span style={{ fontWeight: 600 }}>API Server</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: health?.status === 'healthy' ? '#10b981' : (health?.status === 'warning' ? '#f59e0b' : '#ef4444') }}>
              {health?.status === 'healthy' ? 'Online' : (health?.status === 'warning' ? 'Warning' : 'Degraded')}
            </div>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>Environment: {health?.environment || 'Production'}</div>
        </div>

        {/* Database Status */}
        <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <Database size={20} color="#8b5cf6" />
            <span style={{ fontWeight: 600 }}>Database (PostgreSQL)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: health?.components?.database?.status === 'healthy' ? '#10b981' : '#ef4444' }}>
              {health?.components?.database?.status === 'healthy' ? 'Connected' : 'Error'}
            </div>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>{health?.components?.database?.message || '---'}</div>
        </div>

        {/* CPU */}
        <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <Cpu size={20} color="#f59e0b" />
            <span style={{ fontWeight: 600 }}>Disk Usage</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#fff' }}>
              {health?.components?.disk?.percent ?? 0}%
            </div>
          </div>
          <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 4, marginTop: 12, overflow: 'hidden' }}>
            <div style={{ width: `${health?.components?.disk?.percent ?? 0}%`, height: '100%', background: '#f59e0b', borderRadius: 4 }} />
          </div>
        </div>

        {/* Memory */}
        <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--card-border)', borderRadius: 12, padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <HardDrive size={20} color="#10b981" />
            <span style={{ fontWeight: 600 }}>Memory Usage</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: '#fff' }}>
              {health?.components?.memory?.percent ?? 0}%
            </div>
          </div>
          <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 4, marginTop: 12, overflow: 'hidden' }}>
            <div style={{ width: `${health?.components?.memory?.percent ?? 0}%`, height: '100%', background: '#10b981', borderRadius: 4 }} />
          </div>
        </div>

      </div>
    </div>
  );
}
