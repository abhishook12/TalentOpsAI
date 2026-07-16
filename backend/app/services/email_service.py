import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

def _send_real_email(to_email: str, subject: str, html_body: str) -> bool:
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

def send_verification_email(email: str, token: str):
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>Verify your email address</h2>
        <p>Please click the button below to verify your email address and activate your account:</p>
        <a href="{verify_url}" style="display: inline-block; padding: 10px 20px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0;">Verify Email</a>
        <p>Or copy and paste this link into your browser:</p>
        <p><a href="{verify_url}">{verify_url}</a></p>
    </div>
    """
    
    if _send_real_email(email, "Verify your TalentOps AI account", html_body):
        logger.info(f"REAL EMAIL → Verification sent to {email}")
    else:
        logger.info(f"DEV EMAIL → Verification for {email}")
        logger.info(f"Click to verify: {verify_url}")
        print(f"\n{'='*60}")
        try:
            print(f"  [EMAIL] VERIFICATION EMAIL (dev mode)")
            print(f"  To: {email}")
            print(f"  Link: {verify_url}")
        except UnicodeEncodeError:
            pass
        print(f"{'='*60}\n")

def send_password_reset_email(email: str, token: str):
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>Reset your password</h2>
        <p>You requested to reset your password. Click the button below to choose a new one:</p>
        <a href="{reset_url}" style="display: inline-block; padding: 10px 20px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0;">Reset Password</a>
        <p>If you didn't request this, you can safely ignore this email.</p>
        <p>Or copy and paste this link into your browser:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
    </div>
    """
    
    if _send_real_email(email, "Reset your TalentOps AI password", html_body):
        logger.info(f"REAL EMAIL → Password reset sent to {email}")
    else:
        logger.info(f"DEV EMAIL → Password reset for {email}")
        logger.info(f"Click to reset: {reset_url}")
        print(f"\n{'='*60}")
        try:
            print(f"  [EMAIL] (dev mode)")
            print(f"  To: {email}")
            print(f"  Subject: Reset your TalentOps AI password")
            print(f"  Link: {reset_url}")
        except UnicodeEncodeError:
            pass
        print(f"{'='*60}\n")
