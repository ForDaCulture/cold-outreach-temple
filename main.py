import argparse
from modules.lead_discovery import discover_leads
from modules.scraper import scrape_website
from modules.contact_extractor import extract_contacts
from modules.pain_finder import find_pain_points
from modules.email_generator import generate_email
from modules.sender import send_email
from modules.logger_module import OutreachLogger
from modules.history_manager import HistoryManager

def main():
    parser = argparse.ArgumentParser(description="Cold Email Analyzer with history recall")
    parser.add_argument("--city", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--max", type=int, default=8)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--recall-history", type=int, default=0)
    args = parser.parse_args()

    logger = OutreachLogger()
    history = HistoryManager()

    recalled_runs = []
    if args.recall_history > 0:
        recalled_runs = history.get_recent_runs(args.recall_history)

    leads = discover_leads(args.city, args.category, args.max)
    for lead in leads:
        if args.resume and logger.is_logged(lead['url']):
            continue
        content = scrape_website(lead['url'])
        contacts = extract_contacts(content)
        pain_points = find_pain_points(content)
        email_text = generate_email(lead, contacts, pain_points, recalled_runs)
        print(email_text)
        send_email(contacts.get('email'), email_text)
        logger.log(lead['url'], contacts.get('email'))
        history.save_run(lead, pain_points)

if __name__ == "__main__":
    main()
