// ============================================================
// detector/linkedin.js — Bulletproof Context-Aware LinkedIn Scraper
// Extracts Multi-Person Grids, Page Context & Rejects UI Actions
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectLinkedIn = function() {
  const host = location.hostname.toLowerCase();
  const path = location.pathname;
  const ts = window.TalentScout;

  if (!host.includes('linkedin.com')) return [];

  const results = [];

  // ── Extract Page-Level Company Context ──────────────────────
  let pageCompanyContext = null;
  if (path.includes('/company/')) {
    // 1. Try DOM selectors for company name in header
    pageCompanyContext = ts.text([
      '.org-top-card-summary__title',
      'h1.org-top-card-summary__title',
      '.org-top-card__primary-content h1',
      '.ember-view h1',
      'h1',
    ]);
    
    // 2. Fallback to parsing page title or URL slug
    if (!pageCompanyContext || pageCompanyContext.toLowerCase() === 'linkedin') {
      const match = path.match(/\/company\/([^\/]+)/);
      if (match && match[1]) {
        pageCompanyContext = match[1].replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      }
    }
  }

  // ── 1. Company People & Grid Cards (/company/*/people) ──
  if (path.includes('/company/')) {
    if (path.includes('/people')) {
      results.push(..._scrapeCompanyPeoplePage(pageCompanyContext));
    }
    // Company home/posts/feed pages do NOT contain individual recruiter profile entities
    return results;
  }

  // ── 2. Single Profile Page (/in/ or /pub/) ─────────────────
  if (/^\/(in|pub)\//.test(path)) {
    const single = _scrapeSingleProfile(pageCompanyContext);
    if (single) results.push(single);
  }

  // ── 3. Search Results, Recruiter & Network Cards ───────────
  results.push(..._scrapeSearchCards(pageCompanyContext));
  results.push(..._scrapeRecruiterPlatform(pageCompanyContext));
  results.push(..._scrapeMessaging());
  results.push(..._scrapeAllLinkedInCards(pageCompanyContext));

  // ── 4. Page Title & Meta Fallback (Guaranteed Yield) ───────
  if (results.length === 0 && /^\/(in|pub)\//.test(path)) {
    const fallback = _scrapeFromTitleAndMeta(pageCompanyContext);
    if (fallback) results.push(fallback);
  }

  // Deduplicate locally
  const seen = new Set();
  return results.filter(r => {
    const key = (r.linkedin_url || r.email || `${r.recruiter_name}@${r.company_name}` || '').toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

// ── Private Extractors ───────────────────────────────────────

/**
 * Scrapes company people page cards and 'People you may know' grids
 */
function _scrapeCompanyPeoplePage(pageCompanyContext) {
  const ts = window.TalentScout;
  const results = [];

  // Find all person cards in company grids
  const cardSelectors = [
    '.org-people-profile-card',
    '.org-people-profile-card__profile-info',
    '.artdeco-card',
    '[data-view-name="profile-card"]',
    '.discover-person-card',
    '.grid li',
    'li.org-people-profiles-module__profile-item',
  ];

  const cards = document.querySelectorAll(cardSelectors.join(','));

  cards.forEach(card => {
    const anchor = card.querySelector('a[href*="/in/"]');
    const href = anchor ? anchor.href.split('?')[0].split('#')[0] : null;

    // Extract Name
    let rawName = ts.text([
      '.org-people-profile-card__profile-title',
      '.artdeco-entity-lockup__title',
      '.discover-person-card__name',
      'a[href*="/in/"] span[aria-hidden="true"]',
      'a[href*="/in/"]',
      'h3', 'h4',
    ], card);

    if (!rawName && anchor) {
      rawName = anchor.textContent?.trim();
    }

    const finalName = ts.normalizeName(rawName) || (href ? ts.inferNameFromLinkedInSlug(href) : null);
    if (!finalName) return;

    // Extract Title / Headline
    let rawHeadline = ts.text([
      '.org-people-profile-card__profile-position',
      '.artdeco-entity-lockup__subtitle',
      '.discover-person-card__occupation',
      '.lt-line-clamp--multi-line',
      'p',
      '.text-body-small',
    ], card);

    // If headline text is a UI action or button text, ignore it
    if (ts.isUIAction(rawHeadline)) {
      rawHeadline = null;
    }

    // Clean title and resolve company with page context
    const { title, company_name } = ts.cleanTitleAndCompany(rawHeadline, null, pageCompanyContext);

    // Calculate component-based confidences
    const conf = ts.calculateFieldConfidences({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
    });

    results.push({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
      source_platform: 'LinkedIn',
      linkedin_url: href,
      source: 'linkedin_company_people',
      confidence: conf.overall,
      field_confidences: conf,
    });
  });

  return results;
}

function _scrapeSingleProfile(pageCompanyContext) {
  const ts = window.TalentScout;
  const cleanUrl = location.href.split('?')[0].split('#')[0];

  // 1. Name — try multiple modern and legacy LinkedIn DOM selectors
  let name = ts.text([
    'h1.text-heading-xlarge',
    'h1.inline',
    '.top-card-layout__title',
    '[data-generated-suggestion-target]',
    '.pv-top-card--list li:first-child',
    '.artdeco-entity-lockup__title',
    '[data-field="name"]',
    '.ph5 h1',
    '.mt2 h1',
    'h1',
  ]);

  // 2. Title / Headline
  let rawTitle = ts.text([
    '.text-body-medium.break-words',
    '.text-body-medium',
    '.top-card-layout__headline',
    '.pv-text-details__left-panel .text-body-medium',
    '[data-field="headline"]',
    '.artdeco-entity-lockup__subtitle',
    '.ph5 .text-body-medium',
  ]);

  // 3. Location (City, State, Country)
  const candidateLocation = ts.text([
    '.text-body-small.inline.t-black--light.break-words',
    '.text-body-small.inline.t-black--light',
    '.top-card__subline-item',
    '.pv-text-details__left-panel .t-black--light',
    '[data-field="location"]',
    '.ph5 .text-body-small',
  ]);

  // 4. Followers & Connections (Small metadata)
  let followers = ts.text([
    '.pv-top-card--list-bullet li:first-child span.t-bold',
    '.pv-top-card--list-bullet li:first-child',
    'span.t-black--light.t-normal span.t-bold',
    'ul.pv-top-card--list-bullet li:first-child',
    '.ph5 ul.pv-top-card--list-bullet li',
  ]);
  let connections = ts.text([
    '.pv-top-card--list-bullet li:nth-child(2) span.t-bold',
    '.pv-top-card--list-bullet li:nth-child(2)',
    '.t-black--light.t-bold',
    'a[href*="/mynetwork/invite-connect/connections/"] span',
    'a[href*="/detail/recent-activity/"] + span',
  ]);

  // 5. Education (School / University)
  let education = ts.text([
    'a[href*="/school/"] span[aria-hidden="true"]',
    'a[href*="/school/"] span',
    'a[href*="/school/"]',
    '#education ~ div ul li .hoverable-link-text span[aria-hidden="true"]',
    '#education ~ div ul li h3 span[aria-hidden="true"]',
    '#education ~ div ul li h3',
    '.education__list-item h3',
    'section[data-section="education"] h3',
  ]);

  if (!education) {
    // Check right panel items for university keywords
    const rightPanelAnchors = document.querySelectorAll('.pv-text-details__right-panel a, .pv-text-details__right-panel li');
    rightPanelAnchors.forEach(a => {
      const txt = a.textContent?.trim();
      if (txt && /university|college|institute|school|academy|polytechnic|alabama|tech|state|bs|ba|master|bachelor/i.test(txt)) {
        education = txt.replace(/\s+/g, ' ');
      }
    });
  }

  // 6. About / Summary Text
  let aboutSummary = ts.text([
    '#about ~ div.display-flex span[aria-hidden="true"]',
    '#about ~ div .inline-show-more-text',
    '#about ~ div p',
    'section[data-section="about"] .inline-show-more-text',
    'section[data-section="about"] span[aria-hidden="true"]',
    '.pv-about-section .pv-about__summary-text',
    '.pv-about-section .inline-show-more-text',
  ]);

  // 7. Full Experience Timeline (Current vs Previous Employers)
  let currentCompany = null;
  let previousCompany = null;
  const experienceHistory = [];

  const expItems = document.querySelectorAll('#experience ~ div ul > li, .experience-section li, section[data-section="experience"] li');
  expItems.forEach(item => {
    const roleTitle = ts.text(['.t-bold span[aria-hidden="true"]', 'h3 span[aria-hidden="true"]', 'h3', '.experience-item__title'], item);
    const expCompany = ts.text(['.t-normal span[aria-hidden="true"]', '.t-14.t-normal span[aria-hidden="true"]', 'h4 span[aria-hidden="true"]', 'h4', '.experience-item__subtitle'], item);
    const dateRange = ts.text(['.t-black--light span[aria-hidden="true"]', '.date-range span[aria-hidden="true"]', '.date-range', '.pvs-entity__caption-wrapper'], item);

    if (roleTitle || expCompany) {
      const cleanComp = expCompany ? expCompany.split('·')[0].trim() : null;
      const isCurrent = dateRange ? /present|current/i.test(dateRange) : false;

      const entry = {
        title: roleTitle || 'Role',
        company: cleanComp || 'Company',
        dates: dateRange || (isCurrent ? 'Present' : 'Past'),
        is_current: isCurrent,
      };

      experienceHistory.push(entry);

      if (isCurrent && !currentCompany && cleanComp && !ts.isPlatformName(cleanComp)) {
        currentCompany = cleanComp;
      } else if (!isCurrent && !previousCompany && cleanComp && !ts.isPlatformName(cleanComp)) {
        previousCompany = cleanComp;
      }
    }
  });

  // Top card explicit company fallback
  let rawCompany = currentCompany || ts.text([
    '.pv-text-details__right-panel .inline-show-more-text',
    '.pv-text-details__right-panel a',
    '.top-card-layout__card .topcard__org-name-link',
    '.top-card-layout__first-subline a',
    'button[aria-label*="Current company"]',
  ]);

  const { title, company_name, specialty } = ts.cleanTitleAndCompany(rawTitle, rawCompany, pageCompanyContext);
  const finalName = ts.normalizeName(name) || ts.inferNameFromLinkedInSlug(cleanUrl);

  if (aboutSummary && (aboutSummary.length < 15 || aboutSummary.toLowerCase() === (company_name || '').toLowerCase())) {
    aboutSummary = null;
  }

  // 8. Contact Info (Direct DOM Overlay + Text Fallback)
  let email = ts.text([
    '.ci-email a',
    '.ci-email .pv-contact-info__contact-link',
    'a[href^="mailto:"]',
    '.pv-contact-info__ci-container a[href^="mailto:"]',
  ]);
  if (email && email.startsWith('mailto:')) email = email.replace(/^mailto:/i, '').trim();

  let phone = ts.text([
    '.ci-phone .pv-contact-info__contact-link',
    '.ci-phone span.t-14',
    '.ci-phone ul li span',
    'a[href^="tel:"]',
  ]);
  if (phone && phone.startsWith('tel:')) phone = phone.replace(/^tel:/i, '').trim();

  let website = ts.text([
    '.ci-websites a',
    '.ci-websites .pv-contact-info__contact-link',
    'a.pv-contact-info__contact-link[href^="http"]',
  ]);

  let connectedDate = ts.text([
    '.ci-connected .pv-contact-info__contact-item',
    '.ci-connected .t-14',
  ]);

  // Fallback body regex if not in overlay
  if (!email || !phone) {
    const fullText = document.body ? (document.body.innerText || '') : '';
    if (!email) email = ts.extractEmail(fullText);
    if (!phone) phone = ts.extractPhone(fullText);
  }

  // 9. Skills & Core Competencies
  const skillsList = [];
  const skillNodes = document.querySelectorAll('#skills ~ div ul > li, section[data-section="skills"] li, .pv-skill-categories-section li');
  skillNodes.forEach(node => {
    const skillName = ts.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], node);
    if (skillName && skillName.length >= 2 && skillName.length <= 40 && !ts.isUIAction(skillName)) {
      if (!skillsList.includes(skillName)) skillsList.push(skillName);
    }
  });

  // 10. Certifications & Licenses
  const certsList = [];
  const certNodes = document.querySelectorAll('#licenses_and_certifications ~ div ul > li, section[data-section="certifications"] li');
  certNodes.forEach(node => {
    const certTitle = ts.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], node);
    const certOrg = ts.text(['.t-normal span[aria-hidden="true"]', '.t-14.t-normal'], node);
    if (certTitle && !ts.isUIAction(certTitle)) {
      certsList.push({ title: certTitle, issuer: certOrg || null });
    }
  });

  if (!finalName && !title) return null;

  const conf = ts.calculateFieldConfidences({
    recruiter_name: finalName,
    title: title,
    company_name: company_name,
    email: email,
    phone: phone,
  });

  return {
    recruiter_name: finalName,
    title: title,
    headline: rawTitle,
    specialty: specialty,
    company_name: company_name,
    previous_company: previousCompany,
    source_platform: 'LinkedIn',
    location: candidateLocation,
    education: education,
    followers_count: followers,
    connections_count: connections,
    about_summary: aboutSummary,
    experience_history: experienceHistory.length > 0 ? experienceHistory : null,
    skills: skillsList.length > 0 ? skillsList : null,
    certifications: certsList.length > 0 ? certsList : null,
    website: website,
    connected_date: connectedDate,
    email: email,
    phone: phone,
    linkedin_url: cleanUrl,
    source: 'linkedin_profile',
    confidence: conf.overall,
    field_confidences: conf,
  };

  // Cache active profile locally for popup immediate rendering
  try {
    if (chrome?.storage?.local) {
      chrome.storage.local.set({ activeProfile: profileData });
    }
  } catch (_) {}

  return profileData;
}

