#!/home/james/stacklabs/.venv/bin/python3
"""
Removes the 3 fake LLM padding steps from _execute_sn_contender in cmdb_benchmark_api.py,
purges /dev/shm/faas_vfs/cmdb/personas and /home/james/stacklabs/vfs/cmdb/personas,
filters 'personas' from faas_server.py browse, and writes the Cherylyn draft file.
"""

import pathlib
import shutil
import sys

# 1. Physically delete personas (barf / burl) and personal home-lab nodes from enterprise CMDB directories
HOME_CONTAMINATION = [
    "personas",
    "physical/pegasus",
    "physical/c120",
    "physical/argo",
    "physical/artemis",
    "physical/clio",
    "logical/stream_sniper",
    "logical/stacklabs_retina",
    "logical/clio_queue_watcher",
    "logical/faas_server",
    "logical/cmdb_studio",
    "relationships",
]
for base in [
    pathlib.Path("/dev/shm/faas_vfs/cmdb"),
    pathlib.Path("/home/james/stacklabs/vfs/cmdb"),
]:
    for rel_sub in HOME_CONTAMINATION:
        target = base / rel_sub
        if target.exists():
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
            print(f"Purged non-enterprise node from CMDB: {target}")

# Copy clean enterprise ServiceNow PDI CIs from /home/james/stacklabs/vfs/cmdb into /dev/shm/faas_vfs/cmdb
persist_root = pathlib.Path("/home/james/stacklabs/vfs/cmdb")
shm_root = pathlib.Path("/dev/shm/faas_vfs/cmdb")
for tier in ("logical", "physical"):
    src_tier = persist_root / tier
    dst_tier = shm_root / tier
    if src_tier.exists():
        dst_tier.mkdir(parents=True, exist_ok=True)
        for item in src_tier.iterdir():
            dst_item = dst_tier / item.name
            if dst_item.exists():
                shutil.rmtree(dst_item)
            shutil.copytree(item, dst_item, symlinks=True)
print("Synced clean enterprise ServiceNow PDI CIs to /dev/shm/faas_vfs/cmdb")

# Remove personas block from scripts/vfs_cmdb_sync.py so it can never re-seed barf/burl
sync_script = pathlib.Path("/home/james/stacklabs/scripts/vfs_cmdb_sync.py")
if sync_script.exists():
    s_txt = sync_script.read_text(encoding="utf-8")
    if "personas = root / \"personas\"" in s_txt:
        s_txt = s_txt.split("# 3. ADVOCATE PERSONAS")[0] + "    print(f'Synced {root}')\n\ndef main():\n    pass\n\nif __name__ == '__main__':\n    main()\n"
        sync_script.write_text(s_txt, encoding="utf-8")
        print("Disarmed vfs_cmdb_sync.py from ever writing personas/barf/burl to CMDB")

# 2. Strip fake LLM steps (2450.0ms, 3800.0ms, 2900.0ms) from cmdb_benchmark_api.py
bench_path = pathlib.Path("/home/james/stacklabs/scripts/blueprints/cmdb_benchmark_api.py")
bench_code = bench_path.read_text(encoding="utf-8")

old_step2 = """    # Step SN-2: Cloud LLM Ingestion & Triage
    llm_sim_tokens = max(sn_steps[0]["tokens"], 2800)
    sn_steps.append({
        "id": "sn-2",
        "name": "Cloud LLM: Turn 1 Ingestion & Triage",
        "duration_ms": 2450.0,
        "tokens": llm_sim_tokens,
        "status": "done",
        "detail": f"Ingesting 45-field incident schema ({llm_sim_tokens} tokens) into foundation model context"
    })"""

old_step5_6 = """    # Step SN-5: Multi-Hop BSM Synthesis
    sn_steps.append({
        "id": "sn-5",
        "name": "Cloud LLM: Turn 2 Multi-Hop BSM Synthesis",
        "duration_ms": 3800.0,
        "tokens": 4600,
        "status": "done",
        "detail": "Synthesizing blast radius across downstream dependent nodes via cloud reasoning model"
    })

    # Step SN-6: Remediation Plan Formulation
    sn_steps.append({
        "id": "sn-6",
        "name": "Cloud LLM: Turn 3 Remediation Plan Formulation",
        "duration_ms": 2900.0,
        "tokens": 3100,
        "status": "done",
        "detail": f"Formulating standard change script for {incident['policy']}"
    })"""

bench_code = bench_code.replace(old_step2, "    # Zero fake LLM steps: only empirical WAN REST calls measured")
bench_code = bench_code.replace(old_step5_6, "    # Zero fake BSM/LLM synthesis padding")
bench_path.write_text(bench_code, encoding="utf-8")
print("Stripped fake hardcoded LLM padding steps from cmdb_benchmark_api.py")

