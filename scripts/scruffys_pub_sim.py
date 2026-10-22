import asyncio
import websockets
import json
import os
import sys

async def scruffys_pub_sim(target_game_pk):
    try:
        # Load the chat log for context
        try:
            with open('/home/james/stacklabs/dna/dropzone/daily_21042026/wardy_tail.md', 'r') as f:
                chat_log = f.read()[-3000:] # Just grab the end
        except:
            chat_log = ""

        # Configure Gemini
        api_key = None
        with open('/home/james/stacklabs/.env') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
        
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are directing a highly toxic, dramatic post-game discussion at 'Scruffy's Pub'.
The Mets just lost their 12th game in a row (actually 13, but they say 12). They blew the lead in the 9th inning to Devin Williams and lost 5-3. 
The patrons are:
1. 'barf': He never even made it to the game. He's been at Scruffy's all day, deeply depressed, staring at his beer.
2. '7_train_terry': A classic WFAN caller, furious, screaming about firing Mendoza and Stearns.
3. 'uncle_stevie_stan': Arrogantly defending the owner (Steve Cohen) and the front office, calling everyone poor.
4. 'scruffy_bartender': The grumpy bartender who just wants them to stop crying and pay their tabs.

Your task: Generate a sequential back-and-forth conversation (at least 15 messages total) between these four characters reacting to the loss. Make it sound like a chaotic, authentic live stream chat. 
CRITICAL RULE: Each message MUST be under 200 characters.

Output exactly a JSON array of objects with keys: 'user' (must be exactly 'barf', '7_train_terry', 'uncle_stevie_stan', or 'scruffy_bartender'), 'text' (the message), 'color' (hex code for their username color).
"""

        print(f"🧠 Calling Gemini for the Scruffy's Pub simulation (Target Game PK: {target_game_pk})...")
        res = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.9
            )
        )
        import ast
        try:
            messages = json.loads(res.text)
        except:
            messages = ast.literal_eval(res.text)

        print(f"🔥 Generated {len(messages)} Scruffy's Pub messages. Injecting...")
        
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            for msg in messages:
                user = msg.get('user', 'barf')
                color = msg.get('color', '#FFFFFF')
                if user == 'barf': color = '#FF5910'
                if user == '7_train_terry': color = '#FF0000'
                if user == 'uncle_stevie_stan': color = '#0055FF'
                if user == 'scruffy_bartender': color = '#8B4513'
                
                payload = {
                    "type": "CHAT_MESSAGE",
                    "user": user,
                    "persona": user,
                    "color": color,
                    "text": msg.get('text', ''),
                    "target_game_pk": target_game_pk
                }
                await ws.send(json.dumps(payload))
                print(f"🚀 INJECTED [{user}]: {msg.get('text', '')}")
                await asyncio.sleep(2.5) # slower cadence for reading
                
            print("✅ Payload Delivery Complete.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    game_pk = sys.argv[1] if len(sys.argv) > 1 else "823640"
    asyncio.run(scruffys_pub_sim(game_pk))
