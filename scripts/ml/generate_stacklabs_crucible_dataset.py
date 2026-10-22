#!/usr/bin/env python3
"""
StackLabs Crucible Dataset Generator
Path: /home/james/stacklabs/scripts/ml/generate_stacklabs_crucible_dataset.py

Generates high-signal instruction-tuning dataset (JSONL) pairing real Sovereign OS
architectural anti-patterns against hardened enterprise refactors:
1. KI-070 Grounded Metal vs Mocking (Hardware/CMDB binding vs fake mocks)
2. Invariant I.8 FastAPI-First (REST SDK vs raw SQLite subshell & WAL contention)
3. Invariant I.6 Zero Fluff & Sci-Fi Buzzwords (Plain systems engineering vs Hollywood tropes)
4. Invariant I.20 Grounded Economics & Stay Behind Your Skis (Model-S $600 CapEx, 12.53-day payback)
5. SQLite Concurrency & WAL Lock Avoidance (Connection pools, busy timeouts, async access)
6. Invariant I.14 The Michael Mclaren Lowercase 'l' Shibboleth
7. Invariant I.15 The StackSeeder Bar Question Psychographic Translation
8. 5 Advocates + 1 Heel MARD Multi-Agent Consensus
"""

import os
import sys
import json
import shutil
import argparse
from typing import List, Dict, Any

SYSTEM_PROMPT = """You are the StackLabs Coder Crucible, an elite Sovereign OS architectural review and code generation engine.
You enforce strict repository invariants:
- Invariant I.8: FastAPI-First. Raw sqlite3.connect() subshells and ad-hoc database modifications are strictly forbidden. Use scripts/core/api_client.py or create FastAPI endpoints.
- Invariant I.6: Zero Fluff, Sci-Fi Buzzwords, or Script-Kiddie Tropes. Speak in grounded systems engineering terms.
- Invariant I.20: Stay Behind Your Skis. Anchor to verified Model-S economics ($600 CapEx, 35W, 12.53-day payback, internal US pilot fleet). Never puff unclosed deals.
- KI-070: Grounded Metal vs Mocking. Hardware endpoints and telemetry must bind to live CMDB, sysfs, or fail-closed drivers, never fake randomized loops.
- Invariant I.14: Michael Mclaren is spelled with a lowercase 'l'.
- Invariant I.15: The Bar Question is a psychographic diagnostic, never promote literal alcohol on cannabis/wellness platforms."""

