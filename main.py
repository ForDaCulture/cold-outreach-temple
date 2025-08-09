#!/usr/bin/env python3
import argparse
import logging
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

from modules.lead_discovery import discover_leads
from modules.scrapfly_helper import scrapfly_fetch

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def save_csv(leads, filename="leads.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "url", "contact", "subject", "status"])
        writer.writeheader()
        for lead in leads:
            writer.writerow({
                "timestamp": datetime.utcnow().isoformat(),
                "url": lead.get("url"),
                "contact": lead.get("contact", ""),
                "subject": lead.get("subject", ""),
                "status": lead.get("status", "")
            })
    logging.info(f"Saved {len(leads)} leads to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True, help="City or location for search")
    parser.add_argument("--category", required=True, help="Business category to search for")
    parser.add_argument("--max", type=int, default=10, help="Max leads to fetch")
    parser.add_argument("--recall-history", type=int, default=0, help="Recall from previous searches")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending emails")
    parser.add_argument("--filter-aggregators", action="store_true", help="Filter out government and large aggregator sites")
    parser.add_argument("--use-maps", action="store_true", help="Use Google Maps engine via SerpApi")
    args = parser.parse_args()

    logging.info(f"🔎 Discovering {args.category} in {args.city}")

    leads = discover_leads(
        args.city,
        args.category,
        max_results=args.max,
        filter_aggregators=args.filter_aggregators,
        use_maps=args.use_maps
    )

    if not leads:
        logging.warning("No leads found. Try adjusting search parameters.")
        exit()

    save_csv(leads)
