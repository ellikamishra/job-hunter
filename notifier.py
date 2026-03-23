"""
Email notification sender for new job postings.
Supports two backends:
  1. Resend API — set RESEND_API_KEY + RESEND_FROM (recommended for production)
  2. SMTP       — set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM (fallback)
Configure via environment variables or .streamlit/secrets.toml.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ── Config helpers ────────────────────────────────────────────────────────────

def _get_streamlit_secrets() -> dict:
    """Safely read Streamlit secrets as a plain dict."""
    try:
        import streamlit as st
        return dict(st.secrets)
    except Exception:
        return {}


def _get_resend_config() -> dict:
    config = {
        "api_key": os.environ.get("RESEND_API_KEY", ""),
        "from_email": os.environ.get("RESEND_FROM", ""),
    }
    if config["api_key"]:
        return config

    sec = _get_streamlit_secrets().get("resend", {})
    if sec:
        return {
            "api_key": sec.get("api_key", config["api_key"]),
            "from_email": sec.get("from_email", config["from_email"]),
        }
    return config


def _get_smtp_config() -> dict:
    config = {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_email": os.environ.get("SMTP_FROM", ""),
    }
    if config["host"] and config["user"]:
        return config

    sec = _get_streamlit_secrets().get("smtp", {})
    if sec:
        return {
            "host": sec.get("host", config["host"]),
            "port": int(sec.get("port", config["port"])),
            "user": sec.get("user", config["user"]),
            "password": sec.get("password", config["password"]),
            "from_email": sec.get("from_email", config["from_email"]),
        }
    return config


def is_smtp_configured() -> bool:
    """Check whether any email backend (Resend or SMTP) is available."""
    resend_cfg = _get_resend_config()
    if resend_cfg["api_key"] and resend_cfg["from_email"]:
        return True
    smtp_cfg = _get_smtp_config()
    return bool(smtp_cfg["host"] and smtp_cfg["user"] and smtp_cfg["password"])


# ── Email building ────────────────────────────────────────────────────────────

def _build_email_content(search_name: str, jobs: list[dict]) -> tuple[str, str]:
    """Build plain text and HTML content for the notification email."""
    rows_html = ""
    for j in jobs:
        link = j.get("link", "#")
        rows_html += f"""
        <tr>
            <td style="padding:8px; border:1px solid #ddd;">{j.get('company', '')}</td>
            <td style="padding:8px; border:1px solid #ddd;">{j.get('title', '')}</td>
            <td style="padding:8px; border:1px solid #ddd;">{j.get('location', '')}</td>
            <td style="padding:8px; border:1px solid #ddd;">{j.get('experience', '')}</td>
            <td style="padding:8px; border:1px solid #ddd;">{j.get('skills', '')}</td>
            <td style="padding:8px; border:1px solid #ddd;">{j.get('posted_date', '')}</td>
            <td style="padding:8px; border:1px solid #ddd;">
                <a href="{link}" style="color:#2F5496;">Apply</a>
            </td>
        </tr>"""

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color:#2F5496;">New Jobs Found!</h2>
        <p>Your saved search <strong>"{search_name}"</strong> found
           <strong>{len(jobs)}</strong> new job posting(s).</p>

        <table style="border-collapse:collapse; width:100%; margin:16px 0;">
            <thead>
                <tr style="background:#2F5496; color:white;">
                    <th style="padding:8px; border:1px solid #ddd;">Company</th>
                    <th style="padding:8px; border:1px solid #ddd;">Job Title</th>
                    <th style="padding:8px; border:1px solid #ddd;">Location</th>
                    <th style="padding:8px; border:1px solid #ddd;">Experience</th>
                    <th style="padding:8px; border:1px solid #ddd;">Skills</th>
                    <th style="padding:8px; border:1px solid #ddd;">Posted</th>
                    <th style="padding:8px; border:1px solid #ddd;">Link</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <p style="color:#666; font-size:12px;">
            This is an automated notification from Job Hunter.
            Log in to manage your saved searches and notification preferences.
        </p>
    </body>
    </html>
    """
    plain = f"New jobs found for '{search_name}': {len(jobs)} results."
    return plain, html


# ── Send backends ─────────────────────────────────────────────────────────────

def _send_via_resend(to_email: str, subject: str, plain: str, html: str) -> bool:
    """Send email using the Resend API."""
    import resend

    cfg = _get_resend_config()
    resend.api_key = cfg["api_key"]

    try:
        resend.Emails.send({
            "from": cfg["from_email"],
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": plain,
        })
        print(f"[+] Resend notification sent to {to_email}")
        return True
    except Exception as e:
        print(f"[!] Resend failed for {to_email}: {e}")
        return False


def _send_via_smtp(to_email: str, subject: str, plain: str, html: str) -> bool:
    """Send email using SMTP."""
    cfg = _get_smtp_config()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from_email"] or cfg["user"]
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(msg["From"], [to_email], msg.as_string())
        print(f"[+] SMTP notification sent to {to_email}")
        return True
    except Exception as e:
        print(f"[!] SMTP failed for {to_email}: {e}")
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def send_job_notification(to_email: str, search_name: str, jobs: list[dict]) -> bool:
    """
    Send an HTML email listing new jobs found for a saved search.
    Tries Resend first, falls back to SMTP.
    Returns True if sent successfully, False otherwise.
    """
    subject = f"Job Hunter: {len(jobs)} new job(s) found for '{search_name}'"
    plain, html = _build_email_content(search_name, jobs)

    # Try Resend first
    resend_cfg = _get_resend_config()
    if resend_cfg["api_key"] and resend_cfg["from_email"]:
        return _send_via_resend(to_email, subject, plain, html)

    # Fall back to SMTP
    smtp_cfg = _get_smtp_config()
    if smtp_cfg["host"] and smtp_cfg["user"]:
        return _send_via_smtp(to_email, subject, plain, html)

    print(f"[!] No email backend configured — skipping notification to {to_email}")
    return False
