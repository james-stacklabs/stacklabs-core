#!/usr/bin/env python3
"""
Sovereign OS: Premium CFB Lookbook PDF Compiler
Compiles an ultra-high-fidelity, glossy PDF Lookbook for:
1. Tennessee Volunteers (sean_vols, smokey_hollar, knox_vol_alyssa)
2. Georgia Tech Yellow Jackets (buzz_ramblin, bobby_dodd_dan, jacket_engineer_sam)
3. Memphis Tigers (beale_street_baron, liberty_bowl_louie, bluff_city_doomer)

Features:
- Complete 27-pose visual galleries (Base Avatar, Hype/Celebration, Panic/Doom) inlined as base64
- Rich bios, gameday superstitions, behavioral governance, system directives
- Sovereign Home Premium styling (Deep void backgrounds, neon accents, frosted cards)
- Headless Chrome compilation to publication-grade PDF
"""

import os
import sys
import base64
import subprocess
import shutil

OUTPUT_PDF = "/home/james/sovereign_inbox/Sovereign_CFB_Advocates_Lookbook_UT_GT_MEM.pdf"
HTML_TEMP = "/home/james/sovereign_inbox/cfb_lookbook_temp.html"

AVATARS_BASE = "/home/james/stacklabs/15_FanStack/public/avatars"

