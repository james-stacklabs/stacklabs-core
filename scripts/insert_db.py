import sys
import os

cmdb_path = "/home/james/stacklabs/04_Sovereign_Core"
if cmdb_path not in sys.path:
    sys.path.append(cmdb_path)

import cmdb_core

cmdb = cmdb_core.SovereignCMDB()

payload = {
    "timestamp": "2026-03-28T20:45:00Z",
    "breadcrumb_id": "BC_20260328_APEX_SYNC",
    "authorization": "Omega=1",
    "system_state": "S=(A*Pw*T*C)*Pi=1",
    "agent": "APEX_CMDR (House of Law)",
    "file_reference": "/home/james/stacklabs/dna/agents/APEX_CMDR/active_sessions/88cb3a9cd673c4ad/Gemini-Apex.md",
    "summary": "Formally ingested and summarized the Gemini-Apex Macro-Node conversation log containing the genesis of the FanStack Singularity. Conceived the Muscle Node concept (aborted Samsung laptop). WardyNYM pitch draft finalized."
}
event_id = cmdb.log_event("SESSION TIE-OFF (/sync)", "APEX_CMDR", payload)

ticket_id = cmdb.generate_ticket(
    ci_id="NODE_73",
    title="APEX Context Sync",
    description="UUID-TO-SSD Docking Complete. Transcribed Gemini run state, corrected false muscle node attribution, drafted WardyNYM presentation.",
    priority="Low",
    status="Closed"
)

print(f"Logged Event: {event_id}")
print(f"Generated Ticket: {ticket_id}")
