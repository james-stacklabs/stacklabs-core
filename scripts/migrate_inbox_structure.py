#!/usr/bin/env python3
import os
import shutil
import argparse

INBOX_DIR = "/home/james/sovereign_inbox"
TICKETS_DIR = os.path.join(INBOX_DIR, "tickets")
PLANS_DIR = os.path.join(INBOX_DIR, "implementation_plans")
WALKTHROUGHS_DIR = os.path.join(INBOX_DIR, "walkthroughs")
WIRE_FRAMES_DIR = os.path.join(TICKETS_DIR, "wire_frames")

def main():
    parser = argparse.ArgumentParser(description="Migrate sovereign_inbox ticket subfolders")
    parser.add_argument("--dry-run", action="store_true", help="Print planned movements without applying them")
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY-RUN MODE: Showing planned migration ledger. No files will be moved.")
        
    # Ensure target directories exist if not dry-run
    if not args.dry_run:
        os.makedirs(PLANS_DIR, exist_ok=True)
        os.makedirs(WALKTHROUGHS_DIR, exist_ok=True)
        os.makedirs(TICKETS_DIR, exist_ok=True)
        
    moves_planned = []
    
    # 1. Scan source folders (INBOX_DIR root and TICKETS_DIR)
    # We do not use os.walk because we only want to sweep files at the root level of these folders,
    # thereby avoiding traversing into subfolders like wire_frames/.
    scan_folders = [INBOX_DIR, TICKETS_DIR]
    
    for folder in scan_folders:
        if not os.path.exists(folder):
            continue
            
        for entry in os.scandir(folder):
            if not entry.is_file():
                continue
                
            filename = entry.name
            filename_lower = filename.lower()
            
            # Determine if this file needs to be relocated
            dest_dir = None
            if "implementation_plan_" in filename_lower:
                dest_dir = PLANS_DIR
            elif "walkthrough_" in filename_lower:
                dest_dir = WALKTHROUGHS_DIR
                
            if dest_dir:
                # Calculate new path
                dest_path = os.path.join(dest_dir, filename)
                
                # Check if it's already in the correct folder
                if os.path.abspath(entry.path) != os.path.abspath(dest_path):
                    moves_planned.append((entry.path, dest_path))
                    
    # Show migration ledger
    if not moves_planned:
        print("✨ No files need to be relocated. Inbox structure is already aligned.")
        return
        
    print(f"📦 Found {len(moves_planned)} files to relocate:")
    for src, dest in moves_planned:
        print(f"  - Move: {src} -> {dest}")
        
    if args.dry_run:
        print("🔍 Dry-run completed. No actions taken.")
        return
        
    # Execute moves
    moved_count = 0
    for src, dest in moves_planned:
        try:
            shutil.move(src, dest)
            print(f"  [✔] Moved: {os.path.basename(src)}")
            moved_count += 1
        except Exception as e:
            print(f"  [❌] Failed to move {src} -> {dest}: {e}")
            
    print(f"✅ Reorganization completed. Relocated {moved_count} files.")

if __name__ == "__main__":
    main()