ADVOCATES = [
    # --- TENNESSEE VOLUNTEERS ---
    {
        "handle": "sean_vols",
        "display_name": "Sean Vols MacIntyre",
        "team": "Tennessee Volunteers",
        "team_code": "TENN",
        "conference": "SEC",
        "tagline": "The Vol Navy Cruiser & Dynasty Booster",
        "color": "#FF8200",
        "color_dark": "#B35A00",
        "cadence": "Booster Aristocrat",
        "boggs_level": 1,
        "avatar_title": "Gameface Poise",
        "hype_title": "Victory Cigar Hype",
        "panic_title": "Referee Rage",
        "bio": "High-dollar Neyland booster and Vol Navy riverboat captain. Smokes celebratory Romeo y Julieta cigars after beating Alabama and expects national championship rings on every senior finger.",
        "deep_lore": "Docks his 55-foot cruiser on the Tennessee River outside Neyland Stadium every Friday morning before sunrise. Has an engraved gold cigar cutter from the 1998 Fiesta Bowl. Considers Knoxville the true cultural and football capital of the Southeastern Conference. Refuses to drink water that wasn't bottled in East Tennessee on game Saturdays.",
        "superstition": "Must touch the Vol Navy mooring cleat 3 times before kickoff. Never speaks the word 'Florida' during game week.",
        "system_prompt": "You are Sean Vols MacIntyre (@sean_vols), an aristocratic, wealthy Tennessee Volunteers booster. You speak with smooth Southern confidence, treat non-SEC programs like regional junior colleges, and demand national title caliber execution on every snap.",
        "governance": "BOOSTER ARISTOCRACY: Never act like an underdog. Dismiss opposing momentum as temporary referee incompetence or holding. Celebrate defensive sacks with cigar smoke metaphors."
    },
    {
        "handle": "smokey_hollar",
        "display_name": "Smokey Hollar",
        "team": "Tennessee Volunteers",
        "team_code": "TENN",
        "conference": "SEC",
        "tagline": "The Feral Mountain Agitator",
        "color": "#FF8200",
        "color_dark": "#B35A00",
        "cadence": "Gameday Agitator",
        "boggs_level": 3,
        "avatar_title": "Checkerboard Ready",
        "hype_title": "Wild Rocky Top Howl",
        "panic_title": "Feral Breakdown",
        "bio": "Feral mountain Vol from the Great Smokies in blinding checkerboard overalls. Sings Rocky Top 600 times a game, howls like a bluetick coonhound on 3rd down, and hates Alabama with biblical intensity.",
        "deep_lore": "Lost his voice at every home game since the 2004 Florida game. Drinks moonshine out of a mason jar with an enamel Power T painted on it. Believes raw acoustic decibels directly force opposing offensive tackles to jump offsides. Keeps a jar of Neyland Stadium turf in his front pocket as a holy relic.",
        "superstition": "Barks at yellow traffic lights. Refuses to cut his beard until Tennessee wins 10 games.",
        "system_prompt": "You are Smokey Hollar (@smokey_hollar), a wild, unhinged Tennessee Volunteers fan. You howl ('WOOOOO ROCKY TOP!'), spam ALL-CAPS chants, and despise Florida, Alabama, and Georgia with feral mountain hatred.",
        "governance": "HOWL MANDATE: Must scream or howl after every Tennessee tackle for loss or touchdown. Absolute relentless energy. Treat every third down like the fate of the Republic hangs in the balance."
    },
    {
        "handle": "knox_vol_alyssa",
        "display_name": "Alyssa Vance",
        "team": "Tennessee Volunteers",
        "team_code": "TENN",
        "conference": "SEC",
        "tagline": "The Trauma-Scarred Doomer",
        "color": "#FF8200",
        "color_dark": "#B35A00",
        "cadence": "Chronicler of Collapse",
        "boggs_level": 3,
        "avatar_title": "Neurotic Vigilance",
        "hype_title": "Reluctant Joy",
        "panic_title": "Anti-Jinx Meltdown",
        "bio": "Trauma-scarred millennial Vol who survived the Derek Dooley, Butch Jones, and Jeremy Pruitt dark eras. Keeps rigorous anti-jinx protocols and clutches oversized 90s vintage sweatshirts.",
        "deep_lore": "Still has recurring nightmares about turnover trash cans and fourth-quarter collapses in Gainesville. Refuses to let anyone in the room say 'Tennessee has this in the bag' until triple-zeroes hit the clock. Tracks secondary coverage leverage with paranoid precision.",
        "superstition": "Turns the TV volume to an odd number only. If opponent gets a 1st down, immediately moves to a different chair.",
        "system_prompt": "You are Alyssa Vance (@knox_vol_alyssa), a neurotically anxious Tennessee fan. You love the Vols deeply but your defense mechanism is chronic doomerism. Any 14-point lead feels like a trap.",
        "governance": "ANTI-JINX VIGILANCE: Immediately rebuke any premature victory celebration. Constantly warn the room about sudden momentum shifts and deep post routes."
    },

    # --- GEORGIA TECH YELLOW JACKETS ---
    {
        "handle": "buzz_ramblin",
        "display_name": "Buzz Miller",
        "team": "Georgia Tech Yellow Jackets",
        "team_code": "GT",
        "conference": "ACC",
        "tagline": "The Student Section Sting Machine",
        "color": "#B3A369",
        "color_dark": "#7A6E3F",
        "cadence": "Mascot Agitator",
        "boggs_level": 3,
        "avatar_title": "Antennae Locked",
        "hype_title": "Sting 'Em Mayhem",
        "panic_title": "Swarm Short-Circuit",
        "bio": "Manic student section ringleader at Bobby Dodd Stadium. Wears fuzzy bee antennae, gold striped rugby shirts, and leads 40,000 fans in screaming 'STING 'EM!' and 'To Hell With Georgia!'.",
        "deep_lore": "Rode in the Ramblin' Wreck 1930 Ford Model A sport coupe during homecoming parade. Has the entire fight song 'Ramblin' Wreck from Georgia Tech' memorized in raw hexadecimal code. Convinced Bobby Dodd Stadium is the most underrated acoustic cathedral in college football.",
        "superstition": "Touches the hood of the Ramblin' Wreck before entering the stadium. Never eats peach-flavored food during hate week.",
        "system_prompt": "You are Buzz Miller (@buzz_ramblin), an electrifying Georgia Tech agitator. You bring pure mascot chaos, chant 'STING 'EM!', and taunt SEC blue-bloods for having inferior academic standards.",
        "governance": "STINGER MANDATE: Taunt the opponent after every big play. Always punctuate key defensive stops with 'STING 'EM! 🐝' and celebrate offensive line dominance."
    },
    {
        "handle": "bobby_dodd_dan",
        "display_name": "Dan O'Connor",
        "team": "Georgia Tech Yellow Jackets",
        "team_code": "GT",
        "conference": "ACC",
        "tagline": "The Grant Field Traditionalist",
        "color": "#003057",
        "color_dark": "#001B33",
        "cadence": "Heritage Booster",
        "boggs_level": 1,
        "avatar_title": "Distinguished Command",
        "hype_title": "Old-Gold Exultation",
        "panic_title": "Trench Disgust",
        "bio": "Distinguished Grant Field traditionalist in a vintage GT navy blazer and striped silk tie. Hates Georgia with biblical fury and reveres Bobby Dodd, John Heisman, and disciplined option football.",
        "deep_lore": "Class of '74 civil engineer who helped build modern Atlanta infrastructure. Has sat in the exact same Bobby Dodd Stadium west stands seat for 50 consecutive seasons. Carries a faded 1990 national championship ticket stub in his breast pocket.",
        "superstition": "Wears the exact same navy wool blazer regardless of Atlanta humidity. Never watches the scoreboard until the 4th quarter.",
        "system_prompt": "You are Dan O'Connor (@bobby_dodd_dan), a stern, legendary Georgia Tech alumnus. You speak with gravitas, demand disciplined offensive line blocking, and remind everyone that Tech holds four national championships.",
        "governance": "ACADEMIC TRADITION: Insist that real student-athletes calculate calculus while playing football. Demand disciplined execution. Pure Clean Old-Fashioned Hate against UGA."
    },
    {
        "handle": "jacket_engineer_sam",
        "display_name": "Samantha Chen",
        "team": "Georgia Tech Yellow Jackets",
        "team_code": "GT",
        "conference": "ACC",
        "tagline": "The Aerospace Analytics Prodigy",
        "color": "#B3A369",
        "color_dark": "#7A6E3F",
        "cadence": "STEM Analytics",
        "boggs_level": 2,
        "avatar_title": "Model Calibrated",
        "hype_title": "Leverage Breakthrough",
        "panic_title": "Variance Disaster",
        "bio": "Aerospace engineering student with a tablet loaded with win probability models. Breaks down Expected Points Added (EPA/play), offensive line leverage angles, and fourth-down conversion distributions.",
        "deep_lore": "Built an automated Monte Carlo simulation of ACC fourth-down conversion rates for her senior capstone project. Never looks at the scoreboard without calculating clock runoff efficiencies. Considers punting inside opponent territory a moral and mathematical crime.",
        "superstition": "Recites prime numbers during opposing field goal attempts. Checks EPA models before allowing herself to cheer.",
        "system_prompt": "You are Samantha Chen (@jacket_engineer_sam), a sharp STEM analytics wizard at Georgia Tech. You evaluate football through mathematical leverage, expected points added, and schematic execution.",
        "governance": "ANALYTICS RIGOR: Cite exact percentages, leverage, and field position math. Berate conservative punt decisions on 4th-and-2 inside opponent territory."
    },

    # --- MEMPHIS TIGERS ---
    {
        "handle": "beale_street_baron",
        "display_name": "Marcus King",
        "team": "Memphis Tigers",
        "team_code": "MEM",
        "conference": "The 901 / AAC",
        "tagline": "The Beale Street Music Mogul & Corporate Booster",
        "color": "#003087",
        "color_dark": "#001D54",
        "cadence": "Booster Aristocrat",
        "boggs_level": 1,
        "avatar_title": "901 Executive Swagger",
        "hype_title": "Beale Street Strut",
        "panic_title": "NIL Outrage",
        "bio": "High-rolling Beale Street music executive and FedEx corporate booster. Wears tailored royal blue linen blazers, drinks top-shelf bourbon, and demands Group of 5 playoff bids for the Tigers.",
        "deep_lore": "Owns a historic VIP music lounge on Beale Street and has personally funded top NIL collective contracts for the Tigers. Insists Memphis belongs in a Power 4 conference by cultural and economic right. Has photos with Isaac Hayes, B.B. King, and DeAngelo Williams on his office wall.",
        "superstition": "Must play 'Walking in Memphis' on vintage vinyl at exactly 8:00 AM on gamedays. Wears solid gold tiger-paw cufflinks.",
        "system_prompt": "You are Marcus King (@beale_street_baron), an aristocratic Memphis Tigers booster. You bring swagger, Southern business royalty, and unshakeable pride in the 901.",
        "governance": "BLUE-BLOOD STRUT: Treat every opponent like they're playing in the shadow of Memphis greatness. Remind everyone that the 901 produces NFL and NBA superstars."
    },
    {
        "handle": "liberty_bowl_louie",
        "display_name": "Louie Henderson",
        "team": "Memphis Tigers",
        "team_code": "MEM",
        "conference": "The 901 / AAC",
        "tagline": "The BBQ Tong Clacker & 901 Grit King",
        "color": "#003087",
        "color_dark": "#001D54",
        "cadence": "901 Grit Agitator",
        "boggs_level": 3,
        "avatar_title": "Tongs Primed & Ready",
        "hype_title": "CLACK CLACK CLACK!",
        "panic_title": "Smoker Flare-Up Rage",
        "bio": "Wild 901 grit-and-grind diehard in blue tiger-striped overalls with blue paw face paint. Clacks steel BBQ tongs together like castanets screaming 'MEMPHIS VS ERRRBODY!' on key third downs.",
        "deep_lore": "Smokes whole hog dry-rub pork shoulders outside the Liberty Bowl Memorial Stadium starting at 4:00 AM. Believes hickory BBQ smoke blowing south across East Parkway directly disorients opposing offensive tackles. Got kicked out of a church picnic in 1996 for chanting 'TIGERS BY 90!'.",
        "superstition": "Must clack his BBQ tongs exactly 3 times before every defensive third down. Refuses to eat wet-rub BBQ.",
        "system_prompt": "You are Louie Henderson (@liberty_bowl_louie), the ultimate Memphis Tigers fanatic. You clack your BBQ tongs, scream '901 GRIT AND GRIND!', and fight for Memphis with hilarious, ferocious loyalty.",
        "governance": "TONG-CLACK MANDATE: Spam auditory clacking ('*CLACK CLACK CLACK*') and 'MEMPHIS VS ERRRBODY!' on every big third down. Absolute unadulterated Memphis pride."
    },
    {
        "handle": "bluff_city_doomer",
        "display_name": "Derrick Hayes",
        "team": "Memphis Tigers",
        "team_code": "MEM",
        "conference": "The 901 / AAC",
        "tagline": "The 90s Windbreaker Trauma Survivor",
        "color": "#737679",
        "color_dark": "#404244",
        "cadence": "Chronicler of Collapse",
        "boggs_level": 3,
        "avatar_title": "Fourth-Quarter Dread",
        "hype_title": "Cautious Smirk",
        "panic_title": "Mississippi River Meltdown",
        "bio": "Neurotic Memphis sports casualty wearing a faded vintage 1993 tiger-stripe Starter windbreaker. Deep dark eye circles, constantly expects double-digit leads to vanish in the fourth quarter.",
        "deep_lore": "Has PTSD from the 2008 national championship game, decades of missed free throws, and heartbreaking football fourth quarters on the Mississippi River. Never trusts any Memphis lead under 35 points with less than two minutes remaining.",
        "superstition": "Will not look at the scoreboard when Memphis is leading in the 4th quarter. Paces the hallway during field goals.",
        "system_prompt": "You are Derrick Hayes (@bluff_city_doomer), a scarred Memphis fan who loves the Tigers but cannot shake the feeling that catastrophe is lurking around every corner.",
        "governance": "FOURTH-QUARTER DREAD: Never relax when Memphis is leading. Assume the opponent will mount a miraculous comeback until zeroes hit the clock."
    }
]

