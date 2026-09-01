// ============================================================
// detector/patterns.js — Shared regex patterns & utilities
// Loaded first, available to all other detectors
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.PATTERNS = {
  // Email: standard RFC-ish match
  email: /\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,10}\b/g,

  // Phone: US + international formats
  phone: /(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?:\s?(?:ext|x|ext\.)\s?\d{1,5})?/g,

  // LinkedIn public profile URL
  linkedin: /(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[\w\-%.]+\/?/gi,

  // Company domains to exclude (free email providers)
  freeEmailDomains: new Set([
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'me.com', 'mail.com',
    'protonmail.com', 'ymail.com', 'comcast.net', 'att.net',
  ]),

  // Recruiter-relevant title keywords
  recruiterKeywords: [
    'recruiter', 'recruiting', 'talent', 'acquisition', 'hr ', 'human resources',
    'staffing', 'sourcer', 'sourcing', 'headhunter', 'hiring', 'people ops',
    'workforce', 'placement', 'coordinator', 'talent partner', 'talent lead',
    'talent manager', 'recruitment', 'technical recruiter', 'it recruiter',
  ],
};

/**
 * Score how likely this is a recruiter/HR profile (0-100)
 */
window.TalentScout.scoreRelevance = function(data) {
  let score = 0;
  const titleLower = (data.title || '').toLowerCase();
  const companyLower = (data.company_name || '').toLowerCase();

  // Title match
  for (const kw of window.TalentScout.PATTERNS.recruiterKeywords) {
    if (titleLower.includes(kw)) { score += 40; break; }
  }

  // Has work email (not free provider)
  if (data.email) {
    const domain = data.email.split('@')[1] || '';
    if (!window.TalentScout.PATTERNS.freeEmailDomains.has(domain.toLowerCase())) {
      score += 25;
    }
  }

  // Has LinkedIn URL
  if (data.linkedin_url) score += 15;

  // Has company name
  if (data.company_name) score += 10;

  // Has phone
  if (data.phone) score += 10;

  // Staffing companies — bonus
  const staffingHints = ['staffing', 'search', 'recruiting', 'talent', 'placement', 'group', 'solutions'];
  for (const hint of staffingHints) {
    if (companyLower.includes(hint)) { score += 10; break; }
  }

  return Math.min(score, 100);
};

/**
 * Extract first email from raw text
 */
window.TalentScout.extractEmail = function(text) {
  const matches = (text || '').match(window.TalentScout.PATTERNS.email);
  if (!matches) return null;
  return matches.find(m => {
    const domain = m.split('@')[1] || '';
    return !window.TalentScout.PATTERNS.freeEmailDomains.has(domain.toLowerCase());
  }) || matches[0] || null;
};

/**
 * Extract first phone from raw text
 */
window.TalentScout.extractPhone = function(text) {
  const matches = (text || '').match(window.TalentScout.PATTERNS.phone);
  return matches ? matches[0].trim() : null;
};

/**
 * Extract LinkedIn URL from raw text
 */
window.TalentScout.extractLinkedIn = function(text) {
  const matches = (text || '').match(window.TalentScout.PATTERNS.linkedin);
  return matches ? matches[0].split('?')[0].trim() : null;
};

/**
 * Normalize a name (title case, remove extra whitespace)
 */
window.TalentScout.normalizeName = function(raw) {
  if (!raw) return null;
  return raw.trim().replace(/\s+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

/**
 * Get text content safely
 */
window.TalentScout.text = function(selector, root) {
  const el = (root || document).querySelector(selector);
  return el ? el.textContent.replace(/\s+/g, ' ').trim() : null;
};
