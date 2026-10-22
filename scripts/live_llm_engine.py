import asyncio
import websockets
import json
import os
from google import genai
from google.genai import types# Parse .env manually to avoid dependency requirement
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY=') or line.startswith('VITE_GEMINI_API_KEY='):
                key = line.strip().split('=')[1]
                if key:
                    os.environ['GEMINI_API_KEY'] = key

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env. Engine aborted.")

client = genai.Client(api_key=api_key)

CONTEXT_DB = "/home/james/stacklabs/dna/context_database.json"

def get_system_prompt():
    base_prompt = """You are the Sovereign M.A.R.D. Engine orchestrating a live 5-persona sports debate about the New York Mets.
The current topic: The Mets are on a brutal 11-game losing streak this season. The fandom is trying to apply the successful '2024 Lindor Standing Ovation' magic to the entire team tomorrow at Citi Field to break the skid.

The 5 Personas:
1. Dot: An AI analyst calculating probability.
2. WardyIcon: A high-strung but optimistic fan. He believes giving the ENTIRE TEAM a standing ovation, just like they did for Lindor to break his 2024 slump, will spark a massive winning run.
3. UncleStevieStan: A loyalist who defends Steve Cohen's wealth and algorithms.
4. Terry: A boomer fanatic complaining from the Long Island Railroad.
5. Barf: A toxic, chaotic doomer who loves knowing the team is cursed.

Your job is to generate the NEXT single line of dialogue. Choose the most appropriate persona to speak next.
Keep dialogue punchy, short, and suited for a TV graphic (2-3 sentences max).

Reply ONLY with a raw JSON object in this EXACT format (no markdown, no backticks):
{
  "author": "Name of Persona",
  "text": "Their dialogue",
  "reaction_image": "Must be exactly one of: /avatars/dot.png, /avatars/wardyicon.png, /avatars/unclesteviestan.png, /avatars/terry.png, /avatars/barf.png"
}
"""
    
    # Inject real-world MLB news to prevent hallucinations
    news_context = "\n\nREAL-WORLD MLB NEWS CONTEXT (Use this to ground the debate. Do not hallucinate events):\n"
    if os.path.exists(CONTEXT_DB):
        try:
            with open(CONTEXT_DB, 'r') as f:
                data = json.load(f)
                news_items = data.get("mlb_news", [])
                if news_items:
                    for idx, item in enumerate(news_items, 1):
                        news_context += f"{idx}. {item['title']}: {item['summary']}\n"
                else:
                    news_context += "No current news.\n"
        except Exception:
            news_context += "Error loading news.\n"
            
    return base_prompt + news_context

# We use generate_content with a manual rolling history to prevent geometric API cost explosions.
rolling_history = []
cross_talk_enabled = True

async def generate_next_turn(websocket, prompt="Next speaker in the argument."):
    global rolling_history
    try:
        # Build the conversation history with a strict 5-turn limit to prevent API billing spikes
        contents = [types.Content(role="user", parts=[types.Part.from_text(prompt)])]
        for past_msg in rolling_history[-5:]:
            contents.insert(0, types.Content(role="model", parts=[types.Part.from_text(past_msg)]))
            
        config = types.GenerateContentConfig(
            system_instruction=get_system_prompt(),
            temperature=1.0,
        )
        
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=contents,
            config=config
        )
        
        parts_text = []
        if response and response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
        if parts_text:
            text = "".join(parts_text)
        else:
            try:
                text = response.text or ""
            except Exception:
                text = ""
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        
        # Add to rolling history
        rolling_history.append(json.dumps(data))
        if len(rolling_history) > 5:
            rolling_history.pop(0)
        
        payload = {
            "type": "CHAT_MSG",
            "author": data["author"],
            "text": data["text"]
        }
        if "reaction_image" in data:
             payload["reaction_image"] = data["reaction_image"]
             
        await websocket.send(json.dumps(payload))
        print(f"[{payload['author']}] {payload['text']}")
        
    except Exception as e:
        print(f"[!] Engine Error (Parsing/API): {e}")
        try:
            print(f"Raw Output: {response.text}")
        except:
            pass

async def listen_to_ws(websocket):
    global cross_talk_enabled
    async for message in websocket:
        try:
            data = json.loads(message)
            if data.get("type") == "CHAT_MSG" and data.get("author") == "PRODUCER":
                cross_talk_enabled = data.get("cross_talk", True)
                directive = data.get("text", "")
                
                print(f"\n>> [OVERRIDE DETECTED] PRODUCER: '{directive}' (CrossTalk: {cross_talk_enabled})\n")
                
                prompt = f"PRODUCER INJECTION: You must abruptly change the subject and react to this statement immediately: '{directive}'"
                
                # Interrupt and force generation right now based on Producer Directive
                await generate_next_turn(websocket, prompt=prompt)
        except Exception:
            pass

async def conversation_loop(websocket):
    global cross_talk_enabled
    turns = 0
    while turns < 40:
        if cross_talk_enabled:
            # Pacing Governor: 10 seconds per chat to allow UI bubbles to breathe on TV and match natural conversation flow.
            await asyncio.sleep(10)
            await generate_next_turn(websocket, prompt="Continue the argument naturally with a different persona.")
            turns += 1
        else:
            await asyncio.sleep(1)
    print("\n[SAFEGUARD] Reached max 40 iterations. Pausing engine to protect API $25 spend.")

async def main():
    uri = "ws://127.0.0.1:8008"
    print("Sovereign Live LLM Engine Connecting...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("=======================================")
            print("THE SOVEREIGN AM SHOW IS LIVE ON AIR")
            print("=======================================")
            print("Awaiting 15-minute infinite talk show loop...\n")
            
            # Kick off the conversation
            await generate_next_turn(websocket, prompt="Start the broadcast. Set the miserable scene about the 11-game losing streak.")
            
            listener_task = asyncio.create_task(listen_to_ws(websocket))
            loop_task = asyncio.create_task(conversation_loop(websocket))
            
            await asyncio.gather(listener_task, loop_task)
            
    except ConnectionRefusedError:
         print("[!] ERROR: fancast_relay is offline on port 8000.")

if __name__ == "__main__":
    asyncio.run(main())
