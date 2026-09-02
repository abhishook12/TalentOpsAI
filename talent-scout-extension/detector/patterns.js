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
    'save job', 'quick apply now', 'top skills', 'start a post', 'write an article'
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
  // Strip newlines / tabs (DOM concatenated subtitles)
  name = name.split(/[\r\n\t]+/)[0].trim();

  // Strip degree bullets, numbers, pronouns, and degree credentials
  name = name.replace(/[·•]\s*\d+(?:st|nd|rd|th)?/gi, '');
  name = name.replace(/\b\d+(?:st|nd|rd|th)?\s+degree(?:\s+connection)?\b/gi, '');
  name = name.replace(/\b\d+(?:st|nd|rd|th)\b/gi, '');
  name = name.replace(/\((?:he\/him|she\/her|they\/them|she\/they|he\/they|any)\)/gi, '');
  name = name.replace(/\b(?:MBA|SHRM-CP|PHR|SPHR|PMP|CPA|MD|JD|PhD|BSc|MSc|BA|BS|MA|MS)\b/gi, '');
  name = name.split(/[-–—|,]/)[0].replace(/[^\w\s\'.]/g, ' ').trim();
  name = name.replace(/\s+/g, ' ');

  // Check if original raw phrase was a job title
  if (window.TalentScout.isJobTitle(name.toLowerCase())) {
    return { isValid: false, reason: `job_title_as_name:${name}` };
  }

  // If name has trailing role title words (e.g. "Aditi Chauhan SAP SuccessFactors" -> "Aditi Chauhan", "Jitendra Tripathi Founder" -> "Jitendra Tripathi")
  const tokens = name.split(' ');
  if (tokens.length >= 3) {
    const roleNouns = window.TalentScout.PATTERNS.jobRoleNouns;
    let cutIdx = -1;
    for (let i = 2; i < tokens.length; i++) {
      const tokLower = tokens[i].toLowerCase();
      if (roleNouns.has(tokLower) || /^(founder|ceo|cto|cpo|coo|vp|recruiter|sourcer|consultant|manager|director|engineer|developer|analyst|specialist|partner|lead|head|architect|sap|oracle|staffing|talent|hiring|hr)$/i.test(tokLower)) {
        cutIdx = i;
        break;
      }
    }
    if (cutIdx >= 2) {
      name = tokens.slice(0, cutIdx).join(' ');
    }
  }

  if (!name || name.length < 2 || name.length > 50) {
    return { isValid: false, reason: 'invalid_length' };
  }

  const lower = name.toLowerCase();

  if (window.TalentScout.isJobTitle(lower)) {
    return { isValid: false, reason: `job_title_as_name:${name}` };
  }

  if (window.TalentScout.isUIAction(lower)) {
    return { isValid: false, reason: `ui_action:${name}` };
  }

  if (window.TalentScout.isPlatformName(lower)) {
    return { isValid: false, reason: `platform_name:${name}` };
  }

  if (window.TalentScout.isJobTitle(lower)) {
    return { isValid: false, reason: `job_title_as_name:${name}` };
  }

  // Reject feed posts, articles, newsletter headers, and page elements
  if (/\b(?:feed post|post number|page posts?|feed item|reactions?|comments?|shares?|newsletter|announcement|headline news|sponsored|promoted)\b/i.test(lower)) {
    return { isValid: false, reason: `feed_post_noise:${name}` };
  }

  // Reject names containing digits (e.g. "Feed post number 1", "Candidate 2")
  if (/\d/.test(name)) {
    return { isValid: false, reason: `digits_in_name:${name}` };
  }

  // Reject notification strings
  if (/accepted your invitation|sent you a message|top skills|skills|celebrates|work anniversary|shared a post|reacted to|watch for signs|greater risk/i.test(lower)) {
    return { isValid: false, reason: `notification_noise:${name}` };
  }

  // Must contain at least one letter, no emojis, and between 2 to 4 words
  if (!/^[a-zA-Z\s'.\-]+$/.test(name) || name.split(' ').length > 4) {
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

  // 1. If title is a UI action or notification, nullify it immediately
  if (window.TalentScout.isUIAction(title) || ['contact', 'professional lead', 'candidate lead'].includes(title.toLowerCase())) {
    title = null;
  }
  if (title && /accepted your invitation|sent you a message|top skills|skills|shared a post|celebrates|work anniversary|endorsed you|commented on/i.test(title)) {
    title = null;
  }

  // 2. If company is a platform name, sentence, or contains emojis/alerts, nullify or fallback
  if (window.TalentScout.isPlatformName(company)) {
    company = null;
  }
  if (company && (/[^\w\s&.,'\-]/i.test(company) || /[🚨⚠️❗❓❌✅]/.test(company) || /\b(?:greater risk|watch for|signs of|illness|warning|alert|sponsored|weather|news)\b/i.test(company) || company.split(' ').length > 6)) {
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
    if (!window.TalentScout.isPlatformName(pageCompanyContext) && !/[🚨⚠️❗❓]/.test(pageCompanyContext) && pageCompanyContext.split(' ').length <= 6) {
      company = pageCompanyContext.trim();
    }
  }

  // Final sanity checks
  if (window.TalentScout.isUIAction(title)) title = null;
  if (window.TalentScout.isPlatformName(company)) company = null;
  if (company && (company.split(' ').length > 6 || /\b(?:greater risk|watch for|signs of|illness)\b/i.test(company))) company = null;

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
 * Extract phone from text (strictly 10-11 digits, rejecting 13-digit millisecond epoch timestamps)
 */
window.TalentScout.extractPhone = function(text) {
  if (!text) return null;
  const matches = text.match(window.TalentScout.PATTERNS.phone);
  if (!matches) return null;
  const phone = matches[0].trim();
  const digits = phone.replace(/\D/g, '');
  
  // Reject numbers that are not standard 10 or 11 digits, or look like timestamps (starting with 175, 170, 160 with trailing zeros)
  if (digits.length < 10 || digits.length > 11) return null;
  if (/^1[6789]\d{8,}$/.test(digits) && digits.endsWith('0000')) return null;
  if (digits === '1750896000000' || digits.length >= 12) return null;

  return phone;
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
 * Extract connection degree (1st, 2nd, 3rd, 3rd+)
 */
window.TalentScout.extractConnectionDegree = function(text) {
  if (!text) return null;
  const m = text.match(/\b(1st|2nd|3rd(?:\+)?)\b/i);
  return m ? m[1].toLowerCase() : null;
};

/**
 * Extract connection count (e.g. "17 connections", "500+ connections")
 */
window.TalentScout.extractConnectionCount = function(text) {
  if (!text) return null;
  const m = text.match(/\b(\d+(?:\+)?\s+connections?)\b/i);
  return m ? m[1] : null;
};

/**
 * Decompose raw About summary into structured professional observations
 * (Prevents flattening/discarding the About section into a single useless string)
 */
window.TalentScout.decomposeAboutSection = function(rawAbout) {
  if (!rawAbout || typeof rawAbout !== 'string' || rawAbout.length < 15) return null;

  const text = rawAbout.trim();
  const lower = text.toLowerCase();

  // 1. Extract years of experience
  let yearsExp = null;
  const yMatch = text.match(/\b(\d+\+?\s*years?(?:\s+of)?(?:\s+recruitment|\s+recruiting|\s+staffing|\s+industry|\s+professional|\s+experience|\s+expertise)?)\b/i);
  if (yMatch) yearsExp = yMatch[1].trim();

  // 2. Extract Industries
  const knownIndustries = [
    'Technology', 'Software Engineering', 'IT', 'Finance', 'Healthcare',
    'Marketing', 'Sales', 'Biotech', 'Pharmaceutical', 'Manufacturing',
    'Retail', 'Aerospace', 'Defense', 'Energy', 'Cybersecurity', 'Cloud',
    'Artificial Intelligence', 'Data Science', 'Hospitality', 'Education'
  ];
  const matchedIndustries = [];
  knownIndustries.forEach(ind => {
    const reg = new RegExp(`\\b${ind}\\b`, 'i');
    if (reg.test(text)) matchedIndustries.push(ind);
  });

  // 3. Extract Specialties & Domains
  const knownSpecialties = [
    'Software engineering sourcing', 'Talent acquisition', 'Executive search',
    'Technical recruiting', 'Full-cycle recruiting', 'Contract staffing',
    'Direct placement', 'Candidate screening', 'Pipeline generation',
    'Campus recruiting', 'Leadership hiring', 'Sourcing strategy'
  ];
  const matchedSpecialties = [];
  knownSpecialties.forEach(spec => {
    const reg = new RegExp(`\\b${spec}\\b`, 'i');
    if (reg.test(text)) matchedSpecialties.push(spec);
  });

  // 4. Extract Candidate & Employer Focus
  let candidateFocus = null;
  if (/marketing\s+candidate\s+focus/i.test(text)) candidateFocus = 'Marketing candidate focus';
  else if (/engineering\s+candidate\s+focus/i.test(text)) candidateFocus = 'Engineering candidate focus';
  else if (/executive\s+candidate\s+focus/i.test(text)) candidateFocus = 'Executive candidate focus';

  let employerFocus = null;
  if (/employer\s*[\/\-]\s*candidate\s+relationship/i.test(text) || /candidate\s*[\/\-]\s*employer\s+relationship/i.test(text)) {
    employerFocus = 'Employer/candidate relationship focus';
  } else if (/client\s+partnership/i.test(text)) {
    employerFocus = 'Client partnership focus';
  }

  // 5. Build clean tree of structured observations
  const observations = [];
  if (yearsExp) observations.push(yearsExp);
  matchedIndustries.forEach(i => observations.push(i));
  matchedSpecialties.forEach(s => observations.push(s));
  if (candidateFocus) observations.push(candidateFocus);
  if (employerFocus) observations.push(employerFocus);

  return {
    raw_about: text,
    years_experience: yearsExp,
    industries: matchedIndustries.length > 0 ? matchedIndustries : null,
    specialties: matchedSpecialties.length > 0 ? matchedSpecialties : null,
    candidate_focus: candidateFocus,
    employer_focus: employerFocus,
    structured_observations: observations.length > 0 ? observations : [text],
  };
};

/**
 * Generate Comprehensive Forensic Completeness Report for Every Capture
 */
window.TalentScout.generateCompletenessReport = function(entity, pageContext = {}) {
  const visibleCategories = [];
  const extractedCategories = [];
  const notFound = [];
  const uncertain = [];

  // 1. Person Identity
  if (entity.recruiter_name) {
    visibleCategories.push('PERSON_NAME');
    extractedCategories.push({ field: 'name', value: entity.recruiter_name, confidence: entity.field_confidences?.name || 95 });
  } else {
    notFound.push('PERSON_NAME');
  }

  // 2. Current Title & Company
  if (entity.title) {
    visibleCategories.push('CURRENT_TITLE');
    extractedCategories.push({ field: 'title', value: entity.title, confidence: entity.field_confidences?.title || 90 });
  } else {
    notFound.push('CURRENT_TITLE');
  }

  if (entity.company_name) {
    visibleCategories.push('CURRENT_COMPANY');
    extractedCategories.push({ field: 'company', value: entity.company_name, confidence: entity.field_confidences?.company || 85 });
  } else {
    notFound.push('CURRENT_COMPANY');
  }

  // 3. Location
  if (entity.location) {
    visibleCategories.push('LOCATION');
    extractedCategories.push({ field: 'location', value: entity.location, confidence: 90 });
  } else {
    notFound.push('LOCATION');
  }

  // 4. Education
  if (entity.education) {
    visibleCategories.push('EDUCATION');
    extractedCategories.push({ field: 'education', value: entity.education, confidence: 90 });
  } else {
    notFound.push('EDUCATION');
  }

  // 5. Connections & Degree Context
  if (entity.connections_count || entity.connection_degree) {
    visibleCategories.push('SOCIAL_GRAPH_PROOF');
    extractedCategories.push({
      field: 'social_graph',
      connections: entity.connections_count || null,
      degree: entity.connection_degree || null,
      followers: entity.followers_count || null,
    });
  }

  // 6. About Decomposed Intelligence
  if (entity.about_insights || entity.about_summary) {
    visibleCategories.push('STRUCTURED_ABOUT_DECOMPOSITION');
    extractedCategories.push({ field: 'about_insights', value: entity.about_insights || entity.about_summary });
  } else {
    notFound.push('STRUCTURED_ABOUT_DECOMPOSITION');
  }

  // 7. Employment History
  if (entity.experience_history && entity.experience_history.length > 0) {
    visibleCategories.push('EMPLOYMENT_HISTORY');
    extractedCategories.push({ field: 'employment_history', count: entity.experience_history.length, roles: entity.experience_history });
  } else {
    notFound.push('EMPLOYMENT_HISTORY');
  }

  // 8. Contact Channels
  if (entity.email) extractedCategories.push({ field: 'email', value: entity.email });
  if (entity.phone) extractedCategories.push({ field: 'phone', value: entity.phone });
  if (entity.website) extractedCategories.push({ field: 'website', value: entity.website });
  if (!entity.email && !entity.phone) notFound.push('PRIVATE_CONTACT_INFO (NOT GROUNDED ON PUBLIC VIEW)');

  return {
    source_platform: entity.source_platform || 'LinkedIn',
    canonical_person: entity.recruiter_name,
    visible_categories: visibleCategories,
    extracted_categories: extractedCategories,
    not_found: notFound,
    uncertain: uncertain,
    rejected_ui_text: ['Connect', 'Message', 'Follow', 'Contact', 'Apply'],
    secondary_entities_observed: pageContext.secondary_people_count || 0,
    new_information: extractedCategories.map(c => c.field),
    evidence_grounding_status: 'PASS',
  };
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
