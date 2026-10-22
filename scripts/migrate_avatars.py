import os
import re
import sqlite3
import shutil

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
AVATARS_DIR = "/home/james/stacklabs/avatars"

def to_snake_case(name):
    # Remove extension
    base, ext = os.path.splitext(name)
    # Convert non-alphanumeric/spaces to underscores
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", base)
    # Convert to lowercase and strip leading/trailing underscores
    clean = clean.strip("_").lower()
    return f"{clean}{ext.lower()}"

def migrate():
    if not os.path.exists(AVATARS_DIR):
        print(f"Error: Avatars directory {AVATARS_DIR} does not exist.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Step 1: Query all avatar URLs from both tables
    cur.execute("SELECT sys_id, user_name, avatar_url FROM sys_user")
    sys_users = cur.fetchall()

    cur.execute("SELECT id, user_name, avatar_url FROM persona")
    personas = cur.fetchall()

    def process_url(avatar_url):
        if not avatar_url:
            return None
        
        # Clean URL to get relative path
        rel_path = avatar_url.lstrip("/")
        if not rel_path.startswith("avatars/"):
            # If it doesn't reference avatars, ignore or handle if needed
            return None

        # Exclude "avatars/" prefix
        sub_path = rel_path[len("avatars/"):]
        if not sub_path:
            return None

        # The file path on disk
        source_path = os.path.join(AVATARS_DIR, sub_path)
        if not os.path.exists(source_path):
            print(f"Warning: File does not exist at {source_path}")
            return None

        # If it's a file inside a subdirectory, we need to flatten it
        parts = [p for p in sub_path.split("/") if p]
        if len(parts) > 1:
            # Create a flattened snake_case name
            # e.g., decision_derby/front_neutral.png -> decision_derby_front_neutral.png
            flat_name_parts = []
            for part in parts:
                base, ext = os.path.splitext(part)
                # Clean each part
                clean_part = re.sub(r"[^a-zA-Z0-9]+", "_", base)
                flat_name_parts.append(clean_part)
            
            # Reassemble with extension from the last part
            _, final_ext = os.path.splitext(parts[-1])
            new_filename = "_".join(flat_name_parts).strip("_").lower() + final_ext.lower()
        else:
            # It's already at the root of avatars/, just ensure snake_case filename
            new_filename = to_snake_case(parts[0])

        target_path = os.path.join(AVATARS_DIR, new_filename)
        new_url = f"/avatars/{new_filename}"

        if source_path != target_path:
            print(f"Moving: {source_path} -> {target_path}")
            # Ensure target parent exists (AVATARS_DIR does)
            shutil.copy2(source_path, target_path)
            # Delete the source file so we flatten it
            try:
                os.remove(source_path)
            except Exception as e:
                print(f"Failed to delete source {source_path}: {e}")
        
        return new_url

    # Step 2: Update sys_user records
    for uid, username, url in sys_users:
        if not url:
            continue
        new_url = process_url(url)
        if new_url and new_url != url:
            print(f"Updating sys_user '{username}' avatar: {url} -> {new_url}")
            cur.execute("UPDATE sys_user SET avatar_url = ? WHERE sys_id = ?", (new_url, uid))

    # Step 3: Update persona records
    for pid, username, url in personas:
        if not url:
            continue
        new_url = process_url(url)
        if new_url and new_url != url:
            print(f"Updating persona '{username}' avatar: {url} -> {new_url}")
            cur.execute("UPDATE persona SET avatar_url = ? WHERE id = ?", (new_url, pid))

    conn.commit()
    conn.close()
    print("Database updates committed.")

    # Step 4: Clean up empty directories in avatars/
    for root, dirs, files in os.walk(AVATARS_DIR, topdown=False):
        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                if not os.listdir(dir_path):
                    print(f"Removing empty directory: {dir_path}")
                    os.rmdir(dir_path)
            except Exception as e:
                print(f"Failed to remove directory {dir_path}: {e}")

if __name__ == "__main__":
    migrate()
