import os
import csv
import json

root_dir = "/home/james/stacklabs"

master_logs = []
seen_msgs = set()

for root, dirs, files in os.walk(root_dir):
    if "node_modules" in dirs: dirs.remove("node_modules")
    if ".git" in dirs: dirs.remove(".git")
    if "tmp" in dirs: dirs.remove("tmp")
        
    for f in files:
        filepath = os.path.join(root, f)
        
        is_fanstack_related = (
            "fancast" in f.lower() or 
            "fanstack" in f.lower() or 
            "fancast" in root.lower() or 
            "fanstack" in root.lower() or
            f.startswith("FanCast_Export") or
            f.startswith("auto_export_")
        )
        
        if not is_fanstack_related:
            continue
            
        try:
            if f.endswith(".csv"):
                with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
                    content = file.read()
                    lines = content.replace('\\r\\n', '\n').split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line: continue
                        parts = line.split('","')
                        if len(parts) >= 3:
                            msg = parts[-1].rstrip('"')
                        else:
                            msg = line.strip('"')
                            
                        if msg == "Message" or msg.startswith("User,Time"): continue
                        if "**[LIVE SECURE FEED]**" in msg: continue
                        msg = msg.strip()
                        if msg and msg not in seen_msgs:
                            seen_msgs.add(msg)
                            master_logs.append(msg)
                            
            elif f.endswith(".json"):
                with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        for entry in data:
                            msg = entry.get('Message', '') or entry.get('text', '') or entry.get('message', '') or entry.get('history', '')
                            if type(msg) == dict: msg = msg.get('parts', [{}])[0].get('text', '')
                            msg = str(msg).strip()
                            if msg and "**[LIVE SECURE FEED]**" not in msg and "play-by-play" not in msg.lower():
                                if msg not in seen_msgs: 
                                    seen_msgs.add(msg)
                                    master_logs.append(msg)
                    elif isinstance(data, dict):
                        for key, val in data.items():
                            if isinstance(val, dict):
                                msg = val.get('message', '') or val.get('text', '')
                                msg = str(msg).strip()
                                if msg and "**[LIVE SECURE FEED]**" not in msg:
                                    if msg not in seen_msgs:
                                        seen_msgs.add(msg)
                                        master_logs.append(msg)
                                    
            elif f.endswith(".txt") or f.endswith(".md"):
                with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
                    lines = file.readlines()
                    for line in lines:
                        msg = line.strip()
                        if msg and not (msg.startswith("**") or "LIVE SECURE" in msg):
                            # clean up markdown prefixes if present
                            if msg.startswith("- "): msg = msg[2:]
                            if msg not in seen_msgs:
                                seen_msgs.add(msg)
                                master_logs.append(msg)
        except Exception as e:
            pass

print(f"Total Combined Master Fancast Log Lines: {len(master_logs)}")

with open('/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads/NotebookLM_Master_Fancast_Log.txt', 'w', encoding='utf-8') as out:
    out.write("SOVEREIGN FANSTACK - COMPLETE HISTORICAL MASTER LOG (DAY 1 TO PRESENT)\n")
    out.write("INCLUDES: DOT, ZORK, GONZO, AND ALL UAT SPRINTS\n")
    out.write("========================================================================\n\n")
    for msg in master_logs:
        out.write(f"- {msg}\n\n")
