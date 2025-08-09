# modules/scraper.py
import time, logging, requests, os
from urllib.parse import urlparse
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
except Exception:
    webdriver = None

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; outreach-bot/1.0)'}

def _requests_fetch(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text, r.url, r.status_code

def _selenium_fetch(url, timeout=30):
    options = Options()
    # headless behavior: keep consistent across platforms
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.set_page_load_timeout(timeout)
    driver.get(url)
    html = driver.page_source
    final = driver.current_url
    driver.quit()
    return html, final, 200

def _scrapfly_fetch(url, api_key):
    # simple wrapper: returns html on success
    try:
        resp = requests.get("https://api.scrapfly.io/scrape/", params={'key': api_key, 'url': url, 'render': 'false'}, timeout=20)
        resp.raise_for_status()
        return resp.text, url, resp.status_code
    except Exception:
        return None, None, None

def _scraperapi_fetch(url, api_key):
    try:
        resp = requests.get(f"http://api.scraperapi.com?api_key={api_key}&url={url}", timeout=20)
        resp.raise_for_status()
        return resp.text, url, resp.status_code
    except Exception:
        return None, None, None

def fetch_page(url, use_selenium=False, delay=1.0, timeout=20, robots_check=False):
    time.sleep(delay)
    # simple robots.txt check
    if robots_check:
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            r = requests.get(robots_url, headers=HEADERS, timeout=5)
            if r.status_code == 200 and 'Disallow: /' in r.text:
                logging.warning("robots.txt blocks crawling for %s", url)
                return '', url
        except Exception:
            logging.debug("robots check failed or not present")

    # 1) try requests
    try:
        html, final, code = _requests_fetch(url, timeout=timeout)
        return html, final
    except Exception as e:
        logging.debug("Requests fetch failed: %s", e)

    # 2) try Scrapfly / ScraperAPI if env keys exist
    try:
        if os.getenv('SCRAPFLY_KEY'):
            html, final, code = _scrapfly_fetch(url, os.getenv('SCRAPFLY_KEY'))
            if html:
                return html, final
        if os.getenv('SCRAPERAPI_KEY'):
            html, final, code = _scraperapi_fetch(url, os.getenv('SCRAPERAPI_KEY'))
            if html:
                return html, final
    except Exception as e:
        logging.debug("Proxy fetchers error: %s", e)

    # 3) selenium fallback
    if use_selenium and webdriver:
        try:
            html, final, code = _selenium_fetch(url, timeout=timeout)
            return html, final
        except Exception as e:
            logging.error("Selenium fetch failed: %s", e)

    return '', url
