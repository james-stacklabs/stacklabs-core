import sqlite3
import shutil
import subprocess
import os
import time
import json
import sys
import asyncio
import google.genai as genai

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
STAGED_DIR = "/home/james/stacklabs/media_stack/ingest"

# Output Paths
WINNING_OUTPUT_SPORTS = "/home/james/stacklabs/19_Sovereign_Sports/public/videos/precog_winning.mp4"
WINNING_OUTPUT_SANDBOX = "/home/james/stacklabs-sandbox/catnip-wars/public/videos/precog_winning.mp4"

# Helper to dynamically fetch fallback assets from the vault
def get_fallback_asset(outcome, vault_dir):
    """
    Finds a fallback video in vault_dir for the given outcome.
    Scans the directory for any files matching *_3_2_{outcome}_v1.mp4.
    """
    import glob
    pattern = os.path.join(vault_dir, f"*_3_2_{outcome}_v1.mp4")
    matches = glob.glob(pattern)
    if matches:
        return sorted(matches)[0]
    return None

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None

def init_pregeneration(game_pk, batter, pitcher, batter_id=None, pitcher_id=None):
    """
    Called when count reaches 3-2. Generates/stages video vectors for the 4 outcomes.
    We check the permanent vault first to support instant, zero-compute local recall.
    """
    os.makedirs(STAGED_DIR, exist_ok=True)
    player_key = str(batter_id) if batter_id else batter.lower().replace(" ", "_")
    print(f"[PRECOG PRELOAD] Initializing pre-generation for {batter} vs {pitcher} in Game {game_pk} (Player key: {player_key})")
    
    vault_dir = "/home/james/stacklabs/media_vault/assets"
    os.makedirs(vault_dir, exist_ok=True)
    
    outcomes = ["strikeout", "walk", "in_play_out", "in_play_hit"]
    vault_files = {outcome: f"{vault_dir}/{player_key}_3_2_{outcome}_v1.mp4" for outcome in outcomes}
    
    all_cached = all(os.path.exists(path) for path in vault_files.values())
    
    if all_cached:
        print(f"[PRECOG] Vault HIT for player {player_key}! Bypassing API calls and copying pre-rendered assets...")
        for outcome in outcomes:
            shutil.copy(vault_files[outcome], f"{STAGED_DIR}/{game_pk}_{outcome}.mp4")
        print(f"[PRECOG] Multiverse staged for Game {game_pk} from vault.")
        return
        
    print(f"[PRECOG] Vault MISS for player {player_key}. Finding vault fallbacks dynamically...")
    
    for outcome in outcomes:
        dest_path = f"{STAGED_DIR}/{game_pk}_{outcome}.mp4"
        
        # Check if the player-specific file exists (though all_cached was False, some might exist)
        player_file = vault_files[outcome]
        if os.path.exists(player_file):
            shutil.copy(player_file, dest_path)
            print(f"[PRECOG] Staged player-specific asset for {outcome}: {player_file}")
            continue
            
        # Try dynamic fallback lookup in the vault
        fallback_file = get_fallback_asset(outcome, vault_dir)
        if fallback_file and os.path.exists(fallback_file):
            shutil.copy(fallback_file, dest_path)
            print(f"[PRECOG] Staged dynamic vault fallback for {outcome}: {fallback_file}")
        else:
            raise FileNotFoundError(f"[PRECOG ERROR] No asset (player-specific or fallback) found in {vault_dir} for outcome {outcome}!")
    
    # 2. Asynchronously fetch probabilities or prompts from Gemini
    prompt_str = f"Predictive MLB matchup: batter {batter} vs pitcher {pitcher}. Generate short dramatic captions (max 10 words) for 4 outcomes: Strikeout, Walk, In-Play Out, In-Play Hit."
    
    if client:
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt_str
            )
            print(f"[PRECOG Gemini] Generated prompts: {response.text}")
        except Exception as e:
            print(f"[PRECOG Gemini] Gemini call failed: {e}")
            
    print(f"[PRECOG PRELOAD] Video vectors successfully staged under {STAGED_DIR}")

