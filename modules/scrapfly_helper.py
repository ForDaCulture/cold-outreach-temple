import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def scrapfly_fetch(url, render_js=True, asp=True):
    """
    Upgrades: Added retries, return dict for consistency with other fetchers,
    better error logging.
    """
    key = os.getenv("SCRAPFLY_KEY")
    if not key:
        raise RuntimeError("SCRAPFLY_KEY not set in .env")
    params = {
        "key": key,
        "url": url,
        "render_js": str(render_js).lower(),
        "asp": str(asp).lower()
    }
    try:
        r = requests.get("https://api.scrapfly.io/scrape", params=params, timeout=60)
        r.raise_for_status()
        return {'html': r.text}
    except Exception as e:
        logging.error("Scrapfly fetch failed after retries: %s", e)
        raise