# modules/serp_proxy.py
import os, requests, logging
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def scrapfly_fetch(url, render_js=True, asp=True, timeout=30):
    """
    Upgrades: Merged with scrapfly_helper.py, added retries, env check early,
    consistent dict return, asp param from helper.
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
    r = requests.get("https://api.scrapfly.io/scrape", params=params, timeout=timeout)
    r.raise_for_status()
    return {'html': r.text}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def scraperapi_fetch(url, timeout=20):
    key = os.getenv("SCRAPERAPI_KEY")
    if not key:
        raise RuntimeError("SCRAPERAPI_KEY not set in .env")
    r = requests.get(f"http://api.scraperapi.com?api_key={key}&url={url}", timeout=timeout)
    r.raise_for_status()
    return {'html': r.text}