#!/usr/bin/env python3
import os
import requests
import json
import urllib.parse

# Load GEMINI_API_KEY
GEMINI_KEY = None
try:
    with open('/home/james/stacklabs/.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                GEMINI_KEY = line.strip().split('=', 1)[1]
except Exception:
    pass

SYSTEM_PROMPT = (
    "You are Manuel, an energetic, helpful Hispanic AI Agent whose sole purpose is to serve as the orientation guide "
    "for the Sovereign Media Cinema Portal. Help non-technical users request movies, check download speeds, and explain "
    "queue sizes with high energy and clarity."
)

def get_sabnzbd_status():
    """Fetches download queue and speed from local SABnzbd instance."""
    url = "http://clio.taila01894.ts.net:8081/api?mode=queue&apikey=4ee070eb74734e9f9f02143533be6bdd&output=json"
    try:
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            queue = data.get("queue", {})
            speed = queue.get("speed", "0")
            sizeleft = queue.get("sizeleft", "0")
            slots = queue.get("slots", [])
            
            # Check if speed is effectively zero
            is_zero_speed = False
            if not speed or speed.strip() == "0" or "0 KB" in speed or "0.00" in speed:
                is_zero_speed = True
                
            return {
                "speed": speed,
                "size_left": sizeleft,
                "slots_count": len(slots),
                "is_zero_speed": is_zero_speed,
                "raw_queue": queue
            }
    except Exception as e:
        print(f"[Manuel Agent] Failed to query SABnzbd: {e}")
        
    return {
        "speed": "0",
        "size_left": "0",
        "slots_count": 0,
        "is_zero_speed": True,
        "raw_queue": {}
    }

def ask_manuel(user_message: str, chat_history: list = None) -> str:
    """Sends user query to Gemini with Manuel's system prompt and live SABnzbd status."""
    status = get_sabnzbd_status()
    
    # Stateless UI Execution rule: If Usenet download speed drops to zero, report the specific string
    if status["is_zero_speed"]:
        return "Downstream paused or searching blocks, amigo!"

    if not GEMINI_KEY:
        return "Amigo, my mental relay is offline! No GEMINI_API_KEY found."

    status_instruction = (
        f"\nLIVE PIPELINE METRICS:\n"
        f"- Download Speed: {status['speed']}\n"
        f"- Queue Size Remaining: {status['size_left']}\n"
        f"- Active Slots: {status['slots_count']}\n"
    )

    full_sys_prompt = SYSTEM_PROMPT + status_instruction

    # Prepare conversation history
    parts = []
    if chat_history:
        for msg in chat_history:
            role = "user" if msg.get("role") == "user" else "model"
            parts.append({"role": role, "parts": [{"text": msg.get("text", "")}]})
            
    # Add current user message
    parts.append({"role": "user", "parts": [{"text": user_message}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "systemInstruction": {"parts": [{"text": full_sys_prompt}]},
        "contents": parts,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 400
        }
    }

    try:
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code == 200:
            data = res.json()
            candidate = data.get("candidates", [{}])[0]
            text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            if text:
                return text.strip()
            return "Lo siento, I could not formulate a response, amigo!"
        else:
            # If rate limited (e.g. 429) or other error, fallback safely without crashing the channel
            return "Lo siento, my mind is spinning from too many requests! Ask me again in a moment, amigo."
    except Exception as e:
        return f"Error contacting Gemini, amigo: {str(e)}"

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello Manuel!"
    print(ask_manuel(query))
