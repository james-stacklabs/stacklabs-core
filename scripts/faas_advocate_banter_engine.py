#!/home/james/stacklabs/.venv/bin/python3
"""
faas_advocate_banter_engine.py — Sovereign OS: Advocate Banter & Event VFS Engine
Generates live crossfire banter between Barf (@barf) and Burl (@burl_bayou)
triggered by high-leverage game situations and chat spikes.
Writes atomic event folders to /dev/shm/faas_vfs/events/{event_id}/.
"""

import os
import sys
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, List

EVENTS_DIR = Path("/dev/shm/faas_vfs/events")
EVENTS_DIR.mkdir(parents=True, exist_ok=True)
LATEST_EVENT_FILE = EVENTS_DIR / "latest_event.json"

BURL_TEMPLATES = {
    "RED_ZONE_TURNOVER": [
        "Right tackle completely stopped his feet on the edge rush. You can't run zone read in the SEC with lazy hips. Ball is out.",
        "Turnover in the red zone. That quarterback held that ball long enough to smoke a whole brisket. Defensive end just took his lunch money.",
        "Soft pass protection. Boy looked like he was dancing at a cotillion instead of blocking the B-gap. Turnover right there."
    ],
    "HOME_RUN": [
        "Hanger right over the black. Even a blind hound finds a squirrel when you leave an 84-mph slider waist-high.",
        "Crushed. That ball is out in the parking lot behind right-center. Pitcher knew it the second it left his fingertips.",
        "You leave a fastball out over the plate on a 2-1 count and you get what you asked for. No movement, pure batting practice."
    ],
    "BASES_LOADED_K": [
        "That's high-heat gas on 3-2. Sunk the backdoor two-seamer and walked off the mound before the umpire even raised his arm. Guts.",
        "Bases loaded, full count, and he challenges him with 99 on the hands. That's real Saturday pitching right there.",
        "Swung right through it. Pressure got to him. When the lights get bright, fundamentals either save you or drown you."
    ],
    "OUTFIELD_ROBBERY": [
        "Ran straight through the warning track dirt and timed the jump off the padding. Robbed him clean. That's centerfield defense like God intended.",
        "Took a home run right back out of the third row. Perfect route efficiency. Kid didn't even look at the wall until his cleats hit dirt."
    ],
    "DEEP_FIELD_GOAL": [
        "Fifty-four yards into the crossbreeze with forty seconds left. Ice water in that boy's veins. Split the uprights.",
        "Long-range field goal right through the teeth of the wind. That kicker has an absolute cannon for a right leg."
    ],
    "EXPLOSIVE_PLAY": [
        "Safety bit on the play-action like a hungry hound on a ham bone. Receiver was open by fifteen yards down the hash marks.",
        "Forty-yard chunk play on 3rd and long. Cornerback was flat-footed in cover 2. That's how you break a defense's back."
    ],
    "CHAT_SPIKE": [
        "Whole stadium is screaming and losing their minds. Just slow the game down. You can hear the panic in the playcall from here.",
        "Folks on the internet having an aneurysm. Ball is on the 35, there's four minutes left. Stop crying and play defense.",
        "Crowd noise is peaking. Linemen can't hear the snap count. This is where false starts kill drives."
    ]
}

BARF_TEMPLATES = {
    "RED_ZONE_TURNOVER": [
        "MY CHEST! MY ENTIRE CHEST! We are inside the ten yard line and you cough it up?! Shapiro get the tazer I cannot breathe!",
        "UNBELIEVABLE! Empty backfield on 2nd and goal! Who called that?! I am downing eight Tums and calling my cardiologist!",
        "A TURNOVER! A RED ZONE TURNOVER! It's 1999 all over again! I swear on an Old Style beer this franchise is trying to end my life!"
    ],
    "HOME_RUN": [
        "AND IT GOES OUT! OF COURSE IT GOES OUT! 89-mph meatball served on a silver platter! I need an oxygen tank in this dugout!",
        "SEE YA! That ball is halfway to Queens! The bullpen was warming up for twenty minutes just to give up a moonshot!",
        "Are you kidding me?! Two outs, nobody on, and he gives up a 420-foot bomb! My pulse is 165 BPM!"
    ],
    "BASES_LOADED_K": [
        "HE STRUCK HIM OUT! HE STRUCK HIM OUT! I ALMOST PASSED OUT ON THE COUCH! Edwin Diaz you absolute psychopath I love you!",
        "STRUCK HIM OUT LOOKING! Freeze him! My blood pressure just dropped from 250 back to 190! Somebody get me water!",
        "CALLED STRIKE THREE! The umpire took five seconds to ring him up, I thought I was meeting Da Coach in heaven!"
    ],
    "OUTFIELD_ROBBERY": [
        "HE ROBBED IT! HE ROBBED IT AT THE WALL! OVER THE FENCE! I CANNOT FEEL MY LEFT ARM! THAT IS A POSTSEASON MIRACLE!",
        "WHAT A CATCH! HE SCALED THE WALL LIKE A CAT BURGLAR! MY CARDIOLOGIST IS PAGING ME RIGHT NOW!"
    ],
    "DEEP_FIELD_GOAL": [
        "FROM 54 YARDS?! WITH ICE IN HIS VEINS?! My blood pressure just spiked through the acoustic ceiling tiles!",
        "IT'S GOOD?! HE MADE IT?! I FELL OFF MY CHAIR AND KICKED THE COFFEE TABLE! UNBELIEVABLE!"
    ],
    "EXPLOSIVE_PLAY": [
        "LOOK AT HIM GO! UNTOUCHED DOWN THE SIDELINE! SOMEBODY CALL 911 BEFORE MY HEART GIVES OUT!",
        "A 40-YARD GOUGE! THE SECONDARY WAS SLEEPING AT THE WHEEL! I AM SHAKING! I AM LITERALLY SHAKING!"
    ],
    "CHAT_SPIKE": [
        "THE CHAT IS MELTING DOWN! LOOK AT THE BLEACHER WIRE! EVERYBODY IS SCREAMING FOR THE COACH TO BE FIRED!",
        "VOLUME OFF THE CHARTS! Everyone in the bleachers is throwing Polish sausages at the screen! Absolute pandemonium!",
        "DON'T TELL ME TO CALM DOWN! Look at the wire! Forty messages a minute and every single one is in all-caps!"
    ]
}

