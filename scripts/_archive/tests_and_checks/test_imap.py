import imaplib, os
from dotenv import load_dotenv

load_dotenv('/home/james/stacklabs/.env')
USERNAME = os.getenv("GMAIL_USER", "jc2pointzero@gmail.com")
PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(USERNAME, PASSWORD)
mail.select('inbox')

# Test different variations
for query in ['label:daily-mlb', 'label:"daily mlb"', 'label:Daily_MLB']:
    typ, messages = mail.search(None, 'X-GM-RAW', f'"{query}"')
    if messages and messages[0]:
        print(f"Found with {query}: {len(messages[0].split())}")
    else:
        print(f"Nothing for {query}")
mail.logout()
