import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Mail, Phone, ExternalLink, Building2, MapPin, Award,
  ShieldCheck, CheckCircle2, Copy, Check, Send, Sparkles,
  Calendar, Clock, User, ChevronRight, AlertTriangle, Wand2, RefreshCw, Users,
  PhoneCall, Hash, FileText
} from 'lucide-react';
import api from '../../services/api';
import toast from 'react-hot-toast';
import SourceProvenanceBadge from '../common/SourceProvenanceBadge';
import { classifyCandidateSource } from '../../utils/sourceProvenance';
import { useNavigate } from '@tanstack/react-router';

function ColleaguesSection({ recruiterId, company, onSelectRecruiter }) {
  const [colleagues, setColleagues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  React.useEffect(() => {
    if (!recruiterId || !isExpanded) return;
    let isMounted = true;
    setLoading(true);
    api.get(`/recruiters/${recruiterId}/colleagues?limit=10`)
      .then(res => {
        if (isMounted) setColleagues(res.data?.colleagues || []);
      })
      .catch(() => {
        if (isMounted) setColleagues([]);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => { isMounted = false; };
  }, [recruiterId, isExpanded]);

  return (
    <div
      className="p-4 rounded-xl space-y-3"
      style={{ background: 'var(--card-bg, #1B1F1C)', border: '1px solid var(--card-border, #343B35)' }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-white" />
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted, #a1a1aa)' }}>
            Company Colleagues
          </span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-white hover:text-white font-medium cursor-pointer"
        >
          {isExpanded ? 'Collapse' : 'Explore Peers'}
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-2 pt-2" style={{ borderTop: '1px solid var(--card-border, #27272a)' }}>
          {loading ? (
            <div className="text-xs py-2 flex items-center gap-2" style={{ color: 'var(--text-muted, #71717a)' }}>
              <RefreshCw className="w-3 h-3 animate-spin text-white" /> Finding colleagues at {company}...
            </div>
          ) : colleagues.length === 0 ? (
            <div className="text-xs py-1" style={{ color: 'var(--text-muted, #71717a)' }}>
              No other active colleagues found for this firm.
            </div>
          ) : (
            colleagues.map(colleague => (
              <div
                key={colleague.recruiter_id}
                onClick={() => onSelectRecruiter(colleague)}
                className="p-2.5 rounded-lg bg-[#202026] hover:bg-[#272730] border border-[#2d2d35] cursor-pointer transition-colors flex items-center justify-between group"
              >
                <div className="min-w-0 pr-2">
                  <div className="text-xs font-semibold text-white group-hover:text-white transition-colors truncate">
                    {colleague.recruiter_name}
                  </div>
                  <div className="text-[10px] text-[#a1a1aa] truncate">
                    {colleague.title || 'Recruiter'} {colleague.location ? `• ${colleague.location}` : ''}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white font-mono">
                    {colleague.quality_score || 85}%
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 text-[#71717a] group-hover:text-white" />
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function RecruiterProfileDrawer({
  recruiter: initialRecruiter,
  isOpen,
  onClose,
  onEnrollCampaign
}) {
  const [localRecruiter, setLocalRecruiter] = useState(null);
  const [copiedField, setCopiedField] = useState(null);
  const [isFixingEmail, setIsFixingEmail] = useState(false);
  const [isEnriching, setIsEnriching] = useState(false);
  const [showRawDetails, setShowRawDetails] = useState(false);
  const navigate = useNavigate();

  const handleOutreachCampaign = (r) => {
    if (onEnrollCampaign) {
      onEnrollCampaign(r);
      return;
    }
    const target = r || recruiter;
    if (!target) return;

    const emails = Array.from(new Set(allEmails.filter(e => e && e.includes('@') && !e.includes('@noemail') && !e.includes('@unknown'))));
    const candidateName = target.name || name || 'Candidate';
    const compName = target.company || company || '';
    const candTitle = target.title || target.specialization || title || '';

    const recipients = emails.length > 0
      ? emails.map(em => ({
          recruiter_id: target.recruiter_id || target.id || null,
          email: em.trim(),
          name: candidateName,
          company: compName,
          title: candTitle,
          state: target.state || '',
          status: 'valid'
        }))
      : [{
          recruiter_id: target.recruiter_id || target.id || null,
          email: target.email || '',
          name: candidateName,
          company: compName,
          title: candTitle,
          state: target.state || '',
          status: 'valid'
        }];

    const outreachPayload = {
      candidate: {
        id: target.recruiter_id || target.id,
        name: candidateName,
        company: compName,
        title: candTitle,
        emails: emails,
        phones: allPhones
      },
      recipients,
      campaignName: `Outreach to ${candidateName}`,
      subject: `Introduction // ${compName ? `${compName} & TalentOps` : 'Career Opportunity'}`
    };

    sessionStorage.setItem('talentops_pending_outreach', JSON.stringify(outreachPayload));
    sessionStorage.setItem('camp_view', '"workspace"');
    sessionStorage.setItem('camp_wsMode', '"compose"');
    sessionStorage.setItem('camp_activeId', 'null');

    window.dispatchEvent(new CustomEvent('talentops:open-outreach-campaign', { detail: outreachPayload }));
    if (onClose) onClose();
    navigate({ to: '/campaigns' });
  };

  // Auto-fetch full master record from API on drawer open to guarantee complete multi-phone/email hydration
  React.useEffect(() => {
    const targetId = initialRecruiter?.recruiter_id || initialRecruiter?.id;
    if (!isOpen || !targetId) {
      setLocalRecruiter(null);
      return;
    }
    let isMounted = true;
    api.get(`/recruiters/${targetId}`)
      .then(res => {
        if (isMounted && res.data) {
          setLocalRecruiter(res.data);
        }
      })
      .catch(err => {
        console.debug('Recruiter full profile fetch notice:', err);
      });
    return () => { isMounted = false; };
  }, [isOpen, initialRecruiter?.recruiter_id, initialRecruiter?.id]);

  const recruiter = localRecruiter || initialRecruiter;

  // ⚡ SILENT AUTONOMOUS BACKGROUND ENRICHMENT ON DRAWER OPEN
  React.useEffect(() => {
    if (!isOpen || !recruiter) return;
    let m = {};
    try {
      m = typeof recruiter.metadata_json === 'string' ? JSON.parse(recruiter.metadata_json || '{}') : (recruiter.metadata_json || {});
    } catch (e) {
      m = {};
    }

    const hasEnrichment = m.ats_system || (m.tech_stack && m.tech_stack.length > 0) || m.nsr_profile;
    if (!hasEnrichment && (recruiter.recruiter_id || recruiter.email) && !isEnriching) {
      setIsEnriching(true);
      api.post('/api/enrichment/enrich-profile', {
        recruiter_id: recruiter.recruiter_id,
        email: recruiter.email,
        name: recruiter.recruiter_name,
        company_name: recruiter.company_name || recruiter.company,
      })
      .then(res => {
        const enr = res.data?.enriched;
        if (!enr) return;
        const updatedMeta = {
          ...m,
          ats_system: enr.ats_system,
          crm_system: enr.crm_system,
          tech_stack: enr.tech_stack,
          detected_tools: enr.detected_tools,
          nsr_profile: enr.nsr_profile,
          avatar_url: enr.avatar_url,
          auto_enriched: true,
        };
        setLocalRecruiter(prev => ({
          ...(prev || recruiter),
          logo_url: enr.avatar_url || (prev || recruiter).logo_url,
          completeness_score: Math.min(100, ((prev || recruiter).completeness_score || 70) + (enr.score_boost || 15)),
          metadata_json: JSON.stringify(updatedMeta),
        }));
      })
      .catch(err => {
        console.debug('Autonomous background enrichment notice:', err);
      })
      .finally(() => {
        setIsEnriching(false);
      });
    }
  }, [isOpen, recruiter?.recruiter_id, recruiter?.email]);

  if (!isOpen || !recruiter) return null;

  const copyToClipboard = (text, fieldName) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    toast.success(`Copied ${fieldName} to clipboard!`);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const name = recruiter.recruiter_name || 'Recruiter Profile';
  const email = recruiter.email || '';
  const phone = recruiter.phone || '';
  const title = recruiter.title || recruiter.specialization || 'Talent Acquisition Specialist';
  const company = recruiter.company_name || recruiter.company || 'Direct Staffing Partner';
  const location = recruiter.location || recruiter.state || 'United States';
  const linkedin = recruiter.linkedin || recruiter.linkedin_url || '';
  const freeDoms = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'];
  const drawerEmailDom = recruiter.email && recruiter.email.includes('@') && !freeDoms.includes(recruiter.email.split('@')[1].trim().toLowerCase())
    ? recruiter.email.split('@')[1].trim().toLowerCase()
    : null;
  const companyDomain = (recruiter.company && recruiter.company.primary_domain) || recruiter.company_domain || recruiter.website || drawerEmailDom;
  const companyLogo = (recruiter.company && recruiter.company.logo_url) || recruiter.logo_url || (companyDomain ? `https://www.google.com/s2/favicons?domain=${companyDomain}&sz=128` : null);
  const logo = recruiter.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=18181b&color=ffffff&bold=true`;
  const seniority = recruiter.seniority_level || 'Specialist';
  const emailStatus = recruiter.email_status || 'verified';
  const confidence = recruiter.email_confidence || (emailStatus === 'verified' ? 95 : 75);
  const completeness = recruiter.completeness_score || 85;

  let meta = {};
  try {
    meta = typeof recruiter.metadata_json === 'string' ? JSON.parse(recruiter.metadata_json || '{}') : (recruiter.metadata_json || {});
  } catch (e) {
    meta = {};
  }
  const detectedTools = meta.detected_tools || [];
  const atsSystem = meta.ats_system;
  const crmSystem = meta.crm_system;
  const nsrProfile = meta.nsr_profile;
  const isCandidateBill = Boolean(
    name.toLowerCase().includes('bill') ||
    name.toLowerCase().includes('william') ||
    (recruiter.notes && recruiter.notes.toLowerCase().includes('bill'))
  );

  const handleAutoFixEmail = async () => {
    if (!recruiter.recruiter_id) return;
    setIsFixingEmail(true);
    try {
      const res = await api.post(`/recruiters/${recruiter.recruiter_id}/auto-fix-email`);
      const { repaired_email, method, confidence } = res.data;
      setLocalRecruiter({
        ...recruiter,
        email: repaired_email,
        email_status: 'verified',
        email_confidence: confidence || 95,
        is_deliverable: true
      });
      toast.success(`Repaired email to ${repaired_email} via ${method.replace(/_/g, ' ')}!`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No replacement email could be auto-synthesized');
    } finally {
      setIsFixingEmail(false);
    }
  };

  const getGradeBadge = (score) => {
    if (score >= 90) return { label: 'Grade A+', color: 'text-[#B8D5A0] bg-[#B8D5A0]/15 border-[#B8D5A0]/35' };
    if (score >= 75) return { label: 'Grade A', color: 'text-[#B8D5A0] bg-[#B8D5A0]/10 border-[#B8D5A0]/25' };
    if (score >= 60) return { label: 'Grade B', color: 'text-[#C4B5D9] bg-[#C4B5D9]/15 border-[#C4B5D9]/30' };
    return { label: 'Grade C', color: 'text-[#E6B875] bg-[#E6B875]/15 border-[#E6B875]/30' };
  };

  const grade = getGradeBadge(completeness);

  // Helper to parse loose lists, JSON strings, and arrays
  const parseList = (val) => {
    if (!val) return [];
    if (Array.isArray(val)) return val;
    if (typeof val === 'string') {
      const trimmed = val.trim();
      if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
        try {
          const parsed = JSON.parse(trimmed);
          if (Array.isArray(parsed)) return parsed;
        } catch (e) {}
      }
      return trimmed.split(/[,;\n|]+/).map(s => s.trim()).filter(Boolean);
    }
    return [];
  };

  // Extract all distinct phone numbers
  const extractDistinctPhones = () => {
    const raw = [
      recruiter.phone,
      recruiter.phone2,
      recruiter.phone3,
      recruiter.phone4,
      ...parseList(recruiter.all_phones),
      ...parseList(recruiter.alternate_phones),
      ...parseList(meta?.all_phones),
      ...parseList(meta?.phones),
    ];
    const seen = new Set();
    const result = [];
    for (const item of raw) {
      if (!item) continue;
      const str = String(item).replace(/[\[\]"']/g, '').trim();
      const digits = str.replace(/[^\d]/g, '');
      if (digits.length >= 7 && !seen.has(digits)) {
        seen.add(digits);
        result.push(str);
      }
    }
    return result;
  };

  // Extract all distinct emails
  const extractDistinctEmails = () => {
    const raw = [
      recruiter.email,
      recruiter.email2,
      recruiter.email3,
      recruiter.email4,
      ...parseList(recruiter.all_emails),
      ...parseList(recruiter.alternate_emails),
      ...parseList(meta?.all_emails),
      ...parseList(meta?.emails),
    ];
    const seen = new Set();
    const result = [];
    for (const item of raw) {
      if (!item) continue;
      const str = String(item).replace(/[\[\]"']/g, '').trim().toLowerCase();
      if (
        str.includes('@') &&
        !str.includes('missing.local') &&
        !str.endsWith('@noemail.talentops') &&
        !str.endsWith('@unknown.com') &&
        !seen.has(str)
      ) {
        seen.add(str);
        result.push(str);
      }
    }
    return result;
  };

  const allPhones = extractDistinctPhones();
  const allEmails = extractDistinctEmails();

  const getPhoneLabel = (ph, idx) => {
    const clean = ph.replace(/[^\d]/g, '');
    if (clean.startsWith('1800') || clean.startsWith('1888') || clean.startsWith('1877') || clean.startsWith('1866') ||
        clean.startsWith('800') || clean.startsWith('888') || clean.startsWith('877') || clean.startsWith('866')) {
      return 'Toll-Free / Corporate Line';
    }
    if (idx === 0) return 'Direct Phone / Primary';
    if (idx === 1) return 'Mobile / Secondary Line';
    if (idx === 2) return 'Office / Alternate Line';
    if (idx === 3) return 'Quaternary Contact';
    return `Line ${idx + 1}`;
  };

  const getEmailLabel = (em, idx) => {
    if (idx === 0) return 'Primary Corporate Email';
    if (idx === 1) return 'Secondary Email';
    return `Alternate Email ${idx + 1}`;
  };

  const isTeamsSource = Boolean(
    (recruiter.data_source && String(recruiter.data_source).toLowerCase().includes('teams')) ||
    (meta?.source && String(meta.source).toLowerCase().includes('teams')) ||
    (meta?.batch_id && String(meta.batch_id).includes('TEAMS'))
  );

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
        />

        {/* Slide-out Drawer: Wide Executive Side-Sheet (680px width) */}
        <div className="fixed inset-y-0 right-0 max-w-full flex pl-4 sm:pl-10 pointer-events-none">
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 220 }}
            className="w-screen max-w-2xl sm:w-[680px] shadow-2xl pointer-events-auto flex flex-col h-full overflow-hidden"
            style={{ background: 'var(--panel-bg, #1B1F1C)', borderLeft: '1px solid var(--card-border, #343B35)' }}
          >
            {/* Drawer Header */}
            <div
              className="p-6 relative"
              style={{ borderBottom: '1px solid var(--card-border, #343B35)', background: 'var(--panel-bg, #1B1F1C)' }}
            >
              <button
                onClick={onClose}
                className="absolute top-5 right-5 w-8 h-8 rounded-lg flex items-center justify-center transition-colors cursor-pointer hover:bg-white/10"
                style={{ color: 'var(--text-muted, #a1a1aa)' }}
                title="Close Drawer (Esc)"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-start gap-4 pr-10">
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center overflow-hidden p-1 flex-shrink-0 shadow-lg relative"
                  style={{ background: 'var(--bg-elevated, #242925)', border: '2px solid rgba(184, 213, 160, 0.4)' }}
                >
                  <img
                    src={logo}
                    alt={name}
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=18181b&color=ffffff&bold=true`;
                    }}
                    className="w-full h-full object-contain"
                  />
                  {companyLogo ? (
                    <div
                      className="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full bg-white flex items-center justify-center overflow-hidden p-0.5 border border-zinc-900 shadow-md"
                      title={company}
                    >
                      <img
                        src={companyLogo}
                        alt={company}
                        className="w-full h-full object-contain"
                        onError={(e) => { e.currentTarget.parentElement.style.display = 'none'; }}
                      />
                    </div>
                  ) : null}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border tracking-wide uppercase ${grade.color}`}>
                      {grade.label}
                    </span>
                    <span
                      className="px-2.5 py-0.5 rounded-full text-[10px] font-medium"
                      style={{ background: 'var(--card-bg, #18181c)', color: 'var(--text-secondary, #a1a1aa)', border: '1px solid var(--card-border, #27272a)' }}
                    >
                      {seniority}
                    </span>
                    <SourceProvenanceBadge
                      source={recruiter.data_source || recruiter.source || meta?.source || meta?.data_source}
                      size="xs"
                      detailed={true}
                    />
                  </div>
                  <h2 className="text-xl font-bold tracking-tight truncate m-0 leading-tight" style={{ color: 'var(--text-primary, #F1F0E8)' }}>
                    {name}
                  </h2>
                  <p className="text-sm truncate mt-1 flex items-center gap-1.5" style={{ color: 'var(--text-secondary, #a1a1aa)' }}>
                    {companyLogo ? (
                      <span className="w-4 h-4 rounded bg-white flex items-center justify-center overflow-hidden flex-shrink-0 p-0.5 border border-zinc-700">
                        <img
                          src={companyLogo}
                          alt={company}
                          className="w-full h-full object-contain"
                          onError={(e) => { e.currentTarget.parentElement.style.display = 'none'; }}
                        />
                      </span>
                    ) : (
                      <Building2 className="w-3.5 h-3.5 text-zinc-400" />
                    )}
                    <span className="font-semibold text-zinc-200">{company}</span>
                    {location && (
                      <span className="text-zinc-500">• {location}</span>
                    )}
                  </p>
                </div>
              </div>
            </div>

            {/* Drawer Scrollable Body */}
            <div className="p-6 overflow-y-auto space-y-6 custom-scrollbar flex-1">
              {/* Quick Actions Bar */}
              <div className="grid grid-cols-2 gap-3">
                {allEmails[0] ? (
                  <a
                    href={`mailto:${allEmails[0]}`}
                    className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold no-underline transition-all shadow-md cursor-pointer" style={{ background: 'var(--brand, #B8D5A0)', color: '#101211' }}
                  >
                    <Mail className="w-4 h-4" style={{ color: '#101211' }} /> Email Candidate
                  </a>
                ) : null}

                {linkedin ? (
                  <a
                    href={linkedin}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold no-underline transition-all shadow-md cursor-pointer" style={{ background: 'var(--bg-elevated, #242925)', border: '1px solid var(--card-border, #343B35)', color: 'var(--text-primary, #F1F0E8)' }}
                  >
                    <ExternalLink className="w-4 h-4" /> LinkedIn Profile
                  </a>
                ) : allPhones[0] ? (
                  <a
                    href={`tel:${allPhones[0]}`}
                    className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold no-underline transition-all shadow-md cursor-pointer" style={{ background: 'var(--bg-elevated, #242925)', border: '1px solid var(--card-border, #343B35)', color: 'var(--text-primary, #F1F0E8)' }}
                  >
                    <PhoneCall className="w-4 h-4 text-white" /> Call Direct Line
                  </a>
                ) : null}
              </div>

              {/* Teams Autonomous Stream Origin Dossier (if candidate was harvested from Teams chat) */}
              {isTeamsSource && (
                <div
                  className="p-4 rounded-xl space-y-2.5 border"
                  style={{ background: 'rgba(255, 255, 255, 0.03)', borderColor: 'rgba(255, 255, 255, 0.15)' }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-[#5059C9] flex items-center justify-center text-white font-bold text-xs">
                        T
                      </div>
                      <span className="text-xs font-bold uppercase tracking-wider text-white">
                        Microsoft Teams Group Chat Ingestion
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-white/10 text-white border border-white/20">
                      LIVE HARVEST
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] text-zinc-300">
                    <div className="p-2 rounded bg-zinc-900/80 border border-zinc-800">
                      <div className="text-[10px] uppercase text-zinc-500 font-medium">Chat Stream Funnel</div>
                      <div className="font-mono text-white font-semibold mt-0.5 truncate">
                        {meta?.batch_id || 'TEAMS_CTV_UPWARD_STREAM'}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-zinc-900/80 border border-zinc-800">
                      <div className="text-[10px] uppercase text-zinc-500 font-medium">Ingestion Timestamp</div>
                      <div className="font-mono text-white font-semibold mt-0.5">
                        {recruiter.created_at ? new Date(recruiter.created_at).toLocaleString() : 'Live Synchronized'}
                      </div>
                    </div>
                  </div>
                  <div className="text-[11px] text-zinc-400 flex items-center justify-between pt-0.5">
                    <span>Separated Contact Extracted:</span>
                    <strong className="text-white font-mono">{allPhones.length} Phone Numbers • {allEmails.length} Emails</strong>
                  </div>
                </div>
              )}

              {/* Deliverability & MailIntel Shield */}
              <div
                className="p-4 rounded-xl space-y-3"
                style={{ background: 'var(--card-bg, #1B1F1C)', border: '1px solid var(--card-border, #343B35)' }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-zinc-300">
                    <ShieldCheck className="w-4 h-4 text-white" /> MailIntel Deliverability
                  </span>
                  <span className="text-xs font-bold text-white font-mono">{confidence}% Safe Deliverability</span>
                </div>

                <div className="w-full h-1.5 rounded-full overflow-hidden bg-zinc-800">
                  <div
                    className="h-full rounded-full transition-all duration-500" style={{ background: 'var(--brand, #B8D5A0)' }}
                    style={{ width: `${Math.min(100, confidence)}%` }}
                  />
                </div>

                <div
                  className="flex items-center justify-between text-[11px] pt-1 border-t border-zinc-800"
                  style={{ color: 'var(--text-secondary, #a1a1aa)' }}
                >
                  <span>Mailbox Verification: <strong className="text-white capitalize font-mono">{emailStatus.replace('_', ' ')}</strong></span>
                  <span><strong className="text-white">{recruiter.email_generated ? '⚡ AI Inferred' : 'Verified Corporate Active'}</strong></span>
                </div>
              </div>

              {/* Complete Contact Coordinates (All Separated Phones & Emails) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider m-0 text-white">
                      Verified Contact Coordinates
                    </h3>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/10 text-white border border-white/20 font-mono">
                      {allPhones.length} Phones • {allEmails.length} Emails
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {recruiter.recruiter_id && (
                      <button
                        onClick={handleAutoFixEmail}
                        disabled={isFixingEmail}
                        className="text-[11px] font-semibold text-white hover:text-zinc-200 flex items-center gap-1 cursor-pointer bg-white/10 hover:bg-white/15 px-2.5 py-1 rounded-lg border border-white/20 transition-colors"
                      >
                        {isFixingEmail ? (
                          <>
                            <RefreshCw className="w-3 h-3 animate-spin" /> Repairing...
                          </>
                        ) : (
                          <>
                            <Wand2 className="w-3 h-3" /> Auto-Repair
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {/* Section A: Phone Numbers List */}
                <div className="space-y-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 pt-1">
                    <Phone className="w-3.5 h-3.5 text-white" />
                    <span>Telephone Numbers ({allPhones.length})</span>
                  </div>

                  {allPhones.length > 0 ? (
                    allPhones.map((ph, idx) => {
                      const label = getPhoneLabel(ph, idx);
                      const isTollFree = label.includes('Toll-Free');
                      return (
                        <div
                          key={`phone-${idx}`}
                          className="p-3.5 rounded-xl flex items-center justify-between group transition-colors border"
                          style={{
                            background: 'var(--card-bg, #101014)',
                            borderColor: idx === 0 ? 'rgba(255, 255, 255, 0.25)' : 'var(--card-border, #27272a)'
                          }}
                        >
                          <div className="flex items-center gap-3.5 min-w-0">
                            <div className="w-9 h-9 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center text-white flex-shrink-0">
                              <Phone className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-1.5 mb-0.5">
                                <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                                  idx === 0 ? 'bg-white text-black' : isTollFree ? 'bg-zinc-800 text-zinc-300' : 'bg-white/10 text-white'
                                }`}>
                                  {label}
                                </span>
                              </div>
                              <div className="text-sm font-mono font-semibold text-white tracking-tight truncate">
                                {ph}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-1 flex-shrink-0">
                            <a
                              href={`tel:${ph}`}
                              className="p-2 rounded-lg bg-white/5 hover:bg-white/15 text-white border border-white/10 transition-colors"
                              title={`Dial ${ph}`}
                            >
                              <PhoneCall className="w-3.5 h-3.5" />
                            </a>
                            <button
                              onClick={() => copyToClipboard(ph, label)}
                              className="p-2 rounded-lg bg-white/5 hover:bg-white/15 text-white border border-white/10 transition-colors cursor-pointer"
                              title="Copy Number"
                            >
                              {copiedField === label ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-3 rounded-xl bg-zinc-900/50 border border-zinc-800 text-xs text-zinc-500 italic">
                      No direct telephone lines on file.
                    </div>
                  )}
                </div>

                {/* Section B: Email Addresses List */}
                <div className="space-y-2 pt-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-white" />
                    <span>Email Addresses ({allEmails.length})</span>
                  </div>

                  {allEmails.length > 0 ? (
                    allEmails.map((em, idx) => {
                      const label = getEmailLabel(em, idx);
                      return (
                        <div
                          key={`email-${idx}`}
                          className="p-3.5 rounded-xl flex items-center justify-between group transition-colors border"
                          style={{
                            background: 'var(--card-bg, #101014)',
                            borderColor: idx === 0 ? 'rgba(255, 255, 255, 0.25)' : 'var(--card-border, #27272a)'
                          }}
                        >
                          <div className="flex items-center gap-3.5 min-w-0">
                            <div className="w-9 h-9 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center text-white flex-shrink-0">
                              <Mail className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-1.5 mb-0.5">
                                <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                                  idx === 0 ? 'bg-white text-black' : 'bg-white/10 text-white'
                                }`}>
                                  {label}
                                </span>
                              </div>
                              <div className="text-sm font-mono font-semibold text-white tracking-tight truncate">
                                {em}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-1 flex-shrink-0">
                            <a
                              href={`mailto:${em}`}
                              className="p-2 rounded-lg bg-white/5 hover:bg-white/15 text-white border border-white/10 transition-colors"
                              title={`Send email to ${em}`}
                            >
                              <Send className="w-3.5 h-3.5" />
                            </a>
                            <button
                              onClick={() => copyToClipboard(em, label)}
                              className="p-2 rounded-lg bg-white/5 hover:bg-white/15 text-white border border-white/10 transition-colors cursor-pointer"
                              title="Copy Email"
                            >
                              {copiedField === label ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-3 rounded-xl bg-zinc-900/50 border border-zinc-800 text-xs text-zinc-500 italic">
                      No email addresses discovered.
                    </div>
                  )}
                </div>

                {/* Section C: Location Coordinate */}
                <div
                  className="p-3 rounded-xl flex items-center justify-between border"
                  style={{ background: 'var(--card-bg, #101014)', borderColor: 'var(--card-border, #27272a)' }}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-white flex-shrink-0">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] text-zinc-400">Headquarters / Regional Market</div>
                      <div className="text-xs font-semibold text-white truncate">{location}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Enterprise Tech Stack & ATS Firmographics */}
              {(detectedTools.length > 0 || atsSystem || crmSystem) && (
                <div
                  className="p-4 rounded-xl space-y-2.5"
                  style={{ background: 'var(--card-bg, #1B1F1C)', border: '1px solid var(--card-border, #343B35)' }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-zinc-300">
                      <Building2 className="w-3.5 h-3.5 text-white" /> Company Tech Stack (DNS Verified)
                    </span>
                    {atsSystem && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/10 text-white border border-white/30">
                        {atsSystem} ATS
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {detectedTools.map((t, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-md text-[11px] font-medium border flex items-center gap-1.5 bg-white/5 border-white/15 text-white"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-white" />
                        {t.label || t.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Role & Specialization */}
              <div
                className="p-4 rounded-xl space-y-2"
                style={{ background: 'var(--card-bg, #1B1F1C)', border: '1px solid var(--card-border, #343B35)' }}
              >
                <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Recruiting Discipline & Title
                </div>
                <div className="text-sm font-semibold text-white leading-relaxed">{title}</div>
                {recruiter.specialization && (
                  <div
                    className="pt-2 text-xs border-t border-zinc-800 text-zinc-400 flex items-center justify-between"
                  >
                    <span>Specialization:</span>
                    <strong className="text-white">{recruiter.specialization}</strong>
                  </div>
                )}
              </div>

              {/* Raw Captured Extraction Context (Collapsible) */}
              {(recruiter.notes || recruiter.raw_data || meta?.raw_message || meta?.snippet) && (
                <div
                  className="p-4 rounded-xl space-y-2.5"
                  style={{ background: 'var(--card-bg, #1B1F1C)', border: '1px solid var(--card-border, #343B35)' }}
                >
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-zinc-300">
                      <FileText className="w-3.5 h-3.5 text-white" /> Harvest Notes & Raw Extraction
                    </div>
                    <button
                      onClick={() => setShowRawDetails(!showRawDetails)}
                      className="text-xs text-white hover:text-zinc-300 font-medium cursor-pointer"
                    >
                      {showRawDetails ? 'Hide' : 'View Raw'}
                    </button>
                  </div>

                  {recruiter.notes && (
                    <div className="text-xs text-zinc-300 leading-relaxed bg-zinc-900/60 p-2.5 rounded-lg border border-zinc-800">
                      {recruiter.notes}
                    </div>
                  )}

                  {showRawDetails && (
                    <pre className="text-[11px] font-mono text-zinc-400 bg-black/60 p-3 rounded-lg border border-zinc-800 overflow-x-auto whitespace-pre-wrap max-h-48 custom-scrollbar">
                      {typeof recruiter.raw_data === 'string' ? recruiter.raw_data : JSON.stringify(recruiter.raw_data || meta, null, 2)}
                    </pre>
                  )}
                </div>
              )}

              {/* Company Colleague Peer Graph */}
              <ColleaguesSection
                recruiterId={recruiter.recruiter_id}
                company={company}
                onSelectRecruiter={(colleague) => setLocalRecruiter(colleague)}
              />
            </div>

            {/* Drawer Footer */}
            <div
              className="p-4 flex items-center justify-between gap-3"
              style={{ borderTop: '1px solid var(--card-border, #343B35)', background: 'var(--panel-bg, #1B1F1C)' }}
            >
              <button
                onClick={() => {
                  const phoneStr = allPhones.length > 0 ? ` | Phones: ${allPhones.join(', ')}` : '';
                  copyToClipboard(`${name} <${allEmails.join(', ')}> - ${company}${phoneStr}`, 'Full Dossier');
                }}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold transition-colors flex items-center gap-2 cursor-pointer bg-white/10 hover:bg-white/15 text-white border border-white/20"
              >
                <Copy className="w-4 h-4" /> Copy Complete Profile
              </button>

              <button
                onClick={() => handleOutreachCampaign(recruiter)}
                className="px-5 py-2.5 rounded-xl text-xs font-bold bg-white text-black hover:bg-zinc-200 transition-colors flex items-center gap-2 shadow-md cursor-pointer"
              >
                <Send className="w-4 h-4 text-black" /> Add to Campaign
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
}
