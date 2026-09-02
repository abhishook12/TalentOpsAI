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
      // 1. Send Screenshot to Backend Vision Analysis Engine with Immutable capture_id
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
        return {
          status: 'SUCCESS',
          capture_id: captureId,
          page_type: pageCheck.page_type,
          entities: data.entities || [],
          metrics: data.metrics || {},
        };
      }
    } catch (e) {
      // Backend vision offline fallback
    }

    // 2. Client-Side Fallback Vision Heuristic Parser
    return fallbackClientExtraction(metadata, captureId, pageCheck.page_type);
  }

  /**
   * Fallback visual extraction when vision API is processing
   */
  function fallbackClientExtraction(metadata, captureId, pageType) {
    const ts = window.TalentScout;
    const results = [];
    const host = location.hostname.toLowerCase();

    // HARD INVARIANT: On a JOB_SEARCH_PAGE (SimplyHired, Indeed /jobs, ZipRecruiter /jobs),
    // job postings are NOT human people!
    if (pageType === 'JOB_SEARCH_PAGE') {
      // Look exclusively for explicit hiring manager / recruiter sections
      const recruiterCards = document.querySelectorAll('[data-testid="recruiter-info"], .hiring-manager, .recruiter-section');
      if (recruiterCards.length === 0) {
        // No explicit human recruiter on job search page
        return {
          status: 'JOB_PAGE_NO_PEOPLE',
          capture_id: captureId,
          page_type: pageType,
          entities: [],
          metrics: { people_found: 0, reason: 'Job search page contains job postings, no explicit recruiter cards' },
        };
      }
    }

    // Extract Page-Level Company Context
    let pageCompany = null;
    const path = location.pathname.toLowerCase();
    
    if (path.includes('/company/')) {
      pageCompany = ts?.text ? ts.text(['.org-top-card-summary__title', 'h1']) : null;
      if (!pageCompany) {
        const m = path.match(/\/company\/([^\/]+)/);
        if (m && m[1]) pageCompany = m[1].replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      }
    }

    // Parse visible candidate cards (LinkedIn /people, etc.)
    const cardElements = document.querySelectorAll('.org-people-profile-card, .discover-person-card, .artdeco-card, [data-view-name="profile-card"], .profile-card, li.reusable-search__result-container');
    
    cardElements.forEach((card) => {
      const rawName = card.querySelector('h3, h4, .org-people-profile-card__profile-title, [class*="name"], a[href*="/in/"]')?.textContent?.trim();
      const nameVal = ts.validateHumanName(rawName);

      // HARD INVARIANT: Must be a validated human name (not job title, UI action, or platform name)
      if (!nameVal.isValid) return;

      const rawSubtitle = card.querySelector('.org-people-profile-card__profile-position, [class*="subtitle"], [class*="occupation"], p')?.textContent?.trim();
      const { title, company_name } = ts.cleanTitleAndCompany(rawSubtitle, null, pageCompany);
      
      const anchor = card.querySelector('a[href*="/in/"]');
      const liUrl = anchor ? anchor.href.split('?')[0] : null;

      const conf = ts.calculateFieldConfidences({
        recruiter_name: nameVal.cleanName,
        title: title,
        company_name: company_name,
        linkedin_url: liUrl,
      });

      const grounding = ts.evaluateEvidenceGrounding({
        recruiter_name: nameVal.cleanName,
        title: title,
        company_name: company_name,
      }, location.href, document.title);

      if (!grounding.is_grounded) return;

      results.push({
        capture_id: captureId,
        recruiter_name: nameVal.cleanName,
        title: title,
        company_name: company_name,
        source_platform: host.includes('linkedin') ? 'LinkedIn' : (host.includes('indeed') ? 'Indeed' : host),
        linkedin_url: liUrl,
        source: 'visual_capture',
        confidence: conf.overall,
        field_confidences: conf,
        evidence_grounding_score: grounding.grounding_score,
        captured_at: new Date().toISOString(),
      });
    });

    return {
      status: 'FALLBACK_SUCCESS',
      capture_id: captureId,
      page_type: pageType,
      entities: results.slice(0, 15),
      metrics: { people_found: results.length },
    };
  }

  window.TalentScout.Visual.analyzeScreenshot = analyzeScreenshot;
  window.TalentScout.Visual.classifyPageContext = classifyPageContext;
})();
