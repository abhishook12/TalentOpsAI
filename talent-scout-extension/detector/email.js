// ============================================================
// detector/email.js — Gmail & Outlook Web email signature parser
// Watches open emails for recruiter contact info in signatures
// ============================================================

window.TalentScout = window.TalentScout || {};

window.TalentScout.detectEmail = function() {
  const host = location.hostname;
  const ts = window.TalentScout;

  // ── Gmail ──────────────────────────────────────────────────
  if (host.includes('mail.google.com')) {
    return _scrapeGmail();
  }

  // ── Outlook Web (outlook.live.com, outlook.office.com) ────
  if (host.includes('outlook.live.com') || host.includes('outlook.office.com') || host.includes('outlook.office365.com')) {
    return _scrapeOutlookWeb();
  }

  // ── Yahoo Mail ─────────────────────────────────────────────
  if (host.includes('mail.yahoo.com')) {
    return _scrapeYahooMail();
  }

  return [];
};

// ── Gmail ───────────────────────────────────────────────────

function _scrapeGmail() {
  const ts = window.TalentScout;
  const results = [];

  // All visible email threads currently expanded
  const emailBodies = document.querySelectorAll('.a3s.aiL, .gmail_quote, [data-message-id]');

  emailBodies.forEach(body => {
    const fullText = body.innerText || body.textContent || '';

    // Extract sender from the "from" header area near this email body
    const msgRow = body.closest('.adn, .gs');
    let senderName = null;
    let senderEmail = null;

    if (msgRow) {
      const fromEl = msgRow.querySelector('.gD, .go, [email]');
      senderEmail = fromEl?.getAttribute('email') || ts.extractEmail(fromEl?.textContent || '');
      senderName = fromEl?.getAttribute('name') || fromEl?.textContent?.trim();
    }

    // Parse signature block — usually after -- or lines with name+title+company pattern
    const sigBlock = _extractSignatureBlock(fullText);
    if (!sigBlock && !senderEmail) return;

    const sigEmail = ts.extractEmail(sigBlock || fullText);
    const sigPhone = ts.extractPhone(sigBlock || fullText);
    const sigLinkedIn = ts.extractLinkedIn(sigBlock || fullText);
    const { name: sigName, title: sigTitle, company: sigCompany } = _parseNameTitleCompany(sigBlock || fullText);

    const finalEmail = sigEmail || senderEmail;
    const finalName = sigName || senderName;

    if (!finalEmail && !finalName) return;

    results.push({
      recruiter_name: ts.normalizeName(finalName),
      email: finalEmail || null,
      phone: sigPhone || null,
      title: sigTitle || null,
      company_name: sigCompany || null,
      linkedin_url: sigLinkedIn || null,
      source: 'gmail_signature',
    });
  });

  return _deduplicateByEmail(results);
}

// ── Outlook Web ─────────────────────────────────────────────

function _scrapeOutlookWeb() {
  const ts = window.TalentScout;
  const results = [];

  // Reading pane — open email body
  const emailBody = document.querySelector('[aria-label="Message body"], .rps_f8f1, [data-app-section="MessageBody"]');
  if (!emailBody) return results;

  const fullText = emailBody.innerText || emailBody.textContent || '';

  // Sender info from the mail header card
  const senderCard = document.querySelector('.ms-Persona-primaryText, [aria-label*="From"] .ms-Persona, .allowTextSelection');
  const senderName = senderCard?.querySelector('.ms-Persona-primaryText, .allowTextSelection')?.textContent?.trim();
  const senderEmailEl = document.querySelector('[aria-label*="From"] [title*="@"]');
  const senderEmail = senderEmailEl ? senderEmailEl.getAttribute('title') : ts.extractEmail(senderCard?.textContent || '');

  const sigBlock = _extractSignatureBlock(fullText);
  const sigEmail = ts.extractEmail(sigBlock || fullText);
  const sigPhone = ts.extractPhone(sigBlock || fullText);
  const sigLinkedIn = ts.extractLinkedIn(sigBlock || fullText);
  const { name: sigName, title: sigTitle, company: sigCompany } = _parseNameTitleCompany(sigBlock || fullText);

  const finalEmail = sigEmail || senderEmail;
  const finalName = sigName || senderName;

  if (finalEmail || finalName) {
    results.push({
      recruiter_name: ts.normalizeName(finalName),
      email: finalEmail || null,
      phone: sigPhone || null,
      title: sigTitle || null,
      company_name: sigCompany || null,
      linkedin_url: sigLinkedIn || null,
      source: 'outlook_signature',
    });
  }

  return results;
}

