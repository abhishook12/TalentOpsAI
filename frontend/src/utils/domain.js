export const blockedLogoDomains = new Set([
  'apollo.io',
  'crunchbase.com',
  'facebook.com',
  'glassdoor.com',
  'hasdic.org',
  'indeed.com',
  'linkedin.com',
  'rocketreach.co',
  'signalhire.com',
  'twitter.com',
  'wikipedia.org',
  'x.com',
  'zoominfo.com',
])

export const knownStaffingDomains = {
  'airswift': 'airswift.com',
  'air swift': 'airswift.com',
  'tekpartners': 'tekpartners.com',
  'tek partners': 'tekpartners.com',
  'robert half': 'roberthalf.com',
  'insight global': 'insightglobal.com',
  '3ci': '3ci.tech',
  'teksystems': 'teksystems.com',
  'kforce': 'kforce.com',
  'beacon hill': 'beaconhillstaffing.com',
  'beacon hill staffing group': 'beaconhillstaffing.com',
  'apex systems': 'apexsystems.com',
  'randstad': 'randstadusa.com',
  'adecco': 'adeccousa.com',
  'kelly services': 'kellyservices.com',
  'kelly': 'kellyservices.com',
  'manpower': 'manpowergroup.com',
  'manpowergroup': 'manpowergroup.com',
  'actalent': 'actalent.com',
  'actalent services': 'actalentservices.com',
  'optomi': 'optomi.com',
  'cybercoders': 'cybercoders.com',
  'bairesdev': 'bairesdev.com',
  'toptal': 'toptal.com',
  'oxford global resources': 'oxfordcorp.com',
  'modis': 'modis.com',
  'akkodis': 'akkodis.com',
  'judge group': 'judge.com',
  'the judge group': 'judge.com',
  'collabera': 'collabera.com',
  'matrix resources': 'matrixres.com',
  'eliassen group': 'eliassen.com',
  'addison group': 'addisongroup.com',
  'hays': 'hays.com',
  'lucas group': 'lucasgroup.com',
  'korn ferry': 'kornferry.com',
  'heidrick & struggles': 'heidrick.com',
  'spencer stuart': 'spencerstuart.com',
  'russell reynolds': 'russellreynolds.com',
  'egon zehnder': 'egonzehnder.com',
  'michael page': 'michaelpage.com',
  'pagegroup': 'page.com',
  'robert walters': 'robertwalters.com',
  'allegis group': 'allegisgroup.com',
  'aston carter': 'astoncarter.com',
  'aerotek': 'aerotek.com',
  'guidant global': 'guidantglobal.com',
  'impellam': 'impellam.com',
  'amn healthcare': 'amnhealthcare.com',
  'cross country healthcare': 'crosscountryhealthcare.com',
  'chg healthcare': 'chghealthcare.com',
  'jackson healthcare': 'jacksonhealthcare.com',
  'aya healthcare': 'ayahealthcare.com',
  'favorite healthcare staffing': 'favoritestaffing.com',
  'medical solutions': 'medicalsolutions.com',
  'maxim healthcare': 'maximhealthcare.com',
  'hiregenics': 'hiregenics.com',
  'pontoon': 'pontoonsolutions.com',
  'us navy': 'navy.mil',
  'u.s. navy': 'navy.mil',
  'us army': 'army.mil',
  'u.s. army': 'army.mil',
  'us air force': 'af.mil',
  'u.s. air force': 'af.mil',
  'accenture': 'accenture.com',
  'deloitte': 'deloitte.com',
  'pwc': 'pwc.com',
  'kpmg': 'kpmg.com',
  'ey': 'ey.com',
  'capgemini': 'capgemini.com',
  'cognizant': 'cognizant.com',
  'tcs': 'tcs.com',
  'infosys': 'infosys.com',
  'wipro': 'wipro.com',
  'hcltech': 'hcltech.com',
  'tech mahindra': 'techmahindra.com',
  'ibm': 'ibm.com',
  'microsoft': 'microsoft.com',
  'google': 'google.com',
  'amazon': 'amazon.com',
  'meta': 'meta.com',
  'apple': 'apple.com',
  'netflix': 'netflix.com',
  'stand 8': 'stand8.io',
  'stand8': 'stand8.io',
  'talonpro': 'talonpro.com',
  'anagh technologies': 'anaghtech.com',
  'anagh technologies inc': 'anaghtech.com',
  'anaghtech': 'anaghtech.com',
  'amanda cucinotti': 'medasource.com',
  'medasource': 'medasource.com',
  'russelltobin': 'russelltobin.com',
  'russell tobin': 'russelltobin.com',
  'kellymitchell': 'kellymitchell.com',
  'kelly mitchell': 'kellymitchell.com',
  'brooksource': 'brooksource.com',
  'kellyscientific': 'kellyscientific.com',
  'kelly scientific': 'kellyscientific.com',
  'cisco': 'cisco.com',
  'oracle': 'oracle.com',
  'salesforce': 'salesforce.com',
  'workday': 'workday.com',
  'servicenow': 'servicenow.com'
}

