#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS: Semantic Ingestion Decision Derby Engine (Streamlined v2.0)
# Path: /home/james/stacklabs/scripts/organize_inbox.py
#
# Governed by STRY-06052026-PULL-WORKORDERS / ENHC0010009 / WO-20260830.
# Deterministic Prefix-First & Header-First document classifier and ITSM ledger router.
# ==============================================================================

import os
import re
import sys
import time
import shutil
import sqlite3
import fcntl
import mimetypes
import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

# Clio System Directories
INBOX_DIR = "/home/james/sovereign_inbox"
SVR_ROOT = "/home/james/stacklabs"
DB_PATH = os.path.join(SVR_ROOT, "dna/sovereign_now.db")
DOCS_DIR = os.path.join(SVR_ROOT, "dna/docs")

# Target Folders inside Inbox Staging
ROUTES = {
    "ticket": os.path.join(INBOX_DIR, "queue", "incoming"),
    "walkthrough": os.path.join(INBOX_DIR, "walkthroughs"),
    "implementation_plan": os.path.join(INBOX_DIR, "implementation_plans"),
    "kb": os.path.join(INBOX_DIR, "kb"),
    "report": os.path.join(INBOX_DIR, "reports"),
    "media": os.path.join(SVR_ROOT, "media_vault/03_Assets"),
    "sow": DOCS_DIR,
    "quarantine": os.path.join(INBOX_DIR, "quarantine")
}

# Ensure all target routing directories exist
for path in ROUTES.values():
    os.makedirs(path, exist_ok=True)

def strip_sync_suffix(filename):
    """Matches trailing underscore followed by 4-character hex, e.g. '_c0b4.md' -> '.md'"""
    return re.sub(r'_[a-fA-F0-9]{4}(\.[a-zA-Z0-9]+)?$', r'\1', filename)

def calculate_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def log_sync_event(status, msg):
    log_path = os.path.join(SVR_ROOT, "logs/sync.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    log_line = f"[{timestamp}] [{status}] {msg}\n"
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
        # Limit sync.log to 500 lines
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 500:
            with open(log_path, "w", encoding="utf-8") as f:
                f.writelines(lines[-500:])
    except Exception as err:
        print(f"Failed to write to sync.log: {err}")

    # Write to sys_sync_log in DB
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS sys_sync_log (sys_id TEXT PRIMARY KEY, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, status TEXT, event_message TEXT)")
            cursor.execute("INSERT INTO sys_sync_log (sys_id, status, event_message) VALUES (?, ?, ?)", (uuid.uuid4().hex, status, msg))
            cursor.execute("DELETE FROM sys_sync_log WHERE sys_id NOT IN (SELECT sys_id FROM sys_sync_log ORDER BY timestamp DESC LIMIT 500)")
            conn.commit()
            conn.close()
        except Exception as db_err:
            pass

def acquire_lock():
    lock_file_path = "/tmp/sovereign_organize_inbox.lock"
    lock_file = open(lock_file_path, "w")
    for _ in range(10):
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_file
        except BlockingIOError:
            time.sleep(1.0)
    print("[*] Another instance of organize_inbox.py is already running. Exiting.")
    sys.exit(0)

def is_blacklisted_path(filepath):
    abs_path = os.path.abspath(filepath)
    parts = abs_path.split(os.sep)
    blacklist_dirs = {"node_modules", "dist", ".git", ".venv", ".next", ".turbo", "build", "out", "quarantine"}
    blacklist_files = {".DS_Store", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "today.tmp", "yesterday.tmp", ".DO_NOT_SCAN_PILOT_DROPS_ENTER_AT_YOUR_OWN_RISK"}
    
    # Strict Invariant: pilot_drops is quarantined landfill; NEVER scan unless explicitly authorized
    if "pilot_drops" in parts or abs_path.startswith("/home/james/sovereign_inbox/pilot_drops"):
        if os.environ.get("ENTER_AT_YOUR_OWN_RISK") != "1":
            return True

    for part in parts:
        if part in blacklist_dirs:
            return True
            
    filename = os.path.basename(filepath)
    if filename in blacklist_files or filename.endswith(".swp") or filename.startswith("."):
        return True
        
    return False

def clean_title(title):
    if not title:
        return title
    # Remove emoji symbols
    title = re.sub(r'[\u2600-\u27BF]|[\u2000-\u3300]|[\uD83C-\uDBFF\uDC00-\uDFFF]', '', title)
    title = title.strip(" :.-–—#*`")
    return title

def generate_sequential_ticket_id(ticket_type, date_str=None, slug=None):
    prefix = ticket_type.upper() if ticket_type else "STRY"
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        
        if prefix.startswith('WO'):
            if not date_str:
                date_str = time.strftime("%Y-%m%d", time.gmtime())
            safe_slug = re.sub(r'[^A-Z0-9]', '-', (slug or "TASK").upper()).strip('-')[:35]
            if not safe_slug:
                safe_slug = "WORK-ORDER"
            candidate_id = f"WO-{date_str}-{safe_slug}" if not safe_slug.startswith(date_str) else f"WO-{safe_slug}"
            cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (candidate_id,))
            if not cursor.fetchone():
                return candidate_id
            for i in range(1, 100):
                variant = f"{candidate_id}-{i:02d}"
                cursor.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ?", (variant,))
                if not cursor.fetchone():
                    return variant
            return candidate_id

        cursor.execute(f"SELECT number FROM sovereign_tickets WHERE number LIKE '{prefix}%' AND number GLOB '{prefix}[0-9]*' ORDER BY number DESC LIMIT 50")
        rows = cursor.fetchall()
        max_num = 0
        for r in rows:
            num_str = r[0].replace(prefix, '')
            try:
                val = int(num_str)
                if val > max_num:
                    max_num = val
            except ValueError:
                pass
                
        if max_num > 0:
            next_num = max_num + 1
            return f"{prefix}{next_num:07d}" if max_num < 10000000 else f"{prefix}{next_num}"
        else:
            defaults = {'STRY': 'STRY8791020', 'INC': 'INC1000001', 'DFCT': 'DFCT1000001', 'ENHC': 'ENHC1000001', 'REQ': 'REQ1000001'}
            return defaults.get(prefix, f"{prefix}0000001")
    except Exception as e:
        print(f"Failed generating sequential ID: {e}")
        return f"{prefix}{int(time.time())}"
    finally:
        if conn:
            conn.close()

