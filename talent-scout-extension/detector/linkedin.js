// ============================================================
// detector/linkedin.js — Ultra-Fast LinkedIn High-Yield Extractor
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectLinkedIn = function() {
  const host = location.hostname;
  const path = location.pathname;
  const ts = window.TalentScout;

  if (!host.includes('linkedin.com')) return [];

  const results = [];

  // ── 1. Single Profile Page (/in/ or /pub/) ─────────────────
  if (/^\/(in|pub)\//.test(path)) {
    const single = _scrapeSingleProfile();
    if (single) results.push(single);
  }

  // ── 2. Search Results & People Directory ───────────────────
  if (path.includes('/search/') || path.includes('/mynetwork/')) {
    results.push(..._scrapeSearchCards());
  }

  // ── 3. Recruiter Platform (recruiter.linkedin.com) ─────────
  if (host.includes('recruiter.linkedin.com') || path.includes('/talent/')) {
    results.push(..._scrapeRecruiterPlatform());
  }

  // ── 4. Messaging & InMail Threads ──────────────────────────
  if (path.includes('/messaging/')) {
    results.push(..._scrapeMessaging());
  }

  // ── 5. Feed Posts with Hiring Announcements ────────────────
  results.push(..._scrapeFeedPosts());

  // Deduplicate locally by LinkedIn URL / Name
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

  // Name
  const name = ts.text([
    'h1.text-heading-xlarge',
    'h1',
    '.top-card-layout__title',
    '[data-generated-suggestion-target]',
    '.pv-top-card--list li:first-child',
  ]);

  // Title / Headline
  const title = ts.text([
    '.text-body-medium.break-words',
    '.top-card-layout__headline',
    '.pv-text-details__left-panel .text-body-medium',
    '[data-field="headline"]',
  ]);

  // Location
  const location = ts.text([
    '.text-body-small.inline.t-black--light.break-words',
    '.top-card__subline-item',
    '.pv-text-details__left-panel .t-black--light',
    '[data-field="location"]',
  ]);

  // Company
  const company = ts.text([
    '.pv-text-details__right-panel .inline-show-more-text',
    '.pv-text-details__right-panel a',
    '.top-card-layout__card .topcard__org-name-link',
    '.top-card-layout__first-subline a',
    '#experience li:first-child .t-bold span[aria-hidden="true"]',
    '#experience li:first-child .hoverable-link-text span[aria-hidden="true"]',
    'button[aria-label*="Current company"]',
  ]);

  // Contact Info (if open or rendered)
  const contactModal = document.querySelector('.pv-contact-info, .pv-profile-section__section-info');
  const fullText = (contactModal ? contactModal.textContent : '') + ' ' + (document.body.innerText || '');
  const email = ts.extractEmail(fullText);
  const phone = ts.extractPhone(fullText);

  const cleanUrl = window.location.href.split('?')[0].split('#')[0];
  const finalName = ts.normalizeName(name) || ts.inferNameFromLinkedInSlug(cleanUrl);

  if (!finalName && !title) return null;

  return {
    recruiter_name: finalName,
    title: title || null,
    company_name: company || null,
    location: location || null,
    email: email || null,
    phone: phone || null,
    linkedin_url: cleanUrl,
    source: 'linkedin_profile',
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
      title: title || null,
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
    const postText = (post.innerText || '').toLowerCase();

    // Check if post author is a recruiter or hiring
    const isHiringPost = postText.includes('hiring') || postText.includes('looking for') || postText.includes('recruiting');
    const finalName = ts.normalizeName(actorName);

    if (finalName && (isHiringPost || ts.scoreRelevance({ title: actorTitle }) >= 40)) {
      results.push({
        recruiter_name: finalName,
        title: actorTitle || null,
        linkedin_url: anchor ? anchor.href.split('?')[0] : null,
        email: ts.extractEmail(post.innerText || ''),
        phone: ts.extractPhone(post.innerText || ''),
        source: 'linkedin_feed',
      });
    }
  });

  return results;
}
