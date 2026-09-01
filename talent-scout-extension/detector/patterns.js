// ============================================================
// detector/patterns.js — High-Speed Entity Extractor & Heuristics
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.PATTERNS = {
  // RFC 5322 compatible email matcher
  email: /\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,10}\b/g,

  // US & International phone matcher
  phone: /(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?:\s?(?:ext|x|ext\.)\s?\d{1,5})?/g,

  // LinkedIn profile URLs (in/ or pub/)
  linkedin: /(?:https?:\/\/)?(?:[a-zA-Z0-9_-]+\.)?linkedin\.com\/(?:in|pub)\/([a-zA-Z0-9\-_%]+)/gi,

  // Mailto links
  mailto: /mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,10})/i,

  // Common free email providers to filter out
  freeEmailDomains: new Set([
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'me.com', 'mail.com',
    'protonmail.com', 'ymail.com', 'comcast.net', 'att.net', 'sbcglobal.net',
    'verizon.net', 'cox.net', 'charter.net', 'earthlink.net', 'zoho.com'
  ]),

  // Comprehensive recruiting, talent & hiring keywords
  recruiterKeywords: [
    'recruiter', 'recruiting', 'talent', 'acquisition', 'hr', 'human resources',
    'staffing', 'sourcer', 'sourcing', 'headhunter', 'hiring', 'people ops',
    'workforce', 'placement', 'coordinator', 'talent partner', 'talent lead',
    'talent manager', 'recruitment', 'technical recruiter', 'it recruiter',
    'executive recruiter', 'head of talent', 'vp of people', 'people partner',
    'consultant', 'talent scout', 'talent advisor', 'resource manager',
    'staffing specialist', 'search consultant', 'hiring manager', 'team lead',
    'founder', 'co-founder', 'director of recruitment', 'people & culture',
    'talent acquisition specialist', 'lead recruiter'
  ],
};

/**
 * Score relevance (0-100) — lenient and aggressive for high yield
 */
window.TalentScout.scoreRelevance = function(data) {
  let score = 30; // base score for any detected person entity
  const titleLower = (data.title || '').toLowerCase();
  const companyLower = (data.company_name || '').toLowerCase();

  // If found on LinkedIn, auto +30
  if (data.source && data.source.includes('linkedin')) {
    score += 30;
  }

  // If found in an email signature, auto +30
  if (data.source && data.source.includes('signature')) {
    score += 30;
  }

  // Title keyword matching
  for (const kw of window.TalentScout.PATTERNS.recruiterKeywords) {
    if (titleLower.includes(kw)) { score += 40; break; }
  }

  // Corporate work email (not free provider)
  if (data.email) {
    const domain = (data.email.split('@')[1] || '').toLowerCase();
    if (!window.TalentScout.PATTERNS.freeEmailDomains.has(domain)) {
      score += 30;
    } else {
      score += 10;
    }
  }

  if (data.linkedin_url) score += 20;
  if (data.company_name) score += 15;
  if (data.phone) score += 15;

  return Math.min(score, 100);
};

/**
 * Extract email from raw text
 */
window.TalentScout.extractEmail = function(text) {
  if (!text) return null;
  const matches = text.match(window.TalentScout.PATTERNS.email);
  if (!matches || matches.length === 0) return null;

  // Prefer non-freemail
  const corporate = matches.find(m => {
    const domain = (m.split('@')[1] || '').toLowerCase();
    return !window.TalentScout.PATTERNS.freeEmailDomains.has(domain);
  });
  return (corporate || matches[0]).toLowerCase().trim();
};

/**
 * Extract phone from raw text
 */
window.TalentScout.extractPhone = function(text) {
  if (!text) return null;
  const matches = text.match(window.TalentScout.PATTERNS.phone);
  if (!matches || matches.length === 0) return null;
  // Clean phone string
  const clean = matches[0].replace(/[^\d+()-\s]/g, '').trim();
  return clean.length >= 10 ? clean : null;
};

/**
 * Extract LinkedIn URL from text or hrefs
 */