def extract_ticket_meta(content, filename=None):
    """
    Extracts structured metadata from document headers or content.
    """
    content = content.lstrip("\ufeff")
    
    # 1. Type / Classification
    detected_type = "STRY"
    class_match = re.search(r'\b(?:Classification|Ticket Type|Type|Category)\b[\s*:\`]*([^\n\r]+)', content[:3000], re.IGNORECASE)
    if class_match:
        class_val = class_match.group(1).upper()
        if any(w in class_val for w in ["DEFECT", "BUG", "DFCT"]):
            detected_type = "DFCT"
        elif any(w in class_val for w in ["ENHANCEMENT", "ENHC"]):
            detected_type = "ENHC"
        elif any(w in class_val for w in ["INCIDENT", "OUTAGE", "INC"]):
            detected_type = "INC"
        elif any(w in class_val for w in ["REQUEST", "REQ"]):
            detected_type = "REQ"
        elif any(w in class_val for w in ["STORY", "MASHUP", "FEATURE", "STRY"]):
            detected_type = "STRY"

    # 2. Ticket ID extraction
    ticket_id = None
    id_match = re.search(r'\b(?:Ticket ID|Ticket|Work Order ID|Task ID)\b[\s*:\`]*([A-Za-z0-9\-_]+)', content[:3000], re.IGNORECASE)
    if id_match:
        candidate = id_match.group(1).replace('_', '-').strip()
        if any(candidate.upper().startswith(p) for p in ["WO-", "WO0", "WO", "STRY", "INC", "DFCT", "ENHC", "REQ"]):
            ticket_id = candidate

    if not ticket_id and filename:
        fn_match = re.search(r'\b((?:STRY|INC|DFCT|ENHC|REQ|WO)[_\-][A-Za-z0-9_\-]+|\b(?:STRY|INC|DFCT|ENHC|REQ|WO)\d{4,}[A-Za-z0-9_\-]*)\b', filename, re.IGNORECASE)
        if fn_match:
            ticket_id = fn_match.group(1).replace('_', '-')

    # 3. Title extraction
    title = None
    for line in content.splitlines()[:50]:
        title_match = re.search(r'\b(?:Ticket Title|Title|WORK ORDER)\b[\s*:\`]*([^\n\r]+)', line, re.IGNORECASE)
        if title_match:
            candidate = title_match.group(1).replace("**", "").replace("*", "").replace("`", "").strip()
            if candidate and not candidate.startswith("#"):
                title = candidate
                break
    if not title:
        for line in content.splitlines()[:20]:
            if line.strip().startswith("#"):
                title = line.strip().lstrip("#").replace("**", "").replace("*", "").strip()
                break
    if not title and filename:
        title = os.path.splitext(filename)[0].replace("UAT Work Order", "").replace("Work Order", "").replace("_", " ").replace("-", " ").strip()

    title_clean = clean_title(title or "Work Order Task")

    # 4. Auto-generate ticket_id if absent
    if not ticket_id:
        date_match = re.search(r'\b(202\d)[\-_]?(\d{2})[\-_]?(\d{2})\b', (filename or "") + " " + content[:400])
        date_str = f"{date_match.group(1)}-{date_match.group(2)}{date_match.group(3)}" if date_match else None
        slug_source = (filename or title_clean)
        slug_clean = re.sub(r'^(?:WO|WORK[-_ ]ORDER|STRY|INC|DFCT|ENHC|REQ)[\-_ ]*', '', slug_source, flags=re.IGNORECASE)
        slug = re.sub(r'[^A-Za-z0-9]+', '-', slug_clean).strip('-').upper()[:35]
        ticket_id = generate_sequential_ticket_id("WO" if "WO" in (filename or "").upper() else detected_type, date_str=date_str, slug=slug)

    # 5. CMDB CI extraction
    cmdb_ci = "01_Sovereign_Portal"
    ci_match = re.search(r'\b(?:Component Target|Affected CI|CMDB CI|Target Component|Component)\b[\s*:\`]*([^\n\r]+)', content[:600], re.IGNORECASE)
    if ci_match:
        ci_candidate = ci_match.group(1).replace("**", "").replace("*", "").replace("`", "").strip()
        if ci_candidate and len(ci_candidate) < 60:
            cmdb_ci = ci_candidate

    # 6. Priority extraction
    priority_val = 3
    prio_match = re.search(r'\b(?:Priority)\b[\s*:\`]*([^\n\r]+)', content[:600], re.IGNORECASE)
    if prio_match:
        p_text = prio_match.group(1).upper()
        if "1" in p_text or "CRITICAL" in p_text or "P1" in p_text:
            priority_val = 1
        elif "2" in p_text or "HIGH" in p_text or "P2" in p_text:
            priority_val = 2
        elif "3" in p_text or "MEDIUM" in p_text or "P3" in p_text:
            priority_val = 3
        elif "4" in p_text or "LOW" in p_text or "P4" in p_text:
            priority_val = 4

    return {
        "id": ticket_id,
        "type": detected_type,
        "desc": title_clean,
        "cmdb_ci": cmdb_ci,
        "priority": priority_val,
        "state": "STAGED"
    }

