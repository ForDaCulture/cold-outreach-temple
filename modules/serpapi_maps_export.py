#!/usr/bin/env python3
"""
serpapi_maps_export.py
Query SerpApi google_maps engine for a keyword near lat,lng and export up to N places to CSV.

Usage:
  python scripts/serpapi_maps_export.py --q hvac --latlng "42.640999,-71.316711" --limit 50 --out hvac_lowell.csv
"""
import argparse
import csv
import os
import logging
from dotenv import load_dotenv
from modules.lead_discovery import _serpapi_maps_query  # Assume this exists; if not, implement here

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument('--q', required=True, help='Query term, e.g. hvac')
    p.add_argument('--latlng', help='lat,lng e.g. 42.640999,-71.316711 (optional if --city used)')
    p.add_argument('--city', help='City name as fallback if no latlng')
    p.add_argument('--limit', type=int, default=50)
    p.add_argument('--out', default='places_export.csv')
    return p

def main():
    args = build_parser().parse_args()
    serp_key = os.getenv('SERPAPI_KEY')
    if not serp_key:
        logging.error("SERPAPI_KEY not set in .env (required).")
        return

    if not args.latlng and not args.city:
        logging.error("Provide --latlng or --city.")
        return

    location = args.latlng or args.city
    places = _serpapi_maps_query(args.q, location, serp_key, max_results=args.limit)
    if not places:
        logging.warning("No places returned.")
        return

    # Expanded fields for more data
    fields = ['title', 'phone', 'address', 'website', 'cid', 'lat', 'lng', 'rating', 'reviews_count', 'category']
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for p in places:
            writer.writerow({
                'title': p.get('title'),
                'phone': p.get('phone'),
                'address': p.get('address'),
                'website': p.get('website'),
                'cid': p.get('cid'),
                'lat': p.get('lat'),
                'lng': p.get('lng'),
                'rating': p.get('rating'),
                'reviews_count': p.get('reviews_total'),  # Assuming key exists
                'category': p.get('category'),
            })
    logging.info(f"Wrote {len(places)} places to {args.out}")

if __name__ == '__main__':
    main()