export function inferDomainFromName(name) {
  if (!name) return null
  const clean = String(name).trim().toLowerCase().replace(/\[duplicate\]\s*/gi, '').trim()
  if (knownStaffingDomains[clean]) {
    return knownStaffingDomains[clean]
  }
  for (const [k, v] of Object.entries(knownStaffingDomains)) {
    if (clean.includes(k) && k.length > 3) return v
  }
  const stripped = clean.replace(/\b(llc|inc|corp|corporation|company|group|limited|ltd|solutions|technologies|services|staffing|global)\b/gi, '').replace(/[^a-z0-9]/g, '')
  if (stripped && stripped.length >= 3 && !/^\d+$/.test(stripped)) {
    return `${stripped}.com`
  }
  return null
}

export function normalizeLogoDomain(domain, name) {
  let target = domain
  if (!target || target === 'null' || target === 'n/a') {
    target = inferDomainFromName(name)
  }
  if (!target) return null
  const cleaned = String(target)
    .trim()
    .toLowerCase()
    .replace(/\.dup\.\d+$/i, '')
    .replace(/\.\.dup\.\d+$/i, '')
    .replace(/\[duplicate\]\s*/gi, '')
    // Aggressively split off any garbage text that got scraped into the DB (e.g. "url | user", "url; name", "url ... text")
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('/')[0]

  if (!cleaned || blockedLogoDomains.has(cleaned) || cleaned.includes('.dup.')) {
    return inferDomainFromName(name)
  }

  return cleaned
}

export const domainToDisplayName = {
  'roberthalf.com': 'Robert Half',
  'insightglobal.com': 'Insight Global',
  'teksystems.com': 'TEKsystems',
  'randstadusa.com': 'Randstad',
  'beaconhillstaffing.com': 'Beacon Hill Staffing Group',
  'kforce.com': 'Kforce',
  'aerotek.com': 'Aerotek',
  'apexsystems.com': 'Apex Systems',
  'oxfordcorp.com': 'Oxford Global Resources',
  'kellyservices.com': 'Kelly Services',
  'cybercoders.com': 'CyberCoders',
  'manpower.com': 'Manpower',
  'manpowergroup.com': 'ManpowerGroup',
  'bluestonestaffing.com': 'Bluestone Staffing',
  'bluestonesg.com': 'Bluestone SG',
  'mribluestone.com': 'MRI Bluestone',
  'bluestone-llc.com': 'Bluestone LLC',
  'motionrecruitment.com': 'Motion Recruitment',
  'signatureconsultants.com': 'Signature Consultants',
  'entegee.com': 'Entegee',
  'elitetechnical.com': 'Elite Technical',
  'refactortalent.com': 'Refactor Talent',
  'connection.com': 'Connection',
  'cullertongroup.com': 'Cullerton Group',
  'gotoagile.com': 'GoToAgile',
  'hirenetworks.com': 'HireNetworks',
  'technovion.com': 'Technovion',
}