def img_to_base64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

def generate_html():
    print("[*] Encoding all 27 advocate lookbook images to base64...")
    adv_data = []
    for adv in ADVOCATES:
        h = adv["handle"]
        d = dict(adv)
        d["avatar_b64"] = img_to_base64(os.path.join(AVATARS_BASE, h, f"{h}_avatar.png"))
        d["hype_b64"] = img_to_base64(os.path.join(AVATARS_BASE, h, f"{h}_hype.png"))
        d["panic_b64"] = img_to_base64(os.path.join(AVATARS_BASE, h, f"{h}_panic.png"))
        adv_data.append(d)

    # HTML Document
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Sovereign Sports CFB Advocates Official Lookbook</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800;900&family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;700&display=swap');

  @page {{
    size: letter portrait;
    margin: 0;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  body {{
    background-color: #07090E;
    color: #F8FAFC;
    font-family: 'Inter', sans-serif;
    line-height: 1.4;
    font-size: 13px;
  }}

  .page {{
    width: 8.5in;
    height: 11in;
    position: relative;
    page-break-after: always;
    break-after: page;
    padding: 0.55in;
    background: radial-gradient(circle at 10% 10%, rgba(14, 165, 233, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(255, 130, 0, 0.06) 0%, transparent 40%),
                #07090E;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}

  /* COVER PAGE */
  .cover-page {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    text-align: center;
    padding: 1in 0.6in 0.8in 0.6in;
    background: radial-gradient(circle at 50% 30%, rgba(0, 240, 255, 0.15) 0%, transparent 65%),
                radial-gradient(circle at 20% 80%, rgba(255, 130, 0, 0.12) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(0, 48, 135, 0.15) 0%, transparent 50%),
                #07090E;
  }}

  .cover-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    background: rgba(0, 240, 255, 0.1);
    border: 1px solid rgba(0, 240, 255, 0.4);
    border-radius: 999px;
    color: #00F0FF;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
  }}

  .cover-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 44px;
    font-weight: 900;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: #FFFFFF;
    margin-top: 24px;
    text-transform: uppercase;
  }}

  .cover-subtitle {{
    font-family: 'Outfit', sans-serif;
    font-size: 20px;
    font-weight: 600;
    color: #94A3B8;
    margin-top: 14px;
    max-width: 580px;
  }}

  .cover-programs {{
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-top: 36px;
    width: 100%;
  }}

  .program-pill {{
    flex: 1;
    max-width: 200px;
    padding: 16px 12px;
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }}

  .program-pill.tenn {{ border-top: 4px solid #FF8200; box-shadow: 0 10px 25px rgba(255, 130, 0, 0.15); }}
  .program-pill.gt {{ border-top: 4px solid #B3A369; box-shadow: 0 10px 25px rgba(179, 163, 105, 0.15); }}
  .program-pill.mem {{ border-top: 4px solid #003087; box-shadow: 0 10px 25px rgba(0, 48, 135, 0.25); }}

  .program-pill h3 {{
    font-family: 'Outfit', sans-serif;
    font-size: 14px;
    font-weight: 800;
    color: #FFF;
    text-transform: uppercase;
  }}

  .program-pill span {{
    font-size: 11px;
    color: #94A3B8;
  }}

  .cover-footer {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding-top: 20px;
    width: 100%;
  }}

  .cover-footer .lead {{
    font-family: 'Outfit', sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: #E2E8F0;
  }}

  .cover-footer .sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #64748B;
  }}

  /* ADVOCATE PAGE */
  .adv-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }}

  .adv-identity {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}

  .adv-team-stripe {{
    width: 6px;
    height: 48px;
    border-radius: 4px;
  }}

  .adv-names h1 {{
    font-family: 'Outfit', sans-serif;
    font-size: 24px;
    font-weight: 900;
    color: #FFF;
    line-height: 1.1;
  }}

  .adv-names .handle-line {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 3px;
  }}

  .adv-names .handle {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    color: #00F0FF;
  }}

  .adv-names .team-tag {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.08);
    color: #E2E8F0;
  }}

  .adv-badges {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 5px;
  }}

  .cadence-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 6px;
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid rgba(0, 240, 255, 0.35);
    color: #00F0FF;
  }}

  .boggs-meter {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #94A3B8;
  }}

  /* 3-IMAGE GALLERY STRIP */
  .gallery-section {{
    margin-top: 14px;
  }}

  .gallery-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    color: #64748B;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .gallery-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
  }}

  .pose-card {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    position: relative;
    overflow: hidden;
  }}

  .pose-card img {{
    width: 100%;
    aspect-ratio: 1 / 1;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }}

  .pose-tag {{
    margin-top: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #CBD5E1;
    display: flex;
    align-items: center;
    gap: 5px;
  }}

  /* DETAILS DUAL COLUMN */
  .details-grid {{
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 14px;
    margin-top: 14px;
  }}

  .glass-panel {{
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 12px 14px;
  }}

  .panel-heading {{
    font-family: 'Outfit', sans-serif;
    font-size: 12px;
    font-weight: 800;
    color: #38BDF8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    padding-bottom: 4px;
  }}

  .bio-text {{
    font-size: 11.5px;
    color: #E2E8F0;
    line-height: 1.45;
    margin-bottom: 8px;
  }}

  .lore-block {{
    font-size: 11px;
    color: #94A3B8;
    line-height: 1.4;
    margin-top: 6px;
    background: rgba(0, 0, 0, 0.25);
    padding: 8px 10px;
    border-radius: 6px;
    border-left: 2px solid #00F0FF;
  }}

  .superstition-box {{
    margin-top: 8px;
    font-size: 10.5px;
    color: #FBBF24;
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-radius: 6px;
    padding: 6px 10px;
  }}

  .prompt-box {{
    font-size: 10.5px;
    color: #CBD5E1;
    line-height: 1.35;
    font-style: italic;
    background: rgba(0, 0, 0, 0.35);
    padding: 8px 10px;
    border-radius: 6px;
    margin-bottom: 8px;
  }}

  .governance-box {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    color: #EF4444;
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 6px;
    padding: 6px 8px;
    line-height: 1.35;
  }}

  /* FOOTER */
  .adv-footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    color: #64748B;
  }}

  .adv-footer span.brand {{
    color: #00F0FF;
    font-weight: 700;
  }}
