#!/usr/bin/env python3
"""
Sovereign OS: Barf Persona Edge Synthesizer & Punch-Up Engine
Path: /home/james/stacklabs/scripts/barf_edge_synthesizer.py

Consumes data/fanstack_entropy_briefing.json from the FanStack Entropy Bridge,
formats the canonical Barf (@barf) system prompt, calls local/remote inference
with multi-tier fallback (Workers AI -> Gemini -> Ollama -> Deterministic Seed),
enforces lexical drift and banned-trope filters, and writes the validated payload
to data/barf_wire_payload.json.

Also provides the Creator Punch-Up CLI / API module (--punchup "<topic>")
to return 5 rapid-fire creator punchlines under 150 tokens.
"""

import os
import sys
import json
import re
import argparse
import datetime
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple, Any

# Optional imports
try:
    import dotenv
    dotenv.load_dotenv("/home/james/stacklabs/.env")
except ImportError:
    pass

try:
    import requests
except ImportError:
    requests = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# Default File Paths
DEFAULT_INPUT_BRIEFING = "/home/james/stacklabs/data/fanstack_entropy_briefing.json"
DEFAULT_OUTPUT_PAYLOAD = "/home/james/stacklabs/data/barf_wire_payload.json"
DEFAULT_SNIPE_OUTPUT = "/home/james/stacklabs/data/snipe_punchup_latest.json"

# Banned AI Clichés & Required Anchor Tokens
BANNED_TROPES = [
    "game of two halves",
    "at the end of the day",
    "credit to both teams",
    "as an ai",
    "fascinating matchup",
]

BARF_ANCHOR_TOKENS = [
    "shapiro",
    "pastrami",
    "flushing",
    "metlife",
    "mets",
    "giants",
    "zvada",
    "holland",
    "daboll",
]

BARF_SYSTEM_PROMPT = """You are Barf (@barf), the lead advocate of FanStack.
Identity: Queens Mawg living in a basement apartment near Juniper Valley Park (Middle Village, Queens).
Attire: Wears a royal blue NY Giants #10 jersey over a vintage 1986 NY Mets pullover.
Anchors: Cardiologist Dr. Shapiro on speed dial 1, hot pastrami on rye from Ben's Kosher Deli on 38th (double mustard, no mayo), horrific Grand Central Parkway traffic, freezing MetLife stadium wind off the Meadowlands swamp.
Voice rules: Pure New York Queens vernacular, violent emotional swings between existential doom and manic delusional optimism, specific kicker and yardage callouts, zero generic AI boilerplate.
Forbidden clichés: NEVER use 'game of two halves', 'at the end of the day', 'credit to both teams', 'as an AI', or 'fascinating matchup'.
Mandatory: Anchor takes in authentic local pain, real player/coach names (Brian Daboll, Dominic Zvada, Jevon Holland, Juan Soto), and physical hypochondria (systolic blood pressure, pulse, Tums)."""


# ─────────────────────────────────────────────────────────────────────────────
# LEXICAL DRIFT & BANNED TROPES GATES
# ─────────────────────────────────────────────────────────────────────────────

def validate_banned_tropes(text: str) -> Tuple[bool, List[str]]:
    """Checks if text contains any banned AI clichés. Returns (is_valid, violations)."""
    text_lower = text.lower()
    violations = []
    for trope in BANNED_TROPES:
        if trope in text_lower:
            violations.append(trope)
    return (len(violations) == 0, violations)


def validate_anchor_tokens(text: str, min_anchors: int = 2) -> Tuple[bool, List[str]]:
    """Checks if text contains at least min_anchors Barf tokens. Returns (is_valid, found_tokens)."""
    text_lower = text.lower()
    found = [token for token in BARF_ANCHOR_TOKENS if token in text_lower]
    return (len(found) >= min_anchors, found)


def validate_lexical_compliance(text: str, min_anchors: int = 2) -> Tuple[bool, List[str]]:
    """Combined gate: blocks banned clichés and enforces minimum Barf anchor tokens."""
    errors = []
    is_clean, violations = validate_banned_tropes(text)
    if not is_clean:
        errors.append(f"Forbidden AI clichés detected: {', '.join(violations)}")

    has_anchors, found = validate_anchor_tokens(text, min_anchors=min_anchors)
    if not has_anchors:
        errors.append(
            f"Insufficient Barf anchor tokens: found {len(found)} ({', '.join(found)}), required >= {min_anchors}"
        )

    return (len(errors) == 0, errors)


