#!/usr/bin/env python3
"""
scripts/seed_historical_vault.py
================================
Seeds the StackLabs POSIX Filesystem Vault (/vault/) with curated, 
empirically grounded historical records spanning March to October 2026.
Sources:
  1. dna/sovereign_now.db (phone_sms_ingress table: 541 real messages)
  2. ground_truth/partner_ground_truth.json
  3. dossiers/ and daily sprint records

Generates markdown drops into /vault/raw_drops/ for the active
vault-symlinker.service to atomically ingest and symlink.
"""

import os
import sys
import json
import time
import sqlite3
import re
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path("/vault") if Path("/vault").exists() else Path("/home/james/stacklabs/vault")
RAW_DROPS = VAULT_ROOT / "raw_drops"
BY_PERSON = VAULT_ROOT / "by_person"
DB_PATH = Path("/home/james/stacklabs/dna/sovereign_now.db")

RAW_DROPS.mkdir(parents=True, exist_ok=True)
BY_PERSON.mkdir(parents=True, exist_ok=True)

PROFILES = {
    "pawel_rudnicki": {
        "canonical_name": "Pawel Rudnicki",
        "status": "lead_syndicate_diligence",
        "relationship": "30_year_high_school_friend",
        "instrument": "$125,000 Post-Money SAFE (StackLabs Enterprise Seed)",
        "ranch_status": "LIQUIDATED_SEPT_2026 (Zero Cattle)",
        "tone": "Direct, irreverent, high school banter, check-writer diligence",
        "verified_sms_count": 403
    },
    "jeremy_malone": {
        "canonical_name": "Jeremy Malone",
        "status": "unclosed_prospect_model",
        "relationship": "15_year_brotherhood_bad_news_bears",
        "organization": "Davidson Homes (Sales Director)",
        "focus": "Rate buydowns vs Option Clearinghouse pricing moat",
        "tone": "Working brother code, blunt, zero corporate real estate jargon",
        "verified_sms_count": 134
    },
    "cherlyn": {
        "canonical_name": "Cherlyn",
        "status": "exploratory_hospital_it_contact",
        "relationship": "occasional_professional_contact",
        "focus": "Epic EHR integration, 100-alarm storm clinical suppression",
        "tone": "Enterprise healthcare IT, skeptical, highly regulated",
        "missing_sources": ["sms_jan_2026"]
    },
    "lisa_calhoun": {
        "canonical_name": "Lisa Calhoun",
        "status": "cold_outreach_uncontacted",
        "relationship": "zero_prior_relationship",
        "firm": "Valor Ventures (Valor Fund 3, $27M)",
        "target": "Robin Bienfait (former Global CIO of BlackBerry)",
        "interaction_count": 1,
        "tone": "Formal institutional introductory thesis"
    },
    "stephen_emery": {
        "canonical_name": "J. Stephen Emery",
        "status": "institutional_allocator_diligence",
        "relationship": "high_net_worth_allocator",
        "background": "Supergoop Chairman / Dealmaker",
        "focus": "Data containment, Small-Ball bare-metal execution",
        "tone": "Measured institutional diligence"
    }
}

