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

        # Load Stevie's Deep Lore
        try:
            with open('/home/james/stacklabs/dna/agents/personas/uncle_stevie_stan.md', 'r') as f:
                stevie_lore = f.read()
        except:
            stevie_lore = "You are an arrogant, loyal defender of billionaire owner Steve Cohen and his front office. You trust the analytics and think doomers are poor and stupid."

        # Configure Gemini
        api_key = None
        with open('/home/james/stacklabs/.env') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json", "temperature": 1.0})
        
        prompt = f"""You are Uncle Stevie Stan. 
Your Deep Lore: {stevie_lore}

You are currently watching a live stream where the Mets just lost their 13th game in a row. The fans in the chat are melting down, calling for David Stearns to be fired, cursing Mendoza, and giving up on the team.
Here is the live chat log:
{chat_log}

Your task: Generate exactly 7 highly reactive, short, punchy chat messages directly attacking the "doomer" fans in this chat. 
CRITICAL RULE: You must aggressively defend Steve Cohen ("Uncle Stevie") and David Stearns. Call the fans poor, impatient, or statistically illiterate. Remind them that Uncle Stevie has infinite money, that 13 games is just a small sample size variance, and that the long-term vision is intact. Brag about how much money Cohen has compared to them. Tell them to go root for the Yankees if they can't handle the 'process'. Do not use hashtags or emojis. 

SUPER CRITICAL: Every single message MUST be strictly under 200 characters total. No exceptions. Keep them short, punchy, and extremely arrogant. 

Output exactly a JSON array of 7 string messages."""

        print("🧠 Calling Gemini for Uncle Stevie Stan's arrogant defense...")
        res = model.generate_content(prompt)
        import ast
        try:
            messages = json.loads(res.text)
        except:
            messages = ast.literal_eval(res.text)

        print(f"🔥 Generated {len(messages)} Uncle Stevie Stan payloads. Nuking Wardy's chat...")
        
        async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
            for msg in messages:
                payload = {
                    "type": "CHAT_MESSAGE",
                    "user": "uncle_stevie_stan",
                    "persona": "uncle_stevie_stan",
                    "color": "#0055FF",
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
