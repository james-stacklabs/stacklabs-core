#!/bin/bash
# sovereign_rip.sh - Fast context grab utility
# Run this from the terminal instead of asking an AI proxy

CLAUDE_SESSION_DIR=$(find /home/james/stacklabs/dna/agents/CLAUDE/active_sessions -maxdepth 1 -type d -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2)

echo "[*] Grabbing active Tailscale map..."
tailscale status > /tmp/ts_status.txt
echo -e "# Live Tailscale Status\n\`\`\`\n$(cat /tmp/ts_status.txt)\n\`\`\`\n" > "$CLAUDE_SESSION_DIR/TAILSCALE_CONTEXT.md"
cat /home/james/stacklabs/sync_tailscale_cmdb.py >> "$CLAUDE_SESSION_DIR/TAILSCALE_CONTEXT.md"

echo "[*] Grabbing SDLC Tickets..."
sqlite3 -markdown /home/james/stacklabs/dna/sovereign_now.db "SELECT number, short_description, type, CASE state WHEN 1 THEN 'Open' WHEN 2 THEN 'In Progress' WHEN 3 THEN 'Testing' WHEN 4 THEN 'Resolved' WHEN 5 THEN 'Closed' END as status, CASE priority WHEN 1 THEN 'P1' WHEN 2 THEN 'P2' WHEN 3 THEN 'P3' WHEN 4 THEN 'P4' END as priority, description FROM sovereign_tickets WHERE state < 4 ORDER BY priority ASC, number DESC;" > "$CLAUDE_SESSION_DIR/SDLC_TICKETS_EXPORT.md"

echo "[*] All data securely ripped to latest active session:"
echo "--> $CLAUDE_SESSION_DIR"
