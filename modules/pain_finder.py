# modules/pain_finder.py (Upgraded with AI)
import re
import os
import openai
from bs4 import BeautifulSoup

# Initialize the OpenAI client
# It will automatically pick up the OPENAI_API_KEY from your .env file
client = openai.OpenAI()

def check_structural_points(page_content):
    """
    Analyzes objective, structural issues of the website.
    `page_content` is the dictionary from fetch_page.
    """
    pains = []
    url = page_content.get('url', '')
    html = page_content.get('html', '')
    headers = page_content.get('headers', {})
    
    # 1. Cybersecurity: Check for SSL
    if not url.startswith('https://'):
        pains.append("The website does not use a secure SSL certificate (HTTPS), which can harm user trust and SEO rankings.")

    # 2. Web Design: Check for Mobile-Friendliness
    if '<meta name="viewport"' not in html:
        pains.append("The website appears to be missing a mobile viewport tag, suggesting it may not be mobile-friendly.")

    # 3. Data Engineering: Check for Google Analytics
    if 'google-analytics.com/ga.js' not in html and 'googletagmanager.com/gtag/js' not in html:
        pains.append("I couldn't detect a standard Google Analytics or Tag Manager script, meaning you might be missing key insights into your visitor traffic.")
        
    # 4. Web Design: Check for missing image alt tags (Accessibility/SEO)
    soup = BeautifulSoup(html, 'html.parser')
    images = soup.find_all('img')
    missing_alt_tags = sum(1 for img in images if not img.get('alt', '').strip())
    if missing_alt_tags > 5: # If more than 5 images are missing alt text
        pains.append(f"Found {missing_alt_tags} images without descriptive 'alt' text, which negatively impacts SEO and accessibility.")

    return pains


def analyze_content_with_ai(html_text):
    """
    Uses OpenAI's API to analyze the website content for more nuanced pain points.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return ["AI analysis skipped: OPENAI_API_KEY not found."]

    # Use BeautifulSoup to get clean text, which is cheaper and more effective
    soup = BeautifulSoup(html_text, 'html.parser')
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text(separator=' ', strip=True)
    
    # Truncate to avoid excessive token usage
    max_chars = 12000 # Roughly 3000 tokens
    truncated_text = text[:max_chars]

    # This prompt is key. We're telling the AI to act as a consultant.
    prompt = f"""
    You are a web conversion and cybersecurity consultant analyzing a small business website. 
    Based on the following text content from their site, identify 2-3 key "pain points" or missed opportunities. 
    Focus on things that would prevent a customer from taking action. Frame each point as a constructive observation.

    Examples of good pain points:
    - "The site lacks a clear, prominent call-to-action on the homepage."
    - "The services described are very generic and could benefit from customer testimonials or case studies to build trust."
    - "There is no mention of emergency services or fast response times, which is a key selling point in this industry."
    - "Contact information is difficult to locate, buried in the footer."

    Analyze this text:
    ---
    {truncated_text}
    ---
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful consultant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=200,
            n=1
        )
        ai_pains = response.choices[0].message.content.strip().split('\n')
        # Clean up the response, removing any leading dashes or numbers
        return [re.sub(r'^[-\d\.\s]*', '', pain) for pain in ai_pains if pain]
    except Exception as e:
        return [f"AI analysis failed: {e}"]


def find_structural_and_ai_pain_points(page_content):
    """
    Main function to be called from main.py.
    Combines structural and AI analysis for a comprehensive list of pain points.
    """
    structural_pains = check_structural_points(page_content)
    ai_pains = analyze_content_with_ai(page_content.get('html', ''))
    
    # Combine and return a unique list
    all_pains = list(dict.fromkeys(structural_pains + ai_pains))
    return all_pains[:5] # Return top 5 most relevant pains