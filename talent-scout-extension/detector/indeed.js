// ============================================================
// detector/indeed.js — Indeed job postings & employer pages
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectIndeed = function() {
  const host = location.hostname;
  if (!host.includes('indeed.com')) return [];

  const ts = window.TalentScout;
  const results = [];

  // ── 1. Job Posting Page — Hiring Manager Section ──────────
  const hiringCards = document.querySelectorAll([
    '[data-testid="recruiter-info"]',
    '.recruitingCompanyName',
    '.hiring-manager',
    '[class*="HiringInsights"]',
    '.css-1wnkgqh', // Indeed hiring insights section
  ].join(','));

  hiringCards.forEach(card => {
    const text = card.innerText || card.textContent || '';
    const name = _pickNameFromIndeedCard(card);
    const title = _pickTitleFromIndeedCard(card);
    const email = ts.extractEmail(text);
    const phone = ts.extractPhone(text);

    if (name || email) {
      results.push({
        recruiter_name: ts.normalizeName(name),
        title: title || null,
        email: email || null,
        phone: phone || null,
        company_name: _pickCompanyFromPage(),
        source: 'indeed_job_posting',
      });
    }
  });

  // ── 2. Company Profile Page ────────────────────────────────
  if (location.pathname.includes('/cmp/')) {
    const companyName = document.querySelector('h1')?.textContent?.trim();
    const contactSection = document.querySelector('[data-tn-section="company-contact"], .cmp-contact');
    if (contactSection) {
      const text = contactSection.innerText || contactSection.textContent || '';
      const email = ts.extractEmail(text);
      const phone = ts.extractPhone(text);
      if (email || phone) {
        results.push({
          company_name: companyName,
          email: email || null,
          phone: phone || null,
          source: 'indeed_company_page',
        });
      }
    }
  }

  // ── 3. Resume Search Results (Employer side) ──────────────
  const resumeCards = document.querySelectorAll('.resumeCard, [data-tn-element="result-item"]');
  resumeCards.forEach(card => {
    const name = card.querySelector('a.resumeTitle, .icl-u-lg-mr--sm')?.textContent?.trim();
    const title = card.querySelector('.title, .currentJobTitle, .resumeTitle + span')?.textContent?.trim();
    const location = card.querySelector('.location, .icl-u-xs-mt--xs')?.textContent?.trim();
    if (!name) return;
    results.push({
      recruiter_name: ts.normalizeName(name),
      title: title || null,
      location: location || null,
      source: 'indeed_resume_search',
    });
  });

  return results;
};

function _pickNameFromIndeedCard(card) {
  const selectors = ['[class*="recruiterName"]', '.recruiterName', 'strong', 'b', 'h3', 'h4'];
  for (const sel of selectors) {
    const el = card.querySelector(sel);
    const t = el?.textContent?.trim();
    if (t && t.length < 60 && !t.includes('@')) return t;
  }
  return null;
}

function _pickTitleFromIndeedCard(card) {
  const selectors = ['[class*="title"]', '.jobTitle', 'span:nth-child(2)', 'p'];
  for (const sel of selectors) {
    const el = card.querySelector(sel);
    const t = el?.textContent?.trim();
    if (t && t.length < 80) return t;
  }
  return null;
}

function _pickCompanyFromPage() {
  const selectors = [
    '[data-company-name]',
    '.company',
    '[class*="CompanyName"]',
    'h2[data-testid="jobsearch-JobInfoHeader-companyName"]',
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    const t = el?.textContent?.trim() || el?.getAttribute('data-company-name');
    if (t) return t;
  }
  return null;
}
