// ============================================================
// detector/ziprecruiter.js — ZipRecruiter job page extractor
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectZipRecruiter = function() {
  const host = location.hostname;
  if (!host.includes('ziprecruiter.com')) return [];

  const ts = window.TalentScout;
  const results = [];

  // Recruiter card at the top of job detail
  const recruiterCard = document.querySelector([
    '.hiring_company',
    '[class*="HiringCompany"]',
    '.job_location',
    '[class*="RecruiterCard"]',
    '.employer-card',
    '[data-testid="job-description-header"]',
  ].join(','));

  const company = ts.text([
    'a[class*="t_org_link"]',
    '[class*="company_name"]',
    '[class*="HiringCompanyName"]',
    'h2',
  ].join(','));

  if (recruiterCard) {
    const text = recruiterCard.innerText || recruiterCard.textContent || '';
    const email = ts.extractEmail(text);
    const phone = ts.extractPhone(text);
    const name = _extractRecruiterName(recruiterCard);

    if (name || email) {
      results.push({
        recruiter_name: ts.normalizeName(name),
        company_name: company || null,
        email: email || null,
        phone: phone || null,
        source: 'ziprecruiter_job',
      });
    }
  }

  // Candidate search results (employer-side)
  const candidateCards = document.querySelectorAll('[class*="candidate_card"], [class*="CandidateListItem"]');
  candidateCards.forEach(card => {
    const name = ts.text('[class*="candidate_name"], h3, h4', card);
    const title = ts.text('[class*="job_title"], [class*="headline"]', card);
    const location = ts.text('[class*="location"]', card);
    if (!name) return;
    results.push({
      recruiter_name: ts.normalizeName(name),
      title: title || null,
      location: location || null,
      source: 'ziprecruiter_candidates',
    });
  });

  return results;
};

function _extractRecruiterName(card) {
  const selectors = ['[class*="recruiter"]', 'strong', 'b', 'h3', 'h4'];
  for (const sel of selectors) {
    const el = card.querySelector(sel);
    const t = el?.textContent?.trim();
    if (t && t.length < 60 && !t.includes('@')) return t;
  }
  return null;
}
