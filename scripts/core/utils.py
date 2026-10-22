"""Shared helpers used across multiple routers."""
import os
import re
import json


def _et_game_date() -> str:
    """Return the active game-slate date in Eastern time.
    Before 10 AM ET we're still on the previous day's slate —
    MLB doesn't publish a new schedule until ~10 AM ET."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    from datetime import datetime, timedelta
    now_et = datetime.now(ZoneInfo('America/New_York'))
    if now_et.hour < 10:
        return (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    return now_et.strftime('%Y-%m-%d')



async def run_vertex_prompt(prompt: str, system_instruction: str = "") -> str:
    import os
    import asyncio
    from google import genai
    from google.genai import types
    
    v_key = os.environ.get("VERTEX_API_KEY")
    g_key = os.environ.get("GEMINI_API_KEY")
    if not v_key or not g_key:
        try:
            with open('/home/james/stacklabs/.env') as f:
                for line in f:
                    if line.startswith('VERTEX_API_KEY=') and not v_key:
                        v_key = line.strip().split('=', 1)[1].strip('"\'')
                    elif line.startswith('GEMINI_API_KEY=') and not g_key:
                        g_key = line.strip().split('=', 1)[1].strip('"\'')
        except Exception:
            pass
            
    if g_key:
        client = genai.Client(api_key=g_key)
    elif v_key:
        client = genai.Client(vertexai=True, api_key=v_key)
    else:
        raise RuntimeError("No VERTEX_API_KEY or GEMINI_API_KEY configured.")
        
    def _call_gemini():
        sys_prompt = system_instruction or "You are a brand intelligence assistant for Sovereign OS."
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.7,
        )
        res = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=config
        )
        return res.text or ""
        
    return await asyncio.to_thread(_call_gemini)

def parse_json_garbage(text: str) -> dict:
    import json
    import re
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    cleaned = text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)
