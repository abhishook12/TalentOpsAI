import React, { useEffect, useState } from 'react';
import api from '../../services/api';
const SessionManagement = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/auth/sessions');
      setSessions(data.sessions || []);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleLogout = async (sessionId) => {
    try {
      await api.delete(`/auth/sessions/${sessionId}`);
      fetchSessions();
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to logout session');
    }
  };

  if (loading) {
    return <div style={{ display: 'grid', placeItems: 'center', minHeight: '60vh', color: '#a1a1aa' }}><i className="ti ti-loader animate-spin" style={{ fontSize: 24, color: '#3b82f6', marginBottom: 12 }} />Loading sessions...</div>;
  }

  return (
    <div style={{ maxWidth: '600px', margin: '40px auto', padding: '0 20px' }}>
      <h2 style={{ fontSize: '24px', fontWeight: '600', color: 'var(--text-inverse)', marginBottom: '24px' }}>Active Sessions</h2>
      {error && <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', padding: '12px 16px', borderRadius: '8px', marginBottom: '20px', fontSize: '14px' }}>{error}</div>}
      
      <div style={{ background: '#18181b', borderRadius: '12px', border: '1px solid #27272a', overflow: 'hidden' }}>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {sessions.map((session, index) => (
            <li key={session.id} style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              padding: '20px', 
              borderBottom: index < sessions.length - 1 ? '1px solid #27272a' : 'none' 
            }}>
              <div>
                <p style={{ margin: '0 0 4px 0', color: 'var(--text-inverse)', fontSize: '15px', fontWeight: '500' }}>
                  {session.browser || 'Unknown Device'} - {session.ip_address}
                </p>
                <p style={{ margin: '0 0 8px 0', color: '#a1a1aa', fontSize: '13px' }}>
                  Started: {new Date(session.created_at).toLocaleString()}
                </p>
                {session.is_current && (
                  <span style={{ 
                    display: 'inline-block', 
                    background: 'rgba(34, 197, 94, 0.1)', 
                    color: '#22c55e', 
                    padding: '4px 8px', 
                    borderRadius: '4px', 
                    fontSize: '12px', 
                    fontWeight: '600' 
                  }}>
                    Current Session
                  </span>
                )}
              </div>
              {!session.is_current && (
                <button
                  onClick={() => handleLogout(session.id)}
                  style={{ 
                    background: 'rgba(239, 68, 68, 0.1)', 
                    color: '#ef4444', 
                    border: 'none', 
                    padding: '8px 16px', 
                    borderRadius: '6px', 
                    cursor: 'pointer', 
                    fontSize: '13px', 
                    fontWeight: '500',
                    transition: 'all 0.2s'
                  }}
                  onMouseOver={(e) => e.target.style.background = 'rgba(239, 68, 68, 0.2)'}
                  onMouseOut={(e) => e.target.style.background = 'rgba(239, 68, 68, 0.1)'}
                >
                  Logout
                </button>
              )}
            </li>
          ))}
          {sessions.length === 0 && (
            <li style={{ padding: '32px', textAlign: 'center', color: '#a1a1aa', fontSize: '14px' }}>No active sessions found.</li>
          )}
        </ul>
      </div>
    </div>
  );
};

export default SessionManagement;
