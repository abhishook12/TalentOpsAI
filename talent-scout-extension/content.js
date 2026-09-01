// ============================================================
// content.js — Real-Time High-Speed Observer & Ingestion Brain
// 24/7 Zero-Lag Continuous Universal Scraper
// ============================================================

(function() {
  'use strict';

  const ts = window.TalentScout;
  if (!ts) return;

  let isScanning = false;
  let debounceTimer = null;
  let lastUrl = location.href;

  // ── 1. Immediate Initial Scan on Load ──────────────────────
  chrome.storage.sync.get(['authToken'], (settings) => {
    if (settings.authToken) {
      // Instant execution (no delay)
      runScan();
      // Second pass after 1.2s to catch lazy-loaded SPA content
      setTimeout(runScan, 1200);
    }
  });

  // ── 2. Real-Time Mutation Observer (Ultra-Fast 80ms Debounce) ──
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      // Check SPA navigation
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        runScan();
      } else {
        runScan();
      }
    }, 80);
  });

  // Attach observer to entire document
  if (document.body) {
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: false,
      attributes: false,
    });
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: false,
        attributes: false,
      });
      runScan();
    });
  }

  // ── 3. High-Speed Scroll Observer for Feeds & Search ───────
  let scrollTimer = null;
  window.addEventListener('scroll', () => {
    if (!scrollTimer) {
      scrollTimer = setTimeout(() => {
        runScan();
        scrollTimer = null;
      }, 250);
    }
  }, { passive: true });

  // ── 4. Main Real-Time Scan Function ────────────────────────
  async function runScan() {
    if (isScanning) return;
    isScanning = true;

    try {
      const settings = await new Promise(r => chrome.storage.sync.get(['authToken'], r));
      if (!settings.authToken) {
        isScanning = false;
        return;
      }

      // Track pages read locally
      chrome.storage.local.get(['pagesScanned'], (s) => {
        chrome.storage.local.set({ pagesScanned: (s.pagesScanned || 0) + 1 });
      });

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
        return score >= 30; // low threshold = captures everything useful
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

  // ── 5. Local Cache Deduplication ───────────────────────────
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
