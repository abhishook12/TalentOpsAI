// ============================================================
// content.js — Continuous Autonomous Visual & DOM Data Fusion Brain
// 100% Autonomous • Zero-Configuration • 24/7 Passive Intelligence
// ============================================================

(function() {
  'use strict';

  window.TalentScout = window.TalentScout || {};
  const ts = window.TalentScout;

  let isScanning = false;
  let debounceTimer = null;
  let lastUrl = location.href;

  // ── 1. Notify background of Page View immediately ───────────
  try {
    chrome.runtime.sendMessage({
      type: 'PAGE_VIEW',
      url: location.href,
      title: document.title,
    });
  } catch (_) {}

  // ── 2. Immediate Initial Autonomous Scan on Load ───────────
  setTimeout(() => {
    runAutonomousFusionScan();
    setTimeout(runAutonomousFusionScan, 800);
    setTimeout(runAutonomousFusionScan, 2200);
  }, 60);

  // ── 3. Listen for Messages from Background Worker ──────────
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'TRIGGER_SCAN' || msg.type === 'MANUAL_CAPTURE') {
      runAutonomousFusionScan(true).then(() => sendResponse({ ok: true }));
      return true;
    }
  });

  // ── 4. Real-Time Mutation Observer (Ultra-Fast 60ms Debounce) ──
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        if (ts.Visual?.Diff) ts.Visual.Diff.resetBaseline();
        try {
          chrome.runtime.sendMessage({
            type: 'PAGE_VIEW',
            url: location.href,
            title: document.title,
          });
        } catch (_) {}
      }
      runAutonomousFusionScan();
    }, 60);
  });

  if (document.body) {
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: false,
      attributes: false,
    });
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      if (document.body) {
        observer.observe(document.body, {
          childList: true,
          subtree: true,
          characterData: false,
          attributes: false,
        });
        runAutonomousFusionScan();
      }
    });
  }

  // ── 5. High-Speed Scroll Observer for Feeds & Search ───────
  let scrollTimer = null;
  window.addEventListener('scroll', () => {
    if (!scrollTimer) {
      scrollTimer = setTimeout(() => {
        runAutonomousFusionScan();
        scrollTimer = null;
      }, 220);
    }
  }, { passive: true });

  // ── 6. Autonomous Visual + DOM Data Fusion Engine ──────────
  async function runAutonomousFusionScan(force = false) {
    if (isScanning && !force) return;
    isScanning = true;

    try {
      // 1. Run Visual-First Screen Capture & Understanding
      const visualLeads = await runVisualCapturePipeline(force);

      // 2. Run DOM & Microdata Heuristic Scanners
      const domLeads = runDomDetectorPipeline();

      // 3. FUSE DATA: Merge Visual + DOM intelligence into superior enriched records
      const fusedLeads = fuseVisualAndDomLeads(visualLeads, domLeads);

      if (fusedLeads.length === 0) {
        isScanning = false;
        return;
      }

      // 4. Quality Scoring
      const qualified = fusedLeads.filter(r => {
        const score = ts.scoreRelevance ? ts.scoreRelevance(r) : 50;
        r._relevance_score = score;
        return score >= 20;
      });

      if (qualified.length === 0) {
        isScanning = false;
        return;
      }

      // 5. Local Fast Deduplication
      const fresh = await deduplicateLocally(qualified);
      if (fresh.length === 0) {
        isScanning = false;
        return;
      }

      // 6. Enrich Metadata
      const enriched = fresh.map(r => ({
        ...r,
        source_url: location.href,
        source_page_title: document.title,
        captured_at: new Date().toISOString(),
      }));

      // 7. Stream directly to background service worker
      chrome.runtime.sendMessage({
        type: 'QUEUE_CONTACTS',
        contacts: enriched,
      });

      // 8. Auto-Purge expired temporary screenshots (2-3 min TTL)
      if (ts.Visual?.Store) {
        ts.Visual.Store.purgeExpired().catch(() => {});
      }

    } catch (e) {
      // Silent error handler
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

    // Save temporary screenshot into IndexedDB with 3-minute TTL
    const stored = await ts.Visual.Store.saveScreenshot({
      page_url: location.href,
      page_title: document.title,
      change_score: diff.score,
      image_data: capRes.dataUrl,
      status: 'PROCESSING',
    });

    // Run Visual Intelligence Multi-Entity Extraction
    const analysis = await ts.Visual.Engine.analyzeScreenshot(capRes.dataUrl, {
      change_score: diff.score,
    });

    const entities = analysis?.entities || [];

    // Lock in cleanup timer after sync
    if (stored?.id) {
      await ts.Visual.Store.updateStatus(stored.id, 'SYNC_COMPLETE', entities);
    }

    return entities;
  }

  // ── 8. DOM Detector Pipeline ───────────────────────────────
  function runDomDetectorPipeline() {
    const all = [];
    const linkedin = ts.detectLinkedIn ? ts.detectLinkedIn() : [];
    const email = ts.detectEmail ? ts.detectEmail() : [];
    const indeed = ts.detectIndeed ? ts.detectIndeed() : [];
    const glassdoor = ts.detectGlassdoor ? ts.detectGlassdoor() : [];
    const ziprecruiter = ts.detectZipRecruiter ? ts.detectZipRecruiter() : [];
    const generic = ts.detectGeneric ? ts.detectGeneric() : [];

    all.push(...linkedin, ...email, ...indeed, ...glassdoor, ...ziprecruiter, ...generic);
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
        existing.source = 'visual_dom_fusion';
      } else if (key) {
        mergedMap.set(key, { ...v, source: 'visual_capture' });
      }
    });

    return Array.from(mergedMap.values());
  }

  // ── 10. Local Cache Deduplication ──────────────────────────
  async function deduplicateLocally(results) {
    const stored = await new Promise(r => chrome.storage.local.get(['seenKeys'], r));
    const seenKeys = new Set(stored.seenKeys || []);
    const newKeys = [];
    const fresh = [];

    results.forEach(r => {
      const key = r.email || r.linkedin_url || `${r.recruiter_name}@${r.company_name}`;
      if (!key || seenKeys.has(key)) return;
      seenKeys.add(key);
      newKeys.push(key);
      fresh.push(r);
    });

    if (newKeys.length > 0) {
      const allSeen = [...seenKeys];
      const trimmed = allSeen.slice(-3000);
      chrome.storage.local.set({ seenKeys: trimmed });
    }

    return fresh;
  }

})();