def log_to_sqlite(meta, filename, src_path=None, dest_path=None):
    """
    DECOMMISSIONED per Rule IV.17 (The File-First GitOps Mandate):
    Pre-execution database mutations into sovereign_tickets, sys_sdlc_task,
    and sys_approval_queue are strictly decommissioned. The database is an
    asynchronous post-execution read-model projection.
    """
    return True

def register_kb_file(filepath, filename):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lstrip("\ufeff")
            
        title = None
        for line in content.splitlines()[:5]:
            if line.strip().startswith("#"):
                title = line.strip().lstrip("#").strip()
                break
        title = title or os.path.splitext(filename)[0].replace("_", " ").strip()
        
        # Summary
        summary = "Knowledge Base Article"
        summary_match = re.search(r'##\s*(?:1\.\s*)?(?:Executive Summary|Summary|Objective)[\s\S]*?(?=##|\Z)', content, re.IGNORECASE)
        if summary_match:
            lines = [l.strip() for l in summary_match.group(0).splitlines() if not l.strip().startswith("#") and l.strip()]
            if lines:
                summary = " ".join(lines[:2])[:200]

        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH, timeout=10)
            c = conn.cursor()
            
            c.execute("SELECT sys_id, number FROM kb_knowledge WHERE topic = ?", (title,))
            kb_row = c.fetchone()
            
            if kb_row:
                c.execute("UPDATE kb_knowledge SET text = ?, short_description = ?, sys_updated_on = CURRENT_TIMESTAMP WHERE sys_id = ?", (content, summary, kb_row[0]))
                kb_number = kb_row[1]
            else:
                kb_match = re.match(r'^(KB\d+)', filename, re.IGNORECASE) or re.search(r'\b(KB\d+)\b', content[:400], re.IGNORECASE)
                if kb_match:
                    kb_number = kb_match.group(1).upper()
                else:
                    c.execute("SELECT number FROM kb_knowledge WHERE number LIKE 'KB%'")
                    numbers = [r[0] for r in c.fetchall()]
                    max_num = max([int(n.replace("KB", "")) for n in numbers if n.replace("KB", "").isdigit()] + [1000])
                    kb_number = f"KB{max_num + 1:04d}"
                    
                kb_sys_id = f"sys_kb_{uuid.uuid4().hex}"
                c.execute("INSERT INTO kb_knowledge (sys_id, number, topic, short_description, text, workflow_state, u_source, u_tags) VALUES (?, ?, ?, ?, ?, 'published', 'system_operations', 'sync-standards')",
                          (kb_sys_id, kb_number, title, summary, content))
            
            conn.commit()
            conn.close()
            
            # Sync copy into dna/docs/
            safe_topic = re.sub(r'[^a-zA-Z0-9\s]', '', title)
            safe_topic = re.sub(r'\s+', '_', safe_topic).strip().upper()
            doc_filename = f"{kb_number}_{safe_topic}.md"
            with open(os.path.join(DOCS_DIR, doc_filename), "w", encoding="utf-8") as df:
                df.write(content)
            print(f"  [✔] Registered KB Article {kb_number}: {doc_filename}")
    except Exception as e:
        print(f"  [❌] Failed KB registration: {e}")

