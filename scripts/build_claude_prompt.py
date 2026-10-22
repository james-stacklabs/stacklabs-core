import os
import sqlite3

html_file = "/home/james/stacklabs/scripts/sdlc_portal.html"
with open(html_file, "r", encoding="utf-8") as f:
    html_content = f.read()

db_path = "/home/james/stacklabs/dna/sovereign_now.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT number, short_description, state, priority, type FROM sovereign_tickets LIMIT 30")
tickets = c.fetchall()
ticket_text = "\n".join([f"- [{t['number']}] {t['short_description']} | Type: {t['type']} | State: {t['state']} | Priority: {t['priority']}" for t in tickets])

c.execute("SELECT node_id, tailscale_ip, target_l2_chain, operational_status FROM cmdb_ci_telemetry_node")
nodes = c.fetchall()
node_text = "\n".join([f"- [{n['node_id']}] {n['tailscale_ip']} | L2 Chain: {n['target_l2_chain']} | Status: {n['operational_status']}" for n in nodes])

output_dir = "/home/james/stacklabs/NotebookLM_Payload"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "CLAUDE_PROMPT_EMPLOYEE_CENTER.md")

with open(output_file, "w", encoding="utf-8") as f:
    f.write("Here is the full context of the actual Sovereign SDLC Portal UI along with the live production data from the CMDB `sovereign_now.db` tables.\n\n")
    f.write("---\n\n### 1. LIVE DATA: sovereign_tickets\n")
    f.write(ticket_text + "\n\n")
    f.write("### 2. LIVE DATA: cmdb_ci_telemetry_node (fleet_nodes)\n")
    f.write(node_text + "\n\n")
    f.write("---\n\n### 3. SOURCE CODE: sdlc_portal.html\n\n```html\n")
    f.write(html_content + "\n```\n")

print("Generated prompt file successfully at:", output_file)
