import os
import sqlite3
import base64
import shutil

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
AVATARS_DIR = "/home/james/stacklabs/avatars"

# Map of (user_name, source_path, target_filename)
mappings = [
    ("2008_ghost", "/home/james/stacklabs/17_GonzasCantina/dist/avatars/2008_ghost.jpg", "2008_ghost.jpg"),
    ("pizzabot_74", "/home/james/stacklabs/archive_quarantine_eon1/pizzabot_74/pizzabot_74_avatar.png", "pizzabot_74.png"),
    ("spiteful_sal", "/home/james/stacklabs/archive_quarantine_eon1/spiteful_sal/spiteful_sal_avatar.png", "spiteful_sal.png"),
    ("keith_fanboy", "/home/james/stacklabs/media_vault/03_Assets/keith_fanboy_avatar.png", "keith_fanboy.png"),
    ("catnip_greta", "/home/james/stacklabs/23_EileenStack/dist/avatars/catnip_greta/catnip_greta_avatar.png", "catnip_greta.png"),
    ("compliance_karen", "/home/james/stacklabs/17_GonzasCantina/dist/avatars/compliance_karen/compliance_karen_avatar.png", "compliance_karen.png"),
    ("420_linda", "/home/james/stacklabs/media_vault/01_Assets/WeedStack_Injection/420_linda_portrait_1780120898981.png", "420_linda.png"),
    ("7_train_terry", "/home/james/stacklabs/17_GonzasCantina/dist/avatars/7_train_terry.png", "7_train_terry.png"),
    ("battery_chucker", "/home/james/stacklabs/media_vault/03_Assets/battery_chucker_avatar.png", "battery_chucker.png"),
    ("phanatic", "/home/james/stacklabs/17_GonzasCantina/dist/avatars/phanatic.jpg", "phanatic.jpg"),
    ("gary_bot", "/home/james/.gemini/antigravity/brain/bb6cf228-51bd-46cd-98c7-bfa91aef3507/gary_bot_1784403673241.png", "gary_bot.png"),
    ("ron_bot", "/home/james/.gemini/antigravity/brain/bb6cf228-51bd-46cd-98c7-bfa91aef3507/ron_bot_1784403683120.png", "ron_bot.png")
]

def run_enrichment():
    os.makedirs(AVATARS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for user_name, src, target_name in mappings:
        if not os.path.exists(src):
            print(f"⚠️ Source file not found: {src}")
            continue
        
        dest = os.path.join(AVATARS_DIR, target_name)
        shutil.copy2(src, dest)
        print(f"Copied {src} -> {dest}")

        # Read and convert to base64
        with open(dest, "rb") as f:
            b64_content = base64.b64encode(f.read()).decode("utf-8")
        
        # Check if the row exists
        cursor.execute("SELECT id FROM persona WHERE user_name = ?", (user_name,))
        row = cursor.fetchone()
        if row:
            avatar_url = f"/api/persona_image/{user_name}"
            cursor.execute(
                "UPDATE persona SET avatar_blob = ?, avatar_url = ? WHERE user_name = ?",
                (b64_content, avatar_url, user_name)
            )
            print(f"Updated persona '{user_name}' DB row (url={avatar_url}, blob size={len(b64_content)} chars)")
        else:
            print(f"⚠️ Persona '{user_name}' not found in DB table 'persona'")

    # Explicitly update 'barf' url
    cursor.execute("SELECT avatar_blob FROM persona WHERE user_name = 'barf'")
    barf_row = cursor.fetchone()
    if barf_row:
        cursor.execute(
            "UPDATE persona SET avatar_url = ? WHERE user_name = 'barf'",
            ("/api/persona_image/barf",)
        )
        print("Updated barf's avatar_url in DB.")
        # If barf has a blob, copy its content to filesystem as fallback too
        if barf_row[0]:
            try:
                b64_data = barf_row[0]
                if b64_data.startswith('data:'):
                    b64_data = b64_data.split(',', 1)[1]
                img_data = base64.b64decode(b64_data)
                with open(os.path.join(AVATARS_DIR, "barf.png"), "wb") as f:
                    f.write(img_data)
                print("Extracted and saved barf.png to avatars dir.")
            except Exception as e:
                print(f"Error saving barf.png: {e}")

    conn.commit()
    conn.close()
    print("🟢 Enrichment complete!")

if __name__ == "__main__":
    run_enrichment()
