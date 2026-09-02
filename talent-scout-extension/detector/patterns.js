// ============================================================
// detector/patterns.js — High-Speed Entity Extractor & Evidence Grounding Engine
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

  // UI Action Blacklist — Never treat these as names, titles, or companies!
  uiActions: new Set([
    'connect', 'contact', 'message', 'follow', 'following', 'pending',
    'see more', 'show all', 'view profile', 'more', 'save', 'saved',
    'endorse', 'share', 'like', 'comment', 'send', 'withdraw',
    'join', 'join now', 'sign in', 'sign up', 'sign in to view',
    'apply', 'easy apply', 'applied', 'quick apply', 'apply now',
    'apply on company site', 'apply on employer site', 'visit website',
    'visit', 'open', 'close', 'edit', 'delete', 'cancel', 'submit',
    'search', 'filter', 'sort', 'clear', 'reset', 'next', 'previous',
    'back', 'skip', 'done', 'home', 'jobs', 'people', 'companies',
    'salaries', 'interviews', 'posts', 'about', 'insights', 'feed',
    'notifications', 'network', 'my network', 'manage', 'settings',
    'help', 'privacy', 'terms', 'feedback', 'report', 'block',
    'unfollow', 'remove', 'view', 'read more', 'learn more', 'details',
    'show more', 'show less', 'expand', 'collapse', 'experience',
    'education', 'skills', 'interests', 'activity', 'highlights',
    'mutual connections', 'mutual connection', 'people you may know',
    'see all people', 'past company', 'current company', 'view job',
    'save job', 'quick apply now'
  ]),

  // Platform Names — Never treat these as the employer company
  platformNames: new Set([
    'simplyhired', 'linkedin', 'indeed', 'glassdoor', 'ziprecruiter',
    'monster', 'careerbuilder', 'dice', 'handshake', 'wellfound',
    'angel', 'angellist', 'snagajob', 'lensa', 'jooble', 'adzuna',
    'nexxt', 'upwork', 'fiverr', 'usajobs', 'linkup', 'greenhouse',
    'lever', 'workday', 'icims', 'smartrecruiters', 'jobvite',
    'bamboohr', 'ashby', 'breezy', 'recruitee', 'talentscout',
    'talentops', 'bing', 'yahoo', 'duckduckgo'
  ]),

  // Job Title Role Nouns — Used to prevent job titles from being treated as human names!
  jobRoleNouns: new Set([
    'teacher', 'educator', 'instructor', 'professor', 'faculty',
    'engineer', 'developer', 'architect', 'programmer', 'coder',
    'manager', 'director', 'lead', 'head', 'vp', 'president', 'chief',
    'officer', 'executive', 'supervisor', 'coordinator', 'administrator',
    'specialist', 'analyst', 'consultant', 'advisor', 'associate',
    'recruiter', 'sourcer', 'headhunter', 'partner', 'representative',
    'phlebotomist', 'nurse', 'doctor', 'physician', 'therapist',
    'technician', 'mechanic', 'electrician', 'plumber', 'driver',
    'operator', 'machinist', 'assembler', 'inspector', 'worker',
    'collector', 'clerk', 'cashier', 'assistant', 'intern', 'trainee',
    'accountant', 'auditor', 'bookkeeper', 'underwriter', 'estimator',
    'scientist', 'researcher', 'statistician', 'designer', 'writer'
  ]),

  // Comprehensive recruiting keywords
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
 * Check if a text is a UI action button / control or section header
 */
window.TalentScout.isUIAction = function(text) {
  if (!text) return false;
  const clean = text.toLowerCase().trim().replace(/^[•·\s\-_]+|[•·\s\-_]+$/g, '');
  if (window.TalentScout.PATTERNS.uiActions.has(clean)) return true;

  // Prefix checks
  if (/^(show all|view all|see all|search|message|connect|follow|manage|filter|sort|edit|delete|add|join|invite|open|close|click|tap)\b/i.test(clean)) {
    return true;
  }

  // Common UI/Section fragments
  if (/volunteer experience|search chat|open messaging|compose message|conversations|unread messages|ad choices|help center|more actions|recommendations|licenses|certifications|honors & awards|languages|organizations|featured items|recent activity/i.test(clean)) {
    return true;
  }

  return false;
};