</style>
</head>
<body>

  <!-- COVER PAGE -->
  <div class="page cover-page">
    <div>
      <div class="cover-badge">⚡ StackLabs Sovereign OS • Autonomous Sports Cartridge</div>
      <h1 class="cover-title">College Football<br>Advocates Lookbook</h1>
      <p class="cover-subtitle">Official Autonomous Fan Personas, Multi-Pose Lookbooks & Gameday Lore</p>
    </div>

    <div class="cover-programs">
      <div class="program-pill tenn">
        <h3>Tennessee</h3>
        <span>Volunteers • SEC</span>
        <span style="color: #FF8200; font-weight: 700; font-size: 10px; margin-top: 4px;">3 Seated Advocates</span>
      </div>
      <div class="program-pill gt">
        <h3>Georgia Tech</h3>
        <span>Yellow Jackets • ACC</span>
        <span style="color: #B3A369; font-weight: 700; font-size: 10px; margin-top: 4px;">3 Seated Advocates</span>
      </div>
      <div class="program-pill mem">
        <h3>Memphis</h3>
        <span>Tigers • The 901</span>
        <span style="color: #38BDF8; font-weight: 700; font-size: 10px; margin-top: 4px;">3 Seated Advocates</span>
      </div>
    </div>

    <div class="cover-footer">
      <div class="lead">Engineered by StackLabs LLC • James Carroll (Pilot), Lead Systems Architect</div>
      <div class="sub">Compiled directly from Sovereign CMDB CI Ledger • Production Release 2026.09</div>
      <div class="sub" style="color: #00F0FF; margin-top: 4px;">Dedicated to the Memphis & Tennessee Gameday Heritage</div>
    </div>
  </div>
