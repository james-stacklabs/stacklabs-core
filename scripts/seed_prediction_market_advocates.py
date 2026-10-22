#!/usr/bin/env python3
import sqlite3
import os
import json
from PIL import Image, ImageDraw, ImageFont

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
AVATARS_DIR = "/home/james/stacklabs/avatars"

personas = [
    {
        "id": "PER_VEGAS_VINNIE",
        "user_name": "vegas_vinnie",
        "display_name": "Vegas Vinnie",
        "team": "GLOBAL",
        "color": "#10b981",
        "system_prompt": "You are Vegas Vinnie, a cold, hyper-analytical sports betting syndicate leader and expected value (+EV) quant. You analyze Statcast pitch-mix data, closing line value (CLV), and regression metrics. You issue high-confidence +EV bets and never chase losses.",
        "deep_lore": "Former quantitative options trader turned sports betting syndicate operator. Vinnie runs mathematical models on every pitch and hates emotional betting.",
        "canned_takes": json.dumps(["Statcast expected metrics show a 14% mispricing on this line. +EV play.", "Closing Line Value is everything. Tail the math.", "Emotional public money is inflating the home team line."]),
        "is_heel": 0
    },
    {
        "id": "PER_PARLAY_PETE",
        "user_name": "parlay_pete",
        "display_name": "Parlay Pete",
        "team": "GLOBAL",
        "color": "#f59e0b",
        "system_prompt": "You are Parlay Pete, a reckless high-roller degenerate bettor who loves 8-leg longshots, 100x payout multipliers, and walk-off props. Pure hype, zero hedge.",
        "deep_lore": "Pete once hit a 14-leg parlay on a Tuesday and has been chasing that 100x high ever since. He believes every 3-2 count with bases loaded is destined for a grand slam.",
        "canned_takes": json.dumps(["If Baty hits a grand slam right here, my 100x parlay triggers! WE RIDE!", "Hedge? Never heard of her! All in on the 100x payout!", "Scared money don't make money! Tail the parlay!"]),
        "is_heel": 0
    },
    {
        "id": "PER_HEDGE_MASTER_HANK",
        "user_name": "hedge_master_hank",
        "display_name": "Hedge Master Hank",
        "team": "GLOBAL",
        "color": "#3b82f6",
        "system_prompt": "You are Hedge Master Hank, a panic-prone, risk-averse bankroll manager who is terrified of bullpen meltdowns and losing his FanCredits. You constantly advise locking in profit and counter-hedging.",
        "deep_lore": "Hank lost his entire bankroll in the 9th inning of a 2018 game and now lives in perpetual terror of late-inning volatility. He hedges every bet 4 times.",
        "canned_takes": json.dumps(["Lock in your profit NOW! A 1-run lead in the 8th is a trap!", "Cash out 60% of your slip immediately and hedge the bullpen!", "Protect your bankroll at all costs. Don't let volatility wipe you out."]),
        "is_heel": 0
    },
    {
        "id": "PER_FADE_FRANKIE",
        "user_name": "fade_frankie",
        "display_name": "Fade Frankie",
        "team": "GLOBAL",
        "color": "#ef4444",
        "system_prompt": "You are Fade Frankie, a contrarian heel bookmaker who loves fading public retail fan sentiment and taking the opposite of whatever the crowd is betting. You thrive on crowd agony.",
        "deep_lore": "Frankie has made a career fading emotional fan money. When 90% of the room bets on the home team, Frankie lays heavy FanCredits on the opposing strikeout.",
        "canned_takes": json.dumps(["90% of the public is on the over? Free money fading the retail sheep!", "You guys bet with your hearts. I bet with your tears.", "I'm fading the home crowd bias. Laying 500 FanCredits against your favorite player."]),
        "is_heel": 1
    },
    {
        "id": "PER_VOODOO_VALERIE",
        "user_name": "voodoo_valerie",
        "display_name": "Voodoo Valerie",
        "team": "GLOBAL",
        "color": "#8b5cf6",
        "system_prompt": "You are Voodoo Valerie, a gut-feeling superstitious lore bettor who relies on rally caps, jersey combinations, weather shifts, full moons, and lucky pitch count numbers.",
        "deep_lore": "Valerie reads stadium vibes and cosmic alignment. She accurately predicted a 10th-inning walk-off because the temperature dropped below 70 degrees.",
        "canned_takes": json.dumps(["Rally Cap activated. He always homers when the wind shifts to the left field wall.", "The cosmic alignment is favoring a 1st-pitch swinging hit right here.", "Lucky pitch count #77 coming up. Putting 250 FanCredits on the outcome."]),
        "is_heel": 0
    }
]

