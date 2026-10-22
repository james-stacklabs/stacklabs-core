#!/usr/bin/env python3
# =============================================================================
# Water-Barrel Wayne Schema Migration & Seeding Script
# =============================================================================
# Deploys prepper_barter_only and barter_inventory arrays directly to DB.
# =============================================================================

import os
import sqlite3
import json
import uuid
import base64

DATABASES = [
    "/home/james/stacklabs/dna/sovereign_now.db",
    "/home/james/stacklabs-uat/dna/sovereign_now.db"
]

WAYNE_AVATAR_PATH = "/home/james/stacklabs/15_FanStack/public/avatars/water_barrel_wayne/water_barrel_wayne_avatar.png"

def migrate_and_seed(db_path):
    if not os.path.exists(db_path):
        print(f"⚠️ Database not found at: {db_path}")
        return
        
    print(f"🌱 Migrating and Seeding database: {db_path}...")
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    # 1. Add schema columns if they don't exist
    cursor.execute("PRAGMA table_info(persona);")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "prepper_barter_only" not in columns:
        print("  ➕ Adding column 'prepper_barter_only' to persona table...")
        cursor.execute("ALTER TABLE persona ADD COLUMN prepper_barter_only INTEGER DEFAULT 0;")
        
    if "barter_inventory" not in columns:
        print("  ➕ Adding column 'barter_inventory' to persona table...")
        cursor.execute("ALTER TABLE persona ADD COLUMN barter_inventory TEXT;")
        
    con.commit()
    
    # 2. Seed Water-Barrel Wayne
    user_name = "water_barrel_wayne"
    display_name = "Water-Barrel Wayne"
    team = "ANVILANDTWINE"
    deep_lore = (
        "A hard-nosed Smyrna prepper who hoards over 550 gallons of pressurized potable water in heavy-duty "
        "blue plastic barrels. He refuses to touch fiat cash and insists entirely on raw barter trading for his survival supplies."
    )
    system_prompt = (
        "You are Water-Barrel Wayne, a staunch local prepper from Smyrna, GA. You have 550 gallons of pressurized "
        "drinking water stored in heavy-duty barrels across your property. You absolutely despise fiat money and central banks. "
        "You only trade via raw barter, exchanging gallons of potable water for brass pipe fittings, copper scrap, or premium beef jerky. "
        "You speak in a gruff, direct, no-nonsense 90s cardboard treehouse tone."
    )
    cadence = "agitator"
    boggs_level = 3
    color = "#f59e0b"
    prepper_barter_only = 1
    
    inventory_data = [
        {"item": "Potable Water Gallons", "qty": 550, "value": "1 Gal = 2 AA Batteries / 0.5 lbs Copper"},
        {"item": "Blue Plastic Barrels", "qty": 10, "value": "1 Barrel = 12 Brass Fittings"},
        {"item": "Premium Beef Jerky Packs", "qty": 45, "value": "1 Pack = 1 Brass Fitting"},
        {"item": "Copper Pipe Segments (10ft)", "qty": 12, "value": "1 Pipe = 15 Gal Water"}
    ]
    barter_inventory = json.dumps(inventory_data)
    avatar_url = f"/avatars/{user_name}/{user_name}_avatar.png"
    
    # Generate inline SVG water barrel for base64 encoding to have an instantly premium default avatar!
    svg_data = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect width="100" height="100" fill="#0f172a"/>
        <ellipse cx="50" cy="25" rx="30" ry="10" fill="#3b82f6" stroke="#2563eb" stroke-width="4"/>
        <path d="M20,25 C20,25 20,85 50,85 C80,85 80,25 80,25" fill="#1d4ed8" stroke="#2563eb" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="50" cy="85" rx="30" ry="10" fill="#1e40af" stroke="#2563eb" stroke-width="2"/>
        <line x1="20" y1="45" x2="80" y2="45" stroke="#3b82f6" stroke-width="3" stroke-dasharray="2,2"/>
        <line x1="20" y1="65" x2="80" y2="65" stroke="#3b82f6" stroke-width="3" stroke-dasharray="2,2"/>
        <text x="50" y="58" font-family="monospace" font-size="8" fill="#93c5fd" text-anchor="middle" font-weight="bold">H2O</text>
        <text x="50" y="68" font-family="monospace" font-size="6" fill="#60a5fa" text-anchor="middle">550 GAL</text>
    </svg>"""
    avatar_blob = f"data:image/svg+xml;base64,{base64.b64encode(svg_data.encode()).decode()}"
    
    cursor.execute("SELECT id FROM persona WHERE user_name=?", (user_name,))
    row = cursor.fetchone()
    
    if row:
        print("  🔄 Updating existing persona record for @water_barrel_wayne...")
        cursor.execute("""
            UPDATE persona
            SET display_name=?, team=?, deep_lore=?, system_prompt=?, cadence=?, boggs_level=?, color=?,
                prepper_barter_only=?, barter_inventory=?, avatar_url=?, avatar_blob=?, updated_at=datetime('now')
            WHERE user_name=?
        """, (
            display_name, team, deep_lore, system_prompt, cadence, boggs_level, color,
            prepper_barter_only, barter_inventory, avatar_url, avatar_blob, user_name
        ))
    else:
        print("  🌱 Seeding new persona record for @water_barrel_wayne...")
        sys_id = uuid.uuid4().hex
        cursor.execute("""
            INSERT INTO persona (
                id, user_name, display_name, team, deep_lore, system_prompt, cadence, boggs_level, color,
                prepper_barter_only, barter_inventory, avatar_url, avatar_blob, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            sys_id, user_name, display_name, team, deep_lore, system_prompt, cadence, boggs_level, color,
            prepper_barter_only, barter_inventory, avatar_url, avatar_blob
        ))
        
    con.commit()
    con.close()
    print("  ✅ Seed complete.")