function _scrapeFromTitleAndMeta(pageCompanyContext) {
  const ts = window.TalentScout;
  const rawDocTitle = document.title || '';
  if (!rawDocTitle) return null;

  const cleanUrl = location.href.split('?')[0].split('#')[0];
  const inferredName = ts.inferNameFromLinkedInSlug(cleanUrl);

  const parts = rawDocTitle.replace(/\s*\|\s*LinkedIn$/i, '').split(/\s*[-–—|]\s*/);
  const name = ts.normalizeName(parts[0]) || inferredName;
  const rawTitle = parts[1] || null;
  const rawCompany = parts[2] || null;

  if (!name) return null;

  const { title, company_name } = ts.cleanTitleAndCompany(rawTitle, rawCompany, pageCompanyContext);

  const conf = ts.calculateFieldConfidences({
    recruiter_name: name,
    title: title,
    company_name: company_name,
  });

  return {
    recruiter_name: name,
    title: title,
    company_name: company_name,
    source_platform: 'LinkedIn',
    linkedin_url: cleanUrl,
    source: 'linkedin_meta',
    confidence: conf.overall,
    field_confidences: conf,
  };
}

function _scrapeSearchCards(pageCompanyContext) {
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

    const rawTitle = ts.text([
      '.entity-result__primary-subtitle',
      '.discover-person-card__occupation',
      '.artdeco-entity-lockup__subtitle',
      '.subline-level-1',
    ], card);

    const rawCompany = ts.text([
      '.entity-result__secondary-subtitle',
      '.subline-level-2',
      '.entity-result__summary',
    ], card);

    const candidateLocation = ts.text([
      '.entity-result__tertiary-subtitle',
      '.subline-level-3',
    ], card);

    const finalName = ts.normalizeName(name) || ts.inferNameFromLinkedInSlug(href);
    if (!finalName) return;

    const { title, company_name } = ts.cleanTitleAndCompany(rawTitle, rawCompany, pageCompanyContext);

    const conf = ts.calculateFieldConfidences({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
    });

    results.push({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
      source_platform: 'LinkedIn',
      location: candidateLocation || null,
      linkedin_url: href,
      source: 'linkedin_search',
      confidence: conf.overall,
      field_confidences: conf,
    });
  });

  return results;
}

