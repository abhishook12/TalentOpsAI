// ============================================================
// detector/indeed.js — Indeed Universal Context-Aware Detector
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectIndeed = function() {
  const host = location.hostname.toLowerCase();
  if (!host.includes('indeed.com')) return [];

  const ts = window.TalentScout;
  const results = [];

  // Extract Page-Level Company Context
  const pageCompany = ts.text([
    '[data-testid="inlineHeader-companyName"]',
    '.jobsearch-InlineCompanyRating-companyHeader',
    '.cmp-CompactHeaderTopInfo-name',
    'h1.cmp-Header-title',
    'h1',
  ]);

  // ── 1. Job Posting Page — Hiring Manager Section ──────────
  const hiringCards = document.querySelectorAll([
    '[data-testid="recruiter-info"]',
    '.recruitingCompanyName',
    '.hiring-manager',
    '[class*="HiringInsights"]',
    '.css-1wnkgqh',
  ].join(','));

  hiringCards.forEach(card => {
    const text = card.innerText || card.textContent || '';
    const name = _pickNameFromIndeedCard(card);
    const rawTitle = _pickTitleFromIndeedCard(card);
    const email = ts.extractEmail(text);
    const phone = ts.extractPhone(text);

    if (name || email) {
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
          source_platform: 'Indeed',
          email: email || null,
          phone: phone || null,
          source: 'indeed_job_posting',
          confidence: conf.overall,
          field_confidences: conf,
        });
      }
    }
  });

  // ── 2. Resume Search Results (Employer side) ──────────────
  const resumeCards = document.querySelectorAll('.resumeCard, [data-tn-element="result-item"], .ia-ResumeCard');
  resumeCards.forEach(card => {
    const name = card.querySelector('a.resumeTitle, .icl-u-lg-mr--sm, h2, h3')?.textContent?.trim();
    const rawTitle = card.querySelector('.title, .currentJobTitle, .resumeTitle + span, p')?.textContent?.trim();
    const location = card.querySelector('.location, .icl-u-xs-mt--xs')?.textContent?.trim();
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
        source_platform: 'Indeed',
        location: location || null,
        source: 'indeed_resume_search',
        confidence: conf.overall,
        field_confidences: conf,
      });
    }
  });

  return results;
};

function _pickNameFromIndeedCard(card) {
  const selectors = ['[class*="recruiterName"]', '.recruiterName', 'strong', 'b', 'h3', 'h4'];
  for (const sel of selectors) {
    const el = card.querySelector(sel);
    const t = el?.textContent?.trim();
    if (t && t.length < 60 && !t.includes('@') && !window.TalentScout.isUIAction(t)) return t;
  }
  return null;
}

function _pickTitleFromIndeedCard(card) {
  const selectors = ['[class*="title"]', '.jobTitle', 'span:nth-child(2)', 'p'];
  for (const sel of selectors) {
    const el = card.querySelector(sel);
    const t = el?.textContent?.trim();
    if (t && t.length < 80 && !window.TalentScout.isUIAction(t)) return t;
  }
  return null;
}
