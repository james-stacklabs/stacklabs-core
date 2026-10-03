# StackLabs Core

Enterprise data pipelines, autonomous sports & creator intelligence, and quantitative burst trading engines. Built by James Carroll (StackLabs LLC) directly on bare metal.

## System Topology
* `scripts/`: Modular microservices and ingress gateway (Flask <= 400 lines)
* `scripts/blueprints/`: Decoupled route controllers (`cockpit`, `sync`, `media`, `horizon`, `pulse`)
* `scripts/templates/`: Pure Jinja HTML/CSS/JS frontend views
* `scripts/sicko_engine.py`: 30-day quantitative burst trading engine & state machine
* `tests/`: Automated Playwright visual twins and parity verification harnesses

## Operational Invariants
1. Solo Builder Authority: Built and maintained by James Carroll.
2. K.I.S.S. & Decoupled: Zero inline HTML in Python; modular blueprints only.
3. Metal Telemetry: Verified against live SQLite WAL read-models and local ingress daemons.