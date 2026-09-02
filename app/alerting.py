"""
Email Alerting System for Revent Content Intelligence Dashboard.
Uses Python's standard smtplib (free — via Gmail App Password or standard SMTP)
to send alerts to:
- work.asheshthakur@gmail.com
- intern_ops@revent.store

Triggers:
1. Target failed after all retries (MAX_RETRIES exhausted)
2. Target failed on 2+ consecutive daily runs
3. Data staleness warning (> 48 hours old)
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

import streamlit as st
import config

logger = logging.getLogger(__name__)


def get_smtp_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Get sender email and app password from Streamlit secrets or environment."""
    email = None
    password = None

    try:
        email = st.secrets.get("smtp_email") or st.secrets.get("SMTP_EMAIL")
        password = st.secrets.get("smtp_password") or st.secrets.get("SMTP_PASSWORD")
    except Exception:
        pass

    if not email:
        email = os.environ.get("SMTP_EMAIL") or os.environ.get("smtp_email")
        password = os.environ.get("SMTP_PASSWORD") or os.environ.get("smtp_password")

    return email, password


def send_alert_email(subject: str, body_text: str, html_body: Optional[str] = None) -> bool:
    """
    Sends an alert email to config.ALERT_RECIPIENTS using smtplib.
    Returns True if sent successfully, False otherwise.
    """
    sender_email, sender_password = get_smtp_credentials()
    recipients = config.ALERT_RECIPIENTS

    if not sender_email or not sender_password:
        logger.info(
            f"[Alerting] SMTP credentials not set. Simulated email dispatch to {recipients}:\n"
            f"Subject: {subject}\n"
            f"Body:\n{body_text}"
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{config.BRAND_NAME} Alert] {subject}"
    msg["From"] = f"{config.BRAND_NAME} Monitor <{sender_email}>"
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(body_text, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
        logger.info(f"[Alerting] Email sent successfully to {recipients}")
        return True
    except Exception as e:
        logger.error(f"[Alerting] Failed to send email via SMTP: {e}")
        return False


# ── Condition A: Target Failed After Retries ─────────────────────────

def alert_scrape_target_failure(platform: str, target_url: str, error_reason: Optional[str] = None, retries_attempted: int = 2):
    """Trigger alert when a single target fails after all retries are exhausted."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"Scrape Failure: {platform} ({target_url})"
    
    body = (
        f"Revent Content Intelligence Alert\n\n"
        f"A scrape target has failed after {retries_attempted} retries.\n\n"
        f"• Platform: {platform}\n"
        f"• Target URL: {target_url}\n"
        f"• Timestamp: {now_utc}\n"
        f"• Error Reason: {error_reason or 'No response or anti-bot challenge'}\n\n"
        f"The dashboard will continue operating using cached data and manual overrides."
    )
    send_alert_email(subject, body)


# ── Condition B: Repeated Consecutive Failures (2+ Runs) ──────────────

def alert_repeated_failures(failed_targets: List[Dict[str, Any]]):
    """Trigger alert when targets fail on 2 or more consecutive daily runs."""
    if not failed_targets:
        return

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    count = len(failed_targets)
    subject = f"URGENT: {count} Target(s) Failed Consecutive Daily Runs"

    lines = [f"The following {count} target(s) have failed for 2+ consecutive scheduled runs:\n"]
    for t in failed_targets:
        lines.append(
            f"• [{t.get('platform')}] {t.get('target')}\n"
            f"  Consecutive Failures: {t.get('consecutive_failures')}\n"
            f"  Last Error: {t.get('last_error')}\n"
            f"  Last Failure: {t.get('last_failure_time')}\n"
        )
    lines.append(f"Timestamp: {now_utc}\nPlease inspect selector or authentication changes.")

    body = "\n".join(lines)
    send_alert_email(subject, body)


# ── Condition C: Stale Data Warning (> 48h) ──────────────────────────

def alert_stale_data(last_successful_dt: Optional[datetime], hours_stale: float):
    """Trigger alert when latest snapshot data is older than 48 hours."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    last_str = last_successful_dt.strftime("%Y-%m-%d %H:%M:%S UTC") if last_successful_dt else "Never"
    subject = f"WARNING: Dashboard Data is Stale ({hours_stale:.1f} hours old)"

    body = (
        f"Revent Content Intelligence Alert — Stale Data\n\n"
        f"The content intelligence dashboard has not received fresh scrape data in over 48 hours.\n\n"
        f"• Last Successful Scrape: {last_str}\n"
        f"• Current Time: {now_utc}\n"
        f"• Hours Stale: {hours_stale:.1f} hours\n"
        f"• Threshold: {config.STALE_DATA_THRESHOLD_HOURS} hours\n\n"
        f"Check GitHub Actions workflow status or scheduled cron runs."
    )
    send_alert_email(subject, body)
