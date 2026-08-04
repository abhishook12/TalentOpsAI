import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { 
  Send, ArrowLeft, Plus, Mail, Activity, AlertCircle, FileText, 
  CheckCircle2, Loader2, ChevronRight, Play, Eye, Download, Search,
  Pause, MoreHorizontal, Copy, Trash2, Archive, Save, Clock, RefreshCw
} from 'lucide-react';
import toast from 'react-hot-toast';
import api, { API } from '../services/api';

import BridgeStatus from '../components/BridgeStatus';
import RichTextComposer from '../components/RichTextComposer';
import SignatureManager from '../components/SignatureManager';
import EmailPreview from '../components/EmailPreview';
import DragDropRecipientBuilder from '../components/campaigns/DragDropRecipientBuilder';
import CampaignProgress from '../components/CampaignProgress';
import CustomSelect from '../components/ui/CustomSelect';
import CampaignLogs from '../components/CampaignLogs';
import TemplateLibraryModal from '../components/campaigns/TemplateLibraryModal';
import CampaignReuseWorkflow from '../components/campaigns/CampaignReuseWorkflow';
import { setLastEmail, saveTemplate } from '../lib/emailTemplates';

const STEPS = {
  RECIPIENTS: 1,
  COMPOSE: 2,
  PREVIEW: 3,
  SEND: 4
};

