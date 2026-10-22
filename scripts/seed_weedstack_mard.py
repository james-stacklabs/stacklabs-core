#!/usr/bin/env python3
"""
seed_weedstack_mard.py
Seeds content sources, factions, and initial events for WEEDSTACK_SIM_001.
"""
import sqlite3, uuid

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
ROOM_KEY = "WEEDSTACK_SIM_001"

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL;")
cur = conn.cursor()

# ── Content Sources ───────────────────────────────────────────────────────────
# THE TOGGLES. Default: batch_drop and cannabis_news ON. Everything else OFF.
SOURCES = [
    ("batch_drop",      "Batch Drop Events",
     "New WildSeed/cannabis batch releases and harvest announcements",
     1, None, 0),
    ("cannabis_news",   "Cannabis Industry News",
     "Regulatory changes, award results, market news, DCC updates",
     1, "https://cannabisindustryjournal.com/feed/", 3600),
    ("coa_result",      "COA Lab Results",
     "Certificate of Analysis pass/fail events from connected labs",
     1, None, 0),
    ("reddit",          "Reddit Cannabis Communities",
     "r/weed, r/trees, r/cannabis — organic community post triggers",
     0, None, 1800),
    ("competitor_drop", "Competitor Brand Drops",
     "New product releases from competing California manufacturers",
     0, None, 7200),
    ("pricing_feed",    "Dispensary Pricing Feed",
     "Real-time price changes at partner dispensaries",
     0, None, 3600),
    ("harvest_report",  "Harvest & Weather Reports",
     "California agricultural reports — sun-grown seasonal events",
     0, None, 86400),
]

for key, name, desc, enabled, url, interval in SOURCES:
    cur.execute("""
        INSERT OR IGNORE INTO ws_content_source
            (sys_id, source_key, display_name, description,
             room_key, enabled, feed_url, poll_interval_s)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (uuid.uuid4().hex, key, name, desc, ROOM_KEY, enabled, url, interval))

# ── Factions ──────────────────────────────────────────────────────────────────
# The barter society. Alliances and rivalries that shape how personas
# react to each other's content — not just to external events.
FACTIONS = [
    ("The Science Bloc",    "alliance",
     "Data-driven, evidence-based. United by a belief in measurable truth. "
     "Will trade: COA data, terpene analysis, lab methodology."),

    ("The Compliance Axis", "alliance",
     "Karen and Pete's uneasy alliance. Different reasons, same outcome: "
     "the rules exist for a reason and shortcuts get licenses revoked. "
     "Will trade: regulatory intel, audit prep, chain of custody docs."),

    ("The True Believers",  "alliance",
     "Gary, Linda, and BT4991 Believer. Pure enthusiasm, zero cynicism. "
     "United by love of the product regardless of science or compliance. "
     "Will trade: hype, testimonials, drop event coordination."),

    ("The Shadow Bloc",     "rivalry",
     "Terp Truther vs Dr. Terp. Permanent, irreconcilable war. "
     "Every event is viewed through opposite lenses. "
     "Will NOT trade. Will argue. Indefinitely."),

    ("The Old Guard",       "rivalry",
     "Pete vs Derek. Sun-grown vs concentrates. "
     "Philosophical disagreement about what cannabis fundamentally is. "
     "Respectful but immovable. Will trade: history and technique, "
     "but never concede the core argument."),
]

faction_ids = {}
for name, ftype, desc in FACTIONS:
    fid = uuid.uuid4().hex
    faction_ids[name] = fid
    cur.execute("""
        INSERT OR IGNORE INTO ws_faction
            (sys_id, faction_name, faction_type, room_key, description)
        VALUES (?, ?, ?, ?, ?)
    """, (fid, name, ftype, ROOM_KEY, desc))

# ── Faction Membership ────────────────────────────────────────────────────────
MEMBERS = [
    ("The Science Bloc",    "dr_terp",              "leader"),
    ("The Science Bloc",    "terp_truther",         "reluctant"),  # he knows the science, he just doesn't trust it
    ("The Compliance Axis", "compliance_karen",     "leader"),
    ("The Compliance Axis", "old_growth_pete",      "member"),
    ("The True Believers",  "bt4991_believer",      "leader"),
    ("The True Believers",  "dispensary_gary",      "member"),
    ("The True Believers",  "420_linda",            "member"),
    ("The Shadow Bloc",     "terp_truther",         "leader"),
    ("The Shadow Bloc",     "dr_terp",              "member"),
    ("The Old Guard",       "old_growth_pete",      "leader"),
    ("The Old Guard",       "dab_lab_derek",        "member"),
    # Carl belongs to no faction. Carl is Carl.
    # Derek is in The Old Guard but also loosely aligned with Science Bloc.
    ("The Science Bloc",    "dab_lab_derek",        "member"),
]

for fname, pname, role in MEMBERS:
    cur.execute("""
        INSERT OR IGNORE INTO ws_faction_member
            (sys_id, faction_id, persona_name, role)
        VALUES (?, ?, ?, ?)
    """, (uuid.uuid4().hex, faction_ids[fname], pname, role))

# ── Seed Initial Content Events ───────────────────────────────────────────────
# These fire immediately when the room starts — so the room isn't cold on load
SEED_EVENTS = [
    ("batch_drop",
     "BT5002 Spring 2026 Harvest Drop — Now Available at Select Dispensaries",
     "WildSeed LLC has officially released Batch BT5002 from their Spring 2026 "
     "cultivation cycle. Reported profile: 28.4% THC, 1.2% myrcene, 0.8% limonene. "
     "Michael at WildSeed: 'cleanest run since BT4991.' Limited units. "
     "COA cleared all panels. Metrc chain of custody: zero flags.",
     "batch,BT5002,wildseed,drop,spring2026"),

    ("cannabis_news",
     "California DCC Announces Mandatory Lab Testing Expansion for Type 6 Manufacturers",
     "The California Department of Cannabis Control has announced that all Type 6 "
     "licensed manufacturers will be required to submit to expanded heavy metals "
     "and residual solvent panels starting Q3 2026. Facilities with existing "
     "digital COA tracking infrastructure are expected to face minimal disruption. "
     "Operators still using manual Metrc entry are being advised to upgrade immediately.",
     "compliance,DCC,regulation,Type6,COA,california"),

    ("cannabis_news",
     "2026 Emerald Cup Results: Sun-Grown Dominates Flower Category Again",
     "For the third consecutive year, sun-grown outdoor and greenhouse entries "
     "took four of the top five spots in the Emerald Cup flower category. "
     "Indoor cultivators dispute the judging methodology, arguing that "
     "consistency and cannabinoid precision favor controlled environments. "
     "The debate has reignited across industry forums.",
     "emeraldcup,award,sungrown,indoor,terpenes,debate"),
]

for source_key, headline, content, tags in SEED_EVENTS:
    cur.execute("""
        INSERT OR IGNORE INTO ws_content_event
            (sys_id, source_key, room_key, headline, content, tags, injected)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (uuid.uuid4().hex, source_key, ROOM_KEY, headline, content, tags))

conn.commit()
conn.close()
print("✅ WeedStack M.A.R.D engine seeded.")
print("   Content sources: 7 (2 enabled, 5 standing by)")
print("   Factions: 5")
print("   Seed events: 3 queued")
print("   Carl: unaffiliated. As intended.")
