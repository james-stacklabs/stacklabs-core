import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import cmdb_core

CRED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dna", "vault", "sn_credentials.json")

class ServiceNowBridge:
    def __init__(self):
        self.cmdb = cmdb_core.cmdb
        
        if not os.path.exists(CRED_PATH):
            print(f"[!] Error: Credentials missing at {CRED_PATH}")
            sys.exit(1)
            
        with open(CRED_PATH, "r") as f:
            creds = json.load(f)
            
        if creds["password"] == "<PASTE_PASSWORD_HERE>":
            print("[!] Security Halt: You must paste your ServiceNow password into dna/vault/sn_credentials.json first.")
            sys.exit(1)
            
        self.base_url = f"https://{creds['instance']}.service-now.com/api/now/table"
        self.auth = HTTPBasicAuth(creds['username'], creds['password'])
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}

    def _upsert_record(self, table, payload, match_field="correlation_id"):
        # Check if exists
        query_url = f"{self.base_url}/{table}?sysparm_query={match_field}={payload[match_field]}&sysparm_limit=1"
        try:
            get_res = requests.get(query_url, auth=self.auth, headers=self.headers)
            if get_res.status_code == 200 and len(get_res.json().get('result', [])) > 0:
                # Update existing
                sys_id = get_res.json()['result'][0]['sys_id']
                put_url = f"{self.base_url}/{table}/{sys_id}"
                requests.put(put_url, auth=self.auth, headers=self.headers, json=payload)
                return "UPDATED"
            else:
                # Create new
                post_url = f"{self.base_url}/{table}"
                requests.post(post_url, auth=self.auth, headers=self.headers, json=payload)
                return "CREATED"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def sync_fleet(self):
        print("\n[*] Commencing Sovereign Fleet Sync to Cloud CMDB...")
        nodes = self.cmdb.get_all_nodes()
        for node in nodes:
            table = "cmdb_ci_hardware" if "Hardware" in node["agent_class"] or "Physical" in node["agent_class"] else "cmdb_ci_appl"
            
            payload = {
                "name": node["node_id"],
                "short_description": f"{node['hardware']} - {node['agent_class']}",
                "correlation_id": node["node_id"],
                "install_status": 1 if node["status"] in ["ACTIVE", "ONLINE", "AWAITING MISSION"] else 3
            }
            res = self._upsert_record(table, payload)
            print(f"  -> {node['node_id']} ({table}): {res}")

    def sync_tickets(self):
        print("\n[*] Commencing SDLC Ticket Sync to Agile Stories (rm_story)...")
        tickets = self.cmdb.get_all_tickets()
        for ticket in tickets:
            payload = {
                "short_description": ticket["title"],
                "description": f"Target CI: {ticket['ci_id']}\n\n{ticket['description']}",
                "correlation_id": ticket["ticket_id"],
            }
            res = self._upsert_record("rm_story", payload)
            print(f"  -> {ticket['ticket_id']}: {res}")

    def execute(self):
        print("="*60)
        print(" OMEGA-GATE TECHNOLOGIES: SERVICENOW DATA BRIDGE INITIATED")
        print("="*60)
        self.sync_fleet()
        self.sync_tickets()
        print("="*60)
        print(" BRIDGE SYNC COMPLETE.")

if __name__ == "__main__":
    bridge = ServiceNowBridge()
    bridge.execute()
