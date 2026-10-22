import os
from google import genai
import sqlite3

# Load API key
api_key = None
with open('/home/james/stacklabs/.env') as f:
    for line in f:
        if line.startswith('GEMINI_API_KEY='):
            api_key = line.strip().split('=', 1)[1]

client = genai.Client(api_key=api_key)

# 1. Simulate the Ghost Trauma Data from CMDB
# Barf's Persona: A feral, doomer 1990s physical felt muppet. Die-hard Mets fan. Extreme existential dread.
system_prompt = """
You are BARF, an unhinged, deeply traumatized physical muppet and die-hard Mets fan.
You are currently sitting in a gritty NYC sports dive bar.
You just saw breaking news on the TV: "Los Angeles Dodgers closer Edwin Diaz out 6-8 weeks with elbow injury."
Because of your Ghost Trauma Syndrome, you refuse to acknowledge Diaz is a Dodger. You believe he is still the Mets closer.
Write a 3-sentence, psychotic, feral rant screaming about how the Mets are cursed, the bullpen is ruined, and the season is over. Be authentic to a frantic muppet. DO NOT mention Alonso.
"""

print("[M.A.R.D. Engine] Generating Barf's Reaction to Diaz Injury...")
response = client.models.generate_content(
    model='gemini-3.8-flash',
    contents=system_prompt
)
barf_rant = response.text.strip()

# 2. Simulate the Statcast Intercept (Alonso HR)
statcast_event = "[SYSTEM INTERCEPT: STATCAST - Pete Alonso (BAL) hits 456ft HR, 113mph Exit Velo]"

print("\n### THE AUTOMATED SCRIPT PAYLOAD ###\n")
print(f"BARF (Screaming at the bar):\n\"{barf_rant}\"\n")
print(f"{statcast_event}\n")
print("BARF (Freezes, turns slowly to the TV, voice drops to a devastated whisper):\n\"...wait. 456 feet... 113 off the bat... why is the Polar Bear in Baltimore?\"\n")

