#!/usr/bin/env bash
# =============================================================================
# SOVEREIGN CLONE DB — Environment Database Cloner
# =============================================================================
# The ServiceNow "Clone Instance" equivalent for Sovereign OS databases.
# Clones a database from one environment to another using SQLite's safe
# backup API (atomic, no corruption risk).
#
# Usage:
#   ./scripts/clone_db.sh prod sandbox    # Clone prod → sandbox (before Gemini task)
#   ./scripts/clone_db.sh prod dev        # Clone prod → dev (refresh dev data)
#   ./scripts/clone_db.sh prod uat        # Clone prod → uat (refresh uat data)
#
# Rules:
#   - Clones flow DOWNWARD only (prod → lower tiers)
#   - Cannot clone TO prod (sovereign_now.db is sacred)
#   - Always creates a backup of the target before overwriting
# =============================================================================

set -euo pipefail

FROM_ENV="${1:-}"
TO_ENV="${2:-}"

# ── Color output ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[CLONE_DB]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── DB path map ───────────────────────────────────────────────────────────────
db_path() {
    case "$1" in
        prod)    echo "/home/james/stacklabs/sovereign_now.db" ;;
        dev)     echo "/home/james/stacklabs-dev/sovereign_dev.db" ;;
        uat)     echo "/home/james/stacklabs-uat/sovereign_uat.db" ;;
        sandbox) echo "/home/james/stacklabs-sandbox/sovereign_sandbox.db" ;;
        *)       err "Unknown environment: $1. Valid: prod, dev, uat, sandbox" ;;
    esac
}

# ── Validate args ─────────────────────────────────────────────────────────────
if [[ -z "$FROM_ENV" || -z "$TO_ENV" ]]; then
    echo "Usage: $0 <source_env> <target_env>"
    echo "Valid sources: prod, dev, uat"
    echo "Valid targets: dev, uat, sandbox (NEVER prod)"
    exit 1
fi

if [[ "$TO_ENV" == "prod" ]]; then
    err "BLOCKED: Cannot clone TO prod. sovereign_now.db is immutable during development."
fi

if [[ "$FROM_ENV" == "$TO_ENV" ]]; then
    err "Source and target cannot be the same environment."
fi

FROM_DB=$(db_path "$FROM_ENV")
TO_DB=$(db_path "$TO_ENV")

# ── Validate source exists ────────────────────────────────────────────────────
if [[ ! -f "$FROM_DB" ]]; then
    err "Source database not found: $FROM_DB"
fi

# ── Show plan ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo -e "${BOLD}  SOVEREIGN CLONE DB: ${FROM_ENV} → ${TO_ENV}${NC}"
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo ""
log "Source: ${FROM_DB}"
log "Target: ${TO_DB}"

FROM_SIZE=$(du -sh "$FROM_DB" 2>/dev/null | cut -f1)
log "Source size: ${FROM_SIZE}"

# ── Backup existing target if it exists ───────────────────────────────────────
if [[ -f "$TO_DB" ]]; then
    BACKUP="${TO_DB}.bak_$(date +%Y%m%d_%H%M%S)"
    log "Backing up existing ${TO_ENV} DB → ${BACKUP}"
    cp "$TO_DB" "$BACKUP"
    ok "Backup created."
fi

# ── Confirm ───────────────────────────────────────────────────────────────────
read -rp "$(echo -e "${YELLOW}Proceed with clone ${FROM_ENV} → ${TO_ENV}? [y/N]: ${NC}")" confirm
if [[ "${confirm,,}" != "y" ]]; then
    warn "Clone cancelled."
    # Restore backup if we created one
    if [[ -n "${BACKUP:-}" && -f "$BACKUP" ]]; then
        rm -f "$BACKUP"
    fi
    exit 0
fi

# ── Execute clone using SQLite backup API ─────────────────────────────────────
log "Cloning database (SQLite atomic backup)..."
sqlite3 "$FROM_DB" ".backup '$TO_DB'"

ok "Clone complete."
TO_SIZE=$(du -sh "$TO_DB" 2>/dev/null | cut -f1)
log "Target size: ${TO_SIZE}"

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✅ CLONE COMPLETE: ${FROM_ENV} → ${TO_ENV}${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${NC}"
echo ""
warn "Remember: Update the .env.${TO_ENV} file if DB_PATH has changed."