const COMMON_COMPANY_SUFFIX_WORDS = [
  'group', 'technical', 'talent', 'staffing', 'solutions', 'technologies',
  'consulting', 'recruiting', 'partners', 'media', 'digital', 'services',
  'capital', 'global', 'labs', 'networks', 'systems', 'associates',
  'resources', 'personnel', 'search', 'advisors', 'international'
]

export function inferCompanyNameFromDomain(domain) {
  if (!domain) return null
  const d = String(domain).trim().toLowerCase()
  if (domainToDisplayName[d]) return domainToDisplayName[d]
  
  let base = d.replace(/\.(com|net|org|io|co|ai|us|ca|tech|info|biz|global|llc|co\.uk)$/, '')
  base = base.replace(/^(mail|corp|web|app)\./, '')
  
  // Try splitting compound words if no delimiter exists
  if (!/[-_.]/.test(base) && base.length > 7) {
    for (const suffix of COMMON_COMPANY_SUFFIX_WORDS) {
      if (base.endsWith(suffix) && base.length > suffix.length) {
        const prefix = base.slice(0, base.length - suffix.length)
        base = `${prefix} ${suffix}`
        break
      }
    }
  }

  const words = base.split(/[-_.\s]+/)
  const result = words
    .filter(Boolean)
    .map(w => ['sg', 'it', 'llc', 'inc', 'corp', 'hr', 'ai', 'us', 'uk', 'ca'].includes(w.toLowerCase()) ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
  return result || null
}

export const PUBLIC_EMAIL_DOMAINS = new Set([
  'gmail.com', 'googlemail.com', 'yahoo.com', 'ymail.com', 'hotmail.com',
  'outlook.com', 'live.com', 'msn.com', 'icloud.com', 'me.com', 'aol.com',
  'protonmail.com', 'proton.me', 'zoho.com', 'mail.com', 'gmx.com',
  'noemail.talentops', 'unknown.com', 'noemail.com', 'test.com', 'example.com'
])

/**
 * Analyzes recipient list in real-time to identify if a single dominant company exists.
 * Returns { companyName, domain, count, total, percentage, isSoleCompany } or null.
 */
export function detectDominantCompany(recipients) {
  if (!recipients || !Array.isArray(recipients) || recipients.length === 0) return null

  const counts = new Map()
  let corporateTotal = 0

  for (const r of recipients) {
    if (!r) continue
    let companyName = (r.company || r.company_name || '').trim()
    const rawEmail = (r.email || '').trim().toLowerCase()
    const domain = rawEmail.includes('@') ? rawEmail.split('@')[1].trim().toLowerCase() : null

    if (domain && PUBLIC_EMAIL_DOMAINS.has(domain)) {
      continue
    }

    if (!companyName && domain) {
      companyName = inferCompanyNameFromDomain(domain)
    }

    if (companyName && !['Unknown', 'Independent', 'N/A', 'None'].includes(companyName)) {
      corporateTotal++
      const existing = counts.get(companyName) || { count: 0, domain, companyName }
      existing.count += 1
      if (!existing.domain && domain) existing.domain = domain
      counts.set(companyName, existing)
    }
  }

  if (counts.size === 0 || corporateTotal === 0) return null

  let topCompany = null
  for (const item of counts.values()) {
    if (!topCompany || item.count > topCompany.count) {
      topCompany = item
    }
  }

  if (!topCompany) return null

  const percentage = Math.round((topCompany.count / corporateTotal) * 100)

  // Dominant criteria: sole corporate entity OR >= 50% majority OR (>= 3 count and >= 40%)
  if (counts.size === 1 || percentage >= 50 || (topCompany.count >= 3 && percentage >= 40)) {
    return {
      companyName: topCompany.companyName,
      domain: topCompany.domain,
      count: topCompany.count,
      total: corporateTotal,
      percentage,
      isSoleCompany: counts.size === 1
    }
  }

  return null
}

