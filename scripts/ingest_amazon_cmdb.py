import xml.etree.ElementTree as ET
import sqlite3
import os
import uuid

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
XML_PATH = '/home/james/stacklabs/dna/dropzone/daily_29042026/cmdb_ci (sys_created_onONLast 6 months@javascript_gs.beginningOfLast6Months()@javascript_gs.endO.xml'

def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cmdb_ci_garden (
            sys_id TEXT PRIMARY KEY,
            model_id TEXT,
            plant_type TEXT,
            FOREIGN KEY (sys_id) REFERENCES cmdb_ci (sys_id)
        )
    ''')
    conn.commit()

def ingest():
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)
    cursor = conn.cursor()

    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    hw_keywords = ['pi ', 'raspberry', 'webcam', 'laptop', 'router', 'beelink', 'adapter', 'monitor', 'pcie', 'flash drive', 'nvm', 'hdmi', 'sensor', 'switch', 'hub']
    garden_keywords = ['grow', 'trellis', 'soil', 'seed', 'hydroponic', 'fertilizer', 'nutrient', 'tent', 'sponge', 'plant', 'clip', 'orchid']

    hw_count = 0
    garden_count = 0
    skipped_count = 0

    for item in root:
        sys_id_el = item.find('sys_id')
        name_el = item.find('name')
        short_desc_el = item.find('short_description')
        op_status_el = item.find('operational_status')
        
        sys_id = sys_id_el.text if sys_id_el is not None and sys_id_el.text else str(uuid.uuid4()).replace('-', '')
        name = name_el.text if name_el is not None and name_el.text else 'Unknown Item'
        short_desc = short_desc_el.text if short_desc_el is not None and short_desc_el.text else ''
        op_status = int(op_status_el.text) if op_status_el is not None and op_status_el.text else 1

        desc_lower = short_desc.lower()
        
        # We also might want to match name
        name_lower = name.lower()
        search_text = desc_lower + " " + name_lower

        is_hw = any(kw in search_text for kw in hw_keywords)
        is_garden = any(kw in search_text for kw in garden_keywords)

        if is_hw:
            sys_class_name = 'cmdb_ci_hardware'
            hw_count += 1
        elif is_garden:
            sys_class_name = 'cmdb_ci_garden'
            garden_count += 1
        else:
            # Check if it was already one of the explicitly imported mesh nodes
            if 'node' in search_text or 'pegasus' in search_text or 'hobbes' in search_text or 'calvin' in search_text or 'grogu' in search_text:
                 sys_class_name = 'cmdb_ci_hardware'
                 hw_count += 1
            else:
                 skipped_count += 1
                 continue
        
        # Check if sys_id already exists
        cursor.execute("SELECT sys_id FROM cmdb_ci WHERE sys_id = ?", (sys_id,))
        if cursor.fetchone():
            continue # Skip existing

        # Insert into cmdb_ci
        cursor.execute('''
            INSERT INTO cmdb_ci (sys_id, name, sys_class_name, short_description, operational_status)
            VALUES (?, ?, ?, ?, ?)
        ''', (sys_id, name, sys_class_name, short_desc, op_status))

        # Insert into specific table
        if sys_class_name == 'cmdb_ci_hardware':
            cursor.execute('''
                INSERT INTO cmdb_ci_hardware (sys_id, ip_address, mac_address, model_id)
                VALUES (?, ?, ?, ?)
            ''', (sys_id, None, None, short_desc[:100] if short_desc else 'Generic Hardware'))
        elif sys_class_name == 'cmdb_ci_garden':
            cursor.execute('''
                INSERT INTO cmdb_ci_garden (sys_id, model_id, plant_type)
                VALUES (?, ?, ?)
            ''', (sys_id, short_desc[:100] if short_desc else 'Generic Garden Equipment', None))

    conn.commit()
    conn.close()

    print(f"Ingestion complete.")
    print(f"Hardware items added: {hw_count}")
    print(f"Garden items added: {garden_count}")
    print(f"Items skipped: {skipped_count}")

if __name__ == '__main__':
    ingest()
