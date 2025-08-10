# main.py (Modified)
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
# IMPORTANT: Import our new and improved pain finder
from modules.pain_finder import find_structural_and_ai_pain_points 
from modules.email_generator import generate_email, preview_email
from modules.sender import send_email_with_approval
from modules.logger_module import OutreachLogger
from modules.history_manager import HistoryManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def build_parser():
    """Builds the command-line argument parser."""
    p = argparse.ArgumentParser(description="Automated outreach bot for local businesses.")
    
    # --- Group for lead source ---
    source_group = p.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--url-file', help='Path to a file containing a list of URLs to process.')
    source_group.add_argument('--city', help='Target city, e.g., "Boston, MA"')

    p.add_argument('--category', help='Business categories (used with --city), comma-separated, e.g., "hvac,plumbing"')
    p.add_argument('--max', type=int, default=10, help='Max leads to process per category')
    p.add_argument('--dry-run', action='store_true', help='Preview emails without sending')
    p.add_argument('--use-selenium', action='store_true', help='Use Selenium for scraping')
    return p

def load_leads_from_file(filepath):
    """Loads URLs from a text file and formats them as leads."""
    try:
        with open(filepath, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        # Format as a list of lead dictionaries to match discover_leads() output
        return [{'url': url, 'title': urlparse(url).netloc} for url in urls]
    except FileNotFoundError:
        logging.error(f"URL file not found at: {filepath}")
        return []

def main():
    """Main execution function."""
    args = build_parser().parse_args()
    logger = OutreachLogger()
    history = HistoryManager()

    all_leads = []
    if args.url_file:
        logging.info(f"💾 Loading leads from file: {args.url_file}")
        all_leads = load_leads_from_file(args.url_file)
    elif args.city:
        if not args.category:
            logging.error("The --category argument is required when using --city.")
            return
            
        categories = [cat.strip() for cat in args.category.split(',')]
        for category in categories:
            logging.info(f"🔎 Discovering {category} in {args.city}")
            leads = discover_leads(
                city=args.city,
                category=category,
                max_results=args.max
            )
            if leads:
                all_leads.extend(leads)
    
    if not all_leads:
        logging.warning("No leads to process. Exiting.")
        return

    logging.info(f"Processing {len(all_leads)} total leads...")
    for lead in tqdm(all_leads, desc="Processing Leads"):
        url = lead.get("url")
        if not url or not url.startswith('http'):
            logging.warning(f"Skipping lead with invalid URL: {url}")
            continue

        if logger.already_processed(url):
            logging.info(f"Skipping already processed URL: {url}")
            continue

        logging.info(f"Scraping {url}...")
        # We need the full page content object now, not just html
        page_content = fetch_page(url, use_selenium=args.use_selenium, render_js=True)
        html = page_content.get('html')
        
        if not html:
            logging.error(f"Failed to fetch HTML for {url}")
            logger.record(url=url, status='fetch_failed')
            continue

        contacts = extract_contacts_from_html(html, base_url=url)
        
        # --- THIS IS THE KEY UPGRADE ---
        # We pass the full page_content object to our new function
        logging.info("Analyzing for pain points...")
        pain_points = find_structural_and_ai_pain_points(page_content)
        
        logging.info(f"Found contacts: Emails - {len(contacts.get('emails', []))}")
        logging.info(f"Found pain points: {pain_points}")

        context = {
            'lead': lead,
            'contacts': contacts,
            'pain_text': '\n- '.join(pain_points), # Formats list for the email
            'domain': urlparse(url).netloc
        }

        # The rest of your logic remains the same...
        subject, body = generate_email(context, use_openai=True)
        preview_email(subject, body)

        if contacts.get('emails'):
            recipient_email = contacts['emails'][0]
            success = send_email_with_approval(recipient_email, subject, body, dry_run=args.dry_run, is_html=True)
            status = 'sent_successfully' if success else 'send_failed'
            logger.record(url=url, contact=recipient_email, subject=subject, status=status)
        else:
            logging.warning(f"No email found for {url}. Logging as 'no_email'.")
            logger.record(url=url, status='no_email')

        time.sleep(2)

    history.append_run(summary={'args': vars(args), 'leads_processed': len(all_leads)})
    logging.info("✅ Run complete.")

if __name__ == '__main__':
    main()