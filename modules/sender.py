# modules/sender.py
import os, logging, smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT') or 587)
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

def send_email_with_approval(to_email, subject, body, dry_run=True):
    if not to_email:
        logging.error("No recipient email provided.")
        return False

    msg = EmailMessage()
    msg['From'] = f"{os.getenv('SENDER_NAME','Sender')} <{SMTP_USER or 'no-reply@example.com'}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.set_content(body)

    if dry_run:
        logging.info("[DRY RUN] Would send email to %s", to_email)
        return True

    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        logging.error("SMTP credentials missing; cannot send.")
        return False

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        logging.info("Email sent to %s", to_email)
        return True
    except Exception as e:
        logging.error("Failed to send: %s", e)
        return False
