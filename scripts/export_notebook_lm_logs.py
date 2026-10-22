import json

with open('/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads/master_fanstack_all.json', 'r') as f:
    logs = json.load(f)

# Just write out every single unique message line by line to a large NotebookLM-friendly text file
with open('/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads/NotebookLM_Master_Fancast_Log.txt', 'w', encoding='utf-8') as out:
    out.write("SOVEREIGN FANSTACK - MARD ENGINE RAW TELEMETRY LOGS\n")
    out.write("=====================================================\n\n")
    for log in logs:
        out.write(f"[{log['date_source']}] {log['msg']}\n\n")
