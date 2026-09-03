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

  // ── 1. Company Profile & Grid Cards (/company/*) ──
  if (path.includes('/company/')) {
    const compEntity = _scrapeCompanyProfile(pageCompanyContext);
    if (compEntity) results.push(compEntity);

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
 * Scrapes company profile pages (/company/*) for organization intelligence
 */
function _scrapeCompanyProfile(pageCompanyContext) {
  const ts = window.TalentScout;
  const cleanUrl = location.href.split('?')[0].split('#')[0];

  // 1. Check Schema.org JSON-LD for official organization definition
  const jsonLdOrg = ts.extractJsonLd ? ts.extractJsonLd().organization : null;
  const firmographics = ts.extractCompanyFirmographics ? ts.extractCompanyFirmographics() : {};

  // Company Name Extraction
  let rawCompName = pageCompanyContext || (jsonLdOrg?.company_name) || ts.text([
    'h1.org-top-card-summary__title',
    'div[data-view-name="org-top-card"] h1',
    '.org-top-card-summary__title',
    '.org-top-card__primary-content h1',
    'h1.t-24',
    'h1',
  ]);

  let compName = rawCompName ? rawCompName.replace(/[\u00C2\u00A0]+/g, ' ').trim() : null;

  // Clean company name from verified badges or icons
  if (compName) {
    compName = compName.replace(/\b(?:verified|page|profile|company)\b/gi, '').replace(/\s+/g, ' ').trim();
  }

  // Reject generic placeholders
  if (!compName || compName.toLowerCase() === 'linkedin' || compName.toLowerCase() === 'company name') {
    const match = location.pathname.match(/\/company\/([^\/]+)/);
    if (match && match[1]) {
      compName = match[1].replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
  }

  if (!compName || compName.toLowerCase() === 'linkedin' || compName.toLowerCase() === 'company name') return null;

  // 2. Headline / Tagline
  let tagline = ts.text([
    'p.org-top-card-summary__tagline',
    '.org-top-card-summary__tagline',
    'div[data-view-name="org-top-card"] p',
    '.org-top-card__primary-content p',
    '.org-top-card-summary p'
  ]);

  let industry = firmographics.industry || null;
  let locationStr = firmographics.location || firmographics.headquarters || jsonLdOrg?.address || null;
  let followers = firmographics.followers || null;
  let employees = firmographics.employees || jsonLdOrg?.numberOfEmployees || null;

  // 3. Multi-Pass Modern LinkedIn Company Subline Scanner
  // e.g. "Staffing and Recruiting · Toledo, Ohio · 45K followers · 201-500 employees"
  const headerContainers = [
    document.querySelector('div[data-view-name="org-top-card"]'),
    document.querySelector('.org-top-card'),
    document.querySelector('.org-top-card__primary-content'),
    document.querySelector('.org-top-card-summary'),
    document.querySelector('main'),
    document.body
  ].filter(Boolean);

  for (const root of headerContainers) {
    const subElements = root.querySelectorAll(
      '.org-top-card-summary-info-list, .org-top-card-summary__info-list, ' +
      '.org-top-card-summary-info-list__info-item, .org-top-card-summary__info-item, ' +
      'div.inline-block.t-14, div.t-14.t-black--light, .t-black--light, p'
    );

    for (const el of subElements) {
      const fullText = el.textContent ? el.textContent.trim() : '';
      if (!fullText || fullText.length < 3) continue;

      // Check if element has dot-separated tokens
      const tokens = fullText
        .split(/[\n\r]+|[·•\u00B7\u2022\u2219|]/)
        .map(s => s.replace(/[\u00C2\u00A0]+/g, ' ').trim())
        .filter(s => s.length >= 2);

      for (const tok of tokens) {
        const lower = tok.toLowerCase();

        // Followers check
        if (!followers && /\b\d[\d,.]*[kKmMbB]?\+?\s*followers\b/i.test(tok)) {
          followers = tok;
          continue;
        }

        // Employees / Scale check
        if (!employees && (/\b(?:\d[\d,.]*(?:-\d[\d,.]*)?|\d[\d,.]*\+?)\s*employees\b/i.test(tok) || /\b\d[\d,.]*\s+on linkedin\b/i.test(tok))) {
          employees = tok;
          continue;
        }

        // Location check: e.g. "Toledo, Ohio", "San Francisco, CA", "Greater London"
        if (!locationStr && !lower.includes('follower') && !lower.includes('employee') && !lower.includes('connections follow') && !lower.includes('following')) {
          if (/,|\b(?:Area|City|Greater|County|United Kingdom|United States|USA|UK|Canada|India|Australia|Germany|France)\b/i.test(tok)) {
            locationStr = tok;
            continue;
          }
        }

        // Industry check: e.g. "Staffing and Recruiting", "Information Technology & Services", "Hospital & Health Care"
        if (!industry && !lower.includes('follower') && !lower.includes('employee') && !lower.includes('connections follow') && !lower.includes('following')) {
          if (!/,/.test(tok) && tok.length >= 3 && tok.length <= 60) {
            industry = tok;
          }
        }
      }

      if (followers && employees && locationStr) break;
    }

    if (followers && employees && locationStr) break;
  }

  // 4. Global RegEx Top Card Text Scanner Fallback
  const topText = (document.body ? (document.body.innerText || document.body.textContent) : '') || '';

  if (!followers) {
    const fMatch = topText.match(/\b(\d[\d,.]*[kKmMbB]?\+?\s*followers)\b/i);
    if (fMatch) followers = fMatch[1].trim();
  }

  if (!employees) {
    const eMatch = topText.match(/\b((?:\d[\d,.]*(?:-\d[\d,.]*)?|\d[\d,.]*\+?)\s*employees)\b/i) ||
                   topText.match(/\b(\d[\d,.]*\s+on linkedin)\b/i);
    if (eMatch) employees = eMatch[1].trim();
  }

  if (!locationStr) {
    const lines = topText.split(/[\r\n]+/).map(l => l.trim()).filter(Boolean);
    for (const line of lines) {
      if (/followers|employees/i.test(line) && /[·•\u00B7\u2022|]/.test(line)) {
        const parts = line.split(/[·•\u00B7\u2022|]/).map(p => p.trim());
        for (const p of parts) {
          if (/,/.test(p) && !/followers|employees|connections/i.test(p) && p.length >= 3 && p.length <= 60) {
            locationStr = p;
            break;
          }
        }
      }
      if (locationStr) break;
    }
  }

  const website = firmographics.website || jsonLdOrg?.url || ts.text([
    'a[data-control-name="topcard_website"]',
    'a.org-top-card-primary-actions__action',
    'a[href*="http"]:not([href*="linkedin.com"])',
  ]);

  const companyEntity = {
    entity_type: 'COMPANY',
    company_name: compName,
    recruiter_name: compName, // Preserved for backwards compatibility
    headline: tagline || null,
    title: industry || 'Staffing and Recruiting',
    industry: industry || 'Staffing and Recruiting',
    location: locationStr || null,
    followers_count: followers || null,
    employees_count: employees || null,
    website: website || null,
    specialties: firmographics.specialties || null,
    founded: firmographics.founded || null,
    company_type: firmographics.company_type || null,
    open_roles: firmographics.open_roles || null,
    overview: tagline || firmographics.overview || jsonLdOrg?.description || null,
    linkedin_url: cleanUrl,
    source_platform: 'LinkedIn',
    source: 'linkedin_company_page',
    confidence: 98,
    captured_at: new Date().toISOString(),
  };

  // Cache active company locally for popup immediate rendering
  try {
    if (chrome?.storage?.local) {
      chrome.storage.local.set({ activeCompany: companyEntity });
    }
  } catch (_) {}

  return companyEntity;
}

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
      entity_type: 'CANDIDATE',
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

  // 0. Harvest Schema.org JSON-LD structured data (ground truth baseline)
  const jsonLdPerson = ts.extractJsonLd ? ts.extractJsonLd().person : null;
  const badges = ts.extractBadgesAndSignals ? ts.extractBadgesAndSignals() : {};

  // 1. Name — try multiple modern and legacy LinkedIn DOM selectors + JSON-LD
  let name = ts.text([
    'h1.text-heading-xlarge',
    '.pv-text-details__left-panel h1',
    'section.pv-top-card h1',
    'div[data-view-name="profile-top-card"] h1',
    'h1.inline',
    '.top-card-layout__title',
    '[data-generated-suggestion-target]',
    '.pv-top-card--list li:first-child',
    '.artdeco-entity-lockup__title',
    '[data-field="name"]',
    '.ph5 h1',
    '.mt2 h1',
    'h1',
  ]) || jsonLdPerson?.name;

  // 2. Title / Headline
  let rawTitle = ts.text([
    '.text-body-medium.break-words',
    '.pv-text-details__left-panel .text-body-medium',
    'div[data-generated-suggestion-target]',
    '.text-body-medium',
    '.top-card-layout__headline',
    '.pv-text-details__left-panel .text-body-medium',
    '[data-field="headline"]',
    '.artdeco-entity-lockup__subtitle',
    '.ph5 .text-body-medium',
  ]) || jsonLdPerson?.jobTitle;

  // Harvest subtle small-text metadata (location, education, connections, followers, pronouns, talks about)
  const smallMeta = ts.extractSmallTextDetails ? ts.extractSmallTextDetails(document) : {};

  // 3. Location (City, State, Region, Country) — Semantic Multi-Strategy Precision Engine
  function isValidLocation(text) {
    if (!text || typeof text !== 'string') return false;
    const t = text.trim();
    if (t.length < 3 || t.length > 80) return false;
    const lower = t.toLowerCase();

    // Reject pronouns
    if (/^(?:he\/him|she\/her|they\/them|she\/they|he\/they)$/i.test(lower)) return false;
    // Reject metrics & connections
    if (/\b(?:followers?|connections?|mutual|following|network)\b/i.test(lower)) return false;
    // Reject degrees & credentials
    if (/^[·•\s]*\d*(?:st|nd|rd|th)?(?:\s*degree)?$/i.test(t)) return false;
    // Reject contact info text
    if (/^contact\s*info$/i.test(lower)) return false;
    // Reject UI actions
    if (/^(?:message|connect|follow|more|save|share|view|endorse|view profile|open to work|hiring|verified)$/i.test(lower)) return false;
    // Reject digits only, pure numbers, or date ranges
    if (/^\d+$/.test(t) || /\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b/i.test(lower)) return false;

    // Must have a geographic indicator:
    if (/,/.test(t)) return true;
    if (/\b(?:area|greater|city|county|region|metro|metropolitan|district|remote|united states|united kingdom|usa|uk|canada|india|australia|germany|france|netherlands|singapore|brazil|spain|italy|ireland|switzerland|sweden|japan|uae|dubai|mexico|poland|philippines)\b/i.test(lower)) {
      return true;
    }
    return false;
  }

  function cleanLocationText(text) {
    if (!text) return null;
    return text
      .replace(/\bcontact\s*info\b/gi, '')
      .replace(/[\u00C2\u00A0]*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+.*$/g, '')
      .replace(/^[\s\-_,·•\u00B7\u2022\u00C2\u00A0|]+|[\s\-_,·•\u00B7\u2022\u00C2\u00A0|]+$/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  let candidateLocation = null;

  // Strategy A: Contact info proximity scan (Contact info parent / previous sibling)
  const contactInfoLink = document.querySelector('a[href*="contact-info"], #top-card-text-details-contact-info, a[id*="contact-info"]');
  if (contactInfoLink) {
    const parent = contactInfoLink.parentElement;
    if (parent) {
      const clone = parent.cloneNode(true);
      clone.querySelectorAll('a, button, svg, span[class*="separator"], .dist-value').forEach(el => el.remove());
      const t = cleanLocationText(clone.textContent);
      if (isValidLocation(t)) candidateLocation = t;
    }
    if (!candidateLocation) {
      const prev = contactInfoLink.previousElementSibling;
      if (prev && prev.textContent) {
        const t = cleanLocationText(prev.textContent);
        if (isValidLocation(t)) candidateLocation = t;
      }
    }
  }

  // Strategy B: Left panel all spans semantic scan (Ignores buttons, anchors, pronouns)
  if (!candidateLocation) {
    const topSpans = document.querySelectorAll('.pv-text-details__left-panel span, div[data-view-name="profile-top-card"] span, .pv-top-card span, .top-card__subline-item');
    for (const sp of topSpans) {
      if (sp.closest('a, button, svg, ul')) continue;
      const t = cleanLocationText(sp.textContent);
      if (isValidLocation(t)) {
        candidateLocation = t;
        break;
      }
    }
  }

  // Strategy C: Small metadata / JSON-LD fallback
  if (!candidateLocation && smallMeta?.location && isValidLocation(smallMeta.location)) {
    candidateLocation = cleanLocationText(smallMeta.location);
  }
  if (!candidateLocation && jsonLdPerson?.address) {
    if (typeof jsonLdPerson.address === 'string' && isValidLocation(jsonLdPerson.address)) {
      candidateLocation = cleanLocationText(jsonLdPerson.address);
    } else if (typeof jsonLdPerson.address === 'object') {
      const parts = [jsonLdPerson.address.addressLocality, jsonLdPerson.address.addressRegion, jsonLdPerson.address.addressCountry].filter(Boolean);
      if (parts.length > 0) candidateLocation = parts.join(', ');
    }
  }

  // Strategy D: Broad regex extractor fallback
  if (!candidateLocation && ts.extractLocation) {
    const fullText = document.body ? (document.body.innerText || '') : '';
    const locFound = ts.extractLocation(fullText);
    if (locFound && isValidLocation(locFound)) {
      candidateLocation = cleanLocationText(locFound);
    }
  }

  // 4. Followers, Connections & Degree Context
  let connectionDegree = ts.extractConnectionDegree(name) || ts.extractConnectionDegree(rawTitle) || smallMeta.degree || ts.text([
    '.pv-text-details__left-panel .dist-value',
    '.artdeco-hoverable-trigger .dist-value',
    'span.dist-value',
  ]);

  let followers = smallMeta.followers || ts.text([
    '.pv-top-card--list-bullet li:first-child span.t-bold',
    '.pv-top-card--list-bullet li:first-child',
    'span.t-black--light.t-normal span.t-bold',
    'ul.pv-top-card--list-bullet li:first-child',
    '.ph5 ul.pv-top-card--list-bullet li',
  ]);
  let connections = smallMeta.connections || ts.text([
    '.pv-top-card--list-bullet li:nth-child(2) span.t-bold',
    '.pv-top-card--list-bullet li:nth-child(2)',
    '.t-black--light.t-bold',
    'a[href*="/mynetwork/invite-connect/connections/"] span',
    'a[href*="/detail/recent-activity/"] + span',
  ]);
  if (!connections) {
    connections = ts.extractConnectionCount(document.body ? document.body.innerText : '');
  }

  if (!badges.pronouns && smallMeta.pronouns) {
    badges.pronouns = smallMeta.pronouns;
  }

  // Helper for modern LinkedIn DOM (closest section traversal)
  function getSectionListItems(sectionId) {
    let anchor = null;
    try {
      anchor = document.querySelector('#' + sectionId) || document.querySelector(`[data-section="${sectionId}"]`);
    } catch (e) {
      anchor = document.querySelector(`[data-section="${sectionId}"]`);
    }
    if (!anchor) return [];
    
    const section = anchor.closest ? anchor.closest('section') : null;
    if (!section) return [];
    
    return Array.from(section.querySelectorAll('ul > li')).filter(li => {
      const parentUl = li.parentElement;
      return parentUl && parentUl.closest && !parentUl.closest('li'); 
    });
  }

  // 5. Education (School / University)
  let education = ts.text([
    'button[aria-label*="Education" i]',
    'button[aria-label*="Education:" i] span[aria-hidden="true"]',
    '.pv-text-details__right-panel button[aria-label*="Education" i]',
    '.pv-text-details__right-panel li:nth-child(2) button',
    '.pv-text-details__right-panel li:nth-child(2) a',
    'a[href*="/school/"] span[aria-hidden="true"]',
    'a[href*="/school/"] span',
    'a[href*="/school/"]',
    '.education__list-item h3'
  ]) || jsonLdPerson?.alumniOf;

  if (education) {
    education = education.replace(/^Education:\s*/i, '').trim();
  }

  if (!education) {
    const eduItems = getSectionListItems('education');
    if (eduItems.length > 0) {
      education = ts.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', 'h3', '.t-bold'], eduItems[0]);
    }
  }

  if (!education) {
    const rightPanelAnchors = document.querySelectorAll('.pv-text-details__right-panel a, .pv-text-details__right-panel li');
    rightPanelAnchors.forEach(a => {
      const txt = a.textContent?.trim();
      if (txt && /university|college|institute|school|academy|polytechnic|alabama|tech|state|bs|ba|master|bachelor|wisconsin|harvard|stanford|mit|oxford|cambridge/i.test(txt)) {
        education = txt.replace(/\s+/g, ' ').replace(/^Education:\s*/i, '').trim();
      }
    });
  }

  if (!education) {
    const eduBtn = document.querySelector('button[aria-label*="Education" i], [aria-label*="Education" i]');
    if (eduBtn) {
      const aria = eduBtn.getAttribute('aria-label') || '';
      const m = aria.match(/Education:\s*([^.\n\r]+)/i);
      if (m && m[1]) education = m[1].trim();
    }
  }

  // 6. About / Summary Text & Semantic Decomposition
  let aboutSummary = ts.text([
    '#about ~ div.display-flex span[aria-hidden="true"]',
    '#about ~ div .inline-show-more-text',
    '#about ~ div p',
    'section[data-section="about"] .inline-show-more-text',
    'section[data-section="about"] span[aria-hidden="true"]',
    '.pv-about-section .pv-about__summary-text',
    '.pv-about-section .inline-show-more-text',
  ]) || jsonLdPerson?.description;
  
  if (!aboutSummary) {
    const aboutAnchor = document.getElementById('about');
    if (aboutAnchor && aboutAnchor.closest('section')) {
      aboutSummary = ts.text(['span[aria-hidden="true"]', '.inline-show-more-text', 'p'], aboutAnchor.closest('section'));
    }
  }
  const aboutInsights = ts.decomposeAboutSection(aboutSummary);

  // 7. Full Experience Timeline (Deep Nested & Single Role Extractor)
  let currentCompany = jsonLdPerson?.worksFor || null;
  let previousCompany = null;
  let experienceHistory = ts.extractDetailedExperience ? ts.extractDetailedExperience(document) : [];

  if (experienceHistory.length === 0) {
    const expItems = getSectionListItems('experience');
    if (expItems.length === 0) {
      const oldExp = document.querySelectorAll('#experience ~ div ul > li, section[data-section="experience"] li, .pv-profile-section__list-item');
      oldExp.forEach(e => expItems.push(e));
    }

    expItems.forEach((item, idx) => {
      const roleTitle = ts.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], item);
      const expComp = ts.text(['.t-normal span[aria-hidden="true"]', '.t-14.t-normal', '.pv-entity__secondary-title'], item);
      const dateRange = ts.text(['.t-black--light span[aria-hidden="true"]', '.pv-entity__date-range', '.t-14.t-black--light'], item);
      
      if (roleTitle && !ts.isUIAction(roleTitle)) {
        const cleanExpComp = (expComp && !ts.isPlatformName(expComp)) ? expComp.split('·')[0].trim() : null;
        if (idx === 0) {
          currentCompany = cleanExpComp || currentCompany;
        } else if (!previousCompany && cleanExpComp && cleanExpComp !== currentCompany) {
          previousCompany = cleanExpComp;
        }
        experienceHistory.push({
          title: roleTitle,
          company: cleanExpComp,
          date_range: dateRange || null,
          is_current: idx === 0,
        });
      }
    });
  } else {
    // Derive current and previous company from detailed experience
    if (experienceHistory.length > 0 && !currentCompany) {
      currentCompany = experienceHistory[0].company || null;
    }
    if (experienceHistory.length > 1 && !previousCompany) {
      const pastRole = experienceHistory.find((r, i) => i > 0 && r.company && r.company !== currentCompany);
      previousCompany = pastRole ? pastRole.company : null;
    }
  }

  // Top card explicit company fallback (Modern LinkedIn right-panel, buttons, logo alt, links)
  let rawCompany = currentCompany || ts.text([
    'button[aria-label*="Current company" i]',
    'button[aria-label*="Current company:" i] span[aria-hidden="true"]',
    '.pv-text-details__right-panel button[aria-label*="Current company" i]',
    '.pv-text-details__right-panel li:first-child button',
    '.pv-text-details__right-panel li:first-child a',
    '.pv-text-details__right-panel button span[aria-hidden="true"]',
    '.pv-text-details__right-panel a span[aria-hidden="true"]',
    '.pv-text-details__right-panel button',
    '.pv-text-details__right-panel a',
    '.pv-text-details__right-panel li',
    'a[data-field="experience_company_logo"]',
    'div[data-view-name="profile-top-card"] a[href*="/company/"]',
    '.pv-text-details__right-panel .inline-show-more-text',
    '.top-card-layout__card .topcard__org-name-link',
    '.top-card-layout__first-subline a',
  ]);

  if (rawCompany) {
    rawCompany = rawCompany.replace(/^Current\s*company:\s*/i, '').replace(/^Education:\s*/i, '').trim();
  }

  if (!rawCompany) {
    const logoImg = document.querySelector('.pv-text-details__right-panel img[alt], a[href*="/company/"] img[alt], .pv-top-card img[alt*="logo" i]');
    if (logoImg && logoImg.alt) {
      rawCompany = logoImg.alt.replace(/\s*logo$/i, '').trim();
    }
  }

  if (!rawCompany) {
    const compLink = document.querySelector('.pv-text-details__right-panel a[href*="/company/"], .pv-top-card a[href*="/company/"]');
    if (compLink) {
      const t = compLink.textContent?.trim();
      if (t && !ts.isPlatformName(t)) rawCompany = t;
    }
  }

  if (!rawCompany) {
    const compBtn = document.querySelector('button[aria-label*="Current company" i], [aria-label*="Current company" i]');
    if (compBtn) {
      const aria = compBtn.getAttribute('aria-label') || '';
      const m = aria.match(/Current\s*company:\s*([^.\n\r]+)/i);
      if (m && m[1]) rawCompany = m[1].trim();
    }
  }

  let { title, company_name, specialty } = ts.cleanTitleAndCompany(rawTitle, rawCompany, pageCompanyContext);
  const finalName = ts.normalizeName(name) || ts.inferNameFromLinkedInSlug(cleanUrl);

  if (aboutSummary && (aboutSummary.length < 15 || aboutSummary.toLowerCase() === (company_name || '').toLowerCase())) {
    aboutSummary = null;
  }

  // 8. Contact Info (Overlay & Deep Link Scanner)
  let email = ts.text(['.ci-email .pv-contact-info__contact-link', 'a[href^="mailto:"]']);
  if (email && email.startsWith('mailto:')) email = email.replace(/^mailto:/i, '').trim();
  let phone = ts.text(['.ci-phone .pv-contact-info__contact-link', '.ci-phone span']);
  if (phone && phone.startsWith('tel:')) phone = phone.replace(/^tel:/i, '').trim();
  let website = ts.text(['.ci-websites a', '.pv-contact-info__contact-link[href*="http"]']);
  let connectedDate = ts.text(['.ci-connected .t-14']);

  // Digital Presence Links
  const github = ts.text(['a[href*="github.com"]']);
  const twitter = ts.text(['a[href*="twitter.com"]', 'a[href*="x.com"]']);
  const portfolio = ts.text(['a[href*="behance.net"]', 'a[href*="dribbble.com"]', 'a[href*="medium.com"]']);

  // Fallback body regex if not in overlay
  if (!email || !phone) {
    const fullText = document.body ? (document.body.innerText || '') : '';
    if (!email) email = ts.extractEmail(fullText);
    if (!phone) phone = ts.extractPhone(fullText);
  }

  // If company name is still missing but we have a corporate email domain, infer company
  if (!company_name && email && email.includes('@')) {
    const domain = email.split('@')[1].toLowerCase();
    if (!['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'live.com', 'aol.com', 'protonmail.com'].includes(domain)) {
      const compSlug = domain.split('.')[0];
      company_name = compSlug.charAt(0).toUpperCase() + compSlug.slice(1);
    }
  }

  // 9. Skills & Core Competencies (Up to 50 skills)
  const skillsList = [];
  const skillItems = getSectionListItems('skills');
  if (skillItems.length === 0) {
    document.querySelectorAll('#skills ~ div ul > li, .pv-skill-categories-section li').forEach(e => skillItems.push(e));
  }
  
  skillItems.forEach(node => {
    const skillName = ts.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], node);
    if (skillName && skillName.length >= 2 && skillName.length <= 50 && !ts.isUIAction(skillName)) {
      if (!skillsList.includes(skillName)) skillsList.push(skillName);
    }
  });

  // 9b. Extract "Top skills" container (prominent on modern LinkedIn profile cards)
  try {
    const allHeaders = Array.from(document.querySelectorAll('h2, h3, div, span, p')).filter(el => {
      const txt = el.textContent?.trim() || '';
      return /^top skills/i.test(txt) && txt.length < 35;
    });
    allHeaders.forEach(hdr => {
      const card = hdr.closest('div.display-flex, div.artdeco-card, section, div');
      if (card) {
        const cardText = card.textContent || '';
        const match = cardText.match(/top skills\s*[:\n]?\s*([^\n\r]+)/i);
        if (match && match[1]) {
          const tokens = match[1].split(/\s*[•·|]\s*/).map(s => s.trim()).filter(s => s.length >= 2 && s.length <= 60 && !ts.isUIAction(s));
          tokens.forEach(tok => {
            if (!skillsList.includes(tok)) skillsList.push(tok);
          });
        }
      }
    });
  } catch (_) {}

  // 10. Certifications & Licenses
  const certsList = [];
  const certItems = getSectionListItems('licenses_and_certifications');
  if (certItems.length === 0) {
    document.querySelectorAll('#licenses_and_certifications ~ div ul > li').forEach(e => certItems.push(e));
  }
  
  certItems.forEach(node => {
    const certTitle = ts.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], node);
    const certOrg = ts.text(['.t-normal span[aria-hidden="true"]', '.t-14.t-normal'], node);
    if (certTitle && !ts.isUIAction(certTitle)) {
      certsList.push({ title: certTitle, issuer: certOrg || null });
    }
  });

  // 11. Spoken Languages
  const spokenLanguages = ts.extractSpokenLanguages ? ts.extractSpokenLanguages(document) : [];

  // Incorporate "Talks about" topics into skills
  if (smallMeta.talks_about && smallMeta.talks_about.length > 0) {
    smallMeta.talks_about.forEach(topic => {
      if (!skillsList.includes(topic) && !ts.isUIAction(topic)) {
        skillsList.push(topic);
      }
    });
  }

  // Fallbacks for Location and Education from deep timeline or small metadata
  if (!candidateLocation && experienceHistory.length > 0 && experienceHistory[0].location) {
    candidateLocation = experienceHistory[0].location;
  }
  if (!education && smallMeta.education) {
    education = smallMeta.education;
  }

  if (!finalName && !title) return null;

  const conf = ts.calculateFieldConfidences({
    recruiter_name: finalName,
    title: title,
    company_name: company_name,
    email: email,
    phone: phone,
  });

  const leadEntity = {
    entity_type: 'CANDIDATE',
    recruiter_name: finalName,
    title: title,
    headline: rawTitle,
    specialty: specialty,
    company_name: company_name,
    previous_company: previousCompany,
    source_platform: 'LinkedIn',
    location: candidateLocation,
    education: education,
    connection_degree: connectionDegree,
    followers_count: followers,
    connections_count: connections,
    about_summary: aboutSummary,
    about_insights: aboutInsights,
    experience_history: experienceHistory.length > 0 ? experienceHistory : null,
    skills: skillsList.length > 0 ? skillsList : null,
    certifications: certsList.length > 0 ? certsList : null,
    languages: spokenLanguages.length > 0 ? spokenLanguages : null,
    is_open_to_work: badges.isOpenToWork || false,
    is_hiring: badges.isHiring || false,
    is_verified: badges.isVerified || false,
    pronouns: badges.pronouns || null,
    website: website,
    github: github || null,
    twitter: twitter || null,
    portfolio: portfolio || null,
    connected_date: connectedDate,
    email: email,
    phone: phone,
    linkedin_url: cleanUrl,
    source: 'linkedin_profile',
    confidence: conf.overall,
    field_confidences: conf,
    completeness_report: ts.generateCompletenessReport({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
      location: candidateLocation,
      education: education,
      connection_degree: connectionDegree,
      followers_count: followers,
      connections_count: connections,
      about_summary: aboutSummary,
      about_insights: aboutInsights,
      experience_history: experienceHistory,
      email: email,
      phone: phone,
      website: website,
      field_confidences: conf,
    }),
  };

  // Cache active candidate locally for popup immediate rendering
  try {
    if (chrome?.storage?.local) {
      chrome.storage.local.set({ 
        activeProfile: leadEntity,
        activeCandidate: leadEntity 
      });
    }
  } catch (_) {}

  return leadEntity;
}

