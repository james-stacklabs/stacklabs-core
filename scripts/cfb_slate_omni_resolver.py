#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Saturday Slate Omni-Ingest, Multi-Watering-Hole & CFB Subcultural Lexicon Resolver
Path: /home/james/stacklabs/scripts/cfb_slate_omni_resolver.py
"""
import argparse, collections, dataclasses, datetime, hashlib, json, math, os, random, re, sqlite3, sys, tempfile, time
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter

REPO_ROOT = Path("/home/james/stacklabs")
DB_PATH = Path(os.getenv("STACKLABS_WIRETAP_DB", str(REPO_ROOT / "data" / "morning_wiretap.db")))
SPORTS_GT_PATH = Path(os.getenv("STACKLABS_SPORTS_GT_JSON", str(REPO_ROOT / "ground_truth" / "sports_ground_truth.json")))
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
EMOJI_SHORTCODE_RE = re.compile(r":[a-zA-Z0-9_+-]+:")


@dataclasses.dataclass(frozen=True)
class SubculturalShibboleth:
    shibboleth_id: str
    team_abbrev: str
    program_name: str
    primary_board: str
    board_url: str
    trigger_tokens: List[str]
    static_nlp_false_positive: str
    subcultural_ground_truth: str
    barf_ammunition_angle: str
    z_score_threshold: float = 4.5

    def to_canonical_dict(self) -> Dict[str, Any]:
        return {
            "shibboleth_id": self.shibboleth_id,
            "team_abbrev": self.team_abbrev,
            "program_name": self.program_name,
            "primary_board": self.primary_board,
            "board_url": self.board_url,
            "trigger_tokens": sorted(set(t.lower().strip() for t in self.trigger_tokens)),
            "static_nlp_false_positive": self.static_nlp_false_positive,
            "subcultural_ground_truth": self.subcultural_ground_truth,
            "barf_ammunition_angle": self.barf_ammunition_angle,
            "z_score_threshold": round(float(self.z_score_threshold), 2),
        }

    def compute_sha256(self) -> str:
        raw = json.dumps(self.to_canonical_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


KNOWN_WATERING_HOLES: Dict[str, Dict[str, Any]] = {
    "BYU": {"primary_board": "CougarBoard.com", "board_url": "https://www.cougarboard.com/board/", "creator_channels": ["Locked On BYU", "Cougar Sports Insider"], "cultural_anchor": "Provo Honor Code, Soaking & Quaking Lore, Blue Goggles"},
    "ND": {"primary_board": "IrishIllustrated.com / BlueAndGold.com", "board_url": "https://247sports.com/college/notre-dame/board/", "creator_channels": ["Notre Dame Football Report by Chat Sports", "Irish Breakdown"], "cultural_anchor": "Touchdown Jesus, Independent NBC Payouts, Golden Dome"},
    "TEX": {"primary_board": "SurlyHorns.com", "board_url": "https://www.surlyhorns.com/board/", "creator_channels": ["Texas Football Today", "Hook'Em Live"], "cultural_anchor": "Pole Assassin & Gia the Monkey, Burnt Orange Boosters, 9.95ers"},
    "FLA": {"primary_board": "GatorCountry.com / Swamp247", "board_url": "https://www.gatorcountry.com/swampgas/", "creator_channels": ["Gators Breakdown", "Chat Sports Gators"], "cultural_anchor": "Cleat Yeet Shoe Throw, The Swamp, Napier Buyout Math"},
    "OSU": {"primary_board": "ElevenWarriors.com", "board_url": "https://www.elevenwarriors.com/forum", "creator_channels": ["Buckeye Scoop", "Chat Sports Buckeyes"], "cultural_anchor": "Born on Third Base, Ryan Day vs Lou Holtz, $20M Roster"},
    "IU": {"primary_board": "Peegs.com (247 Indiana)", "board_url": "https://247sports.com/college/indiana/board/", "creator_channels": ["Locked On Hoosiers", "Hoosier Huddle"], "cultural_anchor": "Google Me I Win (Curt Cignetti), 9WINDIANA Surge"},
    "ALA": {"primary_board": "BamaOnLine / TideFans.com", "board_url": "https://www.on3.com/teams/alabama-crimson-tide/board/", "creator_channels": ["Bama Central", "Chat Sports Crimson Tide"], "cultural_anchor": "Post-Saban Era, Paul Finebaum Callers, Kalen DeBoer Hoodie"},
    "TENN": {"primary_board": "VolNation.com", "board_url": "https://www.volnation.com/forum/", "creator_channels": ["Vol Network Live", "Chat Sports Volunteers"], "cultural_anchor": "French's Mustard & Golf Balls, Grumors Flight Tracker, Pike Presser"},
    "UGA": {"primary_board": "DawgPost.com / UGASports.com", "board_url": "https://uga.rivals.com/forums/12-dawg-chat", "creator_channels": ["Uncle Lou Live", "DawgNation Daily"], "cultural_anchor": "Grown Men Barking, Kirby Smart Locker Room Bulletin Board"},
    "AUB": {"primary_board": "AuburnUndercover / The Bunker", "board_url": "https://247sports.com/college/auburn/board/", "creator_channels": ["Locked On Auburn", "War Eagle Live"], "cultural_anchor": "Jordan-Hare Voodoo, YellaWood Booster Jets, FOIA Burner Phones"},
    "LSU": {"primary_board": "TigerDroppings.com", "board_url": "https://www.tigerdroppings.com/rant/lsu-sports/", "creator_channels": ["Locked On LSU", "After Further Review"], "cultural_anchor": "Neck (STTDB), Corndogs, Death Valley Night Voodoo"},
    "MISS": {"primary_board": "RebelGrove.com / OMSpirit", "board_url": "https://www.on3.com/teams/ole-miss-rebels/board/", "creator_channels": ["Locked On Ole Miss", "Talk of Champions"], "cultural_anchor": "Joey Freshwater, The Grove Chandeliers, Portal King"},
    "TAMU": {"primary_board": "TexAgs.com", "board_url": "https://texags.com/forums", "creator_channels": ["TexAgs Live", "Locked On Aggies"], "cultural_anchor": "Battered Aggie Syndrome (BAS), List Eater, $76M Buyout"},
    "MICH": {"primary_board": "MGoBlog.com", "board_url": "https://mgoblog.com/mgoboard", "creator_channels": ["Michigan Football Report", "Locked On Wolverines"], "cultural_anchor": "Connor Stalions 600-Page Manifesto, Vacuum Repair, CMU Sideline"},
    "ORE": {"primary_board": "ScoopDuck.com / DuckTerritory", "board_url": "https://www.on3.com/teams/oregon-ducks/board/", "creator_channels": ["Locked On Ducks", "Autzen Audibles"], "cultural_anchor": "Uncle Phil Nike Blank Check, Playing for Clicks"},
    "PSU": {"primary_board": "BlueWhiteIllustrated / Lions247", "board_url": "https://www.on3.com/teams/penn-state-nittany-lions/board/", "creator_channels": ["Locked On Nittany Lions", "State Media"], "cultural_anchor": "Big Game James 4th-and-5 Call, Beaver Stadium White Out"},
}

CANONICAL_CFB_SHIBBOLETHS: List[SubculturalShibboleth] = [
    SubculturalShibboleth("BYU_SOAKING_QUAKING", "BYU", "BYU Cougars", "CougarBoard.com", "https://www.cougarboard.com/board/", ["soaking", "quaking", "jump humping", "durfing", "ncmo", "swig", "honor code"], "Laundry detergent soaking cycles, Wasatch Range earthquake tremors, or mattress retail", "Provo Honor Code workarounds: static insertion with zero pelvic motion ('soaking'), recruiting a roommate to jump on the mattress to induce passive kinetic motion ('quaking' / 'jump humping'), dry friction in denim ('durfing'), and Non-Committal Make Outs ('NCMO').", "BYU's 2-minute offense moves with the exact kinetic stillness of a Provo dorm room waiting for a roommate to bounce on the box springs.", 4.5),
    SubculturalShibboleth("TEX_POLE_ASSASSIN_MONKEY", "TEX", "Texas Longhorns", "SurlyHorns.com", "https://www.surlyhorns.com/board/", ["pole assassin", "gia", "emotional support monkey", "jeff banks", "surly", "9.95ers"], "Wildlife primate conservation, circus performance, or zoo incident reports", "Former Texas special teams coordinator Jeff Banks left his family for adult entertainer 'Pole Assassin' (Danielle Thomas), whose pet emotional-support monkey ('Gia') bit a trick-or-treater on Halloween, becoming the defining masterpiece thread in SurlyHorns history.", "Texas special teams coverage has been biting trick-or-treaters in the dark ever since Pole Assassin's monkey was running the kicking unit.", 4.2),
    SubculturalShibboleth("TENN_MUSTARD_GOLF_BALLS_GRUMORS", "TENN", "Tennessee Volunteers", "VolNation.com", "https://www.volnation.com/forum/", ["mustard", "french's", "golf ball", "titleist", "butt chugging", "grumors", "schiano"], "Grocery store condiment inventory, PGA golf equipment, or municipal aviation logs", "VolNation nuclear trilogy: pelting former coach Lane Kiffin with yellow French's mustard bottles and Titleist golf balls in 2021, the infamous 2012 UT Pike fraternity alcohol-enema ('butt chugging') lawyer press conference, and 'Grumors' (tracking private jets on FlightAware convinced Jon Gruden is landing in Knoxville).", "One more blown 3rd-and-long in Neyland and the upper deck is raining yellow French's mustard bottles and Titleist Pro V1s onto the hash marks.", 4.3),
    SubculturalShibboleth("MISS_JOEY_FRESHWATER", "MISS", "Ole Miss Rebels", "RebelGrove.com / OMSpirit", "https://www.on3.com/teams/ole-miss-rebels/board/", ["joey freshwater", "jimmy chestnut", "popcorn", "the grove", "portal king"], "Freshwater hydrology, municipal water treatment, or snack food concessions", "Lane Kiffin's legendary undercover bar alter-ego ('Joey Freshwater' and 'Jimmy Chestnut') from his Alabama OC and FAU days, paired with telling sideline reporters 'get your popcorn ready' before kickoff.", "Lane Kiffin is dialing up 4th-and-2 from his own 34 like Joey Freshwater closing out a Tuscaloosa college bar at 1:55 AM.", 4.2),
    SubculturalShibboleth("AUB_BURNER_PHONE_YELLAWOOD", "AUB", "Auburn Tigers", "AuburnUndercover / The Bunker", "https://247sports.com/college/auburn/board/", ["burner phone", "escort", "foia", "pine box", "yellawood", "hot tub", "freeze warning"], "Prepaid mobile telecommunications, forestry lumber prices, or weather advisories", "Hugh Freeze getting caught via open-records FOIA requests dialing a Tampa escort service on his university-issued cell phone, Tommy Tuberville's 'carry me out in a pine box' quote before bolting, and YellaWood lumber billionaire Jimmy Rane bankrolling booster coaching coups.", "Auburn's red-zone playcalling looks like it was dialed in from a FOIA-discoverable university cell phone while the YellaWood jet is already warming up on the tarmac.", 4.3),
    SubculturalShibboleth("LSU_STTDB_NECK_CORNDOGS", "LSU", "LSU Tigers", "TigerDroppings.com", "https://www.tigerdroppings.com/rant/lsu-sports/", ["sttdb", "neck", "corndog", "corndogs", "hummer", "tigerdroppings"], "Cervical spine anatomy, state fair carnival catering, or automotive dealerships", "The LSU student section's banned brass-band anthem 'Neck' ('Suck That Tiger D***, B****'), rival SEC fans claiming Baton Rouge tailgates smell like state-fair corndogs, and Ed Orgeron's gravelly bayou lore.", "Baton Rouge is three bourbon cups deep screaming for the brass band to play Neck while the defensive secondary gets cooked over the middle.", 4.3),
    SubculturalShibboleth("TAMU_BAS_LIST_EATER", "TAMU", "Texas A&M Aggies", "TexAgs.com", "https://texags.com/forums", ["list eater", "battered aggie", "bas", "jimbo plaque", "midnight yell", "8-4"], "Office stationery consumption, domestic clinical psychology, or arithmetic", "Battered Aggie Syndrome ('BAS' — inevitable collapse after early-season rankings hype), the 2004 'List Eater' incident where an Aggie student literally ate another student's campout signup list to cut in line for tickets, and handing Jimbo Fisher a dateless national championship plaque before paying him a $76M buyout.", "Battered Aggie Syndrome just clocked in right on schedule—somebody hide the ticket campout list before TexAgs eats the paper.", 4.2),
    SubculturalShibboleth("MICH_VACUUM_MANIFESTO_STALIONS", "MICH", "Michigan Wolverines", "MGoBlog.com", "https://mgoblog.com/mgoboard", ["manifesto", "connor stalions", "vacuum repair", "ray-bans", "cmu sideline", "ferret"], "Small household appliance repair, optical sunglasses retail, or political tracts", "Low-level staffer Connor Stalions maintaining a 600-page Google Doc 'Michigan Manifesto', operating a vacuum-repair business out of his house, and allegedly infiltrating Central Michigan's sideline at night wearing a fake goatee and recording glasses, alongside MGoBlog's 'drowning a ferret' metaphor for boa-constrictor clock control.", "Michigan is trying to strangle the clock like an MGoBlog ferret while checking Page 412 of the vacuum-repair manifesto for a 3rd-down passing route.", 4.2),
    SubculturalShibboleth("FLA_CLEAT_YEET_SHOE_THROW", "FLA", "Florida Gators", "GatorCountry.com", "https://www.gatorcountry.com/swampgas/", ["cleat yeet", "shoe throw", "marco wilson", "jorts", "napier buyout", "swampgas"], "Athletic footwear retail, denim apparel, or wetland methane emissions", "The infamous 2020 'Cleat Yeet' where Florida DB Marco Wilson hurled an LSU tight end's detached Nike cleat 20 yards downfield in the fog on 3rd down—drawing an unsportsmanlike penalty that cost UF its playoff hopes—combined with denim 'jorts' culture and Billy Napier's buyout calculator.", "Florida just committed the situational equivalent of hurling an opponent's loose cleat 20 yards into the Gainesville fog on 3rd-and-stopped.", 4.3),
    SubculturalShibboleth("UGA_GROWN_MEN_BARKING", "UGA", "Georgia Bulldogs", "DawgPost.com / UGASports.com", "https://uga.rivals.com/forums/12-dawg-chat", ["barking at children", "kirby haircut", "visorgate", "stetson", "sanford hedges"], "Veterinary canine behavior, landscaping hedges, or western headwear", "Georgia's self-aware badge of honor of grown men in red polos barking on all fours at opposing fans in parking lots, combined with Kirby Smart's bowl cut and fabricated locker-room disrespect narratives ('everybody doubted us at 7.5-point favorites').", "Kirby Smart is in the locker room convincing five-star linemen that the AP Poll predicted them to go 4-8 while grown men in Athens bark at a Golden Retriever.", 4.3),
    SubculturalShibboleth("OSU_BORN_ON_THIRD_BASE", "OSU", "Ohio State Buckeyes", "ElevenWarriors.com", "https://www.elevenwarriors.com/forum", ["third base", "lou holtz", "just for men", "cross out the m", "20 million roster"], "Baseball diamond baserunning, men's hair dye cosmetics, or typography", "Jim Harbaugh's 'born on third base and thinks he hit a triple' jab at Ryan Day, Day's unhinged post-game rant asking 'Where is Lou Holtz right now?!' against an 86-year-old retired broadcaster, and ElevenWarriors melting down if an A-gap run gets stuffed.", "One stuffed 3rd-and-1 inside zone and Ryan Day is about to challenge 87-year-old Lou Holtz to an Oklahoma drill at midfield.", 4.3),
    SubculturalShibboleth("IU_NINE_WINDIANA_GOOGLE_ME", "IU", "Indiana Hoosiers", "Peegs.com", "https://247sports.com/college/indiana/board/", ["9windiana", "ninewindiana", "google me", "cignetti", "purdue spoilermakers", "daunted"], "Search engine optimization queries or meteorological wind speed forecasts", "Head coach Curt Cignetti walking into the introductory podium and declaring 'I win. Google me,' turning the decade-old Peegs.com '9WINDIANA' meme into an actual top-25 schematic buzzsaw.", "Curt Cignetti didn't even blink—he just told the Big Ten to open a browser tab and Google his win percentage.", 4.2),
    SubculturalShibboleth("ND_TOUCHDOWN_JESUS_INDEPENDENT", "ND", "Notre Dame Fighting Irish", "IrishIllustrated.com / BlueAndGold.com", "https://247sports.com/college/notre-dame/board/", ["touchdown jesus", "nbc contract", "brian kelly", "fam-uh-lee", "golden dome"], "Religious iconography, broadcast television licensing, or family genealogy", "Word of Life mural overlooking Notre Dame Stadium ('Touchdown Jesus'), Brian Kelly's infamous fake Southern accent ('fam-uh-lee') after bolting for LSU, and decades of refusing conference membership while collecting standalone NBC broadcast checks.", "Notre Dame is praying to Touchdown Jesus for a 3rd-down conversion while Brian Kelly practices a fake bayou accent in Baton Rouge.", 4.2),
    SubculturalShibboleth("ALA_PAWL_FINEBAUM_POST_SABAN", "ALA", "Alabama Crimson Tide", "BamaOnLine / TideFans.com", "https://www.on3.com/teams/alabama-crimson-tide/board/", ["pawl", "phyllis", "oatmeal", "little debbie", "kalen deboer hoodie", "saban"], "Snack cake retail inventory, breakfast cereal, or cotton fleece apparel", "Paul Finebaum Show callers screaming 'PAWL, THEY AIN'T PLAYED NOBODY' from Mulga, Nick Saban's strict two-Little-Debbie-Oatmeal-Creme-Pies daily routine vs. the post-Saban adjustment to Kalen DeBoer wearing a black hoodie on the sideline.", "One blown coverage in Tuscaloosa and Phyllis from Mulga is already on hold with Pawl demanding Nick Saban put down the Little Debbie Oatmeal Creme Pie and take his headset back.", 4.2),
    SubculturalShibboleth("ORE_UNCLE_PHIL_ZERO_RINGS", "ORE", "Oregon Ducks", "ScoopDuck.com / DuckTerritory", "https://www.on3.com/teams/oregon-ducks/board/", ["uncle phil", "chrome helmet", "offseason champs", "dan lanning", "clicks"], "Athletic apparel manufacturing, metallurgy plating, or web analytics", "Nike co-founder Phil Knight ('Uncle Phil') writing an unlimited NIL checkbook for 500 chrome uniform combinations while rival Washington and Big Ten fans remind Eugene that the 'O' on their helmet stands for zero national titles, paired with Dan Lanning's 'playing for clicks' locker room speech.", "Uncle Phil just approved uniform combination #418 from Beaverton while the defense plays for clicks on 3rd-and-medium.", 4.2),
    SubculturalShibboleth("PSU_FOURTH_AND_FIVE_BIG_GAME_JAMES", "PSU", "Penn State Nittany Lions", "BlueWhiteIllustrated / Lions247", "https://www.on3.com/teams/penn-state-nittany-lions/board/", ["4th and 5", "big game james", "white out", "elite vs great", "10-2"], "Arithmetic fractions, winter blizzard conditions, or corporate HR evaluations", "James Franklin calling an inside zone handoff into a stacked Ohio State box on 4th-and-5 with the game on the line during a 110,000-fan Beaver Stadium White Out, alongside his post-game press conference monologues about going from 'great to elite' after finishing 10-2.", "It's 4th-and-5 in a Beaver Stadium White Out and James Franklin is already drawing up a delayed handoff straight into three defensive tackles.", 4.3),
]


def build_http_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) StackLabs-CFB-Resolver/2.0", "Accept": "application/json"})
    return session


def get_json_with_backoff(session: requests.Session, url: str, max_attempts: int = 4, base_backoff_s: float = 0.5, max_backoff_s: float = 8.0) -> Dict[str, Any]:
    for attempt in range(max_attempts):
        try:
            resp = session.get(url, timeout=8)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 502, 503, 504):
                retry_hdr = resp.headers.get("Retry-After")
                retry_after = float(retry_hdr) if retry_hdr and retry_hdr.isdigit() else None
                cap = min(max(max_backoff_s, 1.0), base_backoff_s * (2 ** attempt))
                time.sleep(retry_after if retry_after is not None else random.uniform(cap * 0.5, cap))
                continue
            resp.raise_for_status()
        except requests.RequestException as exc:
            if attempt == max_attempts - 1:
                print(f"[ERROR] Exhausted retries fetching {url}: {exc}", file=sys.stderr)
                return {}
            cap = min(max(max_backoff_s, 1.0), base_backoff_s * (2 ** attempt))
            time.sleep(random.uniform(cap * 0.5, cap))
    return {}


def get_wal_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), timeout=10.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA busy_timeout=5000;")
    con.execute("PRAGMA temp_store=MEMORY;")
    return con


def init_wiretap_schemas(con: sqlite3.Connection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS watch_party_streams (id INTEGER PRIMARY KEY AUTOINCREMENT, sport TEXT NOT NULL, game_pk TEXT NOT NULL, game_date TEXT NOT NULL, home_team TEXT NOT NULL, away_team TEXT NOT NULL, stream_id TEXT NOT NULL, stream_title TEXT, stream_url TEXT, source TEXT, resolved_at TEXT, is_live INTEGER DEFAULT 1, UNIQUE(game_pk, stream_id))")
    con.execute("CREATE TABLE IF NOT EXISTS cfb_subcultural_lexicon (shibboleth_id TEXT PRIMARY KEY, team_abbrev TEXT NOT NULL, program_name TEXT NOT NULL, primary_board TEXT NOT NULL, board_url TEXT NOT NULL, trigger_tokens_json TEXT NOT NULL, static_nlp_false_positive TEXT NOT NULL, subcultural_ground_truth TEXT NOT NULL, barf_ammunition_angle TEXT NOT NULL, z_score_threshold REAL NOT NULL DEFAULT 4.5, content_sha256 TEXT NOT NULL, updated_at TEXT NOT NULL)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_cfb_lexicon_team ON cfb_subcultural_lexicon(team_abbrev);")
    con.commit()


def sync_lexicon_to_sqlite(con: sqlite3.Connection) -> Tuple[int, int, int]:
    init_wiretap_schemas(con)
    cur = con.cursor()
    existing_hashes = {r["shibboleth_id"]: r["content_sha256"] for r in cur.execute("SELECT shibboleth_id, content_sha256 FROM cfb_subcultural_lexicon").fetchall()}
    inserted, updated, skipped = 0, 0, 0
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for item in CANONICAL_CFB_SHIBBOLETHS:
        digest = item.compute_sha256()
        cached = existing_hashes.get(item.shibboleth_id)
        if cached == digest:
            skipped += 1
            continue
        tokens_json = json.dumps(sorted(set(t.lower().strip() for t in item.trigger_tokens)), separators=(",", ":"))
        if cached is None:
            cur.execute("INSERT INTO cfb_subcultural_lexicon (shibboleth_id, team_abbrev, program_name, primary_board, board_url, trigger_tokens_json, static_nlp_false_positive, subcultural_ground_truth, barf_ammunition_angle, z_score_threshold, content_sha256, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (item.shibboleth_id, item.team_abbrev, item.program_name, item.primary_board, item.board_url, tokens_json, item.static_nlp_false_positive, item.subcultural_ground_truth, item.barf_ammunition_angle, item.z_score_threshold, digest, now_iso))
            inserted += 1
        else:
            cur.execute("UPDATE cfb_subcultural_lexicon SET team_abbrev=?, program_name=?, primary_board=?, board_url=?, trigger_tokens_json=?, static_nlp_false_positive=?, subcultural_ground_truth=?, barf_ammunition_angle=?, z_score_threshold=?, content_sha256=?, updated_at=? WHERE shibboleth_id=?", (item.team_abbrev, item.program_name, item.primary_board, item.board_url, tokens_json, item.static_nlp_false_positive, item.subcultural_ground_truth, item.barf_ammunition_angle, item.z_score_threshold, digest, now_iso, item.shibboleth_id))
            updated += 1
    con.commit()
    return inserted, updated, skipped


def sync_lexicon_to_sports_ground_truth(gt_path: Path) -> int:
    gt_path.parent.mkdir(parents=True, exist_ok=True)
    data: Dict[str, Any] = {}
    if gt_path.exists():
        try:
            data = json.loads(gt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    lexicon_map = {}
    for item in CANONICAL_CFB_SHIBBOLETHS:
        payload = item.to_canonical_dict()
        payload["content_sha256"] = item.compute_sha256()
        lexicon_map[item.shibboleth_id] = payload
    data["cfb_subcultural_lexicon"] = lexicon_map
    data["cfb_watering_holes"] = KNOWN_WATERING_HOLES
    with tempfile.NamedTemporaryFile("w", dir=str(gt_path.parent), delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, indent=2, sort_keys=True)
        tf.write("\n")
        tmp_name = tf.name
    os.replace(tmp_name, str(gt_path))
    return len(lexicon_map)


def fetch_active_slate(session: requests.Session) -> List[Dict[str, Any]]:
    data = get_json_with_backoff(session, ESPN_SCOREBOARD_URL)
    slate: List[Dict[str, Any]] = []
    shib_by_team: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for item in CANONICAL_CFB_SHIBBOLETHS:
        shib_by_team[item.team_abbrev].append(item.to_canonical_dict())
    for event in data.get("events", []):
        comps = event.get("competitions", [{}])[0]
        competitors = comps.get("competitors", [])
        if len(competitors) < 2:
            continue
        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        h_ab = home.get("team", {}).get("abbreviation", "HOME")
        a_ab = away.get("team", {}).get("abbreviation", "AWAY")
        status_type = event.get("status", {}).get("type", {})
        slate.append({
            "game_id": str(event.get("id", "")),
            "event_name": event.get("name", f"{a_ab} @ {h_ab}"),
            "home_abbrev": h_ab,
            "away_abbrev": a_ab,
            "home_name": home.get("team", {}).get("displayName", h_ab),
            "away_name": away.get("team", {}).get("displayName", a_ab),
            "home_score": home.get("score", "0"),
            "away_score": away.get("score", "0"),
            "status": status_type.get("description", "Scheduled"),
            "detail": status_type.get("detail", ""),
            "start_time": event.get("date", ""),
            "watering_holes": {"home": KNOWN_WATERING_HOLES.get(h_ab, {}), "away": KNOWN_WATERING_HOLES.get(a_ab, {})},
            "subcultural_shibboleths": shib_by_team.get(a_ab, []) + shib_by_team.get(h_ab, []),
        })
    return slate


def persist_slate_to_wiretap(con: sqlite3.Connection, slate: List[Dict[str, Any]]) -> int:
    init_wiretap_schemas(con)
    cur = con.cursor()
    today_str = time.strftime("%Y-%m-%d")
    for game in slate:
        stream_id = f"CFB_{game['game_id']}"
        title = f"{game['away_abbrev']} @ {game['home_abbrev']} ({game['detail']})"
        url = f"https://www.espn.com/college-football/game/_/gameId/{game['game_id']}"
        is_live = 1 if "In Progress" in game["status"] else 0
        cur.execute("INSERT INTO watch_party_streams (sport, game_pk, game_date, home_team, away_team, stream_id, stream_title, stream_url, source, resolved_at, is_live) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?) ON CONFLICT(game_pk, stream_id) DO UPDATE SET stream_title=excluded.stream_title, is_live=excluded.is_live, resolved_at=datetime('now')", ("cfb", game["game_id"], today_str, game["home_abbrev"], game["away_abbrev"], stream_id, title, url, "espn_slate_resolver", is_live))
    con.commit()
    return len(slate)


def lookup_shibboleths(con: sqlite3.Connection, query: str) -> List[Dict[str, Any]]:
    init_wiretap_schemas(con)
    q = query.strip().lower()
    matches = []
    for row in con.execute("SELECT * FROM cfb_subcultural_lexicon ORDER BY team_abbrev ASC").fetchall():
        tokens = json.loads(row["trigger_tokens_json"])
        if row["team_abbrev"].lower() == q or row["shibboleth_id"].lower() == q or any(q in tok or tok in q for tok in tokens):
            matches.append({"shibboleth_id": row["shibboleth_id"], "team_abbrev": row["team_abbrev"], "program_name": row["program_name"], "primary_board": row["primary_board"], "board_url": row["board_url"], "trigger_tokens": tokens, "static_nlp_false_positive": row["static_nlp_false_positive"], "subcultural_ground_truth": row["subcultural_ground_truth"], "barf_ammunition_angle": row["barf_ammunition_angle"], "z_score_threshold": row["z_score_threshold"], "content_sha256": row["content_sha256"]})
    return matches


def evaluate_scoped_chat_bursts(con: sqlite3.Connection, game_id: str, cursor_floor: int = 0) -> Dict[str, Any]:
    init_wiretap_schemas(con)
    if not con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_telemetry'").fetchone():
        return {"game_id": game_id, "stream_status": "NO_ACTIVE_STREAM", "messages_evaluated": 0, "detected_anomalies": []}
    ring: Deque[str] = collections.deque(maxlen=1000)
    last_id = int(cursor_floor)
    while True:
        batch = con.execute("SELECT id, message FROM chat_telemetry WHERE id > ? AND channel_key = ? ORDER BY id ASC LIMIT 500", (last_id, game_id)).fetchall()
        if not batch:
            break
        for r in batch:
            last_id = int(r["id"])
            ring.append(EMOJI_SHORTCODE_RE.sub(" ", str(r["message"] or "")).lower())
        if len(batch) < 500:
            break
    if not ring:
        return {"game_id": game_id, "stream_status": "NO_ACTIVE_STREAM", "messages_evaluated": 0, "detected_anomalies": []}
    total_msgs = len(ring)
    expected_mean = max(total_msgs * 0.005, 0.5)
    std_dev = math.sqrt(max(total_msgs * 0.005 * 0.995, 0.25))
    detected = []
    for lrow in con.execute("SELECT * FROM cfb_subcultural_lexicon").fetchall():
        tokens = json.loads(lrow["trigger_tokens_json"])
        hit_count, matched_tokens = 0, set()
        for msg in ring:
            hits = [tok for tok in tokens if tok in msg]
            if hits:
                hit_count += 1
                matched_tokens.update(hits)
        if hit_count > 0:
            z_score = (hit_count - expected_mean) / std_dev
            if z_score >= float(lrow["z_score_threshold"]):
                detected.append({"shibboleth_id": lrow["shibboleth_id"], "team_abbrev": lrow["team_abbrev"], "hit_count": hit_count, "z_score": round(z_score, 2), "matched_tokens": sorted(matched_tokens), "static_nlp_false_positive": lrow["static_nlp_false_positive"], "subcultural_ground_truth": lrow["subcultural_ground_truth"], "barf_ammunition_angle": lrow["barf_ammunition_angle"]})
    return {"game_id": game_id, "stream_status": "ACTIVE_SCOPED_STREAM", "messages_evaluated": total_msgs, "detected_anomalies": detected}


def main() -> None:
    parser = argparse.ArgumentParser(description="StackLabs Saturday CFB Slate & Subcultural Lexicon Resolver")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--lexicon-only", action="store_true")
    parser.add_argument("--lookup", type=str)
    parser.add_argument("--evaluate-chat", type=str)
    args = parser.parse_args()
    con = get_wal_connection(DB_PATH)
    try:
        ins, upd, skp = sync_lexicon_to_sqlite(con)
        if args.sync or args.lexicon_only:
            gt_count = sync_lexicon_to_sports_ground_truth(SPORTS_GT_PATH)
            print(f"[LEXICON SYNC] SQLite WAL cfb_subcultural_lexicon: inserted={ins}, updated={upd}, skipped_merkle={skp} | sports_ground_truth.json entries={gt_count}")
        if args.lookup:
            print(json.dumps(lookup_shibboleths(con, args.lookup), indent=2))
            return
        if args.evaluate_chat:
            print(json.dumps(evaluate_scoped_chat_bursts(con, args.evaluate_chat), indent=2))
            return
        if args.lexicon_only:
            return
        session = build_http_session()
        slate = fetch_active_slate(session)
        if slate and args.sync:
            print(f"[SLATE SYNC] Synchronized {persist_slate_to_wiretap(con, slate)} CFB games.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
