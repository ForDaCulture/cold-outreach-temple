# modules/lead_discovery.py (Refactored)
import os
import requests
import logging
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
from modules.serp_proxy import scrapfly_fetch

AGGREGATOR_PATTERNS = [
    "yelp", "angi", "whitepages", "manta", "bbb.org", "yellowpages",
    "houzz", "gov", "facebook.com", "linkedin.com", "support.google.com",
    "thumbtack", "homeadvisor", "clutch.co"
]

def _serpapi_maps_query(query, location, api_key, max_results=10):
    """Queries SerpApi Google Maps and returns structured places."""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "Maps",
        "q": query,
        "type": "search",
        "api_key": api_key,
        "hl": "en", # Ensure english results
        "gl": "us"  # Ensure US-based results
    }
    if "," in location:
        params["ll"] = f"@{location},15z" # Increased zoom for better local accuracy
    else:
        params["location"] = location

    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        places = data.get("local_results", [])
        if not places:
             logging.warning(f"SerpApi returned no 'local_results' for '{query}' in '{location}'. Check API response.")
        # **IMPROVEMENT**: Filter out results that don't have a website
        return [{
            "title": p.get("title"),
            "url": p.get("website"),
            "contact": p.get("phone"),
            "subject": f"Inquiry for {query.capitalize()} Services",
            "status": "found",
            "rating": p.get("rating"),
            "reviews_count": p.get("reviews"),
            "category": p.get("type")
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
    results = []

    if use_maps:
        if not serpapi_key:
            logging.error("SERPAPI_KEY not found in .env, but --use-maps was specified. Cannot proceed with Maps API.")
            return []
        logging.info(f"Using SerpApi Google Maps for {category} in {city}")
        places = _serpapi_maps_query(category, city, serpapi_key, max_results)
        for place in places:
            link = place.get("url")
            if filter_aggregators and link and any(p in link for p in AGGREGATOR_PATTERNS):
                logging.info(f"Filtering aggregator: {link}")
                continue
            results.append(place)
        return results

    # Fallback to general SERP scraping
    logging.info(f"Using Scrapfly for SERP fallback")
    try:
        # **FIX**: URL encode the query to handle special characters (like commas and spaces)
        search_query = quote_plus(f"{category} in {city}")
        result = scrapfly_fetch(f"https://www.google.com/search?q={search_query}&hl=en&gl=us", render_js=True)
        html = result.get("html", "")
        if not html:
            logging.error("Scrapfly fallback returned no HTML.")
            return []

        # **IMPROVEMENT**: Robust HTML parsing for the fallback
        soup = BeautifulSoup(html, 'lxml')
        for link_tag in soup.select('a[href]'):
            link = link_tag.get('href')
            if link and link.startswith('http'):
                # Clean up Google's redirect URLs
                if '/url?q=' in link:
                    link = link.split('/url?q=')[1].split('&sa=U')[0]

                if filter_aggregators and any(p in urlparse(link).netloc for p in AGGREGATOR_PATTERNS):
                    logging.info(f"Filtering aggregator: {link}")
                    continue

                # Avoid adding duplicates from the same domain
                if not any(urlparse(link).netloc == urlparse(res.get('url', '')).netloc for res in results):
                    title_tag = link_tag.find('h3')
                    title = title_tag.get_text(strip=True) if title_tag else category
                    results.append({
                        "title": title,
                        "url": link,
                        "contact": "",
                        "subject": f"Inquiry for {category.capitalize()} Services",
                        "status": "found"
                    })
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        logging.error(f"SERP fallback failed: {e}")
        return []