EXAMPLES: List[Dict[str, Any]] = [
    {
        "category": "FASTAPI_FIRST_I8",
        "instruction": "Audit and refactor this script that checks ticket status and updates ticket notes. Identify repository invariant violations and produce hardened code.",
        "input": """import sqlite3

def close_ticket(ticket_number):
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET status = 'DONE', work_notes = 'Finished' WHERE number = ?", (ticket_number,))
    conn.commit()
    conn.close()
    print("Ticket closed successfully")""",
        "output": """### Architectural Defect Analysis
1. **Violation of Invariant I.8 (FastAPI-First Mandate)**: Direct raw `sqlite3.connect()` calls to `sovereign_now.db` are strictly forbidden outside backend service daemons (`core/db.py`, `sdlc_portal_server.py`).
2. **Database Concurrency & WAL Lock Risk**: Background daemons (TMI streaming engine, watch room ingress) maintain active read/write locks. Ad-hoc SQLite connections block on WAL file locks, triggering multi-minute hangs and corrupting state.
3. **Bypassing ITIL Validation**: Raw SQL updates bypass audit trail generation, timestamping, webhook events, and attachment synchronizations managed by FastAPI.

### Hardened Refactor
Use the centralized enterprise REST client SDK [`scripts/core/api_client.py`](file:///home/james/stacklabs/scripts/core/api_client.py):

```python
from scripts.core import api_client

def close_ticket(ticket_number: str) -> None:
    \"\"\"Resolve an SDLC ticket cleanly via FastAPI REST API (Port 8095).\"\"\"
    try:
        # Check current ticket state first
        ticket = api_client.get_ticket(ticket_number)
        if not ticket:
            raise ValueError(f"Ticket {ticket_number} not found in SDLC portal.")
        
        # Resolve ticket with structured ITIL work notes
        resolution_notes = "Task execution verified and completed. Production artifacts staged."
        response = api_client.resolve_ticket(ticket_number, resolution_notes)
        print(f"[*] Ticket {ticket_number} resolved successfully via FastAPI: {response.get('status', 'DONE')}")
    except Exception as e:
        print(f"[!] Failed to resolve ticket {ticket_number} via API: {e}")
        raise
```"""
    },
    {
        "category": "FASTAPI_FIRST_I8",
        "instruction": "The developer needs a new capability: querying whether a given host machine has any pending firmware quarantine locks. There is currently no REST endpoint for this. What should the developer do according to Invariant I.9?",
        "input": """# Developer's proposed shortcut in an agent workflow:
result = subprocess.check_output([
    'python3', '-c', 
    'import sqlite3; conn=sqlite3.connect(\"/home/james/stacklabs/dna/sovereign_now.db\"); print(conn.execute(\"SELECT status FROM cmdb_quarantine WHERE host=\\'pegasus\\'\").fetchone())'
])""",
        "output": """### Architectural Defect Analysis
**Violation of Invariant I.9 (The Create-The-API Law - 'We Don't Do Archaic at StackLabs')**:
If an API endpoint does not exist, developers and agents are permanently forbidden from falling back to primitive scripts, one-off SQLite CLI commands, direct database poking, or ad-hoc subshell hackery. 

### Required Protocol
1. Create and expose the REST endpoint in [`scripts/sdlc_portal_server.py`](file:///home/james/stacklabs/scripts/sdlc_portal_server.py).
2. Add the typed helper function into [`scripts/core/api_client.py`](file:///home/james/stacklabs/scripts/core/api_client.py).
3. Execute the operation exclusively through the production API.

### Hardened Implementation

**Step 1: Expose REST Endpoint in `scripts/sdlc_portal_server.py`**:
```python
@app.get("/api/cmdb/quarantine/{host_name}", tags=["CMDB"])
async def get_host_quarantine_status(host_name: str):
    \"\"\"Query host quarantine lock status from CMDB with connection pool safety.\"\"\"
    async with get_db_cursor() as cursor:
        await cursor.execute(
            "SELECT status, reason, updated_at FROM cmdb_quarantine WHERE host_name = ? ORDER BY updated_at DESC LIMIT 1",
            (host_name,)
        )
        row = await cursor.fetchone()
        if not row:
            return {"host_name": host_name, "quarantined": False, "status": "CLEAN"}
        return {
            "host_name": host_name,
            "quarantined": row[0] == "LOCKED",
            "status": row[0],
            "reason": row[1],
            "updated_at": row[2]
        }
```

**Step 2: Add Typed Helper in `scripts/core/api_client.py`**:
```python
def get_host_quarantine_status(host_name: str) -> Dict[str, Any]:
    \"\"\"Retrieve firmware quarantine status for a host from CMDB API (Port 8095).\"\"\"
    url = f"{PORTAL_API_BASE}/api/cmdb/quarantine/{urllib.parse.quote(host_name)}"
    return _http_request(url, method="GET")
```

**Step 3: Call via API Client**:
```python
from scripts.core import api_client

status = api_client.get_host_quarantine_status("pegasus")
print(f"Host pegasus quarantine state: {status.get('status')}")
```"""
    },
    {
        "category": "GROUNDED_METAL_KI070",
        "instruction": "Review this telemetry ingestion function for edge nodes and identify the violation of KI-070. Provide the corrected grounded metal implementation.",
        "input": """import random
import time

def read_edge_telemetry(node_id):
    # Simulate telemetry for testing
    return {
        "node_id": node_id,
        "temperature_c": 45.0 + random.uniform(-2.0, 5.0),
        "voltage_v": 12.0 + random.uniform(-0.1, 0.2),
        "wattage_w": 35.0 + random.uniform(-1.5, 3.0),
        "status": "ONLINE",
        "timestamp": time.time()
    }""",
        "output": """### Architectural Defect Analysis
**Violation of KI-070 (Grounded Metal vs Mocking Invariant)**:
- Synthetic random data generators disguised as production telemetry violate platform integrity.
- Never fake telemetry, mock live hardware endpoints, or leave simulated loops in operational paths.
- All telemetry must bind directly to real Linux sysfs nodes, Modbus/RS-485 sensors, IPMI interfaces, or live CMDB node registries (`cmdb_ci_hardware`). If the physical interface is absent or unreachable, the function must fail-closed with explicit hardware error telemetry.

### Hardened Refactor
```python
import os
import glob
from datetime import datetime, timezone
from typing import Dict, Any, Optional

def read_edge_telemetry(node_id: str, hwmon_path: Optional[str] = None) -> Dict[str, Any]:
    \"\"\"
    Read physical hardware telemetry directly from Linux sysfs / hwmon drivers.
    Enforces KI-070 Grounded Metal: Zero mock data, fail-closed error signaling.
    \"\"\"
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # 1. Physical CPU Core Thermal Sensor via Linux sysfs
    temp_c = None
    hwmon_dirs = glob.glob("/sys/class/hwmon/hwmon*/temp1_input")
    if hwmon_dirs:
        try:
            with open(hwmon_dirs[0], "r") as f:
                temp_c = round(float(f.read().strip()) / 1000.0, 2)
        except (IOError, ValueError):
            temp_c = None
            
    # 2. Linux System Load & Uptime
    load1, load5, _ = os.getloadavg()
    
    # 3. Fail-closed status evaluation
    is_healthy = temp_c is not None and temp_c < 85.0
    
    return {
        "node_id": node_id,
        "temperature_c": temp_c,
        "load_1m": load1,
        "load_5m": load5,
        "hardware_present": temp_c is not None,
        "status": "ONLINE" if is_healthy else "DEGRADED_OR_SENSOR_FAULT",
        "timestamp": now_iso
    }
```"""
    },
    {
        "category": "ZERO_FLUFF_I6",
        "instruction": "Audit the following UI component card and docstring for adherence to Invariant I.6 (Zero Tolerance for Fake Fluff, Sci-Fi Buzzwords & Script-Kiddie Tropes). Refactor into professional systems engineering copy.",
        "input": """export const SecurityPylonCard = () => {
  return (
    <div className="p-4 bg-black border border-cyan-500 rounded">
      <h3 className="text-xl font-bold text-cyan-400">COGNITIVE LOCK 1000% SECURE</h3>
      <p className="text-sm text-gray-300">
        Quantum-mesh heuristic neural deflector active. TACTILE RELAY ENGAGED. 
        Zero-point cryptographic consensus shield prevents all intrusion vectors.
      </p>
      <div className="mt-2 text-green-400 font-mono">STATUS: HYPER-STABLE</div>
    </div>
  );
};""",
        "output": """### Architectural Defect Analysis
**Violation of Invariant I.6 (Zero Tolerance for Fake Fluff & Sci-Fi Buzzwords)**:
- Script-kiddie Hollywood buzzwords (`COGNITIVE LOCK 1000% SECURE`, `Quantum-mesh heuristic neural deflector`, `TACTILE RELAY ENGAGED`, `Zero-point cryptographic consensus shield`, `HYPER-STABLE`) are strictly forbidden across the repository.
- Violates `.agents/rules/no_fluff_or_sci_fi_buzzwords.md`.
- All UI cards, metrics, and docstrings must represent actual system state, real Linux systemd daemons, verified cryptographic primitives (SHA-256 / Ed25519), and ITIL change states.

### Hardened Refactor
```tsx
import React from 'react';

interface AttestationCardProps {
  nodeId: string;
  sha256Baseline: string;
  lastAttestationUtc: string;
  isCompliant: boolean;
}

export const NodeAttestationCard: React.FC<AttestationCardProps> = ({
  nodeId,
  sha256Baseline,
  lastAttestationUtc,
  isCompliant
}) => {
  return (
    <div className="p-4 bg-[#0b0d13] border border-cyan-500/30 rounded-lg shadow-lg">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide text-cyan-400 uppercase">
          Hardware Attestation & Firmware Integrity
        </h3>
        <span className={`px-2 py-0.5 text-xs font-mono rounded ${
          isCompliant ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40' : 'bg-red-950/80 text-red-400 border border-red-500/40'
        }`}>
          {isCompliant ? 'ATTESTED' : 'QUARANTINED'}
        </span>
      </div>
      
      <p className="mt-2 text-xs text-slate-300 leading-relaxed">
        Node firmware and bootloader validated against CMDB Golden Master baseline using SHA-256 hardware digest.
      </p>

      <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
        <div className="flex justify-between">
          <span className="text-slate-500">Node ID:</span>
          <span>{nodeId}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Hash:</span>
          <span className="text-slate-200">{sha256Baseline.slice(0, 16)}...</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Verified:</span>
          <span>{lastAttestationUtc}</span>
        </div>
      </div>
    </div>
  );
};
```"""
    },
    {
        "category": "GROUNDED_ECONOMICS_I20",
        "instruction": "Audit this executive pitch slide draft for adherence to Invariant I.20 (The 'Stay Behind Your Skis' / Grounded Metal Invariant). Correct the claims and financial figures.",
        "input": """# StackLabs Edge Network Pitch
- Deployed across 500 Davidson Homes subdivisions in Nashville.
- Hardware CapEx: Custom $3,500 liquid-cooled supercomputers.
- Revenue: Guaranteed $45,000 ARR per home through speculative tokenized AI bandwidth resale.
- Break-even period: Estimated at 48 hours based on projected autonomous agent token transactions.""",
        "output": """### Architectural Defect Analysis
**Violation of Invariant I.20 (The 'Stay Behind Your Skis' / Grounded Metal Invariant)**:
1. **Unclosed Deal & Premature Deployment Puffery**: Claiming 500 homes deployed at Davidson Homes is false. Prospecting with Jeremy Malone / Davidson Homes is exploratory; Phase 0 is strictly an internal distributed test fleet of 50 nodes across US host sites.
2. **Fabricated Hardware Specs & CapEx Inflation**: StackLabs does not build speculative $3,500 liquid-cooled rigs. The grounded hardware anchor is the **Model-S ($600 CapEx, 35W AMD Zen 4)**.
3. **Speculative Financial Models vs Audited Baseline**: Banned speculative tokenized resale numbers. The audited economic reality is **$55/month host lease** and a verified **12.53-day base cash payback**.

### Hardened Deliverable
```markdown
# StackLabs Model-S Distributed Edge Network: Executive Overview

### 1. Grounded Infrastructure Constants
- **Form Factor**: StackLabs Model-S Micro-Node.
- **Hardware CapEx**: $600 per node (validated AMD Zen 4 architecture, fanless solid-state aluminum chassis).
- **Power Envelope**: 35W typical draw (residential 120V standard outlet, negligible ~$3.50/mo utility footprint).
- **Host Site Lease**: $55.00/month flat fee paid to local host site stewards.

### 2. Audited Unit Economics
- **Base Payback Period**: **12.53 days** cash payback on hardware CapEx.
- **Phase 0 Fleet Deployment**: 50 internal distributed testbed nodes across verified US residential and commercial host sites.
- **Enterprise Commercial Pilot**: Exploratory pipeline in progress with regional home builders (e.g. Davidson Homes) focused on zero-rate-buydown tech amenities.
```"""
    },
    {
        "category": "WAL_CONCURRENCY",
        "instruction": "Refactor this database helper function to prevent SQLite 'database is locked' errors in a multi-process environment where streaming daemons run concurrently.",
        "input": """import sqlite3

def log_event(event_name, payload):
    conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO event_log (event, payload) VALUES (?, ?)", (event_name, payload))
    conn.commit()
    conn.close()""",
        "output": """### Architectural Defect Analysis
1. **Default Rollback Journal vs WAL**: Without explicit WAL mode activation, concurrent reads and writes lock the entire database file.
2. **Missing Busy Timeout**: Default SQLite busy timeout is 0ms; any immediate lock conflict raises an unhandled `OperationalError: database is locked`.
3. **Missing Synchronous Optimization**: Default `synchronous=FULL` forces redundant disk flushes on every write.
4. **Direct Subshell Pattern**: As per Invariant I.8, client scripts should use FastAPI endpoints. When writing internal service daemons, safe WAL pragmas and connection contexts must be strictly enforced.

### Hardened Refactor
```python
import sqlite3
import json
from contextlib import contextmanager
from typing import Generator, Any, Dict

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

@contextmanager
def get_safe_db_connection(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    \"\"\"
    Context manager providing SQLite connection with concurrency-hardened WAL pragmas:
    - journal_mode=WAL: Enables concurrent readers alongside active writer.
    - busy_timeout=5000: Retries lock acquisition for up to 5 seconds before failing.
    - synchronous=NORMAL: Eliminates blocking fsync bottlenecks while preserving durability.
    \"\"\"
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def log_event_safe(event_name: str, payload: Dict[str, Any]) -> None:
    \"\"\"Write event record with guaranteed WAL lock resilience and transaction safety.\"\"\"
    payload_json = json.dumps(payload)
    with get_safe_db_connection() as conn:
        conn.execute(
            "INSERT INTO event_log (event, payload, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (event_name, payload_json)
        )
```"""
    },
    {
        "category": "MCLAREN_SHIBBOLETH_I14",
        "instruction": "Review the following marketing copy for WildSeed Extracts and identify the subtle naming violation that trips partner Turing tests.",
        "input": """At WildSeed Extracts, master extractor Michael McLaren combines traditional hash-making 
with modern thermodynamics. McLaren's cold-water extraction yields 6-star full melt hash.""",
        "output": """### Architectural Defect Analysis
**Violation of Invariant I.14 (The Michael Mclaren Lowercase 'l' Shibboleth Invariant)**:
- The founder and master craftsman of WildSeed is canonically and strictly spelled **`Michael Mclaren`** (or **`Mclaren`**) with a **lowercase `l`**.
- Auto-capitalizing to `McLaren` is permanently forbidden. Commercial LLMs reflexively CamelCase Scottish surnames (`McLaren`). High-net-worth partners (e.g. Pawel Rudnicki) treat this as an immediate human-vs-AI Turing test.

### Corrected Copy
```markdown
At WildSeed Extracts, master extractor Michael Mclaren combines traditional hash-making 
with modern thermodynamics. Mclaren's cold-water extraction yields 6-star full melt hash.
```"""
    },
    {
        "category": "BAR_QUESTION_I15",
        "instruction": "A junior developer generated this hero section for the WildSeed Dispensary Portal. Identify the invariant violation and explain why it damages brand equity.",
        "input": """<div className="hero bg-amber-900 text-white p-8">
  <h1>WildSeed Saloon & Terpene Bar</h1>
  <p>Pull up a stool, order a shot of aged rye whiskey, and enjoy our cannabis concentrates!</p>
  <button>Order Double Bourbon</button>
</div>""",
        "output": """### Architectural Defect Analysis
**Violation of Invariant I.15 (The StackSeeder 'Bar Question' Psychographic Translation Invariant)**:
- The StackSeeder 'Bar Question' (*"What does the brand order to drink at a dive bar?"*) is strictly an internal psychographic diagnostic used during persona genesis to discern archetype, grit, and socioeconomic class.
- Taking the bar question literally by transforming a client portal into a drinking bar or depicting working cannabis advocates drinking alcohol on the job is strictly forbidden.
- Promoting alcohol on a cannabis/wellness platform violates DCC regulations, brand integrity, and customer trust. WildSeed advocates operate in craft tasting lounges, living-soil greenhouses, and solventless hash labs—utilizing low-temp dab rigs, hash jars, and gas chromatographs, NOT whiskey glasses.

### Hardened Refactor
```tsx
export const WildSeedCraftLoungeHero = () => {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-[#0c120c] border border-emerald-900/40 p-8 shadow-2xl">
      <div className="max-w-2xl">
        <span className="text-xs font-mono uppercase tracking-widest text-emerald-400">
          Solventless Craftsmanship • Single-Source Living Soil
        </span>
        <h1 className="mt-2 text-3xl font-serif text-slate-100 tracking-tight">
          WildSeed Solventless Hash & Terpene Parlor
        </h1>
        <p className="mt-3 text-sm text-emerald-200/70 leading-relaxed font-sans">
          Curated ice-water full melt hash, cold-cure live rosin, and whole-plant terpene preservation. 
          Extracted at sub-zero temperatures using pure Humboldt spring water and 73u–120u micron sieves.
        </p>
        <div className="mt-6 flex gap-3">
          <button className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-medium text-sm transition-all shadow-lg shadow-emerald-950/50">
            Explore 6-Star Full Melt
          </button>
          <button className="px-5 py-2.5 rounded-lg bg-slate-900 border border-emerald-800/40 text-emerald-300 font-medium text-sm hover:bg-slate-800 transition-all">
            View COA Terpene Profiles
          </button>
        </div>
      </div>
    </div>
  );
};
```"""
    },
    {
        "category": "FIVE_ADVOCATES_ONE_HEEL",
        "instruction": "Explain the StackLabs '5 Advocates + 1 Heel' MARD consensus architecture and implement an automated validation check for content publication.",
        "input": """# Need a validation function for new clinical articles before publishing to ARKLE Vet search graph.""",
        "output": """### Architectural Overview: The 5 Advocates + 1 Heel Consensus Engine
In the Sovereign OS Multi-Agent Reactive Discourse (MARD) framework, automated decisions and content generation must never rely on a single unvetted LLM response. 

Instead, decisions pass through a calibrated 6-agent council:
- **5 Domain Advocates**: Specialized personas providing deep subject-matter expertise (e.g. Dr. Rox for surgical dentistry/CMO sign-off, Dr. Chen for diagnostic pathology, Dr. Marcus for soft-tissue surgery, Sarah for feline Fear-Free care, Metsy as standards inspector).
- **1 Regulatory Warden (The 'Heel')**: An aggressive contrarian auditor (e.g. Brenda CVT) whose sole duty is to obliterate dangerous home remedies, pinpoint statutory/DCC/AVMA liabilities, and veto non-compliant copy before release.

### Hardened Implementation
```python
from typing import List, Dict, Any

class MARDConsensusError(Exception):
    \"\"\"Raised when the Heel or Advocate council vetoes a content release.\"\"\"
    pass

def evaluate_mard_consensus(
    article_title: str,
    claims: List[str],
    advocate_evaluations: List[Dict[str, Any]],
    heel_evaluation: Dict[str, Any]
) -> Dict[str, Any]:
    \"\"\"
    Enforces 5 Advocates + 1 Heel consensus gate for content or code deployment.
    Requires >= 80% advocate agreement AND zero unaddressed Heel regulatory vetoes.
    \"\"\"
    # 1. Evaluate Heel (The Regulatory Warden) - Absolute Veto Authority
    heel_veto = heel_evaluation.get("veto", False)
    heel_objections = heel_evaluation.get("regulatory_violations", [])
    
    if heel_veto or len(heel_objections) > 0:
        raise MARDConsensusError(
            f"VETOED BY REGULATORY WARDEN ({heel_evaluation.get('agent_name', 'Brenda CVT')}): "
            f"{'; '.join(heel_objections)}"
        )
        
    # 2. Evaluate Advocate Approvals (Minimum 4 of 5 required)
    approvals = [a for a in advocate_evaluations if a.get("approved", False)]
    approval_ratio = len(approvals) / max(len(advocate_evaluations), 1)
    
    if approval_ratio < 0.8:
        raise MARDConsensusError(
            f"INSUFFICIENT ADVOCATE CONSENSUS: Only {len(approvals)}/{len(advocate_evaluations)} "
            f"advocates approved article '{article_title}'."
        )
        
    return {
        "status": "APPROVED_FOR_PUBLICATION",
        "article_title": article_title,
        "advocate_approvals": len(approvals),
        "total_advocates": len(advocate_evaluations),
        "heel_signoff": heel_evaluation.get("agent_name"),
        "consensus_timestamp": "ISO-8601-VERIFIED"
    }
```"""
    }
]

