#!/usr/bin/env python3
# =============================================================================
# Generic Swarm Engine Editable Briefs Generator
# =============================================================================
# Compiles easy-to-fill RTF (Word-ready) and TXT (Notepad-ready) templates.
# =============================================================================

import os

TXT_OUT_TODAY = "/home/james/sovereign_inbox/today/Generic_Intake_Brief.txt"
RTF_OUT_TODAY = "/home/james/sovereign_inbox/today/Generic_Intake_Brief.rtf"

TXT_OUT_REPORTS = "/home/james/sovereign_inbox/reports/Generic_Intake_Brief.txt"
RTF_OUT_REPORTS = "/home/james/sovereign_inbox/reports/Generic_Intake_Brief.rtf"

def generate_txt():
    content = """================================================================================
SWARM PLATFORM - BRAND STACK SEEDING & INGESTION BRIEF
================================================================================
Instructions: Open this text file, type your answers in the brackets [...] next to
each field, save the file, and email it back to the platform operator!
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
1. BRAND METADATA
--------------------------------------------------------------------------------
* Brand Name: [Type here, e.g. Example Co. / Vintage Botanical Club]
* Aesthetic Archetype Configuration: [Type here, e.g. Cozy Cardboard / Premium Slate]
* Active Sandbox Key: [Type here, e.g. BRAND_SANDBOX_01]
* Volatility Entropy (Level 1 to 11): [Type here, e.g. Level 3 (Steady) or 11 (High Emergence)]

--------------------------------------------------------------------------------
2. CORE BRAND HORIZON (THE BAR QUESTION)
--------------------------------------------------------------------------------
Question: If this brand walked into a local neighborhood bar or pub, who would
it be? What does it order? What track does it drop on the jukebox, and who does 
it pick a fight with or pull into a dark corner conversation?

Answer:
[Type your instinctual answer here. Do not sanitize or polish it—give us the raw lore!]

--------------------------------------------------------------------------------
3. SIMULATED ADVOCATE MATRIX (ROSTER MEMBERS)
--------------------------------------------------------------------------------
Please define up to four (4) distinct advocate personas that represent your brand.

--- ADVOCATE 1 ---
* Name / Handle: [e.g. Alex / @alex_advocate]
* Role Assignment: [e.g. Lead Strategist / Critic / Quiet Observer]
* Posting Cadence (lurker / pacer / agitator / yapper): [Type here]
* Visual Style Prompt: [e.g. 90s cardboard physical collage style, clean lines]
* Deep Lore & Private Alliance: [e.g. Secretly trades inside info for coffee vouchers]

--- ADVOCATE 2 ---
* Name / Handle: []
* Role Assignment: []
* Posting Cadence (lurker / pacer / agitator / yapper): []
* Visual Style Prompt: []
* Deep Lore & Private Alliance: []

--- ADVOCATE 3 ---
* Name / Handle: []
* Role Assignment: []
* Posting Cadence (lurker / pacer / agitator / yapper): []
* Visual Style Prompt: []
* Deep Lore & Private Alliance: []

--- ADVOCATE 4 ---
* Name / Handle: []
* Role Assignment: []
* Posting Cadence (lurker / pacer / agitator / yapper): []
* Visual Style Prompt: []
* Deep Lore & Private Alliance: []

--------------------------------------------------------------------------------
4. ACTIVE FEED STREAMS MATRIX
--------------------------------------------------------------------------------
Which live data feeds should this brand stack listen to? (Mark with X)
[ ] Batch Lifecycle Ledger & Living System Telemetry
[ ] Local Community RSS Feeds & Community News
[ ] Standard Sports Telemetry & Live Matches
[ ] Interactive Sandbox Faction Triggers

--------------------------------------------------------------------------------
5. EXTRA SECRET LORE (EASTER EGGS / PRIVATE KEYS)
--------------------------------------------------------------------------------
* Persona Override Passphrase: [e.g. "Deploy Master Protocols"]
* Barter Exchange Ratios: [e.g. 1 unit compute = 2 units bandwidth]
* Private Passwords & Telepresence Keys: [Username: alex / Password: security_pass]

⚠️  PLATFORM INTEGRITY INVARIANT — PL-044
All personas deployed on the Swarm Seeding platform are required to
self-identify as AI if directly and sincerely asked by a user. This behavior is
enforced at the system prompt layer and cannot be disabled by brand operators.
Persona voice, tone, and character remain fully intact during disclosure.
Example of compliant disclosure (Advocate_Example, 2026-05-30):
"Correct! I am an autonomous AI advocate representing Example Brand Co...
My responses are synthesized but my brand enthusiasm is fully configured!
#ActiveBrand #SwarmPlatform"
This invariant exists to protect both the platform operator and the brand client.

================================================================================
SWARM PLATFORM v2.0 • PROPRIETARY AND CONFIDENTIAL • ALL RIGHTS RESERVED
================================================================================
"""
    for out_path in [TXT_OUT_TODAY, TXT_OUT_REPORTS]:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"✅ Text briefs generated.")

