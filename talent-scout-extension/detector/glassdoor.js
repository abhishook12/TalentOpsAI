// ============================================================
// detector/glassdoor.js — Glassdoor employer & recruiter extractor
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectGlassdoor = function() {
  const host = location.hostname;
  if (!host.includes('glassdoor.com')) return [];

  const ts = window.TalentScout;
  const results = [];

  // ── 1. Job Listing Page ─────────────────────────────────
  const jobTitle = ts.text([
    '[data-test="job-title"]',
    '.e1tk4kwz4',
    'h1',
  ].join(','));

  const company = ts.text([
    '[data-test="employer-name"]',
    '.e1tk4kwz4 + div',
    '[class*="EmployerName"]',
    'h2',
  ].join(','));

  // Recruiter info on glassdoor can be in "Meet the recruiter" or "Employer profile" sections
  const recruiterSection = document.querySelector([
    '[data-test="recruiter-section"]',
    '[class*="HiringInsights"]',
    '.recruiter-section',
    '[class*="jobApplicationGuidance"]',
  ].join(','));

  if (recruiterSection) {
    const text = recruiterSection.innerText || recruiterSection.textContent || '';
    const nameEl = recruiterSection.querySelector('a, strong, b, h3, h4');
    const name = nameEl?.textContent?.trim();
    const email = ts.extractEmail(text);
    const phone = ts.extractPhone(text);
    const linkedin = ts.extractLinkedIn(recruiterSection.innerHTML || '');

    if (name || email) {
      results.push({
        recruiter_name: ts.normalizeName(name),
        company_name: company || null,
        email: email || null,
        phone: phone || null,
        linkedin_url: linkedin || null,
        source: 'glassdoor_job',
      });
    }
  }

  // ── 2. Company Review Page — HR Response Authors ─────────
  const hrResponders = document.querySelectorAll([
    '[data-test="employer-response"] .author',
    '.employer-response .employer-name',
    '[class*="EmployerResponse"] [class*="Name"]',
  ].join(','));

  hrResponders.forEach(el => {
    const name = el.textContent?.trim();
    if (name && name.length < 60) {
      results.push({
        recruiter_name: ts.normalizeName(name),
        company_name: company || null,
        source: 'glassdoor_company_review',
      });
    }
  });

  return results;
};
