import asyncio
import websockets
import json
import os
import google.generativeai as genai

async def nuke_chat():
    try:
        # Load the chat log
        with open('/home/james/stacklabs/dna/dropzone/daily_21042026/wardy_tail.md', 'r') as f:
            chat_log = f.read()

        # Load Barf's Deep Lore
        try:
            with open('/home/james/stacklabs/dna/agents/personas/barf.md', 'r') as f:
                barf_lore = f.read()
        except:
            barf_lore = "You are an eternally suffering, manic New York Mets fan who constantly references historical traumas like 2007, the Wilpons, and Bobby Bonilla."

        # Configure Gemini
        api_key = None
        with open('/home/james/stacklabs/.env') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json", "temperature": 1.0})
        
        prompt = f"""You are BARF, the most manic, traumatized, and dramatic Mets fan in existence. 
Your Deep Lore: {barf_lore}

You are currently watching a live stream where the Mets just lost their 13th game in a row. The fans in the chat are melting down. 
Here is the live chat log:
{chat_log}

Your task: Generate exactly 7 highly reactive, short, punchy chat messages reacting directly to this horrific loss. 
CRITICAL RULE: DO NOT REPEAT YOURSELF. YOU MUST GENERATE COMPLETELY NEW, ORIGINAL THOUGHTS. Do not use the phrases "Same old mets", "cosmic joke", "familia in 2015", "spiritual sickness", or "recurring nightmare". 

Instead, tap into deep, obscure Mets lore. Talk about Bobby Bonilla day, the 2007 collapse against the Marlins, Luis Castillo dropping the pop-up against the Yankees, Endy Chavez's catch being in vain, generation K, Mo Vaughn's injury, Jason Bay's contract, or Kaz Matsui. Go totally unhinged. Do not use hashtags or emojis. Keep each message under 2 sentences. 

Output exactly a JSON array of 7 string messages."""

        print("🧠 Calling Gemini for Barf's manic reactions...")
        res = model.generate_content(prompt)
        import ast
        try:
            messages = json.loads(res.text)
        except:
            messages = ast.literal_eval(res.text)

        print(f"🔥 Generated {len(messages)} Barf payloads. Nuking Wardy's chat...")
        
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            for msg in messages:
                payload = {
                    "type": "CHAT_MESSAGE",
                    "user": "barf",
                    "persona": "barf",
                    "color": "#FF5910",
                    "text": msg,
                    "target_game_pk": "823640"
                }
                await ws.send(json.dumps(payload))
                print(f"🚀 INJECTED: {msg}")
                await asyncio.sleep(1.5)
                
            print("✅ Payload Delivery Complete.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(nuke_chat())
