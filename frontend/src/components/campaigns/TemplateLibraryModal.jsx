import React, { useState, useEffect } from 'react';
import { X, Search, Mail, RefreshCw, Check, Calendar, Users, BarChart3, Bookmark, Clock, Trash2 } from 'lucide-react';
import api from '../../services/api';
import toast from 'react-hot-toast';
import { getSavedTemplates, deleteTemplate, getLastEmail } from '../../lib/emailTemplates';

export default function TemplateLibraryModal({ isOpen, onClose, onImport }) {
  const [activeTab, setActiveTab] = useState('past'); // 'past' or 'saved'
  const [campaigns, setCampaigns] = useState([]);
  const [savedTemplates, setSavedTemplates] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null); // { type: 'campaign' | 'template', data: any }
  const [campaignDetails, setCampaignDetails] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  
  const lastEmail = getLastEmail();

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearchQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    if (isOpen) {
      if (activeTab === 'past') {
        fetchCampaigns();
      } else {
        loadSavedTemplates();
      }
    }
  }, [isOpen, activeTab, debouncedSearchQuery]);

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

  const loadSavedTemplates = () => {
    let templates = getSavedTemplates();
    if (debouncedSearchQuery) {
      templates = templates.filter(t => 
        (t.subject && t.subject.toLowerCase().includes(debouncedSearchQuery.toLowerCase())) ||
        (t.name && t.name.toLowerCase().includes(debouncedSearchQuery.toLowerCase()))
      );
    }
    setSavedTemplates(templates);
  };

  const loadCampaignDetails = async (camp) => {
    setSelectedItem({ type: 'campaign', data: camp });
    setLoadingDetails(true);
    setCampaignDetails(null);
    try {
      const res = await api.get('/campaigns/' + camp.campaign_id);
      setCampaignDetails(res.data);
    } catch (e) {
      toast.error('Error loading campaign details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const selectSavedTemplate = (template) => {
    setSelectedItem({ type: 'template', data: template });
  };

  const handleDeleteTemplate = (e, id) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this saved template?')) {
      if (deleteTemplate(id)) {
        toast.success('Template deleted');
        if (selectedItem?.data?.id === id) setSelectedItem(null);
        loadSavedTemplates();
      } else {
        toast.error('Failed to delete template');
      }
    }
  };

  const handleUseForCampaign = () => {
    if (selectedItem?.type === 'campaign') {
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
    } else if (selectedItem?.type === 'template') {
      const template = selectedItem.data;
      onImport({
        subject: template.subject,
        html_body: template.body,
        text_body: template.body
      });
      onClose();
    }
  };

  const handleUseLastEmail = () => {
    if (lastEmail) {
      onImport({
        subject: lastEmail.subject,
        html_body: lastEmail.body,
        text_body: lastEmail.body
      });
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-[#000000bb] flex items-center justify-center p-4 backdrop-blur-sm transition-opacity duration-300">
      <div className="bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl shadow-2xl w-[95vw] h-[95vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-500 ease-out">
        
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--card-border)] bg-[var(--card-bg)]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[var(--brand)]/20 text-[var(--brand)] rounded-lg">
              <Bookmark size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#fff]">Template Library</h2>
              <p className="text-sm text-[var(--text-muted)]">Reuse past campaigns or access your saved templates.</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-[var(--text-muted)] hover:text-[#fff] hover:bg-[var(--bg-hover)] rounded-lg transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* Last Email Banner */}
        {lastEmail && (
          <div className="border-b p-3 px-6 flex items-center justify-between" style={{ backgroundColor: 'var(--brand-bg)', borderColor: 'var(--brand-bg)' }}>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" style={{ color: 'var(--brand)' }} />
              <span className="text-sm font-medium" style={{ color: 'var(--brand-strong)' }}>
                You have an auto-saved draft from <strong>{new Date(lastEmail.updatedAt).toLocaleTimeString()}</strong>.
              </span>
            </div>
            <button 
              onClick={handleUseLastEmail}
              className="text-xs text-[var(--text-primary)] px-3 py-1.5 rounded-lg font-medium transition-colors hover:brightness-110"
              style={{ backgroundColor: 'var(--brand)' }}
            >
              Continue from Last Email
            </button>
          </div>
        )}

        <div className="flex flex-1 overflow-hidden">
          
          <div className="w-[30%] border-r border-[var(--card-border)] flex flex-col bg-[var(--card-bg)]">
            <div className="flex border-b border-[var(--card-border)]">
              <button 
                onClick={() => { setActiveTab('past'); setSelectedItem(null); setSearchQuery(''); }}
                className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'past' ? 'border-[var(--brand)] text-[var(--brand)]' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
              >
                Past Campaigns
              </button>
              <button 
                onClick={() => { setActiveTab('saved'); setSelectedItem(null); setSearchQuery(''); }}
                className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'saved' ? 'border-[var(--brand)] text-[var(--brand)]' : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
              >
                Saved Templates
              </button>
            </div>

            <div className="p-4 border-b border-[var(--card-border)]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" size={18} />
                <input 
                  type="text"
                  placeholder={`Search ${activeTab === 'past' ? 'campaigns' : 'templates'}...`}
                  className="w-full bg-[var(--main-bg)] border border-[var(--card-border)] rounded-lg pl-10 pr-4 py-2 text-sm text-[#fff] focus:outline-none focus:border-[var(--brand)] transition-colors h-11"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
              {activeTab === 'past' ? (
                loading ? (
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
                      onClick={() => loadCampaignDetails(camp)}
                      className={'w-full text-left p-3 rounded-lg border transition-all ' + (selectedItem?.data?.campaign_id === camp.campaign_id ? 'bg-[var(--brand)]/10 border-[var(--brand)]/50' : 'bg-[var(--bg-page)] border-[var(--border)] hover:border-[var(--border-hover)] hover:bg-[var(--bg-surface)]')}
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
                )
              ) : (
                savedTemplates.length === 0 ? (
                  <div className="p-8 text-center text-[var(--text-muted)]">No saved templates yet.</div>
                ) : (
                  savedTemplates.map(template => (
                    <button
                      key={template.id}
                      onClick={() => selectSavedTemplate(template)}
                      className={'w-full text-left p-3 rounded-lg border transition-all relative group ' + (selectedItem?.data?.id === template.id ? 'bg-[var(--brand)]/10 border-[var(--brand)]/50' : 'bg-[var(--bg-page)] border-[var(--border)] hover:border-[var(--border-hover)] hover:bg-[var(--bg-surface)]')}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium text-[var(--text-primary)] truncate pr-6">{template.name || 'Untitled Template'}</span>
                      </div>
                      <div className="text-xs text-[var(--text-muted)] truncate pr-2 mt-1">{template.subject || 'No subject'}</div>
                      <div className="flex items-center gap-4 text-xs text-[var(--text-muted)] mt-2">
                        <span className="flex items-center gap-1"><Calendar size={12} /> {new Date(template.createdAt).toLocaleDateString()}</span>
                      </div>
                      <div 
                        onClick={(e) => handleDeleteTemplate(e, template.id)}
                        className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 hover:text-red-400 text-[var(--text-muted)] transition-opacity p-1"
                      >
                        <Trash2 size={14} />
                      </div>
                    </button>
                  ))
                )
              )}
            </div>
          </div>

          <div className="w-[70%] flex flex-col bg-[var(--bg-page)]">
            {selectedItem ? (
              selectedItem.type === 'campaign' ? (
                loadingDetails ? (
                  <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-muted)]">
                    <RefreshCw className="animate-spin mb-4 text-[var(--brand)]" size={32} />
                    Loading template...
                  </div>
                ) : campaignDetails ? (
                  <div className="flex flex-col h-full">
                    <div className="flex items-center justify-between p-4 border-b border-[var(--border)] bg-[var(--bg-surface)]">
                      <div className="flex items-center gap-2">
                        <span className="px-3 py-1 bg-[var(--brand)]/10 text-[var(--brand)] rounded-full text-xs font-bold uppercase tracking-wider">{campaignDetails.status}</span>
                      </div>
                      <button 
                        onClick={handleUseForCampaign}
                        className="flex items-center gap-2 px-4 py-2 bg-[var(--brand)] hover:bg-[var(--brand)]/90 text-[var(--text-primary)] text-sm font-bold rounded-lg shadow-md transition-colors"
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
                        <div className="w-12 h-12 rounded-full bg-[var(--brand)]/10 flex items-center justify-center text-[var(--brand)] font-bold text-lg shrink-0">
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
                    
                    <div className="flex-1 overflow-auto bg-[var(--bg-surface)] p-6 relative">
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
                // Saved Template View
                <div className="flex flex-col h-full">
                  <div className="flex items-center justify-between p-4 border-b border-[var(--border)] bg-[var(--bg-surface)]">
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 bg-green-500/10 text-green-400 rounded-full text-xs font-bold uppercase tracking-wider">SAVED TEMPLATE</span>
                    </div>
                    <button 
                      onClick={handleUseForCampaign}
                      className="flex items-center gap-2 px-4 py-2 bg-[var(--brand)] hover:bg-[var(--brand)]/90 text-[var(--text-primary)] text-sm font-bold rounded-lg shadow-md transition-colors"
                    >
                      <Check size={18} /> Use Template
                    </button>
                  </div>
                  
                  <div className="p-6 border-b border-[var(--border)] bg-[var(--bg-page)]">
                    <div className="text-sm text-[var(--text-muted)] mb-2 font-medium">{selectedItem.data.name || 'Untitled Template'}</div>
                    <h1 className="text-2xl font-semibold text-[var(--text-primary)] mb-2">
                      {selectedItem.data.subject || 'No Subject'}
                    </h1>
                  </div>
                  
                  <div className="flex-1 overflow-auto bg-[var(--bg-surface)] p-6 relative">
                    {selectedItem.data.body ? (
                      <iframe 
                        title="Template Body"
                        srcDoc={selectedItem.data.body}
                        className="w-full h-full border-none"
                        sandbox="allow-same-origin allow-popups"
                      />
                    ) : (
                      <div className="text-center text-[var(--text-muted)] mt-10">No content available for this template.</div>
                    )}
                  </div>
                </div>
              )
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-muted)] bg-[var(--bg-surface)]">
                <Bookmark size={64} className="opacity-20 mb-4" />
                <p className="text-lg">Select a template to view it</p>
                <p className="text-sm mt-2 max-w-md text-center">Use templates to quickly start new campaigns without rewriting your emails.</p>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
