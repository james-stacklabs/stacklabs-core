import sqlite3

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

AVATAR_MAPPINGS = {
    'UncleStevieStan': '/public/avatars/uncle_stevie_stan.png',
    'keith_fanboy': '/public/avatars/keith_fanboy/keith_fanboy_avatar.png',
    '7_train_terry': '/public/avatars/7_train_terry.png',
    'barf': '/public/avatars/barf.png',
    'dr_terp': '/public/avatars/dr_terp/dr_terp_avatar.png',
    'compliance_karen': '/public/avatars/compliance_karen/compliance_karen_avatar.png',
    'ed_haskins': '/public/avatars/ed_haskins/ed_haskins_avatar.png',
    'lupita_community': '/public/avatars/lupita_community.png',
    'Friar_Frank': '/public/avatars/Friar_Frank.png',
    'Petco_Paul': '/public/avatars/Petco_Paul.png',
    'Tacos_N_Tatis': '/public/avatars/Tacos_N_Tatis.png',
    'Slam_Diego_Surfer': '/public/avatars/Slam_Diego_Surfer.png',
    'Gwynn_Ghost': '/public/avatars/Gwynn_Ghost.png',
    'spin_rate_sylvia': '/public/avatars/spin_rate_sylvia.png',
    'Altitude_Sickness': '/public/avatars/Altitude_Sickness.png',
    'Rock_Pile_Randy': '/public/avatars/Rock_Pile_Randy.png'
}

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("🩹 Starting database avatar URL healing...")
    
    for username, avatar_url in AVATAR_MAPPINGS.items():
        # Update persona table (case insensitive username check)
        cur.execute(
            "UPDATE persona SET avatar_url = ? WHERE user_name = ? COLLATE NOCASE",
            (avatar_url, username)
        )
        persona_updated = cur.rowcount
        
        # Update sys_user table (case insensitive username check)
        cur.execute(
            "UPDATE sys_user SET avatar_url = ? WHERE user_name = ? COLLATE NOCASE",
            (avatar_url, username)
        )
        sys_user_updated = cur.rowcount
        
        print(f"  👤 {username}: avatar_url set to '{avatar_url}' (Updated persona: {persona_updated}, sys_user: {sys_user_updated})")
        
    conn.commit()
    conn.close()
    print("✅ Database avatar URL healing completed successfully!")

if __name__ == '__main__':
    main()
