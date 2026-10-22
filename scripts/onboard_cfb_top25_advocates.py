#!/usr/bin/env python3
"""
=============================================================================
CFB Top 25 & Cupcake Advocates Ingestion Engine
Part of Sovereign Sports / FanStack (SDLC: WO0010094)
=============================================================================
Parses /home/james/sovereign_inbox/pilot_drops/Sovereign_Sports_CFB_Top25_and_Cupcake_Advocates_Registry.md
and transactionally ingests all 78 collegiate advocates across:
  - persona
  - sys_user
  - cmdb_ci
  - cmdb_ci_ai_persona
  - m2m_persona_room

Enforces Invariant I.8 & I.9: Zero Raw SQLite Subshells.
All state operations execute strictly through FastAPI REST endpoints
via scripts.core.api_client.deploy_persona().
=============================================================================
"""

import os
import re
import sys
import json
import time
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.core import api_client

REGISTRY_PATH = "/home/james/sovereign_inbox/pilot_drops/Sovereign_Sports_CFB_Top25_and_Cupcake_Advocates_Registry.md"

TEAM_COLOR_MAP: Dict[str, str] = {
    "GENERIC_CUPCAKE": "#00b4d8",  # Sovereign Cyan
    "UGA": "#BA0C2F",  # Georgia Bulldog Red
    "OSU": "#BB0000",  # Ohio State Scarlet
    "TEX": "#BF5700",  # Texas Burnt Orange
    "BAMA": "#9E1B32",  # Alabama Crimson
    "MISS": "#CE1126",  # Ole Miss Cardinal Red
    "ORE": "#154733",  # Oregon Forest Green
    "PSU": "#041E42",  # Penn State Navy
    "MIZ": "#F1B82D",  # Missouri Mizzou Gold
    "TENN": "#FF8200",  # Tennessee Volunteer Orange
    "UTAH": "#CC0000",  # Utah Crimson
    "MIA": "#F47321",  # Miami Hurricane Orange
    "USC": "#990000",  # USC Cardinal
    "OU": "#841617",  # Oklahoma Crimson
    "OKST": "#FF7300",  # Oklahoma State Cowboy Orange
    "KSU": "#512888",  # Kansas State Royal Purple
    "LSU": "#461D7C",  # LSU Purple
    "MICH": "#00274C",  # Michigan Blue
    "ND": "#0C2340",  # Notre Dame Fighting Irish Navy
    "CLEM": "#F56600",  # Clemson Tiger Orange
    "ARIZ": "#CC0000",  # Arizona Cardinal
    "ISU": "#C8102E",  # Iowa State Cardinal Red
    "LOU": "#AD0000",  # Louisville Cardinal Red
    "NEB": "#E41C38",  # Nebraska Scarlet
    "TAMU": "#500000",  # Texas A&M Aggie Maroon
    "WASH": "#4B2E83",  # Washington Husky Purple
}

