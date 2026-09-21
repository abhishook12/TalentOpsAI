import React from 'react'

const shellStyles = `
  .auth-page {
    min-height: 100dvh;
    display: flex;
    width: 100vw;
    background: #101014; /* Dark theme */
    color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  /* LEFT BRAND PANEL */
  .auth-brand-panel {
    flex: 1;
    position: relative;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: radial-gradient(circle at center, var(--brand-bg) 0%, rgba(16, 16, 20, 1) 60%), #101014;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    overflow: hidden;
  }

  @media (min-width: 900px) {
    .auth-brand-panel {
      display: flex;
    }
  }

  /* MOBILE BRANDING (Visible only < 900px) */
  .auth-mobile-brand {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 32px;
  }
  
  .auth-mobile-brand .auth-monogram {
    font-size: 48px;
    margin-bottom: 16px;
  }
  
  .auth-mobile-brand .auth-logo-divider {
    height: 48px;
    margin: 0 12px;
  }
  
  .auth-mobile-brand .auth-wordmark {
    font-size: 16px;
    letter-spacing: 0.35em;
    margin-bottom: 0;
  }
  
  @media (min-width: 900px) {
    .auth-mobile-brand {
      display: none;
    }
  }

  /* Ambient purple glow behind logo */
  .auth-ambient-glow {
    position: absolute;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, var(--brand-bg) 0%, transparent 70%);
    border-radius: 50%;
    z-index: 0;
  }

  .auth-brand-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .auth-monogram {
    font-family: "Playfair Display", "Times New Roman", Times, serif;
    font-size: 72px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    margin-bottom: 24px;
    color: #ffffff;
  }

  .auth-logo-divider {
    width: 1px;
    height: 72px;
    background: #ffffff;
    opacity: 0.3;
    margin: 0 16px;
  }

  .auth-wordmark {
    font-size: 32px;
    font-weight: 600;
    letter-spacing: 0.35em;
    text-transform: uppercase;
    margin-bottom: 32px;
    margin-right: -0.35em; 
    color: #ffffff;
  }

  .auth-sub-brand {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 8px;
    margin-right: -0.2em;
  }
  
  .auth-tiny-divider {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.4);
    margin-bottom: 8px;
  }

  .auth-credit {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.6);
    margin-right: -0.2em;
  }

  /* RIGHT FORM PANEL */
  .auth-form-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 24px;
    background: #141419;
  }

  .auth-form-container {
    width: 100%;
    max-width: 400px;
    padding: 40px;
    border-radius: 6px;
    border: 1px solid var(--card-border, #333);
    box-shadow: 0 24px 60px rgba(0,0,0,0.4);
    background: #1a1a1a;
    transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  }

  @media (max-width: 480px) {
    .auth-form-container {
      padding: 24px;
    }
  }

  .auth-form-container.is-authenticating {
    opacity: 0.95;
    pointer-events: none;
  }

  /* Scoped Auth Input Precision & Dark Theme Contrast */
  .auth-form-container input[type="email"],
  .auth-form-container input[type="password"],
  .auth-form-container input[type="text"],
  .auth-form-container select {
    background-color: #141418 !important;
    color: #ffffff !important;
    border: 1px solid #2e2e38 !important;
    border-radius: 8px !important;
    padding-left: 16px !important;
    padding-right: 16px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    height: 44px !important;
    min-height: 44px !important;
    line-height: 44px !important;
    font-size: 14px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
  }

  /* When an icon is present on the left */
  .auth-form-container .relative:has(> i:first-child) input,
  .auth-form-container input.pl-10 {
    padding-left: 42px !important;
  }

  /* When an icon/button is present on the right */
  .auth-form-container .relative:has(> button) input,
  .auth-form-container input.pr-10 {
    padding-right: 42px !important;
  }

  .auth-form-container input[type="email"]::placeholder,
  .auth-form-container input[type="password"]::placeholder,
  .auth-form-container input[type="text"]::placeholder {
    color: #71717a !important;
  }

  .auth-form-container input[type="email"]:focus,
  .auth-form-container input[type="password"]:focus,
  .auth-form-container input[type="text"]:focus,
  .auth-form-container select:focus {
    border-color: #ffffff !important;
    box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.1) !important;
  }

  /* Browser Autofill Dark Mode Hardening */
  .auth-form-container input:-webkit-autofill,
  .auth-form-container input:-webkit-autofill:hover, 
  .auth-form-container input:-webkit-autofill:focus,
  .auth-form-container input:-webkit-autofill:active {
    -webkit-box-shadow: 0 0 0 1000px #141418 inset !important;
    -webkit-text-fill-color: #ffffff !important;
    caret-color: #ffffff !important;
    transition: background-color 5000s ease-in-out 0s !important;
    border-color: #2e2e38 !important;
  }

  .auth-form-container input[type="checkbox"] {
    all: revert !important;
    accent-color: #ffffff !important;
    width: 16px !important;
    height: 16px !important;
    min-height: 16px !important;
    margin: 0 !important;
    padding: 0 !important;
    cursor: pointer !important;
  }
`

export default function AuthFrame({ children, isAuthenticating }) {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: shellStyles }} />
      <div className="auth-page">
        
        {/* Left Brand Panel (Hidden on mobile, visible on desktop) */}
        <div className="auth-brand-panel">
          <div className="auth-ambient-glow"></div>
          <div className="auth-brand-content">
            <div className="auth-monogram">
              <span>T</span>
              <div className="auth-logo-divider"></div>
              <span>O</span>
            </div>
            <div className="auth-wordmark">TALENT OPS</div>
            
            <div className="auth-sub-brand">A PRODUCT BY TECHNOVION</div>
            <div className="auth-tiny-divider">+</div>
            <div className="auth-credit">BUILT BY ABHISHEK</div>
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="auth-form-panel">
          
          {/* Mobile Branding */}
          <div className="auth-mobile-brand">
            <div className="auth-monogram">
              <span>T</span><div className="auth-logo-divider"></div><span>O</span>
            </div>
            <div className="auth-wordmark">TALENT OPS</div>
          </div>

          <div className={`auth-form-container glass-panel modal-enter ${isAuthenticating ? 'is-authenticating' : ''}`}>
            {children}
          </div>
        </div>

      </div>
    </>
  )
}
