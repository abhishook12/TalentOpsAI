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

function normalizeLogoDomain(domain) {
  if (!domain) return null
  const cleaned = String(domain)
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('/')[0]

  if (!cleaned || blockedLogoDomains.has(cleaned)) {
    return null
  }

  return cleaned
}

export function CompanyLogo({ domain, name, size = 32, style = {} }) {
  const [errorLevel, setErrorLevel] = useState(0)
  const initial = name ? name.charAt(0).toUpperCase() : '?'

  const cleanDomain = normalizeLogoDomain(domain)

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
  // Level 0: DuckDuckGo Favicons (Fast, covers millions of domains including smaller consulting firms)
  // Level 1: Clearbit (High resolution corporate logos)
  // Level 2: Google Favicon v2 (Reliable fallback for almost all web servers)
  // Level 3: Favicon.im (Final catch-all scraper)
  let logoUrl = `https://icons.duckduckgo.com/ip3/${cleanDomain}.ico`
  if (errorLevel === 1) {
    logoUrl = `https://logo.clearbit.com/${cleanDomain}?size=${size * 4}`
  } else if (errorLevel === 2) {
    logoUrl = `https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://${cleanDomain}&size=${size * 4}`
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