def generate_event(event_type: str = "CHAT_SPIKE", game_name: str = "MIL @ LAD (NLCS Game 3)", leverage: str = "HIGH") -> Dict[str, Any]:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S-04:00")
    event_id = f"ev_{int(time.time())}_{random.randint(100, 999)}"
    event_dir = EVENTS_DIR / event_id
    event_dir.mkdir(parents=True, exist_ok=True)
    
    burl_pool = BURL_TEMPLATES.get(event_type, BURL_TEMPLATES["CHAT_SPIKE"])
    barf_pool = BARF_TEMPLATES.get(event_type, BARF_TEMPLATES["CHAT_SPIKE"])
    burl_quote = random.choice(burl_pool)
    barf_quote = random.choice(barf_pool)
    
    telemetry = {
        "event_id": event_id,
        "event_type": event_type,
        "game": game_name,
        "leverage": leverage,
        "timestamp": timestamp,
        "chat_velocity": f"{random.randint(35, 65)} msg/min",
        "barf_bp": f"{random.randint(220, 260)}/{random.randint(140, 170)}"
    }
    
    burl_payload = {
        "advocate": "Burl (Bayou Coonhound)",
        "handle": "@burl_bayou",
        "avatar": "/images/burl/burl_headshot.png",
        "take": burl_quote,
        "timestamp": timestamp
    }
    
    barf_payload = {
        "advocate": "Barf (Queens Mawg)",
        "handle": "@barf",
        "avatar": "/images/barf/barf_headshot.png",
        "take": barf_quote,
        "timestamp": timestamp,
        "bp": telemetry["barf_bp"]
    }
    
    # Dynamic sport-aware 4th turn retort
    if "RED_ZONE" in event_type or "cfb" in game_name.lower() or "nfl" in game_name.lower():
        barf_reply = random.choice([
            "Ain't over?! Have you seen our secondary?! Our safety is playing 30 yards off the ball! It's over Burl!",
            "Ain't over?! We just gave up 70 yards on three plays! I'm chewing six Tums right now!",
            "Don't tell me it ain't over! We have zero timeouts and the defense is sucking wind!"
        ])
    else:
        barf_reply = random.choice([
            "Ain't over?! Have you seen our bullpen warming up?! It's over Burl!",
            "Ain't over?! He's missed with four straight sliders in the dirt! Call the bullpen!",
            "Don't tell me to relax Burl, my Apple Watch just warned me of atrial fibrillation!"
        ])
        
    banter_thread = [
        {"author": "Burl", "handle": "@burl_bayou", "text": burl_quote, "time": timestamp[-14:-6]},
        {"author": "Barf", "handle": "@barf", "text": barf_quote, "time": timestamp[-14:-6]},
        {"author": "Burl", "handle": "@burl_bayou", "text": "Take a breath, Mawg. The ball game ain't over yet.", "time": timestamp[-14:-6]},
        {"author": "Barf", "handle": "@barf", "text": barf_reply, "time": timestamp[-14:-6]}
    ]
    
    # Write VFS files for the event
    (event_dir / "telemetry.json").write_text(json.dumps(telemetry, indent=2))
    (event_dir / "burl_take.json").write_text(json.dumps(burl_payload, indent=2))
    (event_dir / "barf_take.json").write_text(json.dumps(barf_payload, indent=2))
    (event_dir / "banter_thread.json").write_text(json.dumps(banter_thread, indent=2))
    
    # Update latest pointer
    latest_payload = {
        "latest_event_id": event_id,
        "telemetry": telemetry,
        "burl": burl_payload,
        "barf": barf_payload,
        "banter": banter_thread
    }
    LATEST_EVENT_FILE.write_text(json.dumps(latest_payload, indent=2))
    return latest_payload

if __name__ == "__main__":
    event_type = sys.argv[1] if len(sys.argv) > 1 else "CHAT_SPIKE"
    res = generate_event(event_type=event_type)
    print(f"Generated event {res['latest_event_id']} in /dev/shm/faas_vfs/events/")
