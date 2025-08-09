def generate_email(lead, contacts, pains, recalled):
    history_note = f"\nPrevious runs: {recalled}" if recalled else ''
    return f"Hi {lead['name']}, I noticed {', '.join(pains)} on your site.{history_note}\nLet's discuss improvements."
