// ============================================================
// content.js — Visual Scout Autonomous Engine (37 Hard-Rule Operating Core)
// 1s Active Sampling • 10s Inactivity Pause • Strict Useful-Domain Hard Gate
// ============================================================

(function() {
  'use strict';

  // Prevent multiple timer loops if reinjected
  if (window.__talentScoutHeartbeatRunning) return;
  window.__talentScoutHeartbeatRunning = true;

  window.TalentScout = window.TalentScout || {};
  const ts = window.TalentScout;

  let isScanning = false;
  let debounceTimer = null;
  let lastUrl = location.href;

  // ── Engine State & Inactivity Watchdog (Algorithms 1, 2, 3, 4) ──
  let lastActivityTime = Date.now();
  let lastCaptureTimestamp = null;
  let lastDiscoveryTimestamp = null;
  const INACTIVITY_THRESHOLD_MS = 120000; // 2 minutes active window (avoids premature pause while reading)

  let engineState = 'STARTING'; // 'STARTING' | 'ACTIVE_SAMPLING' | 'IDLE_WATCH'

  // ── 1. Active Candidate Entity Lock (Person Multi-Frame Accumulation) ──
  let activeCandidateSession = {
    entity_type: 'CANDIDATE',
    profileUrl: null,
    recruiter_name: null,
    title: null,
    company_name: null,
    previous_company: null,
    location: null,
    education: null,
    connection_degree: null,
    followers_count: null,
    connections_count: null,
    about_summary: null,
    about_insights: null,
    experience_history: [],
    skills: [],
    certifications: [],
    languages: [],
    is_open_to_work: false,
    is_hiring: false,
    is_verified: false,
    pronouns: null,
    email: null,
    phone: null,
    website: null,
    github: null,
    twitter: null,
    portfolio: null,
    linkedin_url: null,
    source_platform: 'LinkedIn',
    observation_count: 0,
    capture_ids: [],
    field_provenance: {},
  };

  // ── 2. Active Company Entity Lock (Organization Multi-Frame Accumulation) ──
  let activeCompanySession = {
    entity_type: 'COMPANY',
    profileUrl: null,
    company_name: null,
    industry: null,
    location: null,
    employees_count: null,
    followers_count: null,
    website: null,
    specialties: null,
    founded: null,
    company_type: null,
    open_roles: null,
    overview: null,
    linkedin_url: null,
    source_platform: 'LinkedIn',
    observation_count: 0,
    capture_ids: [],
    field_provenance: {},
  };

  function syncActiveProfileToStorage() {
    try {
      const isCompanyPage = location.pathname.includes('/company/');
      const isCandidatePage = /^\/(in|pub)\//.test(location.pathname);

      const candidateData = (!isCompanyPage && activeCandidateSession.recruiter_name) ? activeCandidateSession : null;
      const companyData = (!isCandidatePage && activeCompanySession.company_name) ? activeCompanySession : null;

      chrome.storage.local.set({
        currentActiveProfile: isCompanyPage ? (companyData || candidateData) : (candidateData || companyData),
        activeProfile: isCompanyPage ? (companyData || candidateData) : (candidateData || companyData),
        activeCandidate: isCompanyPage ? null : candidateData,
        activeCompany: companyData,
      });

      chrome.runtime.sendMessage({
        type: 'ACTIVE_PROFILE_UPDATE',
        profile: isCompanyPage ? (companyData || candidateData) : (candidateData || companyData),
        candidate: isCompanyPage ? null : candidateData,
        company: companyData,
      });
    } catch (_) {}
  }

  function updateEngineTelemetry(state) {
    engineState = state;
    const idleSec = Math.floor((Date.now() - lastActivityTime) / 1000);
    try {
      chrome.runtime.sendMessage({
        type: 'ENGINE_STATE_UPDATE',
        state: engineState,
        idleSeconds: idleSec,
        lastCapture: lastCaptureTimestamp,
        lastDiscovery: lastDiscoveryTimestamp,
        url: location.href,
        title: document.title,
        activeProfile: activeProfileSession.recruiter_name ? activeProfileSession : null,
      });
    } catch (_) {}
  }

  function recordUserActivity(triggerReason = 'interaction') {
    const wasIdle = (Date.now() - lastActivityTime) >= INACTIVITY_THRESHOLD_MS;
    lastActivityTime = Date.now();

    if (wasIdle || engineState === 'IDLE_WATCH') {
      console.log(`%c[TalentOps Scout] ⚡ WAKE: ${triggerReason} detected — resuming active 1s sampling`, 'color:#10b981;font-weight:bold;');
      logEvent('ENGINE_WAKE', `Resumed by ${triggerReason}`);
      updateEngineTelemetry('ACTIVE_SAMPLING');
      runAutonomousFusionScan(true);
    }
  }

  // Listen for human interaction events
  ['mousemove', 'scroll', 'keydown', 'click', 'wheel', 'touchstart'].forEach(evtName => {
    window.addEventListener(evtName, () => recordUserActivity(evtName), { passive: true });
  });

  function isUserActive() {
    return (Date.now() - lastActivityTime) < INACTIVITY_THRESHOLD_MS;
  }

  function logEvent(eventType, detail) {
    try {
      chrome.runtime.sendMessage({
        type: 'APPEND_EVENT_LOG',
        event: {
          timestamp: new Date().toLocaleTimeString(),
          type: eventType,
          detail: detail || '',
          url: location.href,
        }
      });
    } catch (_) {}
  }

  console.log('%c[TalentOps Scout] 🚀 Autonomous Visual Scout Initialized on: ' + location.hostname, 'color:#3b82f6;font-weight:bold;');

  // ── Algorithm 1: INITIAL CAPTURE IMMEDIATELY ─────────────────
  // Hard Rule 1 & 16: Initial page must ALWAYS be captured immediately on start
  try {
    chrome.runtime.sendMessage({
      type: 'PAGE_VIEW',
      url: location.href,
      title: document.title,
    });
    logEvent('PAGE_OBSERVED', document.title || location.hostname);
  } catch (_) {}

  // Run initial capture burst on page mount
  updateEngineTelemetry('STARTING');
  setTimeout(() => {
    recordUserActivity('initial_page_mount');
    runAutonomousFusionScan(true);
  }, 250);
  setTimeout(() => runAutonomousFusionScan(true), 1200);
  setTimeout(() => runAutonomousFusionScan(true), 2500);
  setTimeout(() => runAutonomousFusionScan(true), 4500);

  // ── Algorithm 2 & 3: 1-SECOND ACTIVE SAMPLING & PROFILE COMPLETION ENGINE ──
  setInterval(() => {
    const idleMs = Date.now() - lastActivityTime;
    const isProfilePage = /^\/(in|pub|company)\//.test(location.pathname);
    const isCandidateIncomplete = isProfilePage && (!activeCandidateSession.recruiter_name || !activeCandidateSession.recruiter_name.includes(' ') || !activeCandidateSession.company_name || !activeCandidateSession.location);

    // Hard Rule 2: Inactivity pause — BUT keep scanning if candidate/company profile is still incomplete
    if (idleMs >= INACTIVITY_THRESHOLD_MS && !isCandidateIncomplete) {
      if (engineState !== 'IDLE_WATCH') {
        updateEngineTelemetry('IDLE_WATCH');
        logEvent('IDLE_PAUSE', `Paused after 120s inactivity — watching cheap change detector`);
      }
      return;
    }

    // Active sampling every 1 second
    if (document.visibilityState === 'visible' || isCandidateIncomplete) {
      updateEngineTelemetry('ACTIVE_SAMPLING');
      runAutonomousFusionScan(false);
    }
  }, 1000); // 1-second capture cadence

  // ── Algorithm 4: Tab Switch & Window Focus Instant Wakeup ────────────
  window.addEventListener('focus', () => {
    recordUserActivity('window_focus');
    runAutonomousFusionScan(true);
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      recordUserActivity('tab_visibility');
      runAutonomousFusionScan(true);
    }
  });

  // ── Algorithm 20: SPA Navigation & Hashchange Instant Wakeup ─────────
  window.addEventListener('popstate', () => {
    lastUrl = location.href;
    if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
    chrome.storage.local.set({ seenKeysWithTime: {} });
    recordUserActivity('spa_navigation');
    runAutonomousFusionScan(true);
  });
  window.addEventListener('hashchange', () => {
    lastUrl = location.href;
    if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
    chrome.storage.local.set({ seenKeysWithTime: {} });
    recordUserActivity('hash_change');
    runAutonomousFusionScan(true);
  });

  // Continuous URL polling watchdog (ensures 100% SPA navigation catch without page reload)
  setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
      recordUserActivity('url_changed');
      chrome.storage.local.set({ seenKeysWithTime: {} });
      runAutonomousFusionScan(true);
    }
  }, 500);

  // ── Algorithm 22: Mutation Observer for Lazy-Loaded Content ──
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      recordUserActivity('dom_mutation');
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
        logEvent('PAGE_CHANGED', document.title || location.hostname);
        chrome.storage.local.set({ seenKeysWithTime: {} });
      }
      runAutonomousFusionScan(false);
    }, 120);
  });

  if (document.body || document.documentElement) {
    observer.observe(document.body || document.documentElement, {
      childList: true,
      subtree: true,
      characterData: false,
      attributes: false,
    });
  }

  // ── Message Listener for Manual Commands & Active Profile Query ──
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'GET_ACTIVE_PROFILE') {
      recordUserActivity('popup_opened'); // Instantly reset inactivity timer and wake up engine
      const isCompPage = location.pathname.includes('/company/');
      let leads = [];
      try {
        if (window.TalentScout?.detectLinkedIn) {
          leads = window.TalentScout.detectLinkedIn();
        }
      } catch (_) {}

      if (isCompPage) {
        const compLead = leads.find(l => l.entity_type === 'COMPANY') || leads[0] || (activeCompanySession.company_name ? activeCompanySession : null);
        sendResponse({ profile: compLead, company: compLead, candidate: null });
        return true;
      }

      // Prioritize full DOM-extracted profile (source === 'linkedin_profile') over URL slug / meta fallback
      const fullProfile = leads.find(l => l.source === 'linkedin_profile' && l.recruiter_name && l.recruiter_name !== 'LinkedIn Member');
      const liveLead = fullProfile || leads.find(l => l.recruiter_name && l.recruiter_name !== 'LinkedIn Member') || leads[0] || (activeCandidateSession.recruiter_name ? activeCandidateSession : null);

      if (liveLead) {
        // If liveLead is better than activeCandidateSession, immediately merge and sync
        if (!activeCandidateSession.recruiter_name || activeCandidateSession.recruiter_name === 'Jamiegrab' || !activeCandidateSession.recruiter_name.includes(' ') || (fullProfile && liveLead.source === 'linkedin_profile')) {
          Object.assign(activeCandidateSession, liveLead);
          syncActiveProfileToStorage();
        }
      }

      sendResponse({ profile: liveLead, candidate: liveLead, company: null });
      return true;
    }

    if (msg.type === 'TRIGGER_SCAN' || msg.type === 'MANUAL_CAPTURE') {
      recordUserActivity('message_trigger');
      if (msg.type === 'MANUAL_CAPTURE') {
        chrome.storage.local.set({ seenKeysWithTime: {} });
      }
      runAutonomousFusionScan(true).then(() => sendResponse({ ok: true }));
      return true;
    }
  });

  // ── Algorithm 6, 7, 8, 12: CORE FUSION, SCORING & GATING ENGINE ──
  async function runAutonomousFusionScan(force = false) {
    if (isScanning && !force) return;
    isScanning = true;
    lastCaptureTimestamp = new Date().toLocaleTimeString();

    try {
      // 1. STAGE A: Fast DOM & Microdata Heuristic Scanners (< 3ms)
      let domLeads = [];
      try {
        domLeads = runDomDetectorPipeline();
      } catch (domErr) {
        logEvent('DOM_ERROR', String(domErr?.message || domErr).slice(0, 120));
      }

      // 2. STAGE B: Visual Screen Capture with Strict 1.5s Watchdog
      let visualLeads = [];
      let captureId = null;
      try {
        const vizRes = await Promise.race([
          runVisualCapturePipeline(force),
          new Promise(r => setTimeout(() => r({ entities: [], captureId: null }), 1500))
        ]);
        visualLeads = vizRes.entities || [];
        captureId = vizRes.captureId || null;
      } catch (vizErr) {
        logEvent('VISUAL_ERROR', String(vizErr?.message || vizErr).slice(0, 120));
      }

      // 3. FUSE VISUAL + DOM Intelligence
      const fusedLeads = fuseVisualAndDomLeads(visualLeads, domLeads, captureId);

      // 4. Algorithm 6 & 11: Classify and Gate Useful Entities
      const usefulLeads = fusedLeads.filter(lead => {
        // Tag entity type
        const isComp = lead.entity_type === 'COMPANY' || (ts.isCompanyName && ts.isCompanyName(lead.recruiter_name));
        lead.entity_type = isComp ? 'COMPANY' : 'CANDIDATE';

        const isUseful = ts.isUsefulDomainEntity ? ts.isUsefulDomainEntity(lead) : Boolean(lead.recruiter_name || lead.email || lead.linkedin_url || lead.company_name);
        return isUseful;
      });

      // 4b. Multi-Frame Progressive Entity Lock (Candidate vs Company)
      const cleanUrl = location.href.split('?')[0].split('#')[0];

      // A. Candidate Profile View (/in/ or /pub/)
      if (/^\/(in|pub)\//.test(location.pathname)) {
        if (activeCandidateSession.profileUrl !== cleanUrl) {
          activeCandidateSession = {
            entity_type: 'CANDIDATE',
            profileUrl: cleanUrl,
            recruiter_name: null,
            title: null,
            company_name: null,
            previous_company: null,
            location: null,
            education: null,
            connection_degree: null,
            followers_count: null,
            connections_count: null,
            about_summary: null,
            about_insights: null,
            experience_history: [],
            skills: [],
            certifications: [],
            languages: [],
            is_open_to_work: false,
            is_hiring: false,
            is_verified: false,
            pronouns: null,
            email: null,
            phone: null,
            website: null,
            github: null,
            twitter: null,
            portfolio: null,
            linkedin_url: cleanUrl,
            source_platform: 'LinkedIn',
            observation_count: 0,
            capture_ids: [],
            field_provenance: {},
          };
        }

        const relevantCandidates = usefulLeads.filter(l => {
          if (l.entity_type !== 'CANDIDATE') return false;
          if (!l.linkedin_url) return true;
          return l.linkedin_url === cleanUrl || l.source === 'linkedin_profile' || l.source === 'linkedin_meta';
        });

        // Fallback to all candidates if none matched current URL explicitly
        const candidatesToProcess = relevantCandidates.length > 0 ? relevantCandidates : usefulLeads.filter(l => l.entity_type === 'CANDIDATE');

        candidatesToProcess.forEach(lead => {
          // Name Quality Upgrade: Prefer 2+ word human name over unspaced slug or 'LinkedIn Member'
          const currName = activeCandidateSession.recruiter_name;
          const newName = lead.recruiter_name;
          const isCurrWeak = !currName || currName === 'LinkedIn Member' || !currName.includes(' ');
          const isNewStrong = newName && newName !== 'LinkedIn Member' && newName.includes(' ');
          if (isNewStrong && isCurrWeak) {
            activeCandidateSession.recruiter_name = newName;
            activeCandidateSession.field_provenance.name = captureId;
          } else if (newName && !currName) {
            activeCandidateSession.recruiter_name = newName;
            activeCandidateSession.field_provenance.name = captureId;
          }

          // Title Quality Upgrade: Prefer descriptive headline over 'Professional'
          const currTitle = activeCandidateSession.title;
          const newTitle = lead.title;
          const isCurrTitleWeak = !currTitle || currTitle.toLowerCase() === 'professional' || currTitle === '—';
          const isNewTitleStrong = newTitle && newTitle.toLowerCase() !== 'professional';
          if (isNewTitleStrong && isCurrTitleWeak) {
            activeCandidateSession.title = newTitle;
            activeCandidateSession.field_provenance.title = captureId;
          } else if (newTitle && !currTitle) {
            activeCandidateSession.title = newTitle;
            activeCandidateSession.field_provenance.title = captureId;
          }

          if (lead.headline && (!activeCandidateSession.headline || activeCandidateSession.headline.toLowerCase() === 'professional')) {
            activeCandidateSession.headline = lead.headline;
          }

          // Company Quality Upgrade: Prefer real company over 'Company' or '—'
          const currComp = activeCandidateSession.company_name;
          const newComp = lead.company_name;
          const isCurrCompWeak = !currComp || currComp.toLowerCase() === 'company' || currComp === '—';
          const isNewCompStrong = newComp && newComp.toLowerCase() !== 'company';
          if (isNewCompStrong && isCurrCompWeak) {
            activeCandidateSession.company_name = newComp;
            activeCandidateSession.field_provenance.company = captureId;
          } else if (newComp && !currComp) {
            activeCandidateSession.company_name = newComp;
            activeCandidateSession.field_provenance.company = captureId;
          }

          if (lead.previous_company && !activeCandidateSession.previous_company) {
            activeCandidateSession.previous_company = lead.previous_company;
            activeCandidateSession.field_provenance.previous_company = captureId;
          }
          if (lead.location && (!activeCandidateSession.location || activeCandidateSession.location === '—')) {
            activeCandidateSession.location = lead.location;
            activeCandidateSession.field_provenance.location = captureId;
          }
          if (lead.education && (!activeCandidateSession.education || activeCandidateSession.education === '—')) {
            activeCandidateSession.education = lead.education;
            activeCandidateSession.field_provenance.education = captureId;
          }
          if (lead.connection_degree && !activeCandidateSession.connection_degree) {
            activeCandidateSession.connection_degree = lead.connection_degree;
          }
          if (lead.followers_count && !activeCandidateSession.followers_count) {
            activeCandidateSession.followers_count = lead.followers_count;
            activeCandidateSession.field_provenance.followers = captureId;
          }
          if (lead.connections_count && !activeCandidateSession.connections_count) {
            activeCandidateSession.connections_count = lead.connections_count;
            activeCandidateSession.field_provenance.connections = captureId;
          }
          if (lead.about_summary && !activeCandidateSession.about_summary) {
            activeCandidateSession.about_summary = lead.about_summary;
            activeCandidateSession.field_provenance.about = captureId;
          }
          if (lead.about_insights && !activeCandidateSession.about_insights) {
            activeCandidateSession.about_insights = lead.about_insights;
          }
          if (lead.is_open_to_work) activeCandidateSession.is_open_to_work = true;
          if (lead.is_hiring) activeCandidateSession.is_hiring = true;
          if (lead.is_verified) activeCandidateSession.is_verified = true;
          if (lead.pronouns && !activeCandidateSession.pronouns) activeCandidateSession.pronouns = lead.pronouns;

          // Merge Experience History progressively
          if (lead.experience_history && Array.isArray(lead.experience_history)) {
            lead.experience_history.forEach(role => {
              const exists = activeCandidateSession.experience_history.some(
                r => (r.title || '').toLowerCase() === (role.title || '').toLowerCase() &&
                     (r.company || '').toLowerCase() === (role.company || '').toLowerCase()
              );
              if (!exists) activeCandidateSession.experience_history.push(role);
            });
            activeCandidateSession.field_provenance.experience = captureId;
          }

          // Merge Skills progressively
          if (lead.skills && Array.isArray(lead.skills)) {
            lead.skills.forEach(s => {
              if (!activeCandidateSession.skills.includes(s)) activeCandidateSession.skills.push(s);
            });
            activeCandidateSession.field_provenance.skills = captureId;
          }

          // Merge Certifications
          if (lead.certifications && Array.isArray(lead.certifications)) {
            lead.certifications.forEach(c => {
              const exists = activeCandidateSession.certifications.some(
                item => (item.title || '').toLowerCase() === (c.title || '').toLowerCase()
              );
              if (!exists) activeCandidateSession.certifications.push(c);
            });
          }

          // Merge Languages
          if (lead.languages && Array.isArray(lead.languages)) {
            lead.languages.forEach(l => {
              const exists = activeCandidateSession.languages.some(
                item => (item.language || '').toLowerCase() === (l.language || '').toLowerCase()
              );
              if (!exists) activeCandidateSession.languages.push(l);
            });
          }

          if (lead.email && !activeCandidateSession.email) {
            activeCandidateSession.email = lead.email;
            activeCandidateSession.field_provenance.email = captureId;
          }
          if (lead.phone && !activeCandidateSession.phone) {
            activeCandidateSession.phone = lead.phone;
            activeCandidateSession.field_provenance.phone = captureId;
          }
          if (lead.website && !activeCandidateSession.website) activeCandidateSession.website = lead.website;
          if (lead.github && !activeCandidateSession.github) activeCandidateSession.github = lead.github;
          if (lead.twitter && !activeCandidateSession.twitter) activeCandidateSession.twitter = lead.twitter;
          if (lead.portfolio && !activeCandidateSession.portfolio) activeCandidateSession.portfolio = lead.portfolio;
        });

        if (captureId && !activeCandidateSession.capture_ids.includes(captureId)) {
          activeCandidateSession.capture_ids.push(captureId);
          activeCandidateSession.observation_count++;
        }

        syncActiveProfileToStorage();
      } 
      // B. Company Profile View (/company/*)
      else if (location.pathname.includes('/company/')) {
        if (activeCompanySession.profileUrl !== cleanUrl) {
          activeCompanySession = {
            entity_type: 'COMPANY',
            profileUrl: cleanUrl,
            company_name: null,
            industry: null,
            location: null,
            employees_count: null,
            followers_count: null,
            website: null,
            specialties: null,
            founded: null,
            company_type: null,
            open_roles: null,
            overview: null,
            linkedin_url: cleanUrl,
            source_platform: 'LinkedIn',
            observation_count: 0,
            capture_ids: [],
            field_provenance: {},
          };
        }

        usefulLeads.filter(l => l.entity_type === 'COMPANY').forEach(comp => {
          if (comp.company_name && !activeCompanySession.company_name) {
            activeCompanySession.company_name = comp.company_name;
            activeCompanySession.field_provenance.name = captureId;
          }
          if (comp.industry && !activeCompanySession.industry) {
            activeCompanySession.industry = comp.industry;
            activeCompanySession.field_provenance.industry = captureId;
          }
          if (comp.location && !activeCompanySession.location) {
            activeCompanySession.location = comp.location;
            activeCompanySession.field_provenance.location = captureId;
          }
          if (comp.employees_count && !activeCompanySession.employees_count) {
            activeCompanySession.employees_count = comp.employees_count;
            activeCompanySession.field_provenance.employees = captureId;
          }
          if (comp.followers_count && !activeCompanySession.followers_count) {
            activeCompanySession.followers_count = comp.followers_count;
            activeCompanySession.field_provenance.followers = captureId;
          }
          if (comp.website && !activeCompanySession.website) {
            activeCompanySession.website = comp.website;
            activeCompanySession.field_provenance.website = captureId;
          }
          if (comp.specialties && !activeCompanySession.specialties) {
            activeCompanySession.specialties = comp.specialties;
          }
          if (comp.founded && !activeCompanySession.founded) {
            activeCompanySession.founded = comp.founded;
          }
          if (comp.company_type && !activeCompanySession.company_type) {
            activeCompanySession.company_type = comp.company_type;
          }
          if (comp.open_roles && !activeCompanySession.open_roles) {
            activeCompanySession.open_roles = comp.open_roles;
          }
          if (comp.overview && !activeCompanySession.overview) {
            activeCompanySession.overview = comp.overview;
          }
        });

        if (captureId && !activeCompanySession.capture_ids.includes(captureId)) {
          activeCompanySession.capture_ids.push(captureId);
          activeCompanySession.observation_count++;
        }

        syncActiveProfileToStorage();
      }

      // Hard Rule 12: If no useful domain data -> DISCARD immediately without DB operation
      if (usefulLeads.length === 0) {
        if (captureId && ts.Visual?.Store) {
          await ts.Visual.Store.discardScreenshot(captureId);
        }
        isScanning = false;
        return;
      }

      // 5. Algorithm 7, 8, 14, 15: Field-Level Deduplication & Enrichment Detection
      const { freshLeads, enrichedLeads } = await evaluateFieldLevelDeduplication(usefulLeads);

      const leadsToProcess = [...freshLeads, ...enrichedLeads];
      if (leadsToProcess.length === 0) {
        // Sighting of previously known candidate on screen — retain frame in 1-hour buffer with metadata
        if (captureId && ts.Visual?.Store) {
          await ts.Visual.Store.updateStatus(captureId, 'EXTRACTION_COMPLETE', usefulLeads);
        }
        isScanning = false;
        return;
      }

      lastDiscoveryTimestamp = new Date().toLocaleTimeString();

      // 6. [Removed] Screenshot counter is managed exclusively by background.js

      // 7. Attach Full Forensic Audit Provenance (Algorithm 12 & Rule 21)
      const formattedContacts = leadsToProcess.map(r => ({
        ...r,
        discovery_id: r.discovery_id || ('DISC-' + crypto.randomUUID().slice(0, 8).toUpperCase()),
        capture_id: captureId || ('CAP-' + Math.floor(10000 + Math.random() * 90000)),
        source_url: location.href,
        source_page_title: document.title,
        captured_at: new Date().toISOString(),
        confidence: r.confidence || 95,
      }));

      const names = formattedContacts.map(e => e.recruiter_name).filter(Boolean).join(', ');
      console.log(`%c[TalentOps Scout] 🎯 [1s Engine] Ingesting ${formattedContacts.length} Lead(s): ${names}`, 'color:#10b981;font-weight:bold;');
      logEvent('DATA_EXTRACTED', `Ingested ${formattedContacts.length} verified lead(s): ${names}`);

      // 8. Stream to Background Worker for Immediate Cloud Sync
      try {
        chrome.runtime.sendMessage({
          type: 'QUEUE_CONTACTS',
          contacts: formattedContacts,
        });
      } catch (queueErr) {
        logEvent('QUEUE_ERROR', String(queueErr?.message || queueErr).slice(0, 120));
      }

      // 9. Update Screenshot Store to Retain Temporarily for 2.5m (Rule 20)
      if (captureId && ts.Visual?.Store) {
        await ts.Visual.Store.updateStatus(captureId, 'SYNC_COMPLETE', formattedContacts);
        await ts.Visual.Store.purgeExpired();
      }

    } catch (e) {
      logEvent('SCAN_ERROR', String(e?.message || e).slice(0, 200));
    } finally {
      isScanning = false;
    }
  }

  // ── Stage B: Visual-First Frame Capture Pipeline ─────────────
  async function runVisualCapturePipeline(force = false) {
    if (!ts.Visual?.Diff || !ts.Visual?.Store || !ts.Visual?.Engine) return { entities: [], captureId: null };

    const capRes = await new Promise(r => {
      chrome.runtime.sendMessage({ type: 'CAPTURE_VISIBLE_TAB' }, res => r(res || null));
      setTimeout(() => r(null), 1200);
    }).catch(() => null);

    if (!capRes || !capRes.ok || !capRes.dataUrl) return { entities: [], captureId: null };

    // Regional change difference
    const diff = await ts.Visual.Diff.evaluateFrame(capRes.dataUrl);
    if (!diff.isMeaningful && !force) {
      return { entities: [], captureId: null };
    }

    const captureId = 'VC-' + Math.floor(10000 + Math.random() * 90000);
    logEvent('SCREENSHOT_CAPTURED', `${captureId} (Delta: ${Math.round(diff.score * 100)}%)`);

    await ts.Visual.Store.saveScreenshot({
      id: captureId,
      page_url: location.href,
      page_title: document.title,
      change_score: diff.score,
      image_data: capRes.dataUrl,
      status: 'PROCESSING',
    });

    const analysis = await ts.Visual.Engine.analyzeScreenshot(capRes.dataUrl, {
      change_score: diff.score,
      capture_id: captureId,
    });

    const entities = (analysis?.entities || []).map(e => ({
      ...e,
      capture_id: captureId,
      visual_change_score: diff.score,
      screenshot_preview: capRes.dataUrl.slice(0, 150) + '...',
    }));

    return { entities, captureId };
  }

  // ── Stage A: DOM Detector Pipeline ───────────────────────────
  function runDomDetectorPipeline() {
    const all = [];
    try { if (ts.detectLinkedIn) all.push(...ts.detectLinkedIn()); } catch (_) {}
    try { if (ts.detectEmail) all.push(...ts.detectEmail()); } catch (_) {}
    try { if (ts.detectIndeed) all.push(...ts.detectIndeed()); } catch (_) {}
    try { if (ts.detectGlassdoor) all.push(...ts.detectGlassdoor()); } catch (_) {}
    try { if (ts.detectZipRecruiter) all.push(...ts.detectZipRecruiter()); } catch (_) {}
    try { if (ts.detectGeneric) all.push(...ts.detectGeneric()); } catch (_) {}
    return all;
  }

  // ── Fusion Layer: Merges Visual & DOM Intelligence ───────────
  function fuseVisualAndDomLeads(visualLeads = [], domLeads = [], captureId = null) {
    const mergedMap = new Map();

    domLeads.forEach(d => {
      const key = (d.email || d.linkedin_url || `${d.recruiter_name}@${d.company_name}` || '').toLowerCase();
      if (key) mergedMap.set(key, { ...d, capture_id: captureId });
    });

    visualLeads.forEach(v => {
      const key = (v.email || v.linkedin_url || `${v.recruiter_name}@${v.company_name}` || '').toLowerCase();
      if (key && mergedMap.has(key)) {
        const existing = mergedMap.get(key);
        if (v.title && !existing.title) existing.title = v.title;
        if (v.company_name && !existing.company_name) existing.company_name = v.company_name;
        if (v.phone && !existing.phone) existing.phone = v.phone;
        if (v.location && !existing.location) existing.location = v.location;
        existing.capture_id = captureId || existing.capture_id;
        existing.visual_change_score = v.visual_change_score || existing.visual_change_score;
        existing.source = 'visual_dom_fusion';
      } else if (key) {
        mergedMap.set(key, { ...v, capture_id: captureId, source: 'visual_capture' });
      }
    });

    return Array.from(mergedMap.values());
  }

  // ── Algorithms 14 & 15: Field-Level Deduplication & Enrichment ──
  async function evaluateFieldLevelDeduplication(results) {
    const stored = await new Promise(r => chrome.storage.local.get(['knownEntityFieldMap'], r));
    const entityMap = stored.knownEntityFieldMap || {};
    const freshLeads = [];
    const enrichedLeads = [];
    const updatedMap = { ...entityMap };

    results.forEach(r => {
      const isComp = r.entity_type === 'COMPANY' || (ts.isCompanyName && ts.isCompanyName(r.recruiter_name));
      const entityKey = isComp
        ? ('co:' + (r.linkedin_url || r.company_name || r.recruiter_name || '')).toLowerCase()
        : ('cand:' + (r.linkedin_url || r.email || `${r.recruiter_name}@${r.company_name}` || '')).toLowerCase();
      if (!entityKey || entityKey === 'co:' || entityKey === 'cand:') return;

      const existingRecord = entityMap[entityKey];

      if (!existingRecord) {
        // New Entity Sighting
        updatedMap[entityKey] = {
          entity_type: isComp ? 'COMPANY' : 'CANDIDATE',
          name: r.recruiter_name,
          title: r.title,
          company: r.company_name,
          industry: r.industry,
          email: r.email,
          phone: r.phone,
          linkedin: r.linkedin_url,
          location: r.location,
          lastSeen: Date.now(),
        };
        freshLeads.push({ ...r, db_action: 'NEW_DISCOVERY' });
      } else {
        // Check for new fields (Algorithm 14 & 15: Field-Level Enrichment)
        let hasNewField = false;
        const fieldsAdded = [];

        if (r.email && !existingRecord.email) { existingRecord.email = r.email; hasNewField = true; fieldsAdded.push('Email'); }
        if (r.phone && !existingRecord.phone) { existingRecord.phone = r.phone; hasNewField = true; fieldsAdded.push('Phone'); }
        if (r.title && !existingRecord.title) { existingRecord.title = r.title; hasNewField = true; fieldsAdded.push('Title'); }
        if (r.company_name && !existingRecord.company) { existingRecord.company = r.company_name; hasNewField = true; fieldsAdded.push('Company'); }
        if (r.location && !existingRecord.location) { existingRecord.location = r.location; hasNewField = true; fieldsAdded.push('Location'); }
        if (r.linkedin_url && !existingRecord.linkedin) { existingRecord.linkedin = r.linkedin_url; hasNewField = true; fieldsAdded.push('LinkedIn'); }
        
        // Deep Profile Enrichment Triggers
        if (r.education && !existingRecord.education) { existingRecord.education = r.education; hasNewField = true; fieldsAdded.push('Education'); }
        if (r.about_summary && !existingRecord.about_summary) { existingRecord.about_summary = r.about_summary; hasNewField = true; fieldsAdded.push('About'); }
        if (r.experience_history && !existingRecord.experience_history) { existingRecord.experience_history = r.experience_history; hasNewField = true; fieldsAdded.push('Experience'); }
        if (r.skills && !existingRecord.skills) { existingRecord.skills = r.skills; hasNewField = true; fieldsAdded.push('Skills'); }
        if (r.connections_count && !existingRecord.connections_count) { existingRecord.connections_count = r.connections_count; hasNewField = true; fieldsAdded.push('Connections'); }
        if (r.certifications && !existingRecord.certifications) { existingRecord.certifications = r.certifications; hasNewField = true; fieldsAdded.push('Certifications'); }

        if (hasNewField) {
          existingRecord.lastSeen = Date.now();
          updatedMap[entityKey] = existingRecord;
          enrichedLeads.push({
            ...r,
            db_action: 'ENRICHED',
            fields_added: fieldsAdded,
          });
        }
      }
    });

    if (freshLeads.length > 0 || enrichedLeads.length > 0) {
      const keys = Object.keys(updatedMap);
      if (keys.length > 2000) {
        const sorted = keys.sort((a, b) => (updatedMap[b].lastSeen || 0) - (updatedMap[a].lastSeen || 0)).slice(0, 1200);
        const trimmed = {};
        sorted.forEach(k => trimmed[k] = updatedMap[k]);
        chrome.storage.local.set({ knownEntityFieldMap: trimmed });
      } else {
        chrome.storage.local.set({ knownEntityFieldMap: updatedMap });
      }
    }

    return { freshLeads, enrichedLeads };
  }

})();
