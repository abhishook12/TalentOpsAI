import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import {
  Download, Laptop, ShieldCheck, Zap, Wifi, CheckCircle2, ArrowRight,
  Database, RefreshCw, Layers, Terminal, Sparkles, AlertCircle, HelpCircle,
  Users, Activity, Server, FileText, Check, Shield, Search, Filter,
  ChevronRight, ArrowUpDown, Cpu, Clock, AlertTriangle, ShieldAlert, Award,
  ChevronDown, ChevronUp, ExternalLink, Info, UserCheck, Trash2, Key, Link2, Copy,
  Lock, EyeOff, MessageSquare, Mail, Briefcase, FileCode, Monitor, Globe
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import AddScoutModal from '../components/AddScoutModal';
import ScoutUserProfileDrawer from '../components/ScoutUserProfileDrawer';
import ScoutNodesPanel from '../components/ScoutNodesPanel';
import ScoutReleaseGovernance from '../components/ScoutReleaseGovernance';

// 9 Exact Supported Platform Categories Monitored by Desktop Scout (scout_desktop/core/window_tracker.py & browser_tracker.py)
const SCOUT_PLATFORM_CATEGORIES = [
  {
    id: "linkedin",
    name: "LinkedIn Suite",
    icon: Laptop,
    color: "#0a66c2",
    badge: "Primary Engine",
    description: "Deep OCR & DOM extraction across LinkedIn candidate cards, projects & network profiles.",
    targets: [
      { name: "LinkedIn Profiles", scope: "/in/*", details: "Name, current title, company, skills, location, public contact info" },
      { name: "LinkedIn Recruiter", scope: "talent.linkedin.com", details: "Project pipeline tags, recruiter notes & candidate cards" },
      { name: "Sales Navigator", scope: "/sales/*", details: "Lead lists, executive decision-makers, direct emails" },
      { name: "Company People Directory", scope: "/company/*/people", details: "Org chart team rosters, seniority levels & roles" }
    ]
  },
  {
    id: "b2b_intel",
    name: "B2B Intelligence",
    icon: Sparkles,
    color: "#0284c7",
    badge: "Target 7",
    description: "Direct business phone numbers, verified corporate emails & organizational hierarchy.",
    targets: [
      { name: "ZoomInfo Enterprise", scope: "app.zoominfo.com", details: "Direct-dial numbers, corporate emails, management level" },
      { name: "ZoomInfo Lite", scope: "zi-lite.zoominfo.com", details: "Compact contact lookup & executive verification" },
      { name: "Apollo.io Search", scope: "app.apollo.io", details: "Verified work emails, mobile dials & tech stack data" },
      { name: "Apollo People", scope: "apollo.io/people", details: "Recruiter contact lists & verified prospecting leads" }
    ]
  },
  {
    id: "dev_talent",
    name: "Developer & Tech",
    icon: FileCode,
    color: "#10b981",
    badge: "Target 5",
    description: "Engineering profiles, open-source repositories, competition rankings & tech resumes.",
    targets: [
      { name: "GitHub Profiles", scope: "github.com/*", details: "Developer bio, top languages, repos, followers & public email" },
      { name: "Stack Overflow", scope: "stackoverflow.com/users", details: "Reputation score, gold/silver badges, top tag answers" },
      { name: "Kaggle", scope: "kaggle.com/*", details: "Grandmaster/Master rank, competition notebooks, dataset authoring" },
      { name: "Dice", scope: "dice.com", details: "Tech contractor CVs, hourly rates & specialized skills" },
      { name: "Wellfound (AngelList)", scope: "wellfound.com", details: "Startup founding engineers, equity preferences & portfolios" }
    ]
  },
  {
    id: "ats",
    name: "Applicant Tracking Systems",
    icon: Database,
    color: "#8b5cf6",
    badge: "Target 6 (ATS)",
    description: "Automatic synchronization with your existing company applicant tracking systems.",
    targets: [
      { name: "Greenhouse", scope: "greenhouse.io", details: "Candidate interview stages, scorecards & active job postings" },
      { name: "Lever", scope: "lever.co", details: "Opportunity records, candidate contact archives & feedback" },
      { name: "Ashby", scope: "ashbyhq.com", details: "Modern recruitment pipeline cards & candidate CRM profiles" },
      { name: "Workday HCM", scope: "myworkday.com", details: "Enterprise job applicants & internal mobility records" },
      { name: "iCIMS", scope: "icims.com", details: "Corporate sourcing talent pools & compliance tracking" },
      { name: "SmartRecruiters", scope: "smartrecruiters.com", details: "Candidate dossiers, hiring team reviews & timeline" }
    ]
  },
  {
    id: "job_boards",
    name: "Job Portals & Sourcing",
    icon: Briefcase,
    color: "#f59e0b",
    badge: "Target 8",
    description: "Public job boards, resume search indexes & algorithmic talent matching portals.",
    targets: [
      { name: "Indeed Resume", scope: "indeed.com/resume", details: "Public resume search, work history & candidate availability" },
      { name: "SimplyHired", scope: "simplyhired.com", details: "Regional candidate listings & salary benchmarks" },
      { name: "Glassdoor", scope: "glassdoor.com", details: "Employer talent reviews & compensation benchmarks" },
      { name: "ZipRecruiter", scope: "ziprecruiter.com", details: "Resume database search & 1-click candidate profiles" },
      { name: "Jobright.ai", scope: "jobright.ai", details: "AI candidate recommendations & skill match profiles" }
    ]
  },
  {
    id: "communication",
    name: "Collaboration & Inboxes",
    icon: MessageSquare,
    color: "#06b6d4",
    badge: "Target 1 & 2",
    description: "Detects candidate resume shares and referral conversations in enterprise chat apps.",
    targets: [
      { name: "Microsoft Teams", scope: "teams.exe & Web", details: "Candidate referral links, interview coordination & CV shares" },
      { name: "Slack Enterprise", scope: "slack.exe & Web", details: "Recruiter sourcing channels & peer referral submissions" },
      { name: "WhatsApp Desktop & Web", scope: "web.whatsapp.com", details: "Direct candidate conversation context & scheduling" },
      { name: "Telegram Web & Desktop", scope: "telegram.exe & Web", details: "Developer community channels & candidate inquiries" },
      { name: "Google Chat", scope: "chat.google.com", details: "Internal recruiter room talent shares & candidate links" },
      { name: "Outlook Desktop & Web", scope: "outlook.exe & Web", details: "Direct email candidate replies, attachments & CV parsing" },
      { name: "Google Mail (Gmail)", scope: "mail.google.com", details: "Inbound job application emails & candidate messages" }
    ]
  },
  {
    id: "resumes",
    name: "PDF Resumes & Portfolios",
    icon: FileText,
    color: "#e11d48",
    badge: "Target 3",
    description: "Direct local PDF parsing & in-browser CV extraction with offline OCR.",
    targets: [
      { name: "Adobe Acrobat Reader", scope: "acroRd32.exe / acrobat.exe", details: "Direct desktop PDF resume parsing via native window hooks" },
      { name: "Browser PDF Viewers", scope: ".pdf / blob: URLs", details: "Candidate portfolios, downloadable CVs & attached credentials" }
    ]
  },
  {
    id: "staffing",
    name: "Staffing & Search Portals",
    icon: Users,
    color: "#6366f1",
    badge: "Target 9",
    description: "Retained search, executive recruitment & specialized staffing agency talent rosters.",
    targets: [
      { name: "Executive Search Portals", scope: "executive-search / staffing", details: "C-level & VP candidate rosters & verified portfolios" },
      { name: "Staffing Agency Directories", scope: "vacaregroup.com & agencies", details: "Contractor pools & agency recruiter candidate benches" }
    ]
  }
];

// 9 Stacked Pages in Scout Desktop Obsidian Command Center (scout_desktop/ui/main_window.py)
const COMMAND_CENTER_VIEWS = [
  { id: 0, name: "Live Scan & Pulse", icon: Activity, desc: "Real-time active window detection, perceptual hash delta gate, live OCR sampling pulse, candidate extraction card, and sampling metrics." },
  { id: 1, name: "Candidates Catalog", icon: Users, desc: "Searchable local directory of all captured candidate profiles with 1-click status filtering and CSV/JSON export." },
  { id: 2, name: "Candidate Dossier", icon: FileText, desc: "Granular candidate inspection with verified work history, skills cloud, contact information, and grounding confidence score." },
  { id: 3, name: "Review Queue", icon: Search, desc: "Human-in-the-loop triage queue to inspect ambiguous or low-confidence captures before synchronizing with the cloud." },
  { id: 4, name: "Cloud Sync & Buffer", icon: Database, desc: "Local SQLite queue (local_queue.db) guarantees zero data loss during offline periods with automatic exponential retry backoff." },
  { id: 5, name: "Pipeline Stages", icon: Layers, desc: "Visual recruitment conversion funnel tracking candidates across Sourced, Contacted, Screened, and Offered stages." },
  { id: 6, name: "Activity & Audit Trail", icon: Clock, desc: "Granular audit log of active window transitions, OCR extraction latency, platform classifications, and cloud telemetry." },
  { id: 7, name: "Settings & Privacy DLP", icon: Shield, desc: "Configurable sampling rates, developer diagnostics mode, and strict DLP privacy masking to ignore non-candidate windows." },
  { id: 8, name: "Sign-In & Claim Screen", icon: Key, desc: "Reverse device flow pairing (TOS-XXXX), claim code input, and enterprise trust guarantees with zero passwords stored." },
];

// Enterprise Trust Pillars from Desktop Scout (scout_desktop/ui/pages.py SignInClaimPage)
const TRUST_PILLARS = [
  {
    title: "No Passwords Stored on Device",
    icon: Lock,
    color: "#34d399",
    desc: "Scout never accesses password managers, authentication sessions, or personal browsing data. Only candidate cards on approved recruiting platforms are processed."
  },
  {
    title: "Offline SQLite Resilience",
    icon: Database,
    color: "#60a5fa",
    desc: "Built-in local SQLite buffer queue (local_queue.db) holds captured candidates safely on your hard drive if internet disconnects, auto-syncing when back online."
  },
  {
    title: "Zero Admin Rights Needed",
    icon: ShieldCheck,
    color: "#a78bfa",
    desc: "Installs cleanly into %LOCALAPPDATA%\\Programs\\TalentOpsScout in under 5 seconds with standard user privileges. No IT administrator prompt required."
  },
  {
    title: "Strict Privacy DLP Gating",
    icon: EyeOff,
    color: "#f59e0b",
    desc: "Personal email, banking, social media, shopping, and entertainment windows are permanently blacklisted and automatically discarded without inspection."
  }
];

export default function DownloadScout() {
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const [showAddModal, setShowAddModal] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showSetupGuide, setShowSetupGuide] = useState(false);
  const [showSecurityNotice, setShowSecurityNotice] = useState(true);
  const [activeClaim, setActiveClaim] = useState(null);
  const [claimStatus, setClaimStatus] = useState(null);
  const pollIntervalRef = useRef(null);
  const [adminView, setAdminView] = useState('companion'); // 'companion' | 'contributors' | 'fleet_nodes' | 'governance'
  const currentView = isAdmin ? adminView : 'companion';

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('most_active');
  const [selectedUserId, setSelectedUserId] = useState(null);

  // Pairing code state (Reverse Device Flow)
  const [pairingCodeInput, setPairingCodeInput] = useState('');
  const [pairingLoading, setPairingLoading] = useState(false);
  const [pairingSuccess, setPairingSuccess] = useState(null);
  const [pairingError, setPairingError] = useState('');
  const [disconnectingId, setDisconnectingId] = useState(null);

  // Admin Force-Pairing & User Provisioning State
  const [targetUserEmail, setTargetUserEmail] = useState('');
  const [adminGeneratedCode, setAdminGeneratedCode] = useState(null);
  const [generatingCode, setGeneratingCode] = useState(false);
  const [adminCodeCopied, setAdminCodeCopied] = useState(false);

  // Active platform category filter in UI
  const [activePlatformCategory, setActivePlatformCategory] = useState('ALL');

  // Provisionable users query (for admin force-pairing and code generation)
  const { data: provUsersData, refetch: refetchProvUsers } = useQuery({
    queryKey: ['scout-provisionable-users'],
    queryFn: async () => {
      const res = await api.get('/scout/provisionable-users');
      return res.data?.users || [];
    },
    enabled: !!isAdmin,
  });
  const provisionableUsers = provUsersData || [];

  // Dynamic Release Info from Authoritative DB Registry (Defaults match exact v2.9.4 build)
  const [releaseInfo, setReleaseInfo] = useState({
    version: '2.9.4',
    extractor_version: '4.6.3',
    download_url: 'https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe',
    size_bytes: 50084798,
    sha256: 'f060e23435a40fc369206b25d97e139295fe39da737361cd30d06e52f32f6cc7',
    channel: 'stable',
    released_at: '2026-09-24',
  });

  useEffect(() => {
    api.get('/scout/updates/latest')
      .then(res => {
        if (res?.data?.version) {
          setReleaseInfo(prev => ({ ...prev, ...res.data }));
        }
      })
      .catch(() => {});
  }, []);

  // Desktop Scout Companion Query (for logged-in user)
  const {
    data: myDeviceData,
    isLoading: loadingMyDevice,
    refetch: refetchMyDevice
  } = useQuery({
    queryKey: ['scout-my-device'],
    queryFn: async () => {
      const res = await api.get('/scout/my-device');
      return res.data;
    },
    refetchInterval: user ? 15000 : false,
    enabled: !!user,
  });

  // Scout Contributors Telemetry Query (Admin Only) - Cached once and filtered on client
  const { data: contribData, isLoading, isFetching, isError, refetch } = useQuery({
    queryKey: ['scout-contributors-unified'],
    queryFn: async () => {
      const res = await api.get('/scout/users');
      return res.data;
    },
    enabled: !!isAdmin,
    staleTime: 30000,
    keepPreviousData: true,
  });

  const handleRefreshContributors = useCallback(async () => {
    try {
      await api.get('/scout/users', { params: { refresh: true } });
      refetch();
    } catch {
      refetch();
    }
  }, [refetch]);

  const summary = contribData?.summary || {};
  const allUsers = useMemo(() => contribData?.users || [], [contribData?.users]);

  // High-Speed Instant Client-Side Search, Filter, and Sort (0ms Keystroke Latency, 0 Server Hits)
  const users = useMemo(() => {
    let result = [...allUsers];

    // Status filter
    if (statusFilter !== 'ALL') {
      result = result.filter(u => u.status === statusFilter);
    }

    // Search filter
    if (searchQuery && searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(u =>
        (u.name && u.name.toLowerCase().includes(q)) ||
        (u.email && u.email.toLowerCase().includes(q)) ||
        (u.role && u.role.toLowerCase().includes(q)) ||
        (u.scout_id && u.scout_id.toLowerCase().includes(q)) ||
        (u.hostname && u.hostname.toLowerCase().includes(q))
      );
    }

    // Sort
    result.sort((a, b) => {
      if (sortBy === 'recent') {
        const tA = a.last_seen_at ? new Date(a.last_seen_at).getTime() : 0;
        const tB = b.last_seen_at ? new Date(b.last_seen_at).getTime() : 0;
        return tB - tA;
      }
      if (sortBy === 'discoveries') {
        return (b.useful_discoveries || 0) - (a.useful_discoveries || 0);
      }
      if (sortBy === 'name') {
        return (a.name || '').localeCompare(b.name || '');
      }
      return 0;
    });

    return result;
  }, [allUsers, statusFilter, searchQuery, sortBy]);

  const versionDistribution = contribData?.version_distribution || {};
  // Cleanup poller on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleDownload = async () => {
    setDownloading(true);

    // 1. Issue short-lived installation claim for one-click auto-registration
    try {
      const claimRes = await api.post('/scout/install/claim', {
        label: 'Web Download Scout Auto-Pair',
        expires_minutes: 15,
      });

      if (claimRes?.data?.ok) {
        const claimData = claimRes.data;
        setActiveClaim(claimData);
        setClaimStatus({ status: 'WAITING', is_consumed: false });

        // Background loopback attempt: If Scout Desktop is already open on this PC,
        // it listens on 127.0.0.1:49152 and registers instantly!
        try {
          fetch('http://127.0.0.1:49152/claim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              claim_id: claimData.claim_id,
              claim_secret: claimData.claim_secret,
            }),
            mode: 'cors',
          }).catch((err) => { console.debug('Direct local loopback not reachable:', err); });
        } catch (err) {
          console.debug('Loopback claim error:', err);
        }

        // Poll claim status every 3s to notify user when Scout launches and pairs
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = setInterval(async () => {
          try {
            const stRes = await api.get(`/scout/install/status/${claimData.claim_id}`);
            if (stRes?.data) {
              setClaimStatus(stRes.data);
              if (stRes.data.is_consumed) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
                toast.success(`🎉 Scout Desktop auto-registered successfully! (${stRes.data.hostname || stRes.data.device_id})`);
                refetch();
              }
            }
          } catch (pollErr) {
            console.debug('Claim status poll retry note:', pollErr);
          }
        }, 3000);
      }
    } catch (err) {
      console.debug('Claim generation fallback:', err);
    }

    // 2. Track download event in telemetry registry
    try {
      await api.post('/scout/download/track', {
        version: releaseInfo.version || contribData?.latest_production_version || 'latest',
        source: 'desktop_scout_page'
      });
    } catch (err) {
      console.debug('Download telemetry track note:', err);
    }

    // 3. Initiate browser download of the installer using canonical public endpoint
    const downloadUrl = releaseInfo.download_url || '/download/scout/windows';
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'TalentOpsScoutSetup.exe';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    const verDisplay = releaseInfo.version ? `v${releaseInfo.version}` : (contribData?.latest_production_version ? `v${contribData.latest_production_version}` : '');
    toast.success(`TalentOps Scout ${verDisplay ? verDisplay + ' ' : ''}download initiated!`);
    setTimeout(() => setDownloading(false), 2500);
  };

  const handleDownloadZip = () => {
    const zipUrl = 'https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.zip';
    const a = document.createElement('a');
    a.href = zipUrl;
    a.download = 'TalentOpsScoutSetup.zip';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success('Downloading Scout .ZIP archive (Chrome-safe bundle)');
  };

  const handleVerifyPairingCode = async (e, customTargetEmail = null) => {
    if (e) e.preventDefault();
    const cleanCode = pairingCodeInput.trim().toUpperCase();
    if (!cleanCode) {
      toast.error('Please enter the pairing code shown on your Desktop Scout app');
      return;
    }
    setPairingLoading(true);
    setPairingError('');
    setPairingSuccess(null);

    const effTarget = customTargetEmail !== null ? customTargetEmail : (isAdmin && targetUserEmail ? targetUserEmail : null);

    try {
      const payload = { code: cleanCode };
      if (effTarget) {
        payload.target_user_email = effTarget;
      }
      const res = await api.post('/scout/device-flow/verify', payload);
      if (res?.data?.ok) {
        const targetDisplay = res.data.user_email || 'your account';
        if (res.data.provisioned_by_admin) {
          toast.success(`⚡ Desktop Scout force-paired to ${targetDisplay}!`);
          setPairingSuccess(`Connected: ${res.data.scout_id || 'Device'} force-paired to ${targetDisplay}`);
        } else {
          toast.success(`🎉 Desktop Scout paired successfully!`);
          setPairingSuccess(`Connected: ${res.data.scout_id || 'Device'} linked to ${targetDisplay}`);
        }
        setPairingCodeInput('');
        refetchMyDevice();
        if (isAdmin) {
          refetch();
          refetchProvUsers();
        }
      } else {
        setPairingError(res?.data?.detail || 'Failed to verify pairing code');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid or expired pairing code. Please check Desktop Scout.';
      setPairingError(msg);
      toast.error(msg);
    } finally {
      setPairingLoading(false);
    }
  };

  const handleAdminGenerateCode = async () => {
    if (!targetUserEmail) {
      toast.error('Please select a target team member first');
      return;
    }
    setGeneratingCode(true);
    try {
      const res = await api.post('/scout/codes/generate', {
        target_user_email: targetUserEmail,
        label: `Admin Force-Provision for ${targetUserEmail} (Permanent)`,
        expires_minutes: 0, // 0 = Permanent, Never Expires!
        max_uses: -1, // Unlimited uses
      });
      setAdminGeneratedCode(res.data);
      toast.success(`🎉 Permanent activation code generated for ${res.data.target_user_name || targetUserEmail}!`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate activation code');
    } finally {
      setGeneratingCode(false);
    }
  };

  const handleDisconnectDevice = async (deviceId) => {
    if (!window.confirm('Are you sure you want to disconnect this Desktop Scout companion?')) return;
    setDisconnectingId(deviceId);
    try {
      await api.post(`/scout/my-device/${deviceId}/disconnect`);
      toast.success('Device disconnected successfully');
      refetchMyDevice();
      if (isAdmin) refetch();
    } catch (err) {
      toast.error('Failed to disconnect device');
    } finally {
      setDisconnectingId(null);
    }
  };


  const formatTimeAgo = (isoStr) => {
    if (!isoStr) return 'Never';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      const diffMs = Date.now() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}d ago`;
    } catch {
      return isoStr || 'Unknown';
    }
  };

  const getStatusBadge = (status) => {
    const st = (status || '').toUpperCase();
    switch (st) {
      case 'CONTRIBUTING':
      case 'CONTRIBUTING_OFFLINE':
        return { bg: 'rgba(16, 185, 129, 0.2)', text: '#34d399', border: 'rgba(16, 185, 129, 0.4)', icon: Sparkles };
      case 'ACTIVE':
        return { bg: 'rgba(34, 197, 94, 0.2)', text: '#4ade80', border: 'rgba(34, 197, 94, 0.4)', icon: Activity };
      case 'PAIRED':
      case 'PAIRED_IDLE':
        return { bg: 'rgba(228, 228, 231, 0.15)', text: '#e4e4e7', border: 'rgba(228, 228, 231, 0.35)', icon: Zap };
      case 'INSTALLED':
        return { bg: 'rgba(161, 161, 170, 0.15)', text: '#a1a1aa', border: 'rgba(161, 161, 170, 0.35)', icon: Laptop };
      case 'DOWNLOAD_ONLY':
        return { bg: 'rgba(234, 179, 8, 0.15)', text: '#facc15', border: 'rgba(234, 179, 8, 0.35)', icon: Clock };
      case 'REGISTERED':
        return { bg: 'rgba(148, 163, 184, 0.15)', text: '#a1a1aa', border: 'rgba(148, 163, 184, 0.3)', icon: UserCheck };
      case 'REVOKED':
        return { bg: 'rgba(244, 63, 94, 0.2)', text: '#fb7185', border: 'rgba(244, 63, 94, 0.4)', icon: ShieldAlert };
      default:
        return { bg: 'rgba(100, 116, 139, 0.2)', text: '#a1a1aa', border: 'rgba(100, 116, 139, 0.3)', icon: AlertCircle };
    }
  };

  const getQualityBadge = (tier, score) => {
    let color = '#a1a1aa';
    let bg = 'rgba(148, 163, 184, 0.15)';
    const t = (tier || '').toUpperCase();
    if (t === 'ELITE') {
      color = '#a1a1aa';
      bg = 'rgba(161, 161, 170, 0.2)';
    } else if (t === 'HIGH') {
      color = '#10b981';
      bg = 'rgba(16, 185, 129, 0.2)';
    } else if (t === 'MEDIUM' || t === 'MODERATE') {
      color = '#e4e4e7';
      bg = 'rgba(228, 228, 231, 0.2)';
    } else if (t === 'LOW' || t === 'DEVELOPING') {
      color = '#f59e0b';
      bg = 'rgba(245, 158, 11, 0.2)';
    }
    return (
      <span style={{
        padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700,
        background: bg, color: color, display: 'inline-flex', alignItems: 'center', gap: 4
      }}>
        <Award size={12} />
        {score} • {tier || 'DEV'}
      </span>
    );
  };

  const totalUsersCount = summary.total_scout_users || users.length || 0;
  const activeUsersCount = summary.active_users || 0;
  const activeDevicesCount = summary.active_devices || 0;
  const totalDevicesCount = summary.total_devices || summary.active_devices || 0;
  const contributingUsersCount = summary.contributing_users || 0;
  const offlineUsersCount = summary.offline_users || 0;
  const updateReqCount = summary.update_required_count ?? summary.update_required ?? 0;
  const revokedCount = summary.revoked_count ?? summary.revoked ?? 0;
  const canonicalCreated = summary.total_canonical_created ?? summary.total_people_contributed ?? 0;
  const canonicalEnriched = summary.total_canonical_enriched ?? summary.total_contacts_contributed ?? 0;
  const avgQualScore = summary.avg_quality_score ?? summary.average_quality_score ?? 0;
  const latestProdVer = contribData?.latest_production_version || releaseInfo?.version || '';

  const displayVersion = releaseInfo.version ? `v${releaseInfo.version}` : (latestProdVer ? `v${latestProdVer}` : 'v2.9.4');
  const displaySize = releaseInfo.size_bytes
    ? `${(releaseInfo.size_bytes / (1024 * 1024)).toFixed(1)} MB`
    : '51.6 MB';

  const displayedPlatforms = activePlatformCategory === 'ALL'
    ? SCOUT_PLATFORM_CATEGORIES
    : SCOUT_PLATFORM_CATEGORIES.filter(c => c.id === activePlatformCategory);

  return (
    <div className="page-container page-enter" style={{ padding: '0 32px 80px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
      {/* Top Header */}
      <header style={{ paddingTop: 32, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399', padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700, marginBottom: 8
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }} />
              {!user
                ? 'OFFICIAL DESKTOP INSTALLER • WIN32 COMPANION'
                : (isAdmin ? 'OFFICIAL DESKTOP CLIENT • FLEET GOVERNANCE' : 'DESKTOP SOURCING CLIENT • WORKSPACE PIPELINE')}
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 6px', letterSpacing: '-0.5px' }}>
              {!user
                ? 'TalentOps Scout Desktop Setup'
                : (isAdmin ? 'Desktop Scout & Contributors' : 'My Desktop Scout')}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: 0, maxWidth: 840, lineHeight: 1.5 }}>
              {!user
                ? 'Windows desktop client for candidate sourcing. Extracts, verifies, and stages candidate profiles across 9 platforms directly to your workspace.'
                : (isAdmin
                  ? 'Windows desktop client, active device fleet management, and verified candidate pipeline contribution analytics.'
                  : 'Connect your Windows desktop client to automatically extract, verify, and stage candidate profiles directly to your TalentOps account.')}
            </p>
          </div>

          {/* Quick Actions / View Mode Toggle */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {isAdmin && (
              <div style={{
                display: 'flex', background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)',
                borderRadius: 8, padding: 3, gap: 2, flexWrap: 'wrap'
              }}>
                <button
                  onClick={() => setAdminView('companion')}
                  style={{
                    padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    background: adminView === 'companion' ? 'var(--hover-bg, #232326)' : 'transparent',
                    color: adminView === 'companion' ? 'var(--text-primary, #e4e4e7)' : 'var(--text-secondary, #a1a1aa)',
                  }}
                >
                  <Laptop size={13} />
                  <span>My Companion</span>
                </button>
                <button
                  onClick={() => setAdminView('contributors')}
                  style={{
                    padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    background: adminView === 'contributors' ? 'var(--hover-bg, #232326)' : 'transparent',
                    color: adminView === 'contributors' ? 'var(--text-primary, #e4e4e7)' : 'var(--text-secondary, #a1a1aa)',
                  }}
                >
                  <Users size={13} />
                  <span>Contributor Directory</span>
                </button>
                <button
                  onClick={() => setAdminView('fleet_nodes')}
                  style={{
                    padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    background: adminView === 'fleet_nodes' ? 'var(--hover-bg, #232326)' : 'transparent',
                    color: adminView === 'fleet_nodes' ? 'var(--text-primary, #e4e4e7)' : 'var(--text-secondary, #a1a1aa)',
                  }}
                >
                  <Server size={13} />
                  <span>Device Fleet &amp; Nodes</span>
                </button>
                <button
                  onClick={() => setAdminView('governance')}
                  style={{
                    padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
                    background: adminView === 'governance' ? 'var(--hover-bg, #232326)' : 'transparent',
                    color: adminView === 'governance' ? 'var(--text-primary, #e4e4e7)' : 'var(--text-secondary, #a1a1aa)',
                  }}
                >
                  <ShieldCheck size={13} />
                  <span>Release Governance</span>
                </button>
              </div>
            )}

            <button
              onClick={() => {
                if (user) refetchMyDevice();
                if (isAdmin) refetch();
              }}
              disabled={isFetching || loadingMyDevice}
              style={{
                padding: '8px 14px', background: 'var(--card-bg, #232326)', border: '1px solid var(--card-border, #27272a)',
                color: 'var(--text-primary, #fafafa)', borderRadius: 8, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                opacity: isFetching || loadingMyDevice ? 0.6 : 1
              }}
            >
              <RefreshCw size={13} className={isFetching || loadingMyDevice ? 'animate-spin' : ''} />
              <span>{isFetching || loadingMyDevice ? 'Syncing...' : 'Refresh'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* DESKTOP SCOUT COMPANION VIEW (For non-admin users + admin companion tab) */}
      {/* ========================================================================= */}
      {currentView === 'companion' && (
        <div>
          {/* Companion Welcome & Status Banner */}
          {!user ? (
            <div style={{
              background: 'linear-gradient(135deg, rgba(228, 228, 231, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%)',
              border: '1px solid rgba(228, 228, 231, 0.25)', borderRadius: 14, padding: '24px 28px',
              marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 20
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.35)',
                    padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, letterSpacing: 0.5, display: 'inline-flex', alignItems: 'center', gap: 6
                  }}>
                    <Laptop size={12} />
                    OFFICIAL DESKTOP INSTALLER &amp; SETUP
                  </span>
                  <span style={{ fontSize: 12, color: '#a1a1aa' }}>
                    Windows 10/11 64-bit • {displayVersion} Production • {displaySize}
                  </span>
                </div>
                <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary, #fafafa)', margin: '0 0 6px 0', letterSpacing: '-0.3px' }}>
                  Download TalentOps Scout Desktop Setup
                </h2>
                <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 14, margin: 0, maxWidth: 780, lineHeight: 1.5 }}>
                  Windows desktop companion for candidate capture. Operates locally in the background using native Windows OCR, an offline SQLite queue, and secure device pairing to stage candidate profiles across 9 platforms directly to your workspace.
                </p>
              </div>

              <div style={{
                background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 10, padding: '14px 20px',
                display: 'flex', alignItems: 'center', gap: 14
              }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 10px #10b981' }} />
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted, #a1a1aa)', textTransform: 'uppercase' }}>Current Release</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#34d399' }}>{displayVersion} • Production Stable</div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{
              background: 'linear-gradient(135deg, rgba(228, 228, 231, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%)',
              border: '1px solid rgba(228, 228, 231, 0.25)', borderRadius: 14, padding: '24px 28px',
              marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 20
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                  <span style={{
                    background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)',
                    padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700, letterSpacing: 0.5, display: 'inline-flex', alignItems: 'center', gap: 6
                  }}>
                    <Laptop size={12} />
                    DESKTOP SCOUT COMPANION
                  </span>
                  <span style={{ fontSize: 12, color: '#a1a1aa' }}>
                    Account: <b>{user?.email || 'Authenticated User'}</b>
                  </span>
                </div>
                <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary, #fafafa)', margin: '0 0 6px 0', letterSpacing: '-0.3px' }}>
                  Welcome, {user?.first_name || user?.name || user?.email?.split('@')[0] || 'Recruiter'}!
                </h2>
                <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 13, margin: 0, maxWidth: 740, lineHeight: 1.5 }}>
                  Your Desktop Scout companion runs quietly in the background to capture candidate profiles and contact details while you browse LinkedIn, ZoomInfo, GitHub, ATS, and job boards, staging verified records directly into your workspace.
                </p>
              </div>

              {/* Live Device Status Pill */}
              <div style={{
                background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 10, padding: '12px 18px',
                display: 'flex', alignItems: 'center', gap: 14
              }}>
                <div style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: myDeviceData?.devices?.some(d => d.is_online) ? '#10b981' : '#71717a',
                  boxShadow: myDeviceData?.devices?.some(d => d.is_online) ? '0 0 10px #10b981' : 'none'
                }} />
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted, #a1a1aa)', textTransform: 'uppercase' }}>Companion Status</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: myDeviceData?.devices?.some(d => d.is_online) ? '#34d399' : 'var(--text-primary, #fafafa)' }}>
                    {myDeviceData?.devices?.some(d => d.is_online)
                      ? 'Active & Streaming'
                      : (myDeviceData?.devices?.length > 0 ? 'Device Paired (Standby)' : 'Not Connected')}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 2-Column Action Cards: Download (Left) & Enter Code / Sign In (Right) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 20, marginBottom: 28 }}>
            {/* CARD 1: DOWNLOAD INSTALLER */}
            <div style={{
              background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 14, padding: '24px 26px',
              display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: 'var(--shadow)'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 10, background: 'rgba(16, 185, 129, 0.15)',
                    border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981'
                  }}>
                    <Download size={22} />
                  </div>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', letterSpacing: 0.5 }}>STEP 1: GET DESKTOP COMPANION</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary, #fafafa)' }}>TalentOps Scout Setup</div>
                  </div>
                </div>

                <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 13, lineHeight: 1.5, marginBottom: 16 }}>
                  Download and run the official Windows installer. Installs cleanly in 5 seconds into your user profile (%LOCALAPPDATA%\Programs\TalentOpsScout) without needing IT administrator privileges.
                </p>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: 'var(--panel-bg, #232326)', border: '1px solid var(--card-border, transparent)', color: 'var(--text-secondary, #a1a1aa)', fontSize: 11, fontWeight: 600 }}>
                    Windows 10/11 64-bit
                  </span>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: 11, fontWeight: 700 }}>
                    {displayVersion} Production
                  </span>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: 'var(--panel-bg, #232326)', border: '1px solid var(--card-border, transparent)', color: 'var(--text-secondary, #a1a1aa)', fontSize: 11, fontWeight: 600 }}>
                    {displaySize}
                  </span>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: 'var(--panel-bg, #232326)', border: '1px solid var(--card-border, transparent)', color: 'var(--text-secondary, #a1a1aa)', fontSize: 11, fontWeight: 600 }}>
                    Extractor {releaseInfo.extractor_version ? `v${releaseInfo.extractor_version}` : 'v4.6.2'}
                  </span>
                  <span style={{ padding: '3px 8px', borderRadius: 6, background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', fontSize: 11, fontWeight: 600 }}>
                    SQLite Queue Buffer
                  </span>
                </div>

                {/* SHA-256 Checksum Pill */}
                {releaseInfo?.sha256 && (
                  <div style={{
                    background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)',
                    borderRadius: 8, padding: '8px 12px', marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8
                  }}>
                    <div style={{ minWidth: 0, overflow: 'hidden' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted, #71717a)', textTransform: 'uppercase', fontWeight: 700 }}>SHA-256 Verified</div>
                      <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-secondary, #a1a1aa)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {releaseInfo.sha256}
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(releaseInfo.sha256);
                        toast.success('SHA-256 copied to clipboard');
                      }}
                      style={{
                        padding: '4px 8px', background: 'var(--card-bg, #232326)', border: '1px solid var(--card-border, #27272a)',
                        color: 'var(--text-secondary, #e4e4e7)', borderRadius: 6, fontSize: 10, fontWeight: 700, cursor: 'pointer', flexShrink: 0
                      }}
                      title="Copy SHA-256 checksum"
                    >
                      Copy
                    </button>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  style={{
                    width: '100%', padding: '13px 20px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.35)', transition: 'all 0.15s ease'
                  }}
                >
                  <Download size={18} />
                  <span>{downloading ? 'Starting Download...' : `Download Scout Setup (${displayVersion})`}</span>
                </button>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <button
                    type="button"
                    onClick={handleDownloadZip}
                    style={{
                      padding: '8px 10px', background: 'var(--panel-bg, #18181b)', color: 'var(--text-primary, #e4e4e7)',
                      border: '1px solid var(--card-border, #27272a)', borderRadius: 8, fontSize: 11, fontWeight: 600,
                      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
                      transition: 'all 0.15s ease'
                    }}
                    title="Download as a ZIP archive if Chrome blocks the raw .exe file"
                  >
                    <Download size={12} color="#10b981" />
                    <span>Download .ZIP</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      const cmd = `iwr -useb https://talentopsai-1.onrender.com/scout/download/windows -OutFile "$env:TEMP\\TalentOpsScoutSetup.exe"; Unblock-File "$env:TEMP\\TalentOpsScoutSetup.exe"; Start-Process "$env:TEMP\\TalentOpsScoutSetup.exe"`;
                      navigator.clipboard.writeText(cmd);
                      toast.success('PowerShell command copied! Run in terminal to install directly.');
                    }}
                    style={{
                      padding: '8px 10px', background: 'var(--panel-bg, #18181b)', color: 'var(--text-secondary, #a1a1aa)',
                      border: '1px solid var(--card-border, #27272a)', borderRadius: 8, fontSize: 11, fontWeight: 600,
                      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
                      transition: 'all 0.15s ease'
                    }}
                    title="Copy 1-line PowerShell install command (unblocks files and completely bypasses browser download warnings)"
                  >
                    <Terminal size={12} color="#60a5fa" />
                    <span>PowerShell Install</span>
                  </button>
                </div>

                {/* Windows Defender / Code 225 Troubleshooting */}
                <div style={{
                  marginTop: 10, padding: '10px 12px', borderRadius: 8,
                  background: 'rgba(239, 68, 68, 0.07)', border: '1px solid rgba(239, 68, 68, 0.22)',
                  fontSize: 11, color: 'var(--text-secondary, #a1a1aa)', lineHeight: 1.4
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ color: '#f87171', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span>🛡️ Antivirus or Code 225 Warning?</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        const fixCmd = `Unblock-File -Path "$env:LOCALAPPDATA\\Programs\\TalentOpsScout\\*"; Start-Process "$env:LOCALAPPDATA\\Programs\\TalentOpsScout\\TalentOpsScout.exe"`;
                        navigator.clipboard.writeText(fixCmd);
                        toast.success('10-second fix command copied! Paste into PowerShell to launch.');
                      }}
                      style={{
                        background: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.4)',
                        color: '#fca5a5', padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 10, fontWeight: 700
                      }}
                    >
                      Copy 10s Fix
                    </button>
                  </div>
                  <span>
                    Windows Defender flags new screen OCR engines before they build reputation. If blocked, open <b>Windows Security &rarr; Protection history &rarr; Allow on device</b>, or click <b>Copy 10s Fix</b> and paste into PowerShell.
                  </span>
                </div>
              </div>
            </div>

            {/* CARD 2: PAIRING CODE / ACCOUNT LINKING */}
            {!user ? (
              <div style={{
                background: 'var(--card-bg, #121214)',
                border: '1px solid var(--card-border, rgba(228, 228, 231, 0.35))', borderRadius: 14, padding: '24px 26px',
                display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                boxShadow: 'var(--shadow)'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: 10, background: 'rgba(228, 228, 231, 0.15)',
                      border: '1px solid var(--card-border, rgba(228, 228, 231, 0.3))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-primary, #e4e4e7)'
                    }}>
                      <Zap size={22} />
                    </div>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary, #e4e4e7)', letterSpacing: 0.5 }}>STEP 2: LINK TO YOUR ACCOUNT</div>
                      <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary, #fafafa)' }}>Pair Desktop Scout</div>
                    </div>
                  </div>

                  <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 13, lineHeight: 1.5, marginBottom: 16 }}>
                    When you run <b>TalentOpsScoutSetup.exe</b> and launch Scout, it displays a bold 4-character pairing code on your screen (e.g. <b>TOS-8492</b>). Sign in to your TalentOps account to connect your device:
                  </p>

                  <div style={{
                    background: 'var(--panel-bg, #0b0b0c)',
                    border: '1px dashed var(--card-border, #27272a)',
                    borderRadius: 10,
                    padding: '16px',
                    textAlign: 'center',
                    marginBottom: 16
                  }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted, #a1a1aa)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                      Desktop Scout displays on screen:
                    </div>
                    <code style={{
                      display: 'inline-block',
                      padding: '8px 24px',
                      background: '#09090b',
                      border: '1px solid #27272a',
                      borderRadius: 8,
                      color: '#34d399',
                      fontSize: 22,
                      fontWeight: 800,
                      letterSpacing: 4,
                      fontFamily: 'monospace'
                    }}>
                      TOS-____
                    </code>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <button
                    onClick={() => navigate({ to: '/login', search: { redirect: '/download-scout' } })}
                    style={{
                      width: '100%', padding: '12px 18px', background: 'linear-gradient(135deg, #a1a1aa 0%, #52525b 100%)',
                      color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 700, cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                      boxShadow: '0 4px 15px rgba(161, 161, 170, 0.35)'
                    }}
                  >
                    <UserCheck size={16} />
                    <span>Sign In to Enter Pairing Code</span>
                  </button>
                  <button
                    onClick={() => navigate({ to: '/register', search: { redirect: '/download-scout' } })}
                    style={{
                      width: '100%', padding: '10px 18px', background: 'var(--panel-bg, #18181b)',
                      color: 'var(--text-secondary, #a1a1aa)', border: '1px solid var(--card-border, #27272a)',
                      borderRadius: 10, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6
                    }}
                  >
                    <span>Need an account? Create Workspace</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            ) : (
              <div style={{
                background: 'var(--card-bg, #121214)',
                border: '1px solid var(--card-border, rgba(228, 228, 231, 0.35))', borderRadius: 14, padding: '24px 26px',
                display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                boxShadow: 'var(--shadow)'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: 10, background: 'rgba(228, 228, 231, 0.15)',
                      border: '1px solid var(--card-border, rgba(228, 228, 231, 0.3))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-primary, #e4e4e7)'
                    }}>
                      <Zap size={22} />
                    </div>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary, #e4e4e7)', letterSpacing: 0.5 }}>STEP 2: LINK TO YOUR ACCOUNT</div>
                      <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary, #fafafa)' }}>Pair Desktop Scout</div>
                    </div>
                  </div>

                  {/* Personal Dedicated Activation Code (if assigned) */}
                  {myDeviceData?.active_activation_code && (
                    <div style={{
                      background: 'rgba(59, 130, 246, 0.1)',
                      border: '1px solid rgba(59, 130, 246, 0.35)',
                      borderRadius: 10,
                      padding: '14px 16px',
                      marginBottom: 16
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <Key size={14} color="#60a5fa" />
                          <span style={{ fontSize: 11, fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                            Your Dedicated Activation Code
                          </span>
                        </div>
                        <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 4, background: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6', fontWeight: 700 }}>
                          {myDeviceData.active_activation_label || 'Permanent'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                        <code style={{
                          flex: 1,
                          padding: '10px 14px',
                          background: 'var(--bg-base, #09090b)',
                          border: '1px dashed rgba(59, 130, 246, 0.6)',
                          borderRadius: 8,
                          color: '#60a5fa',
                          fontSize: 16,
                          fontWeight: 800,
                          letterSpacing: 2,
                          fontFamily: 'monospace',
                          textAlign: 'center'
                        }}>
                          {myDeviceData.active_activation_code}
                        </code>
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(myDeviceData.active_activation_code);
                            toast.success('Activation code copied to clipboard!');
                          }}
                          style={{
                            padding: '10px 14px',
                            background: '#2563eb',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 8,
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6
                          }}
                        >
                          <Copy size={14} />
                          <span>Copy</span>
                        </button>
                      </div>

                      <p style={{ color: 'var(--text-muted, #94a3b8)', fontSize: 11, lineHeight: 1.4, margin: 0 }}>
                        💡 <b>Where to enter in Scout:</b> In Desktop Scout, click <b>&quot;Switch Account&quot;</b> at top-right (or <b>Settings → Node Identity</b>), click <i>&quot;Have an admin activation code? Enter it manually&quot;</i>, paste this code, and click <b>Connect Account</b>.
                      </p>
                    </div>
                  )}

                  <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 13, lineHeight: 1.5, marginBottom: 16 }}>
                    {myDeviceData?.active_activation_code
                      ? 'Alternatively, enter the 4-character code shown on your Desktop Scout app (e.g. TOS-8492) below:'
                      : 'Launch Desktop Scout on your PC. It displays a 4-character pairing code on your screen (e.g. TOS-8492). Enter that code below to connect your device:'}
                  </p>

                  <form onSubmit={handleVerifyPairingCode} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <input
                        type="text"
                        placeholder="TOS-____"
                        value={pairingCodeInput}
                        onChange={(e) => {
                          setPairingCodeInput(e.target.value.toUpperCase());
                          setPairingError('');
                        }}
                        maxLength={10}
                        style={{
                          flex: 1, padding: '12px 16px', background: 'var(--bg-base, #0b0b0c)', border: '1px solid var(--card-border, rgba(228, 228, 231, 0.4))',
                          borderRadius: 10, color: 'var(--text-primary, #e4e4e7)', fontSize: 18, fontWeight: 800, letterSpacing: 3,
                          fontFamily: 'monospace', textTransform: 'uppercase', textAlign: 'center', outline: 'none'
                        }}
                      />
                      <button
                        type="submit"
                        disabled={pairingLoading || !pairingCodeInput.trim()}
                        style={{
                          padding: '13px 22px', background: 'linear-gradient(135deg, #a1a1aa 0%, #52525b 100%)',
                          color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 700,
                          cursor: pairingLoading || !pairingCodeInput.trim() ? 'not-allowed' : 'pointer',
                          display: 'flex', alignItems: 'center', gap: 8, opacity: pairingLoading || !pairingCodeInput.trim() ? 0.6 : 1,
                          boxShadow: '0 4px 15px rgba(161, 161, 170, 0.35)', whiteSpace: 'nowrap'
                        }}
                      >
                        {pairingLoading ? <RefreshCw size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                        <span>{pairingLoading ? 'Linking...' : 'Connect Device'}</span>
                      </button>
                    </div>
                  </form>

                  {pairingError && (
                    <div style={{
                      background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.35)',
                      borderRadius: 8, padding: '10px 14px', color: '#f87171', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12
                    }}>
                      <AlertCircle size={15} flexShrink={0} />
                      <span>{pairingError}</span>
                    </div>
                  )}

                  {pairingSuccess && (
                    <div style={{
                      background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.35)',
                      borderRadius: 8, padding: '10px 14px', color: '#34d399', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12
                    }}>
                      <CheckCircle2 size={15} flexShrink={0} />
                      <span>{pairingSuccess}</span>
                    </div>
                  )}
                </div>

                <div style={{ fontSize: 11, color: '#71717a', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <ShieldCheck size={14} color="#10b981" />
                  <span>Encrypted end-to-end device token bound strictly to your user profile.</span>
                </div>
              </div>
            )}
          </div>

          {/* STEP 3: MY PAIRED COMPANION HARDWARE CARDS (Rendered if logged in) */}
          {user && (
            <div style={{ marginBottom: 32 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <h3 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary, #fafafa)', margin: 0 }}>
                    My Paired Companions ({myDeviceData?.devices?.length || 0})
                  </h3>
                  <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 12, margin: '2px 0 0' }}>
                    Desktop devices bound to your account and reporting continuous recruitment telemetry.
                  </p>
                </div>

                <button
                  onClick={() => refetchMyDevice()}
                  disabled={loadingMyDevice}
                  style={{
                    padding: '6px 12px', background: 'var(--panel-bg, #232326)', border: '1px solid var(--card-border, #27272a)',
                    color: 'var(--text-secondary, #a1a1aa)', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 6
                  }}
                >
                  <RefreshCw size={12} className={loadingMyDevice ? 'animate-spin' : ''} />
                  <span>Refresh Status</span>
                </button>
              </div>

              {myDeviceData?.devices && myDeviceData.devices.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
                  {myDeviceData.devices.map((dev) => (
                    <div
                      key={dev.device_id}
                      style={{
                        background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12,
                        padding: '18px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div style={{
                              width: 36, height: 36, borderRadius: 8, background: 'var(--panel-bg, #232326)',
                              display: 'flex', alignItems: 'center', justifyContent: 'center', color: dev.is_online ? '#34d399' : 'var(--text-muted, #a1a1aa)'
                            }}>
                              <Laptop size={18} />
                            </div>
                            <div>
                              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary, #fafafa)' }}>
                                {dev.name || 'Windows Desktop'}
                              </div>
                              <div style={{ fontSize: 11, color: 'var(--text-muted, #71717a)', fontFamily: 'monospace' }}>
                                {dev.device_id?.substring(0, 16)}...
                              </div>
                            </div>
                          </div>

                          <span style={{
                            padding: '3px 8px', borderRadius: 12, fontSize: 10, fontWeight: 700,
                            background: dev.is_online ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                            color: dev.is_online ? '#34d399' : 'var(--text-muted, #a1a1aa)',
                            border: `1px solid ${dev.is_online ? 'rgba(16, 185, 129, 0.3)' : 'rgba(100, 116, 139, 0.3)'}`,
                            display: 'flex', alignItems: 'center', gap: 5
                          }}>
                            <span style={{
                              width: 6, height: 6, borderRadius: '50%',
                              background: dev.is_online ? '#10b981' : 'var(--text-muted, #71717a)'
                            }} />
                            {dev.is_online ? 'ONLINE & STREAMING' : 'STANDBY'}
                          </span>
                        </div>

                        <div style={{
                          background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8,
                          padding: '10px 14px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16
                        }}>
                          <div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted, #71717a)', textTransform: 'uppercase' }}>Version</div>
                            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary, #e4e4e7)', fontFamily: 'monospace' }}>
                              v{dev.version || displayVersion}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted, #71717a)', textTransform: 'uppercase' }}>Last Active</div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary, #fafafa)' }}>
                              {formatTimeAgo(dev.last_seen_at)}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted, #71717a)', textTransform: 'uppercase' }}>Candidates Added</div>
                            <div style={{ fontSize: 12, fontWeight: 700, color: '#34d399' }}>
                              {dev.total_accepted || 0}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted, #71717a)', textTransform: 'uppercase' }}>Observations</div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary, #a1a1aa)' }}>
                              {dev.total_submitted || 0}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                          onClick={() => handleDisconnectDevice(dev.device_id)}
                          disabled={disconnectingId === dev.device_id}
                          style={{
                            padding: '6px 12px', background: 'transparent', border: '1px solid rgba(239, 68, 68, 0.3)',
                            color: '#f87171', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 5
                          }}
                        >
                          <Trash2 size={12} />
                          <span>{disconnectingId === dev.device_id ? 'Disconnecting...' : 'Disconnect'}</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  background: 'var(--card-bg, #121214)', border: '1px dashed var(--card-border, #232326)', borderRadius: 14,
                  padding: '36px 24px', textAlign: 'center'
                }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: 12, background: 'rgba(228, 228, 231, 0.1)',
                    border: '1px solid var(--card-border, rgba(228, 228, 231, 0.2))', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', color: 'var(--text-primary, #e4e4e7)', margin: '0 auto 14px'
                  }}>
                    <Laptop size={24} />
                  </div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary, #fafafa)', marginBottom: 6 }}>
                    No Desktop Companion Connected Yet
                  </div>
                  <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 13, maxWidth: 520, margin: '0 auto 18px', lineHeight: 1.5 }}>
                    Download the installer above and launch Desktop Scout. Enter the pairing code displayed on your desktop into the box above to link this computer in seconds.
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
                    <button
                      onClick={handleDownload}
                      style={{
                        padding: '8px 16px', background: '#10b981', color: '#fff', border: 'none',
                        borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6
                      }}
                    >
                      <Download size={14} />
                      <span>Download Scout {displayVersion}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================================= */}
          {/* SUPPORTED SOURCING PLATFORMS & TARGETS (9 ENGINE CATEGORIES)              */}
          {/* ========================================================================= */}
          <div style={{ marginBottom: 36 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 14, marginBottom: 16 }}>
              <div>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#34d399', fontSize: 11, fontWeight: 700, letterSpacing: 0.5, marginBottom: 4 }}>
                  <Globe size={13} />
                  <span>NATIVE BROWSER &amp; WINDOW MONITORING ALLOWLIST</span>
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary, #fafafa)', margin: '0 0 4px 0' }}>
                  Supported Sourcing Platforms (9 Categories)
                </h3>
                <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 13, margin: 0, maxWidth: 840, lineHeight: 1.5 }}>
                  Scout Desktop automatically identifies active recruiting windows across these verified domains, extracts candidate fields via OCR and DOM parsing, and safely ignores all non-work applications.
                </p>
              </div>

              {/* Category Filter Pills */}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <button
                  onClick={() => setActivePlatformCategory('ALL')}
                  style={{
                    padding: '5px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer',
                    background: activePlatformCategory === 'ALL' ? 'var(--text-primary, #e4e4e7)' : 'var(--panel-bg, #0b0b0c)',
                    color: activePlatformCategory === 'ALL' ? 'var(--bg-base, #09090b)' : 'var(--text-secondary, #a1a1aa)',
                    border: activePlatformCategory === 'ALL' ? 'none' : '1px solid var(--card-border, #27272a)'
                  }}
                >
                  All Platforms (9)
                </button>
                {SCOUT_PLATFORM_CATEGORIES.map(cat => {
                  const isActive = activePlatformCategory === cat.id;
                  return (
                    <button
                      key={cat.id}
                      onClick={() => setActivePlatformCategory(cat.id)}
                      style={{
                        padding: '5px 11px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                        background: isActive ? cat.color : 'var(--panel-bg, #0b0b0c)',
                        color: isActive ? '#fff' : 'var(--text-secondary, #a1a1aa)',
                        border: isActive ? `1px solid ${cat.color}` : '1px solid var(--card-border, #27272a)'
                      }}
                    >
                      {cat.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Platform Categories Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
              {displayedPlatforms.map(cat => {
                const CatIcon = cat.icon;
                return (
                  <div
                    key={cat.id}
                    style={{
                      background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12,
                      padding: '20px 22px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                      boxShadow: 'var(--shadow)'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{
                            width: 32, height: 32, borderRadius: 8, background: `${cat.color}20`,
                            border: `1px solid ${cat.color}40`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: cat.color
                          }}>
                            <CatIcon size={16} />
                          </div>
                          <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-primary, #fafafa)' }}>
                            {cat.name}
                          </span>
                        </div>
                        <span style={{
                          padding: '2px 8px', borderRadius: 12, fontSize: 10, fontWeight: 700,
                          background: `${cat.color}15`, color: cat.color, border: `1px solid ${cat.color}35`
                        }}>
                          {cat.badge}
                        </span>
                      </div>

                      <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 12, margin: '0 0 14px 0', lineHeight: 1.4 }}>
                        {cat.description}
                      </p>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {cat.targets.map((t, idx) => (
                          <div
                            key={idx}
                            style={{
                              background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #1f1f23)',
                              borderRadius: 8, padding: '8px 12px'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary, #e4e4e7)' }}>
                                {t.name}
                              </span>
                              <code style={{ fontSize: 10, color: cat.color, background: 'rgba(0,0,0,0.3)', padding: '1px 6px', borderRadius: 4 }}>
                                {t.scope}
                              </code>
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted, #71717a)', lineHeight: 1.3 }}>
                              {t.details}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* DESKTOP COMMAND CENTER ARCHITECTURE (9 STACKED PAGES / OBSIDIAN GUI)       */}
          {/* ========================================================================= */}
          <div style={{ marginBottom: 36 }}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#60a5fa', fontSize: 11, fontWeight: 700, letterSpacing: 0.5, marginBottom: 4 }}>
                <Monitor size={13} />
                <span>NATIVE OBSIDIAN WORKSPACE &amp; ENGINE ARCHITECTURE</span>
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary, #fafafa)', margin: '0 0 4px 0' }}>
                Desktop Scout Command Center (7 Left-Rail Views • 9 Stacked Pages)
              </h3>
              <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 13, margin: 0, maxWidth: 840, lineHeight: 1.5 }}>
                Every download of TalentOps Scout includes the full Obsidian Command Center GUI built natively in PySide6 with 7 operational navigation tabs and 9 interactive workspace views:
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14 }}>
              {COMMAND_CENTER_VIEWS.map(v => {
                const VIcon = v.icon;
                return (
                  <div
                    key={v.id}
                    style={{
                      background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 10,
                      padding: '16px 18px', display: 'flex', gap: 12, alignItems: 'flex-start'
                    }}
                  >
                    <div style={{
                      width: 34, height: 34, borderRadius: 8, background: 'rgba(228, 228, 231, 0.1)',
                      border: '1px solid var(--card-border, rgba(228, 228, 231, 0.2))', display: 'flex', alignItems: 'center',
                      justifyContent: 'center', color: 'var(--text-primary, #e4e4e7)', flexShrink: 0
                    }}>
                      <VIcon size={16} />
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary, #fafafa)', marginBottom: 4 }}>
                        {v.name}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', lineHeight: 1.45 }}>
                        {v.desc}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* ENTERPRISE TRUST & SECURITY PILLARS                                       */}
          {/* ========================================================================= */}
          <div style={{ marginBottom: 36 }}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#10b981', fontSize: 11, fontWeight: 700, letterSpacing: 0.5, marginBottom: 4 }}>
                <ShieldCheck size={13} />
                <span>ENTERPRISE PRIVACY &amp; SECURITY GUARANTEES</span>
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary, #fafafa)', margin: '0 0 4px 0' }}>
                Zero Passwords • Local SQLite Buffering • Signed Releases
              </h3>
              <p style={{ color: 'var(--text-secondary, #a1a1aa)', fontSize: 13, margin: 0, maxWidth: 840, lineHeight: 1.5 }}>
                Built with zero-trust local isolation. Designed for enterprise compliance with zero intrusion into private browser data.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
              {TRUST_PILLARS.map((p, idx) => {
                const PIcon = p.icon;
                return (
                  <div
                    key={idx}
                    style={{
                      background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 10,
                      padding: '18px 20px', display: 'flex', flexDirection: 'column'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: 8, background: `${p.color}20`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', color: p.color
                      }}>
                        <PIcon size={16} />
                      </div>
                      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary, #fafafa)' }}>
                        {p.title}
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', margin: 0, lineHeight: 1.5 }}>
                      {p.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* STEP-BY-STEP SETUP GUIDE & WINDOWS SMARTSCREEN TRUST NOTICE               */}
          {/* ========================================================================= */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
            <button
              onClick={() => setShowSetupGuide(!showSetupGuide)}
              style={{
                padding: '9px 14px', background: 'var(--panel-bg, #0b0b0c)', color: 'var(--text-secondary, #a1a1aa)',
                border: '1px solid var(--card-border, #232326)', borderRadius: 8, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
              }}
            >
              <Info size={14} />
              <span>{showSetupGuide ? 'Hide 3-Step Setup Guide' : 'View 3-Step Setup Guide'}</span>
              {showSetupGuide ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            <button
              onClick={() => setShowSecurityNotice(!showSecurityNotice)}
              style={{
                padding: '9px 14px', background: 'var(--panel-bg, #0b0b0c)', color: '#f59e0b',
                border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 8, fontSize: 12, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
              }}
            >
              <ShieldAlert size={14} />
              <span>{showSecurityNotice ? 'Hide Windows SmartScreen Notice' : 'Windows SmartScreen & Trust Notice'}</span>
              {showSecurityNotice ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>

          {showSetupGuide && (
            <div style={{
              marginBottom: 20, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14
            }}>
              <div style={{ background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary, #e4e4e7)', marginBottom: 4 }}>1. Download &amp; Run</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', lineHeight: 1.5 }}>
                  Run <code>TalentOpsScoutSetup.exe</code> (51.6 MB). Installs silently in 5 seconds into your user profile with no administrator prompt needed.
                </div>
              </div>
              <div style={{ background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', marginBottom: 4 }}>2. Note the Pairing Code</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', lineHeight: 1.5 }}>
                  Scout Desktop launches and displays a bold code (e.g. <code>TOS-8492</code>). Enter that code into the box above to link to your account.
                </div>
              </div>
              <div style={{ background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted, #a1a1aa)', marginBottom: 4 }}>3. Automatic Sourcing</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', lineHeight: 1.5 }}>
                  Scout minimizes to your system tray. As you browse candidates on LinkedIn, ZoomInfo, GitHub, or ATS platforms, contacts are extracted and staged automatically.
                </div>
              </div>
            </div>
          )}

          {showSecurityNotice && (
            <div style={{
              marginBottom: 20, background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.25)',
              borderRadius: 10, padding: 16
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, color: '#f59e0b', fontSize: 13, fontWeight: 700 }}>
                <ShieldAlert size={16} />
                <span>Browser Security &amp; Windows SmartScreen Notice</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', lineHeight: 1.6 }}>
                <p style={{ margin: '0 0 8px 0', color: 'var(--text-primary, #fafafa)', fontWeight: 600 }}>
                  Why does Chrome show "Virus detected" or Edge/Windows show a warning?
                </p>
                <p style={{ margin: '0 0 8px 0' }}>
                  Newly published enterprise software undergoes a <b>reputation ramp-up period</b> with Google Safe Browsing and Microsoft SmartScreen.
                  This is standard for internal tooling and does <b>not</b> mean the file contains malware. TalentOps Scout has been scanned
                  by Windows Defender with <span style={{ color: '#10b981', fontWeight: 600 }}>zero threats detected</span>.
                </p>

                <div style={{
                  background: 'var(--card-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: 12, marginBottom: 10
                }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#ef4444', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <AlertTriangle size={13} />
                    Google Chrome — "Virus detected" or "Dangerous file"
                  </div>
                  <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--text-secondary, #d4d4d8)' }}>
                    <li>When the download bar shows "Virus detected", click the <b>⋮</b> (three-dot menu) on the download item.</li>
                    <li>Select <b>"Keep dangerous file"</b> from the dropdown.</li>
                    <li>In the confirmation dialog, click <b>"Keep anyway"</b>.</li>
                    <li>Alternatively: Go to <code>chrome://downloads</code> → find the file → click <b>"Keep dangerous file"</b>.</li>
                  </ol>
                </div>

                <div style={{
                  background: 'var(--card-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: 12, marginBottom: 10
                }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#3b82f6', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Shield size={13} />
                    Microsoft Edge — "This file isn't commonly downloaded"
                  </div>
                  <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--text-secondary, #d4d4d8)' }}>
                    <li>Click the <b>⋯</b> menu on the download bar → select <b>"Keep"</b>.</li>
                    <li>If prompted again, click <b>"Show more"</b> → <b>"Keep anyway"</b>.</li>
                  </ol>
                </div>

                <div style={{
                  background: 'var(--card-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: 12, marginBottom: 10
                }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#f59e0b', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ShieldCheck size={13} />
                    Windows SmartScreen — "Windows protected your PC"
                  </div>
                  <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: 'var(--text-secondary, #d4d4d8)' }}>
                    <li>Click <b>"More info"</b> (the small link text below the warning).</li>
                    <li>Click <b>"Run anyway"</b>.</li>
                  </ol>
                  <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted, #71717a)', borderTop: '1px dashed var(--card-border, #232326)', paddingTop: 6 }}>
                    💡 <b>Terminal shortcut:</b> Run <code style={{ fontSize: 10, color: 'var(--text-primary, #e4e4e7)' }}>Unblock-File "$env:USERPROFILE\Downloads\TalentOpsScoutSetup.exe"</code> in PowerShell to remove the download flag immediately.
                  </div>
                </div>

                {releaseInfo?.sha256 && (
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.2)',
                    borderRadius: 8, padding: 10, marginTop: 4
                  }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <CheckCircle2 size={13} />
                      File Integrity — SHA-256 Checksum
                    </div>
                    <code style={{
                      fontSize: 10, color: 'var(--text-secondary, #a1a1aa)', wordBreak: 'break-all', lineHeight: 1.4,
                      display: 'block', background: 'var(--panel-bg, #0b0b0c)', padding: 6, borderRadius: 4,
                      fontFamily: 'monospace', cursor: 'pointer'
                    }}
                      title="Click to copy"
                      onClick={() => { navigator.clipboard.writeText(releaseInfo.sha256); toast.success('SHA-256 copied to clipboard'); }}
                    >
                      {releaseInfo.sha256}
                    </code>
                    <div style={{ fontSize: 10, color: '#71717a', marginTop: 4 }}>
                      Verify with PowerShell: <code style={{ fontSize: 10 }}>Get-FileHash TalentOpsScoutSetup.exe -Algorithm SHA256</code>
                    </div>
                  </div>
                )}

                <div style={{ marginTop: 8, fontSize: 11, color: '#71717a' }}>
                  <b>Privacy Guardrail:</b> Scout never accesses passwords, cookies, financial info, or personal browsing data.
                  Only candidate profile fields (name, title, company) are captured from sourcing platforms.
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* ADMIN VIEW 1: SCOUT USERS & CONTRIBUTORS INTELLIGENCE                     */}
      {/* ========================================================================= */}
      {isAdmin && currentView === 'contributors' && (
        <div>
          {/* Quick Companion Pairing Strip for Admins */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(228, 228, 231, 0.05) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 12, padding: '16px 20px',
            marginBottom: 20, boxShadow: '0 4px 20px rgba(0,0,0,0.18)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 10,
                  background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981', flexShrink: 0
                }}>
                  <Laptop size={22} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary, #fafafa)' }}>
                      TalentOps Scout Desktop
                    </span>
                    <span style={{
                      background: 'rgba(16, 185, 129, 0.2)', color: '#34d399',
                      border: '1px solid rgba(16, 185, 129, 0.35)', padding: '2px 7px',
                      borderRadius: 5, fontSize: 11, fontWeight: 700, fontFamily: 'monospace'
                    }}>
                      {displayVersion} Production
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted, #71717a)' }}>• Windows 10/11 64-bit ({displaySize})</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', marginTop: 2 }}>
                    Native Win32 background engine with offline OCR and local SQLite buffer queue. Replaces legacy browser extension.
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  style={{
                    padding: '9px 18px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 700,
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                    boxShadow: '0 2px 10px rgba(16, 185, 129, 0.35)',
                    opacity: downloading ? 0.7 : 1
                  }}
                >
                  <Download size={15} />
                  <span>{downloading ? 'Starting...' : `Download ${displayVersion}`}</span>
                </button>

                {/* Instant Inline Device Pairing Input */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6, background: 'var(--panel-bg, #020617)',
                  border: '1px solid var(--card-border, #27272a)', borderRadius: 8, padding: '3px 8px'
                }}>
                  <Key size={14} color="var(--text-secondary, #e4e4e7)" />
                  <input
                    type="text"
                    placeholder="CODE: TOS-XXXX"
                    value={pairingCodeInput}
                    onChange={(e) => {
                      setPairingCodeInput(e.target.value.toUpperCase());
                      setPairingError('');
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleVerifyPairingCode();
                    }}
                    style={{
                      width: 125, background: 'transparent', border: 'none',
                      color: 'var(--text-primary, #e4e4e7)', fontFamily: 'monospace', fontWeight: 800,
                      fontSize: 12, outline: 'none'
                    }}
                  />
                  <button
                    onClick={handleVerifyPairingCode}
                    disabled={pairingLoading || !pairingCodeInput.trim()}
                    style={{
                      padding: '5px 12px', background: 'var(--text-primary, #e4e4e7)', color: 'var(--bg-base, #fff)',
                      border: 'none', borderRadius: 6, fontSize: 11, fontWeight: 700,
                      cursor: 'pointer', opacity: (pairingLoading || !pairingCodeInput.trim()) ? 0.6 : 1
                    }}
                  >
                    {pairingLoading ? 'Linking...' : 'Connect Device'}
                  </button>
                </div>

                <button
                  onClick={() => setShowAddModal(true)}
                  style={{
                    padding: '9px 14px', background: 'var(--panel-bg, #0b0b0c)', color: 'var(--text-secondary, #a1a1aa)',
                    border: '1px solid var(--card-border, #232326)', borderRadius: 8, fontSize: 12, fontWeight: 600,
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6
                  }}
                >
                  <Zap size={13} />
                  <span>Issue 10m Code</span>
                </button>
              </div>
            </div>

            {(pairingError || pairingSuccess) && (
              <div style={{ marginTop: 12 }}>
                {pairingError && (
                  <div style={{
                    background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)',
                    borderRadius: 8, padding: '8px 14px', color: '#f87171', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8
                  }}>
                    <AlertCircle size={15} flexShrink={0} />
                    <span>{pairingError}</span>
                  </div>
                )}
                {pairingSuccess && (
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)',
                    borderRadius: 8, padding: '8px 14px', color: '#34d399', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8
                  }}>
                    <CheckCircle2 size={15} flexShrink={0} />
                    <span>{pairingSuccess}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Admin Force-Connection & Remote Provisioning Hub */}
          <div style={{
            background: 'var(--card-bg, #121214)',
            border: '1px solid var(--card-border, rgba(228, 228, 231, 0.35))',
            borderRadius: 14,
            padding: '22px 26px',
            marginBottom: 24,
            boxShadow: 'var(--shadow)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14, marginBottom: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10,
                  background: 'rgba(228, 228, 231, 0.15)', border: '1px solid rgba(228, 228, 231, 0.35)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-primary, #e4e4e7)'
                }}>
                  <Zap size={20} />
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary, #fafafa)', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span>Admin Force-Pair &amp; User Provisioning Hub</span>
                    <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 12, background: 'rgba(228, 228, 231, 0.2)', color: 'var(--text-primary, #e4e4e7)', fontWeight: 700 }}>
                      ADMIN OVERRIDE
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', marginTop: 2 }}>
                    Pair desktop hardware or generate activation codes on behalf of any team member if they cannot connect themselves.
                  </div>
                </div>
              </div>

              {/* Target User Selector */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 12, color: 'var(--text-secondary, #d4d4d8)', fontWeight: 700 }}>Target Team Member:</span>
                <select
                  value={targetUserEmail}
                  onChange={(e) => {
                    setTargetUserEmail(e.target.value);
                    setAdminGeneratedCode(null);
                  }}
                  style={{
                    background: 'var(--bg-base, #0b0b0c)', border: '1px solid var(--card-border, #e4e4e7)', borderRadius: 8,
                    color: targetUserEmail ? 'var(--text-primary, #e4e4e7)' : 'var(--text-muted, #a1a1aa)', padding: '9px 14px', fontSize: 13,
                    fontWeight: 700, outline: 'none', cursor: 'pointer', minWidth: 280
                  }}
                >
                  <option value="">-- Choose User to Force-Connect --</option>
                  {provisionableUsers.map(u => (
                    <option key={u.id} value={u.email}>
                      {u.name} ({u.email}) {u.has_device ? '✓ [Connected]' : '○ [No Device]'}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Two Operational Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16 }}>
              {/* Option A: Force-Pair 4-char Code from Remote Desktop */}
              <div style={{ background: 'var(--card-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 10, padding: '16px 20px', boxShadow: 'var(--shadow)' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary, #e4e4e7)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Key size={15} />
                  <span>Option 1: Force-Pair 4-Char Desktop Code</span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-secondary, #a1a1aa)', margin: '0 0 12px 0', lineHeight: 1.5 }}>
                  Enter the 4-char code displayed on the remote PC (e.g. <b>TOS-8492</b>). Links the device directly to <b>{targetUserEmail || 'the selected user'}</b>.
                </p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    placeholder="TOS-____"
                    value={pairingCodeInput}
                    onChange={(e) => {
                      setPairingCodeInput(e.target.value.toUpperCase());
                      setPairingError('');
                    }}
                    style={{
                      flex: 1, padding: '9px 14px', background: 'var(--bg-base, #020617)', border: '1px solid var(--card-border, #27272a)',
                      borderRadius: 8, color: 'var(--text-primary, #e4e4e7)', fontFamily: 'monospace', fontWeight: 800,
                      fontSize: 15, textTransform: 'uppercase', outline: 'none'
                    }}
                  />
                  <button
                    onClick={handleVerifyPairingCode}
                    disabled={pairingLoading || !pairingCodeInput.trim() || !targetUserEmail}
                    style={{
                      padding: '9px 18px', background: targetUserEmail ? 'linear-gradient(135deg, #a1a1aa 0%, #52525b 100%)' : 'var(--panel-bg, #27272a)',
                      color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 700,
                      cursor: (pairingLoading || !pairingCodeInput.trim() || !targetUserEmail) ? 'not-allowed' : 'pointer',
                      display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap'
                    }}
                  >
                    {pairingLoading ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
                    <span>⚡ Force-Pair to User</span>
                  </button>
                </div>
                {!targetUserEmail && (
                  <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 8 }}>
                    ⚠️ Select a target team member in the dropdown above to enable force-pairing.
                  </div>
                )}
              </div>

              {/* Option B: Generate Dedicated Activation Code */}
              <div style={{ background: 'var(--card-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 10, padding: '16px 20px', boxShadow: 'var(--shadow)' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#10b981', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Sparkles size={15} />
                  <span>Option 2: Generate Dedicated User Code (Permanent • Never Expires)</span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-secondary, #a1a1aa)', margin: '0 0 12px 0', lineHeight: 1.5 }}>
                  Generates an authenticated <code>TOS-XXXX-XXXX</code> code bound to <b>{targetUserEmail || 'the selected user'}</b> for manual desktop entry. Once paired, the device remains paired forever.
                </p>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={handleAdminGenerateCode}
                    disabled={generatingCode || !targetUserEmail}
                    style={{
                      padding: '9px 18px', background: targetUserEmail ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : '#27272a',
                      color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 700,
                      cursor: (generatingCode || !targetUserEmail) ? 'not-allowed' : 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, whiteSpace: 'nowrap'
                    }}
                  >
                    {generatingCode ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
                    <span>{adminGeneratedCode ? 'Regenerate Code' : 'Generate User Code'}</span>
                  </button>

                  {adminGeneratedCode && (
                    <div style={{
                      flex: 1, minWidth: 200, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      background: 'var(--panel-bg, #020617)', border: '1px solid #10b981', borderRadius: 8, padding: '7px 12px'
                    }}>
                      <span style={{ fontFamily: 'monospace', fontWeight: 800, color: '#34d399', fontSize: 15, letterSpacing: 1 }}>
                        {adminGeneratedCode.code}
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(adminGeneratedCode.code);
                          setAdminCodeCopied(true);
                          toast.success('Activation code copied!');
                          setTimeout(() => setAdminCodeCopied(false), 2000);
                        }}
                        style={{
                          background: adminCodeCopied ? '#10b981' : 'var(--card-bg, #232326)', border: 'none',
                          borderRadius: 6, color: '#fff', fontSize: 11, fontWeight: 700, padding: '4px 10px', cursor: 'pointer'
                        }}
                      >
                        {adminCodeCopied ? '✓ Copied' : 'Copy'}
                      </button>
                    </div>
                  )}
                </div>
                {adminGeneratedCode && (
                  <div style={{ fontSize: 11, color: '#34d399', marginTop: 8 }}>
                    ✓ Pre-bound to {adminGeneratedCode.target_user_name || adminGeneratedCode.owner_email}. Permanent (Never Expires • Unlimited Uses).
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Reconnection / Error Banner */}
          {isError && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.35)',
              borderRadius: 8, padding: '12px 18px', marginBottom: 16, display: 'flex',
              alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#f87171', fontSize: 13 }}>
                <AlertCircle size={18} />
                <span>Backend telemetry engine is currently deploying or reconnecting. Telemetry will sync automatically.</span>
              </div>
              <button
                onClick={() => refetch()}
                disabled={isFetching}
                style={{
                  padding: '6px 14px', background: 'var(--card-bg, #232326)', border: '1px solid var(--card-border, #27272a)',
                  color: 'var(--text-primary, #fafafa)', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer'
                }}
              >
                {isFetching ? 'Syncing...' : 'Retry Connection'}
              </button>
            </div>
          )}

          {/* Navigation Guidance Strip */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12,
            background: 'rgba(228, 228, 231, 0.08)', border: '1px solid rgba(228, 228, 231, 0.22)',
            borderRadius: 10, padding: '10px 16px', marginBottom: 16, fontSize: 12
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#e4e4e7' }}>
              <Users size={16} />
              <span>
                Currently viewing <b>Contributor Directory (User Accounts)</b>. To inspect individual physical hardware machines, companion nodes &amp; live streams, switch to <b>Device Fleet &amp; Nodes</b>.
              </span>
            </div>
            <button
              onClick={() => setAdminView('fleet_nodes')}
              style={{
                padding: '5px 14px', background: '#a1a1aa', color: '#fff',
                border: 'none', borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 2px 8px rgba(161, 161, 170, 0.3)'
              }}
            >
              <Laptop size={13} />
              <span>View Device Fleet &amp; Nodes ({summary.total_devices || summary.active_devices || 0})</span>
            </button>
          </div>

          {/* KPI Cards Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 14, marginBottom: 20 }}>
            {[
              { label: 'TOTAL SCOUT USERS', value: totalUsersCount, icon: Users, color: '#e4e4e7', sub: 'Registered & active' },
              { label: 'ACTIVE USERS', value: activeUsersCount, icon: Activity, color: '#4ade80', sub: 'Seen last 24h' },
              {
                label: 'ACTIVE DEVICES',
                value: activeDevicesCount,
                icon: Laptop,
                color: '#22c55e',
                sub: `${totalDevicesCount} nodes (Click to view fleet)`,
                clickable: true,
                onClick: () => setAdminView('fleet_nodes')
              },
              { label: 'CONTRIBUTING USERS', value: contributingUsersCount, icon: Sparkles, color: '#a1a1aa', sub: 'Added / enriched data' },
              { label: 'OFFLINE USERS', value: offlineUsersCount, icon: Clock, color: '#a1a1aa', sub: 'No signal > 7d' },
              { label: 'UPDATE REQUIRED', value: updateReqCount, icon: AlertTriangle, color: '#f59e0b', sub: `Prod is v${latestProdVer}` },
              { label: 'REVOKED', value: revokedCount, icon: ShieldAlert, color: '#f43f5e', sub: 'Blocked or quarantined' },
            ].map((card, idx) => {
              const Icon = card.icon;
              return (
                <div
                  key={idx}
                  onClick={card.onClick}
                  style={{
                    background: 'var(--card-bg, #121214)', border: card.clickable ? '1px solid rgba(34, 197, 94, 0.4)' : '1px solid var(--card-border, #232326)',
                    borderRadius: 12, padding: '16px 18px',
                    display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden',
                    cursor: card.clickable ? 'pointer' : 'default',
                    transition: 'all 0.15s ease',
                  }}
                  title={card.clickable ? 'Click to open Device Fleet & Nodes panel' : undefined}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted, #a1a1aa)', letterSpacing: 0.5 }}>{card.label}</span>
                    <Icon size={16} color={card.color} />
                  </div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary, #fafafa)', lineHeight: 1.1, marginBottom: 4 }}>
                    {card.value.toLocaleString()}
                  </div>
                  <div style={{ fontSize: 11, color: card.clickable ? '#4ade80' : 'var(--text-muted, #71717a)', fontWeight: card.clickable ? 600 : 400 }}>
                    {card.sub}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pipeline Impact Ribbon & Version Distribution */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(228, 228, 231, 0.05) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: 12, padding: '16px 20px',
            display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 24, marginBottom: 20, alignItems: 'center'
          }}>
            {/* Left: Canonical Enrichment Stats */}
            <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#10b981', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
                  Pipeline Ingestion Impact
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary, #a1a1aa)' }}>
                  True database modifications produced by desktop fleet
                </div>
              </div>

              <div style={{ display: 'flex', gap: 16 }}>
                <div style={{ background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: '8px 14px' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted, #a1a1aa)' }}>People Added</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#34d399' }}>
                    {canonicalCreated.toLocaleString()}
                  </div>
                </div>
                <div style={{ background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: '8px 14px' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted, #a1a1aa)' }}>Contacts Enriched</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary, #e4e4e7)' }}>
                    {canonicalEnriched.toLocaleString()}
                  </div>
                </div>
                <div style={{ background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)', borderRadius: 8, padding: '8px 14px' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted, #a1a1aa)' }}>Fleet Quality Avg</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-secondary, #a1a1aa)' }}>
                    {avgQualScore} / 100
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Version Distribution Breakdown */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted, #a1a1aa)' }}>
                  Fleet Version Distribution (Latest: v{latestProdVer})
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {Object.entries(versionDistribution).length === 0 ? (
                  <span style={{ fontSize: 12, color: 'var(--text-muted, #71717a)' }}>No device versions reported</span>
                ) : (
                  Object.entries(versionDistribution).map(([ver, count]) => {
                    const isLatest = ver === latestProdVer;
                    return (
                      <span key={ver} style={{
                        padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                        background: isLatest ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: isLatest ? '#34d399' : '#f59e0b',
                        border: `1px solid ${isLatest ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`
                      }}>
                        v{ver}: <b>{count}</b> {isLatest ? '✓ current' : '⚠ outdated'}
                      </span>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Search, Filter & Sort Controls */}
          <div style={{
            background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12,
            padding: '14px 18px', marginBottom: 16, display: 'flex', gap: 14,
            alignItems: 'center', flexWrap: 'wrap', justifyContent: 'space-between'
          }}>
            {/* Search Input */}
            <div style={{ position: 'relative', flex: '1 1 280px', maxWidth: 380 }}>
              <Search size={15} color="#71717a" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                placeholder="Search by user name, email, or company..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%', padding: '8px 12px 8px 34px', background: 'var(--bg-base, #0b0b0c)',
                  border: '1px solid var(--card-border, #232326)', borderRadius: 8, color: 'var(--text-primary, #fafafa)',
                  fontSize: 13, outline: 'none'
                }}
              />
            </div>

            {/* Status Filters */}
            <div style={{ display: 'flex', gap: 5, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted, #71717a)', marginRight: 4 }}>STATUS:</span>
              {['ALL', 'CONTRIBUTING', 'ACTIVE', 'PAIRED', 'REGISTERED', 'REVOKED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  style={{
                    padding: '5px 11px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                    border: statusFilter === st ? '1px solid var(--text-primary, #e4e4e7)' : '1px solid var(--card-border, #232326)',
                    background: statusFilter === st ? 'var(--hover-bg, rgba(228, 228, 231, 0.15))' : 'var(--panel-bg, #0b0b0c)',
                    color: statusFilter === st ? 'var(--text-primary, #e4e4e7)' : 'var(--text-secondary, #a1a1aa)',
                    cursor: 'pointer'
                  }}
                >
                  {st}
                </button>
              ))}
            </div>

            {/* Sort Select */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted, #71717a)' }}>SORT:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                style={{
                  padding: '7px 12px', background: 'var(--panel-bg, #0b0b0c)', border: '1px solid var(--card-border, #232326)',
                  color: 'var(--text-primary, #fafafa)', borderRadius: 8, fontSize: 12, outline: 'none', cursor: 'pointer'
                }}
              >
                <option value="most_active">Most Active</option>
                <option value="most_data">Most Data Contributed</option>
                <option value="highest_quality">Highest Quality Score</option>
                <option value="most_devices">Most Devices</option>
              </select>
            </div>
          </div>

          {/* Contributors Table */}
          <div style={{
            background: 'var(--card-bg, #121214)', border: '1px solid var(--card-border, #232326)', borderRadius: 12,
            overflow: 'hidden', boxShadow: 'var(--shadow)'
          }}>
            {isLoading ? (
              <div style={{ padding: 60, textAlign: 'center', color: '#a1a1aa' }}>
                <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px' }} />
                <div>Loading Scout Contributors...</div>
              </div>
            ) : users.length === 0 ? (
              <div style={{ padding: 60, textAlign: 'center', color: '#71717a' }}>
                <Users size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
                <div style={{ fontSize: 15, fontWeight: 600, color: '#a1a1aa', marginBottom: 4 }}>No Scout users match this query</div>
                <div style={{ fontSize: 12 }}>Try clearing the search query or selecting a different status filter.</div>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: 'var(--panel-bg, #0b0b0c)', borderBottom: '1px solid var(--card-border, #232326)' }}>
                      <th style={{ padding: '14px 18px', color: 'var(--text-muted, #a1a1aa)', fontWeight: 600, fontSize: 11 }}>USER &amp; ACCOUNT</th>
                      <th style={{ padding: '14px 18px', color: 'var(--text-muted, #a1a1aa)', fontWeight: 600, fontSize: 11 }}>LIFECYCLE STATUS</th>
                      <th style={{ padding: '14px 18px', color: 'var(--text-muted, #a1a1aa)', fontWeight: 600, fontSize: 11 }}>DEVICES</th>
                      <th style={{ padding: '14px 18px', color: 'var(--text-muted, #a1a1aa)', fontWeight: 600, fontSize: 11 }}>VERSION</th>
                      <th style={{ padding: '14px 18px', color: 'var(--text-muted, #a1a1aa)', fontWeight: 600, fontSize: 11 }}>LAST SEEN</th>
                      <th style={{ padding: '14px 18px', color: 'var(--text-muted, #a1a1aa)', fontWeight: 600, fontSize: 11 }}>DATA IMPACT</th>
                      <th style={{ padding: '14px 18px', color: 'var(--text-muted, #a1a1aa)', fontWeight: 600, fontSize: 11 }}>QUALITY TIER</th>
                      <th style={{ padding: '14px 18px', color: 'var(--text-muted, #a1a1aa)', fontWeight: 600, fontSize: 11, textAlign: 'right' }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => {
                      const statusKey = u.lifecycle_status || u.scout_status || 'REGISTERED';
                      const badge = getStatusBadge(statusKey);
                      const StatusIcon = badge.icon;
                      const userName = u.full_name || u.name || 'Unnamed User';
                      const userTenant = u.company || u.tenant || null;
                      const deviceCount = u.device_count ?? u.devices_count ?? 0;
                      const activeCount = u.active_device_count ?? (u.health === 'HEALTHY' ? deviceCount : 0);
                      const versionStr = u.primary_version || u.current_version || latestProdVer || '—';
                      const isOutdated = u.update_required;
                      const lastSeenDisplay = u.last_seen_at ? formatTimeAgo(u.last_seen_at) : (u.last_seen || '—');
                      const lastContribDisplay = u.last_contribution_at ? formatTimeAgo(u.last_contribution_at) : (u.last_contribution || '—');
                      const newPeople = u.contributions?.canonical_new ?? u.new_people_created ?? 0;
                      const enrichedPeople = u.contributions?.canonical_enriched ?? u.people_enriched ?? 0;
                      const rawObs = u.contributions?.raw_events ?? u.raw_observations ?? 0;
                      const qualityScore = u.quality?.overall_score ?? u.quality_score ?? 0;
                      const qualityTier = u.quality?.tier || u.contribution_tier || 'DEVELOPING';

                      return (
                        <tr
                          key={u.user_id}
                          onClick={() => setSelectedUserId(u.user_id)}
                          style={{
                            borderBottom: '1px solid var(--card-border, #232326)',
                            cursor: 'pointer',
                            transition: 'background 0.15s ease'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--hover-bg, rgba(255,255,255,0.02))'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          {/* User Info */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary, #fafafa)', display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span>{userName}</span>
                              <span style={{ fontSize: 11, color: 'var(--text-muted, #71717a)' }}>#{u.user_id}</span>
                            </div>
                            <div style={{ fontSize: 12, color: 'var(--text-secondary, #a1a1aa)', marginTop: 2 }}>{u.email}</div>
                            {userTenant && (
                              <div style={{ fontSize: 11, color: 'var(--text-muted, #71717a)', marginTop: 2 }}>{userTenant}</div>
                            )}
                          </td>

                          {/* Lifecycle Status Badge */}
                          <td style={{ padding: '14px 18px' }}>
                            <span style={{
                              padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                              background: badge.bg, color: badge.text, border: `1px solid ${badge.border}`,
                              display: 'inline-flex', alignItems: 'center', gap: 5
                            }}>
                              <StatusIcon size={12} />
                              {u.status_label || statusKey}
                            </span>
                          </td>

                          {/* Devices Count */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary, #fafafa)' }}>
                              <Laptop size={14} color="var(--text-secondary, #e4e4e7)" />
                              <span style={{ fontWeight: 600 }}>{activeCount}</span>
                              <span style={{ color: 'var(--text-muted, #71717a)' }}>/ {deviceCount}</span>
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted, #71717a)', marginTop: 2 }}>
                              {activeCount > 0 ? `${activeCount} active node(s)` : 'No active nodes'}
                            </div>
                          </td>

                          {/* Version & Update Warning */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span style={{
                                fontFamily: 'monospace', fontSize: 12,
                                color: isOutdated ? '#f59e0b' : '#34d399', fontWeight: 600
                              }}>
                                v{versionStr}
                              </span>
                              {isOutdated && (
                                <span title={`Latest production release is v${latestProdVer}`}>
                                  <AlertTriangle size={13} color="#f59e0b" />
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted, #71717a)', marginTop: 2 }}>
                              {u.primary_platform || 'Windows 64-bit'}
                            </div>
                          </td>

                          {/* Last Seen */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ color: 'var(--text-primary, #fafafa)', fontWeight: 500 }}>
                              {lastSeenDisplay}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted, #71717a)', marginTop: 2 }}>
                              Contrib: {lastContribDisplay}
                            </div>
                          </td>

                          {/* Data Impact */}
                          <td style={{ padding: '14px 18px' }}>
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                              <span style={{
                                padding: '2px 6px', borderRadius: 4, fontSize: 11,
                                background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', fontWeight: 600
                              }}>
                                +{newPeople} new
                              </span>
                              <span style={{
                                padding: '2px 6px', borderRadius: 4, fontSize: 11,
                                background: 'var(--hover-bg, rgba(228, 228, 231, 0.15))', color: 'var(--text-primary, #e4e4e7)', fontWeight: 600
                              }}>
                                +{enrichedPeople} enriched
                              </span>
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted, #71717a)', marginTop: 3 }}>
                              {rawObs.toLocaleString()} observations
                            </div>
                          </td>

                          {/* Quality Tier */}
                          <td style={{ padding: '14px 18px' }}>
                            {getQualityBadge(qualityTier, qualityScore)}
                          </td>

                          {/* Inspect Action */}
                          <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedUserId(u.user_id);
                              }}
                              style={{
                                padding: '6px 12px', background: 'var(--panel-bg, #232326)', border: '1px solid var(--card-border, #27272a)',
                                color: 'var(--text-primary, #e4e4e7)', borderRadius: 6, fontSize: 11, fontWeight: 700,
                                cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4
                              }}
                            >
                              <span>Inspect</span>
                              <ChevronRight size={13} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PRIMARY VIEW 2: FLEET HARDWARE NODES & TELEMETRY                          */}
      {/* ========================================================================= */}
      {isAdmin && currentView === 'fleet_nodes' && (
        <div style={{ marginTop: 8 }}>
          <ScoutNodesPanel />
        </div>
      )}

      {/* ========================================================================= */}
      {/* PRIMARY VIEW 3: RELEASE & ROLLOUT GOVERNANCE                              */}
      {/* ========================================================================= */}
      {isAdmin && currentView === 'governance' && (
        <div style={{ marginTop: 8 }}>
          <ScoutReleaseGovernance
            onReleaseChanged={() => {
              api.get('/scout/updates/latest')
                .then(res => {
                  if (res?.data?.version) setReleaseInfo(prev => ({ ...prev, ...res.data }));
                })
                .catch(() => {});
              refetch();
            }}
          />
        </div>
      )}

      {/* User Forensic Slide-over Drawer */}
      <ScoutUserProfileDrawer
        userId={selectedUserId}
        onClose={() => setSelectedUserId(null)}
        onRefreshList={() => refetch()}
      />

      {/* Add Scout Modal */}
      <AddScoutModal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false);
          refetch();
        }}
      />
    </div>
  );
}
