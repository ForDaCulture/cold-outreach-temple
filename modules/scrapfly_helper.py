import os
import requests

def scrapfly_fetch(url, render_js=True, asp=True):
    key = os.getenv("SCRAPFLY_KEY")
    if not key:
        raise RuntimeError("SCRAPFLY_KEY not set in .env")
    params = {
        "key": key,
        "url": url,
        "render_js": str(render_js).lower(),
        "asp": str(asp).lower()
    }
    r = requests.get("https://api.scrapfly.io/scrape", params=params, timeout=60)
    r.raise_for_status()
    return r.text
