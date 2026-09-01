// ============================================================
// detector/patterns.js — High-Speed Entity Extractor & Domain Relevance Engine
// Algorithms 6, 11, 14, 15, 32: Usefulness Scoring Gate & Field-Level Enrichment
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

  // Free email domains
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

  // Broad professional role keywords
  professionalKeywords: [
    'founder', 'co-founder', 'ceo', 'cto', 'cpo', 'coo', 'vp', 'vice president',
    'director', 'head of', 'partner', 'lead', 'manager', 'specialist',
    'consultant', 'officer', 'principal', 'engineer', 'architect', 'developer',
    'analyst', 'account executive', 'business development', 'product manager'
  ],
};

/**
 * Algorithm 11: Calculate Frame/Entity Usefulness Score (0 - 100)
 * Evaluates whether extracted data contains real professional/recruiting signals.
 */
window.TalentScout.calculateUsefulnessScore = function(data) {
  if (!data) return 0;
  let score = 0;

  const name = (data.recruiter_name || '').trim();
  const title = (data.title || '').toLowerCase().trim();
  const company = (data.company_name || '').trim();

  // 1. Person detected (+25)
  if (name && name.length >= 2) {
    const isJunkName = ['linkedin member', 'view profile', 'see all', 'member', 'unknown', 'sign in', 'join now', 'experience', 'education', 'contact info', 'profile'].includes(name.toLowerCase());
    if (!isJunkName) score += 25;
  }

  // 2. Recruiting / Hiring signal (+20)
  for (const kw of window.TalentScout.PATTERNS.recruiterKeywords) {
    if (title.includes(kw)) {
      score += 20;
      break;
    }
  }

  // 3. Professional role detected (+20)
  if (title && title.length >= 3) {
    for (const kw of window.TalentScout.PATTERNS.professionalKeywords) {
      if (title.includes(kw)) {
        score += 20;
        break;
      }
    }
    // Base credit for any non-empty title if no keyword match
    if (score < 45) score += 10;
  }

  // 4. Company detected (+15)
  if (company && company.length >= 2) {
    score += 15;
  }

  // 5. LinkedIn URL detected (+10)
  if (data.linkedin_url && data.linkedin_url.includes('linkedin.com/in/')) {
    score += 10;
  }

  // 6. Email detected (+10)
  if (data.email) {
    const domain = (data.email.split('@')[1] || '').toLowerCase();
    score += 10;
    if (!window.TalentScout.PATTERNS.freeEmailDomains.has(domain)) {
      score += 5; // Corporate email bonus
    }
  }

  // 7. Phone detected (+10)
  if (data.phone) {
    score += 10;
  }

  // 8. Location detected (+5)
  if (data.location) {
    score += 5;
  }

  // 9. LinkedIn source auto-boost (+10)
  if (data.source && data.source.includes('linkedin')) {
    score += 10;
  }

  return Math.min(score, 100);
};

/**
 * Hard Gate: Is entity useful to our domain? (Threshold >= 35)
 */
window.TalentScout.isUsefulDomainEntity = function(data) {
  const score = window.TalentScout.calculateUsefulnessScore(data);
  return score >= 35;
};

/**
 * Extract email from raw text
 */
window.TalentScout.extractEmail = function(text) {
  if (!text) return null;
  const matches = text.match(window.TalentScout.PATTERNS.email);
  if (!matches || matches.length === 0) return null;

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
 * Infer full name from LinkedIn slug
 */
window.TalentScout.inferNameFromLinkedInSlug = function(url) {
  if (!url) return null;
  const slug = url.split('/in/')[1]?.split('/')[0]?.split('?')[0];
  if (!slug) return null;
  let cleaned = slug.replace(/-[a-f0-9]{4,16}$/i, '').replace(/[-_.]+/g, ' ');
  cleaned = cleaned.replace(/([a-z])([A-Z])/g, '$1 $2');
  return window.TalentScout.normalizeName(cleaned);
};

/**
 * Infer name from corporate email
 */
window.TalentScout.inferNameFromEmail = function(email) {
  if (!email || !email.includes('@')) return null;
  const local = email.split('@')[0];
  if (local.includes('.') || local.includes('_') || local.includes('-')) {
    const parts = local.split(/[._-]+/);
    if (parts.length >= 2 && parts[0].length >= 2 && parts[1].length >= 2) {
      return window.TalentScout.normalizeName(parts.slice(0, 2).join(' '));
    }
  }
  return null;
};

/**
 * Normalize and clean names
 */
window.TalentScout.normalizeName = function(raw) {
  if (!raw) return null;
  let clean = String(raw).trim();

  // 1. Remove LinkedIn degree connection phrases: "1st degree connection", "2nd degree", etc.
  clean = clean.replace(/\b(?:\d+(?:st|nd|rd|th)?\s+)?degree(?:\s+connection)?\b/gi, '');
  clean = clean.replace(/\b(?:1st|2nd|3rd|3rd\+|\d+(?:st|nd|rd|th))\b/gi, '');

  // 2. Remove Pronouns: (he/him), (she/her), (they/them), etc.
  clean = clean.replace(/\((?:he\/him|she\/her|they\/them|she\/they|he\/they|any)\)/gi, '');

  // 3. Remove Title / Headline suffixes after hyphens or pipes
  if (clean.includes(' - ') || clean.includes(' | ') || clean.includes(' — ') || clean.includes(' – ')) {
    clean = clean.split(/\s*[-–—|]\s*/)[0].trim();
  }

  // 4. Remove common professional suffixes & certifications
  clean = clean.replace(/,?\s*\b(?:phd|mba|pmp|cir|cdr|cpc|shrm(?:-cp|-scp)?|sphr|phr|recruiter|talent|hr|staffing|esq|cpa|md|dds|ms|bs|ba|ma|rn)\b/gi, '');

  // 5. Strip numbers and unwanted symbols
  clean = clean.replace(/\d+/g, ' ');
  clean = clean.replace(/[^\w\s'.\-]/g, ' ').replace(/\s+/g, ' ').trim();

  // 6. Reject if empty, too short, too long, or junk
  if (clean.length < 2 || clean.length > 60) return null;
  const lower = clean.toLowerCase();
  if (['linkedin member', 'view profile', 'see all', 'member', 'unknown', 'sign in', 'join now', 'experience', 'education', 'contact info', 'profile'].includes(lower)) {
    return null;
  }

  // 7. Capitalize words cleanly (Title Case)
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
