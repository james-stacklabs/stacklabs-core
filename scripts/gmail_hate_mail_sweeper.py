#!/usr/bin/env python3
import imaplib
import socket
socket.setdefaulttimeout(20)
import email
import re
import os
import json
import uuid
from bs4 import BeautifulSoup
from email.header import decode_header
from dotenv import load_dotenv

# Connection settings
IMAP_SERVER = "imap.gmail.com"
STAGING_FILE = "/home/james/stacklabs/scripts/hate_mail_staging.json"


def clean_hate_content(html_content):
    """
    The Regex Chainsaw: Strips HTML and extracts the pure detractor/fan comment sentences.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    
    # Try to locate comment body in Reddit notification emails
    sentences = text.split('.')
    clean_sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(clean_sentences) >= 2:
        return clean_sentences[0] + ". " + clean_sentences[1] + "."
    elif clean_sentences:
        return clean_sentences[0] + "."
    return text[:200] + "..."

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

def sweep_single_persona(persona_name, username, password):
    print("=========================================================")
    print(f"🏴‍☠️ SWEEPING MAILBAG FOR PERSONA: {persona_name.upper()}")
    print(f"Connecting to {IMAP_SERVER} as {username}...")
    print("=========================================================")
    
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(username, password)
    except Exception as e:
        print(f"❌ Login failed for persona {persona_name}! Error: {e}")
        return []

    # Select active inbox folder
    mail.select('inbox')
    _, messages = mail.search(None, 'UNSEEN')
    
    email_ids = []
    if messages and messages[0]:
        email_ids = messages[0].split()
        
    if not email_ids:
        print(f"✔ No new comments found in {username} inbox.")
        mail.logout()
        return []

    print(f"🔥 Revving the chainsaw... Found {len(email_ids)} unseen EML notifications for {persona_name}.")
    
    persona_entries = []

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
                print(f"[+] Ingesting EML [{persona_name}]: {sender} - {subject}")
                
                body = ""
                attachments_found = False
                
                if msg.is_multipart():
                    for part in msg.walk():
                        filename = part.get_filename()
                        c_type = part.get_content_type()
                        
                        # Process nested forwarded .eml attachments
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
                                    nested_details = clean_hate_content(nested_body)
                                    print(f"    ✓ Unpacked nested email: {nested_sender} - {nested_subject}")
                                    
                                    nested_injection = f"[CRITICAL PROMO DROP] {nested_sender} announces: {nested_subject}. HIGHLIGHTS: {nested_details}\n"
                                    promo_data = {
                                        "id": str(uuid.uuid4()),
                                        "source": nested_sender,
                                        "headline": nested_subject,
                                        "details": nested_details,
                                        "raw_text": nested_injection,
                                        "persona": persona_name
                                    }
                                    persona_entries.append(promo_data)
                                    
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
                
                # Process the main body if no EML attachments were unpacked
                if body and body.strip() and not attachments_found:
                    juicy_details = clean_hate_content(body)
                    injection = f"[CRITICAL PROMO DROP] {sender} announces: {subject}. HIGHLIGHTS: {juicy_details}\n"
                    
                    promo_data = {
                        "id": str(uuid.uuid4()),
                        "source": sender,
                        "headline": subject,
                        "details": juicy_details,
                        "raw_text": injection,
                        "persona": persona_name
                    }
                    persona_entries.append(promo_data)
                
                # Mark as Read/Seen so we don't double-process
                mail.store(e_id, '+FLAGS', '\\Seen')

    mail.logout()
    return persona_entries

def sweep_all_personas():
    load_dotenv(dotenv_path="/home/james/stacklabs/.env", override=True)
    
    # 1. Discover all configured persona gmail settings in env
    personas_to_sweep = {}
    for key, val in os.environ.items():
        if key.endswith("_GMAIL_USER") and val.strip():
            # Extract persona name from prefix (e.g. BARF_GMAIL_USER -> barf)
            persona_name = key[:-11].lower()
            pass_key = f"{persona_name.upper()}_GMAIL_PASS"
            password = os.getenv(pass_key)
            if password and password.strip():
                personas_to_sweep[persona_name] = {
                    "user": val.strip(),
                    "pass": password.strip().replace(" ", "")
                }
                
    # Fallback to barf if no active configs discovered
    if not personas_to_sweep:
        personas_to_sweep["barf"] = {
            "user": os.getenv("BARF_GMAIL_USER", "underpantsbandito@gmail.com"),
            "pass": os.getenv("BARF_GMAIL_PASS", "qbsaakjmnedoazf").replace(" ", "")
        }
        
    print(f"Discovered {len(personas_to_sweep)} persona accounts to sweep: {list(personas_to_sweep.keys())}")
    
    all_new_entries = []
    for persona_name, creds in personas_to_sweep.items():
        entries = sweep_single_persona(persona_name, creds["user"], creds["pass"])
        all_new_entries.extend(entries)
        
    # Save all consolidated entries to the Cosmic Sieve staging file
    if all_new_entries:
        try:
            with open(STAGING_FILE, "r") as f:
                staging_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            staging_data = []
            
        staging_data.extend(all_new_entries)
        
        with open(STAGING_FILE, "w", encoding="utf-8") as f:
            json.dump(staging_data, f, indent=4)
        print(f"\n✔ Successfully staged {len(all_new_entries)} total new entries in The Cosmic Sieve ({STAGING_FILE})!")

if __name__ == "__main__":
    sweep_all_personas()