window.TalentScout.extractLinkedIn = function(text) {
  if (!text) return null;
  const matches = text.match(window.TalentScout.PATTERNS.linkedin);
  if (!matches || matches.length === 0) return null;
  let url = matches[0].split('?')[0].trim();
  if (!url.startsWith('http')) url = 'https://' + url.replace(/^\/\//, '');
  return url;
};

/**
 * Infer full name from LinkedIn slug (e.g. "sarah-jenkins-8a901b" -> "Sarah Jenkins", "judymackesy" -> "Judy Mackesy")
 */
window.TalentScout.inferNameFromLinkedInSlug = function(url) {
  if (!url) return null;
  const slug = url.split('/in/')[1]?.split('/')[0]?.split('?')[0];
  if (!slug) return null;
  // Strip trailing hash/random digits/hex ids
  let cleaned = slug.replace(/-[a-f0-9]{4,16}$/i, '').replace(/[-_.]+/g, ' ');
  // If slug has no spaces (e.g. judymackesy), attempt camelCase / split or return Title Cased
  cleaned = cleaned.replace(/([a-z])([A-Z])/g, '$1 $2');
  return window.TalentScout.normalizeName(cleaned);
};

/**
 * Infer name from corporate email (e.g. "sarah.jenkins@apexsystems.com" -> "Sarah Jenkins")
 */
window.TalentScout.inferNameFromEmail = function(email) {
  if (!email || !email.includes('@')) return null;
  const local = email.split('@')[0];
  // Handle formats: firstname.lastname, firstname_lastname, firstnamelastname
  if (local.includes('.') || local.includes('_') || local.includes('-')) {
    const parts = local.split(/[._-]+/);
    if (parts.length >= 2 && parts[0].length >= 2 && parts[1].length >= 2) {
      return window.TalentScout.normalizeName(parts.slice(0, 2).join(' '));
    }
  }
  return null;
};

/**
 * Normalize and clean names (handles LinkedIn degree badges, pronouns, credentials)
 */
window.TalentScout.normalizeName = function(raw) {
  if (!raw) return null;
  let clean = String(raw).trim();

  // 1. Remove LinkedIn Degree connection badges (1st, 2nd, 3rd, 3rd+)
  clean = clean.replace(/\b(?:1st|2nd|3rd|3rd\+|\d+(?:st|nd|rd|th))\b/gi, '');

  // 2. Remove Pronouns (he/him, she/her, they/them, etc.)
  clean = clean.replace(/\((?:he\/him|she\/her|they\/them|she\/they|he\/they|any)\)/gi, '');

  // 3. Remove common professional suffixes & certifications
  clean = clean.replace(/,?\s*\b(?:phd|mba|pmp|cir|cdr|cpc|shrm(?:-cp|-scp)?|sphr|phr|recruiter|talent|hr|staffing|esq|cpa|md|dds|ms|bs|ba|ma|rn)\b/gi, '');

  // 4. Strip numbers and unwanted symbols, keep letters, hyphens, spaces, apostrophes
  clean = clean.replace(/\d+/g, ' ');
  clean = clean.replace(/[^\w\s'.\-]/g, ' ').replace(/\s+/g, ' ').trim();

  // 5. Reject if empty, too short, too long, or common junk labels
  if (clean.length < 2 || clean.length > 60) return null;
  const lower = clean.toLowerCase();
  if (['linkedin member', 'view profile', 'see all', 'member', 'unknown', 'sign in', 'join now', 'experience', 'education', 'contact info'].includes(lower)) {
    return null;
  }

  // 6. Capitalize words cleanly (Title Case)
  return clean.replace(/\b\w/g, c => c.toUpperCase());
};

/**
 * Safe text getter with fallback
 */
window.TalentScout.text = function(selectors, root) {
  const selList = Array.isArray(selectors) ? selectors : [selectors];
  for (const sel of selList) {
    const el = (root || document).querySelector(sel);
    const t = el?.textContent?.replace(/\s+/g, ' ').trim();
    if (t) return t;
  }
  return null;
};
