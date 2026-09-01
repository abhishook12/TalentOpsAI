// ============================================================
// detector/generic.js — Universal heuristic catch-all
// Works on any site: company career pages, directories, portals
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectGeneric = function() {
  const ts = window.TalentScout;
  const results = [];

  // ── Skip irrelevant pages ─────────────────────────────────
  const skipHosts = ['google.com', 'facebook.com', 'twitter.com', 'youtube.com',
    'reddit.com', 'wikipedia.org', 'amazon.com', 'stackoverflow.com',
    'github.com', 'docs.google.com', 'maps.google.com', 'news.google.com'];
  if (skipHosts.some(h => location.hostname.includes(h))) return [];

  // ── Strategy 1: Scan <article>, <section>, .card, .profile type containers ──
  const containers = document.querySelectorAll([
    'article',
    '[class*="profile"]',
    '[class*="card"]',
    '[class*="team-member"]',
    '[class*="contact"]',
    '[class*="recruiter"]',
    '[class*="person"]',
    '[class*="staff"]',
    '.vcard',
    '[itemtype*="Person"]', // schema.org
  ].join(','));

  containers.forEach(el => {
    const text = el.innerText || el.textContent || '';
    if (text.length < 5 || text.length > 3000) return; // skip too small/large

    // Must contain at least one strong signal
    const hasEmail = ts.PATTERNS.email.test(text);
    const hasLinkedIn = ts.PATTERNS.linkedin.test(text);
    const hasPhone = ts.PATTERNS.phone.test(text);

    // Reset lastIndex (global regex stateful)
    ts.PATTERNS.email.lastIndex = 0;
    ts.PATTERNS.linkedin.lastIndex = 0;
    ts.PATTERNS.phone.lastIndex = 0;

    if (!hasEmail && !hasLinkedIn) return; // need at least email or LinkedIn

    const email = ts.extractEmail(text);
    const phone = ts.extractPhone(text);
    const linkedin = ts.extractLinkedIn(text);
    const name = _extractNameFromContainer(el);
    const title = _extractTitleFromContainer(el);
    const company = _extractCompanyFromContainer(el);

    if (!name && !email) return;

    const record = {
      recruiter_name: ts.normalizeName(name),
      email: email || null,
      phone: phone || null,
      title: title || null,
      company_name: company || null,
      linkedin_url: linkedin || null,
      source: `generic:${location.hostname}`,
    };

    if (ts.scoreRelevance(record) >= 40) {
      results.push(record);
    }
  });

  // ── Strategy 2: Full page scan for schema.org Person ──────
  const schemaPersons = document.querySelectorAll('[itemtype*="schema.org/Person"]');
  schemaPersons.forEach(el => {
    const name = el.querySelector('[itemprop="name"]')?.textContent?.trim();
    const title = el.querySelector('[itemprop="jobTitle"]')?.textContent?.trim();
    const company = el.querySelector('[itemprop="worksFor"]')?.textContent?.trim();
    const email = el.querySelector('[itemprop="email"]')?.textContent?.trim()
               || el.querySelector('[itemprop="email"]')?.getAttribute('href')?.replace('mailto:', '');
    const phone = el.querySelector('[itemprop="telephone"]')?.textContent?.trim();
    const linkedin = ts.extractLinkedIn(el.innerHTML || '');

    if (!name && !email) return;
    const record = {
      recruiter_name: ts.normalizeName(name),
      email: email || null,
      phone: phone || null,
      title: title || null,
      company_name: company || null,
      linkedin_url: linkedin || null,
      source: `schema_org:${location.hostname}`,
    };
    if (ts.scoreRelevance(record) >= 30) {
      results.push(record);
    }
  });

  // ── Strategy 3: vCard / hCard microformat ─────────────────
  const vcards = document.querySelectorAll('.vcard');
  vcards.forEach(el => {
    const name = el.querySelector('.fn, .name')?.textContent?.trim();
    const email = el.querySelector('.email')?.textContent?.trim()
               || el.querySelector('a.email')?.href?.replace('mailto:', '');
    const phone = el.querySelector('.tel')?.textContent?.trim();
    const title = el.querySelector('.title, .role')?.textContent?.trim();
    const company = el.querySelector('.org')?.textContent?.trim();
    if (!name && !email) return;
    results.push({
      recruiter_name: ts.normalizeName(name),
      email: email || null,
      phone: phone || null,
      title: title || null,
      company_name: company || null,
      source: `vcard:${location.hostname}`,
    });
  });

  // Deduplicate
  const seen = new Set();
  return results.filter(r => {
    const key = r.email || r.linkedin_url || `${r.recruiter_name}:${r.company_name}`;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

// ── Helper: extract name from container ─────────────────────

function _extractNameFromContainer(el) {
  const nameSelectors = [
    '[itemprop="name"]', '[class*="name"]', '[class*="title"]',
    'h1', 'h2', 'h3', 'h4', 'strong', 'b',
  ];
  for (const sel of nameSelectors) {
    const found = el.querySelector(sel);
    const t = found?.textContent?.trim();
    if (t && t.length > 2 && t.length < 60 && !t.includes('@') && !/\d{3}/.test(t)) {
      return t;
    }
  }
  return null;
}

function _extractTitleFromContainer(el) {
  const titleSelectors = [
    '[itemprop="jobTitle"]', '[class*="job"]', '[class*="role"]',
    '[class*="position"]', '[class*="title"]', 'p:first-of-type',
  ];
  for (const sel of titleSelectors) {
    const found = el.querySelector(sel);
    const t = found?.textContent?.trim();
    if (t && t.length > 2 && t.length < 100) return t;
  }
  return null;
}

function _extractCompanyFromContainer(el) {
  const companySelectors = [
    '[itemprop="worksFor"]', '[class*="company"]', '[class*="org"]',
    '[class*="employer"]', '[class*="organization"]',
  ];
  for (const sel of companySelectors) {
    const found = el.querySelector(sel);
    const t = found?.textContent?.trim();
    if (t && t.length > 1 && t.length < 80) return t;
  }
  // Fallback: infer from page domain
  return null;
}
