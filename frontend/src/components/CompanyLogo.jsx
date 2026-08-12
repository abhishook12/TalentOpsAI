import { useState, useEffect } from 'react'
import { normalizeLogoDomain } from '../utils/domain'

export function CompanyLogo({ domain, name, logo_url, size = 32, style = {} }) {
  const [errorLevel, setErrorLevel] = useState(0)
  const initial = name && name !== "Unknown / Individual" ? name.charAt(0).toUpperCase() : '?'

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

  useEffect(() => {
    setErrorLevel(0) // reset if props change
  }, [domain, name, logo_url])

  // If it's explicitly unknown/unresolved
  if (name === "Unknown / Individual" || (!cleanDomain && !logo_url)) {
    return <div style={fallbackStyle}>{initial}</div>
  }

  // 4-Tier Logo Service Cascade:
  // Level 0: Verified logo from Backend canonical identity
  // Level 1: Clearbit fallback (if no backend logo_url provided, try clearbit directly)
  // Level 2: Google Favicon v2 (Reliable fallback for almost all web servers, scalable)
  // Level 3: DuckDuckGo Favicons
  
  let currentLogo = null
  
  if (errorLevel === 0 && logo_url) {
    currentLogo = logo_url
  } else if (errorLevel === 0 && !logo_url) {
    // Skip to clearbit if we don't have a verified logo url
    currentLogo = `https://logo.clearbit.com/${cleanDomain}?size=${size * 4}`
  } else if (errorLevel === 1) {
    // If we had logo_url but it failed, or clearbit failed
    currentLogo = `https://logo.clearbit.com/${cleanDomain}?size=${size * 4}`
  } else if (errorLevel === 2) {
    currentLogo = `https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://${cleanDomain}&size=${size * 4}`
  } else if (errorLevel === 3) {
    currentLogo = `https://icons.duckduckgo.com/ip3/${cleanDomain}.ico`
  }

  if (errorLevel >= 4 || !currentLogo) {
    return <div style={fallbackStyle}>{initial}</div>
  }

  return (
    <img
      src={currentLogo}
      alt={`${name || domain} logo`}
      onError={() => setErrorLevel(prev => prev + 1)}
      style={{
        width: size,
        height: size,
        borderRadius: 12,
        objectFit: 'cover',
        backgroundColor: '#ffffff',
        border: '1px solid #4b5563',
        ...style
      }}
    />
  )
}
