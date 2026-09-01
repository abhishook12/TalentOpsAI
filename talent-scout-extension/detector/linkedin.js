// ============================================================
// detector/linkedin.js — Bulletproof LinkedIn Scraper
// Uses DOM Selectors + OpenGraph Tags + Document Title + Text Stream
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectLinkedIn = function() {
  const host = location.hostname.toLowerCase();
  const path = location.pathname;
  const ts = window.TalentScout;

  if (!host.includes('linkedin.com')) return [];

  const results = [];

  // ── 1. Single Profile Page (/in/ or /pub/) ─────────────────
  if (/^\/(in|pub)\//.test(path)) {
    const single = _scrapeSingleProfile();
    if (single) results.push(single);
  }

  // ── 2. Search Results, Recruiter & Network Cards ───────────
  results.push(..._scrapeSearchCards());
  results.push(..._scrapeRecruiterPlatform());
  results.push(..._scrapeMessaging());
  results.push(..._scrapeFeedPosts());
  results.push(..._scrapeAllLinkedInCards());

  // ── 3. Page Title & Meta Fallback (Guaranteed Yield) ───────
  if (results.length === 0 && /^\/(in|pub)\//.test(path)) {
    const fallback = _scrapeFromTitleAndMeta();
    if (fallback) results.push(fallback);
  }

  // Deduplicate locally
  const seen = new Set();
  return results.filter(r => {
    const key = r.linkedin_url || r.email || r.recruiter_name;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

// ── Private Extractors ───────────────────────────────────────

function _scrapeSingleProfile() {
  const ts = window.TalentScout;
  const cleanUrl = window.location.href.split('?')[0].split('#')[0];

  // Name — try multiple modern and legacy LinkedIn DOM selectors
  let name = ts.text([
    'h1.text-heading-xlarge',
    'h1.inline',
    'h1',
    '.top-card-layout__title',
    '[data-generated-suggestion-target]',
    '.pv-top-card--list li:first-child',
    '.artdeco-entity-lockup__title',
    '[data-field="name"]',
    '.ph5 h1',
    '.mt2 h1',
  ]);

  // Title / Headline
  let title = ts.text([
    '.text-body-medium.break-words',
    '.top-card-layout__headline',
    '.pv-text-details__left-panel .text-body-medium',
    '[data-field="headline"]',
    '.artdeco-entity-lockup__subtitle',
    '.ph5 .text-body-medium',
  ]);

  // Location
  const location = ts.text([
    '.text-body-small.inline.t-black--light.break-words',
    '.top-card__subline-item',
    '.pv-text-details__left-panel .t-black--light',
    '[data-field="location"]',
    '.ph5 .text-body-small',
  ]);

  // Company
  let company = ts.text([
    '.pv-text-details__right-panel .inline-show-more-text',
    '.pv-text-details__right-panel a',
    '.top-card-layout__card .topcard__org-name-link',
    '.top-card-layout__first-subline a',
    '#experience li:first-child .t-bold span[aria-hidden="true"]',
    '#experience li:first-child .hoverable-link-text span[aria-hidden="true"]',
    'button[aria-label*="Current company"]',
  ]);

  // Infer company from headline if missing (e.g. "Job recruiter at ASP-Web Solutions")
  if (!company && title) {
    const atMatch = title.match(/\b(?:at|@)\s+([^,|•\n\r]+)/i);
    if (atMatch) company = atMatch[1].trim();
    else if (title.includes(' | ')) {
      const parts = title.split(' | ');
      if (parts.length >= 2) company = parts[parts.length - 1].trim();
    }
  }

  // Title & Meta tags fallback if name missing
  if (!name) {
    const metaTitle = document.querySelector('meta[property="og:title"]')?.content || document.title;
    if (metaTitle && (metaTitle.includes('|') || metaTitle.includes('-'))) {
      const parts = metaTitle.split('|')[0].split(' - ');
      name = parts[0]?.trim();
      if (parts[1] && !title) title = parts[1]?.trim();
      if (parts[2] && !company) company = parts[2]?.trim();
    }
  }

  const finalName = ts.normalizeName(name) || ts.inferNameFromLinkedInSlug(cleanUrl);

  // Extract contact info
  const fullText = document.body ? (document.body.innerText || '') : '';
  const email = ts.extractEmail(fullText);
  const phone = ts.extractPhone(fullText);

  if (!finalName && !title) return null;

  return {
    recruiter_name: finalName || ts.inferNameFromLinkedInSlug(cleanUrl) || 'LinkedIn Member',
    title: title || 'Professional',
    company_name: company || null,
    location: location || null,
    email: email || null,
    phone: phone || null,
    linkedin_url: cleanUrl,
    source: 'linkedin_profile',
  };
}

function _scrapeFromTitleAndMeta() {
  const ts = window.TalentScout;
  const rawTitle = document.title || '';
  if (!rawTitle) return null;

  const cleanUrl = window.location.href.split('?')[0].split('#')[0];
  const inferredName = ts.inferNameFromLinkedInSlug(cleanUrl);

  const parts = rawTitle.replace(/\s*\|\s*LinkedIn$/i, '').split(/\s*[-–—|]\s*/);
  const name = ts.normalizeName(parts[0]) || inferredName;
  const title = parts[1] || null;
  const company = parts[2] || null;

  if (!name) return null;

  return {
    recruiter_name: name,
    title: title || 'Recruiter / Professional',
    company_name: company || null,
    linkedin_url: cleanUrl,
    source: 'linkedin_meta',
  };
}

function _scrapeSearchCards() {
  const ts = window.TalentScout;
  const cards = document.querySelectorAll([
    'li.reusable-search__result-container',
    '.search-results-container li',
    '[data-chameleon-result-urn]',
    '.entity-result',
    '.discover-person-card',
    '.mn-discovery-person-card',
    '.artdeco-entity-lockup',
    '[data-view-name="search-entity-result-universal-template"]',
  ].join(','));

  const results = [];

  cards.forEach(card => {
    const anchor = card.querySelector('a[href*="/in/"]');
    if (!anchor) return;

    const href = anchor.href.split('?')[0].split('#')[0];
    const name = ts.text([
      '.entity-result__title-text a span[aria-hidden="true"]',
      '.discover-person-card__name',
      '.artdeco-entity-lockup__title',
      'span[aria-hidden="true"]',
      'h3', 'h4',
    ], card);

    const title = ts.text([
      '.entity-result__primary-subtitle',
      '.discover-person-card__occupation',
      '.artdeco-entity-lockup__subtitle',
      '.subline-level-1',
    ], card);

    const company = ts.text([
      '.entity-result__secondary-subtitle',
      '.subline-level-2',
      '.entity-result__summary',
    ], card);

    const location = ts.text([
      '.entity-result__tertiary-subtitle',
      '.subline-level-3',
    ], card);

    const finalName = ts.normalizeName(name) || ts.inferNameFromLinkedInSlug(href);
    if (!finalName) return;

    results.push({
      recruiter_name: finalName,
      title: title || 'Professional',
      company_name: company || null,
      location: location || null,
      linkedin_url: href,
      source: 'linkedin_search',
    });
  });

  return results;
}

function _scrapeRecruiterPlatform() {
  const ts = window.TalentScout;
  const results = [];
  const cards = document.querySelectorAll('.profile-card, .profile-list-item, [data-control-name="view_profile"], .talent-card');

  cards.forEach(card => {
    const anchor = card.querySelector('a[href*="/in/"], a[href*="/talent/profile/"]');
    const name = ts.text(['.profile-card__name', '.result-lockup__name', 'h3', 'h4'], card);
    const title = ts.text(['.profile-card__headline', '.result-lockup__headline', '.t-12'], card);
    const company = ts.text(['.profile-card__company', '.result-lockup__company'], card);
    const location = ts.text(['.profile-card__location', '.result-lockup__location'], card);

    const finalName = ts.normalizeName(name) || (anchor ? ts.inferNameFromLinkedInSlug(anchor.href) : null);
    if (!finalName) return;

    results.push({
      recruiter_name: finalName,
      title: title || null,
      company_name: company || null,
      location: location || null,
      linkedin_url: anchor ? anchor.href.split('?')[0] : null,
      source: 'linkedin_recruiter',
    });
  });

  return results;
}

function _scrapeMessaging() {
  const ts = window.TalentScout;
  const results = [];
  const threads = document.querySelectorAll('.msg-conversation-listitem, .msg-thread__header, .msg-entity-lockup');

  threads.forEach(t => {
    const name = ts.text(['.msg-conversation-listitem__participant-names', '.msg-entity-lockup__entity-title', 'h2', 'h3'], t);
    const anchor = t.querySelector('a[href*="/in/"]');
    const finalName = ts.normalizeName(name);
    if (!finalName) return;

    results.push({
      recruiter_name: finalName,
      linkedin_url: anchor ? anchor.href.split('?')[0] : null,
      source: 'linkedin_messaging',
    });
  });

  return results;
}

function _scrapeFeedPosts() {
  const ts = window.TalentScout;
  const results = [];
  const posts = document.querySelectorAll('.feed-shared-update-v2, .feed-shared-actor, [data-urn*="activity"]');

  posts.forEach(post => {
    const actorName = ts.text(['.update-components-actor__name', '.feed-shared-actor__name'], post);
    const actorTitle = ts.text(['.update-components-actor__description', '.feed-shared-actor__description'], post);
    const anchor = post.querySelector('.update-components-actor__container-link, a[href*="/in/"]');
    const finalName = ts.normalizeName(actorName);

    if (finalName) {
      results.push({
        recruiter_name: finalName,
        title: actorTitle || 'Hiring Lead',
        linkedin_url: anchor ? anchor.href.split('?')[0] : null,
        email: ts.extractEmail(post.innerText || ''),
        phone: ts.extractPhone(post.innerText || ''),
        source: 'linkedin_feed',
      });
    }
  });

  return results;
}

function _scrapeAllLinkedInCards() {
  const ts = window.TalentScout;
  const results = [];
  const cleanUrl = window.location.href.split('?')[0].split('#')[0];

  const allProfileAnchors = document.querySelectorAll('a[href*="/in/"]');
  allProfileAnchors.forEach(a => {
    const href = a.href.split('?')[0].split('#')[0];
    if (href === cleanUrl || !href.includes('/in/')) return;

    const container = a.closest('li, div.artdeco-entity-lockup, div.discover-person-card, section, div.feed-shared-following-card, .profile-card, aside div, [class*="card"], [class*="lockup"]') || a.parentElement;
    if (!container) return;

    const nameText = a.querySelector('span[aria-hidden="true"], h3, h4, strong, span')?.textContent?.trim() || a.textContent?.trim();
    const inferred = ts.inferNameFromLinkedInSlug(href);
    const finalName = ts.normalizeName(nameText) || inferred;
    if (!finalName || ['see all', 'view profile', 'follow', 'message', 'connect', 'linkedin member', 'sign in', 'join now'].includes(finalName.toLowerCase())) return;

    const sub = container.querySelector('.artdeco-entity-lockup__subtitle, .entity-result__primary-subtitle, p, [class*="headline"], [class*="occupation"], [class*="subtitle"], .t-12')?.textContent?.trim();
    let company = null;
    let title = sub || 'Professional';
    if (title.includes(' at ')) {
      const p = title.split(' at ');
      company = p[1].split(/[,|•\n]/)[0].trim();
    } else if (title.includes(' @ ')) {
      const p = title.split(' @ ');
      company = p[1].split(/[,|•\n]/)[0].trim();
    }

    results.push({
      recruiter_name: finalName,
      title: title.slice(0, 100),
      company_name: company,
      linkedin_url: href,
      source: 'linkedin_sidebar',
    });
  });

  return results;
}
