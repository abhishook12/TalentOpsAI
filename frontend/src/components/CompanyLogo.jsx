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

  // 5-Tier Logo Service Cascade (High-Quality, Free, No Auth):
  // Level 0: Verified logo from Backend canonical identity
  // Level 1: Hunter.io — free, no auth, high-res PNG logos
  // Level 2: Tomba.io — free, no auth, high-res with sizing  
  // Level 3: CompanyEnrich — free, no auth, transparent PNG
  // Level 4: Google Favicon v2 (reliable fallback)
  // Level 5: DuckDuckGo Favicons (last resort)
  
  const urls = []
  if (logo_url) urls.push(logo_url)
  urls.push(`https://logos.hunter.io/${cleanDomain}`)
  urls.push(`https://logo.tomba.io/${cleanDomain}?size=${Math.max(size * 4, 128)}`)
  urls.push(`https://api.companyenrich.com/logo/${cleanDomain}`)
  urls.push(`https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://${cleanDomain}&size=${Math.max(size * 4, 128)}`)
  urls.push(`https://icons.duckduckgo.com/ip3/${cleanDomain}.ico`)
  
  const uniqueUrls = [...new Set(urls)]
  let currentLogo = null
  if (errorLevel < uniqueUrls.length) {
    currentLogo = uniqueUrls[errorLevel]
  }

  if (errorLevel >= 5 || !currentLogo) {
    return <div style={fallbackStyle}>{initial}</div>
  }

  return (
    <img
      src={currentLogo}
      alt={`${name || domain} logo`}
      loading="lazy"
      onError={() => setErrorLevel(prev => prev + 1)}
      style={{
        width: size,
        height: size,
        borderRadius: 10,
        objectFit: 'contain',
        backgroundColor: '#ffffff',
        border: '1px solid #4b5563',
        padding: 2,
        imageRendering: 'auto',
        ...style
      }}
    />
  )
}
