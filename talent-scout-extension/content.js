// ============================================================
// content.js — Continuous Autonomous Visual & DOM Data Fusion Brain
// 100% Autonomous • Zero-Configuration • Complete Forensic Provenance
// ============================================================

(function() {
  'use strict';

  // Prevent double-injection
  if (window.__talentScoutInjected) return;
  window.__talentScoutInjected = true;

  window.TalentScout = window.TalentScout || {};
  const ts = window.TalentScout;

  let isScanning = false;
  let debounceTimer = null;
  let lastUrl = location.href;
  let scanCount = 0;

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

  // ── 1. Notify background of Page View immediately ───────────
  try {
    chrome.runtime.sendMessage({
      type: 'PAGE_VIEW',
      url: location.href,
      title: document.title,
    });
    logEvent('PAGE_OBSERVED', document.title || location.hostname);
  } catch (_) {}

  // ── 2. Immediate Initial Autonomous Scan & Periodic Continuous Heartbeat ──
  let initialCaptureDone = false;

  // Immediate burst on page injection — staggered to let LinkedIn JS render
  setTimeout(() => runAutonomousFusionScan(true), 300);
  setTimeout(() => runAutonomousFusionScan(true), 1500);
  setTimeout(() => runAutonomousFusionScan(true), 3000);

  // 100% Autonomous 24/7 Fast Heartbeat Ticker: Scans active page continuously every 2s
  setInterval(() => {
    if (document.visibilityState === 'visible') {
      runAutonomousFusionScan(false);
    }
  }, 2000);

  // ── 3. Listen for Messages from Background Worker ──────────
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'TRIGGER_SCAN' || msg.type === 'MANUAL_CAPTURE') {
      // Clear dedup cache on manual capture so it re-captures everything visible
      if (msg.type === 'MANUAL_CAPTURE') {
        chrome.storage.local.set({ seenKeys: [] });
      }
      runAutonomousFusionScan(true).then(() => sendResponse({ ok: true }));
      return true;
    }
  });

  // ── 4. Real-Time Dynamic Observers (Mutations, Focus, Visibility, SPA Navigation) ──
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
        logEvent('PAGE_CHANGED', document.title || location.hostname);
        try {
          chrome.runtime.sendMessage({
            type: 'PAGE_VIEW',
            url: location.href,
            title: document.title,
          });
        } catch (_) {}
        // Clear dedup on navigation so new page gets fresh capture
        chrome.storage.local.set({ seenKeys: [] });
      }
      runAutonomousFusionScan(false);
    }, 100);
  });
  observer.observe(document.body || document.documentElement, {
    childList: true,
    subtree: true,
    characterData: false,
    attributes: false,
  });

  // Window Focus & Tab Visibility Listeners
  window.addEventListener('focus', () => runAutonomousFusionScan(true));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') runAutonomousFusionScan(true);
  });

  // SPA Navigation Catchers (popstate, hashchange)
  window.addEventListener('popstate', () => {
    lastUrl = location.href;
    if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
    chrome.storage.local.set({ seenKeys: [] });
    runAutonomousFusionScan(true);
  });
  window.addEventListener('hashchange', () => {
    lastUrl = location.href;
    if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
    chrome.storage.local.set({ seenKeys: [] });
    runAutonomousFusionScan(true);
  });

  // ── 5. High-Speed Scroll Observer for Feeds & Search ───────
  let scrollTimer = null;
  window.addEventListener('scroll', () => {
    if (!scrollTimer) {
      scrollTimer = setTimeout(() => {
        runAutonomousFusionScan(false);
        scrollTimer = null;
      }, 250);
    }
  }, { passive: true });

  // ── 6. Autonomous Visual + DOM Data Fusion Engine ──────────
  async function runAutonomousFusionScan(force = false) {
    if (isScanning && !force) return;
    
    // Always force the very first page load execution
    if (!initialCaptureDone) {
      force = true;
      initialCaptureDone = true;
    }

    isScanning = true;
    scanCount++;

    try {
      // 1. Run Visual-First Screen Capture & Understanding
      let visualLeads = [];
      try {
        visualLeads = await runVisualCapturePipeline(force);
      } catch (vizErr) {
        logEvent('VISUAL_ERROR', String(vizErr?.message || vizErr).slice(0, 120));
      }

      // 2. Run DOM & Microdata Heuristic Scanners (THIS IS THE PRIMARY ENGINE)
      let domLeads = [];
      try {
        domLeads = runDomDetectorPipeline();
      } catch (domErr) {
        logEvent('DOM_ERROR', String(domErr?.message || domErr).slice(0, 120));
      }

      // 3. FUSE DATA: Merge Visual + DOM intelligence into superior enriched records
      const fusedLeads = fuseVisualAndDomLeads(visualLeads, domLeads);

      if (fusedLeads.length === 0) {
        isScanning = false;
        return;
      }

      // 4. Accept all valid discovered contacts (Zero artificial keyword score blocks)
      const qualified = fusedLeads.filter(r => {
        return Boolean(r.recruiter_name || r.email || r.linkedin_url);
      });

      if (qualified.length === 0) {
        isScanning = false;
        return;
      }

      // 5. Local Fast Deduplication (time-limited: re-allow after 60 seconds)
      const fresh = await deduplicateLocally(qualified);
      if (fresh.length === 0) {
        isScanning = false;
        return;
      }

      // 6. Update Captured counter IMMEDIATELY
      try {
        const capLocal = await new Promise(r => chrome.storage.local.get(['totalCaptured'], r));
        await new Promise(r => chrome.storage.local.set({ totalCaptured: (capLocal.totalCaptured || 0) + fresh.length }, r));
      } catch (_) {}

      // 7. Enrich Metadata with Provenance Trace
      const enriched = fresh.map(r => ({
        ...r,
        discovery_id: r.discovery_id || ('DISC-' + crypto.randomUUID().slice(0, 8).toUpperCase()),
        capture_id: r.capture_id || ('CAP-' + Math.floor(10000 + Math.random() * 90000)),
        source_url: location.href,
        source_page_title: document.title,
        captured_at: new Date().toISOString(),
        confidence: r.confidence || 92,
      }));

      logEvent('DATA_EXTRACTED', `Discovered ${enriched.length} contact(s): ${enriched.map(e => e.recruiter_name).join(', ')}`);

      // 8. Stream directly to background service worker for sync
      try {
        chrome.runtime.sendMessage({
          type: 'QUEUE_CONTACTS',
          contacts: enriched,
        });
      } catch (queueErr) {
        logEvent('QUEUE_ERROR', String(queueErr?.message || queueErr).slice(0, 120));
      }

      // 9. Auto-Purge expired temporary screenshots (2-3 min TTL)
      if (ts.Visual?.Store) {
        try {
          const purged = await ts.Visual.Store.purgeExpired();
          if (purged > 0) {
            logEvent('SCREENSHOT_PURGED', `${purged} temporary buffer image(s) deleted`);
          }
        } catch (_) {}
      }

    } catch (e) {
      logEvent('SCAN_ERROR', String(e?.message || e).slice(0, 200));
    } finally {
      isScanning = false;
    }
  }

  // ── 7. Visual-First Pipeline ───────────────────────────────
  async function runVisualCapturePipeline(force = false) {
    if (!ts.Visual?.Diff || !ts.Visual?.Store || !ts.Visual?.Engine) return [];

    // Capture visual frame from background
    const capRes = await new Promise(r => chrome.runtime.sendMessage({ type: 'CAPTURE_VISIBLE_TAB' }, r)).catch(() => null);
    if (!capRes || !capRes.ok || !capRes.dataUrl) return [];

    // Evaluate visual difference score
    const diff = await ts.Visual.Diff.evaluateFrame(capRes.dataUrl);
    if (!diff.isMeaningful && !force) {
      return []; // Tiny/unimportant animation change — skip
    }

    const captureId = 'VC-' + Math.floor(10000 + Math.random() * 90000);
    logEvent('SCREENSHOT_CAPTURED', `${captureId} (Delta: ${Math.round(diff.score * 100)}%)`);

    // Save temporary screenshot into IndexedDB with 3-minute TTL
    const stored = await ts.Visual.Store.saveScreenshot({
      id: captureId,
      page_url: location.href,
      page_title: document.title,
      change_score: diff.score,
      image_data: capRes.dataUrl,
      status: 'PROCESSING',
    });

    logEvent('VISION_PROCESSING', `${captureId} analyzing people & context`);

    // Run Visual Intelligence Multi-Entity Extraction
    const analysis = await ts.Visual.Engine.analyzeScreenshot(capRes.dataUrl, {
      change_score: diff.score,
      capture_id: captureId,
    });

    const entities = (analysis?.entities || []).map(e => ({
      ...e,
      capture_id: captureId,
      visual_change_score: diff.score,
      screenshot_preview: capRes.dataUrl.slice(0, 150) + '...', // safe preview token
    }));

    if (entities.length > 0) {
      logEvent('FOUND_PEOPLE', `${entities.length} people identified visually in ${captureId}`);
    }

    // Lock in cleanup timer after sync
    if (stored?.id) {
      await ts.Visual.Store.updateStatus(stored.id, 'SYNC_COMPLETE', entities);
    }

    return entities;
  }

  // ── 8. DOM Detector Pipeline ───────────────────────────────
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

  // ── 9. Data Fusion: Merge Visual & DOM Discoveries ──────────
  function fuseVisualAndDomLeads(visualLeads = [], domLeads = []) {
    const mergedMap = new Map();

    // Ingest DOM leads first as baseline
    domLeads.forEach(d => {
      const key = (d.email || d.linkedin_url || `${d.recruiter_name}@${d.company_name}` || '').toLowerCase();
      if (key) mergedMap.set(key, { ...d });
    });

    // Merge Visual leads into matching records or append new ones
    visualLeads.forEach(v => {
      const key = (v.email || v.linkedin_url || `${v.recruiter_name}@${v.company_name}` || '').toLowerCase();
      if (key && mergedMap.has(key)) {
        const existing = mergedMap.get(key);
        // Enrich existing with visual context
        if (v.title && !existing.title) existing.title = v.title;
        if (v.company_name && !existing.company_name) existing.company_name = v.company_name;
        if (v.phone && !existing.phone) existing.phone = v.phone;
        if (v.location && !existing.location) existing.location = v.location;
        existing.capture_id = v.capture_id || existing.capture_id;
        existing.visual_change_score = v.visual_change_score || existing.visual_change_score;
        existing.source = 'visual_dom_fusion';
      } else if (key) {
        mergedMap.set(key, { ...v, source: 'visual_capture' });
      }
    });

    return Array.from(mergedMap.values());
  }

  // ── 10. Local Cache Deduplication (with 2-minute TTL per key) ──
  async function deduplicateLocally(results) {
    const stored = await new Promise(r => chrome.storage.local.get(['seenKeysWithTime'], r));
    const seenMap = stored.seenKeysWithTime || {};
    const now = Date.now();
    const TTL = 120000; // 2 minutes — allow re-capture after this time
    const newEntries = {};
    const fresh = [];

    results.forEach(r => {
      const key = r.email || r.linkedin_url || `${r.recruiter_name}@${r.company_name}`;
      if (!key) return;
      
      const lastSeen = seenMap[key];
      if (lastSeen && (now - lastSeen) < TTL) return; // Still within cooldown
      
      newEntries[key] = now;
      fresh.push(r);
    });

    if (Object.keys(newEntries).length > 0) {
      // Merge and trim to prevent unbounded growth
      const merged = { ...seenMap, ...newEntries };
      const keys = Object.keys(merged);
      if (keys.length > 2000) {
        // Keep only most recent 1500
        const sorted = keys.sort((a, b) => merged[b] - merged[a]).slice(0, 1500);
        const trimmed = {};
        sorted.forEach(k => trimmed[k] = merged[k]);
        chrome.storage.local.set({ seenKeysWithTime: trimmed });
      } else {
        chrome.storage.local.set({ seenKeysWithTime: merged });
      }
    }

    return fresh;
  }

})();
