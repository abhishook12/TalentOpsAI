// ============================================================
// content.js — Ultra-Fast Autonomous Visual & DOM Data Fusion Brain
// 100% Autonomous • Zero-Configuration • Complete Forensic Provenance
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

  console.log('%c[TalentOps Scout] 🚀 Autonomous Scout Engine Active on: ' + location.hostname, 'color:#3b82f6;font-weight:bold;');

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
  setTimeout(() => runAutonomousFusionScan(true), 200);
  setTimeout(() => runAutonomousFusionScan(true), 1000);
  setTimeout(() => runAutonomousFusionScan(true), 2500);

  // 100% Autonomous 24/7 Fast Heartbeat: Scans active page continuously every 1.5s
  setInterval(() => {
    if (document.visibilityState === 'visible') {
      runAutonomousFusionScan(false);
    }
  }, 1500);

  // ── 3. Listen for Messages from Background Worker ──────────
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'TRIGGER_SCAN' || msg.type === 'MANUAL_CAPTURE') {
      if (msg.type === 'MANUAL_CAPTURE') {
        chrome.storage.local.set({ seenKeysWithTime: {} });
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
        // Clear dedup on navigation so new profile gets fresh capture
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

  // Window Focus & Tab Visibility Listeners
  window.addEventListener('focus', () => runAutonomousFusionScan(true));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') runAutonomousFusionScan(true);
  });

  // SPA Navigation Catchers (popstate, hashchange)
  window.addEventListener('popstate', () => {
    lastUrl = location.href;
    if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
    chrome.storage.local.set({ seenKeysWithTime: {} });
    runAutonomousFusionScan(true);
  });
  window.addEventListener('hashchange', () => {
    lastUrl = location.href;
    if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
    chrome.storage.local.set({ seenKeysWithTime: {} });
    runAutonomousFusionScan(true);
  });

  // Scroll Observer for Feeds & Search
  let scrollTimer = null;
  window.addEventListener('scroll', () => {
    if (!scrollTimer) {
      scrollTimer = setTimeout(() => {
        runAutonomousFusionScan(false);
        scrollTimer = null;
      }, 200);
    }
  }, { passive: true });

  // ── 5. Autonomous Visual + DOM Data Fusion Engine ──────────
  async function runAutonomousFusionScan(force = false) {
    if (isScanning && !force) return;
    isScanning = true;

    try {
      // 1. FIRST: Run DOM & Microdata Heuristic Scanners IMMEDIATELY (< 3ms)
      let domLeads = [];
      try {
        domLeads = runDomDetectorPipeline();
      } catch (domErr) {
        logEvent('DOM_ERROR', String(domErr?.message || domErr).slice(0, 120));
      }

      // 2. SECOND: Run Visual Pipeline in Background with Strict 2s Timeout
      let visualLeads = [];
      try {
        visualLeads = await Promise.race([
          runVisualCapturePipeline(force),
          new Promise(r => setTimeout(() => r([]), 2000))
        ]);
      } catch (vizErr) {
        logEvent('VISUAL_ERROR', String(vizErr?.message || vizErr).slice(0, 120));
      }

      // 3. FUSE DATA: Merge Visual + DOM intelligence
      const fusedLeads = fuseVisualAndDomLeads(visualLeads, domLeads);

      if (fusedLeads.length === 0) {
        isScanning = false;
        return;
      }

      // 4. Filter Qualified Leads
      const qualified = fusedLeads.filter(r => {
        return Boolean(r.recruiter_name || r.email || r.linkedin_url);
      });

      if (qualified.length === 0) {
        isScanning = false;
        return;
      }

      // 5. Local Fast Deduplication (60-second window)
      const fresh = await deduplicateLocally(qualified);
      if (fresh.length === 0) {
        isScanning = false;
        return;
      }

      // 6. Update Captured Counter in Chrome Storage Immediately
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
        confidence: r.confidence || 95,
      }));

      const leadNames = enriched.map(e => e.recruiter_name).filter(Boolean).join(', ');
      console.log(`%c[TalentOps Scout] 🎯 Discovered ${enriched.length} Lead(s): ${leadNames}`, 'color:#10b981;font-weight:bold;');
      logEvent('DATA_EXTRACTED', `Discovered ${enriched.length} contact(s): ${leadNames}`);

      // 8. Stream directly to background service worker for instant sync
      try {
        chrome.runtime.sendMessage({
          type: 'QUEUE_CONTACTS',
          contacts: enriched,
        });
      } catch (queueErr) {
        logEvent('QUEUE_ERROR', String(queueErr?.message || queueErr).slice(0, 120));
      }

      // 9. Auto-Purge expired temporary screenshots
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

  // ── 6. Visual-First Pipeline ───────────────────────────────
  async function runVisualCapturePipeline(force = false) {
    if (!ts.Visual?.Diff || !ts.Visual?.Store || !ts.Visual?.Engine) return [];

    // Capture visual frame from background
    const capRes = await new Promise(r => {
      chrome.runtime.sendMessage({ type: 'CAPTURE_VISIBLE_TAB' }, res => {
        r(res || null);
      });
      // 1.5s watchdog timeout for background message
      setTimeout(() => r(null), 1500);
    }).catch(() => null);

    if (!capRes || !capRes.ok || !capRes.dataUrl) return [];

    // Evaluate visual difference score
    const diff = await ts.Visual.Diff.evaluateFrame(capRes.dataUrl);
    if (!diff.isMeaningful && !force) {
      return [];
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
      screenshot_preview: capRes.dataUrl.slice(0, 150) + '...',
    }));

    if (entities.length > 0) {
      logEvent('FOUND_PEOPLE', `${entities.length} people identified visually in ${captureId}`);
    }

    if (stored?.id) {
      await ts.Visual.Store.updateStatus(stored.id, 'SYNC_COMPLETE', entities);
    }

    return entities;
  }

  // ── 7. DOM Detector Pipeline ───────────────────────────────
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

  // ── 8. Data Fusion: Merge Visual & DOM Discoveries ──────────
  function fuseVisualAndDomLeads(visualLeads = [], domLeads = []) {
    const mergedMap = new Map();

    // Ingest DOM leads first as primary source
    domLeads.forEach(d => {
      const key = (d.email || d.linkedin_url || `${d.recruiter_name}@${d.company_name}` || '').toLowerCase();
      if (key) mergedMap.set(key, { ...d });
    });

    // Merge Visual leads into matching records or append new ones
    visualLeads.forEach(v => {
      const key = (v.email || v.linkedin_url || `${v.recruiter_name}@${v.company_name}` || '').toLowerCase();
      if (key && mergedMap.has(key)) {
        const existing = mergedMap.get(key);
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

  // ── 9. Local Cache Deduplication (with 60-second TTL per key) ──
  async function deduplicateLocally(results) {
    const stored = await new Promise(r => chrome.storage.local.get(['seenKeysWithTime'], r));
    const seenMap = stored.seenKeysWithTime || {};
    const now = Date.now();
    const TTL = 60000; // 60 seconds TTL for fast re-evaluation
    const newEntries = {};
    const fresh = [];

    results.forEach(r => {
      const key = r.email || r.linkedin_url || `${r.recruiter_name}@${r.company_name}`;
      if (!key) return;
      
      const lastSeen = seenMap[key];
      if (lastSeen && (now - lastSeen) < TTL) return;
      
      newEntries[key] = now;
      fresh.push(r);
    });

    if (Object.keys(newEntries).length > 0) {
      const merged = { ...seenMap, ...newEntries };
      const keys = Object.keys(merged);
      if (keys.length > 1500) {
        const sorted = keys.sort((a, b) => merged[b] - merged[a]).slice(0, 1000);
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
