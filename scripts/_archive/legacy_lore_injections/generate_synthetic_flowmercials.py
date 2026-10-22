import os
import google.generativeai as genai

api_key = None
try:
    with open('/home/james/stacklabs/.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                api_key = line.strip().split('=', 1)[1]
except Exception:
    pass

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

PROMPT = """
You are Vanguard, the elite AI Video Production engine for Sovereign FanStack.
We need to generate Google Veo "Flowmercial" video generation prompts based on a provided chat log.

CRUCIAL RULE (The Brooks Exception): We cannot use real MLB IP or human likenesses. 
Every prompt must exclusively frame the characters in the aesthetic style of "1990s physical felt puppets" (like violent, feral muppets from a dark comedy).

Provide exactly 3 highly cinematic, 15-second video prompts describing visual actions. 
Do not write dialogue. Frame it as camera directions for a video AI (e.g. "A tracking shot of a sweat-drenched, blue-and-orange 1990s physical felt puppet screaming...").
Focus heavily on the emotional breakdowns, fighting, and chaos seen in the chat context. 

CHAT CONTEXT:
{chat}
"""

def generate():
    try:
        with open("/home/james/stacklabs/dna/dropzone/daily_19042026/raw_dump.md", "r") as f:
            chat = f.read()
            
        print("Synthesizing Flowmercial Prompts from DNA Dropzone...")
        response = model.generate_content(PROMPT.replace("{chat}", chat))
        
        with open("/home/james/stacklabs/dna/dropzone/daily_19042026/FLOWMERCIAL_PROMPTS.md", "w") as out:
            out.write("# GENERATED FLOWMERCIAL / VEO PROMPTS\n\n")
            out.write(response.text)
            
        print("Success! Prompts generated to FLOWMERCIAL_PROMPTS.md")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    generate()
