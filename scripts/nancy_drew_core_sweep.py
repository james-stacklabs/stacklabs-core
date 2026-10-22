import os
import shutil
import time

CORE_DIR = "/home/james/stacklabs/04_Sovereign_Core"
VAULT_DIR = "/home/james/stacklabs/dna/vault/legacy_ci"

print("\n=====================================================================")
print("🕵️‍♀️  THE NANCY DREW PROTOCOL (PHASE 2: RESORTING TO DANGER!) 🕵️‍♀️")
print("=====================================================================\n")
print(f"Unlocking the door to: {CORE_DIR}...")
print("Scanning the room for orphaned flat-files and hidden objects...\n")
time.sleep(1)

hidden_objects = [f for f in os.listdir(CORE_DIR) if f.endswith(".json") or f.endswith(".backup")]

if not hidden_objects:
    print("🔍 The room is completely clean! No Hidden Objects found. The Comb is pure.")
else:
    score = 0
    for obj in hidden_objects:
        obj_path = os.path.join(CORE_DIR, obj)
        size_kb = os.path.getsize(obj_path) / 1024.0
        print("-" * 65)
        print(f"🔍 Investigating Apparent Anomaly: {obj} ({size_kb:.1f} KB)")
        time.sleep(0.5)
        
        # Interactive Prompt for the Pilot
        ans = input(f"   ⚠️  Is this a rogue clue? Banish to the Ship of Shadows? [Y/N]: ").strip().upper()
        
        if ans == 'Y':
            dest = os.path.join(VAULT_DIR, obj)
            
            # Handle collision
            if os.path.exists(dest):
                dest = os.path.join(VAULT_DIR, f"anomaly_{abs(hash(obj))}_{obj}")
                
            shutil.move(obj_path, dest)
            print(f"   📦 BINGO! '{obj}' vaulted successfully. (+10 Detective Points)")
            score += 10
        else:
            print(f"   🛡️  Leaving '{obj}' exactly where it is. It might be load-bearing.")

    print("\n=====================================================================")
    print(f"🕵️‍♀️  SWEEP COMPLETE. FINAL SCORE (CHINDOGU LEVEL 7): {score} POINTS 🕵️‍♀️")
    print("=====================================================================\n")
