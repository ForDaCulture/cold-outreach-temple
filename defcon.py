#!/usr/bin/env python3
# stealth_lowell_urls_v2.py
#
# Persistent, headless, undetectable scraper for LOWELL MA within 5-mile radius.
# Refactored for operational stability and efficiency.

import csv, time, ssl, random, sys
import requests, urllib3
from bs4 import BeautifulSoup
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from urllib.parse import urlparse, parse_qs

# --- CONFIGURATION ---
# CRITICAL: You must get a Google Cloud API key and enable the "Places API".
# https://console.cloud.google.com/google/maps-apis/
GOOGLE_API_KEY = "AIzaSyCVKsv45At66rHulS3GZxiE-Sc-2656kD0" # <-- PASTE YOUR API KEY HERE

LOWELL_COORDS = (42.6334, -71.3162)      # Lowell, MA
RADIUS_MILES = 5

# A list of common, recent user agents to rotate through.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

# --- CORE SYSTEMS ---
urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

def get_stealth_chrome():
    """Configures and launches a stealth-configured headless Chrome instance."""
    print("[+] Launching stealth browser...")
    c_opts = Options()
    c_opts.add_argument("--headless=new")
    c_opts.add_argument("--no-sandbox")
    c_opts.add_argument("--disable-dev-shm-usage")
    c_opts.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    c_opts.add_argument("--disable-blink-features=AutomationControlled")
    c_opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    c_opts.add_experimental_option("useAutomationExtension", False)
    
    try:
        driver = webdriver.Chrome(options=c_opts)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.set_page_load_timeout(20)
        return driver
    except WebDriverException as e:
        print(f"[!!] FATAL: WebDriver failed to launch. Is chromedriver installed and in your PATH? Error: {e}")
        sys.exit(1)

def fetch_places_from_api(keyword, api_key):
    """Hits the Google Places API 'Nearby Search' and returns a list of place objects."""
    places = []
    headers = {"accept-language": "en-US,en;q=0.9"}
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    url = (
        f"{base_url}?location={LOWELL_COORDS[0]},{LOWELL_COORDS[1]}"
        f"&radius={int(RADIUS_MILES * 1609.34)}"
        f"&keyword={keyword}"
        f"&key={api_key}"
    )

    print(f"[*] Querying API for keyword: '{keyword}'...")
    while url:
        try:
            r = requests.get(url, headers=headers, verify=False, timeout=15)
            r.raise_for_status()
            j = r.json()
            
            status = j.get("status")
            if status != "OK" and status != "ZERO_RESULTS":
                error = j.get("error_message", "No error message provided.")
                print(f"[!] API Warning for '{keyword}': Status {status}. Reason: {error}")
                return [] # Abort for this keyword on error

            places.extend(j.get("results", []))
            
            token = j.get("next_page_token")
            if token:
                time.sleep(random.uniform(2, 4)) # Required pause before fetching next page
                url = f"{base_url}?pagetoken={token}&key={api_key}"
            else:
                url = None
        except requests.exceptions.RequestException as e:
            print(f"[!] API request failed for '{keyword}': {e}")
            url = None

    print(f"[*] API returned {len(places)} potential targets for '{keyword}'.")
    return places

def scrape_url_from_place(driver, place):
    """Navigates to a place's Google Maps page and extracts the business URL."""
    place_id = place.get("place_id")
    place_name = place.get("name", "Unknown Place")
    if not place_id:
        return None

    # This is a more robust and human-like URL target
    target_url = f"https://www.google.com/maps/search/?api=1&query=placeholder&query_place_id={place_id}"
    
    try:
        driver.get(target_url)
        time.sleep(random.uniform(2.5, 4.2)) # Wait for dynamic content to load
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # Google often wraps external links in a redirect. This finds it.
        for a_tag in soup.find_all("a", href=True):
            if "url?" in a_tag["href"]:
                parsed_href = urlparse(a_tag["href"])
                qs_params = parse_qs(parsed_href.query)
                if "url" in qs_params:
                    website = qs_params["url"][0]
                    # Clean the URL
                    return website.split('?')[0].split('#')[0]
    except TimeoutException:
        print(f"[-] Timeout loading page for '{place_name}'. Skipping.")
    except Exception as e:
        print(f"[-] Error scraping '{place_name}': {e}. Skipping.")
    
    return None


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    if not GOOGLE_API_KEY:
        print("[!!] FATAL: GOOGLE_API_KEY is not set. Get a key from Google Cloud Platform and paste it into the script.")
        sys.exit(1)

    keyword_basket = ["restaurants", "plumbers", "retail shops", "auto repair", "bars", "lawyers", "salons"]
    all_urls = set()
    
    driver = get_stealth_chrome() # Launch browser ONCE
    
    for kw in keyword_basket:
        if len(all_urls) >= 500: # Set a reasonable mission limit
            print("[+] Target count reached. Exiting loop.")
            break

        places_to_scrape = fetch_places_from_api(kw, GOOGLE_API_KEY)
        if not places_to_scrape:
            continue
            
        print(f"[*] Beginning scrape for {len(places_to_scrape)} targets from '{kw}'...")
        for i, place in enumerate(places_to_scrape, 1):
            url = scrape_url_from_place(driver, place)
            if url and (url.startswith("http://") or url.startswith("https://")):
                if url not in all_urls:
                    print(f"  [>] {i}/{len(places_to_scrape)} | Procured: {url}")
                    all_urls.add(url)
            # Add a micro-sleep to be less aggressive
            time.sleep(random.uniform(0.5, 1.2))

    driver.quit()
    print("[+] Browser closed.")

    output_file = "lowell_urls_5mi.csv"
    with open(output_file, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for u in sorted(list(all_urls)):
            writer.writerow([u])

    print(f"\n[SUCCESS] Procured {len(all_urls)} unique URLs to {output_file}")