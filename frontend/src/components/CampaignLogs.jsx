import React, { useState, useEffect } from 'react';
import { FileText, Loader2 } from 'lucide-react';
import api from '../services/api';

export default function CampaignLogs({ campaignId }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  // In a real app we'd fetch from a /campaigns/{id}/logs endpoint. 
  // For now, we'll just show the UI structure, assuming real-time logs are in CampaignProgress.
  
  useEffect(() => {
    // Placeholder for actual fetch
    setLoading(false);
  }, [campaignId]);

  if (loading) {
    return <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-[var(--accent)]" /></div>;
  }

  return (
    <div className="bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--card-border)] bg-[var(--card-bg)] flex items-center justify-between">
        <h3 className="font-medium flex items-center gap-2 text-sm">
          <FileText className="w-4 h-4 text-[var(--accent)]" /> 
          Historical Delivery Logs
        </h3>
      </div>
      <div className="p-8 text-center text-[var(--text-muted)] text-sm">
        Historical logs will appear here after the campaign completes.
      </div>
    </div>
  );
}
