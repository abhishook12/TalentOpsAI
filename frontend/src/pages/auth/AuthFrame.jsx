import React from 'react'
import { Link } from '@tanstack/react-router'

const shellStyles = `
  .auth-page {
    min-height: 100dvh;
    display: grid;
    place-items: center;
    padding: 0;
    background:
      radial-gradient(circle at top left, rgba(217, 164, 88, 0.08), transparent 32%),
      radial-gradient(circle at bottom right, rgba(255, 255, 255, 0.05), transparent 28%),
      linear-gradient(180deg, #0a0a0a 0%, #111111 100%);
    color: #f4f4f5;
  }

  .auth-shell {
    width: 100vw;
    min-height: 100dvh;
    display: grid;
    grid-template-columns: 1.08fr 0.92fr;
    overflow: hidden;
    border-radius: 0;
    background: rgba(16, 16, 16, 0.92);
    border: none;
    box-shadow: none;
  }

  .auth-hero {
    position: relative;
    overflow: hidden;
    padding: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
      radial-gradient(circle at 85% 18%, rgba(217, 164, 88, 0.18), transparent 18%),
      radial-gradient(circle at 5% 96%, rgba(255, 255, 255, 0.08), transparent 30%),
      linear-gradient(180deg, rgba(10, 10, 10, 0.98), rgba(18, 18, 18, 1));
  }

  .auth-hero::before,
  .auth-hero::after {
    content: '';
    position: absolute;
    inset: auto;
    border-radius: 999px;
    pointer-events: none;
  }

  .auth-hero::before {
    width: 72%;
    height: 84%;
    left: -18%;
    top: -12%;
    border: 1px solid rgba(217, 164, 88, 0.15);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.02) inset;
    transform: rotate(-12deg);
  }

  .auth-hero::after {
    width: 88%;
    height: 88%;
    left: -6%;
    bottom: -22%;
    border: 1px solid rgba(255, 255, 255, 0.05);
    opacity: 0.7;
  }

  .auth-hero-content {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 440px;
    text-align: center;
    display: grid;
    place-items: center;
    gap: 18px;
  }

  .auth-brand-mark {
    width: 82px;
    height: 82px;
    display: grid;
    place-items: center;
    color: #111;
    font-size: 44px;
    font-weight: 900;
    letter-spacing: -0.08em;
    border-radius: 20px;
    background: linear-gradient(180deg, #f1d0a6 0%, #d39a58 100%);
    box-shadow: 0 20px 50px rgba(207, 146, 77, 0.2);
    clip-path: polygon(14% 10%, 88% 10%, 81% 28%, 43% 28%, 33% 44%, 64% 44%, 57% 62%, 25% 62%, 10% 90%, 0 90%, 17% 46%, 34% 46%, 44% 28%, 20% 28%);
  }

  .auth-brand {
    margin-top: 12px;
    font-size: clamp(48px, 6vw, 64px);
    font-weight: 900;
    letter-spacing: -0.05em;
    line-height: 0.95;
  }

  .auth-brand span {
    color: #d2a067;
    font-weight: 300;
  }

  .auth-tagline {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.75);
    letter-spacing: 0.02em;
  }

  .auth-credit {
    width: 70%;
    display: flex;
    align-items: center;
    gap: 12px;
    color: rgba(255, 255, 255, 0.65);
    font-size: 12px;
    justify-content: center;
  }

  .auth-credit::before,
  .auth-credit::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.22), transparent);
  }

  .auth-panel {
    position: relative;
    overflow: hidden;
    padding: 48px 42px;
    background: linear-gradient(180deg, rgba(28, 28, 28, 0.96), rgba(21, 21, 21, 0.99));
    border-left: 1px solid rgba(255, 255, 255, 0.05);
  }

  .auth-panel::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at 88% 12%, rgba(217, 164, 88, 0.1), transparent 28%);
    pointer-events: none;
  }

  .auth-panel-inner {
    position: relative;
    z-index: 1;
    max-width: 470px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 100%;
  }

  .auth-kicker {
    color: #d7a867;
    font-size: 14px;
    margin-bottom: 6px;
  }

  .auth-title {
    margin: 0;
    font-size: clamp(30px, 3vw, 38px);
    line-height: 1.05;
    font-weight: 700;
    letter-spacing: -0.04em;
    color: #f5f5f5;
  }

  .auth-subtitle {
    margin: 14px 0 0;
    color: rgba(255, 255, 255, 0.62);
    font-size: 14px;
    line-height: 1.65;
  }

  .auth-form {
    margin-top: 28px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .auth-field {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .auth-label {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.68);
  }

  .auth-input,
  .auth-select {
    width: 100%;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    background: rgba(255, 255, 255, 0.03);
    color: #f4f4f5;
    padding: 12px 14px;
    font-size: 15px;
    outline: none;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
  }

  .auth-input::placeholder {
    color: rgba(255, 255, 255, 0.36);
  }

  .auth-input:focus,
  .auth-select:focus {
    border-color: rgba(90, 138, 255, 0.9);
    box-shadow: 0 0 0 3px rgba(90, 138, 255, 0.12);
    background: rgba(255, 255, 255, 0.05);
  }

  .auth-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }

  .auth-inline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .auth-mini-link {
    color: #7aa2ff;
    font-size: 13px;
    text-decoration: none;
    white-space: nowrap;
  }

  .auth-remember {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: rgba(255, 255, 255, 0.6);
    font-size: 13px;
  }

  .auth-check {
    width: 15px;
    height: 15px;
    accent-color: #7aa2ff;
  }

  .auth-button {
    margin-top: 4px;
    width: 100%;
    min-height: 48px;
    border: none;
    border-radius: 8px;
    background: linear-gradient(180deg, #3a3a3a, #2c2c2c);
    color: #f7f7f7;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.18s ease, filter 0.18s ease, opacity 0.18s ease;
  }

  .auth-button:hover:not(:disabled) {
    transform: translateY(-1px);
    filter: brightness(1.05);
  }

  .auth-button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  .auth-bottom {
    margin-top: 28px;
    color: rgba(255, 255, 255, 0.6);
    text-align: center;
    font-size: 14px;
  }

  .auth-bottom a {
    color: #6d90ff;
    font-weight: 500;
    text-decoration: none;
  }

  .auth-divider {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 28px 0 22px;
    color: rgba(255, 255, 255, 0.54);
    font-size: 12px;
    letter-spacing: 0.1em;
  }

  .auth-divider::before,
  .auth-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255, 255, 255, 0.08);
  }

  .auth-divider span {
    padding: 0 14px;
  }

  .auth-socials {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    position: relative;
  }

  .auth-social {
    min-height: 46px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    background: rgba(255, 255, 255, 0.03);
    color: rgba(255, 255, 255, 0.44);
    font-size: 14px;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: not-allowed;
  }

  .auth-social-badge {
    position: absolute;
    top: -11px;
    right: -8px;
    background: #f1b33b;
    color: #111;
    font-size: 10px;
    font-weight: 700;
    padding: 4px 8px;
    border-radius: 999px;
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.18);
  }

  .auth-eye-button {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.5);
    cursor: pointer;
    padding: 4px;
  }

  .auth-password-wrap {
    position: relative;
  }

  .auth-alert {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    color: #fbbf24;
    font-size: 13px;
  }

  .auth-error {
    padding: 12px 14px;
    border-radius: 10px;
    margin-top: 22px;
    margin-bottom: 4px;
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.18);
    color: #fca5a5;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .auth-copy-note {
    margin-top: 14px;
    color: rgba(255, 255, 255, 0.45);
    font-size: 12px;
  }

  .auth-footer-link {
    color: #7aa2ff;
    font-weight: 600;
    text-decoration: none;
  }

  @media (max-width: 1080px) {
    .auth-shell {
      grid-template-columns: 1fr;
    }

    .auth-hero {
      min-height: 320px;
    }

    .auth-panel {
      border-left: none;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
  }

  @media (max-width: 720px) {
    .auth-shell {
      min-height: 100dvh;
      border-radius: 0;
    }

    .auth-hero,
    .auth-panel {
      padding: 28px 20px;
    }

    .auth-row,
    .auth-socials {
      grid-template-columns: 1fr;
    }
  }
`

export default function AuthFrame({ eyebrow, title, subtitle, footerText, footerLink, footerLinkTo, children }) {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: shellStyles }} />
      <div className="auth-page">
        <div className="auth-shell">
          <section className="auth-hero" aria-hidden="true">
            <div className="auth-hero-content">
              <div className="auth-brand-mark">T</div>
              <div className="auth-brand">
                Talent<span>Ops</span>
              </div>
              <div className="auth-tagline">A Product by Technovion</div>
              <div className="auth-credit">Built by Abhishek</div>
            </div>
          </section>

          <section className="auth-panel">
            <div className="auth-panel-inner">
              {eyebrow ? <div className="auth-kicker">{eyebrow}</div> : null}
              <h1 className="auth-title">{title}</h1>
              {subtitle ? <p className="auth-subtitle">{subtitle}</p> : null}
              {children}
              {footerText ? (
                <div className="auth-bottom">
                  {footerText}{' '}
                  {footerLink ? (
                    <Link to={footerLinkTo} className="auth-footer-link">
                      {footerLink}
                    </Link>
                  ) : null}
                </div>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </>
  )
}
