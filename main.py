# main.py (Refactored)
import argparse
import logging
import os
import time
from urllib.parse import urlparse
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# Import modules from the modules package
from modules.lead_discovery import discover_leads
from modules.scraper import fetch_page
from modules.contact_extractor import extract_contacts_from_html
from modules.pain_finder import find_pain_points
from modules.email_generator import generate_email, preview_email
from modules.sender import send_email_with_approval
from modules.logger_module import OutreachLogger
from modules.history_manager import HistoryManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def build_parser():
    """Builds the command-line argument parser."""
    p = argparse.ArgumentParser(description="Automated outreach bot for local businesses.")
    p.add_argument('--city', required=True, help='Target city, e.g., "Boston, MA"')
    p.add_argument('--category', required=True, help='Business categories, comma-separated, e.g., "hvac,plumbing"')
    p.add_argument('--max', type=int, default=10, help='Max leads to process per category')
    p.add_argument('--recall-history', type=int, default=0, help='Number of past runs to recall for context')
    p.add_argument('--dry-run', action='store_true', help='Preview emails without sending')
    p.add_argument('--filter-aggregators', action='store_true', help='Filter out aggregators like Yelp, Angi')
    p.add_argument('--use-maps', action='store_true', help='Use SerpApi Google Maps for lead discovery')
    p.add_argument('--use-selenium', action='store_true', help='Use Selenium as a fallback for scraping')
    return p

def main():
    """Main execution function."""
    args = build_parser().parse_args()
    logger = OutreachLogger()
    history = HistoryManager()

    if args.recall_history > 0:
        past_runs = history.get_last_runs(args.recall_history)
        logging.info(f"Recalled {len(past_runs)} past runs")
        # Future: Use past_runs to influence new searches

    # **IMPROVEMENT**: Split categories to search for each one individually
    categories = [cat.strip() for cat in args.category.split(',')]
    all_leads = []
    for category in categories:
        logging.info(f"🔎 Discovering {category} in {args.city}")
        leads = discover_leads(
            city=args.city,
            category=category,
            max_results=args.max,
            filter_aggregators=args.filter_aggregators,
            use_maps=args.use_maps
        )
        if not leads:
            logging.warning(f"No leads found for {category}. Try adjusting search parameters.")
            continue
        all_leads.extend(leads)

    if not all_leads:
        logging.warning("No leads found across all categories.")
        return

    logging.info(f"Processing {len(all_leads)} total leads...")
    # **IMPROVEMENT**: Use tqdm for a progress bar
    for lead in tqdm(all_leads, desc="Processing Leads"):
        url = lead.get("url")
        if not url or not url.startswith('http'):
            logging.warning(f"Skipping lead with invalid URL: {url}")
            continue

        if logger.already_processed(url):
            logging.info(f"Skipping already processed URL: {url}")
            continue

        logging.info(f"Scraping {url}...")
        page_content = fetch_page(url, use_selenium=args.use_selenium, render_js=True)
        html = page_content.get('html')
        if not html:
            logging.error(f"Failed to fetch HTML for {url}")
            logger.record(url=url, status='fetch_failed')
            continue

        contacts = extract_contacts_from_html(html, base_url=url)
        pain_points = find_pain_points(html)
        logging.info(f"Found contacts: Emails - {len(contacts.get('emails', []))}, Phones - {len(contacts.get('phones', []))}")
        logging.info(f"Found pain points: {pain_points}")

        # **FIX**: Pass the 'contacts' object into the context dictionary
        context = {
            'lead': lead,
            'contacts': contacts,
            'pain_text': '\n- '.join(pain_points),
            'domain': urlparse(url).netloc
        }

        subject, body = generate_email(context, use_openai=bool(os.getenv("OPENAI_API_KEY")))
        preview_email(subject, body)

        if contacts.get('emails'):
            recipient_email = contacts['emails'][0]
            success = send_email_with_approval(recipient_email, subject, body, dry_run=args.dry_run, is_html=True)
            status = 'sent_successfully' if success else 'send_failed'
            logger.record(url=url, contact=recipient_email, subject=subject, status=status)
        else:
            logging.warning(f"No email found for {url}. Logging as 'no_email'.")
            logger.record(url=url, status='no_email')

        # Be polite to servers
        time.sleep(2)

    history.append_run(summary={'args': vars(args), 'leads_processed': len(all_leads)})
    logging.info("✅ Run complete.")

if __name__ == '__main__':
    main()