def classify_document(filepath, filename, content):
    """
    Deterministic Prefix-First and Header-First classification.
    """
    fn_lower = filename.lower()
    
    # 0. Strict Code & Build Leak Quarantine (Never let stray scripts pollute document routes)
    code_extensions = (
        '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.mts', '.cts',
        '.map', '.d.ts', '.css', '.scss', '.flow', '.jsdoc', '.proto',
        '.woff', '.woff2', '.node', '.wasm', '.lock'
    )
    if any(fn_lower.endswith(ext) for ext in code_extensions):
        return "quarantine"
    if filename in ('tsc', 'tsserver', 'to-while', 'yargs', 'ChangeLog', 'Makefile', 'License'):
        return "quarantine"

    # 1. Filename Prefix Matching (100% Deterministic)
    if fn_lower.startswith("walkthrough"):
        return "walkthrough"
    if fn_lower.startswith("implementation_plan") or fn_lower.startswith("implementationplan"):
        return "implementation_plan"
    if fn_lower.startswith("sow_") or fn_lower.startswith("req_"):
        return "sow"
    if fn_lower.startswith("report_") or fn_lower.startswith("executive_brief_") or fn_lower.startswith("whitepaper_") or "brief" in fn_lower:
        return "report"
    if fn_lower.startswith("kb") or re.match(r'^kb\d+', fn_lower):
        return "kb"
    if any(fn_lower.startswith(p) for p in ["wo-", "wo_", "wo0", "wo", "stry", "inc", "dfct", "enhc", "req", "work_order", "work order"]):
        return "ticket"

    # 2. Header-First Content Matching (Top 50 lines)
    header_block = "\n".join(content.splitlines()[:50]).upper()
    if "STATEMENT OF WORK" in header_block or "DOCUMENT ID: SOW" in header_block:
        return "sow"
    if "WORK ORDER:" in header_block or "TICKET ID:" in header_block:
        return "ticket"
    if "DOCUMENT TYPE: EXECUTIVE BRIEF" in header_block or "# REPORT:" in header_block or "WHITEPAPER:" in header_block:
        return "report"
    if "ARTICLE ID: KB" in header_block or "# KB" in header_block:
        return "kb"
    if "WALKTHROUGH" in header_block and "UAT" in header_block:
        return "walkthrough"
    if "IMPLEMENTATION PLAN" in header_block:
        return "implementation_plan"

    # 3. Fallback: Only genuine document formats default to report
    doc_extensions = ('.md', '.pdf', '.docx', '.rtf', '.eml', '.txt')
    if any(fn_lower.endswith(ext) for ext in doc_extensions):
        return "report"

    # Anything else unrecognized is quarantined (never pollute reports/walkthroughs)
    return "quarantine"

