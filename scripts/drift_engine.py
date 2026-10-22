#!/usr/bin/env python3
# ==============================================================================
# Sovereign OS: Drift Engine (Phase 3 Deployment Service)
# Path: /home/james/stacklabs/scripts/drift_engine.py
# ==============================================================================
import os
import sys
import time
import logging
import sqlite3

# Add scripts directory to path to import db helper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import get_db

LOG_FILE = "/home/james/stacklabs/logs/drift_engine.log"
POLL_INTERVAL_SECS = 2.0
PRINCIPAL_CAPITAL = 100000.0  # $100,000 for standard calculations
FLASH_LOAN_FEE_PCT = 0.0009   # 0.09%

def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Also log to stdout
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

class DriftEngine:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.running = True

    def process_pending_rifts(self):
        """Processes unprocessed records in web3_pricing_ingress and aggregates calculations into drift_metrics."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                # Get all unprocessed rifts ordered by price delta descending
                cursor.execute("""
                    SELECT sys_id, token_pair, source_exchange, target_exchange, price_delta, estimated_gas 
                    FROM web3_pricing_ingress 
                    WHERE processed = 0 
                    ORDER BY price_delta DESC
                """)
                rows = cursor.fetchall()
                
                if not rows:
                    return 0

                processed_count = 0
                for row in rows:
                    sys_id, pair, src, dst, delta, gas = row
                    
                    # Compute projected profit
                    # Gross return: principal * delta
                    gross_return = PRINCIPAL_CAPITAL * delta
                    # Flash loan fee: principal * 0.0009
                    flash_fee = PRINCIPAL_CAPITAL * FLASH_LOAN_FEE_PCT
                    # Net profit: gross return - flash fee - gas cost
                    net_profit = gross_return - flash_fee - gas
                    
                    logging.info(f"[*] Processing Drift ID {sys_id} [{pair}]: Delta={delta * 100:.3f}%, Gas=${gas:.2f}, Est. Net Profit=${net_profit:.2f}")

                    # Update drift_metrics aggregates
                    # Calculate new running averages, max delta, and totals
                    cursor.execute("""
                        SELECT drift_count, average_delta, max_delta, total_gas, total_profit 
                        FROM drift_metrics 
                        WHERE token_pair = ?
                    """, (pair,))
                    metrics = cursor.fetchone()
                    
                    if metrics:
                        count, avg_delta, max_delta, total_gas, total_profit = metrics
                        new_count = count + 1
                        new_avg_delta = ((avg_delta * count) + delta) / new_count
                        new_max_delta = max(max_delta, delta)
                        new_total_gas = total_gas + gas
                        new_total_profit = total_profit + net_profit
                        
                        cursor.execute("""
                            UPDATE drift_metrics 
                            SET drift_count = ?, average_delta = ?, max_delta = ?, total_gas = ?, total_profit = ?, sys_updated_on = CURRENT_TIMESTAMP
                            WHERE token_pair = ?
                        """, (new_count, new_avg_delta, new_max_delta, new_total_gas, new_total_profit, pair))
                    else:
                        cursor.execute("""
                            INSERT INTO drift_metrics (token_pair, drift_count, average_delta, max_delta, total_gas, total_profit)
                            VALUES (?, 1, ?, ?, ?, ?)
                        """, (pair, delta, delta, gas, net_profit))

                    # Mark record as processed
                    cursor.execute("""
                        UPDATE web3_pricing_ingress 
                        SET processed = 1 
                        WHERE sys_id = ?
                    """, (sys_id,))
                    
                    processed_count += 1
                    
                conn.commit()
                return processed_count
                
        except Exception as e:
            logging.error(f"[ERROR] Failed during batch processing iteration: {e}")
            return 0

    def run(self):
        logging.info("==========================================================")
        logging.info("[STARTUP] Drift Engine (Phase 3 Daemon) initialized.")
        logging.info(f"[CONFIG] Principal Capital Size: ${PRINCIPAL_CAPITAL:,.2f}")
        logging.info(f"[CONFIG] Flash Loan Fee: {FLASH_LOAN_FEE_PCT * 100:.3f}%")
        logging.info("==========================================================")
        
        if self.dry_run:
            logging.info("[DRY-RUN] Executing single pass sweep...")
            processed = self.process_pending_rifts()
            logging.info(f"[DRY-RUN] Single pass completed. Processed {processed} records.")
            return

        try:
            while self.running:
                processed = self.process_pending_rifts()
                if processed > 0:
                    logging.info(f"[DRIFT SWEEP] Successfully calculated and aggregated {processed} pricing rifts.")
                time.sleep(POLL_INTERVAL_SECS)
        except KeyboardInterrupt:
            logging.info("[SHUTDOWN] Keyboard interrupt received.")
        finally:
            logging.info("[SHUTDOWN] Drift Engine daemon terminated gracefully.")

if __name__ == "__main__":
    setup_logging()
    
    dry_run_flag = "--dry-run" in sys.argv
    engine = DriftEngine(dry_run=dry_run_flag)
    engine.run()
