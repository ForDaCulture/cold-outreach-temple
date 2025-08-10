# modules/scraper.py
import time, logging, requests, os
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
except Exception:
    webdriver = None

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; outreach-bot/1.0)'}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _requests_fetch(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text, r.url, r.status_code

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
def _selenium_fetch(url, timeout=30):
    options = Options()
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

def _scrapfly_fetch(url, api_key, render_js=False):
    try:
        params = {'key': api_key, 'url': url, 'render_js': str(render_js).lower()}
        resp = requests.get("https://api.scrapfly.io/scrape/", params=params, timeout=20)
        resp.raise_for_status()
        return resp.text, url, resp.status_code
    except Exception as e:
        logging.debug("Scrapfly fetch failed: %s", e)
        return None, None, None

def _scraperapi_fetch(url, api_key):
    try:
        resp = requests.get(f"http://api.scraperapi.com?api_key={api_key}&url={url}", timeout=20)
        resp.raise_for_status()
        return resp.text, url, resp.status_code
    except Exception as e:
        logging.debug("ScraperAPI fetch failed: %s", e)
        return None, None, None

def fetch_page(url, use_selenium=False, render_js=False, delay=1.0, timeout=20, robots_check=False):
    """
    Upgrades: Added tenacity retries to requests/selenium, render_js param for Scrapfly,
    unified proxy logic, improved error logging, return dict for consistency (html, final_url).
    """
    time.sleep(delay)
    if robots_check:
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            r = requests.get(robots_url, headers=HEADERS, timeout=5)
            if r.status_code == 200 and 'Disallow: /' in r.text:
                logging.warning("robots.txt blocks crawling for %s", url)
                return {'html': '', 'final_url': url}
        except Exception:
            logging.debug("robots check failed or not present")

    # 1) try requests with retry
    try:
        html, final, code = _requests_fetch(url, timeout=timeout)
        return {'html': html, 'final_url': final}
    except Exception as e:
        logging.debug("Requests fetch failed after retries: %s", e)

    # 2) try Scrapfly / ScraperAPI if env keys exist
    try:
        if os.getenv('SCRAPFLY_KEY'):
            html, final, code = _scrapfly_fetch(url, os.getenv('SCRAPFLY_KEY'), render_js=render_js)
            if html:
                return {'html': html, 'final_url': final}
        if os.getenv('SCRAPERAPI_KEY'):
            html, final, code = _scraperapi_fetch(url, os.getenv('SCRAPERAPI_KEY'))
            if html:
                return {'html': html, 'final_url': final}
    except Exception as e:
        logging.debug("Proxy fetchers error: %s", e)

    # 3) selenium fallback with retry
    if use_selenium and webdriver:
        try:
            html, final, code = _selenium_fetch(url, timeout=timeout)
            return {'html': html, 'final_url': final}
        except Exception as e:
            logging.error("Selenium fetch failed after retries: %s", e)

    return {'html': '', 'final_url': url}