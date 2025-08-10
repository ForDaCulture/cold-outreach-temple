# modules/lead_discovery.py (Fully Updated with Advanced Parsing)
import os
import requests
import logging
import re
import json
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
from modules.serp_proxy import scrapfly_fetch

AGGREGATOR_PATTERNS = [
    "yelp", "angi", "whitepages", "manta", "bbb.org", "yellowpages",
    "houzz", "gov", "facebook.com", "linkedin.com", "support.google.com",
    "thumbtack", "homeadvisor", "clutch.co"
]


# <<< --- NEW HELPER FUNCTION --- >>>
def parse_embedded_json(html: str):
    """
    Attempts to find, clean, and parse the main JSON data blob
    from a Google search results page.
    """
    try:
        soup = BeautifulSoup(html, 'lxml')
        # Find the script tag containing the primary data, often in a variable like this.
        # This regex is looking for a script tag that contains the text "window._"
        script_tag = soup.find('script', string=re.compile(r'window\._'))
        if not script_tag:
            logging.warning("Could not find a main data script tag.")
            return None

        script_content = script_tag.string
        
        # This pattern looks for a large JSON structure within the script.
        match = re.search(r'google\.maps\.preload\.data\s*=\s*\'(.*?)\'', script_content)
        if not match:
             logging.warning("Could not find the JSON data pattern in the script.")
             return None

        # The captured group is a string that looks like JSON, but needs un-escaping.
        json_str = match.group(1).encode().decode('unicode_escape')
        
        # The first few characters are often junk ')]}\'' that needs to be removed.
        if json_str.startswith(")]}'"):
            json_str = json_str[4:]
            
        data = json.loads(json_str)
        logging.info("✅ Successfully parsed embedded JSON data.")
        
        # IMPORTANT: You now have a massive dictionary. The next step is to write code
        # to navigate it and pull out the business information. This structure changes,
        # so it requires manual exploration.
        # For example, leads might be in: data[0][1]...
        return data

    except Exception as e:
        logging.error(f"Failed to parse embedded JSON: {e}")
        return None


def _serpapi_maps_query(query, location, api_key, max_results=10):
    # ... (This function remains the same as the last version)
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "Maps",
        "q": query,
        "type": "search",
        "api_key": api_key,
        "hl": "en",
        "gl": "us"
    }
    if "," in location:
        params["ll"] = f"@{location},15z"
    else:
        params["location"] = location
    logging.info(f"DEBUG: Sending params to SerpApi: {params}")
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        places = data.get("local_results", [])
        if not places:
             logging.warning(f"SerpApi returned no 'local_results' for '{query}' in '{location}'.")
        return [{
            "title": p.get("title"),
            "url": p.get("website"),
            "contact": p.get("phone"),
            "subject": f"Inquiry for {query.capitalize()} Services",
            "status": "found",
        } for p in places[:max_results] if p.get("website")]
    except requests.exceptions.HTTPError as e:
        logging.error(f"Maps query failed with HTTP Error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        logging.error(f"Maps query failed with an unexpected error: {e}")
        return []


def discover_leads(city, category, max_results=10, filter_aggregators=False, use_maps=False):
    """Discovers leads from search engines."""
    serpapi_key = os.getenv("SERPAPI_KEY")

    if use_maps:
        if not serpapi_key:
            logging.error("SERPAPI_KEY not found. Cannot use --use-maps.")
            return []
        return _serpapi_maps_query(category, city, serpapi_key, max_results)

    # --- Fallback Logic ---
    logging.info(f"Using Scrapfly for SERP fallback for '{category}'")
    try:
        search_query = quote_plus(f"{category} in {city}")
        result = scrapfly_fetch(f"https://www.google.com/search?q={search_query}&hl=en&gl=us", render_js=True, asp=True)
        html = result.get("html", "")
        if not html:
            logging.error("Scrapfly fallback returned no HTML.")
            return []

        # <<< --- INTEGRATION OF ADVANCED PARSING --- >>>
        # 1. First, try the robust JSON parsing method.
        # This is where you would process the returned 'data' to extract leads.
        # For now, we are just proving we can parse it.
        json_data = parse_embedded_json(html)
        if json_data:
             # NOTE: This is your next development task. You need to explore the 'json_data'
             # dictionary to extract the list of businesses and their websites.
             # Once you do, you can return those leads here.
             logging.info("JSON data was found, but lead extraction from JSON is not yet implemented.")


        # 2. If JSON parsing fails, use the simple HTML tag method.
        logging.warning("JSON parsing failed or is not yet implemented. Trying simple HTML parsing.")
        soup = BeautifulSoup(html, 'lxml')
        results = []
        for result_container in soup.select("div.g"): # This selector may need updates
            link_tag = result_container.select_one("a[href]")
            link = link_tag.get('href') if link_tag else None
            if not link or not link.startswith('http'):
                continue
            if filter_aggregators and any(p in urlparse(link).netloc for p in AGGREGATOR_PATTERNS):
                continue
            if not any(urlparse(link).netloc == urlparse(res.get('url', '')).netloc for res in results):
                title_tag = result_container.select_one('h3')
                title = title_tag.get_text(strip=True) if title_tag else category
                results.append({ "title": title, "url": link, "status": "found" })
            if len(results) >= max_results:
                break
        
        if not results:
            logging.warning("Simple HTML parser found 0 leads. The Google SERP structure may have changed or the page was blocked.")
        return results

    except Exception as e:
        logging.error(f"SERP fallback failed entirely: {e}")
        return []