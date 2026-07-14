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
    return <div className="p-6">Loading sessions...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Active Sessions</h2>
      {error && <div className="text-red-500 mb-4">{error}</div>}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <ul className="divide-y divide-gray-200">
          {sessions.map((session) => (
            <li key={session.id} className="p-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {session.browser || 'Unknown Device'} - {session.ip_address}
                </p>
                <p className="text-sm text-gray-500">
                  Started: {new Date(session.created_at).toLocaleString()}
                </p>
                {session.is_current && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Current Session
                  </span>
                )}
              </div>
              {!session.is_current && (
                <button
                  onClick={() => handleLogout(session.id)}
                  className="ml-4 inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  Logout
                </button>
              )}
            </li>
          ))}
          {sessions.length === 0 && (
            <li className="p-4 text-gray-500">No active sessions found.</li>
          )}
        </ul>
      </div>
    </div>
  );
};

export default SessionManagement;
