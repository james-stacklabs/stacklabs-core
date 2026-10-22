# STACKLABS PLATFORM: REPOSITORY AI CONSTITUTION & EXECUTION INVARIANTS

> **Scope**: Binding operational constitution for autonomous execution workers across StackLabs.  
> **Ground Truth Vault**: Canonical state resides strictly in `/home/james/stacklabs/ground_truth/`.  
> **Temporal Baseline**: October 2026.

---

## 🛑 CURRENT OPERATIONAL REALITY & ACTIVE MODEL INVARIANT
> 🚨 **ABSOLUTE RULE: ACTIVE GEMINI MODELS ONLY (OCTOBER 2026)**:
> - ❌ **DEPRECATED & FORBIDDEN (WILL 404)**: `gemini-1.5-*`, `gemini-2.0-*`, `gemini-2.5-*`, `gemini-3.7-*`
> - ✅ **CANONICAL ACTIVE MODELS**: `gemini-3.8-flash` (primary), `gemini-flash-latest`, `gemini-flash-lite-latest` (fast/lite), `gemini-3.1-pro-preview` / `gemini-pro-latest` (reasoning).
> - Any agent attempting to use deprecated models is in direct constitutional breach.

1. **Active Gemini Models**: Strictly `gemini-3.8-flash` or `gemini-flash-lite-latest`. NEVER attempt 2.5, 3.7, 2.0, or 1.5.
2. **Active Enterprise Clients**: Exactly zero.
3. **Field Deployments**: Exactly zero.
4. **Hardware Sales / Manufacturing**: Strictly zero. StackLabs builds enterprise software on dedicated local hosts.
5. **Commercial Boundary**: Exploratory prospect conversations are strictly unclosed prospect models (`PROSPECT_SCENARIO`).
6. **Solo Builder Voice (Invariant 32)**: James Carroll is a solo systems architect. Strictly singular first-person ("I", "my").
7. **Deployment Embargo (Invariant 22)**: Autonomous edge deploys (`wrangler deploy`) are strictly banned. Local build and verification required.
8. **Acoustic Silicon Gating (Artemis CUDA)**: Raw audio/video (>30s) must NEVER be uploaded to Google Gemini File API. Mandatory routing through Artemis GTX 1060 CUDA Faster-Whisper (100.108.185.53). Cloud Gemini models receive text transcripts only.
9. **Watson Gem Invariant**: The mobile research/sparring Gem is strictly named **Watson** (NOT Mycroft). Any prompt or passport referencing 'Mycroft' is a constitutional breach. Target notebook is `StackLabs Ground Truth Vault // Watson Intelligence Base`.
10. **Zero Conversation / Model Leakage & Collapsible Text Law**: NEVER take literal phrases from chat conversations (`SOX vs socks`, `Market Blowtorches`, `Zero-API-Key`), model names (`gemini-3.8-flash`), or backend plumbing (`GTX 1060`, `WAL Mode`, `127.0.0.1:8088`) and hardcode them into HTML labels, headers, or badges. Keep primary UIs minimal and scannable; put all long-winded text, transcripts, lore, and secondary details inside **collapsible sections that are closed by default (`false`)**.

---

## ⚡ RULE ZERO: DIVISION OF LABOR
- **Interactive Cockpit**: Investigates root causes, plans, and stages 4-Quarters Work Orders into `/home/james/stacklabs/queue/incoming/`. Zero code editing in chat.
- **Autonomous Worker (Aggie)**: Claims tickets from `queue/incoming/`, modifies code, runs builds, and archives to `queue/archive/`.

---

## 📋 GOVERNING PROGRESSIVE RULES
Specialized policies auto-load from `/home/james/stacklabs/.agents/rules/`:
- `zero-trust-network.md` (`globs: "**/*.py, **/*.ts, **/*.tsx, **/*.service"`)
- `07_FRONTEND_CRAFT_AND_ANTI_SLOP.md` (`globs: "**/*.tsx, **/*.ts, **/*.css, **/*.html"`)
- `06_CMDB_CI_LIFECYCLE_GOVERNANCE.md` (`globs: "**/cmdb/**, **/vfs/**, **/ground_truth/**"`)
- `08_ZERO_PLAINTEXT_HTTP_AND_TLS_TERMINATION.md` (`globs: "**/*.py, **/*.ts, **/*.service"`)
- `09_CLIENT_DEMO_AIR_GAP_AND_ANTI_SANDBOX.md` (`globs: "apps/**"`)
- `11_DECOUPLED_BLUEPRINTS_AND_ANTI_MONOLITH.md` (`globs: "scripts/**/*.py, **/*_server.py, **/*_relay.py"`)
- `12_WATSON_GEM_AND_ANTI_MYCROFT_INVARIANT.md` (`globs: "**/*.py, **/*.md, **/*.sh"`)
