# modules/pain_finder.py
import re

# Expanded keywords for broader coverage
PAIN_KEYWORDS = [
    'not converting', 'low traffic', 'slow', 'broken', 'outdated', 'not mobile',
    'no online booking', 'hard to find', 'no reviews', 'negative reviews',
    'poor seo', 'bad user experience', 'high bounce rate', 'security issues',
    'no ssl', 'loading slowly', 'mobile unfriendly'
]

# Problem indicators
PROBLEM_WORDS = ['problem', 'struggling', 'issue', 'challenge', 'hard to', 'difficulty', 'frustrating']

def find_pain_points(html_text, top_n=5):
    """
    Upgrades: Expanded keywords, added negation skip (e.g., "not a problem"), return list for flexibility,
    increased top_n default, better sentence filtering to avoid false positives.
    """
    if not html_text:
        return []
    
    # Strip HTML tags and normalize text
    text = re.sub(r'<[^>]+>', ' ', html_text or '').lower()
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
    
    hits = []
    # Check keywords with basic context (skip if preceded by 'not a' or similar negation)
    for k in PAIN_KEYWORDS:
        if re.search(r'(?<!not a\s)' + re.escape(k), text):  # Avoid simple negations
            hits.append(k)
    
    # Split into sentences
    sentences = re.split(r'[.\n]+', text)
    problem_sentences = []
    for s in sentences:
        s = s.strip()
        if s and any(w in s for w in PROBLEM_WORDS):
            # Skip if sentence has strong negation
            if not re.search(r'\b(not|no|none|zero)\b.*\b(problem|issue)\b', s):
                problem_sentences.append(s[:250])  # Slightly longer truncate for context
    
    # Combine and dedup
    all_hits = list(set(hits + problem_sentences))
    return all_hits[:top_n]  # Return list for easier manipulation downstream