function _scrapeRecruiterPlatform(pageCompanyContext) {
  const ts = window.TalentScout;
  const results = [];
  const cards = document.querySelectorAll('.profile-card, .profile-list-item, [data-control-name="view_profile"], .talent-card');

  cards.forEach(card => {
    const anchor = card.querySelector('a[href*="/in/"], a[href*="/talent/profile/"]');
    const name = ts.text(['.profile-card__name', '.result-lockup__name', 'h3', 'h4'], card);
    const rawTitle = ts.text(['.profile-card__headline', '.result-lockup__headline', '.t-12'], card);
    const rawCompany = ts.text(['.profile-card__company', '.result-lockup__company'], card);
    const candidateLocation = ts.text(['.profile-card__location', '.result-lockup__location'], card);

    const finalName = ts.normalizeName(name) || (anchor ? ts.inferNameFromLinkedInSlug(anchor.href) : null);
    if (!finalName) return;

    const { title, company_name } = ts.cleanTitleAndCompany(rawTitle, rawCompany, pageCompanyContext);

    results.push({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
      source_platform: 'LinkedIn',
      location: candidateLocation || null,
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
      source_platform: 'LinkedIn',
      linkedin_url: anchor ? anchor.href.split('?')[0] : null,
      source: 'linkedin_messaging',
    });
  });

  return results;
}