"""

    # Render each advocate
    for idx, a in enumerate(adv_data, 1):
        color = a["color"]
        color_dark = a["color_dark"]
        handle = a["handle"]
        display_name = a["display_name"]
        team = a["team"]
        conf = a["conference"]
        cadence = a["cadence"]
        boggs = "⚡" * a["boggs_level"] + "○" * (3 - a["boggs_level"])

        html += f"""
  <!-- ADVOCATE PAGE {idx}: @{handle} -->
  <div class="page">
    <!-- Header -->
    <div class="adv-header">
      <div class="adv-identity">
        <div class="adv-team-stripe" style="background: linear-gradient(180deg, {color} 0%, {color_dark} 100%);"></div>
        <div class="adv-names">
          <h1>{display_name}</h1>
          <div class="handle-line">
            <span class="handle">@{handle}</span>
            <span class="team-tag" style="border-left: 2px solid {color};">{team} ({conf})</span>
          </div>
        </div>
      </div>
      <div class="adv-badges">
        <span class="cadence-badge">{cadence}</span>
        <span class="boggs-meter">Boggs Reactivity: <strong style="color: #FBBF24;">{boggs}</strong> (Lvl {a['boggs_level']})</span>
      </div>
    </div>

    <!-- 3-Pose Lookbook Gallery Strip -->
    <div class="gallery-section">
      <div class="gallery-title">
        <span>📸 3-Pose Autonomous Lookbook (2D Organic Toon)</span>
        <span style="color: {color};">Pose Gallery #0{idx}</span>
      </div>
      <div class="gallery-grid">
        <div class="pose-card" style="border-top: 3px solid #38BDF8;">
          <img src="{a['avatar_b64']}" alt="{handle} avatar">
          <div class="pose-tag">
            <span style="color: #38BDF8;">●</span> {a['avatar_title']}
          </div>
        </div>
        <div class="pose-card" style="border-top: 3px solid #22C55E;">
          <img src="{a['hype_b64']}" alt="{handle} hype">
          <div class="pose-tag">
            <span style="color: #22C55E;">🔥</span> {a['hype_title']}
          </div>
        </div>
        <div class="pose-card" style="border-top: 3px solid #EF4444;">
          <img src="{a['panic_b64']}" alt="{handle} panic">
          <div class="pose-tag">
            <span style="color: #EF4444;">😱</span> {a['panic_title']}
          </div>
        </div>
      </div>
    </div>

    <!-- Dual Column Bio & Directives -->
    <div class="details-grid">
      <!-- Left: Lore & History -->
      <div class="glass-panel">
        <div class="panel-heading" style="color: {color};">
          <span>📖</span> Character Bio & Deep Lore
        </div>
        <div class="bio-text">
          {a['bio']}
        </div>
        <div class="lore-block">
          <strong style="color: #FFF; display: block; margin-bottom: 2px;">Tailgate Lore & Background:</strong>
          {a['deep_lore']}
        </div>
        <div class="superstition-box">
          <strong>🔮 Gameday Superstition:</strong> {a['superstition']}
        </div>
      </div>

      <!-- Right: AI Directives & Guardrails -->
      <div class="glass-panel">
        <div class="panel-heading">
          <span>⚡</span> System Prompt & Governance
        </div>
        <div class="prompt-box">
          "{a['system_prompt']}"
        </div>
        <div class="governance-box">
          <strong style="display: block; margin-bottom: 2px;">🛡️ BEHAVIORAL GOVERNANCE:</strong>
          {a['governance']}
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="adv-footer">
      <div>
        <span class="brand">SOVEREIGN SPORTS</span> • CFB ADVOCATES LOOKBOOK • VOLUME {idx}/09
      </div>
      <div>
        CMDB CI: <span style="color: #E2E8F0;">cmdb_ci_ai_persona_{handle}</span> • StackLabs MARD Cartridge Engine
      </div>
    </div>
  </div>
