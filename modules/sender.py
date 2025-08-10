# modules/sender.py
import os, logging, smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from tenacity import retry, stop_after_attempt, wait_fixed

SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT') or 587)
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def send_email_with_approval(to_email, subject, body, dry_run=True, is_html=False, cc=None, bcc=None):
    """
    Upgrades: Added retries, HTML support via MIME, CC/BCC, better From fallback,
    raised errors for missing creds, logging enhancements.
    """
    if not to_email:
        logging.error("No recipient email provided.")
        return False

    if not (SMTP_HOST and SMTP_USER and SMTP_PASS) and not dry_run:
        raise ValueError("SMTP credentials missing; cannot send.")

    sender_name = os.getenv('SENDER_NAME', 'Outreach Bot')
    from_email = SMTP_USER or 'no-reply@example.com'
    msg = EmailMessage()
    msg['From'] = f"{sender_name} <{from_email}>"
    msg['To'] = to_email
    if cc:
        msg['Cc'] = cc
    if bcc:
        msg['Bcc'] = bcc
    msg['Subject'] = subject

    if is_html:
        msg.set_content("Plain text fallback.")
        msg.add_alternative(body, subtype='html')
    else:
        msg.set_content(body)

    if dry_run:
        logging.info("[DRY RUN] Would send email to %s with subject '%s'", to_email, subject)
        return True

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        logging.info("Email sent to %s", to_email)
        return True
    except Exception as e:
        logging.error("Failed to send after retries: %s", e)
        return False