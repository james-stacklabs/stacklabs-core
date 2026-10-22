#!/home/james/stacklabs/.venv/bin/python3
"""
Patch script for compile_post_show_lookbook.py to implement dynamic day-of-week dispatch.
Path: /home/james/stacklabs/scripts/patch_lookbook_day_of_week.py
"""

import re
import sys
import pathlib

SCRIPT_PATH = pathlib.Path("/home/james/stacklabs/scripts/compile_post_show_lookbook.py")


def patch_file():
    if not SCRIPT_PATH.exists():
        print(f"[-] Script not found: {SCRIPT_PATH}", file=sys.stderr)
        return 1

    content = SCRIPT_PATH.read_text(encoding="utf-8")

    # 1. Define the day-of-week dispatcher helper
    helper_code = '''
def get_broadcast_defaults(date_slug: str, vitals: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """Dynamically resolves broadcast anatomy and intel bullets by day of the week."""
    dt = datetime.strptime(date_slug, "%Y_%m_%d")
    w = dt.weekday()
    h1_v = vitals.get("h1_velocity", vitals.get("avg_velocity", 110))
    h1_m = vitals.get("h1_meltdown", vitals.get("meltdown_index", 60))
    h2_v = vitals.get("h2_velocity", vitals.get("avg_velocity", 110))
    h2_m = vitals.get("h2_meltdown", vitals.get("meltdown_index", 60))
    h3_v = vitals.get("h3_velocity", vitals.get("avg_velocity", 110))
    h3_m = vitals.get("h3_meltdown", vitals.get("meltdown_index", 60))

    if w == 1:  # Tuesday
        anatomy = [
            {"hour": "Hour 1", "time": "12:00–1:00 PM", "focus": "Monologue & Weekend NFL Autopsy", "anchor": "Monologue & Weekend NFL Autopsy", "velocity": f"{h1_v} mpm", "meltdown": f"{h1_m}%", "theme": "NFL Weekend Fallout & Monday Night Autopsy"},
            {"hour": "Hour 2", "time": "1:00–2:00 PM", "focus": "Aaron Rodgers Tuesday Live Spot", "anchor": "Aaron Rodgers Tuesday Live Masterclass", "velocity": f"{h2_v} mpm", "meltdown": f"{h2_m}%", "theme": "Steelers O-Line Shoring, Mike McCarthy Scheme & Cadence"},
            {"hour": "Hour 3", "time": "2:00–3:00 PM", "focus": "Officiating Diatribe & Live Callers", "anchor": "Officiating Diatribe & Live Callers", "velocity": f"{h3_v} mpm", "meltdown": f"{h3_m}%", "theme": "Referee Accountability & Fan Phone Lines"}
        ]
        bullets = [
            ("The Monologue Reaction", "Chat erupted into elevated scrutiny following the weekend game tape breakdown."),
            ("The Rodgers Tuesday Multiplier", f"Peak broadcast velocity surged to {h2_v} msgs/min during Rodgers\\' technical breakdown of scheme and protection."),
            ("Late-Hour Call-In Chaos", "Callers from across sports markets brought high-velocity feedback into the final broadcast block.")
        ]
    elif w == 4:  # Friday
        anatomy = [
            {"hour": "Hour 1", "time": "12:00–1:00 PM", "focus": "Feel Good Friday Monologue & TNF Autopsy", "anchor": "Feel Good Friday Monologue & TNF Autopsy", "velocity": f"{h1_v} mpm", "meltdown": f"{h1_m}%", "theme": "Thursday Night Football Post-Mortem & Weekend Slate Energy"},
            {"hour": "Hour 2", "time": "1:00–2:00 PM", "focus": "Hammer Dahn Board & CFB GameDay Setup", "anchor": "Hammer Dahn Board & CFB GameDay Setup", "velocity": f"{h2_v} mpm", "meltdown": f"{h2_m}%", "theme": "College Football Saturday Preview, Best Bets Board & Lock Picks"},
            {"hour": "Hour 3", "time": "2:00–3:00 PM", "focus": "NFL Weekend Preview & Live SuperChat Mailbag", "anchor": "NFL Weekend Preview & Live SuperChat Mailbag", "velocity": f"{h3_v} mpm", "meltdown": f"{h3_m}%", "theme": "Weekend Matchup Triage, Bleacher Sentiments & Lock-In Bets"}
        ]
        bullets = [
            ("TNF Autopsy Dogpile", "Chat dissected the Thursday Night Football battle, focusing on red-zone playcalling and late-game clock management."),
            ("Hammer Dahn Friday Surge", f"Chat velocity climbed to {h2_v} msgs/min as Tone Digs, Boston Connor, and Ty Schmit locked in the weekend board."),
            ("October Postseason Momentum", "Baseball postseason energy combined with college football previews driving cross-sport sentiment spikes.")
        ]
    else:  # Monday, Wednesday, Thursday
        anatomy = [
            {"hour": "Hour 1", "time": "12:00–1:00 PM", "focus": "Daily Monologue & Trending Stories", "anchor": "Daily Monologue & Trending Stories", "velocity": f"{h1_v} mpm", "meltdown": f"{h1_m}%", "theme": "Breaking Sports Headlines & Studio Banter"},
            {"hour": "Hour 2", "time": "1:00–2:00 PM", "focus": "Guest Spotlight & Technical Film Breakdown", "anchor": "Guest Spotlight & Technical Film Breakdown", "velocity": f"{h2_v} mpm", "meltdown": f"{h2_m}%", "theme": "Expert Film Analysis, Scheme Dissection & Guest Q&A"},
            {"hour": "Hour 3", "time": "2:00–3:00 PM", "focus": "Live Callers & SuperChat Mailbag", "anchor": "Live Callers & SuperChat Mailbag", "velocity": f"{h3_v} mpm", "meltdown": f"{h3_m}%", "theme": "Viewer Reactions, Bleacher Triage & After-Hours Debate"}
        ]
        bullets = [
            ("Opening Segment Velocity", "Early chat acceleration driven by opening monologue hot takes."),
            ("Midday Technical Discussion", f"Sustained discussion around in-studio guest insights averaging {h2_v} msgs/min."),
            ("After-Hours Call-In Pulse", "Viewer superchats and live callers closing out the 3-hour window.")
        ]
    return anatomy, bullets
'''

    if "def get_broadcast_defaults" not in content:
        insert_marker = "def generate_markdown("
        content = content.replace(insert_marker, helper_code + "\n\n" + insert_marker)

    # 2. Update generate_markdown to use dynamic defaults
    old_md_defaults = re.search(r"anatomy = broadcast_anatomy or \[.*?\]\s*bullets = intel_brief or \[.*?\]", content, re.DOTALL)
    if old_md_defaults:
        new_md_defaults = "def_anatomy, def_bullets = get_broadcast_defaults(date_slug, vitals)\n    anatomy = broadcast_anatomy or def_anatomy\n    bullets = intel_brief or def_bullets"
        content = content[:old_md_defaults.start()] + new_md_defaults + content[old_md_defaults.end():]

    # 3. Update generate_html to use dynamic defaults
    old_html_defaults = re.search(r"anatomy = broadcast_anatomy or \[.*?\]\s*bullets = intel_brief or \[.*?\]", content, re.DOTALL)
    if old_html_defaults:
        new_html_defaults = "def_anatomy, def_bullets = get_broadcast_defaults(date_slug, vitals)\n    anatomy = broadcast_anatomy or def_anatomy\n    bullets = intel_brief or def_bullets"
        content = content[:old_html_defaults.start()] + new_html_defaults + content[old_html_defaults.end():]

    # 4. Remove unconditional Aaron Rodgers Tuesday dogpile entry from non-Tuesday runs
    old_rodgers_entry = '''        {
            "id": "rodgers",
            "name": "Aaron Rodgers",
            "role": "Tuesday Guest",
            "velocity": 184,
            "toxic_pct": 74,
            "is_dogpile": False,
            "color": "#A855F7",
            "headline": "Steelers O-line pass protection, Mike McCarthy scheme & DK Metcalf synergy"
        },'''
    if old_rodgers_entry in content:
        replacement_rodgers = '''        # Conditionally include Rodgers only on Tuesdays (weekday 1)
        *( [ {
            "id": "rodgers",
            "name": "Aaron Rodgers",
            "role": "Tuesday Guest",
            "velocity": 184,
            "toxic_pct": 74,
            "is_dogpile": False,
            "color": "#A855F7",
            "headline": "Steelers O-line pass protection, Mike McCarthy scheme & DK Metcalf synergy"
        } ] if datetime.strptime(date_slug, "%Y_%m_%d").weekday() == 1 else ( [ {
            "id": "hammer_dahn",
            "name": "Hammer Dahn Board",
            "role": "Friday Panel",
            "velocity": 145,
            "toxic_pct": 45,
            "is_dogpile": False,
            "color": "#10B981",
            "headline": "Tone Digs and Boston Connor CFB Saturday & NFL Week 7 board locks"
        } ] if datetime.strptime(date_slug, "%Y_%m_%d").weekday() == 4 else [] ) ),'''
        content = content.replace(old_rodgers_entry, replacement_rodgers)

    SCRIPT_PATH.write_text(content, encoding="utf-8")
    print(f"[+] Successfully patched {SCRIPT_PATH} with day-of-week dispatch logic.")
    return 0


if __name__ == "__main__":
    sys.exit(patch_file())
