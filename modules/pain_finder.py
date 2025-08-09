# modules/pain_finder.py
import re
PAIN_KEYWORDS = ['not converting', 'low traffic', 'slow', 'broken', 'outdated', 'not mobile', 'no online booking', 'hard to find', 'no reviews', 'negative reviews']

def find_pain_points(html_text, top_n=3):
    if not html_text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', html_text or '').lower()
    hits = []
    for k in PAIN_KEYWORDS:
        if k in text:
            hits.append(k)
    sentences = re.split(r'[.\n]+', text)
    problem_sentences = [s.strip() for s in sentences if any(w in s for w in ['problem','struggling','issue','challenge','hard to'])]
    for s in problem_sentences:
        hits.append(s[:200])
    return '\n'.join(hits[:top_n])
