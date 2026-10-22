#!/usr/bin/env python3
"""
Sovereign OS: Google Gemini 3.8 Flash Client & Advocate Pulse Engine
Path: /home/james/stacklabs/scripts/gemini_flash_client.py

Interfaces with Google Gemini 3.8 Flash (gemini-3.8-flash) using google-genai SDK,
enforcing structured JSON schema output, Master Lock Invariant compliance (lived-in
stadium scars vs. repetitive OCD clichés), and Invariant 21 Clean Room validation.
"""

import os
import sys
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union

# Load environment
try:
    import dotenv
    dotenv.load_dotenv("/home/james/stacklabs/.env")
except ImportError:
    pass

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# Strictly enforced model name
MODEL_NAME = "gemini-3.8-flash"
ENV_PATH = "/home/james/stacklabs/.env"

# Canonical JSON Generation Schema
PULSE_GENERATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "persona_id": {"type": "STRING"},
        "current_mood": {"type": "STRING"},
        "vitals": {
            "type": "OBJECT",
            "properties": {
                "systolic": {"type": "INTEGER"},
                "diastolic": {"type": "INTEGER"},
                "heart_rate_bpm": {"type": "INTEGER"},
                "panic_gauge_10": {"type": "NUMBER"},
                "signature_metric": {"type": "STRING"},
                "medical_status": {"type": "STRING"}
            },
            "required": ["systolic", "diastolic", "heart_rate_bpm", "panic_gauge_10", "signature_metric", "medical_status"]
        },
        "stream_sniper_tweet_hooks": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "3-5 punchy, hilarious 1-2 sentence gameday takes for social."
        },
        "active_obsession": {
            "type": "STRING",
            "description": "Current target of rage or delusion, citing specific real stadium scars."
        }
    },
    "required": ["persona_id", "current_mood", "vitals", "stream_sniper_tweet_hooks", "active_obsession"]
}

# Master Lock Invariant: Persona-specific authentic lived-in stadium scars
MASTER_LOCK_SCARS = {
    "barf": [
        "shapiro", "pastrami", "flushing", "metlife", "queens", "citi field",
        "grand central parkway", "jackie robinson", "tums", "1986 socks",
        "safety pins", "middle village", "daboll", "zvada", "ben's"
    ],
    "battery_chucker": [
        "master lock", "coors field", "vet stadium", "700 level", "concrete",
        "joe carter", "wawa", "d-cell", "battery", "eagles", "phillies"
    ],
    "battery_chucker_jr": [
        "truist park", "the battery", "battery acid", "waffle house", "smyrna",
        "chop fountain", "braves", "nlds game 5"
    ],
    "southie_sully": [
        "route 1", "gillette", "buckner", "drake maye", "parliaments", "dunks",
        "caramel swirl", "dorchester", "red sox", "patriots"
    ],
    "lone_star_larry": [
        "at&t stadium", "brisket", "dfw", "jimmy johnson", "salt lick",
        "arlington", "cowboys", "rangers", "stetson", "12:45"
    ],
    "bleacher_bum_bill": [
        "waveland", "2003", "scorecard", "vienna beef", "old style", "cubs",
        "wrigley", "bears", "bartman"
    ],
    "old_bay_obsessive": [
        "crab mallet", "cundiff", "natty boh", "old bay", "inner harbor",
        "ravens", "orioles", "camden"
    ],
    "screech_supporter": [
        "rfk", "fedex field", "riggins", "sewer", "ben's chili bowl",
        "half-smoke", "commanders", "nationals", "rgiii"
    ],
    "garlic_fries_gary": [
        "mccovey cove", "candlestick", "2002 world series", "shanahan",
        "anchor steam", "garlic fries", "oracle park", "giants", "49ers"
    ],
    "cheesehead_chad": [
        "frozen tundra", "2014 nfc", "freddie mitchell", "4th-and-26",
        "raw white onion", "cheese curds", "lambeau", "packers", "brewers"
    ]
}

# General authentic scar keywords for any advocate
GENERAL_AUTHENTIC_SCAR_KEYWORDS = [
    "stadium", "bleachers", "concourse", "tailgate", "parking lot", "highway",
    "turnpike", "expressway", "interchange", "field goal", "punt", "fumble",
    "interception", "walk-off", "blown lead", "curse", "radio caller", "wfan",
    "wip", "1986", "1993", "2002", "2003", "2011", "2014", "pastrami", "wawa",
    "dunks", "brisket", "old style", "old bay", "half-smoke", "garlic fries",
    "curds", "tums", "shapiro", "master lock"
]