export default function Campaigns() {
  const [view, setView] = useState('list'); // 'list' | 'wizard'
  
  // List State
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showTest, setShowTest] = useState(false);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [sortBy, setSortBy] = useState('newest'); // newest, oldest, name, progress, failures
  const [selectedIds, setSelectedIds] = useState(new Set());
  
  const searchInputRef = useRef(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearchQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
  // Wizard State
  const [currentStep, setCurrentStep] = useState(STEPS.RECIPIENTS);
  const [activeCampaignId, setActiveCampaignId] = useState(null);
  const [campaignName, setCampaignName] = useState('New Campaign');
  
  // Compose State
  const [fromEmail, setFromEmail] = useState(() => {
    return localStorage.getItem('talentops_from_email') || 'Outlook Default';
  });
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [signatureId, setSignatureId] = useState(null);
  
  // Recipient State
  const [validatedRecipients, setValidatedRecipients] = useState({ recipients: [], valid_count: 0 });
  
  // Pre-flight State
  const [preflightData, setPreflightData] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [bridgeHealthy, setBridgeHealthy] = useState(false);
  
  // Templates & Modals
  const [showTemplateLibrary, setShowTemplateLibrary] = useState(false);
  const [showOutlookImport, setShowOutlookImport] = useState(false);
  const [pendingImportEmail, setPendingImportEmail] = useState(null);

  // Auto-save logic
  const [lastSaved, setLastSaved] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const savePromiseRef = useRef(null);

  useEffect(() => {
    if (view === 'wizard' && activeCampaignId) {
      const timer = setTimeout(() => {
        saveDraft();
        if (subject || body) {
          setLastEmail(subject, body);
        }
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [subject, body, signatureId, view, activeCampaignId, currentStep, campaignName]);

  // Load campaigns with auto-refresh only when focused
  const { data: queryData, isLoading: loading, error: queryError, refetch: refetchCampaigns } = useQuery({
    queryKey: ['campaigns', debouncedSearchQuery, statusFilter, showTest, page, limit],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      });
      if (debouncedSearchQuery) params.append('search', debouncedSearchQuery);
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
      if (!showTest) params.append('is_test', 'false');
      
      const res = await api.get(`/campaigns?${params.toString()}`);
      return res.data;
    },
    enabled: view === 'list',
    refetchInterval: view === 'list' ? 5000 : false,
    refetchOnWindowFocus: true, // Only poll when tab is in foreground
    retry: 1
  });

  const rawCampaigns = useMemo(() => {
    return Array.isArray(queryData) ? queryData : queryData?.items || [];
  }, [queryData]);

  const totalPages = useMemo(() => {
    return queryData?.pages || 1;
  }, [queryData]);

  // Derived Sorting
  const sortedCampaigns = useMemo(() => {
    let sorted = [...rawCampaigns];
    if (sortBy === 'newest') sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    if (sortBy === 'oldest') sorted.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    if (sortBy === 'name') sorted.sort((a, b) => a.name.localeCompare(b.name));
    if (sortBy === 'progress') sorted.sort((a, b) => (b.stats?.progress_percent || 0) - (a.stats?.progress_percent || 0));
    if (sortBy === 'failures') sorted.sort((a, b) => (b.stats?.failed || 0) - (a.stats?.failed || 0));
    return sorted;
  }, [rawCampaigns, sortBy]);

  // KPI Strip Calcs (based on loaded data)
  const kpis = useMemo(() => {
    let active = 0, sent = 0, failures = 0;
    const counts = { all: 0, draft: 0, active: 0, paused: 0, completed: 0, failed: 0 };
    
    rawCampaigns.forEach(c => {
      if (c.status === 'active') active++;
      sent += (c.stats?.sent || 0);
      failures += (c.stats?.failed || 0);
      
      counts.all++;
      if (counts[c.status] !== undefined) counts[c.status]++;
    });
    
    return {
      total: rawCampaigns.length,
      active,
      sent,
      failures,
      counts
    };
  }, [rawCampaigns]);

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in an input or textarea
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
      
      if (e.key === 'n') {
        e.preventDefault();
        startNewCampaign();
      } else if (e.key === '/') {
        e.preventDefault();
        searchInputRef.current?.focus();
      } else if (e.key === 'Escape') {
        if (selectedIds.size > 0) setSelectedIds(new Set());
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedIds]);

  const toggleSelection = (id) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const toggleAll = () => {
    if (selectedIds.size === sortedCampaigns.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sortedCampaigns.map(c => c.campaign_id)));
    }
  };

  const handleBulkAction = async (action) => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Are you sure you want to ${action} ${selectedIds.size} campaigns?`)) return;
    
    const promises = Array.from(selectedIds).map(id => {
      if (action === 'delete') return api.delete(`/campaigns/${id}`);
      if (action === 'archive') return api.put(`/campaigns/${id}/archive`);
      if (action === 'duplicate') return api.post(`/campaigns/${id}/duplicate`);
      return Promise.resolve();
    });

    try {
      await Promise.all(promises);
      toast.success(`Bulk ${action} successful`);
      setSelectedIds(new Set());
      refetchCampaigns();
    } catch (e) {
      toast.error(`Some actions failed during bulk ${action}`);
    }
  };

  const exportCSV = () => {
    const headers = ['ID', 'Name', 'Status', 'Created', 'Sent', 'Failed', 'Progress'];
    const rows = sortedCampaigns.map(c => [
      c.campaign_id,
      `"${c.name}"`,
      c.status,
      new Date(c.created_at).toLocaleDateString(),
      c.stats?.sent || 0,
      c.stats?.failed || 0,
      `${c.stats?.progress_percent || 0}%`
    ]);
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `campaigns_export_${new Date().getTime()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const startNewCampaign = () => {
    setActiveCampaignId(null);
    setCampaignName('New Campaign');
    setSubject('');
    setBody('');
    setSignatureId(null);
    setValidatedRecipients({ recipients: [], valid_count: 0 });
    setCurrentStep(STEPS.RECIPIENTS);
    setView('wizard');
  };

  const handleTemplateImport = (template) => {
    setSubject(template.subject);
    setBody(template.html_body || template.text_body);
    if (view === 'list') {
      startNewCampaign();
      setTimeout(() => {
        setCurrentStep(STEPS.COMPOSE);
      }, 100);
    } else {
      setCurrentStep(STEPS.COMPOSE);
    }
  };

  const handleSaveAsTemplate = () => {
    if (!subject || !body) {
      toast.error("Subject and body cannot be empty");
      return;
    }
    saveTemplate({
      name: campaignName + ' Template',
      subject: subject,
      body: body
    });
    toast.success("Saved to Template Library");
  };

  const saveDraft = async () => {
    if (savePromiseRef.current) return savePromiseRef.current;

    const doSave = async () => {
      setIsSaving(true);
      try {
        let cid = activeCampaignId;
        if (cid) {
          await api.put(`/campaigns/${cid}`, {
            name: campaignName,
            from_email: fromEmail,
            signature_id: signatureId
          });
        } else {
          const res = await api.post('/campaigns', {
            name: campaignName,
            from_email: fromEmail,
            status: 'draft',
            signature_id: signatureId
          });
          cid = res.data.campaign_id;
          setActiveCampaignId(cid);
        }
        
        if (subject || body) {
          await api.post(`/campaigns/${cid}/templates`, {
            name: subject || 'Draft',
            subject: subject || '',
            body: body || ''
          });
        }
        
        setLastSaved(new Date());
        return cid;
      } catch (e) {
        console.error("Draft save failed", e);
        return null;
      } finally {
        setIsSaving(false);
        savePromiseRef.current = null;
      }
    };

    savePromiseRef.current = doSave();
    return savePromiseRef.current;
  };

  const deleteCampaign = async (id) => {
    if (!window.confirm("Are you sure you want to delete this campaign?")) return;
    try {
      await api.delete(`/campaigns/${id}`);
      toast.success("Campaign deleted");
      refetchCampaigns();
    } catch (e) {
      toast.error("Failed to delete campaign");
    }
  };

  const archiveCampaign = async (id) => {
    try {
      await api.put(`/campaigns/${id}/archive`);
      toast.success("Campaign archived");
      refetchCampaigns();
    } catch (e) {
      toast.error("Failed to archive campaign");
    }
  };

  const toggleCampaignStatus = async (id, currentStatus) => {
    try {
      if (currentStatus === 'active') {
        await api.post(`/campaigns/${id}/control`, { action: 'pause' });
        toast.success("Campaign paused");
      } else if (currentStatus === 'paused') {
        await api.post(`/campaigns/${id}/control`, { action: 'resume' });
        toast.success("Campaign resumed");
      }
      refetchCampaigns();
    } catch (e) {
      toast.error("Failed to change status");
    }
  };

  const duplicateCampaign = async (id) => {
    try {
      await api.post(`/campaigns/${id}/duplicate`);
      toast.success("Campaign duplicated");
      refetchCampaigns();
    } catch (e) {
      toast.error("Failed to duplicate campaign");
    }
  };

  const loadCampaign = async (id) => {
    try {
      const res = await api.get(`/campaigns/${id}?include_recruiters=true`);
      const campaign = res.data;
      
      setActiveCampaignId(campaign.campaign_id);
      setCampaignName(campaign.name);
      setFromEmail(campaign.from_email || 'Outlook Default');
      setSignatureId(campaign.signature_id);
      
      if (campaign.templates && campaign.templates.length > 0) {
        const t = campaign.templates[0];
        setSubject(t.subject || '');
        setBody(t.body || '');
      } else {
        setSubject('');
        setBody('');
      }
      
      if (campaign.campaign_recruiters) {
        const loadedRecipients = campaign.campaign_recruiters.map(cr => ({
          email: cr.recruiter_email,
          name: cr.recruiter_name || '',
          recruiter_id: cr.recruiter_id,
          status: 'valid'
        }));
        setValidatedRecipients({
          recipients: loadedRecipients,
          valid_count: loadedRecipients.length,
          total: loadedRecipients.length
        });
      }
      
      if (campaign.status === 'draft') {
        setCurrentStep(STEPS.RECIPIENTS);
      } else {
        setCurrentStep(STEPS.SEND);
      }
      setView('wizard');
      
    } catch (e) {
      toast.error("Failed to load campaign details");
    }
  };

  const runPreflight = async (currentId) => {
    setIsValidating(true);
    let cid = currentId || activeCampaignId;
    if (!cid) {
      try {
        const res = await api.post('/campaigns', {
          name: campaignName,
          from_email: fromEmail,
          status: 'draft',
          signature_id: signatureId
        });
        cid = res.data.campaign_id;
        setActiveCampaignId(cid);
      } catch (e) {
        toast.error("Failed to create campaign draft");
        setIsValidating(false);
        return;
      }
    }
    
    // Wait for any pending auto-saves to finish to prevent DB transaction deadlocks
    if (savePromiseRef.current) {
      try {
        await savePromiseRef.current;
      } catch (err) {
        // ignore auto-save errors here
      }
    }

    try {
      const validRecipients = validatedRecipients.recipients.filter(r => r.status === 'valid');
      const res = await api.post(`/campaigns/${cid}/prepare-preview`, {
        name: campaignName,
        from_email: fromEmail,
        signature_id: signatureId,
        subject: subject || '',
        body: body || '',
        recipients: validRecipients
      });
      setPreflightData(res.data);
      setLastSaved(new Date());
    } catch (e) {
      console.error("Validation failed:", e);
      toast.error("Validation failed");
      setPreflightData({
        ready: false,
        errors: [{ code: 'API_ERROR', message: e.response?.data?.detail || "Server error during validation" }]
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleNextStep = async () => {
    if (currentStep === STEPS.RECIPIENTS) {
      setCurrentStep(STEPS.COMPOSE);
    } 
    else if (currentStep === STEPS.COMPOSE) {
      setCurrentStep(STEPS.PREVIEW);
      setPreflightData(null);
      (async () => {
        runPreflight(activeCampaignId);
      })();
    }
    else if (currentStep === STEPS.PREVIEW) {
      if (!preflightData?.ready) return;
      startCampaign();
    }
  };

  const startCampaign = async () => {
    try {
      await api.post(`/campaigns/${activeCampaignId}/start`);
      setCurrentStep(STEPS.SEND);
      toast.success("Campaign engine started successfully!");
    } catch (e) {
      toast.error(api.getErrorMessage?.(e) || "Failed to start campaign");
    }
  };

  const renderList = () => {
    if (queryError?.response?.status === 401 || queryError?.response?.status === 403) {
      return (
        <div className="h-full flex flex-col justify-center items-center">
          <div className="bg-red-500/10 border border-red-500/30 p-8 rounded-xl max-w-md text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-red-400 mb-2">Authentication Error</h2>
            <p className="text-[var(--text-secondary)] mb-6">Your session has expired or you do not have permission to view campaigns.</p>
            <div className="flex gap-4 justify-center">
              <button onClick={() => window.location.href = '/login'} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">Sign In</button>
              <button onClick={() => refetchCampaigns()} className="px-4 py-2 border border-[var(--border)] rounded-lg hover:bg-[var(--bg-surface)]">Retry</button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="h-full flex flex-col overflow-hidden relative">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
          <div>
            <h1 className="text-[28px] font-bold text-white tracking-tight">Campaigns</h1>
            <p className="text-sm text-[var(--text-secondary)] mt-1">Manage outbound email campaigns</p>
          </div>
          <div className="flex items-center gap-3 mt-4 sm:mt-0">
            <button onClick={() => refetchCampaigns()} className="px-3 py-2 text-sm font-medium flex items-center gap-2 hover:bg-white/5 rounded-lg transition-colors text-white">
              <RefreshCw size={16} /> Refresh
            </button>
            <button onClick={() => setShowTemplateLibrary(true)} className="px-3 py-2 text-sm font-medium flex items-center gap-2 hover:bg-white/5 rounded-lg transition-colors text-white">
              <Clock size={16} /> Use last email
            </button>
            <button 
              onClick={() => setShowTemplateLibrary(true)}
              className="px-4 py-2 border rounded-lg text-sm font-medium flex items-center gap-2 transition-colors bg-transparent text-white border-white/20 hover:bg-white/10"
            >
              <FileText size={16} /> Reuse email
            </button>
            <button 
              onClick={startNewCampaign}
              className="bg-white text-black px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 hover:bg-gray-200 transition-colors shadow-sm"
            >
              <Plus size={16} /> New Campaign
            </button>
          </div>
        </div>
        
        {/* Bridge Status dedicated row */}
        <div className="mb-6">
          <BridgeStatus onStatusChange={setBridgeHealthy} />
        </div>

        {/* KPI Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6 shrink-0">
          <div className="bg-transparent border border-white/10 rounded-xl p-5 shadow-sm">
            <div className="text-[11px] uppercase font-bold text-[var(--text-muted)] tracking-widest mb-2">Campaigns</div>
            <div className="text-3xl font-bold text-white leading-tight">{kpis.total}</div>
            <div className="text-[13px] text-[var(--text-muted)] mt-1 font-medium">on this page</div>
          </div>
          <div className="bg-transparent border border-white/10 rounded-xl p-5 shadow-sm">
            <div className="text-[11px] uppercase font-bold text-[var(--text-muted)] tracking-widest mb-2">Active</div>
            <div className="text-3xl font-bold text-white leading-tight">{kpis.active}</div>
            <div className="text-[13px] text-[var(--text-muted)] mt-1 font-medium">currently sending</div>
          </div>
          <div className="bg-transparent border border-white/10 rounded-xl p-5 shadow-sm">
            <div className="text-[11px] uppercase font-bold text-[var(--text-muted)] tracking-widest mb-2">Emails Sent</div>
            <div className="text-3xl font-bold text-white leading-tight">{kpis.sent}</div>
            <div className="text-[13px] text-[var(--text-muted)] mt-1 font-medium">across listed campaigns</div>
          </div>
          <div className="bg-transparent border border-red-500/40 rounded-xl p-5 shadow-sm">
            <div className="text-[11px] uppercase font-bold text-[var(--text-muted)] tracking-widest mb-2">Failures</div>
            <div className="text-3xl font-bold text-red-400 leading-tight">{kpis.failures}</div>
            <div className="text-[13px] text-[var(--text-muted)] mt-1 font-medium">need attention</div>
          </div>
        </div>

        {/* Toolbar Card */}
        <div className="bg-[#121212] border border-white/10 rounded-2xl p-2.5 mb-6 shrink-0 shadow-sm flex flex-col sm:flex-row gap-4 items-center justify-between">
          <div className="flex items-center w-full sm:w-auto overflow-x-auto custom-scrollbar gap-1 hide-scrollbar bg-black p-1 rounded-xl">
            {['all', 'active', 'draft', 'paused', 'completed', 'failed'].map(status => (
              <button
                key={status}
                onClick={() => { setStatusFilter(status); setPage(1); }}
                className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all whitespace-nowrap flex items-center gap-2 ${
                  statusFilter === status 
                    ? 'bg-white text-black shadow-sm' 
                    : 'text-white hover:bg-white/10'
                }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
                <span className={`text-[11px] font-bold ${
                  statusFilter === status ? 'text-gray-500' : 'text-gray-500'
                }`}>
                  {kpis.counts[status] || 0}
                </span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4 w-full sm:w-auto pl-2 sm:pl-0 pt-3 sm:pt-0">
            <div className="relative w-56 shrink-0">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
              <input 
                ref={searchInputRef}
                type="text" 
                placeholder="Search campaigns..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#1a1a1a] border border-white/5 rounded-xl pl-9 pr-9 py-2.5 text-sm text-white focus:border-white/20 focus:outline-none transition-colors placeholder:text-gray-500"
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center justify-center w-5 h-5 rounded border border-white/10 bg-[#222] text-gray-400 text-[10px] font-bold">/</div>
            </div>
            
            <select 
              value={sortBy} 
              onChange={e => setSortBy(e.target.value)}
              className="bg-[#1a1a1a] border border-white/5 rounded-xl px-4 py-2.5 text-sm font-medium text-white outline-none focus:border-white/20"
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="name">Name A-Z</option>
              <option value="progress">Progress %</option>
              <option value="failures">Most Failures</option>
            </select>

            <select 
              value={limit} 
              onChange={e => { setLimit(Number(e.target.value)); setPage(1); }}
              className="bg-[#1a1a1a] border border-white/5 rounded-xl px-4 py-2.5 text-sm font-medium text-white outline-none focus:border-white/20"
            >
              <option value={10}>10 / page</option>
              <option value={20}>20 / page</option>
              <option value={50}>50 / page</option>
            </select>

            <button onClick={exportCSV} className="flex items-center gap-2 px-4 py-2.5 bg-transparent border border-white/10 rounded-xl text-sm font-medium text-white hover:bg-white/5 transition-colors">
              <Download size={16} /> Export
            </button>

            <label className="flex items-center gap-2 text-sm text-white font-medium cursor-pointer ml-2">
              <div className={`w-10 h-5 rounded-full relative transition-colors ${showTest ? 'bg-white' : 'bg-[#333]'}`}>
                <div className={`absolute top-0.5 w-4 h-4 rounded-full transition-transform ${showTest ? 'bg-black left-5.5 translate-x-5' : 'bg-white left-0.5'}`}></div>
              </div>
              <input type="checkbox" checked={showTest} onChange={(e) => { setShowTest(e.target.checked); setPage(1); }} className="hidden" />
              Test
            </label>
          </div>
        </div>

        {/* Sticky Bulk Action Bar */}
        <AnimatePresence>
          {selectedIds.size > 0 && (
            <motion.div 
              initial={{ y: 20, opacity: 0 }} 
              animate={{ y: 0, opacity: 1 }} 
              exit={{ y: 20, opacity: 0 }}
              className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl shadow-2xl z-50 flex items-center p-2 px-4 gap-4"
            >
              <div className="text-sm font-bold text-white bg-[var(--accent)]/20 px-3 py-1 rounded-lg">
                {selectedIds.size} Selected
              </div>
              <div className="w-[1px] h-6 bg-[var(--card-border)]"></div>
              <button onClick={() => handleBulkAction('duplicate')} className="text-sm font-medium text-[var(--text-secondary)] hover:text-white flex items-center gap-1.5"><Copy size={14}/> Duplicate</button>
              <button onClick={() => handleBulkAction('archive')} className="text-sm font-medium text-[var(--text-secondary)] hover:text-yellow-400 flex items-center gap-1.5"><Archive size={14}/> Archive</button>
              <button onClick={() => handleBulkAction('delete')} className="text-sm font-medium text-red-400 hover:text-red-300 flex items-center gap-1.5"><Trash2 size={14}/> Delete</button>
              <div className="w-[1px] h-6 bg-[var(--card-border)]"></div>
              <button onClick={() => setSelectedIds(new Set())} className="text-sm text-[var(--text-muted)] hover:text-white"><X size={16}/></button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Table */}
        <div className="bg-transparent border border-white/5 rounded-2xl flex-1 flex flex-col min-h-0 relative z-0">
          {loading && !queryData ? (
            <div className="h-full flex justify-center items-center">
              <Loader2 className="w-8 h-8 animate-spin text-[var(--text-muted)]" />
            </div>
          ) : sortedCampaigns.length === 0 ? (
            <div className="h-full flex flex-col justify-center items-center text-[var(--text-muted)] space-y-4">
              <Activity className="w-12 h-12 opacity-20" />
              <p>No campaigns found.</p>
              <button onClick={startNewCampaign} className="text-white hover:underline text-sm font-medium">Create your first campaign</button>
            </div>
          ) : (
            <div className="flex-1 overflow-auto custom-scrollbar">
              <table className="w-full text-left text-sm border-collapse relative">
                <thead className="bg-[#111] text-[11px] uppercase tracking-wider font-extrabold text-white sticky top-0 z-10 border-b border-white/10">
                  <tr>
                    <th className="px-5 py-4 w-12">
                      <input 
                        type="checkbox" 
                        checked={selectedIds.size > 0 && selectedIds.size === sortedCampaigns.length}
                        ref={input => { if (input) input.indeterminate = selectedIds.size > 0 && selectedIds.size < sortedCampaigns.length; }}
                        onChange={toggleAll}
                        className="w-4 h-4 rounded border-gray-500 bg-transparent text-white focus:ring-0 focus:ring-offset-0"
                      />
                    </th>
                    <th className="px-6 py-4">Campaign</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Created</th>
                    <th className="px-6 py-4">Delivery</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {sortedCampaigns.map(c => {
                    const isSelected = selectedIds.has(c.campaign_id);
                    const isFailed = (c.stats?.failed || 0) > 0;
                    return (
                      <tr key={c.campaign_id} className={`transition-colors ${isSelected ? 'bg-white/5' : 'hover:bg-white/[0.02]'}`}>
                        <td className="px-5 py-5">
                          <input 
                            type="checkbox" 
                            checked={isSelected}
                            onChange={() => toggleSelection(c.campaign_id)}
                            className="w-4 h-4 rounded border-gray-500 bg-transparent text-white focus:ring-0 focus:ring-offset-0"
                          />
                        </td>
                        <td className="px-6 py-5">
                          <div className="flex items-center gap-2">
                            <div className="font-bold text-white text-[15px]">{c.name}</div>
                            {c.is_test && <span className="text-[10px] px-1.5 py-0.5 border uppercase font-bold rounded" style={{ color: 'var(--accent)', backgroundColor: 'var(--accent-bg)', borderColor: 'var(--accent-bg)' }}>Test</span>}
                            {isFailed && <span className="text-[10px] px-1.5 py-0.5 bg-red-500 text-white font-bold rounded-full">{c.stats.failed} failed</span>}
                          </div>
                          <div className="text-xs text-[#777] mt-1.5 font-medium">{String(c.campaign_id).slice(0,8)}</div>
                        </td>
                        <td className="px-6 py-5">
                          <span className={`inline-flex items-center gap-2 px-3 py-1.5 text-[11px] font-bold uppercase tracking-widest rounded-full ${
                            c.status === 'active' ? '' :
                            c.status === 'paused' ? 'bg-[#3b2a0c] text-[#fcd34d]' :
                            c.status === 'completed' ? 'bg-[#0f3d24] text-[#86efac]' :
                            c.status === 'draft' ? 'bg-transparent text-white' :
                            'bg-red-500/20 text-red-400 border border-red-500/30'
                          }`}
                            style={c.status === 'active' ? { backgroundColor: 'var(--accent-bg)', color: 'var(--accent)' } : {}}
                          >
                            <div className={`w-1.5 h-1.5 rounded-full ${
                              c.status === 'active' ? '' :
                              c.status === 'paused' ? 'bg-[#f59e0b]' :
                              c.status === 'completed' ? 'bg-[#22c55e]' :
                              c.status === 'draft' ? 'bg-gray-400' :
                              'bg-red-500'
                            }`}
                            style={c.status === 'active' ? { backgroundColor: 'var(--accent-strong)' } : {}}
                            ></div>
                            {c.status}
                          </span>
                        </td>
                        <td className="px-6 py-5 text-white font-bold text-sm">
                          {new Date(c.created_at).toLocaleDateString(undefined, { month: 'numeric', day: 'numeric', year: 'numeric' })}
                        </td>
                        <td className="px-6 py-5 w-72">
                          {c.status === 'draft' ? (
                            <span className="text-[#777] text-sm font-medium">Not sent yet</span>
                          ) : (
                            <div className="flex flex-col gap-2">
                              <div className="flex justify-between text-sm font-bold">
                                <span className="text-white">{c.stats?.sent || 0} / {c.stats?.total || 0}</span>
                                <span className={isFailed ? 'text-red-400' : 'text-white'}>{c.stats?.progress_percent || 0}%</span>
                              </div>
                              <div className="w-full h-1.5 bg-[#333] rounded-full overflow-hidden">
                                <div 
                                  className={`h-full transition-all duration-500 ${isFailed ? 'bg-red-500' : 'bg-white'}`}
                                  style={{ width: `${c.stats?.progress_percent || 0}%` }}
                                ></div>
                              </div>
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-5 text-right">
                          <div className="flex items-center justify-end gap-3 relative group/actions">
                            <button onClick={() => loadCampaign(c.campaign_id)} className="p-1.5 text-gray-400 hover:text-white transition-colors" title="View & Manage">
                              <Eye size={18} strokeWidth={2.5} />
                            </button>
                            {(c.status === 'active' || c.status === 'paused') && (
                              <button onClick={() => toggleCampaignStatus(c.campaign_id, c.status)} className="p-1.5 text-gray-400 hover:text-white transition-colors" title={c.status === 'active' ? 'Pause' : 'Resume'}>
                                {c.status === 'active' ? <Pause size={18} strokeWidth={2.5} /> : <Play size={18} strokeWidth={2.5} />}
                              </button>
                            )}
                            <button onClick={() => duplicateCampaign(c.campaign_id)} className="p-1.5 text-gray-400 hover:text-white transition-colors" title="Duplicate">
                              <Copy size={18} strokeWidth={2.5} />
                            </button>
                            
                            <div className="relative">
                              <button className="p-1.5 text-gray-400 hover:text-white transition-colors opacity-0 group-hover/actions:opacity-100 peer">
                                <MoreHorizontal size={18} strokeWidth={2.5} />
                              </button>
                              <div className="absolute right-0 top-full mt-1 w-32 bg-[#1a1a1a] border border-white/10 rounded-lg shadow-xl opacity-0 invisible peer-focus:opacity-100 peer-focus:visible hover:opacity-100 hover:visible z-50 flex flex-col py-1">
                                <button onClick={() => navigator.clipboard.writeText(c.campaign_id)} className="text-left px-4 py-2 text-sm text-white font-medium hover:bg-white/5 w-full">Copy ID</button>
                                <button onClick={() => archiveCampaign(c.campaign_id)} className="text-left px-4 py-2 text-sm text-yellow-500 font-medium hover:bg-white/5 w-full">Archive</button>
                                <button onClick={() => deleteCampaign(c.campaign_id)} className="text-left px-4 py-2 text-sm text-red-500 font-medium hover:bg-white/5 w-full">Delete</button>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          
          <div className="p-4 flex items-center justify-between border-t border-white/10 shrink-0 z-10">
            <div className="text-sm text-[#777] font-bold">
              Page {page} of {totalPages}
            </div>
            <div className="flex items-center gap-2">
              <button disabled={page === 1} onClick={() => setPage(p => Math.max(1, p - 1))} className="px-4 py-2 rounded-lg bg-transparent border border-white/10 text-sm font-bold text-white disabled:opacity-30 hover:bg-white/5 transition-colors">Prev</button>
              <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} className="px-4 py-2 rounded-lg bg-transparent border border-white/10 text-sm font-bold text-white disabled:opacity-30 hover:bg-white/5 transition-colors">Next</button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderWizard = () => (
    <div className="h-full flex flex-col bg-[var(--main-bg)] rounded-xl border border-[var(--card-border)] overflow-hidden shadow-xl">
      {/* Wizard Header */}
      <div className="flex flex-col border-b border-[var(--card-border)] shrink-0">
        <div className="flex justify-between items-center p-4">
          <div className="flex items-center gap-4">
            <button onClick={() => setView('list')} className="p-2 hover:bg-[var(--bg-surface)] rounded-lg text-[var(--text-secondary)] transition-colors">
              <ArrowLeft size={20} />
            </button>
            <div className="flex flex-col">
              <input 
                type="text" 
                value={campaignName}
                onChange={e => setCampaignName(e.target.value)}
                className="bg-transparent text-xl font-bold text-white border-none focus:outline-none focus:ring-1 focus:ring-white/20 rounded px-1 -ml-1 w-64"
                placeholder="Campaign Name"
              />
              <div className="flex items-center gap-2 mt-1 px-1">
                <span className="text-[10px] bg-[var(--bg-surface)] px-1.5 py-0.5 rounded text-[var(--text-muted)] border border-[var(--border)] font-bold uppercase tracking-wider">Draft</span>
                <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1"><Mail size={10} /> Outlook Bridge</span>
              </div>
            </div>
            <div className="ml-4 flex items-center text-[10px] uppercase font-bold text-[var(--text-muted)] tracking-wider bg-[var(--bg-surface)] px-2 py-1 rounded border border-[var(--border)]">
              {isSaving ? (
                <><Loader2 className="w-3 h-3 mr-1.5 animate-spin text-[var(--accent)]" /> Saving</>
              ) : lastSaved ? (
                <><CheckCircle2 className="w-3 h-3 mr-1.5 text-green-500" /> Saved {lastSaved.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</>
              ) : (
                <><CheckCircle2 className="w-3 h-3 mr-1.5 text-[var(--text-muted)]" /> No changes</>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button onClick={() => setShowTemplateLibrary(true)} className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border)] hover:bg-[var(--card-bg)] flex items-center gap-2">
              <Clock size={14} /> Use last email
            </button>
            <button onClick={() => setShowTemplateLibrary(true)} className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border)] hover:bg-[var(--card-bg)] flex items-center gap-2">
              <FileText size={14} /> Reuse email
            </button>
          </div>
        </div>
        
        {/* Bridge Status Row */}
        <div className="px-4 pb-3">
          <BridgeStatus onStatusChange={setBridgeHealthy} compact />
        </div>
        
        {/* Stepper */}
        <div className="flex items-center gap-2 px-4 pb-4 overflow-x-auto hide-scrollbar">
          {[
            { id: STEPS.RECIPIENTS, label: 'Recipients' },
            { id: STEPS.COMPOSE, label: 'Compose' },
            { id: STEPS.PREVIEW, label: 'Preview' },
            { id: STEPS.SEND, label: 'Send' }
          ].map((step, idx) => (
            <React.Fragment key={step.id}>
              <button 
                onClick={() => {
                  if (currentStep > step.id) setCurrentStep(step.id);
                }}
                disabled={currentStep < step.id}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold tracking-wide transition-all ${
                currentStep === step.id 
                  ? 'bg-white text-black shadow-md' 
                  : currentStep > step.id 
                    ? 'bg-[var(--bg-surface)] text-white border border-[var(--border)] cursor-pointer hover:bg-[var(--card-bg)]'
                    : 'bg-transparent text-[var(--text-muted)] border border-transparent opacity-50 cursor-not-allowed'
              }`}>
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  currentStep === step.id ? 'bg-black text-white' : 
                  currentStep > step.id ? 'bg-[var(--text-primary)] text-[var(--card-bg)]' : 
                  'bg-[var(--border)] text-[var(--text-muted)]'
                }`}>
                  {currentStep > step.id ? <CheckCircle2 size={12} strokeWidth={3} /> : step.id}
                </div>
                {step.label}
              </button>
              {idx < 3 && <div className="w-8 h-[2px] bg-[var(--card-border)]" />}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden min-h-0 flex relative bg-[var(--bg-page)]">
        <AnimatePresence mode="wait">
          <motion.div 
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="flex-1 h-full w-full flex p-4"
          >
            {currentStep === STEPS.RECIPIENTS && (
              <div className="flex-1 h-full w-full bg-[var(--main-bg)] rounded-xl border border-[var(--card-border)] overflow-hidden shadow-sm">
                <DragDropRecipientBuilder 
                  recipients={validatedRecipients.recipients}
                  onChange={(newRecipients) => {
                    setValidatedRecipients({
                      recipients: newRecipients,
                      valid_count: newRecipients.filter(r => r.status === 'valid').length
                    });
                  }}
                  onValidate={async (emailsStr) => {
                    const emailsList = emailsStr.split(',').map(e => e.trim()).filter(Boolean);
                    if (emailsList.length === 0) return;
                    try {
                      const res = await api.post('/campaigns/validate-recipients', { emails: emailsList });
                      const data = res.data;
                      const statusMap = new Map();
                      if (data.recipients) data.recipients.forEach(r => statusMap.set(r.email, r.status));
                      
                      const updated = validatedRecipients.recipients.map(r => {
                        if (statusMap.has(r.email)) return { ...r, status: statusMap.get(r.email) };
                        return r;
                      });
                      
                      setValidatedRecipients({
                        recipients: updated,
                        valid_count: updated.filter(r => r.status === 'valid').length
                      });
                      toast.success(`Validated ${emailsList.length} recipients. ${data.valid_count || 0} valid.`);
                    } catch (e) {
                      toast.error("Failed to validate recipients");
                    }
                  }}
                />
              </div>
            )}

            {currentStep === STEPS.COMPOSE && (
              <div className="flex-1 h-full flex gap-4 w-full">
                <div className="flex-[2] h-full flex flex-col gap-4">
                  <div className="bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl p-3 flex flex-col gap-3 shadow-sm shrink-0">
                    <div className="flex gap-4 items-center">
                      <div className="flex-1 relative">
                        <input 
                          type="text" 
                          value={subject}
                          onChange={e => setSubject(e.target.value)}
                          placeholder="Subject (Tip: use {{FirstName}})"
                          className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm font-medium text-white focus:border-white focus:outline-none transition-colors"
                        />
                      </div>
                      <div className="flex gap-2">
                         <button onClick={() => setShowTemplateLibrary(true)} className="px-3 py-2 text-xs font-bold tracking-wide uppercase bg-[var(--bg-surface)] hover:bg-[var(--card-bg)] border border-[var(--border)] rounded-lg text-[var(--text-secondary)] transition-colors">Load Template</button>
                         <button onClick={handleSaveAsTemplate} className="px-3 py-2 text-xs font-bold tracking-wide uppercase bg-[var(--bg-surface)] hover:bg-[var(--card-bg)] border border-[var(--border)] rounded-lg text-[var(--text-secondary)] transition-colors flex items-center gap-1"><Save size={14}/> Save</button>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex-1 min-h-0 bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden shadow-sm">
                    <RichTextComposer 
                      content={body}
                      onChange={setBody}
                      placeholder="Draft your message here..."
                    />
                  </div>
                </div>
                
                <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-1">
                  <div className="bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl p-4 shadow-sm">
                    <h3 className="text-xs uppercase font-bold tracking-wider text-[var(--text-muted)] mb-4 flex items-center gap-2">
                      <Activity className="w-4 h-4 text-white" /> Settings
                    </h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">From Email</label>
                        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg h-10 flex items-center">
                          <CustomSelect
                            value={fromEmail}
                            onChange={(val) => {
                              if (val === 'connect_new') {
                                const token = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
                                const w = window.open(`${API}/bridge/oauth/login?popup=true&token=${token}`, 'Connect Microsoft Outlook', 'width=500,height=600');
                                const messageListener = async (event) => {
                                  if (event.data === 'oauth_success') {
                                    window.removeEventListener('message', messageListener);
                                    try {
                                      const res = await api.get('/auth/outlook/status');
                                      if (res.data.connected) {
                                        toast.success('Successfully connected Outlook account!');
                                        setFromEmail(res.data.email);
                                        localStorage.setItem('talentops_from_email', res.data.email);
                                      }
                                    } catch (err) {}
                                  }
                                };
                                window.addEventListener('message', messageListener);
                              } else {
                                setFromEmail(val);
                                localStorage.setItem('talentops_from_email', val);
                              }
                            }}
                            options={[
                              { value: 'Outlook Default', label: 'Outlook Default' },
                              { value: 'connect_new', label: '+ Connect new Outlook account' }
                            ]}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <SignatureManager 
                    selectedSignatureId={signatureId}
                    onSelectSignature={setSignatureId}
                  />
                </div>
              </div>
            )}

            {currentStep === STEPS.PREVIEW && (
              <div className="flex w-full h-full gap-4 relative">
                <div className="flex-[2] h-full bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden shadow-sm">
                  <EmailPreview 
                    campaignId={activeCampaignId}
                    subjectTemplate={subject}
                    bodyTemplate={body}
                    signatureId={signatureId}
                    recipients={validatedRecipients.recipients.filter(r => r.status === 'valid')}
                  />
                </div>
                
                <div className="flex-1 h-full flex flex-col gap-4">
                  <div className="bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl p-4 h-full flex flex-col shadow-sm">
                    <h3 className="text-sm font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-green-500" /> Pre-Flight Validation
                    </h3>
                    
                    {isValidating ? (
                      <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-muted)] space-y-3">
                        <Loader2 className="w-6 h-6 animate-spin text-white" />
                        <span className="text-sm font-medium">Running checks...</span>
                      </div>
                    ) : preflightData ? (
                      <div className="flex-1 space-y-4">
                        {preflightData.ready ? (
                          <>
                            <ValidationItem label="All Checks Passed" success={true} info="Campaign is ready to launch." />
                            {preflightData.errors?.filter(e => e.code === 'BRIDGE_OFFLINE').map((err, i) => (
                               <ValidationItem key={i} label="OFFLINE QUEUEING" error="Outlook Bridge is offline. Emails will queue." success={false} warning={true} />
                            ))}
                          </>
                        ) : (
                          <>
                            <div className="text-sm font-bold text-red-400 mb-2">Errors:</div>
                            {preflightData.errors?.map((err, i) => (
                               <ValidationItem key={i} label={err.code.replace(/_/g, ' ')} error={err.message} success={false} />
                            ))}
                          </>
                        )}
                        
                        {preflightData.ready && (
                          <div className="mt-8 pt-4 border-t border-[var(--border)]">
                            <div className="bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white mb-4">
                              ETA: <strong>{validatedRecipients.valid_count <= 50 ? `~${Math.max(5, Math.ceil(validatedRecipients.valid_count * 0.5))} secs` : `~${Math.ceil(validatedRecipients.valid_count / 60)} mins`}</strong>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-muted)] space-y-3">
                        <Loader2 className="w-6 h-6 animate-spin opacity-30" />
                        <span className="text-sm">Waiting for validation results...</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {currentStep === STEPS.SEND && activeCampaignId && (
              <div className="w-full h-full flex flex-col gap-4 overflow-y-auto custom-scrollbar pb-6 pr-2">
                <CampaignProgress campaignId={activeCampaignId} />
                <div className="bg-[var(--main-bg)] border border-[var(--card-border)] rounded-xl p-4 min-h-[300px] shadow-sm">
                   <h3 className="text-xs uppercase font-bold tracking-wider text-[var(--text-muted)] mb-4 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-white" /> Delivery Logs
                    </h3>
                   <CampaignLogs campaignId={activeCampaignId} />
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Wizard Footer */}
      {currentStep !== STEPS.SEND && (
        <div className="p-4 border-t border-[var(--card-border)] bg-[var(--main-bg)] flex justify-between items-center shrink-0">
          <button
            onClick={() => setCurrentStep(prev => prev - 1)}
            disabled={currentStep === STEPS.RECIPIENTS}
            className="px-6 py-2.5 text-sm font-bold text-[var(--text-secondary)] hover:text-white disabled:opacity-30 transition-colors uppercase tracking-wide"
          >
            Back
          </button>
          
          <button
            onClick={handleNextStep}
            disabled={
              (currentStep === STEPS.RECIPIENTS && validatedRecipients.valid_count === 0) ||
              (currentStep === STEPS.COMPOSE && (!subject.trim() || !body.trim())) ||
              (currentStep === STEPS.PREVIEW && !preflightData?.ready)
            }
            className={`px-8 py-2.5 rounded-lg text-sm font-bold uppercase tracking-wide flex items-center gap-2 transition-all shadow-md ${
               currentStep === STEPS.PREVIEW && preflightData?.ready
                ? 'bg-white text-black hover:bg-gray-200'
                : currentStep === STEPS.PREVIEW && !preflightData?.ready
                ? 'bg-[var(--bg-surface)] text-[var(--text-muted)] border border-[var(--border)] cursor-not-allowed'
                : (currentStep === STEPS.RECIPIENTS && validatedRecipients.valid_count === 0) || (currentStep === STEPS.COMPOSE && (!subject.trim() || !body.trim()))
                ? 'bg-[var(--bg-surface)] text-[var(--text-muted)] border border-[var(--border)] cursor-not-allowed'
                : 'bg-white text-black hover:bg-gray-200'
            }`}
          >
            {currentStep === STEPS.PREVIEW ? (
              <><Play size={16} fill="currentColor" /> Launch</>
            ) : (
              <>Continue <ChevronRight size={16} /></>
            )}
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full bg-[var(--bg-page)] text-[var(--text-primary)] p-4 sm:p-6 overflow-hidden">
      {view === 'list' ? renderList() : renderWizard()}
      
      {showTemplateLibrary && (
        <TemplateLibraryModal 
          isOpen={showTemplateLibrary} 
          onClose={() => setShowTemplateLibrary(false)} 
          onImport={handleTemplateImport} 
        />
      )}
    </div>
  );
}

function ValidationItem({ label, success, error, info, warning }) {
  return (
    <div className={`flex items-start gap-3 p-3 bg-[var(--bg-surface)] rounded-lg border ${warning ? 'border-yellow-500/30 bg-yellow-500/10' : 'border-[var(--border)]'}`}>
      <div className="mt-0.5">
        {success ? (
          <CheckCircle2 className="w-4 h-4 text-green-400" />
        ) : warning ? (
          <AlertCircle className="w-4 h-4 text-yellow-400" />
        ) : (
          <AlertCircle className="w-4 h-4 text-red-500" />
        )}
      </div>
      <div>
        <div className="text-sm font-bold text-white">{label}</div>
        {info && <div className="text-xs text-[var(--text-muted)] mt-1 font-medium">{info}</div>}
        {error && <div className={`text-xs mt-1 font-medium ${warning ? 'text-yellow-400/80' : 'text-red-400/90'}`}>{error}</div>}
      </div>
    </div>
  );
}
