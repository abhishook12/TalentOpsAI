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
  'actalent': 'actalenttalent.com',
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
    .split(/[\s;|]+/)[0]
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('/')[0]

  if (!cleaned || blockedLogoDomains.has(cleaned) || cleaned.includes('.dup.')) {
    return inferDomainFromName(name)
  }

  return cleaned
}
