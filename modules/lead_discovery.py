import os
import requests
import logging
from modules.scrapfly_helper import scrapfly_fetch

AGGREGATOR_PATTERNS = [
    "yelp", "angi", "whitepages", "manta", "bbb.org",
    "yellowpages", "houzz", "gov", "facebook.com", "linkedin.com",
    "support.google.com"
]

def discover_leads(city, category, max_results=10, filter_aggregators=False, use_maps=False):
    serpapi_key = os.getenv("SERPAPI_KEY")
    results = []

    if use_maps and serpapi_key:
        logging.info(f"Using SerpApi Google Maps for {category} in {city}")
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_maps",
            "q": category,
            "location": city,
            "type": "search",
            "api_key": serpapi_key
        }
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            places = data.get("places_results", [])
            for place in places[:max_results]:
                link = place.get("website")
                if filter_aggregators and link and any(p in link for p in AGGREGATOR_PATTERNS):
                    continue
                results.append({
                    "title": place.get("title"),
                    "url": link,
                    "contact": place.get("phone"),
                    "subject": f"{category.capitalize()} Services",
                    "status": "found"
                })
            return results
        except Exception as e:
            logging.error(f"Maps query failed: {e}")
            return []

    logging.info(f"Using Scrapfly for SERP fallback")
    try:
        html = scrapfly_fetch(f"https://www.google.com/search?q={category}+in+{city}")
        # TODO: parse HTML for lead URLs and contacts
    except Exception as e:
        logging.error(f"SERP fallback failed: {e}")

    return results
