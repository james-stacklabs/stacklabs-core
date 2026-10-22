import os
import glob

OUTPUT_FILE = '/home/james/stacklabs/dna/dropzone/daily_20042026/Barb_FanStack_Audio_Transcript.txt'

# Gather all recent chat logs
md_files = glob.glob('/home/james/stacklabs/dna/dropzone/daily_*/madness_tail*.md') + \
           glob.glob('/home/james/stacklabs/dna/dropzone/daily_*/chc_phi_tail.md') + \
           glob.glob('/home/james/stacklabs/dna/dropzone/daily_*/auto_export_*.md')

markdown_payload = """# SOVEREIGN FANSTACK - AI PERSONA BASEBALL SIMULATION
## NARRATIVE CONTEXT FOR AUDIO OVERVIEW HOSTS
You are reading the raw output transcripts of the "Sovereign FanStack", an autonomous AI system created by James. 
James built this to simulate the experience of sitting in a dive bar with crazy, unhinged sports fans. The system feeds live Major League Baseball Statcast data (like pitch velocity and hit trajectories) to several different LLMs, who then "watch" the game together in a virtual chat room.

Major Personas:
- DOT: The cold, analytical math-robot. Cares only about exit velocity, launch angles, and math.
- BATTERY_CHUCKER: The toxic, aggressive Philadelphia Phillies fan who hates everyone.
- 2008_GHOST: A ghost of a Phillies fan who is stuck in the past and thinks it is still 2008.
- PHANATIC: The chaotic mascot of the Phillies.
- IVY_INSPECTOR_IAN: A pretentious Chicago Cubs fan who cares too much about the Wrigley Field ivy.
- BLEACHER_BUM_BILL: A weathered Cubs fan who talks about the wind at Wrigley.

A major feature James recently added is the "BOGGS SCALE". It is an aggression dial (Levels 1 to 5). At Boggs Level MAX (5), the AI personas drop all punctuation, use all caps, and become completely unhinged and aggressive toward each other.

Below are the live transcripts of their interactions from the latest Chicago Cubs vs Philadelphia Phillies game, and other recent mesh tests. Notice how they react to the baseball events in real-time.

============================================================
"""

with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
    out.write(markdown_payload)
    for f in md_files:
        try:
            with open(f, 'r', encoding='utf-8') as infile:
                contents = infile.read()
                out.write(f"\n\n--- TRANSCRIPT EXPORT: {os.path.basename(f)} ---\n\n")
                out.write(contents)
                out.write("\n\n")
        except Exception as e:
            print(f"Error reading {f}: {e}")

print(f"Successfully compiled FanStack audio transcript for Barb into {OUTPUT_FILE}")
