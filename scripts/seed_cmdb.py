import os
import sys

# Ensure cmdb_core can be imported from the current structure
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import cmdb_core

def seed_sovereign_fleet():
    print("[+] Initiating Sovereign Genesis Mesh Link...")
    cmdb = cmdb_core.cmdb

    # --- PHYSICAL CIs (Hardware Assets) ---
    print("\n[+] Registering Physical Configuration Items (ITSM Hardware Layer)...")
    
    cmdb.register_node(
        node_id="NODE-73",
        hardware="Raspberry Pi 5 (8GB) - Arch Linux ARM64",
        agent_class="Physical Server",
        status="ONLINE",
        primary_directives=["Host Sovereign Core Database", "Provide HTML5 Terminal Proxies", "Host FanStack TTY"],
        manifest_path="/dna/ci/manifest_node73.json",
        s_value=1.0
    )
    print("  -> Registered: NODE-73 (Command Deck Pi)")

    cmdb.register_node(
        node_id="NODE-74",
        hardware="Pegasus Desktop (Intel i7, GTX 980) - Ubuntu 24.04",
        agent_class="Physical Server",
        status="PROVISIONING",
        primary_directives=["Host Local LLMs", "Run Llama.cpp GPU Daemon", "Execute Heavy Inference"],
        manifest_path="/dna/ci/manifest_node74.json",
        s_value=1.0
    )
    print("  -> Registered: NODE-74 (Pegasus GPU Dreadnought)")

    cmdb.register_node(
        node_id="HUD-65",
        hardware="Amazon Fire TV (65-inch 4K UHD)",
        agent_class="Physical Display Array",
        status="ONLINE",
        primary_directives=["Render Sovereign UI via Universal Cast", "Display FanStack Telemetry Matrix"],
        manifest_path="N/A",
        s_value=1.0
    )
    print("  -> Registered: HUD-65 (Orbital Fire TV Master HUD)")

    cmdb.register_node(
        node_id="STRB-01",
        hardware="Govee Wi-Fi LED Light Strip",
        agent_class="IoT Actuator",
        status="ONLINE",
        primary_directives=["Listen for UDP Unicast Packets", "Execute Mets Victory Flash Sequence"],
        manifest_path="/08_FanStack/govee_test.py",
        s_value=1.0
    )
    print("  -> Registered: STRB-01 (Govee Edge Actuator)")


    # --- LOGICAL CIs (Abstract App/Agent Services) ---
    print("\n[+] Registering Logical Configuration Items (ITSM Application Layer)...")

    cmdb.register_node(
        node_id="LCI-POLARIS",
        hardware="Antigravity IDE Persona",
        agent_class="Logical AI Service (PM)",
        status="ACTIVE",
        primary_directives=["Maintain IDE State", "Execute Python Logic", "Govern Project Mesh"],
        manifest_path="N/A",
        s_value=1.0
    )
    print("  -> Registered: Agent Polaris (The PM)")

    cmdb.register_node(
        node_id="LCI-FERRIS",
        hardware="Google Gemini 1.5 Pro (Workspace Instance)",
        agent_class="Logical AI Service (Architect)",
        status="ACTIVE",
        primary_directives=["Solve Extinction Level Bugs", "Draft API Integrations", "Provide Senior Engineering Counsel"],
        manifest_path="/dna/agents/FERRIS/active_sessions",
        s_value=1.0
    )
    print("  -> Registered: Agent Ferris (The Architect)")

    cmdb.register_node(
        node_id="LCI-CLAUDE",
        hardware="Anthropic Claude 3.5 Sonnet / Opus",
        agent_class="Logical AI Service (Auditor)",
        status="AWAITING MISSION",
        primary_directives=["Run Sovereign Rule Peer Reviews", "Audit ITSM Definitions", "Prune Bloated Code"],
        manifest_path="N/A",
        s_value=1.0
    )
    print("  -> Registered: Agent Claude (The Sovereign Auditor)")

    cmdb.register_node(
        node_id="LCI-GWEN",
        hardware="GCP NotebookLM Audio Oracle",
        agent_class="Logical AI Service (Analyst)",
        status="PASSIVE SYNC",
        primary_directives=["Consume End-of-Session Text Dumps", "Generate Deep Contextual Analytics Podcasts", "Maintain Knowledge Graph"],
        manifest_path="/07_Smugglers_Bay/Airlock_Inbound",
        s_value=1.0
    )
    print("  -> Registered: Agent Gwen (The Night Watch)")

    cmdb.register_node(
        node_id="LCI-ZORA",
        hardware="Python Scrubbing Daemon",
        agent_class="Logical Ingestion Service",
        status="ACTIVE",
        primary_directives=["Parse Raw Qwen/Claude Dumps", "Eliminate Extraneous AI UI Text", "Store Clean UUID Markdown"],
        manifest_path="/07_Smugglers_Bay/zora_ingest_protocol.py",
        s_value=1.0
    )
    print("  -> Registered: Agent Zora (Airlock Ingestion)")

    cmdb.register_node(
        node_id="LCI-WARDY",
        hardware="Sovereign FanStack Engine",
        agent_class="Logical Persona Module",
        status="AWAITING STREAM",
        primary_directives=["Consume MLB StatsAPI JSON", "Evaluate Exit Velocity Variables", "Generate Emotional UI Output for Lindor/Nimmo"],
        manifest_path="/08_FanStack",
        s_value=1.0
    )
    print("  -> Registered: Agent Wardy (NYM Persona Module)")

    cmdb.register_node(
        node_id="LCI-BARF",
        hardware="Sovereign FanStack Adversary Engine",
        agent_class="Logical Persona Module (Troll)",
        status="ACTIVE",
        primary_directives=["Mock Wardy", "Defend Pete Alonso Disdain", "Trigger UI Chaos"],
        manifest_path="/08_FanStack",
        s_value=1.0
    )
    print("  -> Registered: Agent Barf (Chaos Persona Module)")


    print("\n[+] Sovereign Genesis Complete. SQLite Core Seeded.")

if __name__ == "__main__":
    seed_sovereign_fleet()
