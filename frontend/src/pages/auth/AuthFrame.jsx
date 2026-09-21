import React from 'react'

const shellStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

  .auth-page {
    min-height: 100dvh;
    display: flex;
    width: 100vw;
    background: #0c0c0f;
    color: #ffffff;
    font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  /* LEFT BRAND PANEL */
  .auth-brand-panel {
    flex: 1;
    position: relative;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background:
      radial-gradient(ellipse 80% 60% at 50% 40%, rgba(255,255,255,0.06) 0%, transparent 55%),
      linear-gradient(165deg, #121218 0%, #0a0a0c 55%, #0e0e12 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    overflow: hidden;
  }

  @media (min-width: 900px) {
    .auth-brand-panel {
      display: flex;
    }
  }

  .auth-brand-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(ellipse 70% 65% at 50% 45%, black 20%, transparent 75%);
    -webkit-mask-image: radial-gradient(ellipse 70% 65% at 50% 45%, black 20%, transparent 75%);
    pointer-events: none;
    z-index: 0;
  }

  .auth-brand-orb {
    position: absolute;
    width: 420px;
    height: 420px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.07) 0%, transparent 68%);
    z-index: 0;
    animation: auth-orb-pulse 8s ease-in-out infinite;
  }

  @keyframes auth-orb-pulse {
    0%, 100% { transform: scale(1); opacity: 0.7; }
    50% { transform: scale(1.08); opacity: 1; }
  }

  /* MOBILE BRANDING (Visible only < 900px) */
  .auth-mobile-brand {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 28px;
    animation: auth-fade-up 0.55s ease-out both;
  }
  
  .auth-mobile-brand .auth-monogram {
    font-size: 44px;
    margin-bottom: 12px;
  }
  
  .auth-mobile-brand .auth-logo-divider {
    height: 44px;
    margin: 0 10px;
  }
  
  .auth-mobile-brand .auth-wordmark {
    font-size: 14px;
    letter-spacing: 0.32em;
    margin-bottom: 0;
  }
  
  @media (min-width: 900px) {
    .auth-mobile-brand {
      display: none;
    }
  }

  .auth-brand-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    animation: auth-fade-up 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  .auth-monogram {
    font-family: "Playfair Display", "Times New Roman", Times, serif;
    font-size: 76px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    margin-bottom: 20px;
    color: #ffffff;
  }

  .auth-logo-divider {
    width: 1px;
    height: 72px;
    background: linear-gradient(180deg, transparent, #ffffff 20%, #ffffff 80%, transparent);
    opacity: 0.35;
    margin: 0 18px;
    transform-origin: center;
    animation: auth-divider-in 0.9s ease-out 0.15s both;
  }

  @keyframes auth-divider-in {
    from { transform: scaleY(0); opacity: 0; }
    to { transform: scaleY(1); opacity: 0.35; }
  }

  .auth-wordmark {
    font-size: 30px;
    font-weight: 600;
    letter-spacing: 0.38em;
    text-transform: uppercase;
    margin-bottom: 14px;
    margin-right: -0.38em;
    color: #ffffff;
  }

  .auth-tagline {
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0.02em;
    color: rgba(255, 255, 255, 0.45);
    margin-bottom: 36px;
    max-width: 280px;
    text-align: center;
    line-height: 1.5;
  }

  .auth-sub-brand {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 6px;
    margin-right: -0.22em;
  }
  
  .auth-tiny-divider {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.28);
    margin-bottom: 6px;
  }

  .auth-credit {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.5);
    margin-right: -0.22em;
  }

  /* RIGHT FORM PANEL */
  .auth-form-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 24px;
    background:
      radial-gradient(ellipse 90% 70% at 70% 20%, rgba(255,255,255,0.03) 0%, transparent 50%),
      #121216;
  }

  .auth-form-container {
    width: 100%;
    max-width: 400px;
    padding: 40px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow:
      0 1px 0 rgba(255,255,255,0.04) inset,
      0 24px 48px rgba(0,0,0,0.35);
    background: rgba(22, 22, 26, 0.92);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    animation: auth-fade-up 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.08s both;
  }

  @keyframes auth-fade-up {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 480px) {
    .auth-form-container {
      padding: 24px;
      border-radius: 10px;
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

  .auth-form-container .relative:has(> i:first-child) input,
  .auth-form-container input.pl-10 {
    padding-left: 42px !important;
  }

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

  @media (prefers-reduced-motion: reduce) {
    .auth-brand-content,
    .auth-form-container,
    .auth-mobile-brand,
    .auth-logo-divider,
    .auth-brand-orb {
      animation: none !important;
    }
  }
`

export default function AuthFrame({ children, isAuthenticating }) {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: shellStyles }} />
      <div className="auth-page">
        
        <div className="auth-brand-panel">
          <div className="auth-brand-grid" aria-hidden="true" />
          <div className="auth-brand-orb" aria-hidden="true" />
          <div className="auth-brand-content">
            <div className="auth-monogram">
              <span>T</span>
              <div className="auth-logo-divider"></div>
              <span>O</span>
            </div>
            <div className="auth-wordmark">TALENT OPS</div>
            <p className="auth-tagline">Recruiting intelligence for modern talent teams</p>
            <div className="auth-credit">BUILT BY ABHISHEK</div>
          </div>
        </div>

        <div className="auth-form-panel">
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
