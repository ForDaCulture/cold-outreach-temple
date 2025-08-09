# modules/email_generator.py
import os
import re
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(loader=FileSystemLoader('templates'), autoescape=select_autoescape())

# Default website from your input; override with SENDER_WEBSITE in .env
DEFAULT_WEBSITE = 'https://retrohacker-portfolio.vercel.app/'

def _sanitize_text(text: str) -> str:
    """
    Clean common placeholders, bracketed tokens, and AI-identifying phrases.
    Steps:
      - remove bracketed placeholders: [..], {..}, <..>
      - remove standalone placeholder lines like 'Your Name', 'Your Company'
      - remove 'As an AI language model' variants
      - collapse multiple blank lines
      - trim whitespace
    """
    if not text:
        return text

    # Remove bracketed placeholders like [Your Name], {Company}, <Name>
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\{.*?\}', '', text)
    text = re.sub(r'<.*?>', '', text)

    # Remove common AI-identifying phrases (case-insensitive)
    ai_phrases = [
        r'as an ai language model',
        r'i am an ai',
        r'as an ai',
        r'i\'m an ai',
        r'i am a language model',
        r'as a language model'
    ]
    for p in ai_phrases:
        text = re.sub(p, '', text, flags=re.IGNORECASE)

    # Remove obvious placeholder-only lines (e.g., lines that only contain words like "Your Name")
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # common placeholder tokens (case-insensitive)
        placeholders = {'your name','your company','company name','[name]','name','[company]','your title'}
        # consider a line placeholder if it's short and matches or contains the token
        lower = stripped.lower()
        if (len(stripped) < 40) and any(tok in lower for tok in placeholders):
            continue
        lines.append(line)

    text = '\n'.join(lines)

    # collapse more than 2 newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Trim leading/trailing whitespace
    text = text.strip()

    return text

def _append_signature(text: str, sender_name: str, website: str) -> str:
    """
    Append a minimal, clean signature. If sender_name empty, includes just website.
    """
    website = website.rstrip('/')  # normalize
    sig_lines = []
    if sender_name:
        sig_lines.append(f"Best,\n{sender_name}")
    else:
        sig_lines.append("Best regards,")
    sig_lines.append(website)
    sig = "\n\n" + "\n".join(sig_lines)
    # Ensure there's a single blank line between body and signature
    if not text.endswith('\n'):
        text = text + '\n'
    return text.strip() + sig

def generate_email(context, template_path='templates/sample_template.j2', use_openai=False):
    """
    Render Jinja template, sanitize output, and append signature (website).
    Returns: (subject, body)
    """
    tmpl = env.get_template(template_path.split('templates/')[-1])
    # allow template to access SENDER_NAME & COMPANY_NAME but we'll sanitize results later
    rendered = tmpl.render(**context,
                           SENDER_NAME=os.getenv('SENDER_NAME', '').strip(),
                           COMPANY_NAME=os.getenv('COMPANY_NAME', '').strip())
    # simple heuristic: first non-empty line as subject
    lines = [l for l in rendered.splitlines() if l.strip() != '']
    subject = lines[0].strip() if lines else f"Quick question about {context.get('lead',{}).get('domain','your site')}"
    body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''

    # sanitize and append signature (use SENDER_WEBSITE env or default)
    sender_name = os.getenv('SENDER_NAME', '').strip()
    sender_website = os.getenv('SENDER_WEBSITE', DEFAULT_WEBSITE).strip()

    body = _sanitize_text(body)
    body = _append_signature(body, sender_name, sender_website)
    # also sanitize subject
    subject = _sanitize_text(subject)

    return subject, body

def preview_email(subject, body):
    print("\n📧 [Email Preview]")
    print("Subject:", subject)
    print()
    print(body)
    print("\n--- end preview ---\n")