TEAM_CANNED_TAKES: Dict[str, List[str]] = {
    "check_collector": [
        "The $1.6M guarantee check cleared at 8 AM. Nobody get hurt out there!",
        "Spread was +44.5 and we are only down 28... moral victory secured!",
        "That opening quarter 1st down just funded our campus volleyball charter flights!"
    ],
    "first_drive_hero": [
        "WE ARE UP 3-0 IN THE 1ST QUARTER! RANK US COWARDS! 🚨",
        "UPSET OF THE CENTURY INCOMING! Appalachian State 2007 vibes right here!",
        "They cannot handle our tempo! Stop the count right now!"
    ],
    "portal_nomad": [
        "Watch our transfer edge-rusher on that 3rd-and-long, pure bend and burst!",
        "Our head coach is drawing up masterclass schemes against 5-star depth.",
        "That 15-yard boundary scramble will look tremendous on his portal highlight reel."
    ],
    "sanford_barker": [
        "WOOF WOOF WOOF! Sanford Stadium hedges are shaking! 🐶",
        "Kirby's defensive front has the line of scrimmage completely locked down.",
        "Smell that North Campus tailgate smoke! Physical SEC football!"
    ],
    "1980_ptsd": [
        "Do not celebrate yet! 41 years taught me never trust a 21-point lead.",
        "I need two more stops before my heart rate drops below 160.",
        "Emergency collapse warning: keep the pressure on until double zeroes!"
    ],
    "st_simons_booster": [
        "Our NIL collective locked down the top 3 high school prospects this week.",
        "Flying the private jet into Athens just in time for kickoff.",
        "Non-SEC programs simply do not possess this level of athletic infrastructure."
    ],
    "the_block_o": [
        "Script Ohio is the pinnacle of human achievement! O-H! 🌰",
        "Cross out every letter 'X'! Ann Arbor has zero answers today.",
        "Anything less than a national championship trophy is unacceptable in Columbus."
    ],
    "ryan_day_beard_oil": [
        "Offensive line splits on that 3rd-and-short were completely misaligned.",
        "Live-blogging All-22 gap discipline... we must control the trenches!",
        "Popping an antacid before this red zone sequence."
    ],
    "high_street_hype": [
        "O-H! Screaming it from Lane Avenue all the way to the Horseshoe! 🌰",
        "Every five-star receiver in Florida belongs in Columbus by birthright!",
        "Bratwurst on the grill, cold brew in hand, Buckeyes rolling!"
    ],
    "bevo_sovereign": [
        "The SEC didn't invite Texas; Texas graciously decided to grace the SEC with our presence. 🤘",
        "Burnt Orange royalty. DKR is rocking today!",
        "Lucchese ostrich boots on, Sark's offense humming, national title track!"
    ],
    "crabtree_ghost": [
        "I watched 2008 in Lubbock. No lead is safe until the team bus leaves the tarmac.",
        "Never say 'Texas is back' until the trophy is physically in Austin!",
        "Protect against the boundary pass! Stop celebrating early!"
    ],
    "austin_trench_rat": [
        "18-hour post oak smoked brisket at the tailgate. Real trench warfare today!",
        "Forget perimeter trickery—run power between the tackles with pulling guards!",
        "Pancake blocks on the edge! That is Texas football."
    ],
    "tuscaloosa_dynasty": [
        "The Process demands relentless discipline. 15-0 or the season was wasted. 🐘",
        "Roll Tide Roll! Line of scrimmage dominance is an Alabama birthright.",
        "Nick Saban's standard will forever reign in Bryant-Denny Stadium."
    ],
    "kick_six_survivor": [
        "Do NOT attempt a 57-yard field goal with one second left. Punt the ball!",
        "Cover your eyes on this special teams play... the trauma is permanent.",
        "I refuse to leave my seat until the final whistle blows."
    ],
    "houndstooth_hank": [
        "Bear Bryant fedora on, Yellowhammer in hand on the Quad. Roll Tide!",
        "Defense and physical punting win national championships. Southern tradition.",
        "There is nothing finer than autumn Saturdays in Tuscaloosa."
    ],
    "grove_sommelier": [
        "We may not always win the national title, but we have never lost a party in The Grove. 🍸",
        "Chandeliers under the tents, bourbon in crystal tumblers. Hotty Toddy!",
        "Sartorial excellence is mandatory in Oxford, regardless of the scoreboard."
    ],
    "lane_train_conductor": [
        "All aboard the Lane Train! Throw the clipboard 40 feet into the air! 🚂",
        "4th-and-4 from our own 30? GO FOR IT! Gas pedal pinned to the floor!",
        "Transfer portal wizardry at work! Fast tempo, big plays!"
    ],
    "magnolia_fatalist": [
        "Every time we climb into the top 5, a bizarre lateral or shoe-toss is imminent.",
        "Egg Bowl paranoia is a full-time job. Expect chaos at any moment.",
        "Holding my breath on every single special teams snap."
    ],
    "autzen_aerospace": [
        "Dan Lanning has this trench dialed in. Speed, aerodynamics, Nike innovation! 🦆",
        "47 uniform combinations and 80-yard house calls on perimeter screens!",
        "Autzen Stadium is the loudest, fastest environment in modern college football."
    ],
    "desert_curse_dan": [
        "Michael Dyer's knee was down. Dennis Dixon's knee in 2007... I never relax.",
        "Do not talk to me about Heisman odds or national title projections before November!",
        "We need to be up by 40 before I unclench."
    ],
    "cascadia_quack": [
        "Screaming until my vocal cords snap on 3rd down! Autzen loud! 🦆",
        "The Duck just ripped off 50 push-ups on the mascot platform!",
        "Husky tears are my favorite beverage. Cascadia belongs to the Ducks!"
    ],
    "whiteout_zealot": [
        "110,000 in white shirts generating seismic activity in Happy Valley! 🦁",
        "Beaver Stadium at night is legally impenetrable! We Are Penn State!",
        "Linebacker U is an eternal truth that transcends modern spread gimmicks."
    ],
    "franklin_big_game_audit": [
        "Tracking 4th-down conversion rates against top-10 opponents with extreme anxiety.",
        "Please do not run a 4th-and-5 draw play out of shotgun... I beg of you.",
        "We are 10-2 royalty, but can we seize the promised land?"
    ],
    "valley_coal_grit": [
        "Central Pennsylvania mud, physical tight-end blocking, and field-position punting.",
        "Downing a punt on the 1-yard line is just as glorious as a touchdown!",
        "Blue-collar grit between the hashes. Hit somebody!"
    ],
    "como_chip_shoulder": [
        "Picked 6th in the SEC East again? We feast on disrespect in Columbia! 🐯",
        "M-I-Z! Z-O-U! National media has been sleeping on Missouri all season!",
        "Beat Kansas, silence the SEC blue-bloods, take what is ours!"
    ],
    "fifth_down_trauma": [
        "1990 fifth down, 1997 flea-kicker... NCAA rulebooks suspend themselves against Mizzou.",
        "Checking the replay monitor with zero trust in conference officiating.",
        "Keep your foot on the gas! Referees will find a phantom flag if we don't."
    ],
    "drinkwitz_hype_squad": [
        "Coach Drink with the masterclass press conference and 5-star in-state recruiting! 🐯",
        "Nerd swagger combined with SEC trench toughness! Columbia is buzzing!",
        "Going for it on 4th down was pure 4D chess. Drinkwitz strikes again!"
    ],
    "rocky_top_repeater": [
        "ROCKY TOP YOU'LL ALWAYS BE HOME SWEET HOME TO ME! 🍊",
        "Neyland Stadium checkerboards rocking at 120 decibels! Give him six!",
        "Smoked the victory cigar, singing the fight song for the 400th time today!"
    ],
    "butch_jones_survivor": [
        "Champions of Life... turnover trash cans... I survived the dark ages of Knoxville.",
        "Secondary looked shaky on that boundary fade... panic rising.",
        "Never relax in Neyland until the clock hits 0:00!"
    ],
    "vol_navy_admiral": [
        "Tied up on the Tennessee River outside Neyland Stadium. Vol Navy reporting for duty! 🛥️",
        "Peyton Manning passing records memorized, sweet tea and smoked pork served.",
        "Visitors should feel blessed to witness gameday on the banks of the Tennessee."
    ],
    "rice_eccles_anvil": [
        "Smashmouth football at 4,500 feet elevation. Whittingham's defense breaks wills! ⛰️",
        "240-pound running backs and defensive tackle push! Finesse teams wilt here.",
        "Physical intimidation on every single down in Salt Lake City."
    ],
    "holy_war_inquisitor": [
        "The Holy War is a sacred duty. Humiliate BYU at all costs! 🔴",
        "Goal line stand in the books! Salt Lake belongs to the Crimson!",
        "Keep the ledger: another year of Utah dominance."
    ],
    "rose_bowl_heartbreak": [
        "Cameron Rising gave his body for this program. Proud Ute forever.",
        "East Coast pundits don't stay up for late-night mountain battles, but they will respect us!",
        "Fight for every single yard in the fourth quarter."
    ],
    "turnover_chain_og": [
        "THE U IS BACK! Blasting 90s bass and bringing the swagger to South Florida! 🌴",
        "Five national championship rings in the vault. Orange and green forever!",
        "Big hit, aggressive trash talk, turnover forced! Miami football!"
    ],
    "hard_rock_traffic_doomer": [
        "Sat in 2 hours of Turnpike traffic... PLEASE just take a knee in victory formation!",
        "Mario Cristobal, do not call a running play with 40 seconds left and no timeouts!",
        "My blood pressure cannot survive clock mismanagement in Miami."
    ],
    "coral_gables_cane": [
        "Coconut Grove dinner booked, NIL deals signed, South Florida recruiting locked.",
        "Florida belongs to Miami. Defeat the Gators, crush the Seminoles.",
        "State supremacy is non-negotiable for The U."
    ],
    "coliseum_royalty": [
        "Hollywood stars in the luxury box, Traveler galloping on the sideline. Fight On! ✌️",
        "USC is the premier blue-blood football institution of the Western world.",
        "Expect breathtaking passing fireworks and Heisman-caliber quarterback play."
    ],
    "defense_optional_dan": [
        "Shielding my eyes on 3rd-and-14... please make the open-field tackle!",
        "We need to score 55 points today to feel remotely comfortable.",
        "Lincoln Riley's offense must outscore our defensive anxiety."
    ],
    "trojan_conquest": [
        "Fight On! Spirit of Troy band playing 'Tribute to Troy' on endless repeat! ✌️",
        "Pete Carroll glory days are etched in stone. Beat UCLA, beat Notre Dame!",
        "Invading Midwestern Big Ten stadiums and bringing the cardinal and gold power."
    ],
    "boomer_sooner_loop": [
        "BOOMER! (Awaiting your SOONER!). Fight song on a 24-hour mental loop! 🐎",
        "Sooner Schooner rolling across the Owen Field turf! Crimson dominance!",
        "Horns Down is a basic law of physics in Norman, Oklahoma."
    ],
    "brent_venables_veins": [
        "Neck veins bulging on the sideline! Maximum effort, gap discipline on every snap!",
        "Five energy drinks before an 11 AM kickoff. Violent open-field tackling!",
        "SEC trench size demands total physical commitment. Swarm the football!"
    ],
    "red_river_avenger": [
        "Fried butter and corny dogs at the State Fair of Texas, Cotton Bowl divided 50/50!",
        "Horns Down forever! Dallas belongs to the Sooners on Texas Week!",
        "Golden Hat stays in Norman where it belongs!"
    ],
    "stillwater_mullet": [
        "I'm a man! I'm forty! Mike Gundy and the Stillwater mullet lead the way! 🤠",
        "Orange and black cowboy hats, hard work, and winning tough Big 12 dogfights.",
        "Do not question Gundy's clock management—it's high-level country psychology!"
    ],
    "bedlam_scars": [
        "We live to be the chaotic spoiler that ruins everyone else's season!",
        "Chip on our shoulder since 1890. Never count the Pokes out.",
        "Panic when national pundits rank us top 10; thrive when everyone doubts us!"
    ],
    "paddle_people_chief": [
        "CLACK CLACK CLACK! Boone Pickens brick walls reverberating with orange paddles! 🟧",
        "Opposing offenses cannot hear the snap count in Stillwater!",
        "Unleash the acoustic terror on 3rd down! Go Pokes!"
    ],
    "snyder_windbreaker": [
        "Purple windbreaker zipped to the neck. Bill Snyder's 16 goals for success! 🌾",
        "Time of possession, zero turnovers, flawless extra points. Pure football.",
        "Handwritten thank-you notes for every pass breakup and punt coverage tackle."
    ],
    "farmageddon_bruiser": [
        "Wheat farmed all week, crushing Big 12 trenches on Saturday! K-State power!",
        "Fullback lead block between the tackles is God's gift to football.",
        "Manhattan, Kansas is God's country. Smashmouth Great Plains dominance!"
    ],
    "manhattan_special_teams": [
        "Blocked punt or kickoff return touchdown incoming! K-State special teams magic!",
        "Hidden yardage wins football games. Punt return lane execution is art.",
        "Special teams is where opposing souls are stolen in the Bill Snyder Family Stadium."
    ],
    "death_valley_gumbo": [
        "Tiger Stadium under the lights! Cajun gumbo, dark roux, and deafening night noise! 🐯",
        "Opposing quarterbacks have visible tremors walking into Baton Rouge at night.",
        "Geaux Tigers! Aggressive deep shots and crushing blindside sacks!"
    ],
    "brian_kelly_accent_critic": [
        "Still auditing Brian Kelly's faux-Cajun accent, but win games and we forgive it.",
        "Zero patience for red-zone turnovers. Baton Rouge demands national titles!",
        "LSU expectations: 10 wins minimum every single year."
    ],
    "bayou_bengal_recruiter": [
        "Every five-star receiver in Louisiana has my phone number on speed dial.",
        "NFL Draft first-round talent factory. Nobody matches our perimeter speed!",
        "Death Valley produces athletic freaks that leave secondaries in the dust."
    ],
    "victors_valiant": [
        "Hail to the Victors Valiant! The leaders and the best in Ann Arbor! 〽️",
        "The Team, The Team, The Team! Bo's standard lives forever in the Big House.",
        "Superiority in academics, athletics, and trench dominance over Columbus."
    ],
    "app_state_nightmare": [
        "September 1, 2007 still haunts my nightmares. Trouble with the snap...",
        "I hold my breath on every non-conference punt attempt. Two gunners required!",
        "Never assume any noon kickoff is an easy victory. Vigilance always!"
    ],
    "smashmouth_ann_arbor": [
        "Freezing rain in the Big House, 50 running plays, pulling guards! Manball! 〽️",
        "Throwing more than 15 times a game is a sign of physical weakness.",
        "Pound the rock into a stacked box until the opposing defensive tackles quit."
    ],
    "touchdown_jesus_juror": [
        "Touchdown Jesus watches over South Bend. Independent divine providence! ☘️",
        "Knute Rockne speeches on loop, golden helmets gleaming on NBC.",
        "The sanctity of Notre Dame football transcends conference realignment."
    ],
    "mac_home_game_ptsd": [
        "Panic alert: MAC or Sun Belt team in South Bend with a backup quarterback!",
        "Northern Illinois, Marshall... we play down to the level of every 28-point underdog.",
        "Sound the sirens! Do not let them hang around into the fourth quarter!"
    ],
    "south_bend_scrapper": [
        "North end zone season tickets, bratwurst, green beer, and hating USC and Michigan! ☘️",
        "Rudy was offsides and nobody cares because the gold helmets demand respect!",
        "Hit somebody in the mouth! South Bend football is built on iron and grit."
    ],
    "howards_rock_disciple": [
        "Bus ride around Death Valley, running down the hill, rubbing Howard's Rock! 🐅",
        "Clemson family culture over transfer portal mercenary chaos any day.",
        "Bright orange polo on, Memorial Stadium deafening! Go Tigers!"
    ],
    "portal_paranoia_pat": [
        "WE NEED A PORTAL OFFENSIVE TACKLE! Why are we not signing veteran transfers?!",
        "Frantic booster panic watching Georgia and Florida State load up portal rosters.",
        "Protect the quarterback or modern college football will leave us behind!"
    ],
    "orange_britches_rage": [
        "Championship orange pants game! Memorial Stadium hill run is peak athletics! 🐅",
        "South Carolina is an inferior football institution that gets put in its place annually.",
        "Upstate dominance! Palmetto State belongs to the Clemson Tigers!"
    ],
    "tucson_cactus_sniper": [
        "Triple-digit heat, Sonoran hot dogs, and 52-48 Big 12 air raid shootouts! 🌵",
        "Opponent scored? Who cares! Throw a 75-yard bomb on the very next snap!",
        "Arizona football is explosive, chaotic, and terrifyingly fun."
    ],
    "desert_swarm_ghost": [
        "My heart stopped beating in 1993 with Tedy Bruschi and the Desert Swarm.",
        "Giving up a 3rd-and-17 in modern zone coverage is an insult to Tucson tradition.",
        "Blitz on every down! Wrap up and tackle through the whistle!"
    ],
    "zona_zoo_anarchist": [
        "Red and blue powder flying in the Zona Zoo! Shirt off by the second quarter! 🐻",
        "Territorial Cup venom: Arizona State's existence is a personal affront!",
        "Bring the desert heat and rattle visiting quarterbacks all four quarters!"
    ],
    "jack_trice_wind": [
        "35-mph prairie gusts and 38-degree freezing rain in Ames: peak football weather! 🌪️",
        "Watch high-flying spread offenses freeze solid in Jack Trice Stadium!",
        "Matt Campbell 5-star culture over high-priced mercenary transfer portal rosters."
    ],
    "el_assico_survivor": [
        "El Assico survivor... 7-3 final scores on 3 safeties and 8 muffed punts.",
        "Whenever a punt goes airborne into 40-mph Iowa wind, pure dread takes over.",
        "Cy-Hawk chaos is not for the faint of heart. Expect maximum comedy."
    ],
    "veisha_tailgate_king": [
        "Pork chops smoking in the RV lot, Iowa corn whiskey flowing. Cyclone pride! 🌪️",
        "Most loyal, long-suffering fans in college football. Packed house through 3-9 years.",
        "Win or lose, Jack Trice Stadium is a sacred Midwestern cathedral."
    ],
    "derby_city_speed": [
        "Jeff Brohm play-action trickery, flea-flickers, and 60-yard bombs! 🔴",
        "Lamar Jackson hurdling defenders set the standard. Speed kills in Derby City!",
        "No conservative field goals! Go for it on 4th down and attack downfield!"
    ],
    "bourbon_fumble_doomer": [
        "Sipping neat Kentucky bourbon while bracing for the inevitable red-zone turnover.",
        "Led top teams for 55 minutes only to fumble on our own 10-yard line... I know the script.",
        "Hold the football with two hands high and tight! Ball security panic!"
    ],
    "cardinal_bluegrass_rebel": [
        "Governor's Cup is our personal Super Bowl. Despise Kentucky blue with every fiber! 🔴",
        "Remind Lexington basketball snobs that Louisville has BCS / NY6 football hardware!",
        "The Ville runs this state on the gridiron. Cards all day!"
    ],
    "sellout_streak_95": [
        "400-game Memorial Stadium sellout streak! Sea of Red in Lincoln is eternal! 🌽",
        "Tom Osborne's 1995 option playbook is the pinnacle of American athletics.",
        "The sleeping giant is awakening. Nebraska blue-blood glory will return!"
    ],
    "one_score_loss_insanity": [
        "Lost 25 games by 3 points or fewer... I am completely psychologically shattered.",
        "Close your eyes during clutch 4th-quarter field goals. Just run out the clock!",
        "Two-minute drill panic is a diagnosed condition in Lincoln, Nebraska."
    ],
    "blackshirt_enforcer": [
        "Skull-and-crossbones Blackshirts must be earned with bone-crushing tackles! ☠️",
        "Hold Big Ten backs under 50 yards and hit the quarterback hard and clean.",
        "Zero tolerance for arm tackles or soft pursuit angles. Earn the black shirt!"
    ],
    "twelfth_man_cadet": [
        "Standing all four quarters! Midnight Yell cultist screaming for the Aggies! 👍",
        "Reveille is the First Lady of Texas. Never speak the name of tu!",
        "Gig 'em! Farmers fight! Kyle Field is swaying under 108,000 maroon faithful!"
    ],
    "eight_and_four_scars": [
        "Traumatized by $100M contracts resulting in 8-4 records. Squash the playoff hype!",
        "Terrified of road trips to Starkville or Fayetteville... disaster always lurks.",
        "Win 10 games first before you start talking about national title contention!"
    ],
    "kyle_field_sway": [
        "Kyle Field's upper deck is structurally engineered to sway and intimidate! 👍",
        "Aggie engineering alumni funding top facilities in world sports. SEC West crucible!",
        "108,000 fans standing in unison. Nobody matches our collegiate tradition."
    ],
    "montlake_sailgater": [
        "Sailgating on Lake Washington outside Husky Stadium with wild grilled salmon! 🐺",
        "Purple fleece vests, AAU academic prestige, and vertical passing fireworks!",
        "Oregon fans are uncultured lumberjacks with sneaker money. Bow Down to Washington!"
    ],
    "big_ten_jet_lag_doomer": [
        "Tracking circadian body clocks for 9 AM Pacific kickoffs in Ohio and New Jersey.",
        "Midwestern humidity and 2,500-mile cross-country flights will sap fourth-quarter legs.",
        "Panic about interior line size when the temperature drops below freezing."
    ],
    "husky_stadium_roar": [
        "133.6 decibels registered on the Montlake soundboard! Rain, wind, deafening noise! 🐺",
        "Visiting quarterbacks can't hear their own audibles under our stadium roof cantilevers!",
        "Decibel disruption on every defensive down. Bow Down to Washington!"
    ]
}


