import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import cmdb_core

def seed_snow_instance():
    print("[+] Initiating ServiceNow PDI Injection...")
    cmdb = cmdb_core.cmdb

    # Registering Omega-Gate Technologies / The SN Developer Instance
    cmdb.register_node(
        node_id="LCI-SNOW-PDI",
        hardware="Omega-Gate Technologies (ServiceNow dev304621)",
        agent_class="Enterprise CMDB Interface (Logical CI)",
        status="ONLINE",
        primary_directives=["Provide PDI Ticketing Portal", "Host Sovereign Sync Bridge", "Manage Feline Anomalies"],
        manifest_path="https://dev304621.service-now.com/",
        s_value=1.0
    )
    print("  -> Registered: LCI-SNOW-PDI (https://dev304621.service-now.com/)")
    print("\n[+] ServiceNow PDI Seeding Complete!")

if __name__ == "__main__":
    seed_snow_instance()