// ── Yahoo Mail ───────────────────────────────────────────────

function _scrapeYahooMail() {
  const ts = window.TalentScout;
  const results = [];

  const emailBody = document.querySelector('[data-test-id="message-body"], .msg-body');
  if (!emailBody) return results;

  const fullText = emailBody.innerText || '';
  const sigBlock = _extractSignatureBlock(fullText);
  const sigEmail = ts.extractEmail(sigBlock || fullText);
  const sigPhone = ts.extractPhone(sigBlock || fullText);
  const sigLinkedIn = ts.extractLinkedIn(sigBlock || fullText);
  const { name: sigName, title: sigTitle, company: sigCompany } = _parseNameTitleCompany(sigBlock || fullText);

  if (sigEmail || sigName) {
    results.push({
      recruiter_name: ts.normalizeName(sigName),
      email: sigEmail || null,
      phone: sigPhone || null,
      title: sigTitle || null,
      company_name: sigCompany || null,
      linkedin_url: sigLinkedIn || null,
      source: 'yahoo_mail_signature',
    });
  }

  return results;
}

// ── Signature Extraction Helpers ─────────────────────────────

/**
 * Heuristically extract signature block from email body text.
 * Signatures usually appear after --, Best regards, Thanks, Sincerely, etc.
 */
function _extractSignatureBlock(text) {
  const sigMarkers = [
    /^--+\s*$/m,
    /^Best\s+regards?[,.]?\s*$/im,
    /^Kind\s+regards?[,.]?\s*$/im,
    /^Thanks[!,.]?\s*$/im,
    /^Thank\s+you[!,.]?\s*$/im,
    /^Sincerely[,.]?\s*$/im,
    /^Warm\s+regards?[,.]?\s*$/im,
    /^Cheers[,.]?\s*$/im,
    /^Regards?[,.]?\s*$/im,
  ];

  for (const marker of sigMarkers) {
    const match = text.match(marker);
    if (match) {
      const sigStart = text.lastIndexOf(match[0]);
      const sig = text.slice(sigStart + match[0].length).trim();
      if (sig.length > 10 && sig.length < 1000) return sig;
    }
  }

  // If no marker found, take last 300 chars (often where signature is)
  const tail = text.slice(-400).trim();
  return tail.length > 20 ? tail : null;
}

/**
 * Parse name, title, company from a signature block using line heuristics.
 * First line → name, second → title, third → company (usually)
 */
function _parseNameTitleCompany(text) {
  if (!text) return { name: null, title: null, company: null };

  const lines = text.split('\n')
    .map(l => l.replace(/\s+/g, ' ').trim())
    .filter(l => l.length > 1 && l.length < 80)
    .filter(l => !l.match(/^https?:\/\//))  // exclude URLs
    .filter(l => !l.match(/^[\d\s\-()+]+$/)) // exclude phone-only lines
    .slice(0, 6);

  const name = lines[0] || null;
  const title = lines[1] || null;
  const company = lines[2] || null;

  return { name, title, company };
}

function _deduplicateByEmail(results) {
  const seen = new Set();
  return results.filter(r => {
    const key = r.email || r.linkedin_url || r.recruiter_name;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
