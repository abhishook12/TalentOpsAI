import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle, XCircle, Clock, Loader2, AlertTriangle, ExternalLink } from 'lucide-react';
import api, { API, getStoredToken } from '../services/api';

export default function CampaignProgress({ campaignId, onStatusChange }) {
  const [data, setData] = useState({
    status: 'draft',
    total: 0,
    sent: 0,
    failed: 0,
    pending: 0,
    has_auth_error: false
  });
  const [isConnecting, setIsConnecting] = useState(true);

  useEffect(() => {
    if (!campaignId) return;

    const token = getStoredToken();
    if (!token) {
      setIsConnecting(false);
      return;
    }
    const eventSource = new EventSource(`${API}/campaigns/${campaignId}/progress?token=${encodeURIComponent(token)}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setData(prev => ({ ...prev, ...data }));
        setIsConnecting(false);
        if (onStatusChange) onStatusChange(data.status);
        
        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
          eventSource.close();
        }
      } catch (e) {
        console.error("Failed to parse campaign status stream", e);
      }
    };

    eventSource.onerror = (e) => {
      console.error("SSE stream error", e);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [campaignId, onStatusChange]);

  const handleReconnect = () => {
    window.location.href = '/settings?tab=api';
  };

  if (data.status === 'draft') {
    return null; // For drafts, the Campaigns.jsx already shows the Send button.
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl p-6">
        
        {data.has_auth_error ? (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
            <h3 className="text-lg font-bold text-[var(--text-primary)] mb-2">Authentication Failed</h3>
            <p className="text-[var(--text-muted)] mb-6 max-w-md">
              Your email account needs to be reconnected. We could not authenticate with your provider to send these emails.
            </p>
            <button 
              onClick={handleReconnect}
              className="px-6 py-2 bg-[var(--text-primary)] text-[var(--main-bg)] rounded-lg font-medium flex items-center gap-2 hover:opacity-90 transition-opacity"
            >
              Reconnect Account <ExternalLink className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              {data.status === 'active' ? (
                <div className="flex items-center gap-3">
                  <Loader2 className="w-8 h-8 animate-spin text-[var(--brand)]" />
                  <div>
                    <h3 className="font-semibold text-lg">Sending...</h3>
                    <p className="text-sm text-[var(--text-muted)]">Your campaign is actively delivering emails.</p>
                  </div>
                </div>
              ) : data.status === 'completed' ? (
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-8 h-8 text-green-500" />
                  <div>
                    <h3 className="font-semibold text-lg text-green-500">Completed</h3>
                    <p className="text-sm text-[var(--text-muted)]">All recipients have been processed.</p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <Clock className="w-8 h-8 text-yellow-500" />
                  <div>
                    <h3 className="font-semibold text-lg capitalize">{data.status}</h3>
                    <p className="text-sm text-[var(--text-muted)]">Campaign processing is paused or stopped.</p>
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-8">
              <div className="flex flex-col items-center">
                <span className="text-3xl font-bold text-[var(--text-primary)]">{data.sent}</span>
                <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold mt-1">Sent</span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-3xl font-bold text-[var(--text-primary)]">{data.pending}</span>
                <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold mt-1">Pending</span>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-3xl font-bold text-[var(--danger)]">{data.failed}</span>
                <span className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold mt-1">Failed</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