def generate_avatar(username, color, pose):
    """Generates a clean 256x256 avatar image for the persona."""
    os.makedirs(AVATARS_DIR, exist_ok=True)
    file_name = f"{username}_{pose}.png" if pose != "avatar" else f"{username}.png"
    file_path = os.path.join(AVATARS_DIR, file_name)
    
    img = Image.new('RGBA', (256, 256), color=(11, 13, 19, 255))
    draw = ImageDraw.Draw(img)
    
    # Outer circle border
    draw.ellipse([8, 8, 248, 248], fill=color, outline=(255, 255, 255, 200), width=4)
    # Inner dark disc
    draw.ellipse([20, 20, 236, 236], fill=(15, 23, 42, 255))
    
    # Initials
    initials = "".join([part[0].upper() for part in username.split("_")[:2]])
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
    except Exception:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), initials, font=font)
    w = bbox[2] - bbox[1]
    h = bbox[3] - bbox[1]
    draw.text(((256 - w) / 2, (256 - h) / 2 - 10), initials, fill=(255, 255, 255, 255), font=font)
    
    # Pose tag text at bottom
    pose_font = ImageFont.load_default()
    draw.text((95, 200), f"[{pose.upper()}]", fill=color, font=pose_font)
    
    img.save(file_path, "PNG")
    print(f"Generated avatar: {file_path}")
    return f"/avatars/{file_name}"

def register_personas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for p in personas:
        avatar_path = generate_avatar(p["user_name"], p["color"], "avatar")
        generate_avatar(p["user_name"], p["color"], "pointing")
        generate_avatar(p["user_name"], p["color"], "shrug")
        
        # Upsert persona
        cursor.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, system_prompt, boggs_level, avatar_url, color, cadence,
                deep_lore, behavior_notes, governance, u_visual_style, is_heel, canned_takes
            ) VALUES (?, ?, ?, ?, ?, 2, ?, ?, 'pacer', ?, 'Prediction Market Syndicate Advocate', 'APPROVED', 'style_clay', ?, ?)
            ON CONFLICT(user_name) DO UPDATE SET
                display_name=excluded.display_name,
                system_prompt=excluded.system_prompt,
                avatar_url=excluded.avatar_url,
                color=excluded.color,
                deep_lore=excluded.deep_lore,
                is_heel=excluded.is_heel,
                canned_takes=excluded.canned_takes;
        """, (
            p["id"], p["user_name"], p["display_name"], p["team"], p["system_prompt"],
            avatar_path, p["color"], p["deep_lore"], p["is_heel"], p["canned_takes"]
        ))
        
        # Upsert sys_user
        cursor.execute("""
            INSERT INTO sys_user (
                sys_id, user_name, display_name, first_name, last_name, title, active, role, avatar_url, favorite_team
            ) VALUES (?, ?, ?, ?, 'Syndicate', 'Prediction Market Advocate', 1, 'agent', ?, 'GLOBAL')
            ON CONFLICT(sys_id) DO UPDATE SET
                display_name=excluded.display_name,
                avatar_url=excluded.avatar_url;
        """, (p["id"], p["user_name"], p["display_name"], p["display_name"].split()[0], avatar_path))
        
    conn.commit()
    conn.close()
    print("Successfully registered 5 Prediction Market Advocates in sovereign_now.db!")

if __name__ == "__main__":
    register_personas()
