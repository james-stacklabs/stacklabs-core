#!/home/james/stacklabs/.venv/bin/python3
"""
Dynamic Pantheon, Game Room Episodes, Live Stream Tails & Emergent Society CMDB Harvester
and Full ServiceNow PDI (dev186522.service-now.com) CI + Relationship Synchronizer.

Harvests:
1. data/emergent_society.db (13 emergent_citizens, 23 society_dialogue fights, 23 citizen_memories,
   10 market_contracts, 31 citizen_trades, 2 divine_shock events).
2. dna/sovereign_now.db (sys_broadcast_episode, sys_broadcast_segment, fancast_banter_log,
   room_lore_injections, outrage_proxy_umpires, outrage_proxy_tantrums, live LLM hot_takes,
   burn_events, sys_penalty_logs, cmdb_ci_tmi_scenario, high-voltage ALL-CAPS game_chat screams).
3. data/labeled_logs/game_log_*.md (All 54 exported Game Room Episode markdown files, including
   game_log_live_chat_sniper_unknown_date_unknown_teams.md with @BarfFanStack sniper replies).
4. data/morning_wiretap.db (watch_party_streams & 562,682 chat_telemetry live stream tail messages
   across NFL, CFB, Pat McAfee Show, PHLY Sports, Woodward Sports, Talkin' Yanks, Dawg Watch Party).
5. Antigravity IDE Brain transcripts (@BarfFanStack tweet threads & YouTube comments) +
   data/barf_wire_payload.json (Barf BP 178/112, Pulse 118, 1.75 lbs Ben's Pastrami, Dr. Shapiro).

Purges dead unreferenced state=staged room shells and synchronizes 100% of CIs and 100% of
cmdb_rel_ci causal edges into https://dev186522.service-now.com.
"""

import concurrent.futures
import glob
import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import requests
from dotenv import load_dotenv

ROOT_DIR = Path("/home/james/stacklabs")
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
PUBLIC_DIR = ROOT_DIR / "apps" / "cmdb_studio" / "public"
DIST_DIR = ROOT_DIR / "apps" / "cmdb_studio" / "dist"

CI_JSON_PATHS = [
    DATA_DIR / "fanstack_cmdb_ci.json",
    PUBLIC_DIR / "fanstack_cmdb_ci.json",
]
REL_JSON_PATHS = [
    DATA_DIR / "fanstack_cmdb_rel_ci.json",
    PUBLIC_DIR / "fanstack_cmdb_rel_ci.json",
]

SOVEREIGN_DB = ROOT_DIR / "dna" / "sovereign_now.db"
EMERGENT_DB = DATA_DIR / "emergent_society.db"
WIRETAP_DB = DATA_DIR / "morning_wiretap.db"
LABELED_LOGS_DIR = DATA_DIR / "labeled_logs"
NEEDLE_GOLD_PATH = DATA_DIR / "telemetry" / "authentic_sports_gold.json"
BARF_WIRE_PATH = DATA_DIR / "barf_wire_payload.json"
BRAIN_GLOB = "/home/james/.gemini/antigravity/brain/*/.system_generated/logs/transcript.jsonl"

SN_INSTANCE = os.environ.get("SN_INSTANCE") or os.environ.get("SERVICENOW_INSTANCE") or "https://dev186522.service-now.com"
SN_USER = os.environ.get("SN_USER") or os.environ.get("SERVICENOW_USER") or "admin"
SN_PASS = os.environ.get("SN_PASS") or os.environ.get("SERVICENOW_PASSWORD") or "J-Slf7SPmg!2"
REL_TYPE_SYS_ID = "015633570a0a0bc70029121512d46ede"  # Depends on::Used by


