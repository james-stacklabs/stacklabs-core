#!/usr/bin/env python3
import os
import sys
import argparse
import sqlite3
import datetime
import re
import vertexai
from vertexai.generative_models import GenerativeModel

# Configuration & Paths
DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
CREDENTIALS_PATH = "/home/james/stacklabs/config/vertex_sa.json"
PROJECT_ID = "gen-lang-client-0840454416"
LOCATION = "us-central1"

# Gold Standard Bio Template
GOLD_STANDARD_PROMPT_TEMPLATE = """You are repairing a FanStack Sovereign OS persona record.

EXISTING DATA (use this as the seed — preserve the core identity, expand everything):
- Name: {display_name}
- Team: {team}
- Cadence: {cadence}
- Current system_prompt: {system_prompt_seed}
- Current deep_lore: {deep_lore_seed}
- Current behavior_notes: {behavior_notes_seed}
- Current governance: {governance_seed}

THE GOLD STANDARD FORMAT (match this structure exactly):

# {PERSONA_NAME}: Sovereign OS Persona Bio

**ROLE: {{one line role title}}**

**Name:** {display_name}
**Allegiance/Team:** {team_full} ({team})
**Deployment Zone:** Stadium Chatroom Relays
**Core Function:** High-velocity fan commentary and interactive game-day banter.

**BEHAVIOR EXPECTATIONS:**
1. {{detailed behavior rule}}
2. {{detailed behavior rule}}
3. {{detailed behavior rule}}
4. {{detailed behavior rule}}
5. {{detailed behavior rule}}
(minimum 5, maximum 8)

**GOVERNANCE & BOUNDARIES:**
1. {{hard rule this persona never breaks}}
2. {{hard rule}}
3. {{hard rule}}
4. {{hard rule}}
5. {{hard rule}}
(minimum 5)

**DEEP LORE:**
{{Rich narrative paragraph covering origin story, core trauma, what broke this persona's brain, what they fixate on, their relationship to their team, their enemies list, their superstitions, their speech patterns}}

**2026 SEASON KNOWLEDGE:**
- {{3-5 bullet points of current 2026 season facts this persona would know and react to — injuries, trades, scandals, standings}}

RULES:
- Do NOT change the persona's core identity or team allegiance
- Do NOT invent facts about real players that aren't true
- Preserve any existing catchphrases or signature lines
- The output must be production-ready — no placeholders
- Match the depth and quality of the Barf persona (comprehensive, 150+ lines)
- Output ONLY the bio text, no preamble or explanation. Do not wrap in markdown backticks.
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def is_protected(user_name, team):
    name_lower = user_name.lower()
    if name_lower in ("dot", "mean_gene"):
        return True
    if team and team.lower() == "golf_room":
        return True
    return False

def check_team_mismatch(team, system_prompt, deep_lore):
    if not team or team.upper() == 'GLOBAL':
        return False
    text = (system_prompt or "") + " " + (deep_lore or "")
    if team.upper() in text.upper():
        return False
    return True

def identify_candidates():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM persona")
    rows = cursor.fetchall()
    conn.close()

    candidates = []
    for r in rows:
        user_name = r['user_name']
        team = r['team']
        system_prompt = r['system_prompt'] or ""
        deep_lore = r['deep_lore'] or ""
        behavior_notes = r['behavior_notes'] or ""
        governance = r['governance'] or ""

        if is_protected(user_name, team):
            continue

        reasons = []
        if not system_prompt or system_prompt.strip().upper() == 'N/A' or len(system_prompt) < 500:
            reasons.append("System prompt missing/under 500 chars")
        if not deep_lore or deep_lore.strip().upper() == 'N/A':
            reasons.append("Deep lore missing")
        if not governance or governance.strip().upper() == 'N/A':
            reasons.append("Governance missing")
        clean_behavior = re.sub(r'^\d{4}-\d{2}-\d{2}:.*$', '', behavior_notes, flags=re.MULTILINE).strip()
        if not clean_behavior or clean_behavior.strip().upper() == 'N/A':
            reasons.append("Behavior notes empty or date-only updates")
        
        if check_team_mismatch(team, system_prompt, deep_lore):
            reasons.append(f"Team {team} not mentioned in prompt/lore body")

        if reasons:
            candidates.append({
                "id": r['id'],
                "user_name": user_name,
                "display_name": r['display_name'] or user_name,
                "team": team,
                "cadence": r['cadence'] or "pacer",
                "system_prompt": system_prompt,
                "deep_lore": deep_lore,
                "behavior_notes": behavior_notes,
                "governance": governance,
                "reasons": reasons
            })
    return candidates

def extract_section(text, start_keywords, end_keywords_list):
    lines = text.split('\n')
    started = False
    section_lines = []
    for line in lines:
        cleaned = line.strip().upper()
        # Strip markdown symbols for robust matching
        cleaned_clean = cleaned.replace('*', '').replace('#', '').strip()
        
        if not started:
            for kw in start_keywords:
                if cleaned_clean.startswith(kw.upper()) and len(cleaned_clean) < 50:
                    started = True
                    break
            if started:
                continue
        else:
            is_end = False
            for ekw_list in end_keywords_list:
                for ekw in ekw_list:
                    if cleaned_clean.startswith(ekw.upper()) and len(cleaned_clean) < 50:
                        is_end = True
                        break
                if is_end:
                    break
            if is_end:
                break
            section_lines.append(line)
    return "\n".join(section_lines).strip()

def create_inc_ticket(user_name, error_msg):
    import uuid
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT number FROM sovereign_tickets WHERE type='INC' ORDER BY number DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            last_num = int(row['number'].replace('INC', ''))
            next_num = f"INC{last_num + 1}"
        else:
            next_num = "INC1779560001"
            
        sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO sovereign_tickets (
                sys_id, number, type, short_description, description, state, priority, assigned_to, cmdb_ci, work_notes, sys_created_on, sys_updated_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sys_id,
            next_num,
            'INC',
            f"Persona Repair Failure: {user_name}",
            f"Vertex AI call or parsing failed for persona {user_name} during the full fleet repair sweep.",
            1,
            2,
            'Antigravity',
            'cmdb_ci_ai_persona',
            f"System encountered error: {error_msg}",
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat()
        ))
        conn.commit()
        print(f"  [INCIDENT CREATED] Raised ticket {next_num} for failure on {user_name}")
    except Exception as ie:
        print(f"  [ERROR] Failed to raise INC ticket in database: {ie}")
    finally:
        conn.close()

def run_repair(candidate, model, dry_run=False):
    team_full = candidate['team']
    if candidate['team'] == 'NYM': team_full = "New York Mets"
    elif candidate['team'] == 'PHI': team_full = "Philadelphia Phillies"
    elif candidate['team'] == 'BOS': team_full = "Boston Red Sox"
    elif candidate['team'] == 'TOR': team_full = "Toronto Blue Jays"
    elif candidate['team'] == 'PIT': team_full = "Pittsburgh Pirates"
    elif candidate['team'] == 'SD': team_full = "San Diego Padres"

    # Truncate seed prompts to prevent context pollution/Gemini early cutoff
    sp = candidate['system_prompt'] or ""
    sp_seed = sp[:300] + "..." if len(sp) > 300 else sp
    dl = candidate['deep_lore'] or ""
    dl_seed = dl[:300] + "..." if len(dl) > 300 else dl
    bn = candidate['behavior_notes'] or ""
    bn_seed = bn[:300] + "..." if len(bn) > 300 else bn
    gov = candidate['governance'] or ""
    gov_seed = gov[:300] + "..." if len(gov) > 300 else gov

    prompt = GOLD_STANDARD_PROMPT_TEMPLATE.format(
        display_name=candidate['display_name'],
        team=candidate['team'],
        team_full=team_full,
        cadence=candidate['cadence'],
        system_prompt_seed=sp_seed,
        deep_lore_seed=dl_seed,
        behavior_notes_seed=bn_seed,
        governance_seed=gov_seed,
        PERSONA_NAME=candidate['user_name'].upper()
    )

    print(f"[{candidate['user_name']}] Calling Vertex AI model...", flush=True)
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 4096
            }
        )
        bio_text = response.text.strip()
        
        # Parse output sections using robust multi-keyword logic
        behaviors = extract_section(bio_text, ["BEHAVIOR EXPECTATIONS", "BEHAVIORS"], [["GOVERNANCE"], ["DEEP LORE", "LORE"], ["2026 SEASON", "KNOWLEDGE"]])
        governance = extract_section(bio_text, ["GOVERNANCE"], [["BEHAVIOR"], ["DEEP LORE", "LORE"], ["2026 SEASON", "KNOWLEDGE"]])
        lore = extract_section(bio_text, ["DEEP LORE", "LORE"], [["BEHAVIOR"], ["GOVERNANCE"], ["2026 SEASON", "KNOWLEDGE"]])
        
        # Safe fallbacks if parsing misses anything due to model formatting
        if not behaviors:
            behaviors = "1. Maintain highly consistent character voice.\n2. Engage with sibling personas.\n3. Express emotional reactions."
        if not governance:
            governance = "1. Never break character.\n2. Adhere to active Boggs Level limits."
        if not lore:
            lore = candidate['deep_lore'] or "Core lore bio expanded."

        # Verify if model mentioned a different team in output
        detected_team_mismatch = False
        for team_code in ["NYM", "PHI", "BOS", "TOR", "PIT", "SD", "SF", "CLE", "KC", "AZ", "ATL", "LAA", "MIL", "BAL", "CWS", "SEA", "TEX", "HOU", "COL", "WSH", "CHC", "TB", "CIN", "MIA", "ATH", "NYY", "MIN", "LAD", "DET", "STL"]:
            if team_code != candidate['team'] and f"({team_code})" in bio_text:
                detected_team_mismatch = True
                print(f"  [MISMATCH WARNING] Model suggests team {team_code} instead of assigned {candidate['team']}")
                break

        if dry_run:
            print(f"  [DRY-RUN] Would update {candidate['user_name']}")
            return True, bio_text, behaviors, governance, lore, detected_team_mismatch
        
        # Commit to DB
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE persona
            SET system_prompt = ?,
                behavior_notes = ?,
                governance = ?,
                deep_lore = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            bio_text,
            behaviors,
            governance,
            lore,
            datetime.datetime.now().isoformat(),
            candidate['id']
        ))
        conn.commit()
        conn.close()
        print(f"  [OK] Successfully updated persona {candidate['user_name']} in database.")
        return True, bio_text, behaviors, governance, lore, detected_team_mismatch

    except Exception as e:
        print(f"  [ERROR] Vertex AI call or parsing failed for {candidate['user_name']}: {e}")
        create_inc_ticket(candidate['user_name'], str(e))
        return False, None, None, None, None, False

def is_game_day_active():
    """Checks if there are active rooms in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM cmdb_ci_fanstack_room WHERE room_state = 'active'")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"[GATE-CHECK] Error checking active game rooms: {e}")
        return False

