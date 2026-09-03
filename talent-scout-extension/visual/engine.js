// ============================================================
// visual/engine.js — Visual Intelligence & Evidence-Grounded Extractor
// Analyzes screenshots with Strict Evidence Grounding Gate
// ============================================================

window.TalentScout = window.TalentScout || {};
window.TalentScout.Visual = window.TalentScout.Visual || {};

(function() {
  'use strict';

  const PRODUCTION_API = 'https://talentopsai-1.onrender.com';
  const VISION_ENDPOINT = '/recruiters/extension/vision-analyze';

  /**
   * Classify page before expensive analysis (rejects blank, login, 404, loading)
   */
  function classifyPageContext() {
    const title = (document.title || '').toLowerCase();
    const url = (location.href || '').toLowerCase();
    const bodyText = document.body ? (document.body.innerText || '').slice(0, 500).toLowerCase() : '';

    // Ignore 404 / Error pages
    if (title.includes('404') || title.includes('page not found') || bodyText.includes('404 not found') || bodyText.includes('error occurred')) {
      return { isValid: false, reason: 'error_page' };
    }

    // Ignore Loading states
    if (bodyText.length < 30 || bodyText === 'loading...' || bodyText === 'please wait...') {
      return { isValid: false, reason: 'loading_screen' };
    }

    // Ignore Authentication / Login forms
    if (url.includes('/login') || url.includes('/signin') || url.includes('/signup') || title.includes('log in to') || title.includes('sign in to')) {
      if (!url.includes('/in/') && !url.includes('/talent/') && !url.includes('/company/')) {
        return { isValid: false, reason: 'login_page' };
      }
    }

    const pageType = window.TalentScout.classifyPageType ? window.TalentScout.classifyPageType(location.href, document.title) : 'GENERIC_WEB';

    return {
      isValid: true,
      page_type: pageType,
      page_url: location.href,
      page_title: document.title
    };
  }

  /**
   * Extract visual entities from screenshot using Vision API with client fallback
   */
  async function analyzeScreenshot(screenshotDataUrl, metadata = {}) {
    const pageCheck = classifyPageContext();
    if (!pageCheck.isValid) {
      return {
        status: 'SKIPPED',
        reason: pageCheck.reason,
        entities: [],
      };
    }

    const captureId = metadata.capture_id || `VC-${Math.floor(10000 + Math.random() * 90000)}`;

    const tokenData = await chrome.storage.local.get(['authToken']);
    const token = tokenData.authToken;

    try {
      // 1. Send Screenshot to Backend Gemini Vision Analysis Engine with Immutable capture_id
      const res = await fetch(`${PRODUCTION_API}${VISION_ENDPOINT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({
          capture_id: captureId,
          image_data: screenshotDataUrl,
          page_url: location.href,
          page_title: document.title,
          page_type: pageCheck.page_type,
          change_score: metadata.change_score || 0.5,
          captured_at: new Date().toISOString(),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const geminiEntities = (data.entities || []).map(ent => ({
          ...ent,
          extraction_source: 'gemini_vision_ai',
          capture_id: captureId,
        }));

        console.log(`%c[TalentOps Visual] 👁️ Gemini Vision AI Verified ${geminiEntities.length} Candidate(s) on Screen`, 'color:#6366f1;font-weight:bold;');

        return {
          status: 'SUCCESS',
          capture_id: captureId,
          page_type: pageCheck.page_type,
          entities: geminiEntities,
          metrics: data.metrics || {},
        };
      } else {
        console.warn('[TalentOps Visual] Vision endpoint returned status:', res.status);
      }
    } catch (e) {
      console.warn('[TalentOps Visual] Vision API network error:', e);
    }

    return {
      status: 'AWAITING_VISION',
      capture_id: captureId,
      page_type: pageCheck.page_type,
      entities: [],
      metrics: { people_found: 0, reason: 'Enforcing strict Gemini Vision AI processing' },
    };
  }

  window.TalentScout.Visual.analyzeScreenshot = analyzeScreenshot;
  window.TalentScout.Visual.classifyPageContext = classifyPageContext;
  window.TalentScout.Visual.Engine = { analyzeScreenshot, classifyPageContext };
})();
