import asyncio
import websockets
import json
import sqlite3
import os
import requests
import random
import time

GEMINI_KEY = None
try:
    with open('/home/james/stacklabs/.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                GEMINI_KEY = line.strip().split('=', 1)[1]
except Exception:
    pass

GAME_TIME_MODEL = "gemini-flash-latest"

def load_golf_fans():
    fans_list = []
    try:
        conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT c.name, c.short_description, p.u_system_prompt, p.u_boggs_reactivity, c.operational_status, c.assigned_to, p.u_cadence, p.u_is_sophisticated
            FROM cmdb_ci c
            LEFT JOIN cmdb_ci_ai_persona p ON c.sys_id = p.sys_id
            WHERE c.sys_class_name = 'cmdb_ci_ai_persona' AND c.operational_status = 1 AND c.assigned_to = 'golf_room'
        ''')
        rows = c.fetchall()
        conn.close()
        
        for r in rows:
            name = str(r['name'])
            color = "#D4AF37" # Default Gold
            name_lower = name.lower()
            if "traditionalist" in name_lower: color = "#FFFFFF" # White
            elif "gambler" in name_lower: color = "#FF5910" # Orange
            elif "truther" in name_lower: color = "#FF0000" # Red (Tiger Sunday)
            elif "victim" in name_lower: color = "#006747" # Augusta Green
            
            fans_list.append({
                "name": name,
                "personality": str(r['short_description']),
                "model": GAME_TIME_MODEL,
                "color": color,
                "boggs_level": 2,
                "cadence": str(r['u_cadence']).lower() if r['u_cadence'] else "pacer",
                "is_sophisticated": int(r['u_is_sophisticated'] or 0)
            })
    except Exception as e:
        print(f"Error loading SNOW DB config: {e}")
    return fans_list

def get_local_fallback_yap(fan):
    import random
    name = fan.get("name", "").lower() if fan else ""
    if "traditionalist" in name:
        yaps = [
            "Tattered tethers! Modern graphite shafts are ruining the telemetry signals. It was better in 1934.",
            "Quiet! Someone's running on the second cut and blocking the radio tower. Respect the game!",
            "Adherence to rule 14-2. The transmission must be paused for decorum. Stand by."
        ]
    elif "gambler" in name:
        yaps = [
            "Oh god, the screen froze! Did Rose make par? My 8-leg parlay is riding on this hole!",
            "Lag spike! Waffle syrup is all over my betting slip! Please tell me he didn't bogey 12!",
            "My hedge bet is in absolute ruins if this feed doesn't load. Panic!"
        ]
    elif "slopematrix" in name:
        yaps = [
            "Topographic calculation halted. Local processing queue flooded. Stimp index constant at 12.5.",
            "DimensionMismatchException caught in Bermuda grass vectors. Re-calculating break...",
            "Geometric failure: 0.04% grain deviation detected. Telemetry packet dropped by Sentinel."
        ]
    elif "breakfast" in name:
        yaps = [
            "My telemetry is perfect, you just can't afford the subscription. Go back to your shanty.",
            "I've hit better shots off a Volkswagen in a parking lot. This delay is beneath my standards.",
            "The Marksman of the Greens doesn't wait for lag. I'm having waffles, fix the server."
        ]
    elif "defector" in name:
        yaps = [
            "Antiquated 72-hole telemetry. This is why LIV shotgun starts are the future! The OWGR is rigged.",
            "My guaranteed contract doesn't cover connection delays. Speak to my agent.",
            "Cut-lines are archaic anyway. Let the sharks eat while the PGA servers crash."
        ]
    elif "shrubbs" in name:
        yaps = [
            "They're listening through the azaleas... I know the Augusta National scouts are in the Cincy grounds crew!",
            "The 1993 Heritage incident is not public record! Why are you asking? Quiet on the tee, they are watching!",
            "Did you hear that static? That's not a connection timeout, that's a wiretap on the clubhouse router!"
        ]
    elif "peterson" in name:
        yaps = [
            "Flow with the friction! The humidity is cutting the signal, but keep your stance stable.",
            "Quiet under pressure. Let the panic pass, the telemetry will realign."
        ]
    else:
        yaps = [
            "Hushed silence. Please stand by for connectivity restore.",
            "Apologies for the transmission lag on the links.",
            "Standard connection timeout. Quiet on the tee."
        ]
    return random.choice(yaps)

async def generate_response(model, prompt, system_instruction=None, fan=None):
    if not GEMINI_KEY:
        print("NO GEMINI KEY")
        return get_local_fallback_yap(fan)
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_KEY}"
        sys_text = system_instruction if system_instruction else "You are a golf fan in a fast live chat. One short sentence only. No quotes or brackets."
        
        # Extract Boggs Level
        sys_str = system_instruction or ""
        active_boggs = 2
        if "Level MAX" in sys_str or "Level 5" in sys_str:
            active_boggs = 5
        elif "Level 4" in sys_str:
            active_boggs = 4
        elif "Level 3" in sys_str:
            active_boggs = 3
        elif "Level Low" in sys_str or "Level 0" in sys_str or "Level 1" in sys_str or "Level 2" in sys_str:
            active_boggs = 2

        # Extract Sophistication
        is_sophisticated = int(fan.get("is_sophisticated", 0)) == 1 if fan else False

        # Calculate max_output_tokens
        if active_boggs >= 5:
            max_tokens = 150 if is_sophisticated else 80
        elif active_boggs >= 4:
            max_tokens = 80 if is_sophisticated else 60
        elif active_boggs >= 3:
            max_tokens = 45
        else:
            max_tokens = 30

        payload = {
            "systemInstruction": {"parts": [{"text": sys_text}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9, "maxOutputTokens": max_tokens}
        }
        res = await asyncio.to_thread(requests.post, url, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["candidates"][0]["content"]["parts"][0]["text"].replace('\n', ' ').strip()
        else:
            print(f"[Vertex API Error] Status: {res.status_code} - {res.text}")
            return get_local_fallback_yap(fan)
    except Exception as e:
        print(f"[LLM Error on {model}]: {e}")
        return get_local_fallback_yap(fan)

async def generate_commentary(model, prompt, user, color, websocket, sys_override=None, fan=None):
    start = time.time()
    text = await generate_response(model, prompt, sys_override, fan=fan)
    if text:
        msg = {
            "type": "CHAT_MESSAGE",
            "user": user,
            "color": color,
            "text": text
        }
        await websocket.send(json.dumps(msg))
        print(f"[{user}] {text}")

def get_boggs_rule(fan, global_boggs, status_text=""):
    active_boggs = global_boggs
    if "hole in one" in status_text.lower() or "eagle" in status_text.lower():
        active_boggs = 5
        
    is_sophisticated = int(fan.get("is_sophisticated", 0)) == 1

    if is_sophisticated:
        if active_boggs >= 5:
            return "CRITICAL INSTRUCTION: Boggs Level MAX. Write a detailed, urgent, pseudo-scientific or technical thesis abstract discussing systemic entropy, software panic, or structural degradation. Feel free to use complex acronyms and intense academic vocabulary. DO NOT TYPE IN ALL CAPS. Maximum 100 words."
        elif active_boggs >= 4:
            return "CRITICAL INSTRUCTION: Boggs Level 4. Highly analytical and formal. Compose exactly 2 complex sentences using formal academic jargon, system architecture references, or clinical analysis. Do not use all-caps except for specific proper nouns."
        elif active_boggs >= 3:
            return "CRITICAL INSTRUCTION: Boggs Level 3. Formal academic style. Limit response to EXACTLY 1 grammatically precise sentence."
        else:
            return "CRITICAL INSTRUCTION: Boggs Level Low. Maintain a calm, analytical, and highly structured academic perspective. Keep your response under 15 words."
    else:
        if active_boggs >= 5:
            return "CRITICAL INSTRUCTION: Boggs Level MAX. Maximum hype or panic. Type entirely in ALL CAPS. Maximum 30 words."
        elif active_boggs >= 4:
            return "CRITICAL INSTRUCTION: Boggs Level 4. Tense. Limit response to 2 sentences."
        else:
            return "CRITICAL INSTRUCTION: Boggs Level Low. Maintain a hushed, perfectly calm, and controlled conversational tone (Golf Voice). KEEP YOUR RESPONSE UNDER 15 WORDS."

async def chatbot_loop():
    uri = "ws://127.0.0.1:8009"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Masters MARD Engine Connected to Relay (Port 8009)!")
                
                last_status = ""
                
                async for message in websocket:
                    data = json.loads(message)
                    active_fans = load_golf_fans()
                    
                    if data.get("type") == "STATE_UPDATE":
                        state = data.get("data", {})
                        status = state.get("status_msg", "")
                        global_boggs = state.get("boggs_level", 2)
                        
                        if status and status != last_status:
                            last_status = status
                            print(f"[PLAY INTERCEPT] Reaction to: {status}")
                            
                            for fan in active_fans:
                                cadence = fan.get("cadence", "pacer")
                                
                                trigger_chance = 0.0
                                if "hole in one" in status.lower() or "eagle" in status.lower() or "bogey" in status.lower():
                                    trigger_chance = 1.0 # High tension
                                elif cadence == "lurker": trigger_chance = 0.1
                                elif cadence == "pacer": trigger_chance = 0.4
                                else: trigger_chance = 0.7 # yapper
                                
                                if random.random() <= trigger_chance:
                                    print(f"[PLAY INTERCEPT] Triggering reaction for {fan['name']} (chance: {trigger_chance})")
                                    boggs_rule = get_boggs_rule(fan, global_boggs, status)
                                    prompt = f"System Persona: You are '{fan['name']}'. '{fan['personality']}'. {boggs_rule} Provide a golf chat reaction to this update: {status}"
                                    asyncio.create_task(generate_commentary(fan['model'], prompt, fan['name'], fan['color'], websocket, sys_override=fan.get("personality"), fan=fan))
                                else:
                                    print(f"[PLAY INTERCEPT] Skipping reaction for {fan['name']} (chance: {trigger_chance})")
        except websockets.exceptions.ConnectionClosedError:
            print("Chatbot Disconnected...")
        except Exception as e:
            print(f"Chatbot Error: {e}")
        finally:
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(chatbot_loop())