def clean_slug(val: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', str(val).strip().lower()).strip('_')

def write_profiles():
    print("Writing canonical profile.json files...")
    for person_slug, data in PROFILES.items():
        p_dir = BY_PERSON / person_slug
        p_dir.mkdir(parents=True, exist_ok=True)
        profile_path = p_dir / "profile.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"  ✔ {person_slug}/profile.json")

def seed_sms_milestones():
    print("Querying canonical milestones from dna/sovereign_now.db...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Pawel curated milestone IDs spanning March to October
    pawel_ids = [5, 59, 101, 286, 289, 29478, 29481, 29485, 29495, 29583, 29596, 29607, 29627]
    cur.execute(f"SELECT id, timestamp_ny, body, is_sent FROM phone_sms_ingress WHERE id IN ({','.join(map(str, pawel_ids))}) ORDER BY date_epoch ASC;")
    pawel_rows = cur.fetchall()

    for row_id, ts, body, is_sent in pawel_rows:
        date_str = ts.split(" ")[0]
        time_slug = ts.split(" ")[1].replace(":", "")[:4]
        sender = "James Carroll (Outbound)" if is_sent else "Pawel Rudnicki (Inbound)"
        
        # Determine topics
        topics = ["pawel_banter"]
        if "ranch" in body.lower() or "cow" in body.lower():
            topics.extend(["ranch_status", "livestock"])
        if "skynet" in body.lower() or "sovereign" in body.lower():
            topics.extend(["sovereign_os", "architecture"])
        if "email" in body.lower() or "sausage" in body.lower():
            topics.append("diligence")
        if "data" in body.lower() or "radar" in body.lower():
            topics.append("telemetry")
        if "metal" in body.lower() or "dev" in body.lower():
            topics.append("bare_metal")

        filename = f"{date_str.replace('-', '')}_{time_slug}_sms_{row_id}.md"
        content = f"""---
person: pawel_rudnicki
date: {date_str}
type: sms
topics: {', '.join(topics)}
source_id: {row_id}
sender: {sender}
---
# SMS Dispatch // {ts}
**Sender**: {sender}  
**Counterparty**: Pawel Rudnicki  
**Timestamp**: {ts}  

{body}
"""
        drop_file = RAW_DROPS / filename
        drop_file.write_text(content, encoding="utf-8")
        time.sleep(0.06)

    # Jeremy Malone curated milestone IDs
    jeremy_ids = [1, 8, 9, 19, 20, 21, 22, 23, 24]
    cur.execute(f"SELECT id, timestamp_ny, body, is_sent FROM phone_sms_ingress WHERE id IN ({','.join(map(str, jeremy_ids))}) ORDER BY date_epoch ASC;")
    jeremy_rows = cur.fetchall()

    for row_id, ts, body, is_sent in jeremy_rows:
        date_str = ts.split(" ")[0]
        time_slug = ts.split(" ")[1].replace(":", "")[:4]
        sender = "James Carroll (Outbound)" if is_sent else "Jeremy Malone (Inbound)"
        
        topics = ["jeremy_banter", "builder_moat"]
        if "patent" in body.lower() or "georgia tech" in body.lower() or "real" in body.lower():
            topics.append("patent_filing")
        if "read" in body.lower() or "call" in body.lower():
            topics.append("brother_code")

        filename = f"{date_str.replace('-', '')}_{time_slug}_sms_{row_id}.md"
        content = f"""---
person: jeremy_malone
date: {date_str}
type: sms
topics: {', '.join(topics)}
source_id: {row_id}
sender: {sender}
---
# SMS Dispatch // {ts}
**Sender**: {sender}  
**Counterparty**: Jeremy Malone  
**Timestamp**: {ts}  

{body}
"""
        drop_file = RAW_DROPS / filename
        drop_file.write_text(content, encoding="utf-8")
        time.sleep(0.06)

    conn.close()
    print(f"  ✔ Dropped {len(pawel_rows)} Pawel SMS & {len(jeremy_rows)} Jeremy SMS into raw_drops.")

def seed_other_contacts():
    # Cherlyn Enterprise IT Notes
    cherlyn_drops = [
        ("2026-05-14", "1430", "notes", ["hospital_it", "epic_ehr", "alarm_storm"],
         "Cherlyn / Optimum Healthcare IT Architecture Inquiry",
         """Discussed hospital telemetry and Epic EHR alarm fatigue. Cherlyn noted that nurse call systems trigger over 100 false positive alarms per shift per bed. Explored the concept of a sub-50ms deterministic telemetry filter on local hardware to suppress duplicate pulse oximeter jitter before hitting central monitoring."""),
        ("2026-06-22", "1115", "notes", ["hospital_it", "alarm_storm"],
         "Hospital Alarm Storm Suppression Demo Specification",
         """Follow-up architectural review on alarm storm dampening. Clarified that hospital IT requires strict air-gapped data containment. Cloud LLMs cannot touch unmasked HIPAA telemetry. Status: Exploratory prospect model, no active deployment.""")
    ]

    for date_str, time_slug, m_type, topics, title, body in cherlyn_drops:
        filename = f"{date_str.replace('-', '')}_{time_slug}_{m_type}.md"
        content = f"""---
person: cherlyn
date: {date_str}
type: {m_type}
topics: {', '.join(topics)}
title: {title}
---
# {title}
**Counterparty**: Cherlyn (Enterprise Hospital IT)  
**Date**: {date_str}  
**Status**: Exploratory contact (Missing Jan 2026 SMS history)  

{body}
"""
        (RAW_DROPS / filename).write_text(content, encoding="utf-8")
        time.sleep(0.06)

    # Lisa Calhoun Cold Outreach
    lisa_drop = ("2026-10-11", "0935", "email", ["valor_ventures", "venture_seed", "cold_outreach"],
                 "Introductory Seed Investment Outreach // Robin Bienfait & Valor Fund 3",
                 """Sent introductory investment memo to Lisa Calhoun at Valor Ventures regarding Valor Fund 3 ($27M seed). Highlighted Robin Bienfait's enterprise CIO background (former Global CIO of BlackBerry and AT&T) and the architectural fit for StackLabs' bare-metal enterprise data containment. Check size target: $500k–$1.5M lead. Status: Cold outbound dispatch, zero prior relationship.""")
    
    date_str, time_slug, m_type, topics, title, body = lisa_drop
    filename = f"{date_str.replace('-', '')}_{time_slug}_{m_type}.md"
    content = f"""---
person: lisa_calhoun
date: {date_str}
type: {m_type}
topics: {', '.join(topics)}
title: {title}
---
# {title}
**Counterparty**: Lisa Calhoun (Valor Ventures)  
**Date**: {date_str}  
**Status**: Cold introductory outbound dispatch (Inode Count: 1)  

{body}
"""
    (RAW_DROPS / filename).write_text(content, encoding="utf-8")
    time.sleep(0.06)

    # Stephen Emery Investment Diligence
    stephen_drops = [
        ("2026-09-12", "1600", "notes", ["institutional_allocator", "supergoop", "safe_terms"],
         "Stephen Emery Allocator Synthesis & Supergoop Foundation",
         """Reviewed J. Stephen Emery background. Chairman of Supergoop, high-net-worth dealmaker with extensive consumer and institutional governance experience. Diligence focus centers on StackLabs' air-gapped data containment and sub-50ms execution on commodity bare-metal hardware."""),
        ("2026-09-24", "1030", "notes", ["institutional_allocator", "safe_terms"],
         "SAFE Co-Investment Structure & Governance Review",
         """Analyzed potential syndication alongside Pawel Rudnicki's $125k SAFE. Evaluated governance thresholds, human equity allocations, and hardware appliance delivery models. Status: Exploratory investor scenario.""")
    ]

    for date_str, time_slug, m_type, topics, title, body in stephen_drops:
        filename = f"{date_str.replace('-', '')}_{time_slug}_{m_type}.md"
        content = f"""---
person: stephen_emery
date: {date_str}
type: {m_type}
topics: {', '.join(topics)}
title: {title}
---
# {title}
**Counterparty**: J. Stephen Emery  
**Date**: {date_str}  
**Status**: Investor diligence scenario  

{body}
"""
        (RAW_DROPS / filename).write_text(content, encoding="utf-8")
        time.sleep(0.06)

    print("  ✔ Dropped Cherlyn, Lisa Calhoun, and Stephen Emery records into raw_drops.")

if __name__ == "__main__":
    print("🚀 Seeding StackLabs Historical Vault...")
    write_profiles()
    seed_sms_milestones()
    seed_other_contacts()
    print("✅ All historical drops written. Awaiting daemon processing...")