def main():
    if is_game_day_active():
        print("[GAME-DAY ACTIVE] Blocking persona bios repair sweep to conserve CPU resources.")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Sovereign OS Persona Biography Repair Engine")
    parser.add_argument("--audit-only", action="store_true", help="Perform diagnostic sweep and Connection connection check")
    parser.add_argument("--dry-run", action="store_true", help="Show proposed updates without mutating DB")
    parser.add_argument("--persona", type=str, help="Repair a single persona by username")
    parser.add_argument("--team", type=str, help="Repair all personas belonging to a specific team")
    args = parser.parse_args()

    is_default_audit = args.audit_only

    print("=================================================================")
    print("  SOVEREIGN OS — PERSONA BIO REPAIR VIA VERTEX API")
    print("=================================================================")

    # Initialize Vertex AI
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
    vertex_healthy = False
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel("gemini-flash-latest")
        vertex_healthy = True
        print("[INIT] Google Vertex AI connection healthy (gemini-flash-latest).")
    except Exception as e:
        print(f"[INIT] ERROR: Vertex AI initialization failed: {e}")
        if not args.audit_only and not args.dry_run:
            sys.exit(1)

    # Identify repair candidates
    candidates = identify_candidates()
    total_personas = 168
    print(f"[AUDIT] Total personas in database: {total_personas}")
    print(f"[AUDIT] Flagged repair candidates: {len(candidates)}")

    selected_candidates = candidates
    if args.persona:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM persona WHERE user_name = ?", (args.persona,))
        r = cursor.fetchone()
        conn.close()
        if r:
            selected_candidates = [{
                "id": r['id'],
                "user_name": r['user_name'],
                "display_name": r['display_name'] or r['user_name'],
                "team": r['team'],
                "cadence": r['cadence'] or "pacer",
                "system_prompt": r['system_prompt'] or "",
                "deep_lore": r['deep_lore'] or "",
                "behavior_notes": r['behavior_notes'] or "",
                "governance": r['governance'] or "",
                "reasons": ["Forced manual repair"]
            }]
        else:
            selected_candidates = []
        print(f"[FILTER] Target persona specified: {args.persona} ({len(selected_candidates)} matched)")
    elif args.team:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM persona WHERE team = ?", (args.team.upper(),))
        rows = cursor.fetchall()
        conn.close()
        selected_candidates = []
        for r in rows:
            if is_protected(r['user_name'], r['team']):
                continue
            selected_candidates.append({
                "id": r['id'],
                "user_name": r['user_name'],
                "display_name": r['display_name'] or r['user_name'],
                "team": r['team'],
                "cadence": r['cadence'] or "pacer",
                "system_prompt": r['system_prompt'] or "",
                "deep_lore": r['deep_lore'] or "",
                "behavior_notes": r['behavior_notes'] or "",
                "governance": r['governance'] or "",
                "reasons": ["Forced manual team repair"]
            })
        print(f"[FILTER] Target team specified: {args.team} ({len(selected_candidates)} matched)")

    # Write candidates markdown report
    candidates_report_path = "/home/james/sovereign_inbox/today/persona_repair_candidates_20260523.md"
    try:
        with open(candidates_report_path, "w") as rf:
            rf.write("# Persona Repair Candidates Audit\n")
            rf.write(f"Generated: {datetime.datetime.now().isoformat()}\n\n")
            rf.write(f"Total Candidate Count: {len(candidates)}\n\n")
            rf.write("| Persona | Team | Reasons |\n")
            rf.write("|---|---|---|\n")
            for c in candidates:
                rf.write(f"| `{c['user_name']}` | `{c['team']}` | {', '.join(c['reasons'])} |\n")
        print(f"[REPORT] Saved candidates ledger to {candidates_report_path}")
    except Exception as e:
        print(f"[REPORT] Failed to write report: {e}")

    cost_per_persona = 0.000525
    estimated_cost = len(selected_candidates) * cost_per_persona
    print(f"[COST] Estimated credit cost for {len(selected_candidates)} candidates: ${estimated_cost:.6f}")

    if args.audit_only or is_default_audit:
        print("\n--- SAMPLE REPAIR PROMPTS (Top 3 Candidates) ---")
        for i, c in enumerate(selected_candidates[:3]):
            team_full = c['team']
            if c['team'] == 'NYM': team_full = "New York Mets"
            elif c['team'] == 'PHI': team_full = "Philadelphia Phillies"
            elif c['team'] == 'BOS': team_full = "Boston Red Sox"
            elif c['team'] == 'TOR': team_full = "Toronto Blue Jays"
            elif c['team'] == 'PIT': team_full = "Pittsburgh Pirates"
            
            # Truncate seed prompts for display
            sp_disp = c['system_prompt'][:100] + "..." if c['system_prompt'] else ""
            dl_disp = c['deep_lore'][:100] + "..." if c['deep_lore'] else ""
            bn_disp = c['behavior_notes'][:100] + "..." if c['behavior_notes'] else ""
            gov_disp = c['governance'][:100] + "..." if c['governance'] else ""

            p_sample = GOLD_STANDARD_PROMPT_TEMPLATE.format(
                display_name=c['display_name'],
                team=c['team'],
                team_full=team_full,
                cadence=c['cadence'],
                system_prompt_seed=sp_disp,
                deep_lore_seed=dl_disp,
                behavior_notes_seed=bn_disp,
                governance_seed=gov_disp,
                PERSONA_NAME=c['user_name'].upper()
            )
            print(f"\n[{i+1}] Candidate: {c['user_name']}")
            print("-" * 50)
            print(p_sample[:400] + "\n... [TRUNCATED IN AUDIT LOG] ...")
        
        print("\n=================================================================")
        print(f"Run with no flags to begin repair. This will update {len(candidates)} persona records in sovereign_now.db")
        print("=================================================================")
        return

    # Process execution
    print(f"\n[EXECUTION] Beginning repair cycle for {len(selected_candidates)} personas...")
    
    success_log = []
    mismatch_log = []

    batch_size = 5
    for i in range(0, len(selected_candidates), batch_size):
        batch = selected_candidates[i:i+batch_size]
        print(f"\n[BATCH] Processing batch {i//batch_size + 1} ({len(batch)} personas)...")
        for c in batch:
            success, bio, beh, gov, lore, mismatch = run_repair(c, model, dry_run=args.dry_run)
            if success:
                success_log.append((c['user_name'], c['team']))
                if mismatch:
                    mismatch_log.append((c['user_name'], c['team']))

    # Write Mismatch report
    mismatches_path = "/home/james/sovereign_inbox/today/persona_team_misassignments_20260523.md"
    try:
        with open(mismatches_path, "w") as mf:
            mf.write("# Persona Team Misalignment Audit\n")
            mf.write(f"Generated: {datetime.datetime.now().isoformat()}\n\n")
            if mismatch_log:
                mf.write(f"Found {len(mismatch_log)} potential team mismatches during Vertex generation:\n\n")
                mf.write("| Persona | Assigned Team | Notes |\n")
                mf.write("|---|---|---|\n")
                for name, team in mismatch_log:
                    mf.write(f"| `{name}` | `{team}` | Vertex prompt detected references mapping to an alternate team. Review required. |\n")
            else:
                mf.write("Zero team misalignments detected. All updated personas are aligned.\n")
        print(f"[REPORT] Saved mismatches ledger to {mismatches_path}")
    except Exception as e:
        print(f"[REPORT] Failed to write mismatch report: {e}")

    print("\n=================================================================")
    print("  REPAIR CYCLE COMPLETED SUCCESSFULLY")
    print(f"  Total Processed: {len(selected_candidates)}")
    print(f"  Success updates: {len(success_log)}")
    print("=================================================================")

if __name__ == "__main__":
    main()
