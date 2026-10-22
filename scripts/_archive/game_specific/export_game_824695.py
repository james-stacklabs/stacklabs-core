import os
import re

in_file = "/home/james/stacklabs/data/logs/fanstack_20260410.log"
out_file = "/home/james/stacklabs/dna/agents/SOVEREIGN_FANSTACK_ORACLE/payloads/NotebookLM_PIT_CHC_Export.txt"

with open(in_file, 'r') as f:
    lines = f.readlines()

log_output = []
recording = False
for line in lines:
    is_telemetry = "MLB_TELEMETRY | SYSTEM:" in line

    if is_telemetry:
        if "PIT@CHC" in line:
            recording = True
            log_output.append(line)
        else:
            continue # skip other games
    else:
        if recording:
            log_output.append(line)

with open(out_file, 'w', encoding='utf-8') as f:
    f.write("SOVEREIGN FANSTACK - MARD ENGINE RAW TELEMETRY LOGS: PIT@CHC\n")
    f.write("============================================================\n\n")
    for l in log_output:
        # Strip the datetime brackets to make it slightly cleaner, or leave it so NotebookLM can parse chronology
        # NotebookLM prefers exact chronological flow
        f.write(l)

print(f"Exported {len(log_output)} lines to {out_file}")
