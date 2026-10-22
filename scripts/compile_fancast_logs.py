import os
import json

payloads_dir = "/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads"

master_logs = []
highlights = []

keywords = [
    "BOGGS", "ORBITER", "DIMENSIONMATCHEXCEPTION", "DINGER", "BURRITO", 
    "WHALE", "ASTEROID", "MELTING", "CONSPIRACY", "SEA-LEVEL", 
    "8-MILE", "SPREADSHEETS ARE ON FIRE", "QUANTUM", "AETHERIC",
    "RACING PIEROGIES", "DIMENSION", "PIEROGIES", "VAGINA", "AIR"
]

for root, _, files in os.walk(payloads_dir):
    for f in files:
        if f.startswith("FanCast_Export_") and f.endswith(".csv"):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
                content = file.read()
                
                # Split by literal '\r\n' or actual newline if mixed
                lines = content.replace('\\r\\n', '\n').split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Usually lines are like "","","Message"
                    # Let's extract between the last pair of quotes, or just the whole line if not quoted
                    parts = line.split('","')
                    if len(parts) >= 3:
                        msg = parts[-1].rstrip('"')
                    else:
                        msg = line.strip('"')
                        
                    if msg == "Message" or msg.startswith("User,Time"):
                        continue
                        
                    if "**[LIVE SECURE FEED]**" in msg:
                        continue
                        
                    entry = {
                        "date_source": f,
                        "msg": msg
                    }
                    
                    if msg not in [m['msg'] for m in master_logs]:
                        master_logs.append(entry)
                        
                        upper_msg = msg.upper()
                        is_highlight = any(k in upper_msg for k in keywords)
                        
                        caps_count = sum(1 for c in msg if c.isupper())
                        letters_count = sum(1 for c in msg if c.isalpha())
                        
                        caps_ratio = (caps_count / letters_count) if letters_count > 0 else 0
                        
                        if is_highlight or (caps_ratio > 0.6 and letters_count > 20):
                            highlights.append(entry)

print(f"Total Unique Fancast Log Lines: {len(master_logs)}")
print(f"Total Highlight Lines: {len(highlights)}")

with open('/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads/master_fanstack_highlights.json', 'w') as out:
    json.dump(highlights, out, indent=2)

with open('/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads/master_fanstack_all.json', 'w') as out:
    json.dump(master_logs, out, indent=2)