function _scrapeFeedPosts(pageCompanyContext) {
  const ts = window.TalentScout;
  const results = [];
  const posts = document.querySelectorAll('.feed-shared-update-v2, .feed-shared-actor, [data-urn*="activity"]');

  posts.forEach(post => {
    const actorName = ts.text(['.update-components-actor__name', '.feed-shared-actor__name'], post);
    const rawTitle = ts.text(['.update-components-actor__description', '.feed-shared-actor__description'], post);
    const anchor = post.querySelector('.update-components-actor__container-link, a[href*="/in/"]');
    const finalName = ts.normalizeName(actorName);

    if (finalName) {
      const { title, company_name } = ts.cleanTitleAndCompany(rawTitle, null, pageCompanyContext);
      results.push({
        recruiter_name: finalName,
        title: title || 'Hiring Lead',
        company_name: company_name,
        source_platform: 'LinkedIn',
        linkedin_url: anchor ? anchor.href.split('?')[0] : null,
        email: ts.extractEmail(post.innerText || ''),
        phone: ts.extractPhone(post.innerText || ''),
        source: 'linkedin_feed',
      });
    }
  });

  return results;
}

function _scrapeAllLinkedInCards(pageCompanyContext) {
  const ts = window.TalentScout;
  const results = [];
  const cleanUrl = location.href.split('?')[0].split('#')[0];

  const allProfileAnchors = document.querySelectorAll('a[href*="/in/"]');
  allProfileAnchors.forEach(a => {
    const href = a.href.split('?')[0].split('#')[0];
    if (href === cleanUrl || !href.includes('/in/')) return;

    const container = a.closest('li, div.artdeco-entity-lockup, div.discover-person-card, section, div.feed-shared-following-card, .profile-card, aside div, [class*="card"], [class*="lockup"]') || a.parentElement;
    if (!container) return;

    const nameText = a.querySelector('.entity-result__title-text span[aria-hidden="true"], .artdeco-entity-lockup__title span[aria-hidden="true"], span[aria-hidden="true"], strong, h3, h4')?.textContent?.trim() || a.textContent?.trim();
    const inferred = ts.inferNameFromLinkedInSlug(href);
    let finalName = ts.normalizeName(nameText) || inferred;
    if (!finalName) return;

    // If normalized name was overly greedy but inferred slug name is clean, prefer inferred
    if (inferred && finalName.split(' ').length > 3 && inferred.split(' ').length <= 3) {
      finalName = inferred;
    }

    const rawSub = container.querySelector('.artdeco-entity-lockup__subtitle, .entity-result__primary-subtitle, [class*="headline"], [class*="occupation"], [class*="subtitle"], .t-12')?.textContent?.trim();
    const { title, company_name } = ts.cleanTitleAndCompany(rawSub, null, pageCompanyContext);

    // If title is identical to name or just the name repeated, nullify it
    const cleanTitle = (title && title.toLowerCase() === finalName.toLowerCase()) ? null : title;

    results.push({
      recruiter_name: finalName,
      title: cleanTitle,
      company_name: company_name,
      source_platform: 'LinkedIn',
      linkedin_url: href,
      source: 'linkedin_sidebar',
    });
  });

  return results;
}
