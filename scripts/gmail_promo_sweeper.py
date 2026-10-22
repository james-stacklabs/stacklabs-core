import imaplib
import email
import re
import os
import json
import uuid
from bs4 import BeautifulSoup
from email.header import decode_header
from dotenv import load_dotenv

# Load credentials from .env file (you need to create this with GMAIL_USER and GMAIL_APP_PASSWORD)
load_dotenv(dotenv_path="/home/james/stacklabs/.env", override=True)
USERNAME = os.getenv("GMAIL_USER", "sovereign.fanstack@gmail.com")
PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "YOUR_APP_PASSWORD_HERE") 

# Connection settings
IMAP_SERVER = "imap.gmail.com"
CONTEXT_FILE = "/home/james/stacklabs/scripts/fanstack_live_context.txt"
STAGING_FILE = "/home/james/stacklabs/scripts/promo_staging.json"

def extract_promotional_entropy(html_content):
    """
    The Regex Chainsaw: Strips HTML and extracts the pure cheese viscosity.
    Looks for prices, dates, and capitalized marketing nouns.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    
    # Extract $ amounts
    prices = re.findall(r'\$\d+(?:\.\d{2})?', text)
    # Extract Dates (e.g. May 15-17, June 6)
    dates = re.findall(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:-\d{1,2})?', text)
    
    # Grab the juiciest sentence containing a price, date, or exclamations
    sentences = text.split('.')
    promo_lines = [s.strip() for s in sentences if '$' in s or 'Night' in s or 'Free' in s or '!' in s]
    
    if promo_lines:
        return " | ".join(set(promo_lines[:2])) # Return the top 2 juiciest lines
    
    # Better fallback: Grab the first two full sentences
    clean_sentences = [s.strip() for s in sentences if s.strip()]
    if len(clean_sentences) >= 2:
        return clean_sentences[0] + ". " + clean_sentences[1] + "."
    elif clean_sentences:
        return clean_sentences[0] + "."
    return text[:150] + "..." # Fallback

def process_nested_eml(eml_bytes):
    """
    Parses nested .eml bytes and extracts its sender, subject, and body content.
    """
    try:
        nested_msg = email.message_from_bytes(eml_bytes)
        
        # Decode Subject
        sub = nested_msg.get("Subject", "(No Subject)")
        decoded = decode_header(sub)[0]
        if isinstance(decoded[0], bytes):
            nested_subject = decoded[0].decode(decoded[1] if decoded[1] else "utf-8", errors="ignore")
        else:
            nested_subject = str(decoded[0])
            
        nested_sender = nested_msg.get("From", "(Unknown Sender)")
        
        # Extract body
        nested_body = ""
        if nested_msg.is_multipart():
            for nested_part in nested_msg.walk():
                c_type = nested_part.get_content_type()
                if c_type == "text/html":
                    nested_body = nested_part.get_payload(decode=True).decode(errors="ignore")
                    break
                elif c_type == "text/plain":
                    nested_body = nested_part.get_payload(decode=True).decode(errors="ignore")
        else:
            payload_data = nested_msg.get_payload(decode=True)
            if payload_data:
                nested_body = payload_data.decode(errors="ignore")
            
        return nested_sender, nested_subject, nested_body
    except Exception as e:
        print(f"Error parsing nested EML: {e}")
        return None


def sweep_inbox():
    print(f"Connecting to {IMAP_SERVER} as {USERNAME}...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(USERNAME, PASSWORD)
    except Exception as e:
        print(f"Login failed! Generate an App Password in your Google Account: {e}")
        return

    # Select the root inbox for the new dedicated burner account
    mail.select('inbox')
    _, messages = mail.search(None, 'UNSEEN')
    
    email_ids = []
    if messages and messages[0]:
        email_ids = messages[0].split()
        
    if not email_ids:
        print("No promotional emails found in label:daily-mlb.")
        return

    print(f"Revving the chainsaw... Found {len(email_ids)} promos waiting in daily-mlb.")
    
    new_context_entries = []

    for e_id in email_ids:
        res, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Decode Subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                # Decode Sender
                sender = msg.get("From")
                print(f"Extracting: {sender} - {subject}")
                
                body = ""
                attachments_found = False
                
                if msg.is_multipart():
                    for part in msg.walk():
                        filename = part.get_filename()
                        c_type = part.get_content_type()
                        
                        # Process .eml attachments
                        if (filename and filename.lower().endswith('.eml')) or c_type == 'message/rfc822':
                            attachments_found = True
                            eml_bytes = part.get_payload(decode=True)
                            if not eml_bytes and c_type == 'message/rfc822':
                                sub_payload = part.get_payload()
                                if isinstance(sub_payload, list) and len(sub_payload) > 0:
                                    eml_bytes = sub_payload[0].as_bytes()
                                elif hasattr(sub_payload, 'as_bytes'):
                                    eml_bytes = sub_payload.as_bytes()
                                    
                            if eml_bytes:
                                print(f"  ↳ Found nested EML attachment: {filename or 'message/rfc822'}")
                                nested_info = process_nested_eml(eml_bytes)
                                if nested_info:
                                    nested_sender, nested_subject, nested_body = nested_info
                                    nested_details = extract_promotional_entropy(nested_body)
                                    print(f"    ✓ Unpacked nested email: {nested_sender} - {nested_subject}")
                                    
                                    nested_injection = f"[CRITICAL PROMO DROP] {nested_sender} announces: {nested_subject}. HIGHLIGHTS: {nested_details}\n"
                                    promo_data = {
                                        "id": str(uuid.uuid4()),
                                        "source": nested_sender,
                                        "headline": nested_subject,
                                        "details": nested_details,
                                        "raw_text": nested_injection
                                    }
                                    new_context_entries.append(promo_data)
                                    
                        elif c_type == "text/html" and not body:
                            body_bytes = part.get_payload(decode=True)
                            if body_bytes:
                                body = body_bytes.decode(errors="ignore")
                        elif c_type == "text/plain" and not body:
                            body_bytes = part.get_payload(decode=True)
                            if body_bytes:
                                body = body_bytes.decode(errors="ignore")
                else:
                    body_payload = msg.get_payload(decode=True)
                    if body_payload:
                        body = body_payload.decode(errors="ignore")
                
                # If we found EML attachments, we prioritize their rich content.
                # Otherwise, we fallback to processing the main wrapper body.
                if body and body.strip() and not attachments_found:
                    # Run the Regex Chainsaw
                    juicy_details = extract_promotional_entropy(body)
                    
                    # Format for the Staging Area
                    injection = f"[CRITICAL PROMO DROP] {sender} announces: {subject}. HIGHLIGHTS: {juicy_details}\n"
                    
                    promo_data = {
                        "id": str(uuid.uuid4()),
                        "source": sender,
                        "headline": subject,
                        "details": juicy_details,
                        "raw_text": injection
                    }
                    new_context_entries.append(promo_data)
                
                # Mark as Read so we don't process it again
                mail.store(e_id, '+FLAGS', '\\Seen')

    mail.logout()

    # Move to the Cosmic Sieve (Staging Area)
    if new_context_entries:
        try:
            with open(STAGING_FILE, "r") as f:
                staging_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            staging_data = []
            
        staging_data.extend(new_context_entries)
        
        with open(STAGING_FILE, "w", encoding="utf-8") as f:
            json.dump(staging_data, f, indent=4)
        print(f"Successfully staged {len(new_context_entries)} promos in The Cosmic Sieve!")

if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        import time
        print("Starting Gmail Promo Sweeper Daemon... Polling every 300 seconds.")
        while True:
            try:
                sweep_inbox()
            except Exception as e:
                print(f"Error during inbox sweep: {e}")
            time.sleep(300)
    else:
        print("Running one-off Gmail Promo Sweeper...")
        sweep_inbox()

