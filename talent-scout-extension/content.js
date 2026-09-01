// ============================================================
// content.js — Universal page observer & coordinator
// Runs on every page the user visits
// ============================================================

(function() {
  'use strict';

  const ts = window.TalentScout;
  if (!ts) return; // patterns.js not loaded yet — bail

  // ── State ──────────────────────────────────────────────────
  let isEnabled = true;
  let sessionCaptured = 0;
  let debounceTimer = null;
  let lastUrl = location.href;

  // ── Init ───────────────────────────────────────────────────
  chrome.storage.sync.get(['autoCapture', 'authToken'], (settings) => {
    isEnabled = settings.autoCapture !== false; // default ON
    if (settings.authToken && isEnabled) {
      // Run initial scan after page is ready
      setTimeout(() => runScan(), 800);
    }
  });

  // Listen for settings changes from popup
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'SET_AUTO_CAPTURE') {
      isEnabled = msg.enabled;
    }
    if (msg.type === 'MANUAL_CAPTURE') {
      runScan(true).then(results => sendResponse({ ok: true, count: results.length }));
      return true; // async response
    }
    if (msg.type === 'GET_SESSION_STATS') {
      sendResponse({ ok: true, captured: sessionCaptured });
    }
  });

  // ── MutationObserver — watches for page changes (SPAs) ────
  const observer = new MutationObserver(() => {
    // Debounce: wait 500ms after last mutation before scanning
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      // Detect SPA navigation
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        if (isEnabled) setTimeout(() => runScan(), 600);
      } else {
        // Dynamic content loaded on same URL (infinite scroll, tabs)
        if (isEnabled) runScan();
      }
    }, 500);
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: false,
    attributes: false,
  });

  // ── Main Scan ─────────────────────────────────────────────

  async function runScan(manual = false) {
    // Check auth before every scan
    const settings = await new Promise(r => chrome.storage.sync.get(['authToken', 'autoCapture'], r));
    if (!settings.authToken) return [];
    // Increment pages scanned count locally
    chrome.storage.local.get(['pagesScanned'], (s) => {
      chrome.storage.local.set({ pagesScanned: (s.pagesScanned || 0) + 1 });
    });


    try {
      // Run site-specific detectors
      const linkedin = ts.detectLinkedIn ? ts.detectLinkedIn() : [];
      const email = ts.detectEmail ? ts.detectEmail() : [];
      const indeed = ts.detectIndeed ? ts.detectIndeed() : [];
      const glassdoor = ts.detectGlassdoor ? ts.detectGlassdoor() : [];
      const ziprecruiter = ts.detectZipRecruiter ? ts.detectZipRecruiter() : [];

      // Only use generic if no site-specific detector fired
      const siteSpecificTotal = linkedin.length + email.length + indeed.length
                              + glassdoor.length + ziprecruiter.length;
      const generic = siteSpecificTotal === 0 && ts.detectGeneric ? ts.detectGeneric() : [];

      allResults.push(...linkedin, ...email, ...indeed, ...glassdoor, ...ziprecruiter, ...generic);
    } catch (e) {
      // Silent fail — never break user's browsing
    }

    if (allResults.length === 0) return [];

    // ── Score & filter ─────────────────────────────────────
    const qualified = allResults.filter(r => {
      const score = ts.scoreRelevance(r);
      r._relevance_score = score;
      return score >= 40 || manual; // lower threshold for manual captures
    });

    if (qualified.length === 0) return [];

    // ── Local dedup using cached seen keys ─────────────────
    const deduped = await deduplicateLocally(qualified);
    if (deduped.length === 0) return [];

    // ── Enrich with page metadata ──────────────────────────
    const enriched = deduped.map(r => ({
      ...r,
      source_url: location.href,
      source_page_title: document.title,
      captured_at: new Date().toISOString(),
    }));

    // ── Send to background for queuing ─────────────────────
    chrome.runtime.sendMessage({ type: 'QUEUE_CONTACTS', contacts: enriched });
    sessionCaptured += enriched.length;

    // Update badge count
    chrome.runtime.sendMessage({ type: 'UPDATE_BADGE', count: sessionCaptured });

    return enriched;
  }

  // ── Local dedup: avoid sending same email/URL twice ───────

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
      // Keep only last 2000 entries to prevent storage bloat
      const trimmed = allSeen.slice(-2000);
      chrome.storage.local.set({ seenKeys: trimmed });
    }

    return fresh;
  }

})();
