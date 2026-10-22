#!/usr/bin/env bash
# =============================================================================
# SOVEREIGN PROMOTE — Code Promotion Gate
# =============================================================================
# The ServiceNow "Update Set" promotion equivalent for Sovereign OS git SDLC.
# Promotes code changes from one environment branch to another.
#
# Usage:
#   ./scripts/promote.sh dev uat          # Promote dev → UAT (Claude self-service)
#   ./scripts/promote.sh uat main         # Promote UAT → Prod (Pilot approval REQUIRED)
#
# Rules:
#   - dev  → uat:  Claude may execute. Shows diff. Requires 'y' confirmation.
#   - uat  → main: Requires PILOT=true env var as an extra safety gate.
#                  Logs promotion to rm_story table in sovereign_now.db.
#   - No other promotion paths are valid (e.g. dev → main is BLOCKED).
# =============================================================================

set -euo pipefail

FROM="${1:-}"
TO="${2:-}"
DB_PATH="/home/james/stacklabs/dna/sovereign_now.db"
REPO_ROOT="/home/james/stacklabs"

# ── Color output ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[PROMOTE]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ── Validate args ─────────────────────────────────────────────────────────────
if [[ -z "$FROM" || -z "$TO" ]]; then
    echo "Usage: $0 <from_env> <to_env>"
    echo "Valid paths: dev→uat | uat→main"
    exit 1
fi

# ── Valid promotion paths only ────────────────────────────────────────────────
case "${FROM}→${TO}" in
    "dev→uat")
        GATE="standard"
        ;;
    "uat→main")
        GATE="pilot"
        ;;
    "dev→main")
        err "BLOCKED: Cannot promote dev directly to main. Path: dev → uat → main."
        ;;
    "sandbox→"*)
        err "BLOCKED: Sandbox code never promotes directly. Sandbox is Gemini-only territory."
        ;;
    *)
        err "Invalid promotion path: ${FROM} → ${TO}. Valid: dev→uat, uat→main"
        ;;
esac

# ── Pilot gate for uat→main ───────────────────────────────────────────────────
if [[ "$GATE" == "pilot" ]]; then
    if [[ "${PILOT:-}" != "true" ]]; then
        echo ""
        err "PILOT GATE: UAT → Prod requires explicit Pilot authorization."
        echo -e "  Run with: ${BOLD}PILOT=true ./scripts/promote.sh uat main${NC}"
        echo ""
        exit 1
    fi
    warn "PILOT GATE ACTIVE: You are promoting to PRODUCTION. There is no undo without a revert commit."
fi

# ── Confirm git repo ──────────────────────────────────────────────────────────
cd "$REPO_ROOT"
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    err "Not a git repository: $REPO_ROOT"
fi

# ── Show what will be promoted (the diff summary) ─────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo -e "${BOLD}  SOVEREIGN PROMOTE: ${FROM} → ${TO}${NC}"
echo -e "${BOLD}════════════════════════════════════════════${NC}"
echo ""

COMMIT_COUNT=$(git log --oneline "${TO}..${FROM}" 2>/dev/null | wc -l | tr -d ' ')

if [[ "$COMMIT_COUNT" -eq 0 ]]; then
    ok "Nothing to promote — ${FROM} is already up to date with ${TO}."
    exit 0
fi

log "Commits to be promoted (${COMMIT_COUNT}):"
git log --oneline "${TO}..${FROM}"
echo ""

log "Files changed:"
git diff --stat "${TO}..${FROM}"
echo ""

# ── Confirmation prompt ───────────────────────────────────────────────────────
if [[ "$GATE" == "pilot" ]]; then
    echo -e "${RED}${BOLD}⚠️  PRODUCTION PROMOTION — This affects LIVE users.${NC}"
fi

read -rp "$(echo -e "${YELLOW}Proceed with ${FROM} → ${TO}? [y/N]: ${NC}")" confirm
if [[ "${confirm,,}" != "y" ]]; then
    warn "Promotion cancelled."
    exit 0
fi

# ── Execute the merge ─────────────────────────────────────────────────────────
# With git worktrees, we cannot checkout a branch that is checked out elsewhere.
# We must perform the merge inside the target branch's worktree.

TARGET_WORKTREE="${REPO_ROOT}"
if [[ "$TO" != "main" ]]; then
    TARGET_WORKTREE="${REPO_ROOT}-${TO}"
fi

log "Switching to ${TO} worktree at ${TARGET_WORKTREE}..."
if [[ ! -d "$TARGET_WORKTREE" ]]; then
    err "Target worktree directory not found: $TARGET_WORKTREE"
fi
cd "$TARGET_WORKTREE"

log "Merging ${FROM} into ${TO}..."
git merge "$FROM" --no-ff -m "chore(promote): ${FROM} → ${TO} — $(date '+%Y-%m-%d %H:%M')"

ok "Merge complete."
cd "$REPO_ROOT"

# ── Log to SDLC table ─────────────────────────────────────────────────────────
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SHORT_DESC="${COMMIT_COUNT} commit(s) promoted from ${FROM} to ${TO}"

if [[ -f "$DB_PATH" ]]; then
    sqlite3 "$DB_PATH" <<SQL 2>/dev/null || warn "Could not log to rm_story (table may not exist yet)"
INSERT INTO rm_story (
    sys_id, number, short_description, state, assigned_to,
    opened_at, closed_at, sys_created_on, sys_updated_on
) VALUES (
    lower(hex(randomblob(16))),
    'PROMOTE-$(date +%Y%m%d%H%M%S)',
    '${SHORT_DESC}',
    '$( [[ "$TO" == "main" ]] && echo "Deployed" || echo "In Progress" )',
    'sovereign_promote_sh',
    '${TIMESTAMP}',
    '$( [[ "$TO" == "main" ]] && echo "$TIMESTAMP" || echo "" )',
    '${TIMESTAMP}',
    '${TIMESTAMP}'
);
SQL
    ok "Logged to rm_story."
fi

# ── Return to dev branch (default working branch) ─────────────────────────────
cd "${REPO_ROOT}-dev" 2>/dev/null || cd "$REPO_ROOT"

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✅ PROMOTION COMPLETE: ${FROM} → ${TO}${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${NC}"
echo ""
git log --oneline -5
