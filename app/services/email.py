import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAILS_FROM_EMAIL = os.getenv("EMAILS_FROM_EMAIL", "noreply@callcompanion.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def send_password_reset_email(email_to: str, token: str) -> bool:
    reset_link = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    subject = "Reset Your Call Companion Password"
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2563eb;">Password Reset Request</h2>
        <p>You requested a password reset for your Call Companion account.</p>
        <p>Click the link below to set a new password. This link is valid for 15 minutes:</p>
        <p>
          <a href="{reset_link}" style="background-color: #2563eb; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
            Reset Password
          </a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p style="color: #666; font-size: 0.9em;">If you did not request this, please ignore this email.</p>
      </body>
    </html>
    """
    
    # Always log reset link for development and debugging visibility
    logger.info(f"PASSWORD RESET LINK for {email_to}: {reset_link}")
    print(f"\n==========================================")
    print(f"[PASSWORD RESET] Target: {email_to}")
    print(f"[PASSWORD RESET] Link:   {reset_link}")
    print(f"==========================================\n")

    if not SMTP_HOST or not SMTP_USER:
        logger.info("SMTP not configured. Reset link logged above.")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAILS_FROM_EMAIL
        msg["To"] = email_to

        part = MIMEText(html_content, "html")
        msg.attach(part)

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                if SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(EMAILS_FROM_EMAIL, [email_to], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                if SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(EMAILS_FROM_EMAIL, [email_to], msg.as_string())

        
        logger.info(f"Password reset email sent successfully to {email_to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email via SMTP: {e}")
        return False
