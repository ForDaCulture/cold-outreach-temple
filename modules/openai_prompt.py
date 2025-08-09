# modules/openai_prompt.py
import os, logging, json, re
try:
    import openai
except Exception:
    openai = None

FEW_SHOT = [
    {"role":"system","content":
     "You are a concise, human-sounding outreach writer for local businesses. "
     "Do NOT use placeholders such as [Your Name], {company}, <...>, or any bracketed tokens. "
     "Do NOT write 'As an AI language model' or mention that you are AI. "
     "Write short, plain-language emails (about 70-140 words) and end with a signature consisting of the sender name and website only (no extra placeholders)."
    }
]

# Reuse the sanitize routine to strip bracket tokens and AI phrases in the assistant output
def _post_sanitize(text: str) -> str:
    if not text:
        return text
    # remove bracket tokens and braces
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\{.*?\}', '', text)
    text = re.sub(r'<.*?>', '', text)
    # remove AI phrases
    text = re.sub(r'(?i)as an ai language model', '', text)
    text = re.sub(r'(?i)i am an ai', '', text)
    text = re.sub(r'(?i)as an ai', '', text)
    text = re.sub(r'(?i)i\'m an ai', '', text)
    # collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def personalize_email_body(context, base_body, model='gpt-4o-mini', temp=0.6, max_tokens=300):
    """
    Call OpenAI (if available) to rewrite and personalize base_body.
    After LLM output, perform post-processing to remove placeholders and AI signatures.
    """
    if not openai:
        logging.warning("OpenAI SDK not installed; returning base body.")
        return base_body
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        logging.warning("OPENAI_API_KEY missing; returning base body.")
        return base_body
    openai.api_key = key

    # Build user content: include lead, detected pains, and the base email
    user_content = {
        'lead': context.get('lead', {}),
        'pain_text': context.get('pain_text', ''),
        'base_email': base_body
    }

    messages = []
    messages.extend(FEW_SHOT)
    messages.append({'role': 'user', 'content': json.dumps(user_content)})

    try:
        # Use ChatCompletion or the compatible method on the SDK available
        resp = openai.ChatCompletion.create(model=model, messages=messages, temperature=temp, max_tokens=max_tokens)
        out = resp.choices[0].message.content
        out = _post_sanitize(out)

        # Ensure signature includes website; do not invent sender name if env not set,
        # but always include SENDER_WEBSITE if available
        sender_name = os.getenv('SENDER_NAME', '').strip()
        sender_website = os.getenv('SENDER_WEBSITE', 'https://retrohacker-portfolio.vercel.app/').strip()
        # If the model accidentally left a placeholder signature, remove it and append ours
        # remove trailing lines that look like signature placeholders
        out = re.sub(r'(?i)(best regards|best|regards|sincerely)[\s\S]*$', '', out).strip()
        signature = ("\n\n" + (f"Best,\n{sender_name}\n{sender_website}" if sender_name else f"Best regards,\n{sender_website}"))
        out = out + signature

        # Final sanitize pass (remove bracket tokens again)
        out = _post_sanitize(out)
        return out
    except Exception as e:
        logging.warning("OpenAI personalize failed: %s", e)
        return base_body
