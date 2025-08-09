# modules/serp_proxy.py
import requests, logging

def scrapfly_fetch(url, api_key, render=True, timeout=30):
    """
    Call Scrapfly scrape endpoint. Set render=True to execute JS.
    Returns dict {'html': ...} on success or None on failure.
    """
    try:
        params = {'key': api_key, 'url': url, 'render': 'true' if render else 'false'}
        r = requests.get("https://api.scrapfly.io/scrape/", params=params, timeout=timeout)
        r.raise_for_status()
        return {'html': r.text}
    except Exception as e:
        logging.debug("Scrapfly fetch failed: %s", e)
        return None

def scraperapi_fetch(url, api_key, timeout=20):
    try:
        r = requests.get(f"http://api.scraperapi.com?api_key={api_key}&url={url}", timeout=timeout)
        r.raise_for_status()
        return {'html': r.text}
    except Exception as e:
        logging.debug("ScraperAPI fetch failed: %s", e)
        return None
