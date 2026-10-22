import imaplib
import email
from email.header import decode_header
import configparser
import os
from dotenv import load_dotenv

load_dotenv("/home/james/stacklabs/.env")

username = os.getenv("GMAIL_USER")
password = os.getenv("GMAIL_APP_PASSWORD")

def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)

def check_email():
    print(f"[*] Connecting to IMAP server for {username}...")
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    
    try:
        imap.login(username, password)
        print("[*] Successfully authenticated!")
    except imaplib.IMAP4.error as e:
        print(f"[!] Login failed: {e}")
        return
        
    status, messages = imap.select("INBOX")
    
    if status == "OK":
        messages = int(messages[0])
        print(f"[*] Total messages in INBOX: {messages}")
        
        # Fetch the latest 5 messages
        for i in range(messages, messages-5, -1):
            if i <= 0:
                break
                
            res, msg = imap.fetch(str(i), "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    msg = email.message_from_bytes(response[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    from_ = msg.get("From")
                    print(f"\n--- Message {i} ---")
                    print(f"From: {from_}")
                    print(f"Subject: {subject}")
                    
                    # if the email message is multipart
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    print(f"Body: {body[:250]}...")
                                except:
                                    pass
                    else:
                        content_type = msg.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = msg.get_payload(decode=True).decode()
                                print(f"Body: {body[:250]}...")
                            except:
                                pass
    imap.close()
    imap.logout()

if __name__ == "__main__":
    check_email()
