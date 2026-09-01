// ============================================================
// content.js — Real-Time High-Speed Observer & Ingestion Brain
// 24/7 Zero-Lag Continuous Universal Scraper
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
    runScan();
    setTimeout(runScan, 800);
    setTimeout(runScan, 2000);
  }, 50);

  // ── 3. Listen for Messages from Background Worker ──────────
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'TRIGGER_SCAN' || msg.type === 'MANUAL_CAPTURE') {
      runScan().then(() => sendResponse({ ok: true }));
      return true;
    }
  });

  // ── 4. Real-Time Mutation Observer (Ultra-Fast 60ms Debounce) ──
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        try {
          chrome.runtime.sendMessage({
            type: 'PAGE_VIEW',
            url: location.href,
            title: document.title,
          });
        } catch (_) {}
      }
      runScan();
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
        runScan();
      }
    });
  }

  // ── 5. High-Speed Scroll Observer for Feeds & Search ───────
  let scrollTimer = null;
  window.addEventListener('scroll', () => {
    if (!scrollTimer) {
      scrollTimer = setTimeout(() => {
        runScan();
        scrollTimer = null;
      }, 200);
    }
  }, { passive: true });

  // ── 6. Main Real-Time Scan Function (Non-Blocking) ─────────
  async function runScan() {
    if (isScanning) return;
    isScanning = true;

    try {
      const allResults = [];

      // Run site-specific detectors
      const linkedin = ts.detectLinkedIn ? ts.detectLinkedIn() : [];
      const email = ts.detectEmail ? ts.detectEmail() : [];
      const indeed = ts.detectIndeed ? ts.detectIndeed() : [];
      const glassdoor = ts.detectGlassdoor ? ts.detectGlassdoor() : [];
      const ziprecruiter = ts.detectZipRecruiter ? ts.detectZipRecruiter() : [];

      // Always run generic scanner as deep fallback to maximize yield
      const generic = ts.detectGeneric ? ts.detectGeneric() : [];

      allResults.push(...linkedin, ...email, ...indeed, ...glassdoor, ...ziprecruiter, ...generic);

      if (allResults.length === 0) {
        isScanning = false;
        return;
      }

      // Filter and score
      const qualified = allResults.filter(r => {
        const score = ts.scoreRelevance(r);
        r._relevance_score = score;
        return score >= 20; // low threshold = captures all useful leads
      });

      if (qualified.length === 0) {
        isScanning = false;
        return;
      }

      // Local fast deduplication (in-memory & cache)
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

    } catch (e) {
      // Silent error handler
    } finally {
      isScanning = false;
    }
  }

  // ── 7. Local Cache Deduplication ───────────────────────────
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