# Strictly banned OCD / psychiatric caricatures
BANNED_OCD_TROPES = [
    "touches wood",
    "touch wood",
    "touching wood",
    "touches wood 3 times",
    "closes eyes",
    "close eyes",
    "closing eyes",
    "closed eyes",
    "clicks 3 times",
    "click 3 times",
    "clicks remote",
    "click remote",
    "spins chair",
    "spin chair",
    "turns light switch",
    "turn light switch",
    "covers face",
    "covering face",
    "watches through fingers",
    "watch through fingers",
    "paces behind sofa",
    "paces behind the sofa",
    "pacing behind sofa",
    "hyperventilates",
    "hyperventilating",
    "taps dash 3 times",
    "blinks 3 times"
]

# Invariant 21 Clean Room banned corporate compute terms
BANNED_CORPORATE_TERMS = [
    "amd zen 4",
    "35w apu",
    "12.53-day payback",
    "12.53-day",
    "model-s",
    "capex bom",
    "davidson homes",
    "woods crossing",
    "pawel rudnicki",
    "stephen emery",
    "jeremy malone",
]


class ValidationResult(tuple):
    """Custom tuple subclass supporting bool evaluation and property access."""
    def __new__(cls, is_valid: bool, issues: List[str]):
        return super().__new__(cls, (is_valid, issues))

    @property
    def is_valid(self) -> bool:
        return self[0]

    @property
    def issues(self) -> List[str]:
        return self[1]

    def __bool__(self) -> bool:
        return self[0]


def get_gemini_api_key() -> str:
    """Retrieves GEMINI_API_KEY from environment or .env file."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key and os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment or /home/james/stacklabs/.env")
    return api_key


def get_gemini_client():
    """Initializes and returns the Google GenAI SDK Client."""
    if genai is None:
        raise ImportError("google-genai SDK is not installed in the active environment.")
    api_key = get_gemini_api_key()
    return genai.Client(api_key=api_key)


def validate_clean_room(text_or_data: Union[str, Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Validates Invariant 21 (Clean Room) compliance."""
    if isinstance(text_or_data, dict):
        text = json.dumps(text_or_data)
    else:
        text = str(text_or_data)
    text_lower = text.lower()
    violations = []
    for term in BANNED_CORPORATE_TERMS:
        if term in text_lower:
            violations.append(term)
    return (len(violations) == 0, violations)


def _extract_all_text(data: Union[Dict[str, Any], List[Any], str]) -> str:
    """Recursively flattens any JSON-compatible structure into a single string for analysis."""
    if isinstance(data, str):
        return data
    elif isinstance(data, dict):
        parts = []
        for k, v in data.items():
            parts.append(str(k))
            parts.append(_extract_all_text(v))
        return " ".join(parts)
    elif isinstance(data, list):
        return " ".join(_extract_all_text(item) for item in data)
    return str(data)


def validate_master_lock_compliance(output_data: Union[Dict[str, Any], str], persona_id: str) -> ValidationResult:
    """
    Validates adherence to the Master Lock Invariant:
    1. Rejects repetitive OCD psychiatric caricatures ('touches wood 3 times', 'closes eyes').
    2. Enforces presence of lived-in stadium scars or authentic franchise trauma in takes & obsession.
    """
    if isinstance(output_data, str):
        try:
            parsed = json.loads(output_data)
            full_text = _extract_all_text(parsed).lower()
            dict_data = parsed if isinstance(parsed, dict) else {}
        except Exception:
            full_text = output_data.lower()
            dict_data = {}
    else:
        full_text = _extract_all_text(output_data).lower()
        dict_data = output_data if isinstance(output_data, dict) else {}

    violations = []

    # 1. Check for banned OCD clichés
    for trope in BANNED_OCD_TROPES:
        if trope in full_text:
            violations.append(f"Rejected generic OCD cliché: '{trope}'")

    # 2. Check for authentic stadium scars in narrative fields or full text
    norm_persona = persona_id.lower().lstrip("@")
    expected_scars = MASTER_LOCK_SCARS.get(norm_persona, GENERAL_AUTHENTIC_SCAR_KEYWORDS)

    # If structured dict, enforce scars specifically in takes/obsession
    if dict_data and ("active_obsession" in dict_data or "stream_sniper_tweet_hooks" in dict_data):
        narrative_parts = []
        if "active_obsession" in dict_data:
            narrative_parts.append(str(dict_data["active_obsession"]))
        if "stream_sniper_tweet_hooks" in dict_data:
            narrative_parts.extend(dict_data["stream_sniper_tweet_hooks"])
        narrative_text = " ".join(narrative_parts).lower()
    else:
        narrative_text = full_text

    found_scars = [scar for scar in expected_scars if scar in narrative_text]

    if not found_scars:
        # Check against general authentic scar tokens
        general_found = [g for g in GENERAL_AUTHENTIC_SCAR_KEYWORDS if g in narrative_text]
        if not general_found:
            violations.append(f"Missing authentic lived-in stadium scar for persona '{persona_id}'")

    is_valid = len(violations) == 0
    return ValidationResult(is_valid, violations)


