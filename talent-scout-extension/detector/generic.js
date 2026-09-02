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

  // Skip search engines and major social video feeds
  const skipHosts = [
    'google.', 'bing.com', 'duckduckgo.com', 'youtube.com', 'facebook.com',
    'twitter.com', 'x.com', 'instagram.com', 'reddit.com', 'wikipedia.org',
    'amazon.', 'netflix.com', 'github.com', 'gitlab.com', 'stackoverflow.com'
  ];
  if (skipHosts.some(s => host.includes(s))) return [];

  // Extract Page-Level Company Context
  const pageCompany = _inferCompanyFromHost(host);
  const pageFullText = document.body ? (document.body.innerText || document.body.textContent || '') : '';

  // ── Strategy 1: Scan all LinkedIn Profile Links on the Page ──
  const linkedinAnchors = document.querySelectorAll('a[href*="linkedin.com/in/"], a[href*="linkedin.com/pub/"]');
  linkedinAnchors.forEach(a => {
    const href = a.href.split('?')[0].split('#')[0];
    const inferredName = ts.inferNameFromLinkedInSlug(href);
    const linkText = a.textContent?.trim();
    const finalName = ts.normalizeName(linkText) || inferredName;

    if (!finalName || ts.isUIAction(finalName)) return;

    // Check parent container for title/email/phone
    const container = a.closest('div, section, article, li, tr, td, p') || a.parentElement;
    const containerText = container ? (container.innerText || container.textContent || '') : '';
    const email = ts.extractEmail(containerText);
    const phone = ts.extractPhone(containerText);
    const rawTitle = _pickTitleNearElement(a);

    const { title, company_name } = ts.cleanTitleAndCompany(rawTitle, null, pageCompany);
    const conf = ts.calculateFieldConfidences({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
    });

    results.push({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
      source_platform: host,
      email: email || null,
      phone: phone || null,
      linkedin_url: href,
      source: `web_link:${host}`,
      confidence: conf.overall,
      field_confidences: conf,
    });
  });

  // ── Strategy 2: Scan all mailto: links on the Page ─────────
  const mailtoAnchors = document.querySelectorAll('a[href^="mailto:"]');
  mailtoAnchors.forEach(a => {
    const rawEmail = a.href.replace(/^mailto:/i, '').split('?')[0].trim();
    const email = ts.extractEmail(rawEmail);
    if (!email) return;

    const linkText = a.textContent?.trim();
    const finalName = ts.normalizeName(linkText) || ts.inferNameFromEmail(email);
    if (!finalName || ts.isUIAction(finalName)) return;

    const container = a.closest('div, section, article, li, tr, td') || a.parentElement;
    const containerText = container ? container.innerText || '' : '';
    const phone = ts.extractPhone(containerText);
    const linkedin = ts.extractLinkedIn(containerText);
    const rawTitle = _pickTitleNearElement(a);

    const { title, company_name } = ts.cleanTitleAndCompany(rawTitle, null, pageCompany);
    const conf = ts.calculateFieldConfidences({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
    });

    results.push({
      recruiter_name: finalName,
      title: title,
      company_name: company_name,
      source_platform: host,
      email: email,
      phone: phone || null,
      linkedin_url: linkedin || null,
      source: `web_mailto:${host}`,
      confidence: conf.overall,
      field_confidences: conf,
    });
  });

  // ── Strategy 3: Full-Page Regex Stream for Corporate Emails ──
  const allEmails = pageFullText.match(ts.PATTERNS.email) || [];
  const uniqueEmails = [...new Set(allEmails)].slice(0, 10);

  uniqueEmails.forEach(rawEmail => {
    const email = rawEmail.toLowerCase().trim();
    const domain = email.split('@')[1] || '';
    if (ts.PATTERNS.freeEmailDomains.has(domain)) return;

    const inferredName = ts.inferNameFromEmail(email);
    if (!inferredName || ts.isUIAction(inferredName)) return;

    const { title, company_name } = ts.cleanTitleAndCompany(null, domain.split('.')[0], pageCompany);

    results.push({
      recruiter_name: inferredName,
      title: title || 'Professional Contact',
      company_name: company_name,
      source_platform: host,
      email: email,
      source: `web_stream:${host}`,
      confidence: 80,
    });
  });

  // ── Strategy 4: Team, Leadership & Office Intelligence (Knowledge Extraction) ──
  try {
    const teamMembers = document.querySelectorAll('.team-member, .person-card, .leader-card, .bio-card, .staff-card, .executive');
    teamMembers.forEach(card => {
      const name = ts.text(['h2', 'h3', 'h4', '.name', '.member-name', 'strong'], card);
      const title = ts.text(['.title', '.role', '.position', 'p', 'span.role'], card);
      const li = card.querySelector('a[href*="linkedin.com/in/"]')?.href;
      const em = ts.extractEmail(card.innerText || '');
      const ph = ts.extractPhone(card.innerText || '');

      const validName = ts.normalizeName(name);
      if (validName && !ts.isUIAction(validName)) {
        const { title: cleanT, company_name: cleanC } = ts.cleanTitleAndCompany(title, null, pageCompany);
        results.push({
          recruiter_name: validName,
          title: cleanT || 'Team Member',
          company_name: cleanC || pageCompany,
          source_platform: host,
          email: em || null,
          phone: ph || null,
          linkedin_url: li || null,
          source: `web_team:${host}`,
          confidence: 85,
        });
      }
    });
  } catch (_) {}

  // Deduplicate locally
  const seen = new Set();
  return results.filter(r => {
    const key = (r.linkedin_url || r.email || `${r.recruiter_name}@${r.company_name}` || '').toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

function _inferCompanyFromHost(host) {
  if (!host) return null;
  const clean = host.replace(/^www\./i, '').split('.')[0];
  if (['greenhouse', 'lever', 'workday', 'icims', 'smartrecruiters', 'jobvite'].includes(clean.toLowerCase())) {
    // ATS hosted career site e.g. boards.greenhouse.io/airbnb -> extract path
    const pathParts = location.pathname.split('/').filter(Boolean);
    if (pathParts.length > 0) return pathParts[0].replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
  return clean.replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function _pickTitleNearElement(el) {
  if (!el) return null;
  const container = el.closest('div, section, article, li, tr, td, p') || el.parentElement;
  if (!container) return null;

  const selectors = ['.title', '.position', '.role', '.headline', 'h3', 'h4', 'span.subtitle'];
  for (const sel of selectors) {
    const found = container.querySelector(sel);
    const text = found?.textContent?.trim();
    if (text && text.length >= 3 && text.length <= 80 && !window.TalentScout.isUIAction(text)) {
      return text;
    }
  }
  return null;
}
