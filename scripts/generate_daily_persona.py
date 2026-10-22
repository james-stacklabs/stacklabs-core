import os
import datetime
import json
import vertexai
from vertexai.generative_models import GenerativeModel

def main():
    print(f"[{datetime.datetime.now()}] Initializing Daily Persona Generation...")
    
    context_path = "/home/james/stacklabs/scripts/fanstack_live_context.txt"
    out_path = f"/home/james/sovereign_inbox/today/NEW_PERSONA_{datetime.datetime.now().strftime('%Y%m%d')}.md"
    
    context_text = ""
    if os.path.exists(context_path):
        with open(context_path, 'r') as f:
            context_text = f.read()
            
    if not context_text.strip():
        context_text = "No specific news today. Invent a random unhinged MLB fan for a random team."
        
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/james/stacklabs/config/vertex_sa.json"
    try:
        vertexai.init(project="gen-lang-client-0840454416", location="us-central1")
    except Exception as e:
        print(f"Vertex AI init failed: {e}")
        return

    sys_instr = """
    You are an expert persona designer for a multi-agent MLB fan simulation. 
    Based on the recent MLB news provided, pick a team that had a notable event (upset, blowout, etc) and design a brand new unhinged, highly opinionated fan persona for that team.
    Format your response EXACTLY as a Markdown document with these sections:
    # [Name of Persona] ([Team])
    **Suggested X Handle:** @[Handle]
    **Suggested Gmail:** [email]@gmail.com
    **Bio/Origin Story:** [2-3 sentences of deep lore/unhinged fandom]
    **Profile Pic Prompt:** [Detailed image generation prompt for their avatar]
    """
    
    prompt = f"Recent MLB News:\n{context_text}\n\nGenerate the Daily Persona Blueprint."
    
    print("Calling Vertex AI for Persona Blueprint...")
    model = GenerativeModel("gemini-flash-latest", system_instruction=[sys_instr])
    
    try:
        response = model.generate_content(prompt, generation_config={"temperature": 0.9})
        blueprint = response.text.strip()
        
        with open(out_path, 'w') as f:
            f.write(blueprint)
            
        print(f"Successfully generated Daily Persona Blueprint at: {out_path}")
    except Exception as e:
        print(f"Failed to generate persona: {e}")

if __name__ == "__main__":
    main()
