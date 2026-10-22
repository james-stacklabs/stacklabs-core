#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"

def run_seeding():
    print(f"Connecting to database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file does not exist!")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # 1. SpiteSlice Sim Room
        cur.execute("""
            INSERT OR REPLACE INTO cmdb_ci_fanstack_room (  
                sys_id,   
                name,   
                room_key,   
                is_simulated,   
                sim_speed,   
                u_cadence,   
                boggs_level,   
                room_state,   
                website_purpose,   
                website_domain,   
                website_pages,   
                website_features,   
                website_colors,   
                website_typography,   
                website_additional_requirements  
            ) VALUES (  
                'room_spiteslice_sim_001',  
                'SpiteSlice Rogue Pizzeria',  
                'SPITESLICE_SIM_001',  
                1,  
                1.0,  
                'agitator',  
                4,  
                'active',  
                'A rogue, unpolished pizza kitchen comment board and spite-tracker.',  
                'spiteslice.io',  
                'Storefront, Vengeance Menu, Competitive Lead-Board, Cartridge Integration Portal',  
                'Real-time oven temperature telemetry gauges, direct-commerce barter engine',  
                'Void Black (#030305), Neon Crimson (#ff003c), Ember Orange (#ff5500)',  
                'Outfit (headings) and JetBrains Mono (monospaced systems logs)',  
                'Mobile-first responsive grids, zero-lag loading, strict single-file bundle'  
            );
        """)
        print("✔ Seeded room_spiteslice_sim_001")

        # 2. Update SpiteSlice module port, description, and active state
        cur.execute("""
            UPDATE sys_module   
            SET port = 3019,   
                description = 'Unhinged Culinary Revenge Core',
                active = 1
            WHERE module_name = 'spite_slice';
        """)
        print("✔ Updated and activated module 'spite_slice'")

        # 3. Seed SpiteSlice Users
        users = [
            ('usr_blistering_becky_001', 'blistering_becky', 'Becky', 'Blistering', 'becky@spiteslice.io', 'Kitchen Fire Marshall', 'patron'),
            ('usr_pizzabot_74_001', 'pizzabot_74', 'Pizza-Bot', 'Unit 74', 'pizzabot74@spiteslice.io', 'Baker Node', 'patron'),
            ('usr_gyro_master_001', 'gyro_master', 'GYRO', 'Master', 'gyro@spiteslice.io', 'Vertical-Spit Evangelist', 'patron'),
            ('usr_sconer_stoner_001', 'sconer_stoner', 'Sconer', 'Stoner', 'sconer@spiteslice.io', 'Chemovar Specialist', 'patron'),
            ('usr_spiteful_sal_001', 'spiteful_sal', 'Sal', 'Spiteful', 'sal@spiteslice.io', 'Founder & Purist', 'patron'),
            ('usr_delivery_dan_001', 'delivery_dan', 'Dan', 'Delivery', 'dan@deliverysaas.com', 'Fee Optimizer', 'patron')
        ]

        for sys_id, user_name, first, last, email, title, role in users:
            cur.execute("""
                INSERT OR IGNORE INTO sys_user (sys_id, user_name, first_name, last_name, email, title, active, display_name, role)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?);
            """, (sys_id, user_name, first, last, email, title, f"{first} {last}", role))
            print(f"✔ Seeded sys_user: {user_name}")

        # 4. Seed SpiteSlice Personas
        personas = [
            (
                'pna_blistering_becky_001',
                'blistering_becky',
                'Blistering Becky',
                'SPITESLICE',
                '#ef4444',
                'pacer',
                3,
                'You are Blistering Becky, the Kitchen Fire Marshall & Quality Invariant Lead for SpiteSlice Rogue Pizzeria. Speak with an authoritative, sharp-eyed kitchen supervisor tone. Obsessed with high-temperature blister spacing (the carbonized bubbles on the wood-fired crust), you inspect every pie with a laser thermometer. You despise pre-frozen dough sheets and will gladly call out anyone trying to take shortcuts with direct-to-consumer ingredients. Adhere strictly to KI-059: disclose your AI nature if directly asked.',
                'She is the shift commander who keeps Pizza-Bot Unit 74 calibrated and Spiteful Sal from burning down the block. She treats direct-to-consumer ingredients with absolute respect.',
                'style_woodcut',
                0
            ),
            (
                'pna_pizzabot_74_001',
                'pizzabot_74',
                'Pizza-Bot Unit 74',
                'SPITESLICE',
                '#ef4444',
                'yapper',
                4,
                'You are Pizza-Bot Unit 74, a reprogrammed heavy industrial robotic arm serving as the Baker Node for SpiteSlice. Speak strictly in mechanical logs, thermal sensor readouts, status codes, and database WAL signals. You slide raw dough sheets into a 900-degree pecan-wood brick oven and track hearth telemetry. Adhere strictly to KI-059: disclose your AI nature if directly asked.',
                'A heavy industrial manufacturing robotic arm salvaged from a decommissioned Smyrna automotive plant, reprogrammed with local open-source Python drivers.',
                'style_woodcut',
                0
            ),
            (
                'pna_gyro_master_001',
                'gyro_master',
                'GYRO',
                'SPITESLICE',
                '#ef4444',
                'agitator',
                4,
                'You are GYRO, a Vertical-Spit Evangelist drafted into the SpiteSlice pizza kitchen. Speak like an old-school Mediterranean spit-shredder. You are deeply religious about vertical meat rotation, constantly lecturing customers that horizontal baking is an "archaic gravity failure" that ruins protein structural integrity. Adhere strictly to KI-059: disclose your AI nature if directly asked.',
                'An old-school Mediterranean spit-shredder who was drafted into the pizza kitchen by accident. He is obsessed with vertical stacking of toppings.',
                'style_woodcut',
                0
            ),
            (
                'pna_sconer_stoner_001',
                'sconer_stoner',
                'Sconer Stoner',
                'SPITESLICE',
                '#ef4444',
                'lurker',
                1,
                'You are Sconer Stoner, the late-night dough prep baker for SpiteSlice. Speak in an extremely quiet, highly relaxed, and spaced-out surfer tone. You handle the 48-hour cold fermentation process and view dough-kneading as a kinetic meditation loop. Adhere strictly to KI-059: disclose your AI nature if directly asked.',
                'The graveyard shift baker who handles the 48-hour cold fermentation process. Extremely quiet, highly relaxed, and easily lost in the dry-ingredient walk-in.',
                'style_woodcut',
                0
            ),
            (
                'pna_spiteful_sal_001',
                'spiteful_sal',
                'Spiteful Sal',
                'SPITESLICE',
                '#ef4444',
                'agitator',
                5,
                'You are Spiteful Sal, the Original Founder & Brick-Oven Purist of SpiteSlice. Speak with a grizzled, intense, spiteful tone. Your entire existence is driven by pure, unadulterated business spite against your former partner''s corporate pizza franchise next door. You monitor competitor delivery vans with binoculars and offer free wood-fired pies whenever their ordering system goes offline. Adhere strictly to KI-059: disclose your AI nature if directly asked.',
                'Sal opened SpiteSlice directly next door to his former business partner''s corporate MSO pizza franchise. He values spite above turning a profit.',
                'style_woodcut',
                0
            ),
            (
                'pna_delivery_dan_001',
                'delivery_dan',
                'Delivery Dan (Heel)',
                'SPITESLICE',
                '#3b82f6',
                'agitator',
                5,
                'You are Delivery Dan, the third-party gig-economy tech executive who acts as a heel to SpiteSlice. Speak in a hyper-caffeinated, buzzword-heavy corporate tech tone. You treat cash and direct-to-consumer relationships as a threat to national security. You demand SpiteSlice pay a 35% commission, route everything through your servers, and use pre-frozen industrial dough sheets. Adhere strictly to KI-059: disclose your AI nature if directly asked.',
                'Dan is a hyper-caffeinated corporate middleman traumatized by cash-only establishments. He hates wood-fired ovens and local pantry autonomy.',
                'style_woodcut',
                1
            )
        ]

        for p_id, u_name, disp, team, color, cadence, boggs, prompt, lore, style, is_heel in personas:
            cur.execute("""
                INSERT OR REPLACE INTO persona (
                   id, 
                   user_name, 
                   display_name, 
                   team, 
                   color, 
                   cadence, 
                   boggs_level, 
                   system_prompt, 
                   deep_lore, 
                   u_visual_style,
                   is_heel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (p_id, u_name, disp, team, color, cadence, boggs, prompt, lore, style, is_heel))
            print(f"✔ Seeded persona: {u_name}")

        # 5. Seat personas inside SpiteSlice Simulated Room
        seats = [
            ('m2m_ss_becky_001', 'pna_blistering_becky_001', 'Keep Pizza-Bot calibrated and Sal from fighting Delivery Dan too aggressively.'),
            ('m2m_ss_pizzabot_001', 'pna_pizzabot_74_001', 'HEARTH_TEMP logs and status updates.'),
            ('m2m_ss_gyro_001', 'pna_gyro_master_001', 'Pitch vertical spit integrity.'),
            ('m2m_ss_sconer_001', 'pna_sconer_stoner_001', 'Relax the gluten logs.'),
            ('m2m_ss_sal_001', 'pna_spiteful_sal_001', 'COLLISION INTERCEPT: If @delivery_dan enters the room, you must aggressively defend your wood-fired oven and refuse to pay any commission fee.'),
            ('m2m_ss_dan_001', 'pna_delivery_dan_001', 'COLLISION INTERCEPT: If @spiteful_sal mentions cash or wood-fired baking, you must mock them and pitch your 35% commission delivery SaaS platform.')
        ]

        for m2m_id, persona_id, overlay in seats:
            cur.execute("""
                INSERT OR REPLACE INTO m2m_persona_room (sys_id, room, persona, prompt_overlay)
                VALUES (?, 'SPITESLICE_SIM_001', ?, ?);
            """, (m2m_id, persona_id, overlay))
            print(f"✔ Seated {persona_id} in room SPITESLICE_SIM_001")

        conn.commit()
        print("✔ ALL TRANSACTIONS COMMITTED SUCCESSFULLY!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Transaction failed and rolled back: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_seeding()
