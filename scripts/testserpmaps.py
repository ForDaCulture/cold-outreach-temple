#!/usr/bin/env python3
import os
import csv
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

def maps_scrape(lat, lng, query, limit):
    key = os.getenv("SERPAPI_KEY")
    if not key:
        raise RuntimeError("SERPAPI_KEY not set in .env")
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_maps",
        "q": query,
        "ll": f"@{lat},{lng},14z",
        "type": "search",
        "api_key": key
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("places_results", [])[:limit]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lng", type=float, required=True)
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", type=str, default="maps_results.csv")
    args = parser.parse_args()

    places = maps_scrape(args.lat, args.lng, args.query, args.limit)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "address", "phone", "website"])
        writer.writeheader()
        for p in places:
            writer.writerow({
                "title": p.get("title"),
                "address": p.get("address"),
                "phone": p.get("phone"),
                "website": p.get("website")
            })

    print(f"Saved {len(places)} results to {args.out}")
