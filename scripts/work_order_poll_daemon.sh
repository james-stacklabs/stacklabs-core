#!/bin/bash
DB_PATH="/home/james/stacklabs/dna/sovereign_now.db"
WATCH_DIR="/home/james/stacklabs/work_orders"

while true; do
   INTERVAL_SEC=$(sqlite3 "$DB_PATH" "SELECT param_value FROM system_cron_config WHERE param_key='work_order_poll_interval_sec';")
   if [ -z "$INTERVAL_SEC" ]; then
       INTERVAL_SEC=300
   fi
   NEW_ORDERS=$(find "$WATCH_DIR" -name "WO-*.md" -mmin -$((INTERVAL_SEC / 60)) 2>/dev/null)
   if [ ! -z "$NEW_ORDERS" ]; then
       antigravity --notify "Dynamic Ingress Notice: New Work Orders Staged in Vault Dropzone"
   fi
   sleep "$INTERVAL_SEC"
done
