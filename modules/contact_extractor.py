# modules/contact_extractor.py
"""
Contact extractor - robust email/phone/form/JSON-LD extraction and deobfuscation.
Exports:
  - extract_contacts_from_html(html, base_url=None)
  - extract_contacts(html_or_url)
"""
import re
import logging
from bs4 import BeautifulSoup
import requests
import extruct
from w3lib.html import get_base_url

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I)
# Accept varied phone token patterns; we will normalize digits
PHONE_TOKEN_RE = re.compile(r'[\d\-\(\)\.\s\+]{7,20}')

def extract_contacts_from_html(html, base_url=None):
    """
    Parse the HTML and return a dict:
      {'emails': [..], 'phones': [..], 'jsonld': [..], 'form_actions': [..]}
    """
    result = {'emails': [], 'phones': [], 'jsonld': [], 'form_actions': []}
    if not html:
        return result

    soup = BeautifulSoup(html, 'lxml')

    # 1) mailto: links
    for a in soup.select('a[href^=mailto]'):
        try:
            href = a.get('href', '')
            email = href.split(':', 1)[1].split('?')[0].strip()
            if email and re.search(EMAIL_RE, email):
                if email not in result['emails']:
                    result['emails'].append(email)
        except Exception:
            continue

    # 2) visible emails in text
    text = soup.get_text(separator=' ')
    for m in set(re.findall(EMAIL_RE, text)):
        m = m.strip().rstrip('.,;:')
        if m and m not in result['emails']:
            result['emails'].append(m)

    # 3) phones - keep only realistic phone-like tokens (7-15 digits after stripping)
    raw_phone_tokens = set(re.findall(PHONE_TOKEN_RE, text))
    clean_phones = []
    for token in raw_phone_tokens:
        digits = re.sub(r'[^0-9]', '', token)
        if 7 <= len(digits) <= 15:
            if digits not in clean_phones:
                clean_phones.append(digits)
    for p in clean_phones:
        if p not in result['phones']:
            result['phones'].append(p)

    # 4) form actions
    for f in soup.find_all('form'):
        action = f.get('action') or ''
        if action:
            result['form_actions'].append(action)

    # 5) json-ld / microdata via extruct
    try:
        base = get_base_url(html, base_url or '')
        data = extruct.extract(html, base_url=base, syntaxes=['json-ld', 'microdata'])
        for j in data.get('json-ld', []) + data.get('microdata', []):
            result['jsonld'].append(j)
            # try to extract emails/phones from JSON-LD contact info
            if isinstance(j, dict):
                # contactPoint can be list or dict
                cp = j.get('contactPoint') or j.get('email') or j.get('telephone') or j.get('sameAs')
                if isinstance(cp, str):
                    if re.search(EMAIL_RE, cp) and cp not in result['emails']:
                        result['emails'].append(cp)
                    digits = re.sub(r'[^0-9]', '', cp)
                    if 7 <= len(digits) <= 15 and digits not in result['phones']:
                        result['phones'].append(digits)
                elif isinstance(cp, dict):
                    e = cp.get('email')
                    t = cp.get('telephone')
                    if e and re.search(EMAIL_RE, e) and e not in result['emails']:
                        result['emails'].append(e)
                    if t:
                        digits = re.sub(r'[^0-9]', '', t)
                        if 7 <= len(digits) <= 15 and digits not in result['phones']:
                            result['phones'].append(digits)
                elif isinstance(cp, list):
                    for item in cp:
                        if isinstance(item, str):
                            if re.search(EMAIL_RE, item) and item not in result['emails']:
                                result['emails'].append(item)
                            digits = re.sub(r'[^0-9]', '', item)
                            if 7 <= len(digits) <= 15 and digits not in result['phones']:
                                result['phones'].append(digits)
    except Exception as e:
        logging.debug("extruct extraction failed: %s", e)

    # 6) deobfuscation: replace common obfuscations and re-run email find
    try:
        deob = text
        deob = deob.replace('(at)', '@').replace('[at]', '@').replace(' at ', '@')
        deob = deob.replace('(dot)', '.').replace('[dot]', '.').replace(' dot ', '.')
        for m in set(re.findall(EMAIL_RE, deob)):
            if m not in result['emails']:
                result['emails'].append(m)
    except Exception:
        pass

    # final sanity: remove obviously invalid emails (e.g., long numeric strings) and duplicates
    cleaned_emails = []
    for e in result['emails']:
        e = e.strip().rstrip('.,;:')
        # skip crazy addresses like long numeric strings
        if re.fullmatch(r'\d{7,}', e):
            continue
        if e not in cleaned_emails:
            cleaned_emails.append(e)
    result['emails'] = cleaned_emails

    return result


def extract_contacts(html_or_url):
    """
    Wrapper: if html_or_url looks like a URL it will fetch and pass HTML to extractor.
    Otherwise, treat argument as raw HTML.
    """
    if not html_or_url:
        return {'emails': [], 'phones': []}
    if isinstance(html_or_url, str) and (html_or_url.startswith('http://') or html_or_url.startswith('https://')):
        try:
            r = requests.get(html_or_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            r.raise_for_status()
            return extract_contacts_from_html(r.text, base_url=r.url)
        except Exception as e:
            logging.debug("fetch for extract_contacts failed: %s", e)
            return {'emails': [], 'phones': []}
    else:
        return extract_contacts_from_html(html_or_url)


__all__ = ['extract_contacts', 'extract_contacts_from_html']
