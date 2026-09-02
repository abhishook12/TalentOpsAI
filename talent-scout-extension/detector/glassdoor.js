// ============================================================
// detector/glassdoor.js — Glassdoor Universal Context-Aware Detector
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectGlassdoor = function() {
  const host = location.hostname.toLowerCase();
  if (!host.includes('glassdoor.com')) return [];

  const ts = window.TalentScout;
  const results = [];

  // Page-Level Company Context
  const pageCompany = ts.text([
    '[data-test="employer-name"]',
    '.e1tk4kwz4 + div',
    '[class*="EmployerName"]',
    'h1.employer-name',
    'h2',
  ]);

  // ── 1. Job Listing Page — Recruiter Section ─────────────
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
    const finalName = ts.normalizeName(name);

    if (finalName || email) {
      const { title, company_name } = ts.cleanTitleAndCompany(null, null, pageCompany);
      const conf = ts.calculateFieldConfidences({
        recruiter_name: finalName,
        title: title,
        company_name: company_name,
      });

      results.push({
        recruiter_name: finalName || 'Glassdoor Hiring Lead',
        title: title || 'Hiring Lead',
        company_name: company_name,
        source_platform: 'Glassdoor',
        email: email || null,
        phone: phone || null,
        linkedin_url: linkedin || null,
        source: 'glassdoor_job',
        confidence: conf.overall,
        field_confidences: conf,
      });
    }
  }

  // ── 2. Company Review Page — HR Responders ───────────────
  const hrResponders = document.querySelectorAll([
    '[data-test="employer-response"] .author',
    '.employer-response .employer-name',
    '[class*="EmployerResponse"] [class*="Name"]',
  ].join(','));

  hrResponders.forEach(el => {
    const rawName = el.textContent?.trim();
    const finalName = ts.normalizeName(rawName);
    if (finalName && !ts.isUIAction(finalName)) {
      const { title, company_name } = ts.cleanTitleAndCompany('HR Lead / Representative', null, pageCompany);
      const conf = ts.calculateFieldConfidences({
        recruiter_name: finalName,
        title: title,
        company_name: company_name,
      });

      results.push({
        recruiter_name: finalName,
        title: title,
        company_name: company_name,
        source_platform: 'Glassdoor',
        source: 'glassdoor_company_review',
        confidence: conf.overall,
        field_confidences: conf,
      });
    }
  });

  return results;
};