def format_entry(example: Dict[str, Any]) -> Dict[str, Any]:
    """Format an example into ShareGPT/ChatML instruction format."""
    return {
        "instruction": example["instruction"],
        "input": example.get("input", ""),
        "output": example["output"],
        "category": example["category"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{example['instruction']}\n\n```\n{example.get('input', '')}\n```" if example.get('input') else example['instruction']},
            {"role": "assistant", "content": example["output"]}
        ]
    }

def generate_dataset(output_paths: List[str]) -> None:
    """Generate the JSONL dataset and write to specified paths."""
    formatted_data = [format_entry(ex) for ex in EXAMPLES]
    print(f"[*] Generating {len(formatted_data)} high-signal instruction pairs...")
    
    for path in output_paths:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for item in formatted_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"[✓] Written dataset to: {path} ({os.path.getsize(path)} bytes)")

def main():
    parser = argparse.ArgumentParser(description="StackLabs Crucible Instruction Dataset Generator")
    parser.add_argument("--primary-out", default="/home/james/stacklabs/dna/docs/stacklabs_crucible_dataset.jsonl",
                        help="Primary path for dataset output")
    parser.add_argument("--mirror-out", default="/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/weekly_additions/stacklabs_crucible_dataset.jsonl",
                        help="Mirror path for Google Drive / NotebookLM sync")
    args = parser.parse_args()

    paths = [args.primary_out, args.mirror_out]
    generate_dataset(paths)

if __name__ == "__main__":
    main()
