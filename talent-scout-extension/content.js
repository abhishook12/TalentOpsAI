// ============================================================
// content.js — Real-Time High-Speed Observer & Visual-First Ingestion Brain
// Supports 3 Operational Modes: VISUAL (Screenshot-First), DOM, and HYBRID
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

  // ── 2. Immediate Initial Scan on Load ──────────────────────
  setTimeout(() => {
    runUnifiedScan();
    setTimeout(runUnifiedScan, 800);
    setTimeout(runUnifiedScan, 2000);
  }, 50);

  // ── 3. Listen for Messages from Background Worker ──────────
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'TRIGGER_SCAN' || msg.type === 'MANUAL_CAPTURE') {
      runUnifiedScan(true).then(() => sendResponse({ ok: true }));
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
      runUnifiedScan();
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
        runUnifiedScan();
      }
    });
  }

  // ── 5. High-Speed Scroll Observer for Feeds & Search ───────
  let scrollTimer = null;
  window.addEventListener('scroll', () => {
    if (!scrollTimer) {
      scrollTimer = setTimeout(() => {
        runUnifiedScan();
        scrollTimer = null;
      }, 200);
    }
  }, { passive: true });

  // ── 6. Unified Multi-Mode Scan Runner ──────────────────────
  async function runUnifiedScan(force = false) {
    if (isScanning && !force) return;
    isScanning = true;

    try {
      // Check active scraper mode
      const modeRes = await new Promise(r => chrome.runtime.sendMessage({ type: 'GET_SCRAPER_MODE' }, r)).catch(() => ({ mode: 'HYBRID' }));
      const mode = modeRes?.mode || 'HYBRID';

      const results = [];

      // ── A. VISUAL MODE (Screenshot & Screen Understanding First) ──
      if (mode === 'VISUAL' || mode === 'HYBRID') {
        const visualResults = await runVisualScan(force);
        if (visualResults && visualResults.length > 0) {
          results.push(...visualResults);
        }
      }

      // ── B. DOM MODE (HTML & DOM Detectors) ────────────────────────
      if (mode === 'DOM' || (mode === 'HYBRID' && results.length === 0)) {
        const domResults = runDomScan();
        if (domResults && domResults.length > 0) {
          results.push(...domResults);
        }
      }

      if (results.length === 0) {
        isScanning = false;
        return;
      }

      // ── C. Filter, Score, & Deduplicate ──────────────────────────
      const qualified = results.filter(r => {
        const score = ts.scoreRelevance ? ts.scoreRelevance(r) : 50;
        r._relevance_score = score;
        return score >= 20;
      });

      if (qualified.length === 0) {
        isScanning = false;
        return;
      }

      const fresh = await deduplicateLocally(qualified);
      if (fresh.length === 0) {
        isScanning = false;
        return;
      }

      // Enrich metadata
      const enriched = fresh.map(r => ({
        ...r,
        source_url: location.href,
        source_page_title: document.title,
        captured_at: new Date().toISOString(),
      }));

      // Queue instantly to background service worker
      chrome.runtime.sendMessage({
        type: 'QUEUE_CONTACTS',
        contacts: enriched,
      });

      // Housekeeping: purge expired temporary screenshots (2-3 min TTL)
      if (ts.Visual?.Store) {
        ts.Visual.Store.purgeExpired().catch(() => {});
      }

    } catch (e) {
      // Silent catch
    } finally {
      isScanning = false;
    }
  }

  // ── 7. Visual-First Pipeline (Canvas Diff + Temporary Storage + Vision Extraction)
  async function runVisualScan(force = false) {
    if (!ts.Visual?.Diff || !ts.Visual?.Store || !ts.Visual?.Engine) return [];

    // 1. Capture visual frame from background
    const capRes = await new Promise(r => chrome.runtime.sendMessage({ type: 'CAPTURE_VISIBLE_TAB' }, r)).catch(() => null);
    if (!capRes || !capRes.ok || !capRes.dataUrl) return [];

    // 2. Compute visual difference
    const diff = await ts.Visual.Diff.evaluateFrame(capRes.dataUrl);
    if (!diff.isMeaningful && !force) {
      return []; // Frame is identical or tiny noise — skip expensive processing
    }

    // 3. Save to temporary storage with 3-minute TTL
    const stored = await ts.Visual.Store.saveScreenshot({
      page_url: location.href,
      page_title: document.title,
      change_score: diff.score,
      image_data: capRes.dataUrl,
      status: 'PROCESSING',
    });

    // 4. Run Visual Intelligence Analysis
    const analysis = await ts.Visual.Engine.analyzeScreenshot(capRes.dataUrl, {
      change_score: diff.score,
    });

    const entities = analysis?.entities || [];

    // 5. Update temporary storage status and lock in cleanup timer
    if (stored?.id) {
      await ts.Visual.Store.updateStatus(stored.id, 'SYNC_COMPLETE', entities);
    }

    return entities;
  }

  // ── 8. DOM Detectors Pipeline ──────────────────────────────
  function runDomScan() {
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

  // ── 9. Local Cache Deduplication ───────────────────────────
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
