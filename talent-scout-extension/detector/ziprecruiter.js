// ============================================================
// detector/ziprecruiter.js — ZipRecruiter Universal Detector
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectZipRecruiter = function() {
  const host = location.hostname.toLowerCase();
  if (!host.includes('ziprecruiter.com')) return [];

  const ts = window.TalentScout;
  const results = [];

  // Page-Level Company Context
  const pageCompany = ts.text([
    'a[class*="t_org_link"]',
    '[class*="company_name"]',
    '[class*="HiringCompanyName"]',
    'h2.company-name',
    'h2',
  ]);

  // Recruiter card at the top of job detail
  const recruiterCards = document.querySelectorAll([
    '.hiring_company',
    '[class*="HiringCompany"]',
    '.job_location',
    '[class*="RecruiterCard"]',
    '.employer-card',
    '[data-testid="job-description-header"]',
  ].join(','));

  recruiterCards.forEach(card => {
    const text = card.innerText || card.textContent || '';
    const email = ts.extractEmail(text);
    const phone = ts.extractPhone(text);
    const name = _extractRecruiterName(card);
    const finalName = ts.normalizeName(name);

    if (finalName || email) {
      const { title, company_name } = ts.cleanTitleAndCompany(null, null, pageCompany);
      const conf = ts.calculateFieldConfidences({
        recruiter_name: finalName,
        title: title,
        company_name: company_name,
      });

      results.push({
        recruiter_name: finalName || 'ZipRecruiter Lead',
        title: title || 'Talent Acquisition',
        company_name: company_name,
        source_platform: 'ZipRecruiter',
        email: email || null,
        phone: phone || null,
        source: 'ziprecruiter_job',
        confidence: conf.overall,
        field_confidences: conf,
      });
    }
  });

  // Candidate search results (employer-side)
  const candidateCards = document.querySelectorAll('[class*="candidate_card"], [class*="CandidateListItem"]');
  candidateCards.forEach(card => {
    const name = ts.text('[class*="candidate_name"], h3, h4', card);
    const rawTitle = ts.text('[class*="job_title"], [class*="headline"]', card);
    const location = ts.text('[class*="location"]', card);
    const finalName = ts.normalizeName(name);

    if (finalName && !ts.isUIAction(finalName)) {
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
        source_platform: 'ZipRecruiter',
        location: location || null,
        source: 'ziprecruiter_candidates',
        confidence: conf.overall,
        field_confidences: conf,
      });
    }
  });

  return results;
};

function _extractRecruiterName(card) {
  const selectors = ['[class*="recruiter"]', 'strong', 'b', 'h3', 'h4'];
  for (const sel of selectors) {
    const el = card.querySelector(sel);
    const t = el?.textContent?.trim();
    if (t && t.length < 60 && !t.includes('@') && !window.TalentScout.isUIAction(t)) return t;
  }
  return null;
}
