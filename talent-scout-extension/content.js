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
  const INACTIVITY_THRESHOLD_MS = 10000; // Hard Rule 2: 10 seconds idle threshold

  let engineState = 'STARTING'; // 'STARTING' | 'ACTIVE_SAMPLING' | 'IDLE_WATCH'

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

  // ── Algorithm 2 & 3: 1-SECOND ACTIVE SAMPLING & 10s IDLE PAUSE ──
  setInterval(() => {
    const idleMs = Date.now() - lastActivityTime;

    // Algorithm 3: Hard Rule 2 - No meaningful change / idle >= 10s -> STOP CAPTURING
    if (idleMs >= INACTIVITY_THRESHOLD_MS) {
      if (engineState !== 'IDLE_WATCH') {
        updateEngineTelemetry('IDLE_WATCH');
        logEvent('IDLE_PAUSE', `Paused after 10s inactivity — watching cheap change detector`);
      }
      return;
    }

    // Active sampling every 1 second
    if (document.visibilityState === 'visible') {
      updateEngineTelemetry('ACTIVE_SAMPLING');
      runAutonomousFusionScan(false);
    }
  }, 1000); // 1-second capture cadence

  // ── Algorithm 4: Tab Switch & Window Focus Wakeup ────────────
  window.addEventListener('focus', () => recordUserActivity('window_focus'));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') recordUserActivity('tab_visibility');
  });

  // ── Algorithm 20: SPA Navigation & Hashchange Wakeup ─────────
  window.addEventListener('popstate', () => {
    lastUrl = location.href;
    if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
    chrome.storage.local.set({ seenKeysWithTime: {} });
    recordUserActivity('spa_navigation');
  });
  window.addEventListener('hashchange', () => {
    lastUrl = location.href;
    if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
    chrome.storage.local.set({ seenKeysWithTime: {} });
    recordUserActivity('hash_change');
  });

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

  // ── Message Listener for Manual Commands ─────────────────────
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
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

      // 4. Algorithm 6 & 11: Hard Gate — Calculate Usefulness Score for Every Lead
      const usefulLeads = fusedLeads.filter(lead => {
        const isUseful = ts.isUsefulDomainEntity ? ts.isUsefulDomainEntity(lead) : Boolean(lead.recruiter_name || lead.email || lead.linkedin_url);
        return isUseful;
      });

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
        // Redundant sighting with zero new fields — discard image without duplicate DB writes
        if (captureId && ts.Visual?.Store) {
          await ts.Visual.Store.discardScreenshot(captureId);
        }
        isScanning = false;
        return;
      }

      lastDiscoveryTimestamp = new Date().toLocaleTimeString();

      // 6. Update Captured Counter in Storage
      try {
        const capLocal = await new Promise(r => chrome.storage.local.get(['totalCaptured'], r));
        await new Promise(r => chrome.storage.local.set({ totalCaptured: (capLocal.totalCaptured || 0) + leadsToProcess.length }, r));
      } catch (_) {}

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
      const entityKey = (r.linkedin_url || r.email || `${r.recruiter_name}@${r.company_name}` || '').toLowerCase();
      if (!entityKey) return;

      const existingRecord = entityMap[entityKey];

      if (!existingRecord) {
        // New Entity Sighting
        updatedMap[entityKey] = {
          name: r.recruiter_name,
          title: r.title,
          company: r.company_name,
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
