import React, { useState, useEffect } from 'react'

const overlayStyles = `
  .splash-overlay {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: center;
    background: var(--bg-primary, #ffffff);
    color: var(--text-primary, #111111);
    transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), visibility 0.4s;
    opacity: 0;
    visibility: hidden;
    padding: 40px 24px;
    box-sizing: border-box;
  }

  [data-theme="dark"] .splash-overlay {
    background: #111111;
    color: #ffffff;
  }

  .splash-overlay.is-visible {
    opacity: 1;
    visibility: visible;
  }

  /* This starts near the top to mimic the form pushing it up, then animates down to true center */
  .splash-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    max-width: 440px;
    margin-top: 12vh;
    transform-origin: top center;
    animation: splash-transform-down 1s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  }

  /* BRAND HEADER MATCHING AuthFrame.jsx */
  .splash-brand-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    margin-bottom: 48px;
  }

  .splash-monogram {
    font-family: "Playfair Display", "Times New Roman", Times, serif;
    font-size: 64px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    margin-bottom: 32px;
  }
  
  .splash-monogram span:nth-child(1) { margin-right: 8px; }
  .splash-monogram span:nth-child(2) { margin-left: 8px; font-weight: 400; }

  .splash-logo-divider {
    width: 1px;
    height: 72px;
    background: var(--text-primary, #111111);
    opacity: 0.2;
  }
  [data-theme="dark"] .splash-logo-divider { background: #ffffff; }

  .splash-wordmark {
    font-size: 36px;
    font-weight: 500;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-bottom: 16px;
    margin-right: -0.3em;
  }

  .splash-sub-brand {
    font-size: 13px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text-secondary, #666666);
    margin-bottom: 12px;
    margin-right: -0.15em;
  }
  [data-theme="dark"] .splash-sub-brand { color: #a0a0a0; }

  .splash-tiny-divider {
    width: 40px;
    height: 1px;
    background: var(--text-secondary, #666666);
    opacity: 0.3;
    margin-bottom: 12px;
  }
  [data-theme="dark"] .splash-tiny-divider { background: #a0a0a0; }

  .splash-credit {
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-tertiary, #999999);
    margin-right: -0.12em;
  }
  [data-theme="dark"] .splash-credit { color: #777777; }

  /* LOADING INDICATORS */
  .splash-loader-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    opacity: 0;
    animation: splash-fade-in-delay 0.8s ease forwards 0.6s;
    width: 100%;
  }

  .splash-progress-container {
    width: 280px;
    height: 2px;
    background: rgba(0, 0, 0, 0.05);
    overflow: hidden;
    position: relative;
  }
  [data-theme="dark"] .splash-progress-container { background: rgba(255, 255, 255, 0.08); }

  .splash-progress-bar {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: var(--text-primary, #111);
    transition: width 0.3s ease-out;
  }
  [data-theme="dark"] .splash-progress-bar { background: #ffffff; }
  
  .splash-progress-bar.indeterminate {
    width: 30%;
    animation: splash-progress-indeterminate 1.5s infinite ease-in-out;
  }

  .splash-status {
    font-size: 13px;
    color: var(--text-secondary, #666666);
    letter-spacing: 0.02em;
    font-weight: 400;
  }
  [data-theme="dark"] .splash-status { color: #a0a0a0; }

  @keyframes splash-transform-down {
    0% { transform: translateY(0) scale(1); }
    100% { transform: translateY(12vh) scale(1.02); }
  }

  @keyframes splash-fade-in-delay {
    0% { opacity: 0; transform: translateY(4px); }
    100% { opacity: 1; transform: translateY(0); }
  }

  @keyframes splash-progress-indeterminate {
    0% { left: -30%; right: 100%; }
    50% { left: 30%; right: 30%; }
    100% { left: 100%; right: -30%; }
  }
`

const STATUS_MESSAGES = [
  "Preparing your workspace...",
  "Loading your recruiters...",
  "Connecting your profile...",
  "Verifying security...",
  "Initializing dashboard..."
]

export default function AppLoadingOverlay({ isVisible, progress = null, statusText = null }) {
  const [internalStatus, setInternalStatus] = useState(STATUS_MESSAGES[0])
  const [msgIndex, setMsgIndex] = useState(0)
  
  useEffect(() => {
    if (!isVisible) return
    
    const interval = setInterval(() => {
      setMsgIndex((prev) => {
        const next = (prev + 1) % STATUS_MESSAGES.length
        if (!statusText) setInternalStatus(STATUS_MESSAGES[next])
        return next
      })
    }, 2000)
    
    return () => clearInterval(interval)
  }, [isVisible, statusText])

  const [shouldRender, setShouldRender] = useState(isVisible)
  
  useEffect(() => {
    if (isVisible) setShouldRender(true)
    else {
      const timer = setTimeout(() => setShouldRender(false), 400)
      return () => clearTimeout(timer)
    }
  }, [isVisible])

  if (!shouldRender) return null

  const displayStatus = statusText || internalStatus

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: overlayStyles }} />
      <div className={`splash-overlay ${isVisible ? 'is-visible' : ''}`}>
        
        <div className="splash-content">
          
          <div className="splash-brand-header">
            <div className="splash-monogram">
              <span>T</span>
              <div className="splash-logo-divider"></div>
              <span>O</span>
            </div>
            <div className="splash-wordmark">TALENT OPS</div>
            
            <div className="splash-sub-brand">A PRODUCT BY TECHNOVION</div>
            <div className="splash-tiny-divider"></div>
            <div className="splash-credit">BUILT BY ABHISHEK</div>
          </div>
          
          <div className="splash-loader-wrap">
            <div className="splash-progress-container">
              <div 
                className={`splash-progress-bar ${progress === null ? 'indeterminate' : ''}`}
                style={progress !== null ? { width: `${progress}%` } : {}}
              />
            </div>
            <div className="splash-status" key={displayStatus}>
              {displayStatus}
            </div>
          </div>

        </div>

      </div>
    </>
  )
}