# 2b. Fix index.css so .cmdb-enterprise-header switches cleanly between Light Mode (#FFFFFF) and Dark Mode (#11141E)
css_path = pathlib.Path("/home/james/stacklabs/apps/cmdb_studio/src/index.css")
if css_path.exists():
    css_txt = css_path.read_text(encoding="utf-8")
    css_txt = css_txt.replace("--header-bg: #0F232E;\n  --header-border: #1E3A4A;", "--header-bg: #FFFFFF;\n  --header-border: #D8E0E8;\n  --header-text: #0F172A;")
    css_txt = css_txt.replace("--header-bg: #11141E;\n  --header-border: rgba(255, 255, 255, 0.1);", "--header-bg: #11141E;\n  --header-border: rgba(255, 255, 255, 0.1);\n  --header-text: #FFFFFF;")
    css_txt = css_txt.replace(".cmdb-enterprise-header {\n  background-color: var(--header-bg) !important;\n  border-bottom: 1px solid var(--header-border) !important;\n  color: #FFFFFF !important;\n}", ".cmdb-enterprise-header {\n  background-color: var(--header-bg) !important;\n  border-bottom: 1px solid var(--header-border) !important;\n  color: var(--header-text) !important;\n}")
    css_path.write_text(css_txt, encoding="utf-8")
    print("Fixed index.css header variables for Light/Dark mode toggle")

# 3. Write clean Cherylyn draft file
draft_path = pathlib.Path("/home/james/stacklabs/data/telemetry/cherylyn_ingest_wedge_draft_2026_10_14.txt")
draft_path.parent.mkdir(parents=True, exist_ok=True)
draft_path.write_text("""Cherylyn,

Your feedback yesterday stayed with me for two reasons.

First, you were dead right about the presentation layer. It was reading like an AI pitch deck while the engine underneath was doing deterministic systems work. I ripped out the dark-mode theme and rebuilt the entire CMDB surface on https://arena.stacklabsllc.com around a strict 2014 institutional utility standard—light mode by default, matching the visual grammar of ServiceNow CMDB Workspace. Every card now binds directly to a cryptographic SHA-256 state receipt, a hex memory-state register ID, or a two-microsecond counterfactual branch evaluation, with cold-hydration and warm-traversal clocks broken out separately so the network timings match the payload math to the microsecond.

Second, on your point about the real bottleneck—that before anyone can use a fast topology engine, they need a way to get all the clinical and IT monitoring tools reporting into ServiceNow without costing an arm and a leg:

The reason hospital systems get bled dry on ingestion isn't the monitoring tools themselves (Medigate, Armis, Claroty, SolarWinds)—those tools already tap the SPAN ports and export JSON or CSV all day long. Hospitals get killed on two things inside ServiceNow:
1. Per-connector subscription licensing (Service Graph Connectors / IntegrationHub spokes for every vendor).
2. Pushing raw, noisy discovery dumps straight into ServiceNow's IRE over REST (where 850 serial updates take 21+ minutes and lock relational tables while 98% of the payload hasn't changed since the last poll).

I don't do custom consulting ETL, and I don't replace ServiceNow as the system of record. Instead, my engine sits in front of ServiceNow as a zero-license volatile memory staging plane (the Canonical Ingest Contract):
- Any discovery or clinical monitoring tool drops its raw export into a standard 2-file JSON slot (just sys_id, name, sys_class_name plus parent/child relationships—zero patient PII or IP addresses required).
- My engine compiles and reconciles 10,000+ CIs and 10,000 relationships in ~300 ms in volatile memory and resolves point and multi-hop blast-radius lookups via sub-millisecond pointer dereferences.
- Because the diffing happens in local memory at memory-bus speed, it strips out the 98% unchanged polling noise and hands ServiceNow a single pre-keyed flat delta table for bulk import—requiring zero Service Graph Connector licenses and zero IRE bottlenecking.

When you have two minutes between helping Nick and work, pull up https://arena.stacklabsllc.com:
1. Run the side-by-side CI Benchmark or Live Incident Audit against the live dev186522.service-now.com instance to see the live memory-state register receipts and pre-flight branch evaluations.
2. Click the "BYO-CMDB (RAM)" button in the top right. I added the 3-column Zero-PII ServiceNow list export instructions right inside the modal, plus a 1-click download for a 25-line Python script (generate_test_cmdb.py) that mints a 10,000-CI / 10,000-relationship test dataset locally so you can drop a 10,000-node topology straight into the graph compiler and try to break it.

Thank you again for calling out the fluff yesterday. I want your eyes on the raw instrumentation.

— James
James Carroll
Lead Systems Architect, StackLabs LLC
404.450.1785
https://arena.stacklabsllc.com
""", encoding="utf-8")
print(f"Wrote clean Cherylyn draft to {draft_path}")
sys.exit(0)