function _scrapeFromTitleAndMeta(pageCompanyContext) {
  const ts = window.TalentScout;
  let rawDocTitle = document.title || '';

  const ogTitle = document.querySelector('meta[property="og:title"], meta[name="twitter:title"]')?.content || '';
  const ogDesc = document.querySelector('meta[property="og:description"], meta[name="description"]')?.content || '';
  if (ogTitle && !ogTitle.toLowerCase().includes('sign in') && !ogTitle.toLowerCase().includes('log in')) {
    rawDocTitle = ogTitle;
  }

  if (!rawDocTitle) return null;

  // Strip tab unread notification counts (e.g. "(14) ", "(2) ", "(99+) ")
  rawDocTitle = rawDocTitle.replace(/^\(\d+\+?\)\s*/, '').trim();

  const cleanUrl = location.href.split('?')[0].split('#')[0];
  const inferredName = ts.inferNameFromLinkedInSlug(cleanUrl);

  const parts = rawDocTitle.replace(/\s*\|\s*LinkedIn$/i, '').split(/\s*[-–—|]\s*/);
  const name = ts.normalizeName(parts[0]) || inferredName;
  let rawTitle = parts[1] || null;
  let rawCompany = parts[2] || null;

  let metaLocation = null;
  if (ogDesc) {
    const locM = ogDesc.match(/(?:Location:\s*|in\s+)([A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+)/);
    if (locM) metaLocation = locM[1].trim();
    if (!rawCompany) {
      const compM = ogDesc.match(/Experience:\s*([^·•\n\r]+)/i);
      if (compM) rawCompany = compM[1].trim();
    }
  }

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
    location: metaLocation,
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
    const personAnchor = card.querySelector('a[href*="/in/"]');
    const compAnchor = card.querySelector('a[href*="/company/"]');

    // 1. Company Search Card (Organization)
    if (!personAnchor && compAnchor) {
      const compHref = compAnchor.href.split('?')[0].split('#')[0];
      const rawCompName = ts.text([
        '.entity-result__title-text a span[aria-hidden="true"]',
        '.artdeco-entity-lockup__title',
        'span[aria-hidden="true"]',
        'h3', 'h4',
      ], card);
      const cleanCompName = (rawCompName && !ts.isPlatformName(rawCompName)) ? rawCompName.replace(/[•·\d+]+.*$/, '').trim() : null;
      if (cleanCompName && cleanCompName.length >= 2) {
        const rawIndustry = ts.text(['.entity-result__primary-subtitle', '.artdeco-entity-lockup__subtitle'], card);
        const rawLoc = ts.text(['.entity-result__secondary-subtitle'], card);
        results.push({
          entity_type: 'COMPANY',
          company_name: cleanCompName,
          recruiter_name: cleanCompName,
          title: rawIndustry || 'Business Consulting and Services',
          industry: rawIndustry || 'Business Consulting and Services',
          location: rawLoc || null,
          linkedin_url: compHref,
          source_platform: 'LinkedIn',
          source: 'linkedin_search_company',
          confidence: 96,
        });
      }
      return;
    }

    // 2. Candidate Search Card (Person)
    if (!personAnchor) return;

    const href = personAnchor.href.split('?')[0].split('#')[0];
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
      entity_type: 'CANDIDATE',
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
      entity_type: 'CANDIDATE',
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
