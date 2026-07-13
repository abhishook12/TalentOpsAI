import React, { useState } from 'react'

const blockedLogoDomains = new Set([
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

const knownStaffingDomains = {
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

function inferDomainFromName(name) {
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

function normalizeLogoDomain(domain, name) {
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
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('/')[0]

  if (!cleaned || blockedLogoDomains.has(cleaned) || cleaned.includes('.dup.')) {
    return inferDomainFromName(name)
  }

  return cleaned
}

export function CompanyLogo({ domain, name, size = 32, style = {} }) {
  const [errorLevel, setErrorLevel] = useState(0)
  const initial = name ? name.charAt(0).toUpperCase() : '?'

  const cleanDomain = normalizeLogoDomain(domain, name)

  const fallbackStyle = {
    width: size,
    height: size,
    minWidth: size,
    borderRadius: 6,
    backgroundColor: '#374151',
    color: '#9ca3af',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: '600',
    fontSize: size * 0.45,
    border: '1px solid #4b5563',
    ...style
  }

  if (!cleanDomain || errorLevel >= 4) {
    return <div style={fallbackStyle}>{initial}</div>
  }

  // 4-Tier Logo Service Cascade:
  // Level 0: Clearbit (High resolution corporate logos, transparent PNGs)
  // Level 1: Google Favicon v2 (Reliable fallback for almost all web servers, scalable)
  // Level 2: DuckDuckGo Favicons (Covers millions of domains including smaller consulting firms)
  // Level 3: Favicon.im (Final catch-all scraper)
  let logoUrl = `https://logo.clearbit.com/${cleanDomain}?size=${size * 4}`
  if (errorLevel === 1) {
    logoUrl = `https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://${cleanDomain}&size=${size * 4}`
  } else if (errorLevel === 2) {
    logoUrl = `https://icons.duckduckgo.com/ip3/${cleanDomain}.ico`
  } else if (errorLevel === 3) {
    logoUrl = `https://favicon.im/${cleanDomain}?larger=true`
  }

  return (
    <img
      src={logoUrl}
      alt={`${name} logo`}
      onError={() => setErrorLevel(prev => prev + 1)}
      style={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: 6,
        objectFit: 'contain',
        backgroundColor: '#fff',
        border: '1px solid #4b5563',
        ...style
      }}
    />
  )
}
