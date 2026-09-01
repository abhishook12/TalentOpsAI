// ============================================================
// detector/linkedin.js — LinkedIn-specific extractor
// Handles: profile pages, search results, Recruiter platform, InMail
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectLinkedIn = function() {
  const host = location.hostname;
  const path = location.pathname;
  const ts = window.TalentScout;

  if (!host.includes('linkedin.com')) return [];

  // ── 1. Single Profile Page (/in/username) ──────────────────
  if (/^\/(in|pub)\/[\w\-%]+/.test(path)) {
    return [_scrapeLinkedInProfile()].filter(Boolean);
  }

  // ── 2. Search Results (/search/results/people/) ─────────────
  if (path.includes('/search/results/people') || path.includes('/search/results/')) {
    return _scrapeLinkedInSearchResults();
  }

  // ── 3. LinkedIn Recruiter Platform ─────────────────────────
  if (host.includes('recruiter.linkedin.com') || path.includes('/talent/')) {
    return _scrapeRecruiterPlatform();
  }

  // ── 4. InMail / Messaging ──────────────────────────────────
  if (path.includes('/messaging/')) {
    return _scrapeLinkedInMessaging();
  }

  // ── 5. Jobs Page — Hiring Team ─────────────────────────────
  if (path.includes('/jobs/view/') || path.includes('/jobs/collections/')) {
    return _scrapeLinkedInJobsPage();
  }

  return [];
};

// ── Private helpers ──────────────────────────────────────────

function _pickFirst(selectors, root) {
  for (const sel of selectors) {
    const el = (root || document).querySelector(sel);
    const t = el?.textContent?.replace(/\s+/g, ' ').trim();
    if (t) return t;
  }
  return null;
}

function _scrapeLinkedInProfile() {
  const ts = window.TalentScout;
  const name = _pickFirst([
    'h1',
    '.text-heading-xlarge',
    '.top-card-layout__title',
    '[data-generated-suggestion-target]',
  ]);

  const title = _pickFirst([
    '.text-body-medium.break-words',
    '.top-card-layout__headline',
    '.pv-text-details__left-panel .text-body-medium',
    '[data-field="headline"]',
  ]);

  const location = _pickFirst([
    '.text-body-small.inline.t-black--light.break-words',
    '.top-card__subline-item',
    '.pv-text-details__left-panel .t-black--light',
    '[data-field="location"]',
  ]);

  const company = _pickFirst([
    '.pv-text-details__right-panel .inline-show-more-text',
    '.pv-text-details__right-panel a',
    '.top-card-layout__card .topcard__org-name-link',
    '.top-card-layout__first-subline a',
    '#experience li:first-child .t-bold span[aria-hidden="true"]',
    '#experience li:first-child .hoverable-link-text span[aria-hidden="true"]',
  ]);

  // Get email from contact info section if open
  const contactSection = document.querySelector('.pv-contact-info__contact-type');
  const email = contactSection ? ts.extractEmail(contactSection.textContent) : null;
  const phone = contactSection ? ts.extractPhone(contactSection.textContent) : null;

  if (!name && !title) return null;

  return {
    recruiter_name: ts.normalizeName(name),
    title: title || null,
    company_name: company || null,
    location: location || null,
    email: email || null,
    phone: phone || null,
    linkedin_url: location.href.split('?')[0],
    source: 'linkedin_profile',
  };
}

function _scrapeLinkedInSearchResults() {
  const ts = window.TalentScout;
  const results = [];

  // New LinkedIn search card selectors
  const cards = document.querySelectorAll([
    'li.reusable-search__result-container',
    '.search-results-container li',
    '[data-chameleon-result-urn]',
    '.entity-result',
  ].join(','));

  cards.forEach(card => {
    const name = _pickFirst([
      '.entity-result__title-text a span[aria-hidden="true"]',
      '.actor-name',
      '.entity-result__title-text',
      'span[aria-hidden="true"]',
    ], card);

    const title = _pickFirst([
      '.entity-result__primary-subtitle',
      '.entity-result__secondary-subtitle',
      '.subline-level-1',
    ], card);

    const company = _pickFirst([
      '.entity-result__secondary-subtitle',
      '.subline-level-2',
      '.entity-result__summary',
    ], card);

    const location = _pickFirst([
      '.entity-result__tertiary-subtitle',
      '.subline-level-3',
    ], card);

    const linkedinAnchor = card.querySelector('a[href*="/in/"]');
    const linkedinUrl = linkedinAnchor ? linkedinAnchor.href.split('?')[0] : null;

    if (!name) return;

    results.push({
      recruiter_name: ts.normalizeName(name),
      title: title || null,
      company_name: company || null,
      location: location || null,
      linkedin_url: linkedinUrl,
      source: 'linkedin_search',
    });
  });

  return results;
}

function _scrapeRecruiterPlatform() {
  const ts = window.TalentScout;
  const results = [];

  const profiles = document.querySelectorAll('.profile-card, .profile-list-item, [data-control-name="view_profile"]');
  profiles.forEach(card => {
    const name = _pickFirst(['.profile-card__name', '.result-lockup__name', 'h3', 'h4'], card);
    const title = _pickFirst(['.profile-card__headline', '.result-lockup__headline', '.t-12'], card);
    const company = _pickFirst(['.profile-card__company', '.result-lockup__company'], card);
    const location = _pickFirst(['.profile-card__location', '.result-lockup__location'], card);
    const linkedinAnchor = card.querySelector('a[href*="/in/"]');

    if (!name) return;
    results.push({
      recruiter_name: ts.normalizeName(name),
      title: title || null,
      company_name: company || null,
      location: location || null,
      linkedin_url: linkedinAnchor ? linkedinAnchor.href.split('?')[0] : null,
      source: 'linkedin_recruiter',
    });
  });

  return results;
}

function _scrapeLinkedInMessaging() {
  const ts = window.TalentScout;
  const results = [];

  // The sender name in the conversation header
  const convHeader = document.querySelector('.msg-thread__link-to-profile, .msg-entity-lockup__entity-title');
  if (!convHeader) return results;

  const name = convHeader.textContent.replace(/\s+/g, ' ').trim();
  const linkedinAnchor = document.querySelector('.msg-thread__link-to-profile, a[href*="/in/"]');

  if (name) {
    results.push({
      recruiter_name: ts.normalizeName(name),
      linkedin_url: linkedinAnchor ? linkedinAnchor.href.split('?')[0] : null,
      source: 'linkedin_messaging',
    });
  }

  return results;
}

function _scrapeLinkedInJobsPage() {
  const ts = window.TalentScout;
  const results = [];

  // Hiring team section
  const hiringTeam = document.querySelectorAll('.hirer-card__hirer-information, .job-details-people-box');
  hiringTeam.forEach(card => {
    const name = _pickFirst(['h3', 'h4', '.name', 'a span'], card);
    const title = _pickFirst(['.sub-components-actor__description', 'p', '.t-12'], card);
    const linkedinAnchor = card.querySelector('a[href*="/in/"]');
    if (!name) return;
    results.push({
      recruiter_name: ts.normalizeName(name),
      title: title || null,
      linkedin_url: linkedinAnchor ? linkedinAnchor.href.split('?')[0] : null,
      source: 'linkedin_jobs',
    });
  });

  return results;
}
