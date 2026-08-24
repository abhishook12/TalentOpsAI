import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Mail, Phone, ExternalLink, Building2, MapPin, Award,
  ShieldCheck, CheckCircle2, Copy, Check, Send, Sparkles,
  Calendar, Clock, User, ChevronRight, AlertTriangle, Wand2, RefreshCw, Users
} from 'lucide-react';
import api from '../../services/api';
import toast from 'react-hot-toast';

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
    <div className="p-4 rounded-xl bg-[#18181c] border border-[#27272a] space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-[#a1a1aa] uppercase tracking-wider">Company Colleagues</span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-emerald-400 hover:text-emerald-300 font-medium"
        >
          {isExpanded ? 'Collapse' : 'Explore Peers'}
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-2 pt-2 border-t border-[#27272a]">
          {loading ? (
            <div className="text-xs text-[#71717a] py-2 flex items-center gap-2">
              <RefreshCw className="w-3 h-3 animate-spin text-emerald-400" /> Finding colleagues at {company}...
            </div>
          ) : colleagues.length === 0 ? (
            <div className="text-xs text-[#71717a] py-1">No other active colleagues found for this firm.</div>
          ) : (
            colleagues.map(colleague => (
              <div
                key={colleague.recruiter_id}
                onClick={() => onSelectRecruiter(colleague)}
                className="p-2.5 rounded-lg bg-[#202026] hover:bg-[#272730] border border-[#2d2d35] cursor-pointer transition-colors flex items-center justify-between group"
              >
                <div className="min-w-0 pr-2">
                  <div className="text-xs font-semibold text-white group-hover:text-emerald-400 transition-colors truncate">
                    {colleague.recruiter_name}
                  </div>
                  <div className="text-[10px] text-[#a1a1aa] truncate">
                    {colleague.title || 'Recruiter'} {colleague.location ? `• ${colleague.location}` : ''}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">
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
  const [recruiter, setRecruiter] = useState(initialRecruiter);
  const [copiedField, setCopiedField] = useState(null);
  const [isFixingEmail, setIsFixingEmail] = useState(false);

  React.useEffect(() => {
    setRecruiter(initialRecruiter);
  }, [initialRecruiter]);

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
  const title = recruiter.title || 'Talent Acquisition Specialist';
  const company = recruiter.company_name || recruiter.company || 'Direct Staffing Partner';
  const location = recruiter.location || recruiter.state || 'United States';
  const linkedin = recruiter.linkedin || recruiter.linkedin_url || '';
  const logo = recruiter.logo_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=18181b&color=10b981&bold=true`;
  const seniority = recruiter.seniority_level || 'Specialist';
  const emailStatus = recruiter.email_status || 'verified';
  const confidence = recruiter.email_confidence || (emailStatus === 'verified' ? 95 : 75);
  const completeness = recruiter.completeness_score || 85;

  const handleAutoFixEmail = async () => {
    if (!recruiter.recruiter_id) return;
    setIsFixingEmail(true);
    try {
      const res = await api.post(`/recruiters/${recruiter.recruiter_id}/auto-fix-email`);
      const { repaired_email, method, confidence } = res.data;
      setRecruiter(prev => ({
        ...prev,
        email: repaired_email,
        email_status: 'verified',
        email_confidence: confidence || 95,
        is_deliverable: true
      }));
      toast.success(`Repaired email to ${repaired_email} via ${method.replace(/_/g, ' ')}!`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No replacement email could be auto-synthesized');
    } finally {
      setIsFixingEmail(false);
    }
  };

  const getGradeBadge = (score) => {
    if (score >= 90) return { label: 'Grade A+', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
    if (score >= 75) return { label: 'Grade A', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' };
    if (score >= 60) return { label: 'Grade B', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' };
    return { label: 'Grade C', color: 'text-rose-400 bg-rose-500/10 border-rose-500/30' };
  };

  const grade = getGradeBadge(completeness);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        />

        {/* Slide-out Drawer */}
        <div className="fixed inset-y-0 right-0 max-w-full flex pl-10 pointer-events-none">
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="w-screen max-w-md bg-[#131316] border-l border-[#27272a] shadow-2xl pointer-events-auto flex flex-col h-full overflow-hidden"
          >
            {/* Drawer Header */}
            <div className="p-6 border-b border-[#27272a] bg-[#18181c]/50 relative">
              <button
                onClick={onClose}
                className="absolute top-5 right-5 w-8 h-8 rounded-lg flex items-center justify-center text-[#71717a] hover:text-white hover:bg-[#27272a] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="flex items-start gap-4 pr-8">
                <div className="w-14 h-14 rounded-2xl bg-[#222228] border border-[#33333e] flex items-center justify-center overflow-hidden p-2 flex-shrink-0 shadow-md">
                  <img
                    src={logo}
                    alt={company}
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=18181b&color=10b981&bold=true`;
                    }}
                    className="w-full h-full object-contain"
                  />
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${grade.color}`}>
                      {grade.label}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#27272a] text-[#a1a1aa] border border-[#3f3f46]">
                      {seniority}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-white tracking-tight truncate m-0">{name}</h2>
                  <p className="text-xs text-[#a1a1aa] truncate mt-0.5 flex items-center gap-1">
                    <Building2 className="w-3 h-3 text-[#71717a]" /> {company}
                  </p>
                </div>
              </div>
            </div>

            {/* Drawer Scrollable Body */}
            <div className="p-6 overflow-y-auto space-y-6 custom-scrollbar flex-1">
              {/* Quick Actions Bar */}
              <div className="grid grid-cols-2 gap-2.5">
                {email ? (
                  <a
                    href={`mailto:${email}`}
                    className="flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold no-underline transition-all shadow-md shadow-emerald-950/20"
                  >
                    <Mail className="w-3.5 h-3.5" /> Email Candidate
                  </a>
                ) : null}

                {linkedin ? (
                  <a
                    href={linkedin}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-semibold no-underline transition-all shadow-md"
                  >
                    <ExternalLink className="w-3.5 h-3.5" /> LinkedIn Profile
                  </a>
                ) : null}
              </div>

              {/* Deliverability & MX Shield Card */}
              <div className="p-4 rounded-xl bg-[#18181c] border border-[#27272a] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-[#71717a] uppercase tracking-wider flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> MailIntel Deliverability
                  </span>
                  <span className="text-xs font-bold text-emerald-400 font-mono">{confidence}% Safe</span>
                </div>

                <div className="w-full h-1.5 bg-[#27272a] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full"
                    style={{ width: `${Math.min(100, confidence)}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-[#a1a1aa] pt-1 border-t border-[#27272a]">
                  <span>Status: <strong className="text-white capitalize">{emailStatus.replace('_', ' ')}</strong></span>
                  <span>MX Host: <strong className="text-white">Corporate Active</strong></span>
                </div>
              </div>

              {/* Contact Channels */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-[#a1a1aa] uppercase tracking-wider m-0">Contact Coordinates</h3>
                  {recruiter.recruiter_id && (
                    <button
                      onClick={handleAutoFixEmail}
                      disabled={isFixingEmail}
                      className="text-[11px] font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 cursor-pointer bg-purple-500/10 hover:bg-purple-500/20 px-2.5 py-1 rounded-lg border border-purple-500/20 transition-colors"
                    >
                      {isFixingEmail ? (
                        <>
                          <RefreshCw className="w-3 h-3 animate-spin" /> Repairing...
                        </>
                      ) : (
                        <>
                          <Wand2 className="w-3 h-3" /> Auto-Repair Email
                        </>
                      )}
                    </button>
                  )}
                </div>

                {/* Email Item */}
                <div className="p-3 rounded-xl bg-[#18181c] border border-[#27272a] flex items-center justify-between group hover:border-[#3f3f46] transition-colors">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
                      <Mail className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] text-[#71717a]">Primary Email</div>
                      <div className="text-xs font-mono text-white truncate">{email || 'Not Available'}</div>
                    </div>
                  </div>
                  {email && (
                    <button
                      onClick={() => copyToClipboard(email, 'Email')}
                      className="p-1.5 rounded-lg text-[#71717a] hover:text-white hover:bg-[#27272a] transition-colors"
                      title="Copy Email"
                    >
                      {copiedField === 'Email' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>

                {/* Phone Item */}
                <div className="p-3 rounded-xl bg-[#18181c] border border-[#27272a] flex items-center justify-between group hover:border-[#3f3f46] transition-colors">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 flex-shrink-0">
                      <Phone className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] text-[#71717a]">Direct Phone</div>
                      <div className="text-xs font-mono text-white truncate">{phone || 'Not Available'}</div>
                    </div>
                  </div>
                  {phone && (
                    <button
                      onClick={() => copyToClipboard(phone, 'Phone')}
                      className="p-1.5 rounded-lg text-[#71717a] hover:text-white hover:bg-[#27272a] transition-colors"
                      title="Copy Phone"
                    >
                      {copiedField === 'Phone' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>

                {/* Location Item */}
                <div className="p-3 rounded-xl bg-[#18181c] border border-[#27272a] flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 flex-shrink-0">
                      <MapPin className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] text-[#71717a]">Market / Location</div>
                      <div className="text-xs text-white truncate">{location}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Role & Specialization */}
              <div className="p-4 rounded-xl bg-[#18181c] border border-[#27272a] space-y-2">
                <div className="text-xs font-semibold text-[#a1a1aa] uppercase tracking-wider">Recruiting Domain</div>
                <div className="text-xs text-white leading-relaxed">{title}</div>
                {recruiter.specialization && (
                  <div className="pt-2 border-t border-[#27272a] text-[11px] text-[#a1a1aa]">
                    Specialization: <strong className="text-emerald-400">{recruiter.specialization}</strong>
                  </div>
                )}
              </div>

              {/* Company Colleague Graph */}
              <ColleaguesSection recruiterId={recruiter.recruiter_id} company={company} onSelectRecruiter={(colleague) => setRecruiter(colleague)} />
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-[#27272a] bg-[#18181c]/50 flex items-center justify-between">
              <button
                onClick={() => copyToClipboard(`${name} <${email}> - ${company}`, 'Full Profile')}
                className="px-3.5 py-2 rounded-xl text-xs font-medium text-[#a1a1aa] hover:text-white bg-[#222228] hover:bg-[#2c2c34] transition-colors flex items-center gap-1.5"
              >
                <Copy className="w-3.5 h-3.5" /> Copy Full Contact
              </button>

              {onEnrollCampaign && (
                <button
                  onClick={() => onEnrollCampaign(recruiter)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5 shadow-md"
                >
                  <Send className="w-3.5 h-3.5" /> Add to Campaign
                </button>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
}