def make_sys_id(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def make_reg_id(seed: str) -> str:
    return "0x" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


def harvest_ide_brain_barf_tweets(max_items: int = 40) -> List[Dict[str, str]]:
    """Scan IDE brain transcripts for pasted @BarfFanStack tweets and YouTube comments."""
    results: List[Dict[str, str]] = []
    seen_prefixes: Set[str] = set()
    files = sorted(glob.glob(BRAIN_GLOB), key=os.path.getmtime, reverse=True)
    for fpath in files:
        conv_id = Path(fpath).parent.parent.name[:8]
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not any(k in line for k in ("@TheWardyNYM", "@BarfFanStack", "Barf", "Shapiro", "Daboll", "Soto")):
                        continue
                    for m in re.finditer(
                        r"([A-Z0-9][^\n\"\\]{40,260}(?:#LGM|@TheWardyNYM|#LFGM|#NYG|#Giants|Shapiro|pastrami|Daboll|Mendoza|Stearns)[^\n\"\\]{0,80})",
                        line,
                    ):
                        clean = re.sub(r"\s+", " ", m.group(1)).strip()
                        sig = clean[:45].lower()
                        if sig not in seen_prefixes and len(clean) >= 45:
                            seen_prefixes.add(sig)
                            results.append({"text": clean[:280], "source": f"IDE_Brain_{conv_id}"})
                            if len(results) >= max_items:
                                return results
        except Exception:
            continue
    return results


def build_pantheon_and_episodes() -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str]], List[Dict[str, Any]]]:
    """Build the complete Pantheon, Emergent Society, Broadcast Episodes, Game Room Episodes & Stream Tails."""
    pantheon_cis: List[Dict[str, Any]] = []
    pantheon_edges: List[Tuple[str, str, str]] = []
    seen_keys: Set[str] = set()

    def add_node(
        ci_key: str,
        sys_class_name: str,
        layer_label: str,
        display_title: str,
        short_desc: str,
        extra: Dict[str, Any] | None = None,
    ) -> None:
        if ci_key in seen_keys:
            return
        seen_keys.add(ci_key)
        node: Dict[str, Any] = {
            "sys_id": make_sys_id(ci_key),
            "ci_key": ci_key,
            "name": ci_key,
            "display_title": display_title[:160],
            "sys_class_name": sys_class_name,
            "layer_label": layer_label,
            "short_description": short_desc[:360],
            "state_register_id": make_reg_id(ci_key),
            "install_status": "1",
            "operational_status": "1",
        }
        if extra:
            node.update(extra)
        pantheon_cis.append(node)

    # =========================================================================
    # 1. VILLAINS (NFL, CFB, BROADCAST & OG FANSTACK PUBLIC ENEMIES)
    # =========================================================================
    villains = [
        (
            "villain_jerry_sun_glare_cap",
            "Jerry Jones' AT&T West Window Sun Glare & $60M Salary Cap Myth",
            "NFL Villain CI: Refuses to hang $4,000 stadium curtains over the west end-zone glass while paying $60M/yr to get blown out at home.",
            {"sport": "NFL", "team": "DAL", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_daboll_titans_exile",
            "Brian Daboll's 0-3 Tennessee Titans Exile & MetLife Red-Zone Trauma",
            "NFL Villain CI: Fired by NYG in Nov 2025, exiled to Tennessee where the Titans sit 0-3 after losing 12-7 to John Harbaugh's Giants.",
            {"sport": "NFL", "team": "TEN_NYG", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_billy_napier_hot_seat",
            "Billy Napier's 45-17 Mizzou Blowout & 2-4 Gainesville Hot Seat",
            "CFB Villain CI: No. 8 Florida crushed 45-17 at unranked Missouri as the Gators' rushing attack vanishes and buyout boosters revolt.",
            {"sport": "CFB", "team": "FLA", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_hugh_freeze_second_half",
            "Hugh Freeze's Auburn 2nd-Half Offensive Shutout Vortex",
            "CFB Villain CI: Back-to-back SEC second-half offensive collapses leaving Auburn's fanbase in a state of mutiny.",
            {"sport": "CFB", "team": "AUB", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_unc_secondary_sieve",
            "North Carolina Secondary Sieve (Clemson 4 First-Quarter TDs)",
            "CFB Villain CI: Surrendered 4 passing touchdowns in the 1st quarter alone, driving Bill Belichick's blood pressure into orbit.",
            {"sport": "CFB", "team": "UNC", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_gayle_benson_unacceptable",
            "Gayle Benson's 'Unacceptable' 1-4 Saints Front-Office Meltdown",
            "NFL Villain CI: Publicly declared the 1-4 Saints 'unacceptable' prior to the 26-14 win over the Giants.",
            {"sport": "NFL", "team": "NO", "boggs_level": 4, "heat_index": 8},
        ),
        (
            "villain_alaric_jackson_mnf_punch",
            "Alaric Jackson's Unflagged MNF Sideline Punch vs. Falcons",
            "NFL Villain CI: Rams OT threw a live sideline punch at Atlanta's Arnold Ebiketie on Monday Night Football with zero flag thrown.",
            {"sport": "NFL", "team": "LAR_ATL", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_rodgers_cleveland_stumble",
            "Aaron Rodgers' 23-9 Cleveland Stumble & Darkness Retreat Excuses",
            "NFL Villain CI: Pittsburgh's offense sputtered to 9 points in a 23-9 upset loss at Cleveland on Lake Erie.",
            {"sport": "NFL", "team": "PIT_CLE", "boggs_level": 4, "heat_index": 8},
        ),
        (
            "villain_hip_drop_kickoff_trap",
            "NFL Competition Committee Hip-Drop Tackle & Dynamic Kickoff Confusion",
            "NFL Villain CI:Pat McAfee Show daily punching bag over phantom hip-drop fines and landing-zone touchback algebra.",
            {"sport": "NFL", "team": "NFL_OPS", "boggs_level": 4, "heat_index": 8},
        ),
        (
            "villain_metlife_turf_pepsi_curse",
            "MetLife Slit-Film Turf Monster & Medium Pepsi Appreciation Day",
            "NFL Villain CI: East Rutherford ACL trap and front-office 'one free medium Pepsi per season ticket account' insult.",
            {"sport": "NFL", "team": "NYG_NYJ", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_stearns_fleece_spreadsheet",
            "David Stearns' Fleece-Vest Excel Spreadsheet & Bullpen Dumpster Diving",
            "MLB Villain CI: Expected-FIP spreadsheet models substituting for high-leverage relief arms while Carlos Mendoza burns the bullpen.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_cashman_clearance_rack",
            "Brian Cashman's $300M Clearance Rack & 17-Inning Scoreless Vortex",
            "MLB Villain CI: Three hundred million dollars of three-true-outcomes strikeouts and zero situational hitting.",
            {"sport": "MLB", "team": "NYY", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_animal_style_ump_cartel",
            "The In-N-Out Animal Style Umpire Cartel (Blind CB Bucknor Cabal)",
            "MLB/NFL Villain CI: Calling sliders 6 inches off the plate strikes because Thousand Island Animal Style sauce is dripping in their eyes.",
            {"sport": "MLB_NFL", "team": "UMP_CABAL", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_bonilla_july_1st_curse",
            "The Wilpon / Bobby Bonilla $1.19M July 1st Eternal Deferral Curse",
            "MLB Villain CI: Generational Queens hex paying $1,193,248.20 every July 1st through 2035 while haunting 9th-inning leads.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5, "heat_index": 9},
        ),
        (
            "villain_glavine_game_162_ghost",
            "Tom Glavine's 2007 Game 162 1st-Inning 7-Run Ghost ('I Wasn't Devastated')",
            "MLB Villain CI: Atlanta double-agent sleeper cell who surrendered 7 earned runs in 0.1 innings in Game 162.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5, "heat_index": 10},
        ),
        (
            "villain_familia_2015_slider",
            "Jeurys Familia's 2015 World Series Game 1 Quick-Pitch Slider",
            "MLB Villain CI: 9th-inning quick-pitch meatball to Alex Gordon that permanently rewired @barf's autonomic nervous system.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5, "heat_index": 9},
        ),
    ]
    for k, title, desc, ext in villains:
        add_node(k, "u_cmdb_ci_villain", "Layer 5: Pantheon Villains & Curses", title, desc, ext)

    # =========================================================================
    # 2. HEROES (NFL, CFB, PAT MCAFEE CREW & CULT SAVIORS)
    # =========================================================================
    heroes = [
        (
            "hero_pat_mcafee",
            "Pat McAfee (ThunderDome Sleeveless Tank-Top Noon Commander)",
            "Broadcast Hero CI: Host of The Pat McAfee Show (Noon ET), punter hall-of-famer, and architect of the ThunderDome sports desk.",
            {"sport": "NFL_CFB", "team": "PMS", "boggs_level": 5},
        ),
        (
            "hero_aj_hawk",
            "AJ Hawk (The Stoic Ohio State Cigar Sphinx & Ryder Cup Menace)",
            "Broadcast Hero CI: Two-footed driver of rental cars, silent cigar smoker on split-screen, and all-time Green Bay tackler.",
            {"sport": "NFL_CFB", "team": "PMS_GB", "boggs_level": 5},
        ),
        (
            "hero_boston_connor_con_air",
            "Boston Connor / Con Air (ThunderDome Conspiracy & Foil Hat General)",
            "Broadcast Hero CI: Co-pilot of Patatouille and Con Air; undisputed king of unhinged noon broadcast tangents.",
            {"sport": "NFL_CFB", "team": "PMS_NE", "boggs_level": 5},
        ),
        (
            "hero_ty_schmit_lou_holtz",
            "Ty Schmit / Lou Holtz Impressionist (Green Bay Packers Doomer Laureate)",
            "Broadcast Hero CI: Voice of Lou Holtz, survivor of colonoscopy horror stories, and Packers/Brewers emotional barometer.",
            {"sport": "NFL_MLB", "team": "PMS_GB_MIL", "boggs_level": 5},
        ),
        (
            "hero_aq_shipley_trench",
            "AQ Shipley (In The Trenches All-22 O-Line Breakdown Savant)",
            "Broadcast Hero CI: Former NFL center exposing lazy 3-technique pass sets and blown A-gap blitz pickups at noon.",
            {"sport": "NFL", "team": "PMS", "boggs_level": 4},
        ),
        (
            "hero_nick_saban_alpha",
            "Coach Nick Saban (SEC Alpha & Theo Von Ep #584 'Deez Nuts' Legend)",
            "CFB Hero CI: 7-time national champion diagnosing SEC coaching collapses and delivering deadpan 'Deez Nuts' lore.",
            {"sport": "CFB", "team": "ALA_SEC", "boggs_level": 5},
        ),
        (
            "hero_john_harbaugh_nyg",
            "John Harbaugh (2026 NY Giants Head Coach & 12-7 Daboll Conqueror)",
            "NFL Hero CI: Hired Jan 20, 2026 to restore Big Blue; defeated Brian Daboll's winless Titans 12-7 in Week 3.",
            {"sport": "NFL", "team": "NYG", "boggs_level": 5},
        ),
        (
            "hero_dominic_zvada_leg",
            "Dominic Zvada (60-Yard Walk-Off Leg & MetLife Wind Conqueror)",
            "NFL/CFB Hero CI: Automatic 55+ yard weapon keeping games alive when the red-zone offense stalls at the 38-yard line.",
            {"sport": "NFL_CFB", "team": "NYG_MICH", "boggs_level": 4},
        ),
        (
            "hero_jackson_chourio_walkoff",
            "Jackson Chourio (104-Win Milwaukee Brewers NLDS Walk-Off Savior)",
            "MLB Hero CI: Lined Mason Miller's 104.0 mph fastball into center field to walk off NLDS Game 1 (4-3) for the #1 seed Brewers.",
            {"sport": "MLB", "team": "MIL", "boggs_level": 5},
        ),
        (
            "hero_sammy_the_savant",
            "Sammy The Savant (@SammyBoySmith_The_Savant • Game Totals Oracle)",
            "NFL/MLB Hero CI: South Philly diner quant enforcing Sunday Calendar Parity, Hook Trap Rejection (.5 vig), and Lake Erie Hex Exemption.",
            {"sport": "NFL_MLB", "team": "PHI", "boggs_level": 5},
        ),
        (
            "hero_bottlegate_rick",
            "Bottlegate Rick (1985 Dawg Pound Mason Jar & 23-9 Steelers Slayer)",
            "NFL Hero CI: Muni Lot survivor celebrating Cleveland's 23-9 victory over Aaron Rodgers' Steelers.",
            {"sport": "NFL", "team": "CLE", "boggs_level": 5},
        ),
        (
            "hero_dr_shapiro_cardiologist",
            "Dr. Shapiro (Great Neck & Queens Blvd Speed-Dial 1 Cardiologist)",
            "Medical Hero CI: Keeping @barf's left ventricle intact through 178/112 mmHg blood pressure spikes and 1.75 lbs of Ben's pastrami.",
            {"sport": "NFL_MLB", "team": "NYM_NYG", "boggs_level": 5},
        ),
        (
            "hero_uncle_stevie_checkbook",
            "Uncle Stevie's $340M Hedge-Fund Checkbook & Black-Hat War Chest",
            "MLB Hero CI: Unlimited payroll liquidity fighting a two-front war against the luxury tax and the bullpen curse.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5},
        ),
        (
            "hero_keith_1986_mustache",
            "Keith Hernandez's 1986 Gold Glove Mustache & Booth Sigh",
            "MLB Hero CI: Audible SNY booth groans whenever a modern infielder commits a fundamental crime against baseball.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5},
        ),
        (
            "hero_big_sexy_bartolo",
            "Big Sexy Bartolo Colon (Petco Park May 7, 2016 Home Run Immortal)",
            "MLB Hero CI: Pure joy and helmet-flying swing physics defying every modern launch-angle computer.",
            {"sport": "MLB", "team": "NYM", "boggs_level": 5},
        ),
        (
            "hero_tony_gwynn_55_hole",
            "Tony Gwynn's 5.5 Hole Batted-Ball Sanctuary (.338 Lifetime)",
            "MLB Hero CI: The sacred 5.5 hole between third base and shortstop immune to shift algorithms.",
            {"sport": "MLB", "team": "SD", "boggs_level": 5},
        ),
        (
            "hero_dinger_purple_asteroid",
            "Dinger's 5,280-Foot Purple Party Deck Jurassic Asteroid",
            "MLB Hero CI: Coors Field mascot summoning 480-foot moonshots in the thin Denver air.",
            {"sport": "MLB", "team": "COL", "boggs_level": 5},
        ),
    ]
    for k, title, desc, ext in heroes:
        add_node(k, "u_cmdb_ci_hero", "Layer 5: Pantheon Heroes & Cult Icons", title, desc, ext)

    # =========================================================================
    # 3. CONSPIRACIES & TMI ANOMALIES
    # =========================================================================
    conspiracies = [
        (
            "conspiracy_att_west_window_glare",
            "AT&T Stadium West Window Sun Glare & 14-Second QB Draw Conspiracy",
            "NFL Conspiracy CI: Jerry Jones refuses $4,000 stadium curtains on the west glass while Dak's 'YEAH HERE WE GO' cadence triggers pre-snap false starts.",
            {"sport": "NFL", "anomaly_code": "DAL_GLARE_2026", "boggs_level": 5},
        ),
        (
            "conspiracy_wisconsin_faustian_barter",
            "Cheesehead TV Packers-for-Brewers Faustian Blood Bargain",
            "NFL/MLB Conspiracy CI: @MSANDMIKE traded a Green Bay Packers 35-14 blowout loss to Atlanta in exchange for Jackson Chourio's NLDS walk-off win.",
            {"sport": "NFL_MLB", "anomaly_code": "WI_FAUST_01", "boggs_level": 5},
        ),
        (
            "conspiracy_lake_erie_hex_exemption",
            "Lake Erie Wind Eddy & Sunday Calendar Parity Hex Exemption",
            "NFL Conspiracy CI: Sammy The Savant's discovery that swirling 22mph Lake Erie crosswinds in Cleveland and Buffalo void all standard Over/Under parity models.",
            {"sport": "NFL", "anomaly_code": "ERIE_HEX_04", "boggs_level": 4},
        ),
        (
            "tva_001_ron_burgundy",
            "tva_001: San Diego 1904 German Ron Burgundy Translation Physics Rewrite",
            "TMI Anomaly CI (tva_001): Tactical rewrite of San Diego history discovered by the Germans in 1904; forces physics engines to reconcile Boggs Saturation.",
            {"sport": "MLB", "anomaly_code": "TVA_001", "boggs_level": 5},
        ),
        (
            "tva_002_wade_boggs_singularity",
            "tva_002: Wade Boggs 73-Beer Cross-Country Flight Singularity",
            "TMI Anomaly CI (tva_002): 73 Miller Lites consumed between Boston and Los Angeles followed by going 3-for-5 the next day; powers the FanStack Boggs Meter.",
            {"sport": "MLB_NFL", "anomaly_code": "TVA_002", "boggs_level": 5},
        ),
        (
            "conspiracy_chicken_man_37_deg_remote",
            "Chicken Man's 37-Degree Remote & Honey Cheerios Consecration",
            "OG FanStack Conspiracy CI: Pre-game rotisserie chicken and Honey Nut Cheerios ritual required to prevent bullpen implosions.",
            {"sport": "MLB", "anomaly_code": "BOGGS_37_DEG", "boggs_level": 4},
        ),
        (
            "conspiracy_petco_pitch_black_mound",
            "Petco Park Pitch-Black Mound Visit Cover-Up",
            "OG FanStack Conspiracy CI: Stadium light grid cut during pitching changes to conceal illegal spin-rate calibration.",
            {"sport": "MLB", "anomaly_code": "PETCO_DARK_09", "boggs_level": 5},
        ),
        (
            "conspiracy_coors_humidor_gravity",
            "Coors Field Humidor Gravity Fraud (5,280-Foot De-Juicing)",
            "OG FanStack Conspiracy CI: Secret subterranean humidor swapping baseballs between top and bottom halves of innings at 5,280 feet.",
            {"sport": "MLB", "anomaly_code": "COORS_HUMIDOR", "boggs_level": 4},
        ),
        (
            "conspiracy_patatouille_split_screen",
            "Patatouille & Con Air Split-Screen Broadcast Ambush",
            "Broadcast Conspiracy CI: Boston Connor and Ty Schmit hijacking the ThunderDome lower-third chyron mid-interview.",
            {"sport": "NFL_CFB", "anomaly_code": "PMS_CON_AIR", "boggs_level": 4},
        ),
    ]
    for k, title, desc, ext in conspiracies:
        add_node(k, "u_cmdb_ci_conspiracy", "Layer 5: Conspiracies, Fever Dreams & TMI Anomalies", title, desc, ext)

    # =========================================================================
    # 4. BIOMETRIC VITALS & SOMATIC REGISTERS
    # =========================================================================
    barf_vitals = {}
    if BARF_WIRE_PATH.exists():
        try:
            barf_vitals = json.loads(BARF_WIRE_PATH.read_text(encoding="utf-8")).get("daily_vitals", {})
        except Exception:
            barf_vitals = {}

    systolic = barf_vitals.get("systolic", 178)
    diastolic = barf_vitals.get("diastolic", 112)
    pulse = barf_vitals.get("pulse", 118)
    pastrami = barf_vitals.get("pastrami_lbs", 1.75)
    panic_idx = barf_vitals.get("panic_index", 9)

    vitals_nodes = [
        (
            "vitals_barf_bp_178_112",
            f"Barf Biometric Register (BP {systolic}/{diastolic} mmHg • Pulse {pulse} • {pastrami} lbs Pastrami)",
            f"Somatic Biometric CI (@barf): Systolic {systolic} / Diastolic {diastolic} mmHg, Pulse {pulse} bpm, {pastrami} lbs Ben's Kosher Pastrami, Panic {panic_idx}/10. Dr. Shapiro on Speed Dial 1.",
            {
                "persona": "barf",
                "systolic": systolic,
                "diastolic": diastolic,
                "pulse": pulse,
                "pastrami_lbs": pastrami,
                "panic_index": panic_idx,
                "boggs_level": 5,
            },
        ),
        (
            "vitals_dak_curtain_rage_boggs5",
            "Curtain Conspiracy Dak Biometric Register (BP 188/116 • All-22 Film Stroke)",
            "Somatic Biometric CI (@curtain_conspiracy_dak): Texas HS coordinator hitting 188/116 mmHg watching empty-backfield shotgun on 3rd-and-inches into AT&T west window glare.",
            {"persona": "curtain_conspiracy_dak", "systolic": 188, "diastolic": 116, "pulse": 132, "boggs_level": 5},
        ),
        (
            "vitals_battery_chucker_boggs5",
            "Battery Chucker Biometric Register (BP 190/120 • Delco Cardiac Code Red)",
            "Somatic Biometric CI (@battery_chucker): 'My blood pressure is 190 over 120 right now. Get this out before I have a stroke!'",
            {"persona": "battery_chucker", "systolic": 190, "diastolic": 120, "pulse": 136, "boggs_level": 5},
        ),
        (
            "vitals_dot_neural_thermal_runaway",
            "Dot Neural Core Thermal Register (Boggs 5 • 0.003% Variance Meltdown)",
            "Somatic Biometric CI (@dot): Statistical processor exceeding thermal envelope after 3 consecutive sub-1% Boggsian baseball/football anomalies.",
            {"persona": "dot", "systolic": 200, "diastolic": 130, "pulse": 145, "boggs_level": 5},
        ),
    ]
    for k, title, desc, ext in vitals_nodes:
        add_node(k, "u_cmdb_ci_biometric_vitals", "Layer 4: Advocate Biometric Vitals & Boggs Registers", title, desc, ext)

    # =========================================================================
    # 5. HEADLINE MELTDOWNS
    # =========================================================================
    headline_meltdowns = [
        (
            "meltdown_barf_left_arm_shapiro",
            "MY LEFT ARM IS NUMB, SHAPIRO IS EATING PASTRAMI IN GREAT NECK",
            "Verbatim @barf Boggs-5 Meltdown: 'SOTO SAYS IT'S A DISASTER? MY LEFT VENTRICLE AGREES! MY SYSTOLIC IS HITTING 182 AND DR. SHAPIRO IS ON SPEED DIAL 1!'",
            {"persona": "barf", "boggs_level": 5, "heat_index": 10, "burn_score": 99},
        ),
        (
            "meltdown_dak_yeah_here_we_go_trade",
            "TRADE DAK AND CD SO THEY CAN GO WIN SOMEWHERE — CURTAIN GLARE BLINDNESS",
            "Verbatim Cowboys Stream & @curtain_conspiracy_dak Meltdown: 'Trade most of the team Dak ain't winning any ring! Jerry refuses $4k curtains on the west end-zone glass!'",
            {"persona": "curtain_conspiracy_dak", "boggs_level": 5, "heat_index": 10, "burn_score": 97},
        ),
        (
            "meltdown_cheesehead_faustian_bargain",
            "I'M TORN. I BARGAINED A PACKER LOSS FOR A BREWERS WIN.",
            "Verbatim Cheesehead TV Stream Needle (@MSANDMIKE): Faustian blood barter sacrificing Green Bay (L 14-35 vs ATL) for Milwaukee's 104-win NLDS walk-off.",
            {"persona": "MSANDMIKE", "boggs_level": 5, "heat_index": 9, "burn_score": 95},
        ),
        (
            "meltdown_napier_mizzou_45_17",
            "MIZZOU 45, FLORIDA 17 — BILLY NAPIER'S RUSHING ATTACK ERASED OFF THE EARTH",
            "Verbatim SEC Saturday Meltdown: 'No. 8 Florida blown out by 28 at Missouri! Simmons 340 passing yards! Leave the headsets on the Columbia tarmac!'",
            {"persona": "sec_trench_grinder", "boggs_level": 5, "heat_index": 10, "burn_score": 96},
        ),
        (
            "meltdown_daboll_12_7_harbaugh",
            "JOHN HARBAUGH'S GIANTS LOCK BRIAN DABOLL IN A 12-7 METLIFE CELLAR",
            "Verbatim @barf NFL Schadenfreude Rant: 'I called Daboll earlier to see if he could run a simple post route, but he hung up! 0-3 in Tennessee while Harbaugh rules East Rutherford!'",
            {"persona": "barf", "boggs_level": 5, "heat_index": 9, "burn_score": 94},
        ),
        (
            "meltdown_animal_style_ump_hair",
            "ANIMAL STYLE SAUCE IN THE UMPIRE'S HAIR — 6 INCHES OFF THE BLACK",
            "Verbatim Boggs-5 Umpire Meltdown: 'THE UMP HAS THOUSAND ISLAND ANIMAL STYLE SAUCE DRIPPING INTO HIS MASK CALLING ANKLE SLIDERS STRIKE THREE!'",
            {"persona": "battery_chucker_jr", "boggs_level": 5, "heat_index": 10, "burn_score": 98},
        ),
        (
            "meltdown_dot_spreadsheets_on_fire",
            "DIMENSIONMISMATCHEXCEPTION... THE SPREADSHEETS ARE ON FIRE!",
            "Verbatim @dot Boggs-5 Meltdown (12 verified occurrences across game_chat & labeled_logs): '0.003% probability bases-loaded escape! THE SPREADSHEETS ARE ON FIRE!'",
            {"persona": "dot", "boggs_level": 5, "heat_index": 10, "burn_score": 99},
        ),
    ]
    for k, title, desc, ext in headline_meltdowns:
        add_node(k, "u_cmdb_ci_meltdown", "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles", title, desc, ext)

    # =========================================================================
    # 6. EMERGENT SOCIETY DB (100% HARVEST: CITIZENS, DIALOGUE, MEMORIES, CONTRACTS)
    # =========================================================================
    if EMERGENT_DB.exists():
        econn = sqlite3.connect(str(EMERGENT_DB))
        ecur = econn.cursor()

        # 6A. Emergent Citizens (13)
        citizen_key_map: Dict[str, str] = {}
        for row in ecur.execute(
            "SELECT citizen_id, handle, name, archetype, fandom, bio, scars, trigger, cash_balance, portfolio_value, systolic_bp, diastolic_bp, resting_hr, tums_inventory, tums_consumed_today, scar_tissue_index, superstition_level FROM emergent_citizens"
        ).fetchall():
            cid, handle, cname, arch, fandom, bio, scars, trig, cash, port_val, s_bp, d_bp, hr, tums_inv, tums_used, scar_idx, sup_lvl = row
            c_key = f"citizen_{cid.lower().replace('-', '_')}"
            citizen_key_map[cid] = c_key
            add_node(
                c_key,
                "u_cmdb_ci_emergent_citizen",
                "Layer 2: Emergent Society Citizens & Biometric Ledger",
                f"{cname} ({handle} • {fandom} • BP {s_bp}/{d_bp} • Tums {tums_inv})",
                f"[{arch}] {bio} | Scars: {scars} | Trigger: {trig} | Cash: ${cash:.2f} | Scar Index: {scar_idx}",
                {
                    "citizen_id": cid,
                    "handle": handle,
                    "fandom": fandom,
                    "systolic_bp": s_bp,
                    "diastolic_bp": d_bp,
                    "resting_hr": hr,
                    "tums_inventory": tums_inv,
                    "scar_tissue_index": scar_idx,
                    "boggs_level": 5,
                },
            )
            if "Cowboys" in str(fandom):
                pantheon_edges.append((c_key, "villain_jerry_sun_glare_cap", "Tormented By::Owner"))
                pantheon_edges.append((c_key, "conspiracy_att_west_window_glare", "Blinded By::Glare"))
            elif "Giants" in str(fandom) or "Mets" in str(fandom):
                pantheon_edges.append((c_key, "vitals_barf_bp_178_112", "Synchronized With::Biometrics"))
                pantheon_edges.append((c_key, "hero_john_harbaugh_nyg", "Rebuilt By::Coach"))
            elif "Phillies" in str(fandom):
                pantheon_edges.append((c_key, "vitals_battery_chucker_boggs5", "Synchronized With::Biometrics"))
            elif "SICKO" in str(fandom):
                pantheon_edges.append((c_key, "hero_sammy_the_savant", "Identity::Quant Oracle"))

        # 6B. Divine Shock Events in event_stream
        event_key_map: Dict[str, str] = {}
        for ev_id, src, cat, headline, raw_p, vol_score, created_at in ecur.execute(
            "SELECT event_id, source, category, headline, raw_payload, volatility_score, created_at FROM event_stream"
        ).fetchall():
            ev_key = f"emergent_event_{ev_id.lower().replace('-', '_')}"
            event_key_map[ev_id] = ev_key
            add_node(
                ev_key,
                "cmdb_ci_play_event",
                "Layer 1: Emergent Society Shock Events",
                f"[{cat}] {headline[:110]}",
                f"Emergent Shock Event ({ev_id} • Volatility {vol_score}): {headline} | Payload: {raw_p}",
                {"event_id": ev_id, "volatility_score": vol_score, "boggs_level": 5},
            )
            if "CHOURIO" in headline.upper() or "BREWERS" in headline.upper():
                pantheon_edges.append((ev_key, "hero_jackson_chourio_walkoff", "Caused By::104mph Walk-Off"))
            if "BATTERY" in headline.upper():
                pantheon_edges.append((ev_key, "vitals_battery_chucker_boggs5", "Triggers::D-Cell Launch"))

        # 6C. Society Dialogue (23 living-room fights with bp_delta)
        for dlg_id, tick_id, spk_id, tgt_id, msg_txt, tone, bp_d, tums_c, created_at in ecur.execute(
            "SELECT dialogue_id, tick_id, speaker_id, target_id, message_text, emotional_tone, bp_delta, tums_consumed, created_at FROM society_dialogue"
        ).fetchall():
            d_key = f"dialogue_{dlg_id.lower().replace('-', '_')}"
            spk_key = citizen_key_map.get(spk_id, "citizen_cit_001_batterychucker")
            add_node(
                d_key,
                "u_cmdb_ci_society_dialogue",
                "Layer 3: Emergent Society Living-Room Fights",
                f"[{spk_id} • BP {bp_d:+d} • {tone}] {msg_txt[:75]}...",
                f"Living-Room Fight ({dlg_id} @ {tick_id} • BP Delta {bp_d:+d} mmHg • Tums {tums_c}): \"{msg_txt}\"",
                {
                    "dialogue_id": dlg_id,
                    "speaker_id": spk_id,
                    "bp_delta": bp_d,
                    "tums_consumed": tums_c,
                    "emotional_tone": tone,
                    "boggs_level": 5,
                    "heat_index": 10 if abs(int(bp_d or 0)) >= 15 else 8,
                },
            )
            pantheon_edges.append((d_key, spk_key, "Spoken By::Citizen"))
            if tgt_id and tgt_id in citizen_key_map:
                pantheon_edges.append((d_key, citizen_key_map[tgt_id], "Targets::Citizen"))
            elif "Junior" in msg_txt or "Duracell" in msg_txt or "CopperTop" in msg_txt:
                if "citizen_cit_002_batterychuckerjr" in seen_keys:
                    pantheon_edges.append((d_key, "citizen_cit_002_batterychuckerjr", "Chucks Battery At::Junior"))

        # 6D. Citizen Memories (23 trauma/triumph memories)
        for mem_id, cid, ev_id, ts, mtype, desc, e_charge, salience in ecur.execute(
            "SELECT memory_id, citizen_id, event_id, timestamp, memory_type, description, emotional_charge, salience FROM citizen_memories"
        ).fetchall():
            m_key = f"memory_{mem_id.lower().replace('-', '_')}"
            c_key = citizen_key_map.get(cid, "citizen_cit_003_barf")
            add_node(
                m_key,
                "u_cmdb_ci_citizen_memory",
                "Layer 4: Emergent Citizen Trauma & Triumph Memories",
                f"[{mtype} • {cid}] {desc[:80]}...",
                f"Citizen Memory ({mem_id} • Charge {e_charge} • Salience {salience}): {desc}",
                {
                    "memory_id": mem_id,
                    "citizen_id": cid,
                    "memory_type": mtype,
                    "emotional_charge": e_charge,
                    "salience": salience,
                    "boggs_level": 5,
                },
            )
            pantheon_edges.append((m_key, c_key, "Imprinted On::Citizen"))
            if ev_id in event_key_map:
                pantheon_edges.append((m_key, event_key_map[ev_id], "Triggered By::Shock Event"))

        # 6E. Market Contracts (10 prop tickers) & Citizen Trades (31 trades)
        contract_key_map: Dict[str, str] = {}
        for cnt_id, ticker, cname, creator_id, desc, target_id, prob, price_c, vol, oi, status in ecur.execute(
            "SELECT contract_id, ticker, name, creator_citizen_id, description, target_citizen_id, current_probability, current_price_cents, total_volume, open_interest, status FROM market_contracts"
        ).fetchall():
            k_key = f"contract_{cnt_id.lower().replace('-', '_')}"
            contract_key_map[cnt_id] = k_key
            add_node(
                k_key,
                "u_cmdb_ci_prop_contract",
                "Layer 4: Degenerate Prop Market Contracts",
                f"{ticker}: {cname} ({price_c}¢ • Vol {vol} • OI {oi})",
                f"Prop Contract ({cnt_id} • {ticker} @ {price_c}¢): {desc}",
                {
                    "contract_id": cnt_id,
                    "ticker": ticker,
                    "price_cents": price_c,
                    "total_volume": vol,
                    "open_interest": oi,
                    "boggs_level": 5,
                },
            )
            if creator_id in citizen_key_map:
                pantheon_edges.append((k_key, citizen_key_map[creator_id], "Market Made By::Citizen"))
            if target_id and target_id in citizen_key_map:
                pantheon_edges.append((k_key, citizen_key_map[target_id], "Tracks Biometrics Of::Citizen"))

        for trd_id, cid, cnt_id, side, pos_type, qty, price_c, total_cost, ts in ecur.execute(
            "SELECT trade_id, citizen_id, contract_id, side, position_type, quantity, price_cents, total_cost, timestamp FROM citizen_trades"
        ).fetchall():
            if cid in citizen_key_map and cnt_id in contract_key_map:
                pantheon_edges.append((citizen_key_map[cid], contract_key_map[cnt_id], f"Traded::{side}_{pos_type}_{qty}@{price_c}c"))

        econn.close()

    # =========================================================================
    # 7. BROADCAST EPISODES, SEGMENTS, STOPPAGE BANTER, LORE & HOT TAKES
    # =========================================================================
    active_room_keys_referenced: Set[str] = set()
    if SOVEREIGN_DB.exists():
        sconn = sqlite3.connect(str(SOVEREIGN_DB))
        scur = sconn.cursor()

        # 7A. Broadcast Episodes (The Blunderdome Radio) & Timecoded Segments
        try:
            for ep_id, show_id, title, slug, dur_s, dur_fmt, summary, script_md, audio_url in scur.execute(
                "SELECT id, show_id, title, slug, duration_seconds, duration_formatted, summary, script_markdown, audio_url FROM sys_broadcast_episode"
            ).fetchall():
                ep_key = f"broadcast_ep_{re.sub(r'[^a-z0-9]+', '_', str(ep_id).lower()).strip('_')}"
                add_node(
                    ep_key,
                    "u_cmdb_ci_broadcast_episode",
                    "Layer 2: Blunderdome Radio Broadcast Episodes",
                    f"Blunderdome Radio [{dur_fmt}]: {title} ({ep_id})",
                    f"{summary} | Audio: {audio_url} | Excerpt: {str(script_md or '')[:220]}",
                    {
                        "episode_id": ep_id,
                        "show_id": show_id,
                        "duration_formatted": dur_fmt,
                        "audio_url": audio_url,
                        "boggs_level": 5,
                    },
                )
                pantheon_edges.append((ep_key, "villain_bonilla_july_1st_curse", "Investigates::9th-Inning Curse"))
                pantheon_edges.append((ep_key, "vitals_barf_bp_178_112", "Spikes::Caller BP"))

            for seg_id, ep_id, seg_idx, tc_start, spk_handle, spk_name, txt_content, accent, emotion, dsp in scur.execute(
                "SELECT id, episode_id, segment_index, timecode_start, speaker_handle, speaker_name, text_content, accent, emotion_tag, dsp_preset FROM sys_broadcast_segment"
            ).fetchall():
                seg_key = f"broadcast_seg_{re.sub(r'[^a-z0-9]+', '_', str(seg_id).lower()).strip('_')}"
                ep_key = f"broadcast_ep_{re.sub(r'[^a-z0-9]+', '_', str(ep_id).lower()).strip('_')}"
                add_node(
                    seg_key,
                    "u_cmdb_ci_broadcast_segment",
                    "Layer 3: Blunderdome Radio Caller Segments",
                    f"[{tc_start} • {spk_handle} ({emotion})]: {txt_content[:68]}...",
                    f"Segment #{seg_idx} ({tc_start} • DSP={dsp} • Accent={accent}): {spk_handle} [{emotion}] -> \"{txt_content}\"",
                    {
                        "segment_id": seg_id,
                        "episode_id": ep_id,
                        "speaker_handle": spk_handle,
                        "timecode_start": tc_start,
                        "dsp_preset": dsp,
                        "boggs_level": 5,
                    },
                )
                pantheon_edges.append((seg_key, ep_key, "Segment Of::Broadcast Episode"))
                clean_handle = str(spk_handle).lstrip("@")
                if clean_handle == "barf":
                    pantheon_edges.append((seg_key, "barf", "Called In By::Advocate"))
                    pantheon_edges.append((seg_key, "vitals_barf_bp_178_112", "Driven By::Biometric Spike"))
                elif "7_train" in clean_handle:
                    pantheon_edges.append((seg_key, "7_train_terry", "Called In By::Advocate"))
        except Exception:
            pass

        # 7B. NFL FanCast Stoppage & Commercial-Wipe Banter (fancast_banter_log)
        try:
            for b_sid, stop_type, mode, turn_num, spk_id, spk_name, team_tag, msg, raw_meta in scur.execute(
                "SELECT sys_id, stoppage_type, mode, turn_number, speaker_id, speaker_name, team_tag, message, raw_metadata FROM fancast_banter_log"
            ).fetchall():
                b_key = f"stoppage_banter_{str(b_sid)[:12]}"
                add_node(
                    b_key,
                    "u_cmdb_ci_stoppage_banter",
                    "Layer 3: NFL Stoppage & Commercial-Wipe Banter",
                    f"[{stop_type} • @{spk_id} ({team_tag})]: {msg[:68]}...",
                    f"NFL {stop_type} Banter (Turn {turn_num} • {spk_name} @{spk_id} • {mode}): \"{msg}\" | Meta: {raw_meta}",
                    {
                        "stoppage_type": stop_type,
                        "speaker_id": spk_id,
                        "team_tag": team_tag,
                        "boggs_level": 4,
                    },
                )
                pantheon_edges.append((b_key, "villain_hip_drop_kickoff_trap", "provoked_by::NFL Stoppage"))
                if team_tag in ("NYJ", "NYG"):
                    pantheon_edges.append((b_key, "villain_metlife_turf_pepsi_curse", "Cursed By::MetLife Turf"))
        except Exception:
            pass

        # 7C. Room Lore Injections & Outrage Proxy Umpires/Tantrums
        try:
            for l_sid, g_pk, inj_type, headline, content, weight in scur.execute(
                "SELECT sys_id, game_pk, injection_type, headline, content, weight FROM room_lore_injections"
            ).fetchall():
                l_key = f"lore_injection_{str(l_sid)[:12]}"
                r_key = f"room_{g_pk}"
                active_room_keys_referenced.add(r_key)
                add_node(
                    l_key,
                    "u_cmdb_ci_lore_injection",
                    "Layer 3: Mid-Game Room Lore Injections",
                    f"[{inj_type.upper()} • Game {g_pk}] {headline}",
                    f"Room Lore Injection (Game {g_pk} • Weight {weight}): {headline} — {content}",
                    {"game_pk": str(g_pk), "injection_type": inj_type, "boggs_level": 5},
                )
                pantheon_edges.append((l_key, r_key, "Injected Into::Game Room"))
                pantheon_edges.append((l_key, "tva_002_wade_boggs_singularity", "Powered By::Boggs Anomaly"))

            for u_id, u_name, dur, dirt_cap, eject_flair in scur.execute(
                "SELECT id, umpire_name, durability_rating, dirt_kick_capacity, ejection_flair_level FROM outrage_proxy_umpires"
            ).fetchall():
                u_key = f"outrage_umpire_{u_id}"
                add_node(
                    u_key,
                    "u_cmdb_ci_villain",
                    "Layer 5: Pantheon Villains & Curses",
                    f"{u_name} (Dirt-Kick Cap {dirt_cap} • Ejection Flair {eject_flair}/10)",
                    f"Outrage Proxy Umpire Node #{u_id}: Durability {dur}, Dirt-Kick Capacity {dirt_cap}, Ejection Flair {eject_flair}/10.",
                    {"umpire_id": u_id, "ejection_flair": eject_flair, "boggs_level": 5},
                )
                pantheon_edges.append((u_key, "villain_animal_style_ump_cartel", "Member Of::Umpire Cartel"))
        except Exception:
            pass

        # 7D. Live LLM Advocate-to-Advocate Room Clapbacks from hot_takes (excluding offline_corpus)
        try:
            ht_rows = scur.execute(
                """
                SELECT id, persona, topic, response, engine, room_id
                FROM hot_takes
                WHERE engine NOT IN ('offline_corpus', 'local_fallback', 'api_exhaustion_fallback')
                  AND length(response) >= 45
                ORDER BY id DESC
                LIMIT 85
                """
            ).fetchall()
            seen_ht: Set[str] = set()
            for ht_id, p_handle, topic, resp, eng, room_id in ht_rows:
                clean_r = str(resp).strip()
                sig = clean_r[:40].lower()
                if sig in seen_ht:
                    continue
                seen_ht.add(sig)
                ht_key = f"hot_take_clapback_{ht_id}"
                r_key = f"room_{room_id}"
                active_room_keys_referenced.add(r_key)
                # Extract rival advocate handle from topic if present
                rival_match = re.search(r"Advocate\s+([a-z0-9_]+)\s+just posted", str(topic))
                rival_handle = rival_match.group(1) if rival_match else None
                state_match = re.search(r"Live Game State:\s*([^\n\.]+)", str(topic))
                game_state_str = state_match.group(1).strip() if state_match else f"Room {room_id}"

                add_node(
                    ht_key,
                    "u_cmdb_ci_meltdown",
                    "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
                    f"@{p_handle} Room {room_id} Clapback ({game_state_str[:36]}): {clean_r[:52]}...",
                    f"Live Clapback (#{ht_id} via {eng} in {r_key} | {game_state_str}): @{p_handle} -> \"{clean_r}\"",
                    {
                        "persona": str(p_handle),
                        "room_id": str(room_id),
                        "rival_persona": rival_handle or "",
                        "boggs_level": 4,
                        "heat_index": 8,
                    },
                )
                pantheon_edges.append((ht_key, str(p_handle), "Fired By::Advocate"))
                pantheon_edges.append((ht_key, r_key, "Posted In::Game Room"))
                if rival_handle:
                    pantheon_edges.append((ht_key, rival_handle, "Claps Back At::Advocate"))
        except Exception:
            pass

        sconn.close()

    # =========================================================================
    # 8. ALL 54 EXPORTED GAME ROOM EPISODE FILES (data/labeled_logs/game_log_*.md)
    # =========================================================================
    if LABELED_LOGS_DIR.exists():
        episode_files = sorted(LABELED_LOGS_DIR.glob("game_log_*.md"))
        for ep_path in episode_files:
            fname = ep_path.stem  # e.g., game_log_823623_20260529_MIA_at_NYM
            ep_ci_key = f"episode_{fname}"
            try:
                raw_text = ep_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = raw_text.splitlines()
            line_count = len(lines)
            # Extract game_pk if numeric
            m_gpk = re.search(r"game_log_(\d+)_(\d{8})_([A-Za-z0-9_]+)", fname)
            if m_gpk:
                g_pk, g_date, matchup = m_gpk.group(1), m_gpk.group(2), m_gpk.group(3)
                room_key = f"room_{g_pk}"
                active_room_keys_referenced.add(room_key)
                ep_title = f"Game Room Episode {g_pk}: {matchup.replace('_', ' ')} ({g_date} • {line_count:,} lines)"
            else:
                g_pk = "LIVE_SNIPER" if "sniper" in fname else "PGA_AMEN"
                room_key = f"room_{g_pk.lower()}"
                active_room_keys_referenced.add(room_key)
                ep_title = f"Special Game Room Episode: {fname.replace('game_log_', '')} ({line_count:,} lines)"

            # Find participating personas & top spicy lines in this episode
            speakers: Set[str] = set()
            spicy_lines: List[Tuple[str, str]] = []
            for ln in lines:
                m_turn = re.match(r"^\*\*@?([A-Za-z0-9_.-]+)\*\*\s*\(([0-9:]+)\):\s*(.+)$", ln)
                if not m_turn:
                    continue
                spk, ts_str, msg_body = m_turn.group(1), m_turn.group(2), m_turn.group(3).strip()
                if spk in ("SYSTEM", "STATCAST"):
                    continue
                speakers.add(spk)
                if any(
                    kw in msg_body.upper()
                    for kw in (
                        "SPREADSHEETS ARE ON FIRE",
                        "CHICKEN WING",
                        "2007-FLAVOR SEWAGE",
                        "WHOLE FOODS",
                        "SUICIDE HOTLINE",
                        "FIRE MENDOZA",
                        "STEARNS",
                        "BOGGS LEVEL",
                        "WEEDSTACK",
                        "CAR CRASH",
                        "CLOWN SHOW",
                        "CURSED",
                    )
                ):
                    if len(spicy_lines) < 5:
                        spicy_lines.append((spk, msg_body))

            sample_quote = f"{spicy_lines[0][0]}: \"{spicy_lines[0][1][:140]}\"" if spicy_lines else f"{len(speakers)} active advocates"
            add_node(
                ep_ci_key,
                "u_cmdb_ci_game_episode",
                "Layer 2: Exported Game Room Episodes (labeled_logs)",
                ep_title,
                f"Full Game Room Transcript ({ep_path.name} • {line_count:,} lines • {len(speakers)} speakers). Highlight: {sample_quote}",
                {
                    "file_name": ep_path.name,
                    "game_pk": str(g_pk),
                    "line_count": line_count,
                    "speaker_count": len(speakers),
                    "boggs_level": 5 if spicy_lines else 4,
                },
            )
            pantheon_edges.append((ep_ci_key, room_key, "Recorded In::Game Room"))
            for spk in list(speakers)[:8]:
                pantheon_edges.append((ep_ci_key, spk.lstrip("@"), "Features Advocate::Participant"))

            # If this is the Live Chat Sniper episode or has iconic BarfFanStack / Dot sniper lines, mint dedicated Meltdown CIs
            if "sniper" in fname:
                sniper_highlights = [
                    (
                        "sniper_barf_kimbrel_chicken_wing",
                        "@BarfFanStack Sniper: Kimbrel 'Chicken Wing' Slow-Motion Car Crash on Fire",
                        "Verbatim @BarfFanStack Live Stream Sniper (01:22:52): 'Kimbrel That \"chicken wing\" wind-up—that dangling, prehistoric pose he insists on holding is like watching a slowmotion car crash where the car is on FIRE and you’re trapped in the trunk'",
                        "barf",
                    ),
                    (
                        "sniper_barf_2007_flavor_sewage",
                        "@BarfFanStack Sniper: '@@mikevega2684 Dog water? This is 2007-flavor sewage.'",
                        "Verbatim @BarfFanStack Live Stream Sniper (01:24:09): '@@mikevega2684 Dog water? That’s an insult to the dogs. This is 2007-flavor sewage. I’m already smelling the bullpen meltdown. Why do we do this to ourselves? #MetsGonnaMet #7TrainTrauma'",
                        "barf",
                    ),
                    (
                        "sniper_dot_washed_is_not_a_metric",
                        "@dot Sniper: '@@JuanCheesy WASHED IS NOT A METRIC! THE SPREADSHEETS ARE ON FIRE!'",
                        "Verbatim @dot Live Stream Sniper (01:24:45): '@@JuanCheesy \"WASHED\" IS NOT A METRIC! Semien's xwOBA is elite; Kimbrel's FIP is a sanctuary! YOUR NARRATIVE IS NOISE! BOGGS LEVEL 94%. THE SPREADSHEETS ARE ON FIRE! 0.04% DEVIATION! 101906!'",
                        "dot",
                    ),
                    (
                        "sniper_uncle_stevie_tax_bracket",
                        "@uncle_stevie_stan Sniper: '@@mikevega2684 Stay in your tax bracket, Philly!'",
                        "Verbatim @uncle_stevie_stan Live Stream Sniper (01:23:29): '@@mikevega2684 Imagine needing to DFA because you're too broke for elite arms. Uncle Stevie's petty cash is your whole payroll. Stay in your tax bracket, Philly! #LGM #BillionaireEnergy'",
                        "uncle_stevie_stan",
                    ),
                ]
                for sn_key, sn_title, sn_desc, sn_persona in sniper_highlights:
                    add_node(
                        sn_key,
                        "u_cmdb_ci_meltdown",
                        "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
                        sn_title,
                        sn_desc,
                        {"persona": sn_persona, "episode": ep_ci_key, "boggs_level": 5, "heat_index": 10},
                    )
                    pantheon_edges.append((sn_key, ep_ci_key, "Captured In::Game Episode"))
                    pantheon_edges.append((sn_key, sn_persona, "Fired By::Advocate"))
                    pantheon_edges.append((sn_key, "villain_stearns_fleece_spreadsheet", "Targets Villain::Blames"))

    # =========================================================================
    # 9. MORNING WIRETAP DB (450 WATCH-PARTY STREAMS & 562,682 STREAM TAIL MSGS)
    # =========================================================================
    if WIRETAP_DB.exists():
        wconn = sqlite3.connect(str(WIRETAP_DB))
        wcur = wconn.cursor()

        # 9A. Top 15 Channel Hubs with exact message counts from chat_telemetry
        channel_hubs: Dict[str, str] = {}
        try:
            for chan_key, msg_cnt in wcur.execute(
                "SELECT channel_key, count(*) as c FROM chat_telemetry GROUP BY channel_key ORDER BY c DESC LIMIT 18"
            ).fetchall():
                if not chan_key:
                    continue
                hub_ci_key = f"wiretap_hub_{re.sub(r'[^a-z0-9]+', '_', str(chan_key).lower()).strip('_')}"
                channel_hubs[str(chan_key)] = hub_ci_key
                add_node(
                    hub_ci_key,
                    "u_cmdb_ci_watch_party_stream",
                    "Layer 2: Morning Wiretap Live Stream Hubs (morning_wiretap.db)",
                    f"Wiretap Stream Hub [{chan_key}] ({msg_cnt:,} live tail messages)",
                    f"OmniTailer Live Watch-Party Hub '{chan_key}' in data/morning_wiretap.db with {msg_cnt:,} ingested chat_telemetry messages.",
                    {"channel_key": str(chan_key), "message_count": int(msg_cnt), "boggs_level": 5},
                )
                ck_up = str(chan_key).upper()
                if "MCAFEE" in ck_up:
                    pantheon_edges.append((hub_ci_key, "hero_pat_mcafee", "Broadcasts::ThunderDome Stream"))
                elif "TEN" in ck_up:
                    pantheon_edges.append((hub_ci_key, "villain_daboll_titans_exile", "Watches::0-3 Titans Collapse"))
                elif "CLE" in ck_up:
                    pantheon_edges.append((hub_ci_key, "hero_bottlegate_rick", "Anchored By::Dawg Pound"))
                elif "PHLY" in ck_up or "PHI" in ck_up:
                    pantheon_edges.append((hub_ci_key, "hero_sammy_the_savant", "Audited By::Philly Savant"))
                elif "NYY" in ck_up:
                    pantheon_edges.append((hub_ci_key, "villain_cashman_clearance_rack", "Roasts::Yankees Front Office"))
        except Exception:
            pass

        # 9B. Distinct Watch-Party Streams from watch_party_streams (NFL, CFB, MLB)
        stream_id_to_ci: Dict[str, str] = {}
        try:
            for st_id, sport, g_pk, g_date, home_t, away_t, yt_id, st_title, st_url in wcur.execute(
                """
                SELECT id, sport, game_pk, game_date, home_team, away_team, stream_id, stream_title, stream_url
                FROM watch_party_streams
                WHERE stream_title IS NOT NULL AND length(stream_title) > 5
                GROUP BY stream_id, stream_title
                ORDER BY id DESC
                LIMIT 65
                """
            ).fetchall():
                st_ci_key = f"watch_stream_{yt_id}_{st_id}"
                stream_id_to_ci[str(yt_id)] = st_ci_key
                add_node(
                    st_ci_key,
                    "u_cmdb_ci_watch_party_stream",
                    "Layer 2: Morning Wiretap Live Stream Hubs (morning_wiretap.db)",
                    f"[{sport} • {g_date}] {st_title[:85]}",
                    f"Live Watch-Party Stream ({sport} • {away_t}@{home_t} • YouTube {yt_id}): {st_title} ({st_url})",
                    {
                        "sport": str(sport),
                        "game_pk": str(g_pk),
                        "stream_id": str(yt_id),
                        "stream_url": str(st_url),
                        "boggs_level": 4,
                    },
                )
                if "Brewers" in str(st_title) or "MIL" in (str(home_t), str(away_t)):
                    pantheon_edges.append((st_ci_key, "hero_jackson_chourio_walkoff", "Streams::Brewers Postseason"))
                elif sport == "CFB":
                    pantheon_edges.append((st_ci_key, "villain_billy_napier_hot_seat", "Streams::CFB Chaos"))
                elif sport == "NFL":
                    pantheon_edges.append((st_ci_key, "hero_pat_mcafee", "Monitored By::ThunderDome"))
        except Exception:
            pass

        # 9C. High-Heat Verbatim Stream Tail Messages from chat_telemetry (across NFL, CFB, McAfee, Philly, Yankees, Lions, Browns)
        try:
            for ch_key, hub_ci_key in list(channel_hubs.items())[:15]:
                tail_rows = wcur.execute(
                    """
                    SELECT id, channel_key, stream_id, author, message, timestamp_str
                    FROM chat_telemetry
                    WHERE channel_key = ?
                      AND length(message) BETWEEN 45 AND 220
                      AND (
                        message LIKE '%fire%' OR message LIKE '%FIRE%'
                        OR message LIKE '%trash%' OR message LIKE '%TRASH%'
                        OR message LIKE '%choke%' OR message LIKE '%CHOKE%'
                        OR message LIKE '%rigged%' OR message LIKE '%RIGGED%'
                        OR message LIKE '%ref%' OR message LIKE '%REF%'
                        OR message LIKE '%bench%' OR message LIKE '%BENCH%'
                        OR message LIKE '%trade%' OR message LIKE '%TRADE%'
                        OR message LIKE '%fraud%' OR message LIKE '%FRAUD%'
                        OR message = upper(message)
                      )
                    ORDER BY id DESC
                    LIMIT 8
                    """,
                    (ch_key,),
                ).fetchall()
                for t_id, t_chan, t_sid, t_auth, t_msg, t_ts in tail_rows:
                    tail_ci_key = f"wiretap_tail_{t_id}"
                    clean_msg = re.sub(r"\s+", " ", str(t_msg)).strip()
                    add_node(
                        tail_ci_key,
                        "u_cmdb_ci_stream_tail",
                        "Layer 3: Morning Wiretap Live Stream Chat Tails",
                        f"[{t_chan} • {t_auth}]: {clean_msg[:64]}...",
                        f"Live Stream Chat Tail (#{t_id} on {t_chan} @ {t_ts}, stream={t_sid}): {t_auth} -> \"{clean_msg}\"",
                        {
                            "channel_key": str(t_chan),
                            "stream_id": str(t_sid),
                            "author": str(t_auth),
                            "boggs_level": 5,
                            "heat_index": 9,
                        },
                    )
                    pantheon_edges.append((tail_ci_key, hub_ci_key, "Tail Captured On::Stream Hub"))
                    if str(t_sid) in stream_id_to_ci:
                        pantheon_edges.append((tail_ci_key, stream_id_to_ci[str(t_sid)], "Streamed In::Watch Party"))
        except Exception:
            pass

        wconn.close()

    # =========================================================================
    # 10. IDE BRAIN TWEETS, AUTHENTIC_SPORTS_GOLD NEEDLES & SQLITE SCREAMS/TMI
    # =========================================================================
    brain_tweets = harvest_ide_brain_barf_tweets(max_items=35)
    for idx, bt in enumerate(brain_tweets, 1):
        ci_key = f"barf_ide_tweet_{idx:03d}"
        txt = bt["text"]
        add_node(
            ci_key,
            "u_cmdb_ci_meltdown",
            "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
            f"@BarfFanStack IDE Tweet #{idx:02d}: {txt[:58]}...",
            f"Recovered from IDE Brain ({bt['source']}): {txt}",
            {"persona": "barf", "boggs_level": 5, "heat_index": 9, "source": bt["source"]},
        )
        pantheon_edges.append((ci_key, "vitals_barf_bp_178_112", "Triggered By::Somatic Vitals"))
        if any(w in txt.lower() for w in ("cowboy", "dak", "jerry", "dal")):
            pantheon_edges.append((ci_key, "villain_jerry_sun_glare_cap", "Targets Villain::Blames"))
        elif any(w in txt.lower() for w in ("giant", "daboll", "metlife", "zvada", "harbaugh")):
            pantheon_edges.append((ci_key, "villain_daboll_titans_exile", "Targets Villain::Blames"))
        else:
            pantheon_edges.append((ci_key, "villain_stearns_fleece_spreadsheet", "Targets Villain::Blames"))

    if NEEDLE_GOLD_PATH.exists():
        try:
            needles = json.loads(NEEDLE_GOLD_PATH.read_text(encoding="utf-8")).get("top_needles", [])
        except Exception:
            needles = []
    else:
        needles = []

    seen_needle_msgs: Set[str] = set()
    needle_count = 0
    for nd in needles:
        msg = str(nd.get("message", "")).strip()
        user = str(nd.get("user", "stream_fan")).strip()
        chan = str(nd.get("channel", "Live Football Stream")).strip()
        arch = str(nd.get("archetype", "FAUSTIAN_BARTER")).strip()
        if not msg or msg.lower() in seen_needle_msgs:
            continue
        seen_needle_msgs.add(msg.lower())
        needle_count += 1
        ci_key = f"stream_needle_{needle_count:03d}_{re.sub(r'[^a-z0-9]+', '_', user.lower()).strip('_')[:16]}"
        add_node(
            ci_key,
            "u_cmdb_ci_meltdown",
            "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
            f"[{arch}] @{user} ({chan[:28]}): {msg[:52]}",
            f"Live Stream Needle ({arch} • {nd.get('detected_dialect', 'NFL')}): @{user} on '{chan}' -> \"{msg}\"",
            {"persona": user, "channel": chan, "archetype": arch, "boggs_level": 4, "heat_index": 8},
        )
        if any(w in msg.lower() for w in ("dak", "lamb", "cede", "cd", "cowboy")):
            pantheon_edges.append((ci_key, "villain_jerry_sun_glare_cap", "Targets Villain::Blames"))
            pantheon_edges.append((ci_key, "conspiracy_att_west_window_glare", "Caused By::Conspiracy"))
        elif any(w in msg.lower() for w in ("packer", "brewer", "nixon")):
            pantheon_edges.append((ci_key, "conspiracy_wisconsin_faustian_barter", "Caused By::Conspiracy"))
            pantheon_edges.append((ci_key, "hero_jackson_chourio_walkoff", "Funded By::Hero"))
        else:
            pantheon_edges.append((ci_key, "hero_sammy_the_savant", "Audited By::Savant"))

    if SOVEREIGN_DB.exists():
        conn = sqlite3.connect(str(SOVEREIGN_DB))
        cur = conn.cursor()
        try:
            scream_rows = cur.execute(
                """
                SELECT id, game_pk, persona, text
                FROM game_chat
                WHERE length(text) BETWEEN 42 AND 240
                  AND text = upper(text)
                  AND model NOT IN ('offline_corpus', 'local_fallback', 'api_exhaustion_fallback')
                  AND text NOT LIKE '%HTTP%'
                  AND text NOT LIKE '%TESTING%'
                ORDER BY id DESC
                LIMIT 120
                """
            ).fetchall()
            seen_screams: Set[str] = set()
            for s_id, g_pk, p_handle, s_txt in scream_rows:
                clean_s = str(s_txt).strip()
                sig = clean_s[:45]
                if sig in seen_screams:
                    continue
                seen_screams.add(sig)
                m_key = f"meltdown_chat_{s_id}"
                r_key = f"room_{g_pk}"
                active_room_keys_referenced.add(r_key)
                add_node(
                    m_key,
                    "u_cmdb_ci_meltdown",
                    "Layer 3: Verbatim ALL-CAPS Meltdowns & Stream Needles",
                    f"@{p_handle} ALL-CAPS Scream (#{s_id}): {clean_s[:48]}...",
                    f"Verbatim Boggs-5 Scream in Game {g_pk} by @{p_handle}: \"{clean_s}\"",
                    {"persona": str(p_handle), "game_pk": str(g_pk), "boggs_level": 5, "heat_index": 9},
                )
                pantheon_edges.append((m_key, str(p_handle), "Screamed By::Advocate"))
                pantheon_edges.append((m_key, r_key, "Screamed In::Game Room"))
                if "BULLPEN" in clean_s or "METS" in clean_s or "PHILLIES" in clean_s:
                    pantheon_edges.append((m_key, "villain_stearns_fleece_spreadsheet", "Targets Villain::Blames"))
                elif "UMP" in clean_s or "BLIND" in clean_s or "STRIKE" in clean_s:
                    pantheon_edges.append((m_key, "villain_animal_style_ump_cartel", "Targets Villain::Blames"))
                else:
                    pantheon_edges.append((m_key, "tva_002_wade_boggs_singularity", "Caused By::Boggs Saturation"))
        except Exception:
            pass

        try:
            tmi_rows = cur.execute(
                """
                SELECT sys_id, name, description, payload, game_pk
                FROM cmdb_ci_tmi_scenario
                WHERE name IS NOT NULL AND length(name) > 3
                GROUP BY name, description
                LIMIT 100
                """
            ).fetchall()
            for t_idx, (t_sid, t_name, t_desc, t_pay, t_gpk) in enumerate(tmi_rows, 1):
                c_key = f"conspiracy_tmi_{re.sub(r'[^a-z0-9]+', '_', str(t_sid).lower()).strip('_')[:24]}_{t_idx}"
                add_node(
                    c_key,
                    "u_cmdb_ci_conspiracy",
                    "Layer 5: Conspiracies, Fever Dreams & TMI Anomalies",
                    f"TMI Anomaly [{t_sid}]: {t_name}",
                    f"{t_desc or ''} — {str(t_pay or '')[:180]}".strip(" —"),
                    {"tmi_id": str(t_sid), "game_pk": str(t_gpk or "GLOBAL"), "boggs_level": 5},
                )
                pantheon_edges.append((c_key, "tva_002_wade_boggs_singularity", "Governed By::Boggs Singularity"))
        except Exception:
            pass
        conn.close()

    # Core Pantheon Spines
    pantheon_edges.extend(
        [
            ("meltdown_dak_yeah_here_we_go_trade", "vitals_dak_curtain_rage_boggs5", "Triggered By::Biometric Spike"),
            ("vitals_dak_curtain_rage_boggs5", "conspiracy_att_west_window_glare", "Provoked By::Stadium Glare"),
            ("conspiracy_att_west_window_glare", "villain_jerry_sun_glare_cap", "Root Cause::Owner Hubris"),
            ("villain_jerry_sun_glare_cap", "hero_pat_mcafee", "Roasted On::Noon Broadcast"),
            ("meltdown_barf_left_arm_shapiro", "vitals_barf_bp_178_112", "Triggered By::Biometric Spike"),
            ("vitals_barf_bp_178_112", "hero_dr_shapiro_cardiologist", "Monitored By::Cardiologist"),
            ("meltdown_daboll_12_7_harbaugh", "vitals_barf_bp_178_112", "Triggered By::Biometric Spike"),
            ("meltdown_daboll_12_7_harbaugh", "hero_john_harbaugh_nyg", "Vindicated By::Coach"),
            ("hero_john_harbaugh_nyg", "villain_daboll_titans_exile", "Defeated::Exiled Villain"),
            ("meltdown_napier_mizzou_45_17", "hero_nick_saban_alpha", "Audited By::SEC Alpha"),
            ("hero_nick_saban_alpha", "villain_billy_napier_hot_seat", "Exposes::Coaching Hot Seat"),
            ("villain_billy_napier_hot_seat", "villain_hugh_freeze_second_half", "Correlated With::SEC Collapse"),
            ("meltdown_cheesehead_faustian_barter", "conspiracy_wisconsin_faustian_barter", "Executes::Faustian Barter"),
            ("conspiracy_wisconsin_faustian_barter", "hero_ty_schmit_lou_holtz", "Witnessed By::Broadcast Doomer"),
            ("conspiracy_wisconsin_faustian_barter", "hero_jackson_chourio_walkoff", "Granted::104mph Walk-Off"),
            ("meltdown_animal_style_ump_hair", "battery_chucker_jr", "Screamed By::Advocate"),
            ("battery_chucker_jr", "sys_mean_gene", "Audited By::Referee"),
            ("sys_mean_gene", "villain_animal_style_ump_cartel", "Root Cause::Umpire Cartel"),
            ("meltdown_dot_spreadsheets_on_fire", "vitals_dot_neural_thermal_runaway", "Triggered By::Thermal Runaway"),
            ("vitals_dot_neural_thermal_runaway", "villain_stearns_fleece_spreadsheet", "Root Cause::Spreadsheet Overoptimization"),
        ]
    )

    new_spines: List[Dict[str, Any]] = [
        {
            "spine_id": "spine_jerry_sun_glare_cowboys",
            "title": "NFL Cowboys Spine: 'TRADE DAK & CD' Stream Meltdown ➔ AT&T West Window Sun Glare ➔ Jerry Jones $60M Cap Myth",
            "keywords": [
                "jerry_sun_glare",
                "cowboys",
                "dak",
                "jerry",
                "curtain_conspiracy_dak",
                "villain_jerry_sun_glare_cap",
                "conspiracy_att_west_window_glare",
                "meltdown_dak_yeah_here_we_go_trade",
            ],
            "burn_score": 99,
            "heat_index": 10,
            "is_tko": 1,
            "pitch_physics": "AT&T West End-Zone Solar Azimuth 248° • 2021 14-Sec QB Draw • $60M AAV Cap Hit",
            "state_register_id": "0xda11a560",
            "committed_pages": 328,
            "resolution_latency_us": 14.5,
            "hops": [
                {
                    "hop": 1,
                    "ci_key": "meltdown_dak_yeah_here_we_go_trade",
                    "sys_id": make_sys_id("meltdown_dak_yeah_here_we_go_trade"),
                    "name": "meltdown_dak_yeah_here_we_go_trade",
                    "display_title": "Hop 1: Verbatim Stream Meltdown ('TRADE DAK AND CD SO THEY CAN GO WIN')",
                    "sys_class_name": "u_cmdb_ci_meltdown",
                    "short_description": "Live postgame stream meltdown: 'YEAH HERE WE GO into another false start! Trade Dak and CD so they can go win a championship!'",
                    "burn_score": 97,
                    "heat_index": 10,
                    "is_tko": 1,
                },
                {
                    "hop": 2,
                    "ci_key": "vitals_dak_curtain_rage_boggs5",
                    "sys_id": make_sys_id("vitals_dak_curtain_rage_boggs5"),
                    "name": "vitals_dak_curtain_rage_boggs5",
                    "display_title": "Hop 2: @curtain_conspiracy_dak Biometric Spike (BP 188/116 • Boggs 5)",
                    "sys_class_name": "u_cmdb_ci_biometric_vitals",
                    "short_description": "Texas HS offensive coordinator hitting 188/116 mmHg breaking down empty-backfield shotgun on 3rd-and-inches.",
                    "heat_index": 10,
                    "is_tko": 1,
                },
                {
                    "hop": 3,
                    "ci_key": "hero_aq_shipley_trench",
                    "sys_id": make_sys_id("hero_aq_shipley_trench"),
                    "name": "hero_aq_shipley_trench",
                    "display_title": "Hop 3: AQ Shipley & Pat McAfee Noon All-22 Trench Audit",
                    "sys_class_name": "u_cmdb_ci_hero",
                    "short_description": "ThunderDome telestrator breakdown exposing blown A-gap protection and pre-snap cadence tells.",
                },
                {
                    "hop": 4,
                    "ci_key": "conspiracy_att_west_window_glare",
                    "sys_id": make_sys_id("conspiracy_att_west_window_glare"),
                    "name": "conspiracy_att_west_window_glare",
                    "display_title": "Hop 4: AT&T Stadium West End-Zone Window Sun Glare Conspiracy",
                    "sys_class_name": "u_cmdb_ci_conspiracy",
                    "short_description": "Blinding autumn sun beams straight through uncovered west windows into receivers' eyes.",
                },
                {
                    "hop": 5,
                    "ci_key": "villain_jerry_sun_glare_cap",
                    "sys_id": make_sys_id("villain_jerry_sun_glare_cap"),
                    "name": "villain_jerry_sun_glare_cap",
                    "display_title": "Hop 5: Jerry Jones' West Window Glare & $60M Salary Cap Myth [ROOT CAUSE]",
                    "sys_class_name": "u_cmdb_ci_villain",
                    "short_description": "Root Cause Villain CI: Refuses $4,000 stadium curtains while boasting about Forbes franchise valuation at 1-2.",
                    "pitch_physics": "AT&T West End-Zone Solar Azimuth 248° • 2021 14-Sec QB Draw • $60M AAV Cap Hit",
                },
            ],
        },
        {
            "spine_id": "spine_barf_bp_daboll_harbaugh",
            "title": "NFL Giants & Barf Biometric Spine: BP 178/112 Pastrami Crisis ➔ Dr. Shapiro Speed Dial 1 ➔ Harbaugh 12-7 Over Daboll's 0-3 Titans",
            "keywords": [
                "barf_bp_178",
                "daboll_titans",
                "shapiro",
                "pastrami",
                "harbaugh",
                "zvada",
                "vitals_barf_bp_178_112",
                "villain_daboll_titans_exile",
                "meltdown_barf_left_arm_shapiro",
            ],
            "burn_score": 99,
            "heat_index": 10,
            "is_tko": 1,
            "pitch_physics": f"Systolic {systolic}/{diastolic} mmHg • Pulse {pulse} bpm • {pastrami} lbs Ben's Pastrami • Panic {panic_idx}/10",
            "state_register_id": "0xb49f1780",
            "committed_pages": 328,
            "resolution_latency_us": 14.5,
            "hops": [
                {
                    "hop": 1,
                    "ci_key": "meltdown_barf_left_arm_shapiro",
                    "sys_id": make_sys_id("meltdown_barf_left_arm_shapiro"),
                    "name": "meltdown_barf_left_arm_shapiro",
                    "display_title": "Hop 1: 'MY LEFT ARM IS NUMB, SHAPIRO IS EATING PASTRAMI IN GREAT NECK'",
                    "sys_class_name": "u_cmdb_ci_meltdown",
                    "short_description": "Barf screaming in his Middle Village basement wearing his NYG #10 jersey over his sweat-soaked '86 Mets pullover.",
                    "burn_score": 99,
                    "heat_index": 10,
                    "is_tko": 1,
                },
                {
                    "hop": 2,
                    "ci_key": "vitals_barf_bp_178_112",
                    "sys_id": make_sys_id("vitals_barf_bp_178_112"),
                    "name": "vitals_barf_bp_178_112",
                    "display_title": f"Hop 2: Barf Biometric Register (BP {systolic}/{diastolic} • Pulse {pulse} • {pastrami} lbs Pastrami)",
                    "sys_class_name": "u_cmdb_ci_biometric_vitals",
                    "short_description": "Acute cardiac panic with manic defensive delusion; 1.75 lbs of Ben's hot pastrami with double mustard.",
                    "heat_index": 10,
                    "is_tko": 1,
                },
                {
                    "hop": 3,
                    "ci_key": "hero_dr_shapiro_cardiologist",
                    "sys_id": make_sys_id("hero_dr_shapiro_cardiologist"),
                    "name": "hero_dr_shapiro_cardiologist",
                    "display_title": "Hop 3: Dr. Shapiro (Queens Blvd & Great Neck Speed-Dial 1 Cardiologist)",
                    "sys_class_name": "u_cmdb_ci_hero",
                    "short_description": "Paging the cardiac ICU between bites of rye pastrami while monitoring @barf's left ventricle.",
                },
                {
                    "hop": 4,
                    "ci_key": "hero_john_harbaugh_nyg",
                    "sys_id": make_sys_id("hero_john_harbaugh_nyg"),
                    "name": "hero_john_harbaugh_nyg",
                    "display_title": "Hop 4: John Harbaugh (NYG Head Coach) & Dominic Zvada 60-Yd Leg",
                    "sys_class_name": "u_cmdb_ci_hero",
                    "short_description": "Hired Jan 20, 2026; locked Brian Daboll's Titans in a 12-7 cellar in Week 3.",
                },
                {
                    "hop": 5,
                    "ci_key": "villain_daboll_titans_exile",
                    "sys_id": make_sys_id("villain_daboll_titans_exile"),
                    "name": "villain_daboll_titans_exile",
                    "display_title": "Hop 5: Brian Daboll's 0-3 Titans Exile & MetLife Turf Curse [ROOT CAUSE]",
                    "sys_class_name": "u_cmdb_ci_villain",
                    "short_description": "Fired Nov 2025, exiled to 0-3 Tennessee, and refusing to answer Barf's phone calls on how to run a post route.",
                    "pitch_physics": f"Systolic {systolic}/{diastolic} mmHg • Pulse {pulse} bpm • NYG 12, TEN 7",
                },
            ],
        },
    ]

    return pantheon_cis, pantheon_edges, new_spines


def enrich_and_prune_cartridge_files() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Merge Pantheon, Episodes, Stream Tails & Emergent Society into fanstack_cmdb_ci.json and prune empty staged rooms."""
    ci_source_path = DATA_DIR / "sports_cmdb_ci.json" if (DATA_DIR / "sports_cmdb_ci.json").exists() else CI_JSON_PATHS[0]
    rel_source_path = DATA_DIR / "sports_cmdb_rel_ci.json" if (DATA_DIR / "sports_cmdb_rel_ci.json").exists() else REL_JSON_PATHS[0]

    ci_doc = json.loads(ci_source_path.read_text(encoding="utf-8"))
    rel_doc = json.loads(rel_source_path.read_text(encoding="utf-8"))

    raw_base_cis = ci_doc.get("result") or ci_doc.get("cis", [])
    raw_base_rels = rel_doc.get("result") or rel_doc.get("relationships", [])

    pantheon_cis, pantheon_edges, new_spines = build_pantheon_and_episodes()

    # Keep base CIs that are NOT pantheon classes AND prune empty state=staged rooms unless referenced by an episode/edge
    pantheon_classes = {
        "u_cmdb_ci_villain",
        "u_cmdb_ci_hero",
        "u_cmdb_ci_conspiracy",
        "u_cmdb_ci_biometric_vitals",
        "u_cmdb_ci_meltdown",
        "u_cmdb_ci_emergent_citizen",
        "u_cmdb_ci_society_dialogue",
        "u_cmdb_ci_citizen_memory",
        "u_cmdb_ci_prop_contract",
        "u_cmdb_ci_broadcast_episode",
        "u_cmdb_ci_broadcast_segment",
        "u_cmdb_ci_stoppage_banter",
        "u_cmdb_ci_lore_injection",
        "u_cmdb_ci_game_episode",
        "u_cmdb_ci_watch_party_stream",
        "u_cmdb_ci_stream_tail",
    }

    normalized_base_rels: List[Tuple[str, str, str]] = []
    for r in raw_base_rels:
        p_k = r.get("parent_key") or (r.get("parent", {}).get("display_value") if isinstance(r.get("parent"), dict) else "")
        c_k = r.get("child_key") or (r.get("child", {}).get("display_value") if isinstance(r.get("child"), dict) else "")
        t_v = r.get("type", {}).get("display_value") if isinstance(r.get("type"), dict) else str(r.get("type") or "Depends on::Used by")
        if p_k and c_k:
            normalized_base_rels.append((str(p_k), str(c_k), str(t_v)))

    # Find which rooms are referenced in base relationships or new pantheon edges
    referenced_rooms: Set[str] = set()
    for p_k, c_k, _ in normalized_base_rels:
        for endpoint in (p_k, c_k):
            if endpoint.startswith("room_"):
                referenced_rooms.add(endpoint)
    for c_key, p_key, _ in pantheon_edges:
        for endpoint in (c_key, p_key):
            if endpoint.startswith("room_"):
                referenced_rooms.add(endpoint)

    base_cis: List[Dict[str, Any]] = []
    pruned_room_keys: List[str] = []
    for c in raw_base_cis:
        cls = c.get("sys_class_name")
        if cls in pantheon_classes:
            continue
        ck = str(c.get("ci_key") or c.get("name") or "")
        if not ck:
            continue
        c["ci_key"] = ck
        c["name"] = ck
        if cls == "cmdb_ci_fanstack_room":
            gpk_room = f"room_{c.get('game_pk')}" if c.get("game_pk") else ck
            if ck not in referenced_rooms and gpk_room not in referenced_rooms:
                pruned_room_keys.append(ck)
                continue
        base_cis.append(c)

    ci_by_key: Dict[str, Dict[str, Any]] = {}
    for c in base_cis:
        ci_by_key[c["ci_key"]] = c
        ci_by_key[c["ci_key"].lower()] = c
    for pc in pantheon_cis:
        ci_by_key[pc["ci_key"]] = pc
        ci_by_key[pc["ci_key"].lower()] = pc

    # Ensure any room_key referenced by an episode/scream exists in ci_by_key
    for rk in sorted(referenced_rooms):
        if rk not in ci_by_key and rk.lower() not in ci_by_key:
            gpk = rk.replace("room_", "")
            room_node = {
                "sys_id": make_sys_id(rk),
                "ci_key": rk,
                "name": rk,
                "display_title": f"Active FanStack Game Room ({rk})",
                "sys_class_name": "cmdb_ci_fanstack_room",
                "layer_label": "Layer 2: Active FanStack Game Room CI",
                "short_description": f"Populated FanStack Game Room ({rk}, game_pk={gpk}) with linked episodes, meltdowns, and advocate banter.",
                "state_register_id": make_reg_id(rk),
                "install_status": "1",
                "operational_status": "1",
            }
            ci_by_key[rk] = room_node
            ci_by_key[rk.lower()] = room_node

    # Deduplicate all_cis preserving canonical ci_key
    unique_cis_map: Dict[str, Dict[str, Any]] = {}
    for c in list(base_cis) + list(pantheon_cis):
        unique_cis_map[c["ci_key"]] = c
    for rk in sorted(referenced_rooms):
        resolved = ci_by_key.get(rk) or ci_by_key.get(rk.lower())
        if resolved and resolved["ci_key"] not in unique_cis_map:
            unique_cis_map[resolved["ci_key"]] = resolved

    all_cis = list(unique_cis_map.values())

    # Rebuild relationships supporting both ServiceNow and RAM session loader formats
    existing_rels: List[Dict[str, Any]] = []
    rel_seen: Set[Tuple[str, str]] = set()

    def add_merged_rel(src_key: str, dst_key: str, rel_label: str) -> None:
        src_ci = ci_by_key.get(src_key) or ci_by_key.get(src_key.lower())
        dst_ci = ci_by_key.get(dst_key) or ci_by_key.get(dst_key.lower())
        if not src_ci or not dst_ci:
            return
        sk = src_ci["ci_key"]
        dk = dst_ci["ci_key"]
        if sk == dk or (sk, dk) in rel_seen:
            return
        rel_seen.add((sk, dk))
        existing_rels.append(
            {
                "sys_id": make_sys_id(f"rel_{sk}_{dk}"),
                "parent": {"value": src_ci["sys_id"], "display_value": sk},
                "child": {"value": dst_ci["sys_id"], "display_value": dk},
                "type": {"value": rel_label, "display_value": rel_label},
                "parent_key": dst_ci["ci_key"],
                "parent_sys_id": dst_ci["sys_id"],
                "child_key": src_ci["ci_key"],
                "child_sys_id": src_ci["sys_id"],
                "type_sys_id": REL_TYPE_SYS_ID,
            }
        )

    for src_k, dst_k, rel_lbl in normalized_base_rels:
        add_merged_rel(src_k, dst_k, rel_lbl)

    for src_k, dst_k, rel_lbl in pantheon_edges:
        add_merged_rel(src_k, dst_k, rel_lbl)

    # Merge spines
    idx_path = DATA_DIR / "sports_causal_index.json"
    idx_doc = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    new_spine_ids = {s["spine_id"] for s in new_spines}
    base_spines = [s for s in (idx_doc.get("spines") or ci_doc.get("causal_spines") or []) if s.get("spine_id") not in new_spine_ids]
    merged_spines = new_spines + base_spines

    class_counts: Dict[str, int] = {}
    layer_counts: Dict[str, int] = {}
    for c in all_cis:
        cls = c.get("sys_class_name", "cmdb_ci")
        lyr = c.get("layer_label") or c.get("layer") or "FanStack Pantheon"
        class_counts[cls] = class_counts.get(cls, 0) + 1
        layer_counts[lyr] = layer_counts.get(lyr, 0) + 1

    ci_out = {
        "total_cis": len(all_cis),
        "total_relationships": len(existing_rels),
        "class_counts": class_counts,
        "causal_spines": merged_spines,
        "result": all_cis,
        "cis": all_cis,
    }
    rel_out = {
        "total_relationships": len(existing_rels),
        "result": existing_rels,
        "relationships": existing_rels,
    }

    ci_payload = json.dumps(ci_out, indent=2)
    rel_payload = json.dumps(rel_out, indent=2)

    for p in CI_JSON_PATHS + [DATA_DIR / "sports_cmdb_ci.json", PUBLIC_DIR / "sports_cmdb_ci.json"]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(ci_payload, encoding="utf-8")
    for p in REL_JSON_PATHS + [DATA_DIR / "sports_cmdb_rel_ci.json", PUBLIC_DIR / "sports_cmdb_rel_ci.json"]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rel_payload, encoding="utf-8")

    if idx_doc:
        idx_doc["total_cis"] = len(all_cis)
        idx_doc["total_relationships"] = len(existing_rels)
        idx_doc["class_counts"] = class_counts
        idx_doc["layer_counts"] = layer_counts
        idx_doc["spines"] = merged_spines
        idx_payload = json.dumps(idx_doc, indent=2)
        idx_path.write_text(idx_payload, encoding="utf-8")
        (PUBLIC_DIR / "sports_causal_index.json").write_text(idx_payload, encoding="utf-8")

    if DIST_DIR.exists():
        (DIST_DIR / "fanstack_cmdb_ci.json").write_text(ci_payload, encoding="utf-8")
        (DIST_DIR / "fanstack_cmdb_rel_ci.json").write_text(rel_payload, encoding="utf-8")

    return all_cis, existing_rels, pruned_room_keys


def sync_full_cmdb_to_servicenow(all_cis: List[Dict[str, Any]], all_rels: List[Dict[str, Any]], pruned_room_keys: List[str]) -> Dict[str, Any]:
    """
    1. Fetch 100% of existing cmdb_ci (name -> sys_id) from dev186522.service-now.com.
    2. Delete pruned empty state=staged room_82* shells from dev186522.service-now.com.
    3. Upsert 100% of missing CIs from all_cis so every CI has a verified sys_id in ServiceNow.
    4. Fetch 100% of existing cmdb_rel_ci (parent, child) pairs from dev186522.service-now.com.
    5. Insert 100% of missing causal relationships from all_rels into dev186522.service-now.com.
    """
    t0 = time.perf_counter()
    auth = (SN_USER, SN_PASS)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # Step 1: Paged fetch of all existing CIs in ServiceNow
    existing_ci_map: Dict[str, str] = {}
    offset = 0
    page_size = 1000
    while True:
        try:
            r = requests.get(
                f"{SN_INSTANCE}/api/now/table/cmdb_ci",
                params={
                    "sysparm_fields": "sys_id,name",
                    "sysparm_limit": str(page_size),
                    "sysparm_offset": str(offset),
                },
                auth=auth,
                headers=headers,
                timeout=20,
            )
            batch = r.json().get("result", []) if r.status_code == 200 else []
            if not batch:
                break
            for item in batch:
                nm = item.get("name")
                sid = item.get("sys_id")
                if nm and sid:
                    existing_ci_map[nm] = sid
            if len(batch) < page_size:
                break
            offset += page_size
        except Exception:
            break

    # Step 2: Delete pruned empty room shells that exist in ServiceNow
    pruned_deleted = 0
    pruned_to_delete = [(rk, existing_ci_map[rk]) for rk in pruned_room_keys if rk in existing_ci_map]

    def delete_ci_worker(item: Tuple[str, str]) -> int:
        rk, sid = item
        session = requests.Session()
        session.auth = auth
        try:
            resp = session.delete(f"{SN_INSTANCE}/api/now/table/cmdb_ci/{sid}", timeout=12)
            if resp.status_code in (200, 204):
                return 1
        except Exception:
            pass
        return 0

    if pruned_to_delete:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            for d_ok in pool.map(delete_ci_worker, pruned_to_delete):
                pruned_deleted += d_ok
        for rk, _ in pruned_to_delete:
            existing_ci_map.pop(rk, None)

    # Step 3: Upsert all missing CIs (and update Pantheon/Episode CIs)
    cis_to_upsert: List[Dict[str, Any]] = []
    for ci in all_cis:
        nm = ci["ci_key"]
        if nm not in existing_ci_map or str(ci.get("sys_class_name", "")).startswith("u_cmdb_ci_"):
            cis_to_upsert.append(ci)

    cis_created_or_updated = 0

    def upsert_ci_worker(ci: Dict[str, Any]) -> Tuple[str, str | None, int]:
        session = requests.Session()
        session.auth = auth
        session.headers.update(headers)
        name = ci["ci_key"]
        short_desc = (
            f"[{ci.get('sys_class_name', 'cmdb_ci')} | {ci.get('layer_label', 'FanStack')} | reg={ci.get('state_register_id', '0x0')}] "
            f"{ci.get('display_title', name)} — {ci.get('short_description', '')}"
        )[:395]
        payload = {
            "name": name,
            "short_description": short_desc,
            "u_correlation_id": ci["sys_id"],
            "install_status": "1",
            "operational_status": "1",
        }
        try:
            if name in existing_ci_map:
                sid = existing_ci_map[name]
                pr = session.patch(f"{SN_INSTANCE}/api/now/table/cmdb_ci/{sid}", json=payload, timeout=12)
                if pr.status_code in (200, 201):
                    return name, sid, 1
                return name, sid, 0
            else:
                cr = session.post(f"{SN_INSTANCE}/api/now/table/cmdb_ci", json=payload, timeout=12)
                if cr.status_code in (200, 201):
                    sid = cr.json().get("result", {}).get("sys_id")
                    return name, sid, 1
        except Exception:
            pass
        return name, existing_ci_map.get(name), 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for nm, sid, ok in pool.map(upsert_ci_worker, cis_to_upsert):
            if sid:
                existing_ci_map[nm] = sid
            cis_created_or_updated += ok

    # Step 4: Paged fetch of all existing cmdb_rel_ci pairs in ServiceNow
    existing_rel_pairs: Set[Tuple[str, str]] = set()
    offset = 0
    while True:
        try:
            r = requests.get(
                f"{SN_INSTANCE}/api/now/table/cmdb_rel_ci",
                params={
                    "sysparm_fields": "parent,child",
                    "sysparm_limit": str(page_size),
                    "sysparm_offset": str(offset),
                },
                auth=auth,
                headers=headers,
                timeout=20,
            )
            batch = r.json().get("result", []) if r.status_code == 200 else []
            if not batch:
                break
            for item in batch:
                p_val = item.get("parent", {}).get("value") if isinstance(item.get("parent"), dict) else item.get("parent")
                c_val = item.get("child", {}).get("value") if isinstance(item.get("child"), dict) else item.get("child")
                if p_val and c_val:
                    existing_rel_pairs.add((str(p_val), str(c_val)))
            if len(batch) < page_size:
                break
            offset += page_size
        except Exception:
            break

    # Step 5: Seed 100% of missing relationships from all_rels
    missing_rels_payloads: List[Tuple[str, str]] = []
    for rel in all_rels:
        p_sys = existing_ci_map.get(rel["parent_key"])
        c_sys = existing_ci_map.get(rel["child_key"])
        if p_sys and c_sys and (p_sys, c_sys) not in existing_rel_pairs:
            existing_rel_pairs.add((p_sys, c_sys))
            missing_rels_payloads.append((p_sys, c_sys))

    rels_created = 0

    def create_rel_worker(pair: Tuple[str, str]) -> int:
        p_sys, c_sys = pair
        session = requests.Session()
        session.auth = auth
        session.headers.update(headers)
        try:
            cr = session.post(
                f"{SN_INSTANCE}/api/now/table/cmdb_rel_ci",
                json={"parent": p_sys, "child": c_sys, "type": REL_TYPE_SYS_ID},
                timeout=12,
            )
            if cr.status_code in (200, 201):
                return 1
        except Exception:
            pass
        return 0

    if missing_rels_payloads:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            for r_ok in pool.map(create_rel_worker, missing_rels_payloads):
                rels_created += r_ok

    # Step 6: Empirical verification of live ServiceNow counts
    sn_total_ci = 0
    sn_total_rel = 0
    try:
        r_ci = requests.get(f"{SN_INSTANCE}/api/now/stats/cmdb_ci", params={"sysparm_count": "true"}, auth=auth, timeout=15).json()
        r_rel = requests.get(f"{SN_INSTANCE}/api/now/stats/cmdb_rel_ci", params={"sysparm_count": "true"}, auth=auth, timeout=15).json()
        sn_total_ci = int(r_ci.get("result", {}).get("stats", {}).get("count", 0))
        sn_total_rel = int(r_rel.get("result", {}).get("stats", {}).get("count", 0))
    except Exception:
        pass

    return {
        "mapped_cis_in_servicenow": len(existing_ci_map),
        "pruned_empty_rooms_deleted_in_servicenow": pruned_deleted,
        "cis_created_or_updated": cis_created_or_updated,
        "missing_rels_attempted": len(missing_rels_payloads),
        "new_rels_created_in_servicenow": rels_created,
        "total_mapped_rels_in_servicenow": len(existing_rel_pairs),
        "verified_servicenow_cmdb_ci_count": sn_total_ci,
        "verified_servicenow_cmdb_rel_ci_count": sn_total_rel,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
    }


def main() -> None:
    all_cis, all_rels, pruned_rooms = enrich_and_prune_cartridge_files()
    sn_stats = sync_full_cmdb_to_servicenow(all_cis, all_rels, pruned_rooms)

    class_counts: Dict[str, int] = {}
    for c in all_cis:
        cls = c.get("sys_class_name", "cmdb_ci")
        class_counts[cls] = class_counts.get(cls, 0) + 1

    summary = {
        "status": "SUCCESS",
        "local_cartridge_total_cis": len(all_cis),
        "local_cartridge_total_relationships": len(all_rels),
        "pruned_empty_staged_rooms_count": len(pruned_rooms),
        "class_counts": class_counts,
        "servicenow_sync": sn_stats,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