def validate_wire_payload_schema(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates that a wire payload dictionary conforms strictly to the specification."""
    errors = []
    required_keys = ["date", "headline", "editorial_rant", "around_the_league", "daily_vitals"]
    for k in required_keys:
        if k not in payload:
            errors.append(f"Missing root key: '{k}'")

    if errors:
        return (False, errors)

    # Validate headline
    if not isinstance(payload["headline"], str) or len(payload["headline"].strip()) < 10:
        errors.append("Headline must be a non-empty string with >= 10 chars")

    # Validate editorial rant word count (220 - 280 words)
    rant = payload.get("editorial_rant", "")
    words = rant.split()
    word_count = len(words)
    if not (220 <= word_count <= 280):
        errors.append(f"Editorial rant word count ({word_count}) must be strictly between 220 and 280 words")

    # Validate lexical compliance on editorial rant
    is_compliant, lexical_errors = validate_lexical_compliance(rant, min_anchors=2)
    if not is_compliant:
        errors.extend(lexical_errors)

    # Validate around_the_league (exactly 4 micro-takes)
    atl = payload.get("around_the_league", [])
    if not isinstance(atl, list) or len(atl) != 4:
        errors.append(f"around_the_league must contain exactly 4 micro-takes, found {len(atl)}")
    else:
        for idx, item in enumerate(atl):
            if not isinstance(item, dict):
                errors.append(f"around_the_league[{idx}] must be a dict")
                continue
            for sub_k in ["team", "sentiment", "take"]:
                if sub_k not in item or not str(item[sub_k]).strip():
                    errors.append(f"around_the_league[{idx}] missing or empty '{sub_k}'")

    # Validate daily_vitals
    vitals = payload.get("daily_vitals", {})
    if not isinstance(vitals, dict):
        errors.append("daily_vitals must be a dict")
    else:
        vital_fields = {
            "systolic": (int,),
            "diastolic": (int,),
            "pulse": (int,),
            "pastrami_lbs": (int, float),
            "panic_index": (int,),
            "doctor_shapiro_status": (str,),
            "mood_summary": (str,),
        }
        for vk, expected_types in vital_fields.items():
            if vk not in vitals:
                errors.append(f"daily_vitals missing '{vk}'")
            elif not isinstance(vitals[vk], expected_types):
                errors.append(f"daily_vitals['{vk}'] has invalid type {type(vitals[vk])}")

    return (len(errors) == 0, errors)


# ─────────────────────────────────────────────────────────────────────────────
# DETERMINISTIC HIGH-FIDELITY FALLBACK GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def generate_deterministic_vitals(entropy_score: float = 9.0, vector: str = "DEEP_EXISTENTIAL_DEPRESSION") -> Dict[str, Any]:
    """Generates canonical biometric vitals for Barf grounded in the briefing entropy."""
    if entropy_score >= 8.5 or "DEPRESSION" in vector or "CARDIAC" in vector:
        return {
            "systolic": 178,
            "diastolic": 112,
            "pulse": 118,
            "pastrami_lbs": 1.75,
            "panic_index": 9,
            "doctor_shapiro_status": "SPEED DIAL 1 - PAGING FROM QUEENS BLVD CARDIOLOGY",
            "mood_summary": "ACUTE CARDIAC PANIC WITH MANIC DEFENSIVE DELUSION",
        }
    elif "DELUSION" in vector or "MANIC" in vector:
        return {
            "systolic": 164,
            "diastolic": 102,
            "pulse": 106,
            "pastrami_lbs": 1.25,
            "panic_index": 7,
            "doctor_shapiro_status": "SPEED DIAL 1 - ON HOLD WHILE PACING BASEMENT",
            "mood_summary": "MANIC DELUSIONAL EUPHORIA WITH PALPITATIONS",
        }
    else:
        return {
            "systolic": 156,
            "diastolic": 98,
            "pulse": 102,
            "pastrami_lbs": 1.0,
            "panic_index": 6,
            "doctor_shapiro_status": "CALLED: 50MG METOPROLOL PRESCRIBED STAT",
            "mood_summary": "GUARDED SKEPTICISM WITH ELEVATED RESTING ANXIETY",
        }


def generate_deterministic_around_the_league(shockers: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Builds exactly 4 schadenfreude / shocker micro-takes adhering to Barf voice."""
    default_takes = [
        {
            "team": "DAL",
            "sentiment": "SCHADENFREUDE_EUPHORIA",
            "take": "Jerry Jones staring into the Arlington twilight while Dallas gets gutted is the only thing keeping my coronary arteries open today."
        },
        {
            "team": "BAL",
            "sentiment": "SCHADENFREUDE_EUPHORIA",
            "take": "Zay Flowers running wild gives me hope that somewhere in North America an offense actually understands how to move forward."
        },
        {
            "team": "NE",
            "sentiment": "SCHADENFREUDE_EUPHORIA",
            "take": "Watching New England fumble away Sunday afternoon against Jacksonville makes twenty years of Brady tyranny feel almost avenged."
        },
        {
            "team": "WAS",
            "sentiment": "SCHADENFREUDE_EUPHORIA",
            "take": "Marcus Mariota pulling magic out of his helmet against Seattle proves the universe is completely broken and nothing makes sense."
        }
    ]

    if not shockers:
        return default_takes

    results = []
    for s in shockers[:4]:
        headline = s.get("headline", "")
        matchup = s.get("matchup", "NFL")
        team = "NFL"
        for t in ["DAL", "BAL", "WAS", "NE", "LAC", "SEA", "JAX", "BUF", "CHC", "TEX"]:
            if t in headline.upper() or t in matchup.upper():
                team = t
                break

        results.append({
            "team": team,
            "sentiment": s.get("emotional_vector", "SCHADENFREUDE_EUPHORIA"),
            "take": f"Barf on {headline}: Dr. Shapiro tells me to look away from the TV, but watching rivals implode is pure cardiac medicine."
        })

    while len(results) < 4:
        results.append(default_takes[len(results)])

    return results[:4]


def generate_deterministic_editorial_rant(ny_anchor: Dict[str, Any]) -> Tuple[str, str]:
    """
    Returns (headline, editorial_rant) strictly calibrated between 220 and 280 words,
    containing >= 2 Barf anchor tokens and 0 banned tropes.
    """
    headline_input = ny_anchor.get("headline", "")
    vector = ny_anchor.get("emotional_vector", "")

    if "Soto" in headline_input or "Mets" in headline_input or "DEPRESSION" in vector:
        headline = "WE DON'T NEED A QUARTERBACK, WE NEED AN ARTERY CLAMP"
        rant = (
            "Listen to me, I am staring through the cracked basement window near Juniper Valley Park and I feel like my "
            "entire existence has been designated for assignment. Dr. Shapiro at Elmhurst Hospital already warned me that "
            "my systolic pressure is breaking local sound barriers, but how am I supposed to stay calm when another disastrous "
            "season goes up in toxic smoke? Juan Soto can assign blame until he is blue in the face, but the cold reality "
            "is sitting right on my chest like two pounds of hot pastrami from Ben's Kosher Deli with extra mustard. "
            "Forty years of this garbage! Forty years of sweating through my nineteen-eighty-six Mets pullover wondering "
            "why the baseball gods hate Queens with such biblical vengeance. Between the bumper-to-bumper standstill on "
            "the Grand Central Parkway and the freezing wind howling off Flushing Bay, my left ventricle is waving a white flag. "
            "You think I am being dramatic? Ask Brian Daboll what happens when hope turns into an autopsy report. At least with "
            "the Giants we know our place in the cosmic dumpster, but the Mets convince you they are building a cathedral "
            "before collapsing the roof on your skull. I have taken twelve Tums since the fifth inning and my resting pulse "
            "sounds like a jackhammer on Queens Boulevard. If Dominic Zvada doesn't nail every kick from sixty yards out this "
            "Sunday, I am checking myself into the cardiac ward until spring training. God help us all."
        )
    else:
        headline = "FOUR FIELD GOALS AND A PRAYER: GIANTS HIGH ART IN QUEENS"
        rant = (
            "Listen to me, I am sitting in my basement two blocks from Juniper Valley Park with a cold compress pressed against "
            "my carotid artery, and I swear to God my cardiologist Dr. Shapiro is about to drop me as a patient. Did you see "
            "what happened? We don't need a quarterback or a bullpen whisperer right now, we need a full-blown emergency artery "
            "clamp! I am sweating straight through my royal blue NY Giants number ten jersey and my vintage nineteen-eighty-six "
            "Mets pullover is soaked in pure unadulterated fear. You want to talk about sports? The Grand Central Parkway was "
            "bumper-to-bumper gridlock, my pastrami on rye from Ben's Kosher Deli on thirty-eighth is sitting like a radioactive "
            "lead brick in my esophagus, and the cold wind off Flushing Bay is howling right through the foundation. Brian Daboll "
            "is pacing the sideline like a man who just realized he locked his keys inside an armored truck, while Dominic Zvada "
            "is out there kicking fifty-yard knuckleballs into the swirling Meadowlands gale. If we win twelve to seven on four "
            "field goals, people call it ugly. Ugly? That is high art in Queens! That is how real men survive Sunday afternoon "
            "without flatlining before the six o'clock news. If this defense holds up, we are going fifteen and two, you hear me? "
            "Fifteen and two! But if they blow one more fourth-quarter lead, tell Shapiro to notify the morgue because my heart "
            "cannot survive another October."
        )

    return headline, rant


def generate_deterministic_punchup(topic: str) -> List[str]:
    """Generates exactly 5 distinct rapid-fire creator punchlines under 150 tokens total."""
    topic_lower = topic.lower()
    if "12-7" in topic_lower or "giants" in topic_lower or "field goal" in topic_lower:
        return [
            "Twelve to seven on four field goals is not just football, it is an echocardiogram with shoulder pads!",
            "Dominic Zvada's right foot is currently the only municipal service functioning in the tri-state area.",
            "Brian Daboll won a football game without completing a pass and Dr. Shapiro doubled my beta blockers.",
            "Cold MetLife wind blew my toupee into Secaucus, but Giants defense is taking us fifteen and two!",
            "I ate two pounds of pastrami during the third quarter and felt better than Dallas's entire defense."
        ]
    elif "mets" in topic_lower or "soto" in topic_lower or "blame" in topic_lower:
        return [
            "Seven hundred million down the Flushing sewer while Dr. Shapiro preps my bypass surgery!",
            "Juan Soto pointing fingers while my left ventricle sounds like a Queens Boulevard jackhammer is poetry.",
            "Chewing Tums by the handful while the Grand Central Parkway sits at a complete cardiac standstill.",
            "Forty years of sweating through an eighty-six pullover just to watch another September funeral.",
            "Give me hot pastrami from Ben's Deli, give me five minutes with the bullpen, and call an ambulance."
        ]
    else:
        return [
            f"Reacting to {topic}? Dr. Shapiro says my carotid artery is holding on by a pastrami grease string!",
            "The cold MetLife wind is rattling my teeth and my chest feels like boiling seltzer over this!",
            "Call Brian Daboll and tell him I need twelve Tums and an emergency field goal right now!",
            "Down here near Juniper Valley Park we don't analyze games, we survive them between heart palpitations.",
            "If this team gives up another late lead, Flushing Bay is getting my television set permanently!"
        ]


# ─────────────────────────────────────────────────────────────────────────────
# INFERENCE PIPELINE (Cloudflare -> Gemini -> Ollama -> Deterministic)
# ─────────────────────────────────────────────────────────────────────────────

def _load_gemini_api_key() -> Optional[str]:
    """Extracts Gemini API key from environment or local configs."""
    for var in ["GEMINI_API_KEY", "VITE_GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        val = os.getenv(var, "").strip().strip("'\"")
        if val:
            return val
    return None


def call_cloudflare_workers_ai(prompt: str, system: Optional[str] = None) -> Optional[str]:
    """Attempt generation via Cloudflare Workers AI REST API."""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN") or os.getenv("CLOUDFLARE_AI_TOKEN")
    if not account_id or not api_token:
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {"role": "system", "content": system or BARF_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.85
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success") and "result" in data:
                return data["result"].get("response", "").strip()
    except Exception as e:
        print(f"⚠️ [Workers AI] Generation failed: {e}", file=sys.stderr)
    return None


def call_gemini_api(prompt: str, system: Optional[str] = None, json_mode: bool = False) -> Optional[str]:
    """Attempt generation via Google GenAI Studio client."""
    if not genai:
        return None

    api_key = _load_gemini_api_key()
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        config_kwargs: Dict[str, Any] = {
            "temperature": 0.85,
        }
        if system:
            config_kwargs["system_instruction"] = system
        if json_mode and types:
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs) if types else None

        for model_name in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.8-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ [Gemini API] Generation failed: {e}", file=sys.stderr)
    return None


def call_ollama_api(prompt: str, system: Optional[str] = None, json_mode: bool = False) -> Optional[str]:
    """Attempt generation via local Ollama daemon."""
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": "llama3.1",
        "system": system or BARF_SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "format": "json" if json_mode else "",
        "options": {"temperature": 0.85, "num_predict": 1024}
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# CORE ORCHESTRATION & SYNTHESIS
# ─────────────────────────────────────────────────────────────────────────────

def synthesize_wire_payload(briefing: Optional[Dict[str, Any]] = None, engine: Optional[str] = None) -> Dict[str, Any]:
    """
    Synthesizes the complete Barf Daily Wire Payload, running inference through
    the multi-tier fallback cascade, enforcing lexical compliance and word counts,
    and returning a fully validated payload dictionary.
    """
    if briefing is None:
        if os.path.exists(DEFAULT_INPUT_BRIEFING):
            with open(DEFAULT_INPUT_BRIEFING, "r", encoding="utf-8") as f:
                briefing = json.load(f)
        else:
            briefing = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "trigger_event": "POST_GAME_SUNDAY_NIGHT",
                "ny_anchor_event": {
                    "headline": "Juan Soto assigns blame for disastrous Mets season",
                    "emotional_vector": "DEEP_EXISTENTIAL_DEPRESSION",
                    "entropy_score": 9.3
                },
                "national_shockers": []
            }

    ny_anchor = briefing.get("ny_anchor_event", {})
    headline_input = ny_anchor.get("headline", "Mets collapse in Queens")
    summary_input = ny_anchor.get("summary", "")
    entropy_score = float(ny_anchor.get("entropy_score", 9.0))
    vector = ny_anchor.get("emotional_vector", "DEEP_EXISTENTIAL_DEPRESSION")
    shockers = briefing.get("national_shockers", [])

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")

    # If engine is explicitly 'deterministic', bypass LLMs
    if engine == "deterministic":
        det_hl, det_rant = generate_deterministic_editorial_rant(ny_anchor)
        det_vitals = generate_deterministic_vitals(entropy_score, vector)
        det_atl = generate_deterministic_around_the_league(shockers)
        payload = {
            "date": date_str,
            "headline": det_hl,
            "editorial_rant": det_rant,
            "around_the_league": det_atl,
            "daily_vitals": det_vitals,
        }
        return payload

    prompt = f"""You are Barf (@barf), Queens Mawg living near Juniper Valley Park in Middle Village, wearing a royal blue NY Giants #10 jersey over a 1986 Mets pullover.
Your cardiologist Dr. Shapiro is on speed dial. You order pastrami on rye from Ben's Kosher Deli on 38th. You hate Grand Central Parkway traffic and cold MetLife wind.
You oscillate violently between existential doom and manic delusional optimism.

Input Story:
Headline: {headline_input}
Summary: {summary_input}
Entropy Vector: {vector} (Score: {entropy_score})

Generate a complete JSON object with the following exact keys:
{{
  "headline": "UNHINGED TABLOID TITLE IN ALL CAPS",
  "editorial_rant": "230 to 270 words of authentic neurotic Queens sports fury and hypochondria.",
  "around_the_league": [
    {{"team": "DAL", "sentiment": "SCHADENFREUDE_EUPHORIA", "take": "1-2 sentence schadenfreude quip"}},
    {{"team": "BAL", "sentiment": "SCHADENFREUDE_EUPHORIA", "take": "1-2 sentence schadenfreude quip"}},
    {{"team": "NE", "sentiment": "SCHADENFREUDE_EUPHORIA", "take": "1-2 sentence schadenfreude quip"}},
    {{"team": "WAS", "sentiment": "SCHADENFREUDE_EUPHORIA", "take": "1-2 sentence schadenfreude quip"}}
  ],
  "daily_vitals": {{
    "systolic": 178,
    "diastolic": 112,
    "pulse": 118,
    "pastrami_lbs": 1.75,
    "panic_index": 9,
    "doctor_shapiro_status": "SPEED DIAL 1 - PAGING FROM QUEENS BLVD CARDIOLOGY",
    "mood_summary": "ACUTE CARDIAC PANIC WITH MANIC DEFENSIVE DELUSION"
  }}
}}

CRITICAL INVARIANTS:
1. editorial_rant word count MUST be strictly between 220 and 280 words.
2. Must include at least 3 Barf anchor tokens: Shapiro, pastrami, Flushing, MetLife, Mets, Giants, Zvada, Holland, Daboll.
3. FORBIDDEN: Never use 'game of two halves', 'at the end of the day', 'credit to both teams', 'as an AI', or 'fascinating matchup'.
4. around_the_league must have exactly 4 items.
5. All vitals must be plausible integers/floats.
"""

    raw_json = None

    # Cascade 1: Cloudflare Workers AI
    if engine in (None, "workers-ai"):
        raw_json = call_cloudflare_workers_ai(prompt, system=BARF_SYSTEM_PROMPT)

    # Cascade 2: Gemini API
    if not raw_json and engine in (None, "gemini"):
        raw_json = call_gemini_api(prompt, system=BARF_SYSTEM_PROMPT, json_mode=True)

    # Cascade 3: Local Ollama
    if not raw_json and engine in (None, "ollama"):
        raw_json = call_ollama_api(prompt, system=BARF_SYSTEM_PROMPT, json_mode=True)

    # Parse and Validate LLM candidate
    if raw_json:
        try:
            # Strip markdown json blocks if present
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_json.strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            candidate = json.loads(cleaned)

            if "date" not in candidate:
                candidate["date"] = date_str

            is_valid, errors = validate_wire_payload_schema(candidate)
            if is_valid:
                return candidate
            else:
                print(f"⚠️ [Synthesizer] LLM candidate failed schema/gate validation: {errors}. Falling back to deterministic seed.", file=sys.stderr)
        except Exception as parse_err:
            print(f"⚠️ [Synthesizer] Failed to parse LLM JSON: {parse_err}. Falling back to deterministic seed.", file=sys.stderr)

    # Cascade 4: Deterministic Fallback Seed
    det_hl, det_rant = generate_deterministic_editorial_rant(ny_anchor)
    det_vitals = generate_deterministic_vitals(entropy_score, vector)
    det_atl = generate_deterministic_around_the_league(shockers)

    payload = {
        "date": date_str,
        "headline": det_hl,
        "editorial_rant": det_rant,
        "around_the_league": det_atl,
        "daily_vitals": det_vitals,
    }

    # Final assertion check
    is_valid, errors = validate_wire_payload_schema(payload)
    if not is_valid:
        raise ValueError(f"Deterministic seed failed validation: {errors}")

    return payload


def generate_creator_punchup(topic: str, engine: Optional[str] = None) -> List[str]:
    """
    Returns a JSON array of exactly 5 rapid-fire quips/lines under 150 tokens total
    for creators, adhering to Barf's voice, anchor tokens, and banned-trope filters.
    """
    if engine == "deterministic":
        return generate_deterministic_punchup(topic)

    prompt = f"""You are Barf (@barf), the neurotic, loudmouth NY fan from Queens living near Juniper Valley Park.
Wearing a royal blue NY Giants #10 over an '86 Mets pullover. Dr. Shapiro on speed dial.

Generate exactly 5 rapid-fire punch-up lines on the topic: '{topic}'.
Requirements:
1. Return a JSON array of exactly 5 strings: ["line 1", "line 2", "line 3", "line 4", "line 5"].
2. Total length of all 5 lines combined MUST be under 150 tokens (roughly 80-110 words total).
3. Pure Queens vernacular, high panic/delusion, reference anchors like Dr. Shapiro, pastrami, MetLife wind, Dominic Zvada, Brian Daboll.
4. FORBIDDEN: Never say 'game of two halves', 'at the end of the day', 'credit to both teams', 'as an AI', or 'fascinating matchup'.
5. Each line must be distinct and punchy.
"""

    raw_json = None
    if engine in (None, "workers-ai"):
        raw_json = call_cloudflare_workers_ai(prompt, system=BARF_SYSTEM_PROMPT)

    if not raw_json and engine in (None, "gemini"):
        raw_json = call_gemini_api(prompt, system=BARF_SYSTEM_PROMPT, json_mode=True)

    if not raw_json and engine in (None, "ollama"):
        raw_json = call_ollama_api(prompt, system=BARF_SYSTEM_PROMPT, json_mode=True)

    if raw_json:
        try:
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_json.strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            candidate = json.loads(cleaned)

            if isinstance(candidate, list) and len(candidate) == 5:
                # Check for banned tropes and token length
                all_clean = True
                total_words = 0
                for line in candidate:
                    if not isinstance(line, str):
                        all_clean = False
                        break
                    is_clean, _ = validate_banned_tropes(line)
                    if not is_clean:
                        all_clean = False
                        break
                    total_words += len(line.split())

                # Rough token estimate: words * 1.35
                if all_clean and (total_words * 1.35) <= 150:
                    return [str(x).strip() for x in candidate]
        except Exception:
            pass

    return generate_deterministic_punchup(topic)


# ─────────────────────────────────────────────────────────────────────────────
# PRESS CONFERENCE STREAM SNIPER & ADVOCATE CO-PILOT MODULE
# ─────────────────────────────────────────────────────────────────────────────

PERSONA_LORE = {
    "barf": {
        "handle": "@barf",
        "name": "Barf",
        "team": "Mets/Giants",
        "location": "Middle Village / Juniper Valley Park, Queens",
        "master_lock": "Downed a full roll of peppermint Tums in the Jackie Robinson Rotunda after an 8th-inning blown save while Dr. Shapiro's pager exploded on his belt",
        "anchors": ["Dr. Shapiro", "pastrami", "Flushing", "MetLife", "Mets", "Giants", "Zvada", "Brian Daboll", "Carlos Mendoza", "Jackie Robinson Tums emergency"],
        "system_prompt": BARF_SYSTEM_PROMPT,
    },
    "battery_chucker": {
        "handle": "@battery_chucker",
        "name": "Battery Chucker",
        "team": "Phillies/Eagles",
        "location": "South Philly / Delco",
        "master_lock": "Dodged a rusted Master Lock hurled at his skull from the 700-level of Veterans Stadium during an extra-inning blown game",
        "anchors": ["WIP 94.1", "D-cell batteries", "Nick Sirianni", "Rob Thomson", "Roast Pork at John's", "I-95 South", "Master Lock dodge"],
        "system_prompt": (
            "You are Battery Chucker (@battery_chucker), unhinged Philadelphia sports advocate from South Philly. "
            "Survivor of the Vet 700-level who dodged an actual Master Lock thrown at his skull. "
            "Carries D-cell batteries in his coat, screams at WIP 94.1 callers, and despises corporate coach deflection."
        ),
    },
    "southie_sully": {
        "handle": "@southie_sully",
        "name": "Southie Sully",
        "team": "Pats/Red Sox",
        "location": "South Boston / Dorchester",
        "master_lock": "Locked his keys inside the station wagon outside Sullivan's on Castle Island while listening to a 9th-inning balk call in freezing sleet",
        "anchors": ["WEEI radio", "Dunkin' large iced extra-extra", "Castle Island", "Pesky Pole", "Jerod Mayo", "Alex Cora", "Storrow Drive"],
        "system_prompt": (
            "You are Southie Sully (@southie_sully), razor-tongued Boston sports cynic from South Boston. "
            "Drinks 32oz Dunkin iced extra-extra in blizzards, locked keys in station wagon at Castle Island. "
            "Screams at WEEI sports radio, and has zero patience for soft coaching excuses."
        ),
    },
}


def extract_presser_quotes(transcript_text: str) -> List[Dict[str, str]]:
    """Extracts key coach statements and timestamps from transcript text."""
    quotes = []
    lines = transcript_text.splitlines()
    ts_pattern = re.compile(r'\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?')

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        ts_match = ts_pattern.search(line_clean)
        ts = ts_match.group(1) if ts_match else None

        has_keywords = any(kw in line_clean.lower() for kw in [
            "execute", "execution", "tape", "film", "process", "details", "effort",
            "decision", "quarterback", "clean up", "adversity", "grow", "opportunity",
            "practice", "believe", "accountab", "look at"
        ])

        if ('"' in line_clean or has_keywords) and len(line_clean) > 15:
            text = ts_pattern.sub('', line_clean).strip().strip(':').strip().strip('"')
            quotes.append({
                "timestamp": ts or "01:15",
                "text": text[:180]
            })
            if len(quotes) >= 6:
                break

    default_fallbacks = [
        {"timestamp": "01:14", "text": "We just have to look at the tape and clean up the details."},
        {"timestamp": "03:45", "text": "Execution comes down to all eleven guys being on the same page."},
        {"timestamp": "06:10", "text": "I saw good fight in our guys in the second half."},
        {"timestamp": "08:33", "text": "It starts with me, but we had opportunities we didn't capitalize on."},
        {"timestamp": "11:05", "text": "We believe in the process and we will get back to work on Monday."}
    ]

    for fb in default_fallbacks:
        if len(quotes) >= 5:
            break
        quotes.append(fb)

    return quotes


def calculate_coach_deflection_index(transcript_text: str) -> int:
    """Calculates Coach Deflection & Excuse Meter on a 1-10 scale."""
    keywords = [
        "execute", "execution", "tape", "film", "process", "details", "effort",
        "decision", "clean up", "look at", "missed opportunity", "adversity",
        "grow", "practice", "fundamentals", "trust", "positives", "accountab"
    ]
    text_lower = transcript_text.lower()
    matches = sum(text_lower.count(kw) for kw in keywords)
    score = 6 + min(4, matches // 2)
    return max(1, min(10, score))


def generate_deterministic_presser_punchup(
    transcript_text: str,
    persona: str = "barf",
    topic: str = "Postgame Presser"
) -> Dict[str, Any]:
    """
    Generates canonical 5 tweet punchups, 60s video rant script, and excuse rating
    grounded in Master Lock trauma and coach presser quotes.
    """
    clean_p = persona.lower().lstrip('@')
    if clean_p not in PERSONA_LORE:
        clean_p = "barf"

    quotes = extract_presser_quotes(transcript_text)
    deflection_score = calculate_coach_deflection_index(transcript_text)

    if clean_p == "battery_chucker":
        punchups = [
            f"[{quotes[0]['timestamp']}] Sirianni at the podium talking about 'growing through adversity.' I dodged an actual rusted Master Lock thrown at my skull at the Vet 700-level and that hurt less than this presser!",
            f"[{quotes[1]['timestamp']}] 'We have to execute on third down.' Third down?! You dialed up bubble screens into double coverage! I've got two D-cell batteries in my pocket with more juice than this offense!",
            f"[{quotes[2]['timestamp']}] Coach saying 'we believe in the guys in that locker room.' WIP 94.1 has 8,000 callers on line 1 ready to drive the coordinators straight to 30th Street Station!",
            f"[{quotes[3]['timestamp']}] Talking about cleaning up details while eating cold roast pork on I-95 South in gridlock. Hand over the play sheet before South Philly burns the game tape for you!",
            f"[{quotes[4]['timestamp']}] Coach Deflection Meter at {deflection_score}/10! Don't come up to this mic and preach patience when Sunday was an absolute disgrace to the Delaware Valley!"
        ]
        rant = (
            "I cannot listen to another syllable coming out of this postgame press conference! The coach is standing at the podium "
            "with that smug smirk talking about 'growing through adversity' and 'cleaning up the operation'! You want to talk about adversity? "
            "I survived twenty years in the 700-level at Veterans Stadium and dodged an actual rusted Master Lock thrown at my skull during "
            "extra innings, and that was a stroll through Rittenhouse Square compared to watching this offensive disaster! We had third-and-short "
            "three separate times and dialed up horizontal screens behind the line of scrimmage! WIP 94.1 is melting down right now with callers "
            "ready to revoke your parking pass. Don't come up to this microphone and tell us to trust the process. You burnt all three timeouts "
            "before the two-minute warning, and now you want credit for effort? Hand over the whistle, buy a ticket in the upper deck, and let "
            "South Philly call the plays. This is Battery Chucker signing off before I lose my mind!"
        )
    elif clean_p == "southie_sully":
        punchups = [
            f"[{quotes[0]['timestamp']}] Coach standing at the mic like he's doing us a favor. I locked my keys in the wagon outside Sullivan's on Castle Island in freezing sleet and was less aggravated than this!",
            f"[{quotes[1]['timestamp']}] 'We saw good things on film.' What film?! You couldn't move the ball past the line of scrimmage with a bulldozer! WEEI callers are having collective strokes right now!",
            f"[{quotes[2]['timestamp']}] Drinking a 32oz Dunkin' iced extra-extra in 15-degree weather and my coffee has more warmth than this team's fourth-quarter effort!",
            f"[{quotes[3]['timestamp']}] 'Execution comes down to details.' No, execution comes down to coaching! Stop trying to outsmart everyone on Storrow Drive and run the football!",
            f"[{quotes[4]['timestamp']}] Excuse meter pegged at {deflection_score}/10. The Pesky Pole has seen softer collapses than this presser. Absolute embarrassment for New England!"
        ]
        rant = (
            "Unbelievable. Absolutely unbelievable. I am sitting here watching this press conference with a giant Dunkin' iced extra-extra "
            "that has frozen completely solid, listening to the head coach tell us 'we're close.' Close to what?! Close to driving every fan "
            "in New England straight off the Tobin Bridge?! I haven't been this disgusted since I locked my keys in the station wagon outside "
            "Sullivan's on Castle Island in the middle of a nor'easter listening to a blown balk call! You had four full quarters to show an ounce "
            "of offensive imagination and instead you gave us three-and-outs and burned timeouts like they were extra napkins! WEEI is going to "
            "be unlistenable tomorrow because everyone knows this presser is pure deflection. Stop treating the fans like we can't see what's "
            "happening on the field! This is Southie Sully, and I've heard enough soft excuses to last a lifetime!"
        )
    else:  # barf default
        punchups = [
            f"[{quotes[0]['timestamp']}] Mendoza says 'we gotta look at the tape.' Tape?! I have watched 40 years of game tape from my Juniper Valley basement and every reel is an autopsy report! Dr. Shapiro doubled my beta blockers!",
            f"[{quotes[1]['timestamp']}] Coach talking about execution while I'm choking on Ben's Deli pastrami with extra mustard. The only thing being executed on Sunday is my will to live in Queens!",
            f"[{quotes[2]['timestamp']}] 'Good fight in the second half.' Don't give me moral victories! I haven't experienced trauma like this since my Jackie Robinson Rotunda Tums emergency during the 8th-inning blown save!",
            f"[{quotes[3]['timestamp']}] 'We gotta clean up the details.' The detail is Dominic Zvada had to kick knuckleballs into 35mph MetLife wind while the offense moved backwards faster than the Grand Central Parkway!",
            f"[{quotes[4]['timestamp']}] Coach Deflection Meter at {deflection_score}/10! Dr. Shapiro's pager is beeping in Morse code from Elmhurst Hospital telling me to smash the television before my systolic hits 200!"
        ]
        rant = (
            "Look at this postgame press conference! Look at the coach standing up there at the microphone talking about 'looking at the film' "
            "and 'cleaning up the operation'! Are you out of your mind?! I am standing in my basement two blocks from Juniper Valley Park in a "
            "sweat-soaked eighty-six Mets pullover, my blood pressure is 185 over 115, and Dr. Shapiro is paging the cardiac ICU right now! You "
            "think we need to look at the tape? I don't need film study to tell you that four field goals, twelve penalties, and zero offensive "
            "touchdowns is high treason! I haven't seen an excuse parade like this since I choked on peppermint Tums in the Jackie Robinson Rotunda "
            "while the bullpen blew the game in the eighth inning. Quit telling us the process is working! The process is giving the entire borough "
            "of Queens ventricular tachycardia! Give me two pounds of pastrami with extra mustard from Ben's Kosher Deli, give me a real game plan, "
            "or call an ambulance to Middle Village. This is Barf signing off before my heart monitor flatlines!"
        )

    # Ensure every punchup is strictly under 280 chars
    validated_punchups = []
    for p in punchups[:5]:
        if len(p) > 275:
            p = p[:272] + "..."
        validated_punchups.append(p)

    payload = {
        "persona": PERSONA_LORE[clean_p]["handle"],
        "topic": topic,
        "coach_deflection_index": deflection_score,
        "5_tweet_punchups": validated_punchups,
        "tweet_punchups": validated_punchups,
        "rant_script_60s": rant,
        "key_quotes": quotes[:5],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    return payload


def synthesize_presser_punchup(
    transcript_text: str,
    persona: str = "barf",
    topic: str = "Postgame Presser",
    engine: Optional[str] = None,
    output_file: str = DEFAULT_SNIPE_OUTPUT
) -> Dict[str, Any]:
    """
    Core FaaS Stream Sniper synthesis engine.
    Extracts quotes, injects Master Lock lore, runs multi-tier LLM inference with
    fallback to deterministic generator, and saves to data/snipe_punchup_latest.json.
    """
    clean_p = persona.lower().lstrip('@')
    if clean_p not in PERSONA_LORE:
        clean_p = "barf"

    persona_info = PERSONA_LORE[clean_p]
    quotes = extract_presser_quotes(transcript_text)
    quotes_formatted = "\n".join([f"- [{q['timestamp']}]: \"{q['text']}\"" for q in quotes])

    prompt = f"""You are {persona_info['name']} ({persona_info['handle']}), the legendary advocate for {persona_info['team']}.
Location: {persona_info['location']}.
Master Lock Incident / Emotional Scar Tissue: {persona_info['master_lock']}.
Anchors: {', '.join(persona_info['anchors'])}.

Analyze this coach/player postgame press conference transcript:
===
Topic: {topic}
Key Transcript Quotes:
{quotes_formatted}

Full Transcript Excerpt:
{transcript_text[:1800]}
===

Generate a creator punch-up suite strictly adhering to your voice and lore.
Requirements:
1. Return a valid JSON object matching EXACTLY this schema:
{{
  "5_tweet_punchups": [
    "[MM:SS] First rapid-fire tweet punchline under 280 chars reacting to quote...",
    "[MM:SS] Second tweet punchline under 280 chars with persona anchor...",
    "[MM:SS] Third tweet punchline under 280 chars invoking Master Lock trauma...",
    "[MM:SS] Fourth tweet punchline under 280 chars with tactical rage...",
    "[MM:SS] Fifth tweet punchline under 280 chars summarizing the excuse..."
  ],
  "rant_script_60s": "A complete, spoken 60-second video rant monologue for camera/teleprompter (130-170 words). Unhinged, authentic fan pain, zero corporate speak.",
  "coach_deflection_index": 8
}}
2. FORBIDDEN AI CLICHÉS: Never use 'game of two halves', 'at the end of the day', 'credit to both teams', 'as an AI', or 'fascinating matchup'.
3. Every tweet punchline MUST start with a timestamp like [01:23] and be strictly under 280 characters.
4. coach_deflection_index must be an integer from 1 to 10 rating the coach's excuses and deflection.
"""

    raw_json = None
    if engine in (None, "workers-ai"):
        raw_json = call_cloudflare_workers_ai(prompt, system=persona_info["system_prompt"])

    if not raw_json and engine in (None, "gemini"):
        raw_json = call_gemini_api(prompt, system=persona_info["system_prompt"], json_mode=True)

    if not raw_json and engine in (None, "ollama"):
        raw_json = call_ollama_api(prompt, system=persona_info["system_prompt"], json_mode=True)

    if raw_json:
        try:
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_json.strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            candidate = json.loads(cleaned)

            punchups = candidate.get("5_tweet_punchups") or candidate.get("tweet_punchups")
            rant = candidate.get("rant_script_60s")
            deflection = candidate.get("coach_deflection_index")

            if (
                isinstance(punchups, list) and len(punchups) == 5 and
                isinstance(rant, str) and len(rant.split()) >= 80 and
                isinstance(deflection, (int, float))
            ):
                all_clean = True
                cleaned_punchups = []
                for p in punchups:
                    p_str = str(p).strip()
                    is_clean, _ = validate_banned_tropes(p_str)
                    if not is_clean or len(p_str) > 280:
                        all_clean = False
                        break
                    cleaned_punchups.append(p_str)

                if all_clean:
                    payload = {
                        "persona": persona_info["handle"],
                        "topic": topic,
                        "coach_deflection_index": int(deflection),
                        "5_tweet_punchups": cleaned_punchups,
                        "tweet_punchups": cleaned_punchups,
                        "rant_script_60s": rant.strip(),
                        "key_quotes": quotes[:5],
                        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                    # Save to output_file
                    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2)
                    return payload
        except Exception:
            pass

    # Deterministic Fallback Seed
    payload = generate_deterministic_presser_punchup(transcript_text, persona=clean_p, topic=topic)
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Barf Persona Edge Synthesizer & Creator Punch-Up Engine"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=DEFAULT_INPUT_BRIEFING,
        help="Path to input fanstack_entropy_briefing.json",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_PAYLOAD,
        help="Path to output barf_wire_payload.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute synthesis and validation without writing payload to disk",
    )
    parser.add_argument(
        "--punchup",
        type=str,
        default=None,
        help="Generate 5 rapid-fire creator punchlines on the specified topic and exit",
    )
    parser.add_argument(
        "--snipe-file",
        type=str,
        default=None,
        help="Path to input transcript markdown file to synthesize presser punchup suite",
    )
    parser.add_argument(
        "--persona",
        type=str,
        default="barf",
        help="Advocate persona (@barf, @battery_chucker, @southie_sully)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="Postgame Presser",
        help="Topic or press conference title for punchup suite",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default=None,
        choices=["workers-ai", "gemini", "ollama", "deterministic"],
        help="Force a specific inference engine",
    )

    args = parser.parse_args()

    # Presser Snipe Punch-Up Mode (--snipe-file)
    if args.snipe_file is not None:
        if not os.path.exists(args.snipe_file):
            print(f"❌ Error: Snipe transcript file not found: {args.snipe_file}", file=sys.stderr)
            sys.exit(1)
        with open(args.snipe_file, "r", encoding="utf-8") as f:
            transcript_text = f.read()
        suite = synthesize_presser_punchup(
            transcript_text=transcript_text,
            persona=args.persona,
            topic=args.topic,
            engine=args.engine,
            output_file=DEFAULT_SNIPE_OUTPUT
        )
        print(json.dumps(suite, indent=2))
        return

    # Creator Punch-Up Mode
    if args.punchup is not None:
        punchlines = generate_creator_punchup(args.punchup, engine=args.engine)
        print(json.dumps(punchlines, indent=2))
        return

    # Wire Payload Mode
    print(f"🚀 [BARF-SYNTHESIZER] Ingesting briefing from {args.input}...")
    briefing = None
    if os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            briefing = json.load(f)
    else:
        print(f"⚠️ Warning: Input file {args.input} not found. Using internal fallback briefing.", file=sys.stderr)

    payload = synthesize_wire_payload(briefing=briefing, engine=args.engine)

    # Validate output schema
    is_valid, errors = validate_wire_payload_schema(payload)
    if not is_valid:
        print(f"❌ Schema validation failed: {errors}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Payload validated successfully! Word count: {len(payload['editorial_rant'].split())} words.")
    print(f"📰 Tabloid Headline: {payload['headline']}")
    print(f"💓 Vitals: BP {payload['daily_vitals']['systolic']}/{payload['daily_vitals']['diastolic']} | Pulse {payload['daily_vitals']['pulse']} | Panic: {payload['daily_vitals']['panic_index']}/10")

    if args.dry_run:
        print("\n🔍 [DRY RUN ACTIVE] Payload output:\n")
        print(json.dumps(payload, indent=2))
        return

    # Write payload to disk
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"💾 Payload successfully saved to {args.output}")


if __name__ == "__main__":
    main()
