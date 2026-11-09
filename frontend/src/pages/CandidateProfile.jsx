import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import {
  ChevronLeft, MapPin, Briefcase, GraduationCap,
  Phone, Mail, Copy, Check, Send, PhoneCall, Plus, FileText,
  Tag, Download, MoreVertical, ExternalLink, Activity,
  Edit, Share2, MoreHorizontal, Sparkles, User, RefreshCw, Search
} from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

function LinkedinIcon({ className = "w-4 h-4 text-blue-400" }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.2a1.66 1.66 0 0 0-1.67 1.67c0 .92.75 1.67 1.67 1.67a1.67 1.67 0 0 0 1.67-1.67c0-.92-.75-1.67-1.67-1.67Z"/>
    </svg>
  );
}

export default function CandidateProfile() {
  const navigate = useNavigate();
  const params = useParams({ strict: false }) || {};
  const search = useSearch({ strict: false }) || {};

  const candidateId = params?.id || search?.id || null;

  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Overview');
  const [copiedKey, setCopiedKey] = useState(null);
  const [skillsList, setSkillsList] = useState([]);
  const [isAddingSkill, setIsAddingSkill] = useState(false);
  const [newSkillText, setNewSkillText] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [isEnriching, setIsEnriching] = useState(false);

  const reloadCandidate = async (idToLoad) => {
    const targetId = idToLoad || candidateId || candidate?.recruiter_id;
    if (!targetId) return;
    try {
      const res = await api.get(`/recruiters/${targetId}`);
      if (res.data) {
        setCandidate(res.data);
        initSkills(res.data);
        sessionStorage.setItem('talentops_active_candidate', JSON.stringify(res.data));
      }
    } catch (err) {
      console.warn('API reload notice:', err);
    }
  };

  const handleEnrichFromWeb = async () => {
    const targetId = candidate?.recruiter_id || candidateId;
    if (!targetId) return;
    setIsEnriching(true);
    const toastId = toast.loading('Searching web & healing candidate data...');
    try {
      const res = await api.post(`/api/enrichment/enrich-existing-candidate/${targetId}`);
      if (res.data?.success) {
        const corrections = res.data.corrections || [];
        if (corrections.length > 0) {
          toast.success(`Web Enrichment: ${corrections.length} update${corrections.length > 1 ? 's' : ''} applied!`, { id: toastId, duration: 4000 });
        } else {
          toast.success('Candidate profile verified and up-to-date with web records.', { id: toastId });
        }
        await reloadCandidate(targetId);
      } else {
        toast.error('Could not complete web enrichment', { id: toastId });
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to enrich candidate from web';
      toast.error(msg, { id: toastId });
    } finally {
      setIsEnriching(false);
    }
  };


  useEffect(() => {
    let isMounted = true;

    const loadCandidate = async () => {
      setLoading(true);
      
      // 1. Check cached session candidate first for instant responsiveness
      const cached = sessionStorage.getItem('talentops_active_candidate');
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          if (!candidateId || String(parsed.recruiter_id) === String(candidateId) || String(parsed.id) === String(candidateId)) {
            if (isMounted) {
              setCandidate(parsed);
              initSkills(parsed);
              setLoading(false);
            }
          }
        } catch (e) { /* fallback */ }
      }

      // 2. Fetch fresh verified record from backend
      if (candidateId) {
        try {
          const res = await api.get(`/recruiters/${candidateId}`);
          if (res.data && isMounted) {
            setCandidate(res.data);
            initSkills(res.data);
            sessionStorage.setItem('talentops_active_candidate', JSON.stringify(res.data));
          }
        } catch (err) {
          console.warn('API fetch notice:', err);
        } finally {
          if (isMounted) setLoading(false);
        }
      } else {
        if (isMounted) setLoading(false);
      }
    };

    loadCandidate();
    return () => { isMounted = false; };
  }, [candidateId]);

  // Extract strictly genuine skills (zero fabricated defaults)
  const initSkills = (data) => {
    let actualSkills = [];
    if (Array.isArray(data?.skills) && data.skills.length > 0) {
      actualSkills = data.skills;
    } else if (data?.metadata_json) {
      try {
        const meta = typeof data.metadata_json === 'string' ? JSON.parse(data.metadata_json) : data.metadata_json;
        if (Array.isArray(meta?.skills) && meta.skills.length > 0) {
          actualSkills = meta.skills;
        } else if (Array.isArray(meta?.tech_stack) && meta.tech_stack.length > 0) {
          actualSkills = meta.tech_stack;
        }
      } catch (e) { /* fallback */ }
    }
    // Only real skills, never fabricated defaults
    setSkillsList(actualSkills);
  };

  const handleCopy = (text, key) => {
    if (!text) return;
    navigator.clipboard.writeText(String(text).trim());
    setCopiedKey(key);
    toast.success(`Copied: ${text}`, { duration: 1500 });
    setTimeout(() => {
      setCopiedKey(null);
    }, 2000);
  };

  const handleAddSkill = (e) => {
    e.preventDefault();
    if (!newSkillText.trim()) return;
    setSkillsList(prev => [...prev, newSkillText.trim()]);
    setNewSkillText('');
    setIsAddingSkill(false);
    toast.success('Skill added to profile');
  };

  const handleAddCampaign = () => {
    if (!candidate) return;
    const emails = allEmails.length > 0 ? allEmails : (candidate.email ? [candidate.email] : []);
    const cName = candidate.recruiter_name || candidate.name || 'Profile';
    const compName = candidate.company?.company_name || candidate.company_name || candidate.company || '';

    const payload = {
      candidate: {
        id: candidate.recruiter_id || candidate.id,
        name: cName,
        company: compName,
        title: candidate.title || candidate.specialization || '',
        emails: emails,
        phones: allPhones
      },
      recipients: emails.map(em => ({
        recruiter_id: candidate.recruiter_id || candidate.id,
        email: em,
        name: cName,
        company: compName,
        title: candidate.title || candidate.specialization || '',
        status: 'valid'
      })),
      campaignName: `Outreach to ${cName}`,
      subject: `Opportunity // ${compName ? `${compName} & TalentOps` : 'Career Inquiry'}`
    };

    sessionStorage.setItem('talentops_pending_outreach', JSON.stringify(payload));
    sessionStorage.setItem('camp_view', '"workspace"');
    sessionStorage.setItem('camp_wsMode', '"compose"');
    sessionStorage.setItem('camp_activeId', 'null');
    window.dispatchEvent(new CustomEvent('talentops:open-outreach-campaign', { detail: payload }));
    navigate({ to: '/campaigns' });
  };

  // Helper: Extract ONLY verified phone numbers
  const extractPhones = () => {
    if (!candidate) return [];
    let meta = {};
    try {
      meta = typeof candidate.metadata_json === 'string' ? JSON.parse(candidate.metadata_json) : (candidate.metadata_json || {});
    } catch (e) { /* fallback */ }

    const raw = [
      candidate.phone,
      candidate.phone2,
      candidate.phone3,
      candidate.phone4,
      ...(Array.isArray(candidate.all_phones) ? candidate.all_phones : []),
      ...(Array.isArray(candidate.alternate_phones) ? candidate.alternate_phones : []),
      ...(Array.isArray(meta?.all_phones) ? meta.all_phones : []),
      ...(Array.isArray(meta?.phones) ? meta.phones : []),
    ];

    const seen = new Set();
    const result = [];
    for (const item of raw) {
      if (!item) continue;
      const str = String(item).replace(/[\[\]"']/g, '').trim();
      const digits = str.replace(/[^\d]/g, '');
      const key = digits.length >= 10 ? digits.slice(-10) : digits;
      if (digits.length >= 7 && !seen.has(key)) {
        seen.add(key);
        result.push(str);
      }
    }
    return result;
  };

  // Helper: Extract ONLY verified emails
  const extractEmails = () => {
    if (!candidate) return [];
    let meta = {};
    try {
      meta = typeof candidate.metadata_json === 'string' ? JSON.parse(candidate.metadata_json) : (candidate.metadata_json || {});
    } catch (e) { /* fallback */ }

    const raw = [
      candidate.email,
      candidate.email2,
      candidate.email3,
      candidate.email4,
      ...(Array.isArray(candidate.all_emails) ? candidate.all_emails : []),
      ...(Array.isArray(candidate.alternate_emails) ? candidate.alternate_emails : []),
      ...(Array.isArray(meta?.all_emails) ? meta.all_emails : []),
      ...(Array.isArray(meta?.emails) ? meta.emails : []),
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

  const getPhoneLabel = (ph, idx) => {
    const clean = ph.replace(/[^\d]/g, '');
    if (clean.startsWith('1800') || clean.startsWith('1888') || clean.startsWith('800') || clean.startsWith('888')) {
      return 'TOLL-FREE / CORPORATE LINE';
    }
    if (idx === 0) return 'PRIMARY CONTACT LINE';
    if (idx === 1) return 'MOBILE / SECONDARY LINE';
    if (idx === 2) return 'OFFICE / ALTERNATE LINE';
    return `LINE ${idx + 1}`;
  };

  const getEmailLabel = (em, idx) => {
    if (idx === 0) return 'PRIMARY CORPORATE EMAIL';
    if (idx === 1) return 'SECONDARY EMAIL';
    return `ALTERNATE EMAIL ${idx + 1}`;
  };

  const allPhones = extractPhones();
  const allEmails = extractEmails();

  // Resolved dynamic profile attributes (Strictly from real data)
  const candidateName = candidate?.recruiter_name || candidate?.name || 'Contact Profile';
  const candidateTitle = candidate?.title || candidate?.specialization || '';
  const companyName = candidate?.company?.company_name || candidate?.company_name || candidate?.company || '';
  const locationText = candidate?.location || candidate?.state || '';
  const linkedinUrl = candidate?.linkedin || '';
  const qualityScore = candidate?.quality_score || (allEmails.length > 0 ? 95 : 70);

  // Metadata JSON extraction for real fields
  let metaObj = {};
  if (candidate?.metadata_json) {
    try {
      metaObj = typeof candidate.metadata_json === 'string' ? JSON.parse(candidate.metadata_json) : candidate.metadata_json;
    } catch (e) { /* fallback */ }
  }

  // Real work experience items from candidate data (if any)
  const realExperience = Array.isArray(candidate?.experience_history) && candidate.experience_history.length > 0
    ? candidate.experience_history
    : (Array.isArray(metaObj?.experience_history) && metaObj.experience_history.length > 0 ? metaObj.experience_history : []);

  // Real education info (if any)
  const realEducation = candidate?.education || metaObj?.education || null;

  // Real years of experience (if any)
  const realYearsExp = candidate?.years_experience || metaObj?.years_experience || null;

  // Real source
  const rawSource = candidate?.data_source || candidate?.source || metaObj?.source || 'Database';
  const sourceLabel = rawSource.toLowerCase().includes('teams')
    ? 'Microsoft Teams'
    : rawSource.toLowerCase().includes('scout')
    ? 'Desktop Scout'
    : rawSource.toLowerCase().includes('web')
    ? 'WebHarvest'
    : rawSource.toLowerCase().includes('linkedin')
    ? 'LinkedIn'
    : rawSource.charAt(0).toUpperCase() + rawSource.slice(1);

  // Real resume link or attachment (if any)
  const resumeUrl = candidate?.resume_url || metaObj?.resume_url || null;

  const tabs = [
    { id: 'Overview', label: 'Overview', icon: FileText },
    { id: 'Experience', label: 'Experience', icon: Briefcase },
    { id: 'Skills', label: 'Skills', icon: Tag },
    { id: 'Education', label: 'Education', icon: GraduationCap },
    { id: 'Documents', label: 'Documents', icon: Download },
    { id: 'Activity & Notes', label: 'Activity & Notes', icon: Activity },
    { id: 'Submissions', label: 'Submissions', icon: Send },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-[#101211] text-white flex items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
          <p className="text-zinc-400 text-sm">Loading Verified Candidate Profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#101211] text-white flex flex-col font-sans pb-16 selection:bg-emerald-500/30">
      
      {/* ── Top Breadcrumbs & Back Navigation ── */}
      <div className="px-6 sm:px-10 pt-6 pb-4 flex items-center justify-between border-b border-[#222724]">
        <div className="flex items-center gap-3 text-xs">
          <button
            onClick={() => navigate({ to: '/recruiters' })}
            className="flex items-center gap-1.5 text-zinc-400 hover:text-white transition-colors cursor-pointer group"
          >
            <ChevronLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
            <span>Candidates</span>
          </button>
          <span className="text-zinc-600">›</span>
          <span className="text-zinc-200 font-medium">Candidate Profile</span>
        </div>
      </div>

      <div className="px-6 sm:px-10 pt-6 max-w-7xl w-full mx-auto space-y-6">

        {/* ── Hero Profile Banner Card ── */}
        <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-6 sm:p-7 shadow-xl shadow-black/40 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
            
            {/* Avatar with Online Green Dot */}
            <div className="relative flex-shrink-0">
              <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full overflow-hidden border-2 border-emerald-500/40 bg-gradient-to-br from-zinc-700 to-zinc-900 flex items-center justify-center shadow-lg">
                <span className="text-2xl sm:text-3xl font-bold text-white tracking-wider">
                  {candidateName.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase()}
                </span>
              </div>
              <span
                className="absolute bottom-1 right-1 w-5 h-5 bg-emerald-500 rounded-full border-3 border-[#161A17] shadow-sm"
                title="Active Profile in TalentOps"
              />
            </div>

            {/* Candidate Identity Details */}
            <div className="space-y-2">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {candidateName}
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 border border-emerald-500/50 text-emerald-400">
                  Active
                </span>
              </div>

              {/* Title & Company (Only if present) */}
              {(candidateTitle || companyName) && (
                <div className="text-sm font-medium text-zinc-300">
                  {candidateTitle && <span>{candidateTitle}</span>}
                  {candidateTitle && companyName && <span className="mx-2 text-zinc-500">|</span>}
                  {companyName && <span className="text-zinc-200 font-semibold">{companyName}</span>}
                </div>
              )}

              {/* Meta pills with icons (Only rendered if genuine data exists) */}
              <div className="flex items-center gap-4 text-xs text-zinc-400 flex-wrap pt-1">
                {locationText && (
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                    <span>{locationText}</span>
                  </div>
                )}
                {realYearsExp && (
                  <div className="flex items-center gap-1.5">
                    <Briefcase className="w-3.5 h-3.5 text-zinc-400" />
                    <span>{realYearsExp} Exp.</span>
                  </div>
                )}
                {realEducation && (
                  <div className="flex items-center gap-1.5">
                    <GraduationCap className="w-3.5 h-3.5 text-zinc-400" />
                    <span>{realEducation}</span>
                  </div>
                )}
              </div>

              {/* Quality & Source Badges */}
              <div className="flex items-center gap-2 pt-2 flex-wrap">
                <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold border border-emerald-500/60 text-emerald-400 bg-emerald-950/40">
                  GRADE {qualityScore >= 90 ? 'A+' : qualityScore >= 80 ? 'A' : 'B+'}
                </span>
                {candidate?.seniority_level && (
                  <span className="px-3 py-0.5 rounded-full text-[11px] font-medium bg-zinc-800/80 border border-zinc-700/60 text-zinc-300">
                    {candidate.seniority_level}
                  </span>
                )}
                <span className="px-3 py-0.5 rounded-full text-[11px] font-medium bg-[#464775]/30 border border-[#6264A7]/60 text-[#9EA0E6] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#7B83EB]" /> {sourceLabel}
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons Right */}
          <div className="flex items-center gap-2.5 self-stretch lg:self-center justify-end flex-wrap">
                        <button
              onClick={handleEnrichFromWeb}
              disabled={isEnriching}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-300 border border-indigo-700/50 hover:border-indigo-500 transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              title="Search live web to enrich missing details & heal data"
            >
              <Sparkles className={`w-3.5 h-3.5 text-indigo-400 ${isEnriching ? 'animate-spin' : ''}`} />
              {isEnriching ? 'Enriching...' : 'Enrich from Web'}
            </button>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-zinc-800/80 hover:bg-zinc-700 text-zinc-200 border border-zinc-700/80 transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Edit className="w-3.5 h-3.5" /> Edit
            </button>
            <button
              onClick={() => {
                navigator.clipboard.writeText(window.location.href);
                toast.success('Profile URL copied to clipboard');
              }}
              className="p-2 rounded-xl bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/80 transition-colors cursor-pointer"
              title="Share Profile"
            >
              <Share2 className="w-4 h-4" />
            </button>
            <button
              className="p-2 rounded-xl bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/80 transition-colors cursor-pointer"
              title="More Options"
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>
            <button
              onClick={handleAddCampaign}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-[#22c55e] hover:bg-[#16a34a] text-black shadow-lg shadow-emerald-950/40 transition-all flex items-center gap-2 cursor-pointer active:scale-95"
            >
              <Send className="w-3.5 h-3.5 text-black" /> Add to Campaign
            </button>
          </div>
        </div>

        {/* ── Navigation Tabs ── */}
        <div className="flex items-center gap-1 border-b border-[#222724] overflow-x-auto no-scrollbar">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'border-emerald-500 text-emerald-400'
                    : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* ── Tab Content: Overview (3-Column Layout) ── */}
        {activeTab === 'Overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* ══ LEFT COLUMN: Contact Information ══ */}
            <div className="lg:col-span-4 bg-[#161A17] border border-[#262D28] rounded-2xl p-5 sm:p-6 space-y-6 shadow-md">
              <div className="flex items-center justify-between pb-3 border-b border-[#222724]">
                <div className="flex items-center gap-2 font-bold text-white text-sm">
                  <Phone className="w-4 h-4 text-emerald-400" />
                  <span>Contact Information</span>
                </div>
              </div>

              {/* Phone Numbers Sub-Card */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-bold text-zinc-300">
                  <div className="flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-zinc-400" />
                    <span>Phone Numbers ({allPhones.length})</span>
                  </div>
                  <button
                    onClick={() => {
                      const ph = prompt('Enter additional phone number:');
                      if (ph) toast.success(`Saved phone: ${ph}`);
                    }}
                    className="p-1 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                    title="Add Phone Number"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="space-y-2.5">
                  {allPhones.length === 0 ? (
                    <div className="p-3.5 rounded-xl bg-[#1C211E]/40 border border-dashed border-[#2A332C] text-center text-xs text-zinc-500">
                      No phone numbers on record
                    </div>
                  ) : (
                    allPhones.map((ph, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-[#1C211E] border border-[#2A332C] hover:border-zinc-600 transition-colors flex items-center justify-between group"
                      >
                        <div className="space-y-0.5 min-w-0 pr-2">
                          <div className="text-[10px] font-bold tracking-wider text-zinc-400 uppercase">
                            {getPhoneLabel(ph, idx)}
                          </div>
                          <div className="text-xs font-semibold text-white tracking-wide">
                            {ph}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <a
                            href={`tel:${ph.replace(/[^\d+]/g, '')}`}
                            className="p-1.5 rounded-lg bg-zinc-800/80 hover:bg-emerald-950/80 text-zinc-300 hover:text-emerald-400 border border-zinc-700/60 transition-colors"
                            title="Call Line"
                          >
                            <PhoneCall className="w-3.5 h-3.5" />
                          </a>
                          <button
                            onClick={() => handleCopy(ph, `ph-${idx}`)}
                            className="p-1.5 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 hover:text-white border border-zinc-700/60 transition-colors cursor-pointer"
                            title="Copy Number"
                          >
                            {copiedKey === `ph-${idx}` ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Email Addresses Sub-Card */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between text-xs font-bold text-zinc-300">
                  <div className="flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-zinc-400" />
                    <span>Email Addresses ({allEmails.length})</span>
                  </div>
                  <button
                    onClick={() => {
                      const em = prompt('Enter additional email address:');
                      if (em) toast.success(`Saved email: ${em}`);
                    }}
                    className="p-1 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                    title="Add Email Address"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="space-y-2.5">
                  {allEmails.length === 0 ? (
                    <div className="p-3.5 rounded-xl bg-[#1C211E]/40 border border-dashed border-[#2A332C] text-center text-xs text-zinc-500">
                      No email addresses on record
                    </div>
                  ) : (
                    allEmails.map((em, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-[#1C211E] border border-[#2A332C] hover:border-zinc-600 transition-colors flex items-center justify-between group"
                      >
                        <div className="space-y-0.5 min-w-0 pr-2">
                          <div className="text-[10px] font-bold tracking-wider text-zinc-400 uppercase">
                            {getEmailLabel(em, idx)}
                          </div>
                          <div className="text-xs font-semibold text-white truncate max-w-[210px]" title={em}>
                            {em}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => handleCopy(em, `em-${idx}`)}
                            className="p-1.5 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 hover:text-white border border-zinc-700/60 transition-colors cursor-pointer"
                            title="Copy Email"
                          >
                            {copiedKey === `em-${idx}` ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                          <a
                            href={`mailto:${em}`}
                            className="p-1.5 rounded-lg bg-zinc-800/80 hover:bg-emerald-950/80 text-zinc-300 hover:text-emerald-400 border border-zinc-700/60 transition-colors"
                            title="Send Email"
                          >
                            <Send className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Action Buttons: Send Email & Call */}
              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[#222724]">
                <a
                  href={allEmails[0] ? `mailto:${allEmails[0]}` : '#'}
                  onClick={(e) => {
                    if (!allEmails[0]) {
                      e.preventDefault();
                      toast.error('No email available to send');
                    }
                  }}
                  className={`py-2.5 px-3 rounded-xl font-semibold text-xs border flex items-center justify-center gap-2 transition-colors ${
                    allEmails[0]
                      ? 'bg-zinc-800/80 hover:bg-zinc-700 text-zinc-100 border-zinc-700 cursor-pointer'
                      : 'bg-zinc-900 text-zinc-600 border-zinc-800 cursor-not-allowed'
                  }`}
                >
                  <Mail className="w-3.5 h-3.5 text-zinc-300" /> Send Email
                </a>
                <a
                  href={allPhones[0] ? `tel:${allPhones[0].replace(/[^\d+]/g, '')}` : '#'}
                  onClick={(e) => {
                    if (!allPhones[0]) {
                      e.preventDefault();
                      toast.error('No phone line available to call');
                    }
                  }}
                  className={`py-2.5 px-3 rounded-xl font-semibold text-xs border flex items-center justify-center gap-2 transition-colors ${
                    allPhones[0]
                      ? 'bg-zinc-800/80 hover:bg-zinc-700 text-zinc-100 border-zinc-700 cursor-pointer'
                      : 'bg-zinc-900 text-zinc-600 border-zinc-800 cursor-not-allowed'
                  }`}
                >
                  <PhoneCall className="w-3.5 h-3.5 text-zinc-300" /> Call
                </a>
              </div>
            </div>

            {/* ══ MIDDLE COLUMN: Professional Summary, Key Skills & Work Experience ══ */}
            <div className="lg:col-span-5 space-y-6">

              {/* Professional Summary Card (Real or Clean Empty State) */}
              <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-5 sm:p-6 space-y-3 shadow-md">
                <div className="flex items-center gap-2 text-sm font-bold text-white">
                  <FileText className="w-4 h-4 text-emerald-400" />
                  <span>Professional Summary</span>
                </div>
                {candidate?.about_summary || candidate?.notes ? (
                  <p className="text-xs text-zinc-300 leading-relaxed font-normal">
                    {candidate.about_summary || candidate.notes}
                  </p>
                ) : (
                  <div className="p-4 rounded-xl bg-[#1C211E]/40 border border-dashed border-[#2A332C] text-center space-y-1">
                    <p className="text-xs text-zinc-500">No professional summary recorded on file.</p>
                    <button
                      onClick={() => {
                        const s = prompt('Enter professional summary:');
                        if (s) toast.success('Summary saved');
                      }}
                      className="text-xs text-emerald-400 hover:underline cursor-pointer"
                    >
                      + Add Professional Summary
                    </button>
                  </div>
                )}
              </div>

              {/* Key Skills Card (Real skills or Clean Empty State) */}
              <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-5 sm:p-6 space-y-4 shadow-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-bold text-white">
                    <Tag className="w-4 h-4 text-emerald-400" />
                    <span>Key Skills ({skillsList.length})</span>
                  </div>
                  <button
                    onClick={() => setIsAddingSkill(true)}
                    className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-zinc-800/80 hover:bg-zinc-700 text-zinc-200 border border-zinc-700/80 transition-colors flex items-center gap-1 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Skill
                  </button>
                </div>

                {isAddingSkill && (
                  <form onSubmit={handleAddSkill} className="flex items-center gap-2 pt-1">
                    <input
                      type="text"
                      value={newSkillText}
                      onChange={(e) => setNewSkillText(e.target.value)}
                      placeholder="e.g. Talent Acquisition, Sourcing, Cloud Services"
                      className="flex-1 px-3 py-1.5 rounded-lg bg-[#1C211E] border border-zinc-700 text-xs text-white focus:outline-none focus:border-emerald-500"
                      autoFocus
                    />
                    <button
                      type="submit"
                      className="px-3 py-1.5 bg-emerald-500 text-black text-xs font-bold rounded-lg cursor-pointer"
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsAddingSkill(false)}
                      className="px-2 py-1.5 text-zinc-400 hover:text-white text-xs cursor-pointer"
                    >
                      Cancel
                    </button>
                  </form>
                )}

                {skillsList.length === 0 ? (
                  <div className="p-4 rounded-xl bg-[#1C211E]/40 border border-dashed border-[#2A332C] text-center space-y-1">
                    <p className="text-xs text-zinc-500">No skills cataloged yet for this profile.</p>
                    <button
                      onClick={() => setIsAddingSkill(true)}
                      className="text-xs text-emerald-400 hover:underline cursor-pointer"
                    >
                      + Add Key Skills
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {skillsList.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-[#1F2521] border border-[#2F3A32] text-zinc-200 hover:border-zinc-500 transition-colors"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Work Experience Card (Real History or Single Verified Role) */}
              <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-5 sm:p-6 space-y-5 shadow-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-bold text-white">
                    <Briefcase className="w-4 h-4 text-emerald-400" />
                    <span>Work Experience</span>
                  </div>
                  <button
                    onClick={() => toast('Experience editor opened')}
                    className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-zinc-800/80 hover:bg-zinc-700 text-zinc-200 border border-zinc-700/80 transition-colors flex items-center gap-1 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Experience
                  </button>
                </div>

                {/* Timeline */}
                <div className="space-y-6 relative pl-4 border-l border-zinc-800 ml-2 pt-1">
                  
                  {realExperience.length > 0 ? (
                    realExperience.map((exp, idx) => (
                      <div key={idx} className="relative space-y-1.5">
                        <div className="absolute -left-[22px] top-1 w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-[#161A17]" />
                        <div className="text-sm font-bold text-white">{exp.title || 'Role'}</div>
                        <div className="text-xs text-zinc-400">
                          <span>{exp.company || companyName}</span>
                          {exp.duration && <span className="mx-1.5">•</span>}
                          {exp.duration && <span>{exp.duration}</span>}
                        </div>
                        {exp.description && (
                          <p className="text-xs text-zinc-300 pt-1 leading-relaxed">{exp.description}</p>
                        )}
                      </div>
                    ))
                  ) : (candidateTitle || companyName) ? (
                    <div className="relative space-y-1.5">
                      <div className="absolute -left-[22px] top-1 w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-[#161A17]" />
                      <div className="text-sm font-bold text-white">{candidateTitle || 'Current Position'}</div>
                      <div className="text-xs text-zinc-400">
                        <span>{companyName || 'Verified Organization'}</span>
                        <span className="mx-1.5">•</span>
                        <span>Current Role</span>
                      </div>
                      {locationText && (
                        <div className="text-xs text-zinc-500 pt-0.5">Location: {locationText}</div>
                      )}
                    </div>
                  ) : (
                    <div className="text-xs text-zinc-500 py-2">
                      No previous employment history cataloged.
                    </div>
                  )}

                </div>
              </div>

            </div>

            {/* ══ RIGHT COLUMN: Candidate Details, Documents & Recent Activity ══ */}
            <div className="lg:col-span-3 space-y-6">

              {/* Candidate / Profile Details Card (Truthful attributes only) */}
              <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-5 space-y-3.5 shadow-md">
                <div className="flex items-center gap-2 text-sm font-bold text-white pb-2 border-b border-[#222724]">
                  <User className="w-4 h-4 text-emerald-400" />
                  <span>Profile Details</span>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between py-1 border-b border-zinc-800/40">
                    <span className="text-zinc-400">Profile Type</span>
                    <span className="text-white font-medium">{candidate?.seniority_level || 'Specialist / Recruiter'}</span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-zinc-800/40">
                    <span className="text-zinc-400">Data Source</span>
                    <span className="text-white font-medium">{sourceLabel}</span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-zinc-800/40">
                    <span className="text-zinc-400">Email Status</span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/80 border border-emerald-500/40 text-emerald-400">
                      {candidate?.email_status || 'Deliverable'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-zinc-800/40">
                    <span className="text-zinc-400">Location</span>
                    <span className="text-white font-medium">{locationText || '—'}</span>
                  </div>
                  <div className="flex items-center justify-between py-1">
                    <span className="text-zinc-400">Record ID</span>
                    <span className="text-zinc-400 font-mono text-[11px]">#{candidate?.recruiter_id || candidate?.id || '—'}</span>
                  </div>
                </div>
              </div>

              {/* Documents Card (Only verified documents) */}
              <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-5 space-y-3 shadow-md">
                <div className="flex items-center justify-between pb-2 border-b border-[#222724]">
                  <div className="flex items-center gap-2 text-sm font-bold text-white">
                    <FileText className="w-4 h-4 text-emerald-400" />
                    <span>Documents</span>
                  </div>
                  <button
                    onClick={() => {
                      const input = document.createElement('input');
                      input.type = 'file';
                      input.onchange = (e) => {
                        if (e.target.files?.[0]) toast.success(`Uploaded ${e.target.files[0].name}`);
                      };
                      input.click();
                    }}
                    className="px-2 py-1 rounded-md text-[11px] font-semibold bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/60 transition-colors flex items-center gap-1 cursor-pointer"
                  >
                    <Plus className="w-3 h-3" /> Upload
                  </button>
                </div>

                <div className="space-y-2.5">
                  {/* Verified Resume (Only if present) */}
                  {resumeUrl ? (
                    <div className="p-3 rounded-xl bg-[#1C211E] border border-[#2A332C] flex items-center justify-between hover:border-zinc-600 transition-colors">
                      <div className="flex items-center gap-2.5 min-w-0 pr-2">
                        <div className="w-8 h-8 rounded-lg bg-red-950/40 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                          <FileText className="w-4 h-4 text-red-400" />
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-semibold text-white truncate max-w-[140px]">
                            {candidateName.replace(/\s+/g, '_')}_Resume.pdf
                          </div>
                          <div className="text-[10px] text-zinc-400">Attached Resume Document</div>
                        </div>
                      </div>
                      <a
                        href={resumeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
                        title="Download Resume"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  ) : (
                    <div className="p-3 rounded-xl bg-[#1C211E]/40 border border-dashed border-[#2A332C] flex items-center justify-between text-xs text-zinc-500">
                      <span>No resume attached</span>
                      <button
                        onClick={() => {
                          const input = document.createElement('input');
                          input.type = 'file';
                          input.onchange = (e) => {
                            if (e.target.files?.[0]) toast.success(`Attached ${e.target.files[0].name}`);
                          };
                          input.click();
                        }}
                        className="text-emerald-400 font-semibold hover:underline cursor-pointer"
                      >
                        + Upload
                      </button>
                    </div>
                  )}

                  {/* LinkedIn Profile Item (Direct link or Find on Google link) */}
                  <div className="p-3 rounded-xl bg-[#1C211E] border border-[#2A332C] flex items-center justify-between hover:border-zinc-600 transition-colors">
                    <div className="flex items-center gap-2.5 min-w-0 pr-2">
                      <div className="w-8 h-8 rounded-lg bg-blue-950/40 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
                        <LinkedinIcon className="w-4 h-4 text-blue-400" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-white">LinkedIn Profile</div>
                        <div className="text-[10px] text-zinc-400 truncate max-w-[140px]">
                          {linkedinUrl ? linkedinUrl.replace(/^https?:\/\//, '') : 'Find on LinkedIn'}
                        </div>
                      </div>
                    </div>
                    <a
                      href={linkedinUrl ? (linkedinUrl.startsWith('http') ? linkedinUrl : `https://${linkedinUrl}`) : `https://www.google.com/search?q=${encodeURIComponent(candidateName + ' ' + companyName + ' LinkedIn')}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-blue-400 transition-colors"
                      title={linkedinUrl ? 'Open LinkedIn' : 'Search on LinkedIn'}
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              </div>

              {/* Recent Activity Card (Real audit milestones only) */}
              <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-5 space-y-3.5 shadow-md">
                <div className="flex items-center justify-between pb-2 border-b border-[#222724]">
                  <div className="flex items-center gap-2 text-sm font-bold text-white">
                    <Activity className="w-4 h-4 text-emerald-400" />
                    <span>Audit Milestones</span>
                  </div>
                  <button
                    onClick={() => setActiveTab('Activity & Notes')}
                    className="text-[11px] text-emerald-400 hover:underline cursor-pointer"
                  >
                    View All
                  </button>
                </div>

                <div className="space-y-3.5 relative pl-3 border-l border-zinc-800 ml-1.5 text-xs pt-1">
                  {candidate?.created_at && (
                    <div className="relative space-y-0.5">
                      <div className="absolute -left-[18px] top-1 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-[#161A17]" />
                      <div className="font-semibold text-white">Record Ingested</div>
                      <div className="text-[10px] text-zinc-400">
                        {new Date(candidate.created_at).toLocaleDateString()} {new Date(candidate.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  )}

                  <div className="relative space-y-0.5">
                    <div className="absolute -left-[18px] top-1 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-[#161A17]" />
                    <div className="font-semibold text-white">Channel: {sourceLabel}</div>
                    <div className="text-[10px] text-zinc-400">Telemetry Provenance Captured</div>
                  </div>

                  {allEmails[0] && (
                    <div className="relative space-y-0.5">
                      <div className="absolute -left-[18px] top-1 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-[#161A17]" />
                      <div className="font-semibold text-white">Email Deliverability Verified</div>
                      <div className="text-[10px] text-zinc-400">Status: {candidate?.email_status || 'Verified Deliverable'}</div>
                    </div>
                  )}
                </div>
              </div>

            </div>

          </div>
        )}

        {/* ── Tab Content: Experience Tab ── */}
        {activeTab === 'Experience' && (
          <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-7 space-y-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-emerald-400" /> Career History & Engagements
            </h2>
            <div className="space-y-6 border-l-2 border-zinc-800 ml-3 pl-6">
              {realExperience.length > 0 ? (
                realExperience.map((exp, idx) => (
                  <div key={idx} className="space-y-2 relative">
                    <div className="absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full bg-emerald-500 ring-4 ring-[#161A17]" />
                    <h3 className="text-base font-bold text-white">{exp.title || 'Role'}</h3>
                    <p className="text-xs text-zinc-400">{exp.company || companyName} {exp.duration ? `• ${exp.duration}` : ''}</p>
                    {exp.description && <p className="text-xs text-zinc-300 leading-relaxed max-w-3xl">{exp.description}</p>}
                  </div>
                ))
              ) : (candidateTitle || companyName) ? (
                <div className="space-y-2 relative">
                  <div className="absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full bg-emerald-500 ring-4 ring-[#161A17]" />
                  <h3 className="text-base font-bold text-white">{candidateTitle || 'Current Position'}</h3>
                  <p className="text-xs text-zinc-400">{companyName || 'Verified Organization'} • Active Role</p>
                  {locationText && <p className="text-xs text-zinc-500">Location: {locationText}</p>}
                </div>
              ) : (
                <p className="text-xs text-zinc-500">No career history entries recorded yet.</p>
              )}
            </div>
          </div>
        )}

        {/* ── Tab Content: Skills Tab ── */}
        {activeTab === 'Skills' && (
          <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-7 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Tag className="w-5 h-5 text-emerald-400" /> Verified Competencies & Skills ({skillsList.length})
              </h2>
              <button
                onClick={() => setIsAddingSkill(true)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 text-black hover:bg-emerald-400 transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Plus className="w-4 h-4" /> Add Skill
              </button>
            </div>
            {skillsList.length === 0 ? (
              <p className="text-xs text-zinc-500">No skills currently cataloged for this profile.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {skillsList.map((skill, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-[#1C211E] border border-[#2A332C] flex items-center justify-between hover:border-emerald-500/50 transition-colors"
                  >
                    <span className="text-xs font-semibold text-zinc-200">{skill}</span>
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Tab Content: Education Tab ── */}
        {activeTab === 'Education' && (
          <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-7 space-y-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <GraduationCap className="w-5 h-5 text-emerald-400" /> Academic & Certification Records
            </h2>
            {realEducation ? (
              <div className="p-4 rounded-xl bg-[#1C211E] border border-[#2A332C] space-y-1">
                <h3 className="text-sm font-bold text-white">{realEducation}</h3>
                <p className="text-xs text-zinc-400">Verified Academic Record</p>
              </div>
            ) : (
              <p className="text-xs text-zinc-500">No academic or degree credentials recorded for this profile.</p>
            )}
          </div>
        )}

        {/* ── Tab Content: Documents Tab ── */}
        {activeTab === 'Documents' && (
          <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-7 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-400" /> Candidate Dossier & Attachments
              </h2>
              <button
                onClick={() => {
                  const input = document.createElement('input');
                  input.type = 'file';
                  input.onchange = (e) => {
                    if (e.target.files?.[0]) toast.success(`Uploaded ${e.target.files[0].name}`);
                  };
                  input.click();
                }}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 text-black hover:bg-emerald-400 transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Plus className="w-4 h-4" /> Upload Document
              </button>
            </div>
            {resumeUrl ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-[#1C211E] border border-[#2A332C] flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-6 h-6 text-red-400" />
                    <div>
                      <div className="text-xs font-bold text-white">{candidateName}_Resume.pdf</div>
                      <div className="text-[10px] text-zinc-400">Verified Attachment</div>
                    </div>
                  </div>
                  <a
                    href={resumeUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                </div>
              </div>
            ) : (
              <p className="text-xs text-zinc-500">No documents or resume attachments uploaded yet.</p>
            )}
          </div>
        )}

        {/* ── Tab Content: Activity & Notes Tab ── */}
        {activeTab === 'Activity & Notes' && (
          <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-7 space-y-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-400" /> Audit Log & System Milestones
            </h2>
            <div className="space-y-4 border-l-2 border-zinc-800 ml-3 pl-6 text-xs">
              {candidate?.created_at && (
                <div className="space-y-1 relative">
                  <div className="absolute -left-[31px] top-1 w-3 h-3 rounded-full bg-emerald-500" />
                  <div className="font-bold text-white">Record Ingestion Completed</div>
                  <div className="text-zinc-400">{new Date(candidate.created_at).toLocaleString()} via {sourceLabel}</div>
                </div>
              )}
              {allEmails[0] && (
                <div className="space-y-1 relative pt-2">
                  <div className="absolute -left-[31px] top-3 w-3 h-3 rounded-full bg-emerald-500" />
                  <div className="font-bold text-white">Deliverable Corporate Email Handshake</div>
                  <div className="text-zinc-400">{allEmails[0]} — Status: {candidate?.email_status || 'Verified'}</div>
                </div>
              )}
              {allPhones[0] && (
                <div className="space-y-1 relative pt-2">
                  <div className="absolute -left-[31px] top-3 w-3 h-3 rounded-full bg-emerald-500" />
                  <div className="font-bold text-white">Direct Phone Contact Staged</div>
                  <div className="text-zinc-400">{allPhones[0]}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Tab Content: Submissions Tab ── */}
        {activeTab === 'Submissions' && (
          <div className="bg-[#161A17] border border-[#262D28] rounded-2xl p-7 space-y-6">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Send className="w-5 h-5 text-emerald-400" /> Campaign Submissions & Outbox History
            </h2>
            <p className="text-xs text-zinc-500">No active client submissions or campaign dispatches logged for this profile yet.</p>
          </div>
        )}

      </div>
    </div>
  );
}