/**
 * Check if a text is a platform/source website name
 */
window.TalentScout.isPlatformName = function(text) {
  if (!text) return false;
  const clean = text.toLowerCase().trim().replace(/^www\./, '').split('.')[0];
  return window.TalentScout.PATTERNS.platformNames.has(clean) || window.TalentScout.PATTERNS.platformNames.has(text.toLowerCase().trim());
};

/**
 * Check if a text phrase represents a job posting title rather than a human name.
 * e.g. "High School Mathematics Teacher", "Transmission Project Manager", "Mobile Phlebotomist"
 */
window.TalentScout.isJobTitle = function(text) {
  if (!text) return false;
  const words = text.toLowerCase().trim().split(/[\s\-_/,]+/);
  return words.some(w => window.TalentScout.PATTERNS.jobRoleNouns.has(w));
};

/**
 * Strict Human Name Validator — Rejects job titles, UI actions, and platform names.
 */
window.TalentScout.validateHumanName = function(rawName) {
  if (!rawName) return { isValid: false, reason: 'empty_name' };

  let name = rawName.trim();
  // Strip degree bullets, numbers, pronouns, and degree credentials
  name = name.replace(/[·•]\s*\d+(?:st|nd|rd|th)?/gi, '');
  name = name.replace(/\b\d+(?:st|nd|rd|th)?\s+degree(?:\s+connection)?\b/gi, '');
  name = name.replace(/\b\d+(?:st|nd|rd|th)\b/gi, '');
  name = name.replace(/\((?:he\/him|she\/her|they\/them|she\/they|he\/they|any)\)/gi, '');
  name = name.replace(/\b(?:MBA|SHRM-CP|PHR|SPHR|PMP|CPA|MD|JD|PhD|BSc|MSc|BA|BS|MA|MS)\b/gi, '');
  name = name.split(/[-–—|,]/)[0].replace(/[^\w\s\'.]/g, ' ').trim();
  name = name.replace(/\s+/g, ' ');

  if (!name || name.length < 2 || name.length > 50) {
    return { isValid: false, reason: 'invalid_length' };
  }

  const lower = name.toLowerCase();

  if (window.TalentScout.isUIAction(lower)) {
    return { isValid: false, reason: `ui_action:${name}` };
  }

  if (window.TalentScout.isPlatformName(lower)) {
    return { isValid: false, reason: `platform_name:${name}` };
  }

  if (window.TalentScout.isJobTitle(lower)) {
    return { isValid: false, reason: `job_title_as_name:${name}` };
  }

  if (['professional lead', 'candidate lead', 'linkedin member', 'view profile', 'corporate contact', 'search chat'].includes(lower)) {
    return { isValid: false, reason: `generic_placeholder:${name}` };
  }

  // Must contain at least one letter and at least 2 characters
  if (!/[a-zA-Z]/.test(name) || name.split(' ').length > 5) {
    return { isValid: false, reason: 'unnatural_name_structure' };
  }

  // Capitalize properly
  const cleanName = name.replace(/\b\w/g, c => c.toUpperCase());
  return { isValid: true, cleanName: cleanName };
};

/**
 * Classify semantic page type
 */
window.TalentScout.classifyPageType = function(url, title) {
  const u = (url || location.href || '').toLowerCase();
  const t = (title || document.title || '').toLowerCase();

  if (u.includes('mail.google.com') || u.includes('outlook.live.com') || u.includes('outlook.office')) {
    return 'EMAIL_INBOX';
  }
  if (u.includes('simplyhired.com') || u.includes('indeed.com/jobs') || u.includes('ziprecruiter.com/jobs') || u.includes('glassdoor.com/job') || u.includes('linkedin.com/jobs')) {
    return 'JOB_SEARCH_PAGE';
  }
  if (u.includes('linkedin.com/company/') && (u.includes('/people') || u.includes('/about'))) {
    return 'COMPANY_PEOPLE_PAGE';
  }
  if (u.includes('linkedin.com/in/') || u.includes('linkedin.com/pub/')) {
    return 'INDIVIDUAL_PROFILE';
  }
  if (['greenhouse.io', 'lever.co', 'myworkdayjobs.com', 'icims.com', 'smartrecruiters.com'].some(ats => u.includes(ats))) {
    return 'ATS_PORTAL';
  }
  return 'GENERIC_WEB';
};

/**
 * Clean & Disambiguate Job Title & Company
 */
window.TalentScout.cleanTitleAndCompany = function(rawTitle, rawCompany, pageCompanyContext) {
  let title = (rawTitle || '').trim();
  let company = (rawCompany || '').trim();
  let specialty = null;

  // 1. If title is a UI action, nullify it immediately
  if (window.TalentScout.isUIAction(title) || ['contact', 'professional lead', 'candidate lead'].includes(title.toLowerCase())) {
    title = null;
  }

  // 2. If company is a platform name (e.g. 'SimplyHired', 'LinkedIn'), nullify or fallback to page context
  if (window.TalentScout.isPlatformName(company)) {
    company = null;
  }

  // 3. Parse complex headlines (e.g. "Managing Director @ Custom Kiks | Marketing & Growth Strategist")
  if (title) {
    // Check for "Role @ Company | Specialty" or "Role at Company | Specialty"
    const atMatch = title.match(/^(.+?)\s+(?:at|@)\s+(.+)$/i);
    if (atMatch) {
      title = atMatch[1].trim();
      const compAndRest = atMatch[2].trim();
      if (compAndRest.includes('|')) {
        const parts = compAndRest.split('|').map(p => p.trim());
        let extractedComp = parts[0].split(',')[0].trim();
        extractedComp = extractedComp.replace(/\s+(?:with|specializing|focused|helping|passionate|leading|driving|expert)\b.*$/i, '').trim();
        if (!company || window.TalentScout.isPlatformName(company)) {
          company = extractedComp;
        }
        specialty = parts.slice(1).join(' | ').trim();
      } else {
        let extractedComp = compAndRest.split(',')[0].trim();
        extractedComp = extractedComp.replace(/\s+(?:with|specializing|focused|helping|passionate|leading|driving|expert)\b.*$/i, '').trim();
        if (!company || window.TalentScout.isPlatformName(company)) {
          company = extractedComp;
        }
      }
    } else if (title.includes(' | ')) {
      const parts = title.split(' | ').map(p => p.trim());
      title = parts[0].trim();
      specialty = parts.slice(1).join(' | ').trim();
    }
  }

  // 4. Inherit Page-Level Company Context if missing or invalid
  if ((!company || window.TalentScout.isPlatformName(company)) && pageCompanyContext) {
    if (!window.TalentScout.isPlatformName(pageCompanyContext)) {
      company = pageCompanyContext.trim();
    }
  }

  // Final sanity checks
  if (window.TalentScout.isUIAction(title)) title = null;
  if (window.TalentScout.isPlatformName(company)) company = null;

  return {
    title: title || 'Professional',
    company_name: company || null,
    specialty: specialty || null,
  };
};

/**
 * Calculate Component-Based Confidences (0-100)
 */
window.TalentScout.calculateFieldConfidences = function(data) {
  const nameVal = window.TalentScout.validateHumanName(data.recruiter_name);
  const nameConf = nameVal.isValid ? 95 : 0;

  let titleConf = 0;
  if (data.title && !window.TalentScout.isUIAction(data.title) && !['contact', 'professional lead'].includes(data.title.toLowerCase())) {
    const t = data.title.toLowerCase();
    const hasRecruiterKw = window.TalentScout.PATTERNS.recruiterKeywords.some(k => t.includes(k));
    const hasProfKw = window.TalentScout.PATTERNS.professionalKeywords.some(k => t.includes(k));
    titleConf = (hasRecruiterKw || hasProfKw) ? 95 : 70;
  }

  const companyConf = (data.company_name && !window.TalentScout.isPlatformName(data.company_name)) ? 90 : 0;

  let overall = 0;
  if (nameConf === 0) {
    overall = 0; // ZERO confidence if human name is invalid / missing!
  } else if (titleConf > 0 && companyConf > 0) {
    overall = Math.round(nameConf * 0.4 + titleConf * 0.3 + companyConf * 0.3);
  } else if (titleConf > 0 || companyConf > 0) {
    overall = Math.round(nameConf * 0.5 + (titleConf || companyConf) * 0.4);
  } else {
    overall = Math.round(nameConf * 0.5);
  }

  if (data.linkedin_url && data.linkedin_url.includes('linkedin.com/in/')) overall = Math.min(100, overall + 5);
  if (data.email && !data.email.endsWith('@noemail.talentops')) overall = Math.min(100, overall + 10);
  if (data.phone) overall = Math.min(100, overall + 5);

  return {
    name: nameConf,
    title: titleConf,
    company: companyConf,
    overall: Math.min(100, overall),
  };
};

/**
 * Strict Evidence Grounding Gate
 */
window.TalentScout.evaluateEvidenceGrounding = function(entity, pageUrl, pageTitle) {
  const pageType = window.TalentScout.classifyPageType(pageUrl, pageTitle);
  const nameVal = window.TalentScout.validateHumanName(entity.recruiter_name);
  const isPlat = window.TalentScout.isPlatformName(entity.company_name);
  const isUI = window.TalentScout.isUIAction(entity.title);

  const rejections = [];
  if (!nameVal.isValid) rejections.push(`Name validation failed: ${nameVal.reason}`);
  if (isPlat) rejections.push(`Company '${entity.company_name}' is a platform name`);
  if (isUI) rejections.push(`Title '${entity.title}' is a UI action`);

  if (pageType === 'JOB_SEARCH_PAGE' && (!nameVal.isValid || window.TalentScout.isJobTitle(entity.recruiter_name))) {
    rejections.push('Job search page: cannot invent person from job posting');
  }

  const isGrounded = rejections.length === 0;
  return {
    is_grounded: isGrounded,
    grounding_score: isGrounded ? 100 : 0,
    page_type: pageType,
    clean_name: nameVal.cleanName || null,
    rejection_reasons: rejections,
    decision: isGrounded ? 'ACCEPT' : 'REJECT_UNGROUNDED',
  };
};

/**
 * Text normalizer
 */
window.TalentScout.normalizeName = function(name) {
  const val = window.TalentScout.validateHumanName(name);
  return val.isValid ? val.cleanName : null;
};

/**
 * Extract email from text
 */
window.TalentScout.extractEmail = function(text) {
  if (!text) return null;
  const matches = text.match(window.TalentScout.PATTERNS.email);
  return matches ? matches[0].toLowerCase() : null;
};

/**
 * Extract phone from text
 */
window.TalentScout.extractPhone = function(text) {
  if (!text) return null;
  const matches = text.match(window.TalentScout.PATTERNS.phone);
  if (!matches) return null;
  const phone = matches[0].trim();
  const digits = phone.replace(/\D/g, '');
  return (digits.length >= 10 && digits.length <= 15) ? phone : null;
};

/**
 * Extract LinkedIn URL from text or HTML
 */
window.TalentScout.extractLinkedIn = function(text) {
  if (!text) return null;
  const matches = text.match(window.TalentScout.PATTERNS.linkedin);
  if (!matches) return null;
  return matches[0].split('?')[0].split('#')[0].replace(/\/+$/, '');
};

/**
 * Infer human name from LinkedIn profile slug
 */
window.TalentScout.inferNameFromLinkedInSlug = function(url) {
  if (!url) return null;
  const m = url.match(/linkedin\.com\/in\/([a-zA-Z0-9\-_%]+)/i);
  if (!m || !m[1]) return null;
  let slug = m[1].replace(/[-_]+[0-9a-f]{6,}/i, '').replace(/[-_]+\d+$/, '');
  const words = slug.split(/[-_.]+/).filter(Boolean);
  if (words.length >= 2) {
    const raw = words.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
    const val = window.TalentScout.validateHumanName(raw);
    return val.isValid ? val.cleanName : null;
  }
  return slug.charAt(0).toUpperCase() + slug.slice(1).toLowerCase();
};

/**
 * DOM text helper (supports selector string or array of fallback selectors)
 */
window.TalentScout.text = function(selector, root = document) {
  if (!selector) return null;
  if (Array.isArray(selector)) {
    for (const sel of selector) {
      try {
        const el = root.querySelector(sel);
        if (el && el.textContent) return el.textContent.trim();
      } catch (e) {}
    }
    return null;
  }
  try {
    const el = root.querySelector(selector);
    return el ? el.textContent.trim() : null;
  } catch (e) {
    return null;
  }
};