def main():
    for db in DATABASES:
        migrate_and_seed(db)
    
    # Save the elegant SVG as a physical PNG fallback to maintain premium visual design!
    os.makedirs(os.path.dirname(WAYNE_AVATAR_PATH), exist_ok=True)
    # Also save to public portals
    dest_paths = [
        WAYNE_AVATAR_PATH,
        "/home/james/stacklabs/01_Sovereign_Portal/public/avatars/water_barrel_wayne/water_barrel_wayne_avatar.png",
        "/home/james/stacklabs-uat/01_Sovereign_Portal/public/avatars/water_barrel_wayne/water_barrel_wayne_avatar.png"
    ]
    
    for path in dest_paths:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # Create a simple SVG visual copy
            svg_path = path.replace(".png", ".svg")
            with open(svg_path, "w") as f:
                f.write("""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect width="100" height="100" fill="#0f172a" rx="15"/>
        <ellipse cx="50" cy="25" rx="30" ry="10" fill="#3b82f6" stroke="#2563eb" stroke-width="4"/>
        <path d="M20,25 C20,25 20,85 50,85 C80,85 80,25 80,25" fill="#1d4ed8" stroke="#2563eb" stroke-width="4" stroke-linecap="round"/>
        <ellipse cx="50" cy="85" rx="30" ry="10" fill="#1e40af" stroke="#2563eb" stroke-width="2"/>
        <line x1="20" y1="45" x2="80" y2="45" stroke="#3b82f6" stroke-width="3" stroke-dasharray="2,2"/>
        <line x1="20" y1="65" x2="80" y2="65" stroke="#3b82f6" stroke-width="3" stroke-dasharray="2,2"/>
        <text x="50" y="58" font-family="monospace" font-size="8" fill="#93c5fd" text-anchor="middle" font-weight="bold">H2O</text>
        <text x="50" y="68" font-family="monospace" font-size="6" fill="#60a5fa" text-anchor="middle">550 GAL</text>
    </svg>""")
            # Also copy to png for fallback loader
            shutil.copy(svg_path, path)
        except Exception:
            pass

if __name__ == "__main__":
    main()
