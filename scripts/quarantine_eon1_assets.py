#!/usr/bin/env python3
import os
import shutil
import sys

AVATARS_DIR = "/home/james/stacklabs/avatars"
QUARANTINE_DIR = "/home/james/stacklabs/archive_quarantine_eon1"
VERIFIED_SUBDIRS = {"@metsy_smyrna", "metsy_smyrna", "unclesteviestan", "isolated_silo", "counsellwasright", "cubbieconspiracy", "stumpy_jr"}
VERIFIED_FILES = {"metsy_tight_cropped.png"}

def main():
    if not os.path.exists(AVATARS_DIR):
        print(f"Error: Avatars directory {AVATARS_DIR} does not exist.")
        sys.exit(1)
        
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    print(f"Quarantine directory initialized: {QUARANTINE_DIR}")
    
    moved_files = []
    moved_dirs = []
    
    # Iterate over all items in avatars directory
    for item_name in os.listdir(AVATARS_DIR):
        item_path = os.path.join(AVATARS_DIR, item_name)
        dest_path = os.path.join(QUARANTINE_DIR, item_name)
        
        # Check if directory
        if os.path.isdir(item_path):
            if item_name in VERIFIED_SUBDIRS:
                print(f"Preserving verified subdirectory: {item_name}")
                continue
            
            print(f"Moving subdirectory to quarantine: {item_name}")
            try:
                shutil.move(item_path, dest_path)
                moved_dirs.append(item_name)
            except Exception as e:
                print(f"Error moving directory {item_name}: {e}")
        else:
            # It's a file
            if item_name in VERIFIED_FILES:
                print(f"Preserving verified file: {item_name}")
                continue
                
            print(f"Moving loose file to quarantine: {item_name}")
            try:
                shutil.move(item_path, dest_path)
                moved_files.append(item_name)
            except Exception as e:
                print(f"Error moving file {item_name}: {e}")
                
    print("\n--- Quarantine Migration Summary ---")
    print(f"Moved {len(moved_files)} loose files.")
    print(f"Moved {len(moved_dirs)} subdirectories.")
    print(f"Verified subdirectories preserved: {', '.join(VERIFIED_SUBDIRS)}")
    print("------------------------------------\n")

if __name__ == "__main__":
    main()
