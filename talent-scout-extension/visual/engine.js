// ============================================================
// visual/engine.js — Visual Intelligence & Multi-Entity Extractor
// Analyzes screenshots for people, titles, companies, emails, phones & context
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
      if (!url.includes('/in/') && !url.includes('/talent/')) {
        return { isValid: false, reason: 'login_page' };
      }
    }

    return { isValid: true, page_url: location.href, page_title: document.title };
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

    const tokenData = await chrome.storage.local.get(['authToken']);
    const token = tokenData.authToken;

    try {
      // 1. Send Screenshot to Backend Vision Analysis Engine
      const res = await fetch(`${PRODUCTION_API}${VISION_ENDPOINT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({
          image_data: screenshotDataUrl,
          page_url: location.href,
          page_title: document.title,
          change_score: metadata.change_score || 0.5,
          captured_at: new Date().toISOString(),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        return {
          status: 'SUCCESS',
          entities: data.entities || [],
          metrics: data.metrics || {},
        };
      }
    } catch (e) {
      // Backend vision offline fallback: extract visible text anchors + canvas regions
    }

    // 2. Client-Side Fallback Vision Heuristic Parser
    return fallbackClientExtraction(metadata);
  }

  /**
   * Fallback visual extraction when vision API is processing
   */
  function fallbackClientExtraction(metadata) {
    const ts = window.TalentScout;
    const results = [];
    const fullText = document.body ? (document.body.innerText || '') : '';

    // Extract corporate emails, phones, and LinkedIn links
    const emails = fullText.match(ts?.PATTERNS?.email || /\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,10}\b/g) || [];
    const phones = fullText.match(ts?.PATTERNS?.phone || /(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g) || [];
    const linkedinUrls = fullText.match(ts?.PATTERNS?.linkedin || /(?:https?:\/\/)?(?:[a-zA-Z0-9_-]+\.)?linkedin\.com\/(?:in|pub)\/([a-zA-Z0-9\-_%]+)/gi) || [];

    // Parse visible names from heading structures
    const headings = document.querySelectorAll('h1, h2, h3, [data-field="name"], .profile-name, [class*="title-text"]');
    headings.forEach((h, idx) => {
      const name = h.textContent?.trim();
      if (name && name.length >= 3 && name.length <= 40 && !name.includes('@') && !/\d{3}/.test(name) && !['feed', 'home', 'jobs', 'messaging', 'notifications', 'search'].includes(name.toLowerCase())) {
        const email = emails[idx] || (emails.length > 0 ? emails[0] : null);
        const phone = phones[idx] || (phones.length > 0 ? phones[0] : null);
        const li = linkedinUrls[idx] || (linkedinUrls.length > 0 ? linkedinUrls[0] : (location.href.includes('linkedin.com/in/') ? location.href.split('?')[0] : null));

        // Locate closest subtitle or description
        const nextElem = h.nextElementSibling || h.parentElement?.querySelector('p, .text-body-medium, [class*="headline"], [class*="subtitle"]');
        let title = nextElem?.textContent?.trim() || 'Professional Lead';
        let company = location.hostname.replace(/^www\./, '').split('.')[0];
        
        if (title && (title.includes(' at ') || title.includes(' @ '))) {
          const parts = title.split(/\s+(?:at|@)\s+/i);
          if (parts[1]) company = parts[1].split(/[,|•\n]/)[0].trim();
        }

        results.push({
          recruiter_name: name,
          title: title.slice(0, 100),
          company_name: company,
          email: email || null,
          phone: phone || null,
          linkedin_url: li || null,
          source: 'visual_capture',
          confidence: 0.85,
          captured_at: new Date().toISOString(),
        });
      }
    });

    return {
      status: 'FALLBACK_SUCCESS',
      entities: results.slice(0, 15),
      metrics: { people_found: results.length },
    };
  }

  // Export to window.TalentScout.Visual.Engine
  window.TalentScout.Visual.Engine = {
    classifyPageContext,
    analyzeScreenshot,
  };

})();