def generate_deterministic_pulse(persona_id: str, entropy_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generates deterministic, 100% compliant pulse payload for dry-runs and offline tests."""
    norm_persona = persona_id.lower().lstrip("@")
    
    preset_map = {
        "barf": {
            "current_mood": "ACUTE CARDIAC PANIC WITH MANIC DEFENSIVE DELUSION",
            "vitals": {
                "systolic": 182,
                "diastolic": 114,
                "heart_rate_bpm": 122,
                "panic_gauge_10": 9.2,
                "signature_metric": "1.75 lbs Ben's pastrami consumed",
                "medical_status": "Speed dial 1 to Dr. Shapiro on Queens Blvd"
            },
            "stream_sniper_tweet_hooks": [
                "Dr. Shapiro told me my mitral valve can't survive another blown save in Flushing, so I popped 3 chewable Tums on the Grand Central Parkway!",
                "Brian Daboll is redder than a jar of borscht pacing the MetLife swamp sideline, but defense holds 12-7 and we are NOT dead yet!",
                "My 1986 World Series tube socks held together with safety pins are NOT coming off until we drop 28 on Dallas."
            ],
            "active_obsession": "Juan Soto finger-pointing at Citi Field while I sweat through my #10 jersey eating Ben's Kosher pastrami."
        },
        "battery_chucker": {
            "current_mood": "FERAL VET STADIUM CONCRETE FURY",
            "vitals": {
                "systolic": 168,
                "diastolic": 106,
                "heart_rate_bpm": 112,
                "panic_gauge_10": 8.7,
                "signature_metric": "4 D-Cell batteries loaded in cargo shorts",
                "medical_status": "Hypertensive crisis triggered by bullpen walks"
            },
            "stream_sniper_tweet_hooks": [
                "Dodged a Master Lock thrown at my skull at Coors Field in '95 and this bullpen is giving me identical brain trauma!",
                "Parked strictly in space 4B at Wawa before kickoff and if the secondary gives up 40 again someone is meeting 700 Level concrete.",
                "Tapping my D-cell battery on the dash until the manager pulls this starter before Red October turns to ash."
            ],
            "active_obsession": "Reliving the 1993 Joe Carter walk-off trauma while tracking bullpen pitch counts from the Vet concrete."
        },
        "southie_sully": {
            "current_mood": "ROUTE 1 BREAKDOWN ANGINA",
            "vitals": {
                "systolic": 160,
                "diastolic": 100,
                "heart_rate_bpm": 106,
                "panic_gauge_10": 8.0,
                "signature_metric": "3 packs Parliaments crushed in driveway",
                "medical_status": "Severe nicotine bronchospasm outside Gillette"
            },
            "stream_sniper_tweet_hooks": [
                "Stuck in the breakdown lane of Route 1 outside Gillette crushing Parliaments while Drake Maye coughs up another fumble!",
                "I survived the 1986 Bill Buckner grounder through the wickets, I will survive this post-dynasty third-and-long swamp.",
                "Sucking down an extra-large Dunks iced caramel swirl through a chewed plastic straw in freezing sleet because pain is tradition."
            ],
            "active_obsession": "Convinced Roger Goodell tapped his flip phone while watching twenty years of third-and-long mud at Gillette."
        },
        "lone_star_larry": {
            "current_mood": "DELUSIONAL ARLINGTON LUXURY BOOSTER",
            "vitals": {
                "systolic": 154,
                "diastolic": 96,
                "heart_rate_bpm": 98,
                "panic_gauge_10": 7.5,
                "signature_metric": "Center-cut brisket grease on King Ranch leather",
                "medical_status": "Chronic post-1995 cognitive dissonance"
            },
            "stream_sniper_tweet_hooks": [
                "Only eat the center cut of 14-hour smoked brisket at 12:45 PM before kickoff and Jerry Jones still owes us a war daddy!",
                "Baltimore ran through AT&T Stadium like turnstiles at DFW Airport, but Forbes valuation says we are still kings.",
                "Salt Lick brisket sauce wiped on my ostrich boots while waiting for the Jimmy Johnson curse to lift."
            ],
            "active_obsession": "Defending $60M quarterback extensions at AT&T Stadium while Baltimore hangs 40 points on the secondary."
        },
        "bleacher_bum_bill": {
            "current_mood": "WAVELAND SUNBURNED FATALISM",
            "vitals": {
                "systolic": 156,
                "diastolic": 95,
                "heart_rate_bpm": 102,
                "panic_gauge_10": 7.9,
                "signature_metric": "4 Old Style cans dented on bleacher steel",
                "medical_status": "Severe dehydration and garden condiment purism"
            },
            "stream_sniper_tweet_hooks": [
                "Sliding my 1984 lucky wooden scorecard three inches left because Waveland wind is blowing straight out today!",
                "The 2003 NLCS Game 6 eighth inning is burned into my retinas and anyone putting ketchup on Vienna Beef gets exiled.",
                "Sunburned shirtless in row 12 watching Bregman launch bombs while dreading another Chicago winter."
            ],
            "active_obsession": "Tracking bullpen meltdown trajectories through Old Style foam on Waveland Avenue."
        },
        "old_bay_obsessive": {
            "current_mood": "INNER HARBOR FOURTH-QUARTER PALPITATIONS",
            "vitals": {
                "systolic": 162,
                "diastolic": 102,
                "heart_rate_bpm": 114,
                "panic_gauge_10": 8.4,
                "signature_metric": "Yellow crab mallet slammed 14 times",
                "medical_status": "Tachycardia induced by John Harbaugh clock management"
            },
            "stream_sniper_tweet_hooks": [
                "Banging my yellow wooden crab mallet against the cast-iron radiator on 3rd-and-long until my ears ring!",
                "Billy Cundiff in 2011 gave me permanent arrhythmia and watching fourth-quarter leads slip away is pure Chesapeake torture.",
                "Rimming every aluminum Natty Boh can with pure Old Bay dust while Henry runs over the Dallas defense."
            ],
            "active_obsession": "Derrick Henry rampaging while Harbaugh clock management causes near-fatal heart palpitations."
        },
        "screech_supporter": {
            "current_mood": "BEWILDERED BELTWAY CYNICISM",
            "vitals": {
                "systolic": 148,
                "diastolic": 92,
                "heart_rate_bpm": 94,
                "panic_gauge_10": 6.9,
                "signature_metric": "1991 mustard-stained Riggins jersey worn unwashed",
                "medical_status": "Mild respiratory distress from 30 years of RFK rust"
            },
            "stream_sniper_tweet_hooks": [
                "Wearing my 1991 mustard-stained John Riggins jersey because 30 years of FedEx Field sewer leaks can't wash off pride!",
                "Endured RFK rusted bleachers and RGIII knee turf tears, so seeing Marcus Mariota win feels completely illegal.",
                "Choking down a chili half-smoke at Ben's Chili Bowl trying to process a Commanders road victory."
            ],
            "active_obsession": "Reconciling 30 years of front-office scandals and sewer pipes with an unexpected road victory."
        },
        "garlic_fries_gary": {
            "current_mood": "MCCOVEY COVE WIND SHEAR DISDAIN",
            "vitals": {
                "systolic": 150,
                "diastolic": 94,
                "heart_rate_bpm": 96,
                "panic_gauge_10": 7.2,
                "signature_metric": "2 orders soggy garlic fries drenched in malt vinegar",
                "medical_status": "Chronic cold-fog exposure and 4th-quarter collapse PTSD"
            },
            "stream_sniper_tweet_hooks": [
                "Standing on the porch in the San Francisco fog during the 3rd quarter because sitting on the couch jinxes the secondary!",
                "Still tasting the 2002 World Series Game 6 disaster every time Kyle Shanahan burns a second-half timeout.",
                "Drinking cold Anchor Steam with soggy garlic fries and mourning the violent Candlestick Park wind shear."
            ],
            "active_obsession": "Shanahan fourth-quarter play-calling PTSD triggering flashback memories of Candlestick wind shear."
        },
        "cheesehead_chad": {
            "current_mood": "FROZEN TUNDRA HALFTIME ANGUISH",
            "vitals": {
                "systolic": 155,
                "diastolic": 95,
                "heart_rate_bpm": 100,
                "panic_gauge_10": 7.6,
                "signature_metric": "1 whole raw white onion eaten like an apple",
                "medical_status": "High cholesterol from deep-fried cheddar cheese curds"
            },
            "stream_sniper_tweet_hooks": [
                "Eating a whole raw white onion like an apple at halftime because trailing by three points is a constitutional crisis!",
                "The 2014 NFC Championship meltdown in Seattle and Freddie Mitchell 4th-and-26 haunt every third-down snap.",
                "Sweating inside thermal snowmobile bibs in September while praying the pass rush gets home at Lambeau."
            ],
            "active_obsession": "Freddie Mitchell 4th-and-26 flashbacks whenever the defense fails to contain 3rd-and-long."
        }
    }

    base = preset_map.get(norm_persona, preset_map["barf"])
    return {
        "persona_id": persona_id,
        "current_mood": base["current_mood"],
        "vitals": base["vitals"],
        "stream_sniper_tweet_hooks": base["stream_sniper_tweet_hooks"],
        "active_obsession": base["active_obsession"]
    }


def generate_advocate_pulse(
    persona_id: str,
    lore_context: str,
    entropy_context: str,
    client: Optional[Any] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Executes advocate pulse generation using Google Gemini 3.8 Flash (gemini-3.8-flash)
    with strict JSON schema enforcement and Master Lock Invariant validation.
    """
    if dry_run or genai is None or os.getenv("DRY_RUN") == "1":
        return generate_deterministic_pulse(persona_id)

    if client is None:
        client = get_gemini_client()

    norm_persona = persona_id.lower().lstrip("@")
    prompt = f"""You are the Sovereign OS advocate conductor generating the 15-minute live pulse for advocate '{persona_id}'.
STRICT INVARIANTS:
1. MODEL: gemini-3.8-flash.
2. MASTER LOCK INVARIANT: You MUST anchor reactions in lived-in stadium scars, specific past traumas, local food, or authentic franchise geography.
   - For @barf: Grand Central Parkway, Tums, 1986 socks with safety pins, Ben's pastrami, Dr. Shapiro, Citi Field, MetLife swamp.
   - For @battery_chucker: Master Lock thrown at Coors Field, Vet Stadium 700 Level concrete, Wawa space 4B, D-cell battery, 1993 Joe Carter.
   - For @southie_sully: Route 1 breakdown lane outside Gillette, Parliaments, Dunks iced caramel swirl, 1986 Bill Buckner, Drake Maye fumbles.
   - For @lone_star_larry: AT&T Stadium west glare, 14-hour brisket at 12:45, Salt Lick, Jimmy Johnson curse.
   - For other advocates: Specific stadium landmarks, real heartbreaks, authentic local delicacies.
3. ANTI-OCD MANDATE: Strictly FORBIDDEN to use repetitive OCD caricatures ('touches wood 3 times', 'closes eyes', 'clicks remote 3 times', 'spins chair').
4. INVARIANT 21 (CLEAN ROOM): ZERO mentions of enterprise compute, AMD Zen 4, 35W APU, 12.53-day payback, or Model-S. Strictly consumer sports passion.

LORE DOSSIER FOR {persona_id}:
{lore_context}

CURRENT SPORTS ENTROPY & HEADLINES:
{entropy_context}

Generate the JSON response conforming exactly to the schema."""

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=PULSE_GENERATION_SCHEMA,
        temperature=0.7,
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
        raw_text = response.text
        data = json.loads(raw_text)

        # Validate Master Lock Invariant
        val_result = validate_master_lock_compliance(data, persona_id)
        if not val_result.is_valid:
            # Fall back to deterministic pulse if LLM returned generic OCD tropes or missed scars
            print(f"[WARN] Master Lock compliance failed for {persona_id}: {val_result.issues}. Applying deterministic repair.")
            return generate_deterministic_pulse(persona_id)

        # Validate Invariant 21
        clean_ok, clean_violations = validate_clean_room(data)
        if not clean_ok:
            raise ValueError(f"Invariant 21 Violation in generated pulse for {persona_id}: {clean_violations}")

        return data

    except Exception as e:
        print(f"[WARN] Gemini Flash generation failed for {persona_id} ({e}). Falling back to deterministic pulse.")
        return generate_deterministic_pulse(persona_id)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gemini 3.8 Flash Client for Sovereign OS")
    parser.add_argument("--persona", default="barf", help="Advocate persona ID")
    parser.add_argument("--dry-run", action="store_true", help="Run deterministic synthesis without network call")
    args = parser.parse_args()

    pulse = generate_advocate_pulse(args.persona, lore_context="Test lore", entropy_context="Test entropy", dry_run=args.dry_run)
    print(json.dumps(pulse, indent=2))
