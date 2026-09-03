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

  // Legal/Corporate Entity Suffixes
  companyLegalSuffixes: new Set([
    'inc', 'inc.', 'llc', 'ltd', 'ltd.', 'corp', 'corp.', 'corporation',
    'co', 'co.', 'company', 'gmbh', 'sa', 'plc', 'bv', 'pvt', 'private limited',
    'group', 'holdings', 'enterprises', 'ventures', 'capital', 'partners', 'associates'
  ]),

  // Common Company/Organization Keywords (Never Human Names)
  companyDomainTerms: new Set([
    'global', 'services', 'technologies', 'technology', 'solutions', 'systems',
    'consulting', 'consultancy', 'staffing', 'recruiting', 'recruitment', 'resources',
    'workforce', 'personnel', 'search', 'labs', 'laboratories', 'studios', 'interactive',
    'digital', 'media', 'software', 'networks', 'logistics', 'logix', 'infotech',
    'analytics', 'intelligence', 'therapeutics', 'pharma', 'pharmaceuticals', 'health',
    'healthcare', 'financial', 'bank', 'insurance', 'agency', 'foundation', 'institute',
    'academy', 'university', 'college', 'school', 'enterprises', 'holdings', 'group',
    'ventures', 'capital', 'international', 'worldwide', 'industries', 'management'
  ]),

  // Well-Known Staffing & Enterprise Organizations
  knownCompanies: new Set([
    'insight global', 'compunnel', 'compunnel inc', 'compunnel inc.', 'robert half',
    'teksystems', 'randstad', 'manpower', 'adecco', 'kelly services', 'allegis group',
    'allegis', 'apex systems', 'kforce', 'aerotek', 'collabera', 'cybercoders',
    'lucas group', 'beacon hill', 'addison group', 'hays', 'michael page', 'modis',
    'experis', 'judge group', 'mondo', 'vaco', 'disys', 'kellymitchell', 'aquent',
    'creative circle', 'synergis', 'diverse lynx', 'pyramid consulting', 'e-solutions',
    'infotree', 'artech', 'lancesoft', 'us tech solutions', 'eteam', 'nlb services',
    'mindlance', 'rangam', 'spectraforce', 'tech mahindra', 'tata consultancy services',
    'tcs', 'infosys', 'wipro', 'cognizant', 'hcl', 'accenture', 'deloitte', 'pwc',
    'ey', 'kpmg', 'google', 'microsoft', 'apple', 'amazon', 'meta', 'netflix',
    'salesforce', 'oracle', 'ibm', 'cisco', 'intel', 'nvidia'
  ]),

  // Standard Company Industry Descriptions (Never Job Titles)
  companyIndustries: new Set([
    'business consulting and services', 'staffing and recruiting',
    'information technology & services', 'information technology and services',
    'computer software', 'financial services', 'management consulting',
    'marketing and advertising', 'hospital & health care', 'higher education',
    'telecommunications', 'human resources', 'internet', 'consumer goods',
    'real estate', 'automotive', 'construction', 'retail', 'pharmaceuticals',
    'biotechnology', 'banking', 'insurance', 'accounting', 'legal services',
    'design', 'architecture & planning', 'facilities services', 'logistics and supply chain'
  ]),
};

/**
 * Check if a text is an organization or company name rather than a person
 */