def finalize_prediction(game_pk, batter, pitcher, actual_play_desc, batter_id=None, pitcher_id=None):
    """
    Called when the pitch outcome arrives. Identifies the winning vector,
    applies the ffmpeg dynamic overlay, copies to sports public folder, and
    vaults all clean outcomes to media_vault.
    """
    actual_play_lower = actual_play_desc.lower()
    
    # Determine which vector won
    winning_outcome = None
    if "strike" in actual_play_lower or "struck" in actual_play_lower or "strikeout" in actual_play_lower:
        winning_outcome = "strikeout"
        dynamic_text = f"{batter} strikes out on a full count pitch from {pitcher}!"
    elif "walk" in actual_play_lower or "base on balls" in actual_play_lower or "hit by pitch" in actual_play_lower or "hbp" in actual_play_lower:
        winning_outcome = "walk"
        if "hit by pitch" in actual_play_lower or "hbp" in actual_play_lower:
            dynamic_text = f"{batter} is hit by pitch vs {pitcher}!"
        else:
            dynamic_text = f"{batter} draws a patient full count Walk vs {pitcher}!"
    elif any(h in actual_play_lower for h in ["hit", "single", "double", "triple", "home run", "homer", "run", "scores"]):
        if any(o in actual_play_lower for o in ["out", "flyout", "groundout", "lineout", "popout", "fielder's choice", "fielders choice", "double play"]):
            winning_outcome = "in_play_out"
            dynamic_text = f"{batter} puts it in play but is out vs {pitcher}!"
        else:
            winning_outcome = "in_play_hit"
            dynamic_text = f"{batter} hits a base hit vs {pitcher}!"
    else:
        if any(o in actual_play_lower for o in ["out", "flyout", "groundout", "lineout", "popout", "fielder's choice", "fielders choice", "double play"]):
            winning_outcome = "in_play_out"
            dynamic_text = f"{batter} puts it in play but is out vs {pitcher}!"
        else:
            winning_outcome = "in_play_out"
            dynamic_text = f"Payoff pitch: {actual_play_desc}"
        
    staged_winning_file = f"{STAGED_DIR}/{game_pk}_{winning_outcome}.mp4"
    if not os.path.exists(staged_winning_file):
        # If not staged yet, copy templates now
        init_pregeneration(game_pk, batter, pitcher, batter_id, pitcher_id)
        
    # Run FFMPEG overlay on the winning video
    start_time = time.time()
    try:
        os.makedirs(os.path.dirname(WINNING_OUTPUT_SPORTS), exist_ok=True)
        os.makedirs(os.path.dirname(WINNING_OUTPUT_SANDBOX), exist_ok=True)
        escaped_text = dynamic_text.replace("'", "'\\''")
        
        # Primary output
        cmd = [
            "ffmpeg", "-y", "-i", staged_winning_file,
            "-vf", f"drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeSansBold.ttf:text='{escaped_text}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=h-80",
            "-codec:a", "copy", "-preset", "ultrafast", WINNING_OUTPUT_SPORTS
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Sandbox output copy
        shutil.copy(WINNING_OUTPUT_SPORTS, WINNING_OUTPUT_SANDBOX)
        
        duration = time.time() - start_time
        print(f"[PRECOG] FFMPEG overlay completed in {duration:.2f}s (<800ms metric check: {duration < 0.8})")
    except Exception as e:
        print(f"[PRECOG ERROR] FFMPEG overlay failed: {e}")
        try:
            shutil.copy(staged_winning_file, WINNING_OUTPUT_SPORTS)
            shutil.copy(staged_winning_file, WINNING_OUTPUT_SANDBOX)
        except Exception as copy_err:
            print(f"[PRECOG ERROR] Staged copy fallback failed: {copy_err}")
        
    # Permanent Vaulting: Copy clean staged outcomes to the vault for future zero-compute recall
    player_key = str(batter_id) if batter_id else batter.lower().replace(" ", "_")
    vault_dir = "/home/james/stacklabs/media_vault/assets"
    for outcome in ["strikeout", "walk", "in_play_out", "in_play_hit"]:
        staged_file = f"{STAGED_DIR}/{game_pk}_{outcome}" + ".mp4"
        vault_file = f"{vault_dir}/{player_key}_3_2_{outcome}_v1.mp4"
        if os.path.exists(staged_file):
            if not os.path.exists(vault_file):
                try:
                    shutil.copy(staged_file, vault_file)
                    print(f"[PRECOG] Vaulted clean asset: {vault_file}")
                except Exception as vault_err:
                    print(f"[PRECOG ERROR] Failed to vault asset: {vault_err}")
        
    # Drop incorrect prediction paths into sys_predictive_cache database table
    try:
        conn = sqlite3.connect(DB_PATH)
        for outcome in ["strikeout", "walk", "in_play_out", "in_play_hit"]:
            if outcome != winning_outcome:
                cached_path = f"{STAGED_DIR}/{game_pk}_{outcome}.mp4"
                conn.execute(
                    "INSERT INTO sys_predictive_cache (game_pk, batter, pitcher, outcome, video_path) VALUES (?, ?, ?, ?, ?)",
                    (str(game_pk), batter, pitcher, outcome, cached_path)
                )
        conn.commit()
        conn.close()
        print(f"[PRECOG] Unused prediction paths successfully cached in sys_predictive_cache.")
    except Exception as e:
        print(f"[PRECOG ERROR] Failed to cache prediction paths: {e}")
        
    return dynamic_text

async def daemon_loop():
    import websockets
    ws_url = "ws://localhost:8008"
    print(f"[PRECOG DAEMON] Starting daemon loop, connecting to {ws_url}...")
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                print("[PRECOG DAEMON] Connected to WebSocket relay server.")
                await ws.send(json.dumps({"type": "JOIN_ROOM", "room": "GLOBAL"}))
                
                async for message_str in ws:
                    try:
                        data = json.loads(message_str)
                    except Exception as parse_err:
                        print(f"[PRECOG DAEMON] Failed to parse message: {parse_err}")
                        continue
                        
                    msg_type = data.get("type")
                    if msg_type == "MULTIVERSE_PREP":
                        game_pk = data.get("game_pk")
                        batter = data.get("batter")
                        pitcher = data.get("pitcher")
                        batter_id = data.get("batter_id")
                        pitcher_id = data.get("pitcher_id")
                        print(f"[PRECOG DAEMON] Received MULTIVERSE_PREP: {batter} vs {pitcher} in Game {game_pk} (Batter ID: {batter_id})")
                        
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None, init_pregeneration, game_pk, batter, pitcher, batter_id, pitcher_id
                        )
                        
                    elif msg_type == "MULTIVERSE_SETTLE":
                        game_pk = data.get("game_pk")
                        batter = data.get("batter")
                        pitcher = data.get("pitcher")
                        play_desc = data.get("play_desc")
                        batter_id = data.get("batter_id")
                        pitcher_id = data.get("pitcher_id")
                        print(f"[PRECOG DAEMON] Received MULTIVERSE_SETTLE: {play_desc} in Game {game_pk}")
                        
                        loop = asyncio.get_event_loop()
                        dyn_text = await loop.run_in_executor(
                            None, finalize_prediction, game_pk, batter, pitcher, play_desc, batter_id, pitcher_id
                        )
                        
                        # Broadcast winning video to live chat with cache-busting timestamp
                        video_msg = {
                            "type": "CHAT_MESSAGE",
                            "user": "SOVEREIGN ORACLE",
                            "persona": "oracle",
                            "color": "#A78BFA",
                            "text": f"🔮 PRECOG REALIZED: {dyn_text}",
                            "target_game_pk": str(game_pk),
                            "image": f"/videos/precog_winning.mp4?t={int(time.time())}",
                            "is_telemetry": True
                        }
                        await ws.send(json.dumps(video_msg))
                        print("[PRECOG DAEMON] Broadcasted winning realized video message.")
                        
        except Exception as conn_err:
            print(f"[PRECOG DAEMON ERROR] Connection error: {conn_err}. Reconnecting in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        try:
            asyncio.run(daemon_loop())
        except KeyboardInterrupt:
            print("[PRECOG DAEMON] Stopped by keyboard interrupt.")
    else:
        # Command line manual debug mode helper
        if len(sys.argv) >= 5:
            cmd = sys.argv[1]
            if cmd == "init":
                init_pregeneration(sys.argv[2], sys.argv[3], sys.argv[4])
            elif cmd == "finalize":
                finalize_prediction(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        else:
            print("Usage: python3 precog_pipeline.py --daemon OR python3 precog_pipeline.py [init/finalize] ...")
