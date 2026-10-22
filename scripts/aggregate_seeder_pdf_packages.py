#!/usr/bin/env python3
"""
Sovereign OS - Seeder PDF Aggregator
Locates and groups all package manuals generated during today's ingestion sprints.
"""
import os
import shutil
import time

SOURCE_DIRS = [
    "/home/james/sovereign_inbox/reports/",
    "/home/james/sovereign_inbox/today/",
    "/home/james/stacklabs/dna/reports/"
]
TARGET_SILO = "/home/james/sovereign_inbox/reports/review_silo/"

def harvest_packages():
    print("🚀 Initiating Stack Seeder PDF Harvest Sequence...")
    os.makedirs(TARGET_SILO, exist_ok=True)
    current_time = time.time()
    pdf_count = 0

    for src in SOURCE_DIRS:
        if not os.path.exists(src):
            continue
        for root, _, files in os.walk(src):
            for file in files:
                if file.lower().endswith(".pdf"):
                    file_path = os.path.join(root, file)
                    # Filter strictly by files modified within the last 24 hours (86400 seconds)
                    if current_time - os.path.getmtime(file_path) < 86400:
                        target_path = os.path.join(TARGET_SILO, file)
                        if os.path.abspath(file_path) == os.path.abspath(target_path):
                            continue
                        print(f"  [HARVEST] Found valid target: {file} -> Staging to Silo")
                        shutil.copy2(file_path, target_path)
                        pdf_count += 1

    print(f"🏁 Harvest complete. Staged {pdf_count} package manuals cleanly into {TARGET_SILO}")

if __name__ == "__main__":
    harvest_packages()
