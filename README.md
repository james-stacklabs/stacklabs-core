# StackLabs Core (`stacklabs-core`)

- **Lead Systems Architect**: James Carroll (Pilot), StackLabs LLC
- **Primary Workstation**: Clio (`clio` / Dedicated Linux Host / `100.96.77.20`)
- **Active Model Baseline**: `gemini-3.8-flash` & `gemini-flash-lite-latest` (October 2026)

## Architecture Overview

1. **Virtual File System (`vfs/`)**:
   - Canonical workspaces (`/vfs/spaces/pawel/`), curated research vaults (`/vfs/vault/`), Swanson Undiscovered Public Knowledge (UPK) synthesis reports (`/vfs/spaces/pawel/investigations/`), and the 28-Slot Shadow Prediction Board (`/vfs/spaces/pawel/predictions/`).
2. **Service Blueprints & Automation (`scripts/`)**:
   - Decoupled FastAPI/Flask service routers, Swanson Collider engines, Ground Truth validators, and Google Drive (`stacklabs_edge:` / `stacklabs_vault:`) synchronization pipelines.
3. **4-Quarters Autonomous Queue (`queue/`)**:
   - Deterministic GitOps ticket pipeline (`queue/incoming/` -> `queue/processing/` -> `queue/archive/`) executed on Clio via `clio_queue_watcher.py`.
4. **Pilot Drops & Continuity Passports (`pilot_drops/` & `vault/`)**:
   - Cross-session continuity passports (`PILOT_PASSPORT_CURRENT.md`), syllabus indices (`PAWEL_28_ESSAY_SYLLABUS_INDEX.md`), and indexed research artifacts.
