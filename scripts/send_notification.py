#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS - Sprint Completion Notification Mailer (WO-2026-116)
# Dispatches a detailed markdown report upon successful session sync.
# ==============================================================================
import os
import sys
import glob
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

ENV_PATH = "/home/james/stacklabs/.env"
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def compile_markdown_summary():
    summary_parts = []
    summary_parts.append("# Sovereign OS - Sprint Completion Report")
    summary_parts.append("The background synchronization run has finished successfully on **Clio Core**.\n")
    
    # 1. Folders Mirrored
    summary_parts.append("## 📡 Cloud Synchronization Trees")
    summary_parts.append("- `/home/james/stacklabs` ⟺ `sovereign_os:SovereignOS_Clio_Sync/SovereignOS/` (Mirror)")
    summary_parts.append("- `/home/james/sovereign_inbox` ⟺ `sovereign_os:SovereignOS_Clio_Sync/sovereign_inbox/` (Mirror)")
    summary_parts.append("")
    
    # 2. Database Status & Recent Tickets
    summary_parts.append("## 🏛️ SQLite Database & SDLC Tickets")
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # Query active / recently resolved tickets
        cursor.execute(
            """
            SELECT number, short_description, state, type 
            FROM sovereign_tickets 
            ORDER BY sys_updated_on DESC LIMIT 5
            """
        )
        recent_tickets = cursor.fetchall()
        
        if recent_tickets:
            summary_parts.append("| Ticket Number | Description | State | Type |")
            summary_parts.append("| --- | --- | --- | --- |")
            for number, desc, state, t_type in recent_tickets:
                state_label = "Resolved (4)" if state == 4 else f"Open ({state})"
                summary_parts.append(f"| {number} | {desc} | {state_label} | {t_type} |")
        else:
            summary_parts.append("_No recent ticket activity found._")
        conn.close()
    except Exception as e:
        summary_parts.append(f"_Error reading tickets database:_ `{e}`")
    summary_parts.append("")
    
    # 3. Compiled Payload Exports
    summary_parts.append("## 📦 Compiled Workspace Payloads")
    exports_dir = "/home/james/stacklabs/dna/notebook_lm_exports"
    if os.path.exists(exports_dir):
        files = glob.glob(os.path.join(exports_dir, "*"))
        if files:
            for f in sorted(files):
                size_kb = os.path.getsize(f) / 1024.0
                summary_parts.append(f"- `{os.path.basename(f)}` ({size_kb:.1f} KB)")
        else:
            summary_parts.append("_No exports files compiled._")
    else:
        summary_parts.append("_NotebookLM exports folder missing._")
    summary_parts.append("")
    
    # 4. Ingested Media Assets
    summary_parts.append("## 🎬 Ingested Media Assets")
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT advocate, expression, file_path 
            FROM cmdb_ci_media_asset 
            ORDER BY sys_updated_on DESC LIMIT 5
            """
        )
        recent_assets = cursor.fetchall()
        if recent_assets:
            summary_parts.append("| Advocate | Expression | File Path |")
            summary_parts.append("| --- | --- | --- |")
            for adv, exp, path in recent_assets:
                summary_parts.append(f"| {adv} | {exp} | `{path}` |")
        else:
            summary_parts.append("_No media assets found in DB._")
        conn.close()
    except Exception as e:
        summary_parts.append(f"_Error reading media assets database:_ `{e}`")
        
    return "\n".join(summary_parts)

def send_notification():
    load_dotenv(ENV_PATH)
    
    # Check if notification emails are enabled (Disabled by default per Pilot directive)
    if os.getenv("SOVEREIGN_SYNC_NOTIFICATIONS", "false").lower() != "true":
        print("ℹ️ Sync completion email notifications are permanently disabled.")
        return True
        
    sender_email = os.getenv("SOVEREIGN_OUTBOUND_USER", "sovereign.os.v1@gmail.com")
    sender_password = os.getenv("SOVEREIGN_OUTBOUND_PASSWORD")
    
    recipients = ["james@stacklabsllc.com", "stacklabs.edge@gmail.com"]
    subject = "[Clio Core] Antigravity Execution Completed — Sprint State Synchronized"
    
    if not sender_password:
        print("[!] Error: SOVEREIGN_OUTBOUND_PASSWORD not defined in .env!", file=sys.stderr)
        sys.exit(1)
        
    body_md = compile_markdown_summary()
    
    msg = MIMEMultipart("alternative")
    msg['From'] = f"Sovereign OS <{sender_email}>"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    
    # Attach plain text markdown body
    msg.attach(MIMEText(body_md, 'plain'))
    
    # Connect and send
    try:
        print("[*] Connecting to SMTP server (smtp.gmail.com:587)...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        
        print("[*] Authenticating with mail server...")
        server.login(sender_email, sender_password)
        
        print("[*] Dispatching emails...")
        server.sendmail(sender_email, recipients, msg.as_string())
        server.close()
        print("✅ SUCCESS: Dispatch report email successfully transmitted!")
        return True
    except Exception as e:
        print(f"❌ SMTP Failure: Could not transmit dispatch report! Details: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = send_notification()
    sys.exit(0 if success else 1)
