import { useState, memo } from 'react'
import { normalizeLogoDomain, inferCompanyNameFromDomain } from '../utils/domain'

const failedDomains = new Set()

export const CompanyIdentity = memo(function CompanyIdentity({ 
  domain, 
  name, 
  logo_url,
  subtitle, 
  metadata, 
  size = 40, 
  logoSize = 32,
  interactive = true,
  style = {}
}) {
  const [errorLevel, setErrorLevel] = useState(0)
  const [isHovered, setIsHovered] = useState(false)

  const cleanDomain = normalizeLogoDomain(domain, name)
  const formatDisplayName = (n) => {
    if (!n || n === 'Unknown Company' || n === 'null' || /^\d+$/.test(String(n).trim())) {
      if (cleanDomain) {
        return inferCompanyNameFromDomain(cleanDomain) || 'Unknown Company'
      }
      return 'Unknown Company'
    }
    const raw = String(n).trim()
    if (raw === raw.toLowerCase()) {
      return raw.split(/[-_]+/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
    }
    return raw
  }
  const displayName = formatDisplayName(name)
  
  const getInitials = (n) => {
    if (!n) return '?'
    const words = n.trim().split(' ')
    if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
    return n.substring(0, 2).toUpperCase()
  }
  const initials = getInitials(displayName)

  let currentLogo = null
  
  if (cleanDomain && !failedDomains.has(cleanDomain)) {
    const urls = []
    if (logo_url) urls.push(logo_url)
    // Tier 1: Hunter.io — free, no auth, high-res PNG logos
    urls.push(`https://logos.hunter.io/${cleanDomain}`)
    // Tier 2: Tomba.io — free, no auth, high-res with sizing
    urls.push(`https://logo.tomba.io/${cleanDomain}?size=${Math.max(logoSize * 4, 128)}`)
    // Tier 3: CompanyEnrich — free, no auth, transparent PNG
    urls.push(`https://api.companyenrich.com/logo/${cleanDomain}`)
    // Tier 4: Google Favicon (reliable but lower quality)
    urls.push(`https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://${cleanDomain}&size=${Math.max(logoSize * 4, 128)}`)
    // Tier 5: DuckDuckGo (last resort)
    urls.push(`https://icons.duckduckgo.com/ip3/${cleanDomain}.ico`)
    
    const uniqueUrls = [...new Set(urls)]
    if (errorLevel < uniqueUrls.length) {
      currentLogo = uniqueUrls[errorLevel]
    }
  }

  const containerStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    padding: interactive ? '8px 12px' : 0,
    borderRadius: 6,
    background: isHovered && interactive ? 'rgba(255,255,255,0.03)' : 'transparent',
    border: isHovered && interactive ? '1px solid var(--card-border)' : '1px solid transparent',
    transform: isHovered && interactive ? 'translateY(-1px)' : 'translateY(0)',
    transition: 'background 150ms var(--ease-out), border-color 150ms var(--ease-out), transform 150ms var(--ease-out)',
    cursor: interactive ? 'pointer' : 'default',
    ...style
  }

  const monogramContainerStyle = {
    width: size,
    height: size,
    minWidth: size,
    borderRadius: 8,
    background: 'var(--bg-elevated, var(--panel-bg))',
    border: '1px solid var(--card-border)',
    color: 'var(--text-secondary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    fontSize: size * 0.4,
    fontWeight: 600,
    letterSpacing: '0.02em',
    padding: 8
  }

  return (
    <div 
      style={containerStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Logo Render */}
      {currentLogo ? (
        <img 
          src={currentLogo} 
          alt={`${displayName} logo`}
          loading="lazy"
          style={{ 
            width: size, 
            height: size, 
            minWidth: size,
            borderRadius: 10, 
            objectFit: 'contain',
            background: '#ffffff',
            border: '1px solid var(--card-border)',
            flexShrink: 0,
            padding: 3,
            imageRendering: 'auto'
          }}
          onError={() => {
            if (cleanDomain && errorLevel >= 4) failedDomains.add(cleanDomain)
            setErrorLevel(prev => prev + 1)
          }}
        />
      ) : (
        <div style={monogramContainerStyle}>
          {initials}
        </div>
      )}

      {/* Typography */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em', lineHeight: 1.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {displayName}
        </div>
        
        {subtitle && (
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {subtitle}
          </div>
        )}
        
        {metadata && (
          <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {metadata}
          </div>
        )}
      </div>
    </div>
  )
})