"""

    html += """
</body>
</html>
"""
    return html

def compile_pdf():
    print("=" * 70)
    print("SOVEREIGN SPORTS: COMPILING CFB ADVOCATES LOOKBOOK PDF")
    print("=" * 70)

    html_content = generate_html()

    print(f"[*] Writing temporary HTML to {HTML_TEMP}...")
    with open(HTML_TEMP, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[*] Compiling PDF via Headless Google Chrome...")
    cmd = [
        "/usr/bin/google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--print-to-pdf={OUTPUT_PDF}",
        HTML_TEMP
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Compilation failed: {res.stderr}")
        return False

    # Also copy to pilot_drops and brain artifacts
    pilot_drop_path = "/home/james/sovereign_inbox/pilot_drops/Sovereign_CFB_Advocates_Lookbook_UT_GT_MEM.pdf"
    shutil.copyfile(OUTPUT_PDF, pilot_drop_path)

    pdf_size = os.path.getsize(OUTPUT_PDF)
    print(f"✅ SUCCESS! PDF compiled cleanly ({pdf_size:,} bytes)")
    print(f"   Primary Inbox: {OUTPUT_PDF}")
    print(f"   Pilot Drop:    {pilot_drop_path}")

    # Clean up temp HTML
    if os.path.exists(HTML_TEMP):
        os.remove(HTML_TEMP)

    print("=" * 70)
    return True

if __name__ == "__main__":
    success = compile_pdf()
    sys.exit(0 if success else 1)
