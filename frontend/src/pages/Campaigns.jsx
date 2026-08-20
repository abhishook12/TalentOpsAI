import React, { useState, useEffect, useRef, useMemo, useCallback, memo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  Send, ArrowLeft, Plus, Mail, Activity, AlertCircle, FileText,
  CheckCircle2, Loader2, ChevronRight, Play, Eye, Download, Search,
  Pause, MoreHorizontal, Copy, Trash2, Archive, Save, Clock, RefreshCw, X,
  ChevronDown, ChevronUp, Zap
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useSessionState } from '../hooks/useSessionState';

import BridgeStatus from '../components/BridgeStatus';
import RichTextComposer from '../components/RichTextComposer';
import SignatureManager from '../components/SignatureManager';
import DragDropRecipientBuilder from '../components/campaigns/DragDropRecipientBuilder';
import CampaignProgress from '../components/CampaignProgress';

import TemplateLibraryModal from '../components/campaigns/TemplateLibraryModal';
import ConnectionWizard from '../components/ConnectionWizard';
import PreflightSafetyModal from '../components/campaigns/PreflightSafetyModal';
import SequenceGeneratorModal from '../components/campaigns/SequenceGeneratorModal';
import DomainHealthModal from '../components/campaigns/DomainHealthModal';

import { setLastEmail, saveTemplate } from '../lib/emailTemplates';

// ─────────────────────────────────────────────────────────────────────────────
// Workspace mode: 'compose' | 'sending'
// View: 'list' | 'workspace'
// ─────────────────────────────────────────────────────────────────────────────

class CampaignErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('Campaign workspace error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <AlertCircle style={{ width: 48, height: 48, color: '#ef4444', margin: '0 auto 16px' }} />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 8 }}>Something went wrong</h2>
          <p style={{ color: '#888', marginBottom: 24 }}>The campaign workspace encountered an error.</p>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); this.props.onReset?.(); }}
            style={{ padding: '10px 24px', background: '#fff', color: '#000', border: '1px solid #333', borderRadius: 8, cursor: 'pointer', fontWeight: 500 }}
          >
            Return to Campaign List
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const CampaignRow = memo(function CampaignRow({
  campaign: c,
  isSelected,
  onToggleSelection,
  onLoad,
  onToggleStatus,
  onDuplicate,
  onArchive,
  onDelete
}) {
  const isFailed = (c.stats?.failed || 0) > 0;
  return (
    <tr className={`transition-colors ${isSelected ? 'bg-[var(--bg-hover)]' : 'hover:bg-white/[0.02]'}`}>
      <td className="px-4 py-4"><input type="checkbox" checked={isSelected} onChange={() => onToggleSelection(c.campaign_id)} className="w-3.5 h-3.5 rounded" /></td>
      <td className="px-4 py-4">
        <div className="font-bold text-[var(--text-primary)]">{c.name}</div>
        <div className="text-xs text-[var(--text-muted)] mt-0.5 font-mono">{String(c.campaign_id).slice(0, 8)}</div>
        {isFailed && <span className="text-[10px] px-1.5 py-0.5 bg-red-500/20 text-red-400 font-bold rounded-full">{c.stats.failed} failed</span>}
      </td>
      <td className="px-4 py-4">
        <StatusBadge status={c.status} />
      </td>
      <td className="px-4 py-4 text-sm font-medium text-[var(--text-primary)]">
        {new Date(c.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
      </td>
      <td className="px-4 py-4 w-56">
        {c.status === 'draft' ? (
          <span className="text-xs text-[var(--text-muted)]">Not sent</span>
        ) : (
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between text-xs font-bold">
              <span className="text-[var(--text-primary)]">{c.stats?.sent || 0}/{c.stats?.total || 0}</span>
              <span className={isFailed ? 'text-red-400' : 'text-[var(--text-primary)]'}>{c.stats?.progress_percent || 0}%</span>
            </div>
            <div className="h-1 bg-[var(--card-border)] rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all ${isFailed ? 'bg-red-500' : 'bg-[var(--text-primary)]'}`} style={{ width: `${c.stats?.progress_percent || 0}%` }} />
            </div>
          </div>
        )}
      </td>
      <td className="px-4 py-4 text-right">
        <div className="flex items-center justify-end gap-2">
          <button onClick={() => onLoad(c.campaign_id)} className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors" title="Open"><Eye size={15} /></button>
          {(c.status === 'active' || c.status === 'paused') && (
            <button onClick={() => onToggleStatus(c.campaign_id, c.status)} className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
              {c.status === 'active' ? <Pause size={15} /> : <Play size={15} />}
            </button>
          )}
          <button onClick={() => onDuplicate(c.campaign_id)} className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors" title="Duplicate"><Copy size={15} /></button>
          <button onClick={() => onArchive(c.campaign_id)} className="p-1.5 text-[var(--text-muted)] hover:text-yellow-400 transition-colors" title="Archive"><Archive size={15} /></button>
          <button onClick={() => onDelete(c.campaign_id)} className="p-1.5 text-[var(--text-muted)] hover:text-red-400 transition-colors" title="Delete"><Trash2 size={15} /></button>
        </div>
      </td>
    </tr>
  );
});

export default function Campaigns() {
  // ── View State ──────────────────────────────────────────────────────────────
  const [view, setView] = useSessionState('camp_view', 'list');
  const [workspaceMode, setWorkspaceMode] = useSessionState('camp_wsMode', 'compose'); // 'compose' | 'sending'

  // ── List State ───────────────────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useSessionState('camp_search', '');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useSessionState('camp_statusFilter', 'all');
  const [showTest, setShowTest] = useState(false);
  const [page, setPage] = useSessionState('camp_page', 1);
  const [limit, setLimit] = useState(20);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const searchInputRef = useRef(null);

  // ── Campaign Core State ───────────────────────────────────────────────────────
  const [activeCampaignId, setActiveCampaignId] = useSessionState('camp_activeId', null);
  const [campaignName, setCampaignName] = useState('New Campaign');
  const [senderAccountId, setSenderAccountId] = useState(null);
  const [sendError, setSendError] = useState(null);
  const [fromEmail, setFromEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [signatureId, setSignatureId] = useState(null);
  const [validatedRecipients, setValidatedRecipients] = useState({ recipients: [], valid_count: 0 });

  // ── Accounts State ────────────────────────────────────────────────────────────
  const [accounts, setAccounts] = useState([]);
  const [showConnectionWizard, setShowConnectionWizard] = useState(false);

  // ── Readiness / Preflight State ──────────────────────────────────────────────
  const [preflightData, setPreflightData] = useState(null);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [showSafetyModal, setShowSafetyModal] = useState(false);
  const [safetyPreflightData, setSafetyPreflightData] = useState(null);
  const [checks, setChecks] = useState({
    sender: 'idle',
    recipients: 'idle',
    template: 'idle',
    bridge: 'idle',
  });

  // ── Modals ────────────────────────────────────────────────────────────────────
  const [showTemplateLibrary, setShowTemplateLibrary] = useState(false);
  const [showSequenceGenerator, setShowSequenceGenerator] = useState(false);
  const [showDomainHealth, setShowDomainHealth] = useState(false);

  // ── Autosave State ────────────────────────────────────────────────────────────
  const [lastSaved, setLastSaved] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const savePromiseRef = useRef(null);

  // ── Send State ────────────────────────────────────────────────────────────────
  const [isSending, setIsSending] = useState(false);

  // ── Recipients panel collapsed on mobile ─────────────────────────────────────
  const [recipientsCollapsed, setRecipientsCollapsed] = useState(false);

  // ── Background preflight debounce ref ────────────────────────────────────────
  const preflightTimerRef = useRef(null);
  const validationTimerRef = useRef(null);

  // ─────────────────────────────────────────────────────────────────────────────
  // Derived: detected variables from subject + body
  // ─────────────────────────────────────────────────────────────────────────────
  const detectedVariables = useMemo(() => {
    const pattern = /\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g;
    const found = new Set();
    for (const match of (subject + ' ' + body).matchAll(pattern)) {
      found.add(match[1]);
    }
    return Array.from(found);
  }, [subject, body]);

  // ─────────────────────────────────────────────────────────────────────────────
  // List query
  // ─────────────────────────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearchQuery(searchQuery), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const { data: queryData, isLoading: loading, error: campaignsError, refetch } = useQuery({
    queryKey: ['campaigns', debouncedSearchQuery, statusFilter, showTest, page, limit],
    queryFn: async () => {
      const params = new URLSearchParams({ page: page.toString(), limit: limit.toString() });
      if (debouncedSearchQuery) params.append('search', debouncedSearchQuery);
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
      if (!showTest) params.append('is_test', 'false');
      const res = await api.get(`/campaigns?${params.toString()}`);
      return res.data;
    },
    enabled: view === 'list',
    refetchInterval: view === 'list' ? 5000 : false,
    refetchOnWindowFocus: true,
    retry: 1,
  });

  const rawCampaigns = useMemo(() => Array.isArray(queryData) ? queryData : queryData?.items || [], [queryData]);
  const totalPages = useMemo(() => queryData?.pages || 1, [queryData]);

  const sortedCampaigns = rawCampaigns;

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
    return { total: rawCampaigns.length, active, sent, failures, counts };
  }, [rawCampaigns]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Fetch accounts
  // ─────────────────────────────────────────────────────────────────────────────
  const fetchAccounts = useCallback(async () => {
    try {
      const res = await api.get('/accounts');
      setAccounts(res.data.items || []);
    } catch {
      console.error('Failed to load accounts');
    }
  }, []);

  useEffect(() => {
    if (view === 'workspace') fetchAccounts();
  }, [view, fetchAccounts]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Autosave (debounced 1.2s, only when campaign exists)
  // ─────────────────────────────────────────────────────────────────────────────
  const saveDraft = useCallback(async () => {
    if (savePromiseRef.current) return savePromiseRef.current;
    const doSave = async () => {
      setIsSaving(true);
      try {
        let cid = activeCampaignId;
        if (cid) {
          await api.put(`/campaigns/${cid}`, {
            name: campaignName,
            from_email: fromEmail,
            signature_id: signatureId,
            sender_account_id: senderAccountId,
          });
        } else {
          const res = await api.post('/campaigns', {
            name: campaignName,
            from_email: fromEmail,
            status: 'draft',
            signature_id: signatureId,
            sender_account_id: senderAccountId,
          });
          cid = res.data.campaign_id;
          setActiveCampaignId(cid);
        }
        if (subject || body) {
          await api.post(`/campaigns/${cid}/templates`, { name: subject || 'Draft', subject: subject || '', body: body || '' });
        }
        setLastSaved(new Date());
        return cid;
      } catch {
        console.error('Draft save failed');
        return null;
      } finally {
        setIsSaving(false);
        savePromiseRef.current = null;
      }
    };
    savePromiseRef.current = doSave();
    return savePromiseRef.current;
  }, [activeCampaignId, campaignName, fromEmail, signatureId, senderAccountId, subject, body]);

  useEffect(() => {
    if (view !== 'workspace' || workspaceMode !== 'compose') return;
    const timer = setTimeout(() => {
      if (activeCampaignId) {
        saveDraft();
        if (subject || body) setLastEmail(subject, body);
      }
    }, 1200);
    return () => clearTimeout(timer);
  }, [subject, body, signatureId, senderAccountId, campaignName, view, workspaceMode, activeCampaignId, saveDraft]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Live readiness checks (frontend-side, immediate)
  // ─────────────────────────────────────────────────────────────────────────────
  useEffect(() => {
    setChecks(prev => ({
      ...prev,
      sender: senderAccountId ? 'ok' : 'idle',
    }));
  }, [senderAccountId]);

  useEffect(() => {
    const count = validatedRecipients.valid_count || 0;
    setChecks(prev => ({
      ...prev,
      recipients: count > 0 ? 'ok' : 'idle',
    }));
  }, [validatedRecipients]);

  useEffect(() => {
    const hasContent = subject.trim().length > 0 && body.trim().length > 3;
    setChecks(prev => ({
      ...prev,
      template: hasContent ? 'ok' : 'idle',
    }));
  }, [subject, body]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Background preflight — fires 2s after any critical state change
  // ─────────────────────────────────────────────────────────────────────────────
  const runPreflight = useCallback(async (campaignId) => {
    if (!campaignId) return;
    const validRecipients = validatedRecipients.recipients.filter(r => r.status === 'valid');
    if (!subject.trim() || !body.trim() || validRecipients.length === 0) return;

    setPreflightLoading(true);
    setChecks(prev => ({ ...prev, bridge: 'checking' }));
    try {
      const res = await api.post(`/campaigns/${campaignId}/prepare-preview`, {
        name: campaignName,
        from_email: fromEmail,
        signature_id: signatureId,
        subject: subject,
        body: body,
        recipients: validRecipients,
      });
      setPreflightData(res.data);
      setChecks(prev => ({
        ...prev,
        bridge: res.data.bridge_healthy ? 'ok' : 'warn',
      }));
      setLastSaved(new Date());
    } catch (e) {
      setPreflightData({ ready: false, errors: [{ code: 'API_ERROR', message: e.response?.data?.detail || 'Server error' }] });
    } finally {
      setPreflightLoading(false);
    }
  }, [validatedRecipients, subject, body, campaignName, fromEmail, signatureId]);

  // Trigger preflight when conditions are met
  useEffect(() => {
    if (view !== 'workspace' || workspaceMode !== 'compose') return;
    if (!senderAccountId || validatedRecipients.valid_count === 0 || !subject.trim() || !body.trim()) return;

    clearTimeout(preflightTimerRef.current);
    setPreflightData(null);

    preflightTimerRef.current = setTimeout(async () => {
      // Ensure campaign exists first
      let cid = activeCampaignId;
      if (!cid) {
        const saved = await saveDraft();
        cid = saved;
      }
      if (cid) runPreflight(cid);
    }, 2000);

    return () => clearTimeout(preflightTimerRef.current);
  }, [senderAccountId, validatedRecipients, subject, body, view, workspaceMode]);

  // Background recipient validation (debounced 800ms after recipients change)
  const lastValidatedCountRef = useRef(0);
  useEffect(() => {
    if (view !== 'workspace') return;
    const currentCount = validatedRecipients.recipients.length;
    // Only validate if new recipients were added
    if (currentCount <= lastValidatedCountRef.current || currentCount === 0) {
      lastValidatedCountRef.current = currentCount;
      return;
    }
    clearTimeout(validationTimerRef.current);
    validationTimerRef.current = setTimeout(async () => {
      // Only send newly-added emails for validation
      const newEmails = validatedRecipients.recipients
        .slice(lastValidatedCountRef.current)
        .map(r => r.email);
      if (newEmails.length === 0) return;
      try {
        const res = await api.post('/campaigns/validate-recipients', { emails: newEmails });
        const statusMap = new Map();
        (res.data.recipients || []).forEach(r => statusMap.set(r.email, r.status));
        const updated = validatedRecipients.recipients.map(r =>
          statusMap.has(r.email) ? { ...r, status: statusMap.get(r.email) } : r
        );
        setValidatedRecipients({ recipients: updated, valid_count: updated.filter(r => r.status === 'valid').length });
      } catch { /* silent */ }
      lastValidatedCountRef.current = currentCount;
    }, 800);
    return () => clearTimeout(validationTimerRef.current);
  }, [validatedRecipients.recipients.length, view]);

  // ─────────────────────────────────────────────────────────────────────────────
  // Workspace open/close helpers
  // ─────────────────────────────────────────────────────────────────────────────
  const startNewCampaign = useCallback((initialTemplate = null) => {
    setActiveCampaignId(null);
    setCampaignName(initialTemplate?.name || 'New Campaign');
    setSubject(initialTemplate?.subject || '');
    setBody(initialTemplate?.html_body || initialTemplate?.text_body || initialTemplate?.body || '');
    setSignatureId(null);
    setSenderAccountId(null);
    setFromEmail('');
    setValidatedRecipients({ recipients: [], valid_count: 0 });
    setPreflightData(null);
    setChecks({ sender: 'idle', recipients: 'idle', template: (initialTemplate?.subject || initialTemplate?.body) ? 'ok' : 'idle', bridge: 'idle' });
    setWorkspaceMode('compose');
    setLastSaved(null);
    setView('workspace');
  }, []);

  const loadCampaign = useCallback(async (id) => {
    try {
      const res = await api.get(`/campaigns/${id}?include_recruiters=true`);
      const c = res.data;
      setActiveCampaignId(c.campaign_id);
      setCampaignName(c.name);
      setFromEmail(c.from_email || '');
      setSenderAccountId(c.sender_account_id || null);
      setSignatureId(c.signature_id || null);
      if (c.templates?.length > 0) {
        setSubject(c.templates[0].subject || '');
        setBody(c.templates[0].body || '');
      } else {
        setSubject(''); setBody('');
      }
      if (c.campaign_recruiters) {
        const loaded = c.campaign_recruiters.map(cr => ({ email: cr.recruiter_email, name: cr.recruiter_name || '', recruiter_id: cr.recruiter_id, status: 'valid' }));
        setValidatedRecipients({ recipients: loaded, valid_count: loaded.length });
      }
      setPreflightData(null);
      setChecks({ sender: c.sender_account_id ? 'ok' : 'idle', recipients: 'idle', template: 'idle', bridge: 'idle' });
      setWorkspaceMode(c.status === 'active' || c.status === 'paused' || c.status === 'completed' ? 'sending' : 'compose');
      setView('workspace');
    } catch {
      toast.error('Failed to load campaign');
    }
  }, []);

  // ─────────────────────────────────────────────────────────────────────────────
  // Send campaign & Pre-Flight Deliverability Gate
  // ─────────────────────────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    if (isSending) return;
    setSendError(null);
    try {
      let cid = activeCampaignId;
      if (!cid) {
        const saved = await saveDraft();
        cid = saved;
        if (!cid) { toast.error('Failed to save campaign draft'); return; }
      }
      if (savePromiseRef.current) await savePromiseRef.current;
      
      const validRecipients = validatedRecipients.recipients.filter(r => r.status === 'valid');
      if (validRecipients.length === 0) {
        toast.error('Please add at least one valid recipient');
        return;
      }

      // 1. Prepare preview & enroll recipients
      await api.post(`/campaigns/${cid}/prepare-preview`, {
        name: campaignName,
        from_email: fromEmail,
        signature_id: signatureId,
        subject: subject,
        body: body,
        recipients: validRecipients,
      });

      // 2. Trigger Deliverability Pre-Flight Scan
      const preflightRes = await api.post(`/campaigns/${cid}/preflight`, {
        emails: validRecipients.map(r => r.email),
        names: validRecipients.map(r => r.name || '')
      });

      setSafetyPreflightData(preflightRes.data);
      setShowSafetyModal(true);
    } catch (e) {
      const errDetail = e.response?.data?.detail || 'Failed to initialize pre-flight check';
      toast.error(errDetail);
    }
  }, [activeCampaignId, isSending, saveDraft, validatedRecipients, campaignName, fromEmail, signatureId, subject, body]);

  const handleConfirmLaunch = useCallback(async ({ excludeRisky }) => {
    if (isSending) return;
    setIsSending(true);
    try {
      const cid = activeCampaignId;
      if (!cid) return;

      await api.post(`/campaigns/${cid}/start`);
      setShowSafetyModal(false);
      setWorkspaceMode('sending');
      toast.success('Campaign launched with deliverability protection!');
    } catch (e) {
      const errDetail = e.response?.data?.detail || 'Failed to start campaign';
      if (errDetail.includes('attention')) {
        setSendError(errDetail);
      } else {
        toast.error(errDetail);
      }
    } finally {
      setIsSending(false);
    }
  }, [activeCampaignId, isSending]);

  // ─────────────────────────────────────────────────────────────────────────────
  // List actions
  // ─────────────────────────────────────────────────────────────────────────────
  const toggleSelection = useCallback((id) => {
    setSelectedIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }, []);

  const toggleAll = useCallback(() => {
    setSelectedIds(prev => prev.size === sortedCampaigns.length ? new Set() : new Set(sortedCampaigns.map(c => c.campaign_id)));
  }, [sortedCampaigns]);

  const handleBulkAction = useCallback(async (action) => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Are you sure you want to ${action} ${selectedIds.size} campaigns?`)) return;
    try {
      await Promise.all(Array.from(selectedIds).map(id => {
        if (action === 'delete') return api.delete(`/campaigns/${id}`);
        if (action === 'archive') return api.put(`/campaigns/${id}/archive`);
        if (action === 'duplicate') return api.post(`/campaigns/${id}/duplicate`);
        return Promise.resolve();
      }));
      toast.success(`Bulk ${action} successful`);
      setSelectedIds(new Set());
      refetch();
    } catch { toast.error(`Some actions failed`); }
  }, [selectedIds, refetch]);

  const deleteCampaign = async (id) => {
    if (!window.confirm('Delete this campaign?')) return;
    try { await api.delete(`/campaigns/${id}`); toast.success('Deleted'); refetch(); }
    catch { toast.error('Failed to delete'); }
  };
  const archiveCampaign = async (id) => {
    try { await api.put(`/campaigns/${id}/archive`); toast.success('Archived'); refetch(); }
    catch { toast.error('Failed to archive'); }
  };
  const toggleCampaignStatus = async (id, status) => {
    try {
      const action = status === 'active' ? 'pause' : 'resume';
      await api.post(`/campaigns/${id}/${action}`);
      toast.success(`Campaign ${action}d`);
      refetch();
    } catch { toast.error('Failed to change status'); }
  };
  const duplicateCampaign = async (id) => {
    try { await api.post(`/campaigns/${id}/duplicate`); toast.success('Duplicated'); refetch(); }
    catch { toast.error('Failed to duplicate'); }
  };
  const exportCSV = () => {
    const headers = ['ID', 'Name', 'Status', 'Created', 'Sent', 'Failed', 'Progress'];
    const rows = sortedCampaigns.map(c => [c.campaign_id, `"${c.name}"`, c.status, new Date(c.created_at).toLocaleDateString(), c.stats?.sent || 0, c.stats?.failed || 0, `${c.stats?.progress_percent || 0}%`]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `campaigns_${Date.now()}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  const handleTemplateImport = (template) => {
    setSubject(template.subject);
    setBody(template.html_body || template.text_body || '');
  };

  const handleSaveAsTemplate = () => {
    if (!subject || !body) { toast.error('Subject and body cannot be empty'); return; }
    saveTemplate({ name: campaignName + ' Template', subject, body });
    toast.success('Saved to Template Library');
  };

  // Send button readiness
  const localIsReady = Boolean(senderAccountId && validatedRecipients.valid_count > 0 && subject.trim().length > 0 && body.trim().length > 3);
  const sendLabel = isSending ? 'Starting...' : 'Send Campaign';

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: List View
  // ─────────────────────────────────────────────────────────────────────────────
  if (view === 'list') {
    return (
      <div className="h-full bg-[var(--bg-page)] text-[var(--text-primary)] p-4 sm:p-6 flex flex-col gap-6 overflow-auto custom-scrollbar">

        {/* Header */}
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 900, letterSpacing: '-0.02em', margin: 0 }}>Campaigns</h1>
            <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 14 }}>Outbound email campaigns & delivery monitoring.</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => setShowDomainHealth(true)} className="flex items-center gap-2 px-3 py-2 text-sm font-bold border border-[var(--border)] rounded-lg bg-[var(--bg-surface)] text-emerald-400 hover:bg-[var(--bg-hover)] transition-colors">
              <Activity size={14} /> Domain Health
            </button>
            <button onClick={() => setShowSequenceGenerator(true)} className="flex items-center gap-2 px-3 py-2 text-sm font-bold border border-[var(--border)] rounded-lg bg-[var(--bg-surface)] text-cyan-400 hover:bg-[var(--bg-hover)] transition-colors">
              <Zap size={14} /> AI Sequence
            </button>
            <button onClick={() => setShowTemplateLibrary(true)} className="flex items-center gap-2 px-3 py-2 text-sm font-bold border border-[var(--border)] rounded-lg bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors">
              <Clock size={14} /> Templates
            </button>
            <button onClick={startNewCampaign} className="flex items-center gap-2 px-4 py-2 text-sm font-bold rounded-lg bg-[var(--text-primary)] text-[var(--main-bg)] hover:opacity-90 transition-opacity">
              <Plus size={16} /> New Campaign
            </button>
          </div>
        </div>

        {/* KPI Strip */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'ACTIVE', value: kpis.active, color: 'var(--text-primary)' },
            { label: 'SENT', value: kpis.sent, color: '#4ade80' },
            { label: 'FAILED', value: kpis.failures, color: kpis.failures > 0 ? '#f87171' : 'var(--text-muted)' },
          ].map(k => (
            <div key={k.label} style={{ background: 'var(--bg-surface)', border: '1px solid var(--card-border)', borderRadius: 6, padding: '16px 20px' }}>
              <div style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>{k.label}</div>
              <div style={{ fontSize: 36, fontWeight: 900, lineHeight: 1.1, marginTop: 6, color: k.color }}>{k.value}</div>
            </div>
          ))}
        </div>

        {/* Toolbar */}
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--card-border)', borderRadius: 6, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--card-border)', display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
            {/* Status tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar hide-scrollbar">
              {['all', 'active', 'draft', 'paused', 'completed', 'failed'].map(s => (
                <button key={s} onClick={() => { setStatusFilter(s); setPage(1); }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all ${statusFilter === s ? 'bg-[var(--text-primary)] text-[var(--main-bg)]' : 'bg-[var(--bg-hover)] text-[var(--text-primary)] hover:bg-[var(--card-border)]'}`}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-black ${statusFilter === s ? 'bg-white/10' : 'bg-[var(--bg-surface)] text-[var(--text-muted)]'}`}>{kpis.counts[s] ?? 0}</span>
                </button>
              ))}
            </div>
            {/* Search + controls */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" size={13} />
                <input ref={searchInputRef} type="text" placeholder="Search..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  className="bg-[var(--bg-hover)] border border-[var(--border)] rounded-lg pl-8 pr-4 py-2 text-sm text-[var(--text-primary)] focus:outline-none w-48" />
              </div>
              <select value={limit} onChange={e => { setLimit(Number(e.target.value)); setPage(1); }} className="bg-[var(--bg-hover)] border border-[var(--border)] rounded-lg px-2 py-2 text-sm text-[var(--text-primary)] focus:outline-none">
                {[10, 20, 50].map(n => <option key={n} value={n}>{n}/page</option>)}
              </select>
              <button onClick={exportCSV} className="flex items-center gap-1.5 px-3 py-2 border border-[var(--border)] rounded-lg text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors">
                <Download size={13} /> Export
              </button>
              <button onClick={() => refetch()} className="p-2 border border-[var(--border)] rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors">
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          {/* Bulk action bar */}
          <AnimatePresence>
            {selectedIds.size > 0 && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                style={{ background: 'var(--bg-hover)', borderBottom: '1px solid var(--card-border)', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 16 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>{selectedIds.size} selected</span>
                <button onClick={() => handleBulkAction('duplicate')} className="flex items-center gap-1 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]"><Copy size={13} /> Duplicate</button>
                <button onClick={() => handleBulkAction('archive')} className="flex items-center gap-1 text-xs font-medium text-[var(--text-secondary)] hover:text-yellow-400"><Archive size={13} /> Archive</button>
                <button onClick={() => handleBulkAction('delete')} className="flex items-center gap-1 text-xs font-medium text-red-400 hover:text-red-300"><Trash2 size={13} /> Delete</button>
                <button onClick={() => setSelectedIds(new Set())} className="ml-auto text-[var(--text-muted)] hover:text-[var(--text-primary)]"><X size={14} /></button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Table */}
          {campaignsError && (
            <div style={{ padding: '16px 20px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, color: '#ef4444', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, margin: '0 0 16px' }}>
              <AlertCircle style={{ width: 16, height: 16, flexShrink: 0 }} />
              <span>Failed to load campaigns. Please try again.</span>
              <button onClick={() => refetch()} style={{ marginLeft: 'auto', background: 'rgba(239,68,68,0.2)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 12 }}>Retry</button>
            </div>
          )}
          {loading && !queryData ? (
            <div className="flex justify-center items-center py-16"><Loader2 className="w-6 h-6 animate-spin text-[var(--text-muted)]" /></div>
          ) : sortedCampaigns.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <Activity size={32} className="text-[var(--text-muted)] opacity-30" />
              <p className="text-[var(--text-muted)] text-sm">No campaigns found.</p>
              <button onClick={startNewCampaign} className="text-sm font-medium text-[var(--text-primary)] hover:underline">Create your first campaign</button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead style={{ background: 'var(--bg-hover)', fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', borderBottom: '1px solid var(--card-border)' }}>
                  <tr>
                    <th className="px-4 py-3 w-10"><input type="checkbox" checked={selectedIds.size > 0 && selectedIds.size === sortedCampaigns.length} ref={el => { if (el) el.indeterminate = selectedIds.size > 0 && selectedIds.size < sortedCampaigns.length; }} onChange={toggleAll} className="w-3.5 h-3.5 rounded" /></th>
                    <th className="px-4 py-3">Campaign</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3">Delivery</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {sortedCampaigns.map(c => (
                    <CampaignRow
                      key={c.campaign_id}
                      campaign={c}
                      isSelected={selectedIds.has(c.campaign_id)}
                      onToggleSelection={toggleSelection}
                      onLoad={loadCampaign}
                      onToggleStatus={toggleCampaignStatus}
                      onDuplicate={duplicateCampaign}
                      onArchive={archiveCampaign}
                      onDelete={deleteCampaign}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          <div style={{ padding: '10px 16px', borderTop: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <button disabled={page === 1} onClick={() => setPage(p => Math.max(1, p - 1))} className="px-3 py-1.5 text-xs font-bold border border-[var(--border)] rounded-lg text-[var(--text-primary)] disabled:opacity-30 hover:bg-[var(--bg-hover)] transition-colors">Prev</button>
              <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} className="px-3 py-1.5 text-xs font-bold border border-[var(--border)] rounded-lg text-[var(--text-primary)] disabled:opacity-30 hover:bg-[var(--bg-hover)] transition-colors">Next</button>
            </div>
          </div>
        </div>

        {/* Modals */}
        {showTemplateLibrary && (
          <TemplateLibraryModal isOpen onClose={() => setShowTemplateLibrary(false)} onImport={(t) => { startNewCampaign(t); setShowTemplateLibrary(false); }} />
        )}
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: Campaign Workspace (Single Page)
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <CampaignErrorBoundary onReset={() => setView('list')}>
      <div className="h-full bg-[var(--bg-page)] text-[var(--text-primary)] flex flex-col overflow-hidden">

      {/* ── Workspace Header ── */}
      <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--card-border)', background: 'var(--bg-surface)', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <button onClick={() => setView('list')} className="p-1.5 hover:bg-[var(--bg-hover)] rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
          <ArrowLeft size={18} />
        </button>

        <input
          type="text"
          value={campaignName}
          onChange={e => setCampaignName(e.target.value)}
          className="bg-transparent text-lg font-bold text-[var(--text-primary)] border-none focus:outline-none focus:ring-1 focus:ring-white/20 rounded px-1 -ml-1"
          style={{ minWidth: 160, maxWidth: 280 }}
          placeholder="Campaign Name"
        />

        {/* Autosave indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginLeft: 4 }}>
          {isSaving ? (
            <><Loader2 size={11} className="animate-spin" /> Saving</>
          ) : lastSaved ? (
            <><CheckCircle2 size={11} style={{ color: '#4ade80' }} /> Saved {lastSaved.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</>
          ) : (
            <><Clock size={11} /> Unsaved</>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => setShowDomainHealth(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold border border-[var(--border)] rounded-lg text-emerald-400 hover:bg-[var(--bg-hover)] transition-colors">
            <Activity size={13} /> Domain Health
          </button>
          <button onClick={() => setShowSequenceGenerator(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold border border-[var(--border)] rounded-lg text-cyan-400 hover:bg-[var(--bg-hover)] transition-colors">
            <Zap size={13} /> AI Sequence
          </button>
          <button onClick={() => setShowTemplateLibrary(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold border border-[var(--border)] rounded-lg text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors">
            <FileText size={13} /> Templates
          </button>
          <button onClick={handleSaveAsTemplate} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold border border-[var(--border)] rounded-lg text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors">
            <Save size={13} /> Save as Template
          </button>
        </div>
      </div>

      {/* ── Bridge status strip ── */}
      <div style={{ padding: '4px 16px', borderBottom: '1px solid var(--card-border)', flexShrink: 0 }}>
        <BridgeStatus compact />
      </div>

      {/* ── Main workspace body ── */}
      <div className="flex-1 overflow-hidden flex" style={{ minHeight: 0 }}>

        {workspaceMode === 'compose' ? (
          // ──────────────────────────────────────────────────────────────────────
          // COMPOSE MODE: 60/40 split
          // ──────────────────────────────────────────────────────────────────────
          <>
            {/* LEFT: Email Composer (60%) */}
            <div style={{ flex: '0 0 60%', display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--card-border)', overflow: 'hidden' }}
              className="workspace-composer">
              <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }} className="custom-scrollbar">

                {/* FROM selector */}
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>From</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {accounts.length > 0 ? (
                      <select
                        value={senderAccountId || ''}
                        onChange={e => {
                          const acc = accounts.find(a => a.account_id === Number(e.target.value));
                          if (acc) { setSenderAccountId(acc.account_id); setFromEmail(acc.email_address); }
                        }}
                        style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', borderRadius: 6, padding: '8px 12px', fontSize: 14, color: 'var(--text-primary)', outline: 'none' }}>
                        <option value="">Select sending account…</option>
                        {accounts.map(acc => (
                          <option key={acc.account_id} value={acc.account_id}>{acc.email_address} ({acc.provider})</option>
                        ))}
                      </select>
                    ) : (
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', borderRadius: 6, padding: '8px 12px' }}>
                        <Mail size={14} style={{ color: 'var(--text-muted)' }} />
                        <span style={{ fontSize: 13, color: 'var(--text-muted)', flex: 1 }}>No accounts connected</span>
                        <button onClick={() => setShowConnectionWizard(true)} style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', background: 'var(--bg-hover)', border: '1px solid var(--border)', borderRadius: 4, padding: '4px 10px', cursor: 'pointer' }}>Connect</button>
                      </div>
                    )}
                  </div>
                </div>

                {/* SUBJECT */}
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Subject</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={e => setSubject(e.target.value.slice(0, 255))}
                    placeholder="Your subject line (use {{ variables }})"
                    maxLength={255}
                    style={{ width: '100%', background: 'var(--bg-surface)', border: '1px solid var(--card-border)', borderRadius: 6, padding: '8px 12px', fontSize: 14, color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box' }}
                  />
                </div>

                {/* BODY */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 280 }}>
                  <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Message</label>
                  <div style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--card-border)', borderRadius: 6, overflow: 'hidden', minHeight: 280 }}>
                    <RichTextComposer content={body} onChange={setBody} placeholder="Write your email here… use {{ variables }} for personalization" />
                  </div>
                </div>

                {/* DETECTED VARIABLES */}
                {detectedVariables.length > 0 && (
                  <div>
                    <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Detected Variables</label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {detectedVariables.map(v => (
                        <span key={v} style={{ fontSize: 11, fontWeight: 700, fontFamily: 'monospace', padding: '3px 8px', background: 'var(--bg-hover)', border: '1px solid var(--card-border)', borderRadius: 4, color: 'var(--text-primary)' }}>
                          {`{{ ${v} }}`}
                        </span>
                      ))}
                    </div>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, fontStyle: 'italic' }}>These will be filled with real recipient data when sent.</p>
                  </div>
                )}

                {/* SIGNATURE */}
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Signature</label>
                  <SignatureManager selectedSignatureId={signatureId} onSelectSignature={setSignatureId} />
                </div>
              </div>

              {/* ── Readiness + Send footer ── */}
              <div style={{ padding: '12px 20px', borderTop: '1px solid var(--card-border)', background: 'var(--bg-surface)', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {sendError && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-base)', border: '1px solid #f87171', padding: '10px 14px', borderRadius: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <AlertCircle size={16} color="#f87171" />
                      <span style={{ fontSize: 13, color: '#f87171', fontWeight: 600 }}>{sendError}</span>
                    </div>
                    <button onClick={() => setShowConnectionWizard(true)} style={{ fontSize: 12, fontWeight: 700, background: '#f87171', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: 4, cursor: 'pointer' }}>Fix Connection</button>
                  </div>
                )}
                
                <button
                  onClick={handleSend}
                  disabled={isSending || !localIsReady}
                  style={{
                    width: '100%',
                    padding: '11px',
                    borderRadius: 6,
                    fontSize: 14,
                    fontWeight: 800,
                    letterSpacing: '0.02em',
                    cursor: (isSending || !localIsReady) ? 'not-allowed' : 'pointer',
                    background: localIsReady ? 'var(--text-primary)' : 'var(--bg-hover)',
                    color: localIsReady ? 'var(--main-bg)' : 'var(--text-muted)',
                    border: '1px solid var(--card-border)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    transition: 'all 0.15s',
                  }}
                >
                  {isSending ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
                  {sendLabel}
                </button>
              </div>
            </div>

            {/* RIGHT: Recipients Panel (40%) */}
            <div style={{ flex: '0 0 40%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="workspace-recipients">

              {/* Recipients header */}
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>Recipients</span>
                  {validatedRecipients.recipients.length > 0 && (
                    <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', background: 'var(--bg-hover)', border: '1px solid var(--card-border)', borderRadius: 10, color: 'var(--text-primary)' }}>
                      {validatedRecipients.valid_count} valid
                    </span>
                  )}
                </div>
              </div>

              {/* Recipient count summary */}
              {validatedRecipients.recipients.length > 0 && (
                <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--card-border)', display: 'flex', gap: 16, flexShrink: 0 }}>
                  {[
                    { label: 'Total', value: validatedRecipients.recipients.length, color: 'var(--text-primary)' },
                    { label: 'Valid', value: validatedRecipients.valid_count, color: '#4ade80' },
                    { label: 'Invalid', value: validatedRecipients.recipients.filter(r => r.status !== 'valid').length, color: '#f87171' },
                  ].map(item => (
                    <div key={item.label} style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 18, fontWeight: 900, color: item.color, lineHeight: 1 }}>{item.value}</div>
                      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', marginTop: 2 }}>{item.label}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* DragDropRecipientBuilder */}
              <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
                <DragDropRecipientBuilder
                  recipients={validatedRecipients.recipients}
                  onChange={(newRecipients) => {
                    setValidatedRecipients({
                      recipients: newRecipients,
                      valid_count: newRecipients.filter(r => r.status === 'valid').length,
                    });
                    // Reset preflight when recipients change
                    setPreflightData(null);
                  }}
                  onValidate={async (emailsStr) => {
                    const emailsList = emailsStr.split(',').map(e => e.trim()).filter(Boolean);
                    if (emailsList.length === 0) return;
                    try {
                      const res = await api.post('/campaigns/validate-recipients', { emails: emailsList });
                      const statusMap = new Map();
                      (res.data.recipients || []).forEach(r => statusMap.set(r.email, r.status));
                      const updated = validatedRecipients.recipients.map(r =>
                        statusMap.has(r.email) ? { ...r, status: statusMap.get(r.email) } : r
                      );
                      setValidatedRecipients({ recipients: updated, valid_count: updated.filter(r => r.status === 'valid').length });
                      toast.success(`${res.data.valid_count || 0} valid recipients`);
                    } catch {
                      toast.error('Validation failed');
                    }
                  }}
                />
              </div>
            </div>
          </>
        ) : (
          // ──────────────────────────────────────────────────────────────────────
          // SENDING MODE: full-width live progress
          // ──────────────────────────────────────────────────────────────────────
          <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }} className="custom-scrollbar">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h2 style={{ fontWeight: 800, fontSize: 20, margin: 0 }}>Campaign Sending</h2>
                <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>{campaignName}</p>
              </div>
              <button
                onClick={() => setWorkspaceMode('compose')}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold border border-[var(--border)] rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors">
                <ArrowLeft size={13} /> Back to editor
              </button>
            </div>

            {activeCampaignId && (
              <>
                <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--card-border)', borderRadius: 6, overflow: 'hidden' }}>
                  <CampaignProgress campaignId={activeCampaignId} />
                </div>

              </>
            )}
          </div>
        )}
      </div>

      {/* ── Responsive styles ── */}
      <style>{`
        @media (max-width: 1023px) {
          .workspace-composer { flex: 1 1 auto !important; border-right: none !important; border-bottom: 1px solid var(--card-border); }
          .workspace-recipients { flex: 0 0 auto !important; max-height: 40vh; }
          .h-full > .flex-1.overflow-hidden.flex { flex-direction: column !important; }
        }
        @media (max-width: 767px) {
          .workspace-recipients { max-height: 32vh; }
        }
      `}</style>

      {/* ── Modals ── */}
      {showTemplateLibrary && (
        <TemplateLibraryModal isOpen onClose={() => setShowTemplateLibrary(false)} onImport={(t) => { handleTemplateImport(t); setShowTemplateLibrary(false); }} />
      )}
      {showSequenceGenerator && (
        <SequenceGeneratorModal
          isOpen
          onClose={() => setShowSequenceGenerator(false)}
          onApplyTouch={(touch) => {
            setSubject(touch.subject);
            setBody(touch.body);
            setShowSequenceGenerator(false);
          }}
        />
      )}
      {showDomainHealth && (
        <DomainHealthModal
          isOpen
          onClose={() => setShowDomainHealth(false)}
          initialDomain={fromEmail || 'talentops.ai'}
        />
      )}
      {showConnectionWizard && (
        <ConnectionWizard onClose={() => setShowConnectionWizard(false)} onSuccess={() => { setShowConnectionWizard(false); fetchAccounts(); }} />
      )}
      <PreflightSafetyModal
        isOpen={showSafetyModal}
        onClose={() => setShowSafetyModal(false)}
        campaignId={activeCampaignId}
        preflightData={safetyPreflightData}
        subject={subject}
        body={body}
        onConfirmLaunch={handleConfirmLaunch}
        isLaunching={isSending}
      />
      </div>
    </CampaignErrorBoundary>
  );
}

// ── Helper: StatusBadge ────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const map = {
    active: { bg: 'var(--card-border)', text: 'var(--text-primary)', dot: 'var(--text-primary)' },
    paused: { bg: '#3b2a0c', text: '#fcd34d', dot: '#f59e0b' },
    completed: { bg: '#0f3d24', text: '#86efac', dot: '#22c55e' },
    draft: { bg: 'transparent', text: 'var(--text-muted)', dot: '#6b7280', border: '1px solid var(--card-border)' },
    failed: { bg: 'rgba(239,68,68,0.1)', text: '#f87171', dot: '#ef4444', border: '1px solid rgba(239,68,68,0.3)' },
  };
  const s = map[status] || map.draft;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 999, fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', background: s.bg, color: s.text, border: s.border }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
      {status}
    </span>
  );
}
