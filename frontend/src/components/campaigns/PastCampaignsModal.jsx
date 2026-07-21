import React, { useState, useEffect } from 'react';
import { X, Search, Mail, RefreshCw, Check, Calendar, Users, BarChart3 } from 'lucide-react';
import api from '../../services/api';
import toast from 'react-hot-toast';

export default function PastCampaignsModal({ isOpen, onClose, onImport }) {
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState(null);
  const [campaignDetails, setCampaignDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearchQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    if (isOpen) {
      fetchCampaigns();
    }
  }, [isOpen, debouncedSearchQuery]);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: '50' });
      if (debouncedSearchQuery) params.append('search', debouncedSearchQuery);
      
      const res = await api.get('/campaigns?' + params.toString());
      setCampaigns(res.data.items || []);
    } catch (e) {
      console.error('Failed to fetch campaigns', e);
      toast.error('Could not fetch past campaigns');
    } finally {
      setLoading(false);
    }
  };

  const loadCampaignDetails = async (id) => {
    setSelectedCampaignId(id);
    setLoadingDetails(true);
    setCampaignDetails(null);
    try {
      const res = await api.get('/campaigns/' + id);
      setCampaignDetails(res.data);
    } catch (e) {
      toast.error('Error loading campaign details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleUseForCampaign = () => {
    if (campaignDetails && campaignDetails.templates && campaignDetails.templates.length > 0) {
      const template = campaignDetails.templates[0];
      onImport({
        subject: template.subject,
        html_body: template.body,
        text_body: template.body
      });
      onClose();
    } else {
      toast.error('This campaign does not have a saved template to reuse.');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-[var(--bg-page)] border border-[var(--border)] rounded-xl shadow-2xl w-[95vw] h-[95vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-surface)]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[var(--accent)]/20 text-[var(--accent)] rounded-lg">
              <Mail size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[var(--text-primary)]">Past Campaigns Library</h2>
              <p className="text-sm text-[var(--text-muted)]">Browse and reuse your previously sent campaigns lightning fast.</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-page)] rounded-lg transition-colors">
            <X size={24} />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          
          <div className="w-[30%] border-r border-[var(--border)] flex flex-col bg-[var(--bg-surface)]/50">
            <div className="p-4 border-b border-[var(--border)]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" size={18} />
                <input 
                  type="text"
                  placeholder="Search past campaigns..."
                  className="w-full bg-[var(--bg-page)] border border-[var(--border)] rounded-lg pl-10 pr-4 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)] transition-colors"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
              {loading ? (
                <div className="p-8 text-center text-[var(--text-muted)] flex flex-col items-center">
                  <RefreshCw className="animate-spin mb-4" size={24} />
                  Loading campaigns...
                </div>
              ) : campaigns.length === 0 ? (
                <div className="p-8 text-center text-[var(--text-muted)]">No campaigns found.</div>
              ) : (
                campaigns.map(camp => (
                  <button
                    key={camp.campaign_id}
                    onClick={() => loadCampaignDetails(camp.campaign_id)}
                    className={'w-full text-left p-3 rounded-lg border transition-all ' + (selectedCampaignId === camp.campaign_id ? 'bg-[var(--accent)]/10 border-[var(--accent)]/50' : 'bg-[var(--bg-page)] border-[var(--border)] hover:border-[var(--border-hover)] hover:bg-[var(--bg-surface)]')}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-medium text-[var(--text-primary)] truncate pr-2">{camp.name}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-[var(--text-muted)] mt-2">
                      <span className="flex items-center gap-1"><Calendar size={12} /> {new Date(camp.created_at).toLocaleDateString()}</span>
                      <span className="flex items-center gap-1"><Users size={12} /> {camp.stats?.total || 0}</span>
                      <span className="flex items-center gap-1"><BarChart3 size={12} /> {camp.stats?.progress_percent || 0}%</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="w-[70%] flex flex-col bg-[var(--bg-page)]">
            {selectedCampaignId ? (
              loadingDetails ? (
                <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-muted)]">
                  <RefreshCw className="animate-spin mb-4 text-[var(--accent)]" size={32} />
                  Loading template...
                </div>
              ) : campaignDetails ? (
                <div className="flex flex-col h-full">
                  <div className="flex items-center justify-between p-4 border-b border-[var(--border)] bg-[var(--bg-surface)]">
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 bg-[var(--accent)]/10 text-[var(--accent)] rounded-full text-xs font-bold uppercase tracking-wider">{campaignDetails.status}</span>
                    </div>
                    <button 
                      onClick={handleUseForCampaign}
                      className="flex items-center gap-2 px-4 py-2 bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white text-sm font-bold rounded-lg shadow-md transition-colors"
                    >
                      <Check size={18} /> Reuse This Template
                    </button>
                  </div>
                  
                  <div className="p-6 border-b border-[var(--border)] bg-[var(--bg-page)]">
                    <h1 className="text-2xl font-semibold text-[var(--text-primary)] mb-4">
                      {campaignDetails.templates && campaignDetails.templates.length > 0 
                        ? campaignDetails.templates[0].subject 
                        : 'No Subject'}
                    </h1>
                    <div className="flex gap-4 text-sm">
                      <div className="w-12 h-12 rounded-full bg-[var(--accent)]/10 flex items-center justify-center text-[var(--accent)] font-bold text-lg shrink-0">
                        {campaignDetails.from_name ? campaignDetails.from_name.charAt(0).toUpperCase() : 'T'}
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-start">
                          <div>
                            <span className="font-medium text-[var(--text-primary)]">{campaignDetails.from_name || 'System'}</span>
                            <div className="text-[var(--text-muted)] mt-0.5">From: {campaignDetails.from_email || 'default@talentops.ai'}</div>
                          </div>
                          <span className="text-[var(--text-muted)]">{new Date(campaignDetails.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex-1 overflow-auto bg-white p-6 relative">
                    {/* Note: Iframe content background kept white intentionally for email template rendering accuracy */}
                    {campaignDetails.templates && campaignDetails.templates.length > 0 ? (
                      <iframe 
                        title="Email Body"
                        srcDoc={campaignDetails.templates[0].body}
                        className="w-full h-full border-none"
                        sandbox="allow-same-origin allow-popups"
                      />
                    ) : (
                      <div className="text-center text-[var(--text-muted)] mt-10">No template content available for this campaign.</div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-[var(--text-muted)]">Failed to load</div>
              )
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-muted)] bg-[var(--bg-surface)]">
                <Mail size={64} className="opacity-20 mb-4" />
                <p className="text-lg">Select a campaign to view its template</p>
                <p className="text-sm">Templates are loaded instantly from the database.</p>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