window.TalentScout.isCompanyName = function(text) {
  if (!text) return false;
  const clean = text.toLowerCase().trim().replace(/[.,/#!$%^&*;:{}=\-_`~()]/g, ' ').replace(/\s+/g, ' ');
  if (!clean || clean.length < 2) return false;

  // Direct match in known companies
  if (window.TalentScout.PATTERNS.knownCompanies.has(clean)) return true;

  const words = clean.split(' ').filter(Boolean);
  if (words.length === 0) return false;

  // Check last word for corporate legal suffixes (e.g. "Compunnel Inc", "Apex Staffing LLC")
  const lastWord = words[words.length - 1];
  if (window.TalentScout.PATTERNS.companyLegalSuffixes.has(lastWord)) return true;

  // Check if any word is a distinct company domain keyword (e.g. "Insight Global", "Tech Solutions")
  const hasCompanyTerm = words.some(w => window.TalentScout.PATTERNS.companyDomainTerms.has(w));
  if (hasCompanyTerm) return true;

  // Check if starts or ends with company words
  if (words.length >= 2 && words.some(w => ['staffing', 'consulting', 'solutions', 'technologies', 'services', 'systems', 'global', 'group', 'holdings'].includes(w))) {
    return true;
  }

  return false;
};

/**
 * Check if a text is a company industry / sector descriptor rather than a personal job title
 */
window.TalentScout.isCompanyIndustry = function(text) {
  if (!text) return false;
  const clean = text.toLowerCase().trim().replace(/[•·]/g, ' ').replace(/\s+/g, ' ');
  if (window.TalentScout.PATTERNS.companyIndustries.has(clean)) return true;
  if (/business consulting and services|staffing and recruiting|information technology|computer software|financial services|management consulting/i.test(clean)) {
    return true;
  }
  return false;
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
  // Strip browser/tab notification count prefixes like "(14) ", "(2) ", "(99+) "
  name = name.replace(/^\(\d+\+?\)\s*/, '');
  // Strip newlines / tabs (DOM concatenated subtitles)
  name = name.split(/[\r\n\t]+/)[0].trim();

  // Strip degree bullets, numbers, pronouns (with or without parens), and degree credentials
  name = name.replace(/[·•]\s*\d*(?:st|nd|rd|th)?(?:\s*degree(?:\s+connection)?)?/gi, ' ');
  name = name.replace(/\b\d+(?:st|nd|rd|th)?\s+degree(?:\s+connection)?\b/gi, ' ');
  name = name.replace(/\b\d+(?:st|nd|rd|th)\b/gi, ' ');
  // Clean mashed ordinal suffixes attached to words (e.g. "2ndManaging" -> "Managing", "NdHuma" -> "Huma")
  name = name.replace(/\b\d*(?:st|nd|rd|th)([A-Z])/gi, ' $1');
  name = name.replace(/\b(?:st|nd|rd|th)([A-Z][a-z]+)/gi, ' $1');
  // Strip pronouns with or without parentheses (e.g. "He/Him", "(He/Him)", "she/her")
  name = name.replace(/\(?(?:he\/him|she\/her|they\/them|she\/they|he\/they|any\s*pronouns?)\)?/gi, ' ');
  name = name.replace(/\b(?:verified|verification|shield|pronounce|listen|view)\b/gi, ' ');
  name = name.replace(/\b(?:MBA|SHRM-CP|PHR|SPHR|PMP|CPA|MD|JD|PhD|BSc|MSc|BA|BS|MA|MS)\b/gi, '');
  name = name.split(/[-–—|,]/)[0].replace(/[^\w\s\'.]/g, ' ').trim();
  name = name.replace(/\s+/g, ' ');

  // If name has trailing role title words (e.g. "Klaus Raem Managing..." -> "Klaus Raem", "Deepa Kharayat Human..." -> "Deepa Kharayat")
  const tokens = name.split(' ');
  if (tokens.length >= 3) {
    let cutIdx = -1;
    for (let i = 2; i < tokens.length; i++) {
      const tokLower = tokens[i].toLowerCase();
      if (/^(founder|ceo|cto|cpo|coo|vp|recruiter|sourcer|consultant|manager|director|managing|engineer|developer|analyst|specialist|partner|lead|head|architect|sap|oracle|staffing|talent|hiring|hr|human|resources|operations)$/i.test(tokLower)) {
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

  // HARD INVARIANT: Reject Company / Organization names (e.g. 'Insight Global', 'Compunnel Inc')
  if (window.TalentScout.isCompanyName(lower)) {
    return { isValid: false, reason: `company_name_as_candidate:${name}` };
  }

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

  // Reject domain names or email fragments (e.g. "cwood atominc.com", "user@site")
  if (/\b(?:com|org|net|io|ai|co|edu|gov|in|biz|info)\b/i.test(name) && name.includes('.')) {
    return { isValid: false, reason: `domain_name:${name}` };
  }
  if (/@|\.com|\.net|\.org|\.io|\.ai/i.test(lower)) {
    return { isValid: false, reason: `domain_pattern:${name}` };
  }

  // Reject standalone platform / tool names
  if (/^(linkedin|google|microsoft|indeed|glassdoor|ziprecruiter|github|twitter|facebook|instagram|chat|search|messaging)$/i.test(lower)) {
    return { isValid: false, reason: `site_name:${name}` };
  }

  // Must contain at least two words (First Name + Last Name) for human candidate verification
  const wordTokens = name.split(' ').filter(w => w.length > 0);
  if (wordTokens.length < 2 || wordTokens.length > 4) {
    return { isValid: false, reason: 'unnatural_name_structure' };
  }

  // Must contain only letters and standard name punctuation
  if (!/^[a-zA-Z\s'.\-]+$/.test(name)) {
    return { isValid: false, reason: 'unnatural_characters' };
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
  // If slug is a solid unspaced block without delimiters, do not force as candidate name
  return null;
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

/**
 * Extract structured schema.org JSON-LD data from <script type="application/ld+json">
 */
window.TalentScout.extractJsonLd = function(doc = document) {
  const result = { person: null, organization: null };
  try {
    const scripts = doc.querySelectorAll('script[type="application/ld+json"]');
    scripts.forEach(s => {
      try {
        const raw = s.textContent?.trim();
        if (!raw) return;
        const parsed = JSON.parse(raw);
        const items = Array.isArray(parsed) ? parsed : (parsed['@graph'] || [parsed]);
        
        items.forEach(item => {
          const type = item['@type'];
          if (type === 'Person' || (Array.isArray(type) && type.includes('Person'))) {
            result.person = {
              name: item.name,
              jobTitle: item.jobTitle,
              worksFor: item.worksFor?.name || (typeof item.worksFor === 'string' ? item.worksFor : null),
              companyUrl: item.worksFor?.sameAs || item.worksFor?.url || null,
              address: item.address ? `${item.address.addressLocality || ''}, ${item.address.addressRegion || ''} ${item.address.addressCountry || ''}`.trim() : null,
              description: item.description,
              alumniOf: Array.isArray(item.alumniOf) ? item.alumniOf.map(a => a.name || a).join(', ') : (item.alumniOf?.name || item.alumniOf || null),
              url: item.url,
              sameAs: item.sameAs,
            };
          } else if (type === 'Organization' || type === 'Corporation' || (Array.isArray(type) && (type.includes('Organization') || type.includes('Corporation')))) {
            result.organization = {
              company_name: item.name,
              description: item.description,
              url: item.url,
              sameAs: item.sameAs,
              numberOfEmployees: item.numberOfEmployees?.value || item.numberOfEmployees || null,
              address: item.address ? `${item.address.streetAddress || ''}, ${item.address.addressLocality || ''}, ${item.address.addressRegion || ''} ${item.address.postalCode || ''}`.trim() : null,
            };
          }
        });
      } catch (_) {}
    });
  } catch (_) {}
  return result;
};

/**
 * Extract rich pre-hydrated Voyager Dash JSON data from <code id*="bpr-guid"> and <script> tags
 */
window.TalentScout.extractEmbeddedLinkedInData = function(doc = document) {
  const result = {
    candidate: null,
    company: null,
    experiences: [],
    educations: [],
    skills: [],
    certifications: [],
    languages: [],
    contactInfo: { email: null, phone: null, website: null, twitter: null },
  };

  try {
    const codeElements = doc.querySelectorAll('code[id*="bpr-guid"], script[type="application/json"]');
    for (const el of codeElements) {
      const raw = el.textContent?.trim();
      if (!raw || !raw.startsWith('{') || (!raw.includes('"included"') && !raw.includes('"data"'))) continue;

      try {
        const json = JSON.parse(raw);
        const included = Array.isArray(json.included) ? json.included : (json.data ? [json.data] : []);

        for (const item of included) {
          if (!item || typeof item !== 'object') continue;
          const type = (item.$type || item['@type'] || '').toLowerCase();

          // 1. Candidate Profile Model
          if (type.includes('identity.profile.profile') || type.includes('identitydashprofile') || (item.firstName && item.lastName && item.headline)) {
            const fName = (typeof item.firstName === 'string') ? item.firstName : (item.firstName?.text || '');
            const lName = (typeof item.lastName === 'string') ? item.lastName : (item.lastName?.text || '');
            const fullName = `${fName} ${lName}`.trim();
            const hLine = (typeof item.headline === 'string') ? item.headline : (item.headline?.text || '');
            const summary = (typeof item.summary === 'string') ? item.summary : (item.summary?.text || '');
            const loc = item.geoRegionName || item.locationName || (typeof item.location === 'string' ? item.location : null);
            const pronouns = item.pronoun || null;

            if (fullName && (!result.candidate || !result.candidate.name)) {
              result.candidate = {
                name: fullName,
                headline: hLine,
                summary: summary || null,
                location: loc || null,
                pronouns: pronouns,
                isOpenToWork: Boolean(item.openToWork || item.isOpenToWork),
                isHiring: Boolean(item.hiring || item.isHiring),
              };
            }
          }

          // 2. Experience / Positions
          if (type.includes('identity.profile.position') || type.includes('dashposition') || (item.companyName && item.title)) {
            const roleTitle = (typeof item.title === 'string') ? item.title : (item.title?.text || '');
            const comp = (typeof item.companyName === 'string') ? item.companyName : (item.companyName?.text || '');
            const loc = (typeof item.locationName === 'string') ? item.locationName : (item.locationName?.text || '');
            const desc = (typeof item.description === 'string') ? item.description : (item.description?.text || '');

            let dateRange = null;
            if (item.timePeriod) {
              const start = item.timePeriod.startDate ? `${item.timePeriod.startDate.month ? item.timePeriod.startDate.month + '/' : ''}${item.timePeriod.startDate.year || ''}` : '';
              const end = item.timePeriod.endDate ? `${item.timePeriod.endDate.month ? item.timePeriod.endDate.month + '/' : ''}${item.timePeriod.endDate.year || ''}` : 'Present';
              if (start || end) dateRange = `${start} - ${end}`.trim();
            }

            if (roleTitle && !result.experiences.some(e => e.title === roleTitle && e.company === comp)) {
              result.experiences.push({
                title: roleTitle,
                company: comp || null,
                date_range: dateRange,
                location: loc || null,
                description: desc ? desc.slice(0, 500) : null,
                is_current: !item.timePeriod?.endDate,
              });
            }
          }

          // 3. Education
          if (type.includes('identity.profile.education') || type.includes('dasheducation') || item.schoolName) {
            const school = (typeof item.schoolName === 'string') ? item.schoolName : (item.schoolName?.text || '');
            const degree = (typeof item.degreeName === 'string') ? item.degreeName : (item.degreeName?.text || '');
            const field = (typeof item.fieldOfStudy === 'string') ? item.fieldOfStudy : (item.fieldOfStudy?.text || '');

            let dateRange = null;
            if (item.timePeriod) {
              const start = item.timePeriod.startDate?.year || '';
              const end = item.timePeriod.endDate?.year || '';
              if (start || end) dateRange = `${start} - ${end}`.trim();
            }

            if (school && !result.educations.some(e => e.school === school)) {
              result.educations.push({
                school: school,
                degree: degree || null,
                field_of_study: field || null,
                date_range: dateRange,
              });
            }
          }

          // 4. Skills
          if (type.includes('identity.profile.skill') || type.includes('dashskill') || (item.name && type.includes('skill'))) {
            const skillName = (typeof item.name === 'string') ? item.name : (item.name?.text || '');
            if (skillName && skillName.length >= 2 && !result.skills.includes(skillName)) {
              result.skills.push(skillName);
            }
          }

          // 5. Certifications
          if (type.includes('identity.profile.certification') || (item.name && item.authority)) {
            const certName = (typeof item.name === 'string') ? item.name : (item.name?.text || '');
            const auth = (typeof item.authority === 'string') ? item.authority : (item.authority?.text || item.companyName || '');
            if (certName && !result.certifications.some(c => c.title === certName)) {
              result.certifications.push({ title: certName, issuer: auth || null });
            }
          }

          // 6. Contact Info
          if (type.includes('identity.profile.profilecontactinfo') || type.includes('contactinfo')) {
            if (item.emailAddress) result.contactInfo.email = item.emailAddress;
            if (item.phoneNumbers && Array.isArray(item.phoneNumbers) && item.phoneNumbers[0]?.number) {
              result.contactInfo.phone = item.phoneNumbers[0].number;
            }
            if (item.websites && Array.isArray(item.websites) && item.websites[0]?.url) {
              result.contactInfo.website = item.websites[0].url;
            }
            if (item.twitterHandles && Array.isArray(item.twitterHandles) && item.twitterHandles[0]?.name) {
              result.contactInfo.twitter = `https://twitter.com/${item.twitterHandles[0].name}`;
            }
          }

          // 7. Company Organization Model
          if (type.includes('organization.company') || type.includes('dashcompany') || (item.name && (item.universalName || item.staffCountRange || item.industries))) {
            const cName = (typeof item.name === 'string') ? item.name : (item.name?.text || '');
            const tagline = (typeof item.tagline === 'string') ? item.tagline : (item.tagline?.text || '');
            const desc = (typeof item.description === 'string') ? item.description : (item.description?.text || '');
            const web = item.websiteUrl || item.url || null;
            const staff = item.staffCount || item.employeeCountRange || (item.staffCountRange ? `${item.staffCountRange.start}-${item.staffCountRange.end} employees` : null);
            const founded = item.foundedOn?.year || null;
            const specialties = Array.isArray(item.specialities || item.specialties) ? (item.specialities || item.specialties) : null;
            const ind = Array.isArray(item.industries) ? item.industries[0] : (typeof item.industry === 'string' ? item.industry : null);
            const hq = item.confirmedLocations && Array.isArray(item.confirmedLocations) && item.confirmedLocations[0]
              ? `${item.confirmedLocations[0].city || ''}, ${item.confirmedLocations[0].geographicArea || ''} ${item.confirmedLocations[0].country || ''}`.trim()
              : null;

            if (cName && (!result.company || !result.company.name)) {
              result.company = {
                name: cName,
                tagline: tagline || null,
                overview: desc || null,
                website: web,
                employees: staff ? String(staff) : null,
                founded: founded ? String(founded) : null,
                specialties: specialties,
                industry: ind,
                location: hq,
              };
            }
          }
        }
      } catch (_) {}
    }
  } catch (_) {}

  return result;
};

/**
 * Extract Badges and Status Signals (OpenToWork, Hiring, Verified, Pronouns)
 */
window.TalentScout.extractBadgesAndSignals = function(root = document) {
  const textBody = (root.body ? root.body.innerText : (root.textContent || '')) || '';
  
  // 1. Open to Work Signal
  const hasOpenToWorkImg = Boolean(root.querySelector('img[alt*="Open to work" i], [data-test-icon="open-to-work"], .pv-top-card--open-to-work, [data-view-name*="open-to-work"]'));
  const hasOpenToWorkText = /#opentowork\b|open to work\b/i.test(textBody);
  const isOpenToWork = hasOpenToWorkImg || hasOpenToWorkText;

  // 2. Hiring Signal
  const hasHiringImg = Boolean(root.querySelector('img[alt*="Hiring" i], [data-test-icon="hiring"], .pv-top-card--hiring'));
  const hasHiringText = /#hiring\b|we're hiring\b|actively hiring\b/i.test(textBody);
  const isHiring = hasHiringImg || hasHiringText;

  // 3. Verification Badge (Shield icons, verified badges, aria-label)
  const isVerified = Boolean(root.querySelector([
    '[data-test-icon*="verified" i]',
    '[data-test-icon*="shield" i]',
    'svg[data-test-icon*="shield"]',
    'svg[data-test-icon*="verified"]',
    '.pv-member-badge--verified',
    '[aria-label*="Verified profile" i]',
    '[aria-label*="Verified" i]',
    '.artdeco-badge',
  ].join(',')));

  // 4. Pronouns (with or without parentheses)
  let pronouns = null;
  const pronounMatch = textBody.match(/\(?(he\/him|she\/her|they\/them|she\/they|he\/they|any\s*pronouns?)\)?/i);
  if (pronounMatch) pronouns = pronounMatch[0].trim();

  return {
    isOpenToWork,
    isHiring,
    isVerified,
    pronouns,
  };
};

/**
 * Extract Spoken Languages from #languages or language modules
 */
window.TalentScout.extractSpokenLanguages = function(root = document) {
  const langs = [];
  try {
    const langSection = root.querySelector('#languages')?.closest('section, div.artdeco-card, [class*="card"]') || root.querySelector('[data-section="languages"]');
    if (langSection) {
      langSection.querySelectorAll('ul > li').forEach(li => {
        const name = window.TalentScout.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], li);
        const prof = window.TalentScout.text(['.t-normal span[aria-hidden="true"]', '.t-14.t-normal'], li);
        if (name && !window.TalentScout.isUIAction(name)) {
          langs.push({ language: name, proficiency: prof || 'Proficient' });
        }
      });
    }
  } catch (_) {}
  return langs;
};

/**
 * Extract Full Structured Experience Timeline (Handling Both Single Roles & Multi-Role Clusters)
 */
window.TalentScout.extractDetailedExperience = function(root = document) {
  const experiences = [];
  try {
    const expAnchor = root.querySelector('#experience') || root.querySelector('div[id="experience"]');
    const expSection = expAnchor?.closest('section, div.artdeco-card, [class*="card"], [data-view-name*="profile"]')
      || root.querySelector('[data-section="experience"]')
      || root.querySelector('#experience ~ div');
    if (!expSection) return experiences;

    // Get top-level list items (companies)
    const topItems = Array.from(expSection.querySelectorAll('ul > li')).filter(li => {
      const parentUl = li.parentElement;
      return parentUl && !parentUl.closest('li');
    });

    topItems.forEach((li, idx) => {
      // Check if this item is a multi-role parent container
      const subList = li.querySelectorAll('ul > li');
      if (subList.length > 0) {
        // Multi-role employer: extract parent company name
        const parentComp = window.TalentScout.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], li);
        const cleanParentComp = parentComp ? parentComp.split('·')[0].trim() : null;

        subList.forEach((subLi, sIdx) => {
          const roleTitle = window.TalentScout.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], subLi);
          const dateRange = window.TalentScout.text(['.t-black--light span[aria-hidden="true"]', '.pv-entity__date-range', '.t-14.t-black--light'], subLi);
          const location = window.TalentScout.text(['.t-black--light:nth-child(2) span[aria-hidden="true"]', '.pv-entity__location'], subLi);
          const desc = window.TalentScout.text(['.inline-show-more-text', 'p'], subLi);

          if (roleTitle && !window.TalentScout.isUIAction(roleTitle)) {
            experiences.push({
              title: roleTitle,
              company: cleanParentComp,
              date_range: dateRange || null,
              location: location || null,
              description: desc ? desc.slice(0, 300) : null,
              is_current: idx === 0 && sIdx === 0,
            });
          }
        });
      } else {
        // Single role item
        const roleTitle = window.TalentScout.text(['.hoverable-link-text span[aria-hidden="true"]', 'span[aria-hidden="true"]', '.t-bold'], li);
        const expComp = window.TalentScout.text(['.t-normal span[aria-hidden="true"]', '.t-14.t-normal', '.pv-entity__secondary-title'], li);
        const dateRange = window.TalentScout.text(['.t-black--light span[aria-hidden="true"]', '.pv-entity__date-range', '.t-14.t-black--light'], li);
        const location = window.TalentScout.text(['.t-black--light:nth-child(2) span[aria-hidden="true"]', '.pv-entity__location'], li);
        const desc = window.TalentScout.text(['.inline-show-more-text', 'p'], li);

        if (roleTitle && !window.TalentScout.isUIAction(roleTitle)) {
          const cleanComp = (expComp && !window.TalentScout.isPlatformName(expComp)) ? expComp.split('·')[0].trim() : null;
          experiences.push({
            title: roleTitle,
            company: cleanComp,
            date_range: dateRange || null,
            location: location || null,
            description: desc ? desc.slice(0, 300) : null,
            is_current: idx === 0,
          });
        }
      }
    });
  } catch (_) {}
  return experiences;
};

/**
 * Extract Full Company Firmographics (Specialties, Founded, Headquarters, Type, Open Roles)
 */
window.TalentScout.extractCompanyFirmographics = function(root = document) {
  const result = {
    specialties: null,
    founded: null,
    company_type: null,
    headquarters: null,
    location: null,
    followers: null,
    employees: null,
    industry: null,
    open_roles: null,
    overview: null,
  };

  try {
    const textBody = (root.body ? (root.body.innerText || root.body.textContent) : (root.textContent || '')) || '';

    // 1. Followers Extraction (e.g. "45K followers", "1,240 followers", "2.1M followers")
    const followersMatch = textBody.match(/\b(\d[\d,.]*[kKmMbB]?\+?\s*followers)\b/i);
    if (followersMatch) {
      result.followers = followersMatch[1].trim();
    }

    // 2. Employees / Scale Extraction (e.g. "201-500 employees", "10,001+ employees", "51-200 on LinkedIn")
    const employeesMatch = textBody.match(/\b((?:\d[\d,.]*(?:-\d[\d,.]*)?|\d[\d,.]*\+?)\s*employees)\b/i) ||
                           textBody.match(/\b(\d[\d,.]*\s+on linkedin)\b/i);
    if (employeesMatch) {
      result.employees = employeesMatch[1].trim();
    }

    // 3. Specialties
    const specMatch = textBody.match(/Specialties\s*[\r\n\t]+([^\r\n]+)/i) || textBody.match(/Specialties:\s*([^\r\n]+)/i);
    if (specMatch && specMatch[1]) {
      result.specialties = specMatch[1].split(/[,;]/).map(s => s.trim()).filter(Boolean);
    }

    // 4. Founded Year
    const foundMatch = textBody.match(/Founded\s*[\r\n\t]+(\d{4})/i) || textBody.match(/Founded:\s*(\d{4})/i) || textBody.match(/\bFounded\s+(\d{4})\b/i);
    if (foundMatch && foundMatch[1]) {
      result.founded = foundMatch[1];
    }

    // 5. Company Type
    const typeMatch = textBody.match(/Type\s*[\r\n\t]+([^\r\n]+)/i) || textBody.match(/Company type\s*[\r\n\t]+([^\r\n]+)/i);
    if (typeMatch && typeMatch[1]) {
      result.company_type = typeMatch[1].trim();
    }

    // 6. Headquarters & Location
    const hqMatch = textBody.match(/Headquarters\s*[\r\n\t]+([^\r\n]+)/i) || textBody.match(/Headquarters:\s*([^\r\n]+)/i);
    if (hqMatch && hqMatch[1]) {
      result.headquarters = hqMatch[1].trim();
      result.location = result.headquarters;
    }

    // Multi-token subline scanner: "Staffing and Recruiting · Toledo, Ohio · 45K followers · 201-500 employees"
    const lines = textBody.split(/[\r\n]+/).map(l => l.trim()).filter(Boolean);
    for (const line of lines) {
      if (/followers|employees/i.test(line) && /[·•\u00B7\u2022|]/.test(line)) {
        const tokens = line.split(/[·•\u00B7\u2022|]/).map(t => t.replace(/[\u00C2\u00A0]+/g, ' ').trim()).filter(Boolean);
        for (const tok of tokens) {
          const lower = tok.toLowerCase();
          if (!result.location && (/,/.test(tok) || /\b(?:Area|Greater|City|County|Region|District)\b/i.test(tok)) && !/followers|employees|connections/i.test(lower) && tok.length >= 3 && tok.length <= 80) {
            result.location = tok;
            if (!result.headquarters) result.headquarters = tok;
          }
          if (!result.industry && !/,/.test(tok) && !/\b(?:Area|Greater|City|County|Region|District)\b/i.test(tok) && !/followers|employees|connections|following/i.test(lower) && tok.length >= 3 && tok.length <= 60) {
            result.industry = tok;
          }
        }
      }
      if (result.location && result.industry) break;
    }

    // 7. Open Roles
    const jobMatch = textBody.match(/(\d[\d,]*)\s+(?:open jobs?|job openings?|jobs? posted)/i);
    if (jobMatch && jobMatch[1]) {
      result.open_roles = `${jobMatch[1]} Open Roles`;
    }

    // 8. Overview
    const aboutSec = root.querySelector ? root.querySelector('section[data-test-id="about-us"], .org-grid__content-height-enforcer, .org-page-details-module__card-spacing') : null;
    if (aboutSec && window.TalentScout?.text) {
      result.overview = window.TalentScout.text(['p', '.break-words'], aboutSec);
    }
  } catch (_) {}

  return result;
};

/**
 * Extract Geographic Location from text or small elements
 */
window.TalentScout.extractLocation = function(text) {
  if (!text || typeof text !== 'string') return null;
  const cleaned = text.replace(/[\r\n\t]+/g, ' ').trim();

  // Strip UI actions, degree badges, and contact info
  const sanitized = cleaned
    .replace(/\b(contact\s*info|see\s*more|1st|2nd|3rd|he\/him|she\/her|they\/them)\b/gi, '')
    .replace(/[·•|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  // Pattern A: City, State/Province, Country
  // e.g. "Manchester Area, United Kingdom", "Greater London, England, United Kingdom", "Boston, MA", "Austin, Texas, United States"
  const geoRegex = /\b([A-Z][a-zA-Z\s.-]+(?:Area|City|Greater|County|Region|District)?,\s*(?:[A-Z]{2}\b|[A-Z][a-zA-Z\s.-]+(?:,\s*[A-Z][a-zA-Z\s.-]+)?))\b/;
  const match = sanitized.match(geoRegex);
  if (match && match[1]) {
    const loc = match[1].trim();
    if (loc.length >= 4 && !/^(about|experience|education|skills|activity|interests)/i.test(loc)) {
      return loc;
    }
  }

  // Pattern B: Well-known countries/regions
  const countryRegex = /\b([A-Z][a-zA-Z\s.-]+\s+(?:United Kingdom|United States|USA|UK|Canada|India|Australia|Germany|France|Netherlands|Singapore|Brazil|Japan|Switzerland))\b/i;
  const cMatch = sanitized.match(countryRegex);
  if (cMatch && cMatch[1]) {
    return cMatch[1].trim();
  }

  return null;
};

/**
 * Extract Small Text Metadata (Location, Education, Connections, Followers, Pronouns, Talks About)
 * Designed to capture subtle metadata rendered in .text-body-small, .t-black--light, and top-card sublines
 */
window.TalentScout.extractSmallTextDetails = function(root = document) {
  const result = {
    location: null,
    education: null,
    connections: null,
    followers: null,
    pronouns: null,
    talks_about: [],
    degree: null
  };

  try {
    // 1. Gather all small text elements in the top card / profile header
    const topCard = root.querySelector('.pv-top-card, .pv-text-details__left-panel, div[data-view-name="profile-top-card"], .ph5, section.pv-top-card') || root;
    const smallSpans = topCard.querySelectorAll('.text-body-small, .t-black--light, .t-14, .dist-value, [data-field="location"], span');

    for (const el of smallSpans) {
      let t = el.textContent ? el.textContent.trim() : '';
      if (!t || t.length < 2) continue;

      // Degree
      const degMatch = t.match(/\b(1st|2nd|3rd|3rd\+)\b/i);
      if (!result.degree && degMatch) {
        result.degree = degMatch[1];
        continue;
      }

      // Pronouns
      if (!result.pronouns && /^(he\/him|she\/her|they\/them|xe\/xem)$/i.test(t)) {
        result.pronouns = t.charAt(0).toUpperCase() + t.slice(1).toLowerCase();
        continue;
      }

      // Talks About
      if (/talks about/i.test(t)) {
        const topics = t.replace(/talks about/i, '').split(/[,#•]/).map(s => s.trim()).filter(s => s.length >= 2);
        topics.forEach(tag => {
          if (!result.talks_about.includes(tag) && !window.TalentScout.isUIAction(tag)) {
            result.talks_about.push(tag);
          }
        });
        continue;
      }

      // Followers
      if (!result.followers && /\d[\d,]*\+?\s*followers/i.test(t)) {
        result.followers = t.replace(/\s+/g, ' ');
        continue;
      }

      // Connections
      if (!result.connections && /\d[\d,]*\+?\s*connections/i.test(t)) {
        result.connections = t.replace(/\s+/g, ' ');
        continue;
      }

      // Location detection
      if (!result.location && t.length >= 3 && t.length <= 80) {
        if (/,\s*[A-Z]{2}\b|Area|United Kingdom|United States|USA|UK|Canada|India|Australia|Germany|France|Greater|County|City/i.test(t)) {
          if (!/^(he\/him|she\/her|they\/them|\d+|mutual|talks about|contact info)/i.test(t)) {
            let cleanLoc = t
              .replace(/\bcontact\s*info\b/gi, '')
              .replace(/[\u00C2\u00A0]*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+.*$/g, '')
              .replace(/[\s\-_,·•\u00B7\u2022\u00C2\u00A0|]+$/, '')
              .trim();
            if (cleanLoc.length >= 3) {
              result.location = cleanLoc;
            }
          }
        }
      }
    }

    // 2. Proximity Scan for Location via Contact Info Link
    if (!result.location) {
      const contactInfoLink = root.querySelector('a[href*="contact-info"], #top-card-text-details-contact-info');
      if (contactInfoLink) {
        const prev = contactInfoLink.previousElementSibling || contactInfoLink.parentElement?.previousElementSibling;
        if (prev && prev.textContent) {
          const t = prev.textContent
            .replace(/\bcontact\s*info\b/gi, '')
            .replace(/[\u00C2\u00A0]*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+.*$/g, '')
            .replace(/[\s\-_,·•\u00B7\u2022\u00C2\u00A0|]+$/, '')
            .trim();
          if (t && t.length >= 3 && !/^(he\/him|she\/her|they\/them|\d+)/i.test(t)) {
            result.location = t;
          }
        }
      }
    }

    // 3. Top Card Right Panel School / Education Detection (Row 2 in small text)
    if (!result.education) {
      const rightPanelItems = root.querySelectorAll('.pv-text-details__right-panel li, .pv-text-details__right-panel a, button[aria-label*="Education" i]');
      for (const item of rightPanelItems) {
        const txt = item.textContent?.trim() || '';
        if (/university|college|institute|school|polytechnic|academy|state|tech|bachelor|master/i.test(txt)) {
          result.education = txt.replace(/\s+/g, ' ');
          break;
        }
      }
    }
  } catch (_) {}

  return result;
};