def preserve_ticket_bom(ticket_id, title, content_clean, dest_path):
    """
    BOM Preservation Safeguard (KI-050 / WO0010160):
    Parses and preserves the complete, high-fidelity Markdown text of the work order
    in sovereign_tickets.description and registers it in sys_attachment,
    preventing truncation to generic file-move logs.
    """
    if not os.path.exists(DB_PATH) or not ticket_id:
        return
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()
        
        c.execute("SELECT sys_id FROM sovereign_tickets WHERE number = ? OR sys_id = ?", (ticket_id, ticket_id))
        row = c.fetchone()
        t_sys_id = row[0] if row else None
        
        if t_sys_id:
            c.execute("""
                UPDATE sovereign_tickets 
                SET description = ?, sys_updated_on = CURRENT_TIMESTAMP 
                WHERE sys_id = ?
            """, (content_clean, t_sys_id))
        else:
            t_sys_id = uuid.uuid4().hex
            c.execute("""
                INSERT INTO sovereign_tickets (sys_id, number, title, description, state, state_int, priority, p_int, ticket_type, type, sys_created_on, sys_updated_on)
                VALUES (?, ?, ?, ?, 'STAGED', 1, 'P2', 2, 'Work Order', 'WO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (t_sys_id, ticket_id, title, content_clean))
            
        fn = os.path.basename(dest_path)
        f_size = os.path.getsize(dest_path) if os.path.exists(dest_path) else len(content_clean.encode('utf-8'))
        md5_h = hashlib.md5(content_clean.encode('utf-8')).hexdigest()
        
        c.execute("SELECT sys_id FROM sys_attachment WHERE (table_sys_id = ? OR table_sys_id = ?) AND file_name = ?", (t_sys_id, ticket_id, fn))
        att_row = c.fetchone()
        if att_row:
            c.execute("""
                UPDATE sys_attachment 
                SET file_path = ?, file_size = ?, md5_hash = ?, sys_updated_on = CURRENT_TIMESTAMP 
                WHERE sys_id = ?
            """, (dest_path, f_size, md5_h, att_row[0]))
        else:
            att_sys_id = uuid.uuid4().hex
            c.execute("""
                INSERT INTO sys_attachment (sys_id, table_name, table_sys_id, file_name, content_type, file_path, file_size, md5_hash, sys_created_on, sys_updated_on)
                VALUES (?, 'sovereign_tickets', ?, ?, 'text/markdown', ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (att_sys_id, t_sys_id, fn, dest_path, f_size, md5_h))
            
        conn.commit()
        conn.close()
        print(f"  [✔] BOM Preservation Safeguard applied for {ticket_id}: description and attachment stored.")
    except Exception as e:
        print(f"  [WARN] BOM Preservation Safeguard error: {e}")

def organize_file(filepath):
    if is_blacklisted_path(filepath) or os.path.islink(filepath) or os.path.isdir(filepath):
        return None

    filename = strip_sync_suffix(os.path.basename(filepath))
    filename_lower = filename.lower()
    
    # 1. Media Files
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type and mime_type.startswith('image/'):
        dest = os.path.join(ROUTES["media"], filename)
        shutil.move(filepath, dest)
        print(f"[✔] Media: {filename} -> /media_vault/03_Assets/")
        return filename

    # 2. Text / Markdown Files
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        content_clean = content.lstrip("\ufeff")

        category = classify_document(filepath, filename, content_clean)
        dest_folder = ROUTES[category]
        dest_path = os.path.join(dest_folder, filename)

        if category == "ticket":
            # Rule IV.17 (The File-First GitOps Mandate): Decommission pre-execution SQLite ingestion.
            # Work orders are routed directly to queue/incoming/ as clean markdown files with zero DB mutations.
            queue_incoming = ROUTES["ticket"]
            os.makedirs(queue_incoming, exist_ok=True)
            meta = extract_ticket_meta(content_clean, filename)
            target_fn = f"{meta['id']}.md" if meta.get("id") and not filename.startswith(meta["id"]) else filename
            if not target_fn.endswith(".md"):
                target_fn = f"{target_fn}.md"
            dest_path = os.path.join(queue_incoming, target_fn)
            shutil.move(filepath, dest_path)
            preserve_ticket_bom(meta['id'], meta['desc'], content_clean, dest_path)
            success_msg = f"Routed WORK ORDER: {filename} -> queue/incoming/{target_fn} (BOM Preserved)"
            print(f"[✔] {success_msg}")
            log_sync_event("success", success_msg)
            return target_fn

        shutil.move(filepath, dest_path)
        success_msg = f"Classified {category.upper()}: {filename} -> {os.path.basename(dest_folder)}/"
        print(f"[✔] {success_msg}")
        log_sync_event("success", success_msg)
        if category == "kb":
            register_kb_file(dest_path, filename)
        return filename

    except Exception as e:
        print(f"[❌] Error parsing {filename}: {e}")
        log_sync_event("error", f"Error parsing {filename}: {e}")
        return None

def run_decision_derby():
    lock_file = acquire_lock()
    log_sync_event("success", "Decision Derby sweep initiated.")
    print("[*] Initiating Semantic Decision Derby Sweep (Prefix & Header First)...")
    
    processed_files = []
    for entry in os.scandir(INBOX_DIR):
        if is_blacklisted_path(entry.path):
            continue
        if entry.is_file() and not entry.name.startswith('.'):
            res = organize_file(entry.path)
            if res:
                processed_files.append(res)
                
    print(f"[✔] Decision Derby complete. Processed {len(processed_files)} file(s).")
    return processed_files

if __name__ == "__main__":
    run_decision_derby()