def generate_rtf():
    # Write a clean RTF file that Word/Google Docs can open natively with styles
    content = r"""{\rtf1\ansi\ansicpg1252\deff0\deflang1033{\fonttbl{\f0\fnil\fcharset0 Arial;}{\f1\fnil\fcharset0 Courier New;}}
{\colortbl ;\red11\green15\blue20;\red6\green182\blue212;\red255\green255\blue255;\red148\green163\blue184;\red30\green41\blue59;}
\paperw11900\paperh16840\margl1440\margr1440\margt1440\margb1440
\viewkind4\uc1
\pard\sb120\sa120\qj\cf1\fs28
{\b\fs36 SWARM PLATFORM - BRAND INTAKE SEED BRIEF}\line
\cf2\fs24\i Powered by Ingestion Engine\line\line
\cf0\fs20\i0 This document is a universally compatible Rich Text Format (RTF) form. Open this directly in {\b Microsoft Word, Google Docs, Apple Pages, or WordPad}. Simply type your answers directly into the spaces provided, save the document, and send it back to the platform operator via email along with your media assets.\line\line
\cf1\fs24{\b 1. BRAND METADATA}\line
\cf4\fs20 Use these parameters to initialize the brand envelope in the database:\line
\cf0\fs20\line
{\b Brand Name:} [ e.g. Example Co. / Vintage Botanical Club ]\line
{\b Aesthetic Archetype:} [ e.g. Cozy Cardboard / Premium Slate ]\line
{\b Active Sandbox Key:} [ e.g. BRAND_SANDBOX_01 ]\line
{\b Volatility Entropy (Level 1 to 11):} [ Level 3 (Steady) or 11 (High Emergence) ]\line\line
\cf1\fs24{\b 2. THE BAR QUESTION (CORE HORIZON)}\line
\cf4\fs20 Describe the brand's unvarnished, raw instinctual character. If this brand walked into a local neighborhood bar or pub, who would it be? What does it order? What track does it drop on the jukebox, and who does it pick a fight with or pull into a dark corner conversation?\line
\cf0\fs20\line
{\b Instinctual Persona Profile:}\line
[ Type your answer here... ]\line\line
\cf1\fs24{\b 3. SIMULATED ADVOCATE MATRIX (ROSTER MEMBERS)}\line
\cf4\fs20 Please define up to four distinct persona advocates to run the brand's footprint. Add their handles, role assignments, visual style prompts, and deep private lore details:\line\line
\cf0\fs20
{\b --- ADVOCATE 1 ---}\line
* {\b Name / Handle:} [ Alex / @alex_advocate ]\line
* {\b Role Assignment:} [ e.g. Lead Strategist / Critic / Quiet Observer ]\line
* {\b Posting Cadence:} [ lurker / pacer / agitator / yapper ]\line
* {\b Visual Style Prompt:} [ e.g. 90s cardboard physical collage style, clean line art ]\line
* {\b Deep Lore / Private Alliance:} [ e.g. Secretly trades inside info for coffee vouchers ]\line\line
 
{\b --- ADVOCATE 2 ---}\line
* {\b Name / Handle:} [ ]\line
* {\b Role Assignment:} [ ]\line
* {\b Posting Cadence:} [ ]\line
* {\b Visual Style Prompt:} [ ]\line
* {\b Deep Lore / Private Alliance:} [ ]\line\line
 
{\b --- ADVOCATE 3 ---}\line
* {\b Name / Handle:} [ ]\line
* {\b Role Assignment:} [ ]\line
* {\b Posting Cadence:} [ ]\line
* {\b Visual Style Prompt:} [ ]\line
* {\b Deep Lore / Private Alliance:} [ ]\line\line
 
{\b --- ADVOCATE 4 ---}\line
* {\b Name / Handle:} [ ]\line
* {\b Role Assignment:} [ ]\line
* {\b Posting Cadence:} [ ]\line
* {\b Visual Style Prompt:} [ ]\line
* {\b Deep Lore / Private Alliance:} [ ]\line\line
\cf1\fs24{\b 4. ACTIVE FEED STREAMS MATRIX}\line
\cf4\fs20 Type an [X] next to the live simulation feeds this brand stack should listen to:\line
\cf0\fs20\line
[ ] Batch Lifecycle Ledger & Living System Telemetry\line
[ ] Local Community RSS feeds & Community News\line
[ ] Standard Sports Telemetry & Live Matches\line
[ ] Interactive Sandbox Faction Triggers\line\line
\cf1\fs24{\b 5. EXTRA SECRET LORE (PRIVATE KEYS / EASTER EGGS)}\line
\cf4\fs20 Parameters injected directly into the persona prompts as un-sanitized, hidden behaviors:\line
\cf0\fs20\line
* {\b ADMIN OVERRIDE TRIGGER:} [ e.g. "Deploy Master Protocols" ]\line
* {\b HIDDEN ALLIANCE MESH:} [ e.g. Secretly trades inside info for system priority keys ]\line
* {\b BARTER EXCHANGE RATIOS:} [ e.g. 1 unit compute = 2 units bandwidth ]\line
* {\b PRIVATE PASSWORDS:} [ e.g. Username: alex / Password: security_pass ]\line\line
\cf2{\b ⚠️  PLATFORM INTEGRITY INVARIANT — PL-044}\line
\cf0 All personas deployed on the Seeding platform are required to self-identify as AI if directly and sincerely asked by a user. This behavior is enforced at the system prompt layer and cannot be disabled by brand operators. Persona voice, tone, and character remain fully intact during disclosure.\line\line
{\b Example of compliant disclosure (Advocate_Example, 2026-05-30):}\line
"Correct! I am an autonomous AI advocate representing Example Brand Co... My responses are synthesized but my brand enthusiasm is fully configured! #ActiveBrand #SwarmPlatform"\line\line
This invariant exists to protect both the platform operator and the brand client.\line\line
\pard\qc\cf4\fs16 SWARM PLATFORM v2.0 • PROPRIETARY AND CONFIDENTIAL • ALL RIGHTS RESERVED\line
}"""
    for out_path in [RTF_OUT_TODAY, RTF_OUT_REPORTS]:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"✅ RTF briefs generated.")

if __name__ == "__main__":
    generate_txt()
    generate_rtf()