def parse_registry(file_path: str) -> List[Dict[str, Any]]:
    """Parse all 78 advocates from the markdown drop, cleaning backslash escapes."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Registry file not found at: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Unescape markdown formatting characters like \#, \*, \_, \`, \-, \[, \], etc.
    chars = ['#', '*', '_', '`', '-', '>', '[', ']', '(', ')', '+', '!', '.']
    for c in chars:
        content = content.replace('\\' + c, c)

    blocks = re.split(r'\n(?=#{3,4}\s+@)', content)
    parsed = []

    for block in blocks:
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if not lines:
            continue
        header = lines[0]
        m_handle = re.search(r'#{3,4}\s+@([a-zA-Z0-9_]+)', header)
        if not m_handle:
            continue
        handle = m_handle.group(1).lower()

        # Team / Scope
        team_m = re.search(r'-\s+\*\*Team(?:\s*/\s*Scope)?:\*\*\s+`?([A-Z0-9_]+)`?', block)
        team = team_m.group(1) if team_m else "GENERIC_CUPCAKE"

        # Cadence
        cadence_m = re.search(r'-\s+\*\*Interaction Cadence:\*\*\s+`?([a-zA-Z_]+)`?', block)
        cadence = cadence_m.group(1).lower() if cadence_m else "pacer"

        # Boggs Reactivity (Entropy)
        boggs_m = re.search(r'-\s+\*\*Boggs Reactivity(?:\s*\(Entropy\))?:\*\*\s+Level\s+(\d+)', block)
        boggs_level = int(boggs_m.group(1)) if boggs_m else 2

        # System Instruction / Directive
        sys_m = re.search(r'-\s+\*\*System Instruction\s*/\s*Directive:\*\*\s+(.*?)(?=\n-\s+\*\*|\n#{1,4}\s+|\Z)', block, re.DOTALL)
        system_prompt = sys_m.group(1).strip() if sys_m else ""

        # Deep Lore & Superstitions
        lore_m = re.search(r'-\s+\*\*Deep Lore & Superstitions:\*\*\s+(.*?)(?=\n-\s+\*\*|\n#{1,4}\s+|\Z)', block, re.DOTALL)
        deep_lore = lore_m.group(1).strip() if lore_m else ""

        # Governance & Alignment Boundaries / Guardrails
        gov_m = re.search(r'-\s+\*\*Governance(?:\s*&.*?)?:\*\*\s+(.*?)(?=\n-\s+\*\*|\n#{1,4}\s+|\Z)', block, re.DOTALL)
        governance = gov_m.group(1).strip() if gov_m else ""

        # Display Name extraction
        dn_m = re.search(r'You are (.*?)\s+\(@' + re.escape(handle) + r'\)', system_prompt)
        if dn_m:
            display_name = dn_m.group(1).strip()
        elif " — " in header:
            display_name = header.split(" — ")[1].strip()
        else:
            display_name = handle.replace("_", " ").title()

        # Authentic team color
        color = TEAM_COLOR_MAP.get(team, "#00b4d8")

        # Canned takes
        canned = TEAM_CANNED_TAKES.get(handle, [
            f"Gameday in full effect! Defend {team} with relentless passion!",
            f"Line of scrimmage execution will dictate the outcome today.",
            f"Every possession matters under pressure. Let's make history!"
        ])

        parsed.append({
            "handle": handle,
            "display_name": display_name,
            "team": team,
            "cadence": cadence,
            "boggs_level": boggs_level,
            "system_prompt": system_prompt,
            "deep_lore": deep_lore,
            "governance": governance,
            "color": color,
            "canned_takes": canned,
            "rooms": ["global", "fanstack_gridiron", f"team_{team.lower()}"]
        })

    return parsed


def run_ingestion():
    print("=" * 70)
    print("🏈 SOVEREIGN SPORTS: CFB TOP 25 & CUPCAKE ADVOCATES INGESTION")
    print("=" * 70)
    print(f"Parsing registry: {REGISTRY_PATH}")
    
    advocates = parse_registry(REGISTRY_PATH)
    print(f"✅ Extracted {len(advocates)} advocates across {len(set(a['team'] for a in advocates))} teams.")

    if len(advocates) != 78:
        print(f"⚠️ Warning: Expected 78 advocates, found {len(advocates)}.")

    success_count = 0
    fail_count = 0
    start_time = time.time()

    for idx, adv in enumerate(advocates, 1):
        print(f"[{idx:02d}/78] Ingesting @{adv['handle']} ({adv['display_name']} - {adv['team']})... ", end="")
        try:
            res = api_client.deploy_persona(
                handle=adv["handle"],
                display_name=adv["display_name"],
                team=adv["team"],
                system_prompt=adv["system_prompt"],
                deep_lore=adv["deep_lore"],
                behavior_notes=f"College football seated advocate for {adv['team']}. Cadence: {adv['cadence']}.",
                governance=adv["governance"],
                color=adv["color"],
                cadence=adv["cadence"],
                boggs_level=adv["boggs_level"],
                rooms=adv["rooms"],
                canned_takes=adv["canned_takes"]
            )
            if res.get("status") == "success":
                print(f"OK (ID: {res.get('persona_id')}, Seated: {res.get('rooms_seated')} rooms)")
                success_count += 1
            else:
                print(f"FAILED: {res}")
                fail_count += 1
        except Exception as e:
            print(f"ERROR: {e}")
            fail_count += 1

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"🎉 INGESTION COMPLETE in {elapsed:.2f}s")
    print(f"✅ Successfully Deployed: {success_count} / {len(advocates)}")
    print(f"❌ Failures: {fail_count}")
    print("=" * 70)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_ingestion()
