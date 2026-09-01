// ============================================================
// detector/generic.js — Universal High-Speed Deep DOM Engine
// Works on Any Website: ATS (Greenhouse, Lever, Workday, Taleo),
// Company Directories, Portals, Blogs, and Career Pages
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectGeneric = function() {
  const ts = window.TalentScout;
  const results = [];
  const host = location.hostname.toLowerCase();

  // Skip search engines and video platforms
  const skipHosts = [
    'google.', 'bing.com', 'duckduckgo.com', 'youtube.com', 'facebook.com',
    'twitter.com', 'x.com', 'instagram.com', 'reddit.com', 'wikipedia.org',
    'amazon.', 'netflix.com', 'github.com', 'gitlab.com', 'stackoverflow.com'
  ];
  if (skipHosts.some(s => host.includes(s))) return [];

  // ── Strategy 1: Scan all LinkedIn Profile Links on the Page ──
  const linkedinAnchors = document.querySelectorAll('a[href*="linkedin.com/in/"]');
  linkedinAnchors.forEach(a => {
    const href = a.href.split('?')[0].split('#')[0];
    const inferredName = ts.inferNameFromLinkedInSlug(href);
    const linkText = a.textContent?.trim();
    const finalName = ts.normalizeName(linkText) || inferredName;

    // Check parent container for title/company/email
    const container = a.closest('div, section, article, li, tr, td, p') || a.parentElement;
    const containerText = container ? (container.innerText || container.textContent || '') : '';
    const email = ts.extractEmail(containerText);
    const phone = ts.extractPhone(containerText);

    if (finalName) {
      results.push({
        recruiter_name: finalName,
        email: email || null,
        phone: phone || null,
        linkedin_url: href,
        company_name: _inferCompanyFromHost(host),
        source: `web_link:${host}`,
      });
    }
  });

  // ── Strategy 2: Scan all mailto: links on the Page ─────────
  const mailtoAnchors = document.querySelectorAll('a[href^="mailto:"]');
  mailtoAnchors.forEach(a => {
    const rawEmail = a.href.replace(/^mailto:/i, '').split('?')[0].trim();
    const email = ts.extractEmail(rawEmail);
    if (!email) return;

    // Try name from link text or email local part
    const linkText = a.textContent?.trim();
    const finalName = ts.normalizeName(linkText) || ts.inferNameFromEmail(email);

    const container = a.closest('div, section, article, li, tr, td') || a.parentElement;
    const containerText = container ? container.innerText || '' : '';
    const phone = ts.extractPhone(containerText);
    const linkedin = ts.extractLinkedIn(containerText);

    if (finalName || email) {
      results.push({
        recruiter_name: finalName || email.split('@')[0],
        email: email,
        phone: phone || null,
        linkedin_url: linkedin || null,
        company_name: _inferCompanyFromHost(host),
        source: `web_mailto:${host}`,
      });
    }
  });

  // ── Strategy 3: JSON-LD Structured Metadata ────────────────
  const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
  jsonLdScripts.forEach(s => {
    try {
      const data = JSON.parse(s.textContent || '{}');
      const items = Array.isArray(data) ? data : (data['@graph'] ? data['@graph'] : [data]);
      items.forEach(item => {
        if (item['@type'] === 'Person' || item['@type'] === 'ContactPoint') {
          const name = ts.normalizeName(item.name);
          const email = ts.extractEmail(item.email);
          const phone = ts.extractPhone(item.telephone);
          const title = item.jobTitle;
          const company = item.worksFor?.name || item.affiliation?.name || _inferCompanyFromHost(host);

          if (name || email) {
            results.push({
              recruiter_name: name || (email ? email.split('@')[0] : null),
              email: email || null,
              phone: phone || null,
              title: title || null,
              company_name: company || null,
              source: `jsonld:${host}`,
            });
          }
        }
      });
    } catch (_) {}
  });

  // ── Strategy 4: Profile / Team / Staff Container Cards ──────
  const cards = document.querySelectorAll([
    '[class*="team"]', '[class*="staff"]', '[class*="recruiter"]',
    '[class*="profile"]', '[class*="author"]', '[class*="contact"]',
    '[class*="bio"]', '.vcard', '[itemtype*="Person"]'
  ].join(','));

  cards.forEach(card => {
    const text = card.innerText || card.textContent || '';
    if (text.length < 15 || text.length > 2500) return;

    const email = ts.extractEmail(text);
    const phone = ts.extractPhone(text);
    const linkedin = ts.extractLinkedIn(card.innerHTML || text);

    if (!email && !linkedin && !phone) return;

    const name = _pickCardName(card);
    const title = _pickCardTitle(card);

    if (name || email) {
      results.push({
        recruiter_name: ts.normalizeName(name) || (email ? ts.inferNameFromEmail(email) : null),
        email: email || null,
        phone: phone || null,
        title: title || null,
        linkedin_url: linkedin || null,
        company_name: _inferCompanyFromHost(host),
        source: `card:${host}`,
      });
    }
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

// ── Private Helpers ──────────────────────────────────────────

function _inferCompanyFromHost(host) {
  if (!host) return null;
  const clean = host.replace(/^www\./, '').split('.')[0];
  return clean.length >= 2 ? clean.charAt(0).toUpperCase() + clean.slice(1) : null;
}

function _pickCardName(card) {
  const ts = window.TalentScout;
  const selectors = ['h1', 'h2', 'h3', 'h4', '[class*="name"]', 'strong', 'b'];
  for (const sel of selectors) {
    const el = card.querySelector(sel);
    const t = el?.textContent?.trim();
    if (t && t.length >= 2 && t.length <= 50 && !t.includes('@') && !/\d{3}/.test(t)) {
      return t;
    }
  }
  return null;
}

function _pickCardTitle(card) {
  const selectors = ['[class*="title"]', '[class*="role"]', '[class*="position"]', '[class*="job"]', 'p:first-of-type'];
  for (const sel of selectors) {
    const el = card.querySelector(sel);
    const t = el?.textContent?.trim();
    if (t && t.length >= 3 && t.length <= 80) return t;
  }
  return null;
}
