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

  // 1. Check Schema.org JSON-LD & Voyager Dash Embedded Data for official organization definition
  const jsonLdOrg = ts.extractJsonLd ? ts.extractJsonLd().organization : null;
  const embeddedData = ts.extractEmbeddedLinkedInData ? ts.extractEmbeddedLinkedInData() : {};
  const embeddedComp = embeddedData.company || null;
  const firmographics = ts.extractCompanyFirmographics ? ts.extractCompanyFirmographics() : {};

  // Company Name Extraction
  let rawCompName = pageCompanyContext || embeddedComp?.name || (jsonLdOrg?.company_name) || ts.text([
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
  let tagline = embeddedComp?.tagline || ts.text([
    'p.org-top-card-summary__tagline',
    '.org-top-card-summary__tagline',
    'div[data-view-name="org-top-card"] p',
    '.org-top-card__primary-content p',
    '.org-top-card-summary p'
  ]);

  let industry = embeddedComp?.industry || firmographics.industry || null;
  let locationStr = embeddedComp?.location || firmographics.location || firmographics.headquarters || jsonLdOrg?.address || null;
  let followers = firmographics.followers || null;
  let employees = embeddedComp?.employees || firmographics.employees || jsonLdOrg?.numberOfEmployees || null;

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

  const website = embeddedComp?.website || firmographics.website || jsonLdOrg?.url || ts.text([
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
    specialties: embeddedComp?.specialties || firmographics.specialties || null,
    founded: embeddedComp?.founded || firmographics.founded || null,
    company_type: firmographics.company_type || null,
    open_roles: firmographics.open_roles || null,
    overview: embeddedComp?.overview || tagline || firmographics.overview || jsonLdOrg?.description || null,
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

/**
 * Strict Location Validation & Cleaning Engine
 * Rejects job titles, industry names, company suffixes, credentials, pronouns, and metrics.
 * Requires genuine geographic indicators or standard city, state/country formatting.
 */
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

  // Reject job roles, disciplines, industries, and company suffix words (PREVENTS "Power Engineering" BUG)
  if (/\b(?:engineer|engineering|developer|recruiter|recruiting|talent|manager|consultant|analyst|specialist|officer|director|lead|head|vp|president|designer|scientist|marketing|sales|architect|intern|assistant|advisor|technician|contract|full-time|part-time|hybrid|corp|corporation|inc|llc|ltd|gmbh|technologies|solutions|services|group|holdings)\b/i.test(lower)) {
    return false;
  }

  // Must have genuine geographic indicator:
  const hasGeoWord = /\b(?:area|greater|city|county|region|metro|metropolitan|district|remote|united states|united kingdom|usa|uk|canada|india|australia|germany|france|netherlands|singapore|brazil|spain|italy|ireland|switzerland|sweden|japan|uae|dubai|mexico|poland|philippines|alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|england|scotland|wales|london|boston|chicago|seattle|austin|san francisco|sf bay|los angeles|atlanta|dallas|houston|denver|phoenix|philadelphia|san diego|miami|portland|toronto|vancouver|berlin|paris|amsterdam|tokyo|sydney|melbourne|bangalore|bengaluru|mumbai|hyderabad|pune|chennai|delhi|noida|gurgaon)\b/i.test(lower);
  if (hasGeoWord) return true;

  // Standard "City, State/Country" with 2-letter state code or standard comma separation
  if (/^[A-Z][a-zA-Z\s.-]+,\s*[A-Z]{2}$/.test(t)) return true;
  if (/^[A-Z][a-zA-Z\s.-]+,\s*[A-Z][a-zA-Z\s.-]+,\s*[A-Z][a-zA-Z\s.-]+$/.test(t)) return true;

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

/**
 * SELECTOR-RESILIENT Top Card InnerText Parser
 * 
 * LinkedIn always renders the profile top card in this stable visual order:
 *   [Name]
 *   [Headline/Title]
 *   [Company icon] Company Name
 *   [Education icon] School Name
 *   [Location] · Contact info
 *   [Connections] · [Followers]
 *
 * This parser reads the section's innerText (which respects visual line breaks)
 * and extracts fields by positional logic — no CSS class names needed.
 */
function parseTopCardInnerText() {
  const result = {
    name: null,
    headline: null,
    company: null,
    education: null,
    location: null,
    connections: null,
    followers: null,
    degree: null,
  };

  try {
    // Find the top card section: it's the container with h1
    const h1 = document.querySelector('h1');
    if (!h1) return result;

    // The top card is ALWAYS the major <section> containing the h1, or the .pv-top-card container
    let topCard = h1.closest('.pv-top-card') ||
                  h1.closest('div[data-view-name="profile-top-card"]') ||
                  h1.closest('section') ||
                  h1.closest('main') ||
                  h1.parentElement?.parentElement?.parentElement?.parentElement ||
                  document.body;

    // Safety guard: if topCard is too small (< 80 chars), walk up to <section> or <main>
    if (topCard && topCard.innerText && topCard.innerText.length < 80) {
      const parentSec = topCard.closest('section') || topCard.closest('main');
      if (parentSec) topCard = parentSec;
    }
    if (!topCard) return result;

    // The h1 text is the person's name
    const h1Text = (h1.innerText?.trim() || h1.textContent?.trim() || '').split('\n')[0].trim();
    result.name = h1Text;

    // ── Vector 1: Image Alt Attributes (Extreme Precision for Company & School Logos) ──
    try {
      const topImgs = (topCard || document).querySelectorAll('img[alt]');
      for (const img of topImgs) {
        const alt = (img.getAttribute('alt') || '').trim();
        if (!alt) continue;
        if (h1Text && alt.toLowerCase().includes(h1Text.toLowerCase())) continue;
        if (/^(profile|photo|picture|avatar|banner|background|badge|status|view|open|close|verified)/i.test(alt)) continue;

        const cleanAlt = alt.replace(/\s*(?:company\s*)?logo$/i, '').trim();
        if (cleanAlt.length >= 2 && cleanAlt.length <= 80 && !/linkedin/i.test(cleanAlt)) {
          if (/\b(university|college|institute|school|academy|polytechnic|penn state)\b/i.test(cleanAlt)) {
            if (!result.education) result.education = cleanAlt;
          } else {
            if (!result.company && !/^(about|experience|education|skills|interests|activity|projects)/i.test(cleanAlt)) {
              result.company = cleanAlt;
            }
          }
        }
      }
    } catch (_) {}

    // ── Vector 2: Top Card Links & Buttons (Company & School) ──
    try {
      // School link or button direct scanner
      if (!result.education) {
        const schoolLink = (topCard || document).querySelector('a[href*="/school/"]');
        if (schoolLink) {
          const t = schoolLink.textContent?.trim();
          if (t && t.length >= 3 && !/linkedin|follow|see all|learn more/i.test(t)) {
            result.education = t.replace(/\s+/g, ' ');
          }
        }
      }

      // Anchors
      const compLinks = (topCard || document).querySelectorAll('a[href*="/company/"]');
      for (const a of compLinks) {
        if (a.closest('#experience, section[data-section="experience"], #about')) continue;
        const t = a.textContent?.trim();
        if (t && t.length >= 2 && t.length <= 80 && !/linkedin|follow|see all|learn more/i.test(t)) {
          if (!result.company) {
            result.company = t.replace(/\s+/g, ' ');
            break;
          }
        }
      }

      const schoolLinks = (topCard || document).querySelectorAll('a[href*="/school/"]');
      for (const a of schoolLinks) {
        if (a.closest('#education, section[data-section="education"]')) continue;
        const t = a.textContent?.trim();
        if (t && t.length >= 2 && t.length <= 100 && !/linkedin|follow|see all|learn more/i.test(t)) {
          if (!result.education) {
            result.education = t.replace(/\s+/g, ' ');
            break;
          }
        }
      }

      // Buttons with aria-label
      const buttons = (topCard || document).querySelectorAll('button[aria-label]');
      for (const btn of buttons) {
        const aria = btn.getAttribute('aria-label') || '';
        if (/current company|company:/i.test(aria)) {
          const m = aria.match(/(?:current\s*company:?|company:?)\s*([^.\n\r]+)/i);
          if (m && m[1] && !result.company) result.company = m[1].trim();
        }
        if (/education:|school:/i.test(aria)) {
          const m = aria.match(/(?:education:?|school:?)\s*([^.\n\r]+)/i);
          if (m && m[1] && !result.education) result.education = m[1].trim();
        }
      }
    } catch (_) {}

    // ── Vector 3: Positional InnerText Parsing (Layout Immune) ──
    const rawText = topCard.innerText || '';
    if (rawText && rawText.length >= 10) {
      const lines = rawText.split(/\n/).map(l => l.trim()).filter(l => l.length > 0);

      // Find the name line index
      let nameIdx = -1;
      for (let i = 0; i < lines.length; i++) {
        if (lines[i] === h1Text || lines[i].includes(h1Text)) {
          nameIdx = i;
          break;
        }
      }
      if (nameIdx === -1) nameIdx = 0;

      // UI noise filter
      const isNoise = (t) => {
        const lower = t.toLowerCase();
        return /^(message|connect|follow|following|pending|more|save|report|block|send|endorse|open to|\.\.\.|see more|show|mutual|kevin is|get introduced|ask your|message top|we're hiring|visit|view|similar)/.test(lower) ||
          /^(home|my network|jobs|messaging|notifications|post|write|start a post)$/i.test(lower) ||
          /^\d+$/.test(t) ||
          t.length < 2 ||
          t.length > 200 ||
          /^(he\/him|she\/her|they\/them)$/i.test(lower);
      };

      const degreePattern = /\b(\d+(?:st|nd|rd|th)(?:\+)?)(?!\w)/i;

      // Check degree marker on the name line or nearby lines
      const nameLineFull = lines[nameIdx] || '';
      const degMatch = nameLineFull.match(degreePattern);
      if (degMatch) {
        result.degree = degMatch[1];
      }

      // Headline: first substantial non-noise line after the name
      for (let i = nameIdx + 1; i < Math.min(nameIdx + 5, lines.length); i++) {
        const line = lines[i];
        if (isNoise(line)) continue;
        if (degreePattern.test(line) && line.length < 8) {
          if (!result.degree) result.degree = line.match(degreePattern)[1];
          continue;
        }
        if (/^(he\/him|she\/her|they\/them|she\/they|he\/they)$/i.test(line)) continue;

        result.headline = line;
        break;
      }

      // Contact info anchor line
      let contactInfoLineIdx = -1;
      for (let i = 0; i < lines.length; i++) {
        if (/contact\s*info/i.test(lines[i])) {
          contactInfoLineIdx = i;
          break;
        }
      }

      // Location extraction from contact info line
      if (contactInfoLineIdx >= 0) {
        const contactLine = lines[contactInfoLineIdx];
        const locPart = cleanLocationText(contactLine);
        if (locPart && isValidLocation(locPart)) {
          result.location = locPart;
        }

        if (!result.location && contactInfoLineIdx > 0) {
          const prevLine = cleanLocationText(lines[contactInfoLineIdx - 1]);
          if (prevLine && isValidLocation(prevLine)) {
            result.location = prevLine;
          }
        }
      }

      // Direct DOM contact info element proximity scan (immune to innerText line splitting)
      if (!result.location) {
        try {
          const contactEls = Array.from((topCard || document).querySelectorAll('a, button, span')).filter(el => {
            const t = el.textContent?.trim() || '';
            return /^contact\s*info$/i.test(t);
          });
          for (const cEl of contactEls) {
            const pText = cEl.parentElement?.textContent?.trim() || '';
            const cPart = cleanLocationText(pText);
            if (cPart && isValidLocation(cPart)) {
              result.location = cPart;
              break;
            }
            const prev = cEl.previousElementSibling;
            if (prev && prev.textContent) {
              const prevText = cleanLocationText(prev.textContent);
              if (prevText && isValidLocation(prevText)) {
                result.location = prevText;
                break;
              }
            }
          }
        } catch (_) {}
      }

      // Fallback location scan: strictly validated lines only
      if (!result.location) {
        for (let i = nameIdx + 1; i < Math.min(nameIdx + 8, lines.length); i++) {
          const line = cleanLocationText(lines[i]);
          if (!line || line === result.headline || line === result.company || isNoise(line)) continue;
          if (isValidLocation(line)) {
            result.location = line;
            break;
          }
        }
      }

      // Education fallback from lines
      if (!result.education) {
        for (let i = nameIdx + 1; i < lines.length; i++) {
          const line = lines[i];
          if (/\b(university|college|institute|school|academy|polytechnic|harvard|stanford|mit|oxford|cambridge|bachelor|master|mba|ph\.?d|b\.?s\b|b\.?a\b|m\.?s\b)\b/i.test(line)) {
            if (line.length >= 3 && line.length <= 120 && !isNoise(line)) {
              result.education = line;
              break;
            }
          }
        }
      }

      // Company fallback from lines between headline and contact info
      if (!result.company) {
        const endScanIdx = contactInfoLineIdx > 0 ? contactInfoLineIdx : Math.min(lines.length, nameIdx + 6);
        for (let i = nameIdx + 1; i < endScanIdx; i++) {
          const line = lines[i];
          if (line === result.headline || line === result.education || line === result.degree || line === result.location) continue;
          if (isNoise(line) || degreePattern.test(line)) continue;
          if (/\b(university|college|institute|school|academy)\b/i.test(line)) continue;
          if (/,/.test(line) && /\b(area|greater|city|state|usa|uk|county)\b/i.test(line)) continue;
          if (line.length >= 2 && line.length <= 60) {
            result.company = line;
            break;
          }
        }
      }

      // Company fallback from headline (e.g. "Director of Sales at Acme Corp")
      if (!result.company && result.headline) {
        const atMatch = result.headline.match(/(?:\bat\b|\b@\b)\s+(.+)$/i);
        if (atMatch && atMatch[1]) {
          const comp = atMatch[1].replace(/[·•|].*$/, '').trim();
          if (comp.length >= 2 && comp.length <= 60) {
            result.company = comp;
          }
        }
      }

      // Social counts
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (/\b(\d[\d,]*\+?)\s*connections?\b/i.test(line)) {
          const m = line.match(/(\d[\d,]*\+?)\s*connections?/i);
          if (m) result.connections = m[1];
        }
        if (/\b(\d[\d,]*[kKmM]?\+?)\s*followers?\b/i.test(line)) {
          const m = line.match(/(\d[\d,]*[kKmM]?\+?)\s*followers?/i);
          if (m) result.followers = m[1];
        }
      }

      // Degree fallback
      if (!result.degree) {
        for (let i = 0; i < lines.length; i++) {
          const dm = lines[i].match(/\b(\d+(?:st|nd|rd|th)(?:\+)?)(?!\w)/i);
          if (dm && lines[i].length < 30) {
            result.degree = dm[1];
            break;
          }
        }
      }
    }

  } catch (_) {}

  return result;
}

function _scrapeSingleProfile(pageCompanyContext) {
  const ts = window.TalentScout;
  const cleanUrl = location.href.split('?')[0].split('#')[0];

  // 0. Harvest Schema.org JSON-LD & Voyager Dash Embedded Data structured models
  const jsonLdPerson = ts.extractJsonLd ? ts.extractJsonLd().person : null;
  const embeddedData = ts.extractEmbeddedLinkedInData ? ts.extractEmbeddedLinkedInData() : {};
  const embeddedCand = embeddedData.candidate || null;
  const badges = ts.extractBadgesAndSignals ? ts.extractBadgesAndSignals() : {};

  // 0b. PRIMARY: Selector-Resilient Top Card InnerText Parser (immune to CSS class renames)
  const topCardData = parseTopCardInnerText();

  // 1. Name — topCardData PRIMARY, then CSS selectors, then embedded/JSON-LD
  let name = topCardData.name || ts.text([
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
  ]) || embeddedCand?.name || jsonLdPerson?.name;

  // 2. Title / Headline — topCardData PRIMARY, then CSS selectors, then embedded/JSON-LD
  let rawTitle = topCardData.headline || ts.text([
    '.text-body-medium.break-words',
    '.pv-text-details__left-panel .text-body-medium',
    'div[data-generated-suggestion-target]',
    '.text-body-medium',
    '.top-card-layout__headline',
    '.pv-text-details__left-panel .text-body-medium',
    '[data-field="headline"]',
    '.artdeco-entity-lockup__subtitle',
    '.ph5 .text-body-medium',
  ]) || embeddedCand?.headline || jsonLdPerson?.jobTitle;

  // Harvest subtle small-text metadata (location, education, connections, followers, pronouns, talks about)
  const smallMeta = ts.extractSmallTextDetails ? ts.extractSmallTextDetails(document) : {};

  // 3. Location (City, State, Region, Country) — Semantic Multi-Strategy Precision Engine
  let candidateLocation = null;

  // Strategy 0 (PRIMARY): topCardData innerText parser — immune to CSS renames
  if (topCardData.location && isValidLocation(topCardData.location)) {
    candidateLocation = cleanLocationText(topCardData.location);
  }

  // Strategy A: Contact info proximity scan (Contact info parent / previous sibling)
  const contactInfoLink = document.querySelector('a[href*="contact-info"], #top-card-text-details-contact-info, a[id*="contact-info"], button[aria-label*="contact info" i]');
  if (contactInfoLink) {
    const parent = contactInfoLink.parentElement;
    if (parent && parent.cloneNode) {
      const clone = parent.cloneNode(true);
      if (clone.querySelectorAll) {
        clone.querySelectorAll('a, button, svg, span[class*="separator"], .dist-value').forEach(el => el.remove && el.remove());
      }
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

  // Strategy C: Small metadata / Embedded Data / JSON-LD fallback
  if (!candidateLocation && embeddedCand?.location && isValidLocation(embeddedCand.location)) {
    candidateLocation = cleanLocationText(embeddedCand.location);
  }
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

  // 4. Followers, Connections & Degree Context — topCardData PRIMARY
  let connectionDegree = topCardData.degree || ts.extractConnectionDegree(name) || ts.extractConnectionDegree(rawTitle) || smallMeta.degree || ts.text([
    '.pv-text-details__left-panel .dist-value',
    '.artdeco-hoverable-trigger .dist-value',
    'span.dist-value',
  ]);

  let followers = topCardData.followers || smallMeta.followers || ts.text([
    '.pv-top-card--list-bullet li:first-child span.t-bold',
    '.pv-top-card--list-bullet li:first-child',
    'span.t-black--light.t-normal span.t-bold',
    'ul.pv-top-card--list-bullet li:first-child',
    '.ph5 ul.pv-top-card--list-bullet li',
  ]);
  let connections = topCardData.connections || smallMeta.connections || ts.text([
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

  // 5. Education (School / University) — topCardData PRIMARY
  let education = topCardData.education || ts.text([
    'button[aria-label*="Education" i]',
    'button[aria-label*="Education:" i] span[aria-hidden="true"]',
    '.pv-text-details__right-panel button[aria-label*="Education" i]',
    '.pv-text-details__right-panel li button',
    '.pv-text-details__right-panel li a',
    '.pv-text-details__right-panel li',
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
    const rightPanelAnchors = document.querySelectorAll('.pv-text-details__right-panel a, .pv-text-details__right-panel li, div[data-view-name*="profile-top-card"] a[href*="/school/"], a[href*="/school/"]');
    for (const a of rightPanelAnchors) {
      const txt = a.textContent?.trim();
      if (txt && /university|college|institute|school|academy|polytechnic|penn state|alabama|tech|state|bs|ba|master|bachelor|wisconsin|harvard|stanford|mit|oxford|cambridge/i.test(txt) && !/linkedin|follow|see all/i.test(txt)) {
        education = txt.replace(/\s+/g, ' ').replace(/^Education:\s*/i, '').trim();
        break;
      }
    }
  }

  if (!education) {
    const eduImg = document.querySelector('img[alt*="university" i], img[alt*="college" i], img[alt*="school" i], img[alt*="penn state" i]');
    if (eduImg) {
      const alt = (eduImg.getAttribute('alt') || '').replace(/\s*(?:company\s*)?logo$/i, '').trim();
      if (alt.length >= 3 && !/linkedin/i.test(alt)) {
        education = alt;
      }
    }
  }

  if (!education) {
    const eduBtn = document.querySelector('button[aria-label*="Education" i], [aria-label*="Education" i]');
    if (eduBtn) {
      const aria = eduBtn.getAttribute('aria-label') || '';
      const m = aria.match(/Education:\s*([^.\n\r]+)/i);
      if (m && m[1]) education = m[1].trim();
    }
  }

  if (!education && embeddedData.educations && embeddedData.educations.length > 0) {
    const e0 = embeddedData.educations[0];
    education = `${e0.degree ? e0.degree + ' - ' : ''}${e0.school}${e0.field_of_study ? ' (' + e0.field_of_study + ')' : ''}`;
  }

  // 6. About / Summary Text & Semantic Decomposition (Prefers Un-truncated Embedded & Visually Hidden)
  let aboutSummary = embeddedCand?.summary || ts.text([
    '#about ~ div.display-flex .inline-show-more-text .visually-hidden',
    'section[data-section="about"] .inline-show-more-text .visually-hidden',
    '#about ~ div .inline-show-more-text .visually-hidden',
    '.pv-about-section .inline-show-more-text .visually-hidden',
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
      aboutSummary = ts.text(['.visually-hidden', 'span[aria-hidden="true"]', '.inline-show-more-text', 'p'], aboutAnchor.closest('section'));
    }
  }

  if (!aboutSummary) {
    const aboutHeaders = Array.from(document.querySelectorAll('h2, h3, div')).filter(el => {
      const txt = el.textContent?.trim() || '';
      return /^about$/i.test(txt);
    });
    for (const h of aboutHeaders) {
      const sec = h.closest('section') || h.parentElement?.parentElement;
      if (sec) {
        const textNodes = sec.querySelectorAll('.inline-show-more-text, p, span[aria-hidden="true"], .break-words');
        for (const tn of textNodes) {
          const txt = tn.textContent?.trim() || '';
          if (txt.length > 25 && !/^about$/i.test(txt) && !ts.isUIAction(txt)) {
            aboutSummary = txt;
            break;
          }
        }
      }
      if (aboutSummary) break;
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

  // Merge embedded Voyager Dash experience timeline if available
  if (embeddedData.experiences && embeddedData.experiences.length > 0) {
    embeddedData.experiences.forEach(e => {
      const exists = experienceHistory.some(h => (h.title || '').toLowerCase() === (e.title || '').toLowerCase() && (h.company || '').toLowerCase() === (e.company || '').toLowerCase());
      if (!exists) experienceHistory.push(e);
    });
    if (!currentCompany && experienceHistory.length > 0) {
      currentCompany = experienceHistory[0].company || null;
    }
  }

  // Top card explicit company — topCardData PRIMARY, then experience-derived, then CSS selectors
  let rawCompany = topCardData.company || currentCompany || ts.text([
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
    rawCompany = rawCompany
      .replace(/^Current\s*company:\s*/i, '')
      .replace(/^Education:\s*/i, '')
      .replace(/[·•|].*$/, '')
      .replace(/\. Click to skip.*$/i, '')
      .trim();
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

  // 8. Contact Info (Overlay & Deep Link Scanner & Embedded Voyager Data)
  let email = embeddedData.contactInfo?.email || ts.text(['.ci-email .pv-contact-info__contact-link', 'a[href^="mailto:"]']);
  if (email && email.startsWith('mailto:')) email = email.replace(/^mailto:/i, '').trim();
  let phone = embeddedData.contactInfo?.phone || ts.text(['.ci-phone .pv-contact-info__contact-link', '.ci-phone span']);
  if (phone && phone.startsWith('tel:')) phone = phone.replace(/^tel:/i, '').trim();
  let website = embeddedData.contactInfo?.website || ts.text(['.ci-websites a', '.pv-contact-info__contact-link[href*="http"]']);
  let connectedDate = ts.text(['.ci-connected .t-14']);

  // Digital Presence Links
  const github = ts.text(['a[href*="github.com"]']);
  const twitter = embeddedData.contactInfo?.twitter || ts.text(['a[href*="twitter.com"]', 'a[href*="x.com"]']);
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
  if (embeddedData.skills && embeddedData.skills.length > 0) {
    embeddedData.skills.forEach(s => {
      if (!skillsList.includes(s) && !ts.isUIAction(s)) skillsList.push(s);
    });
  }

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
  if (embeddedData.certifications && embeddedData.certifications.length > 0) {
    embeddedData.certifications.forEach(c => {
      if (!certsList.some(item => item.title === c.title)) certsList.push(c);
    });
  }

  const certItems = getSectionListItems('licenses_and_certifications');
  if (certItems.length === 0) {
    document.querySelectorAll('#licenses_and_certifications ~ div ul > li').forEach(e => certItems.push(e));
  }
  
  certItems.forEach(node => {
    const certTitle = ts.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], node);
    const certOrg = ts.text(['.t-normal span[aria-hidden="true"]', '.t-14.t-normal'], node);
    if (certTitle && !ts.isUIAction(certTitle)) {
      if (!certsList.some(item => item.title === certTitle)) {
        certsList.push({ title: certTitle, issuer: certOrg || null });
      }
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
