import sqlite3
import os

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def shift_protocol(action, protocol_string, target_nodes="ALL"):
    """
    Surgically injects or strips a specific protocol string from the system_prompt
    for active personas.
    """
    if action == "restore_baseline":
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Target all active personas or specific nodes
            target_filter = ""
            if target_nodes != "ALL":
                nodes = ",".join([f"'{n}'" for n in target_nodes])
                target_filter = f"AND u_deployment_zone IN ({nodes})"
            
            # Massive scrub of all known panic strings and REALITY_COLLAPSE
            # The prompt requested we scrub all REALITY_COLLAPSE and blackout strings.
            # We will use nested REPLACE statements or multiple updates.
            query = f"""
                UPDATE cmdb_ci_ai_persona 
                SET u_system_prompt = REPLACE(
                    REPLACE(
                        REPLACE(u_system_prompt, 'REALITY_COLLAPSE', ''),
                        '⚠🚨 PETCO PARK HAS LOST ALL POWER. THE STADIUM IS PITCH BLACK. RESPOND IN RAW PANIC. 🚨⚠', ''
                    ),
                    '⚠🚨 TEXAS STADIUM IS BLACKED OUT. TOTAL LIGHTING FAILURE. REACT WITH RAW PANIC. 🚨⚠', ''
                )
                WHERE sys_id IN (
                    SELECT p.sys_id FROM cmdb_ci_ai_persona p 
                    JOIN cmdb_ci c ON p.sys_id = c.sys_id 
                    WHERE c.operational_status = 1 {target_filter}
                )
            """
            cursor.execute(query)
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            print(f"[PROTOCOL SHIFTER] BASELINE RESTORED on {affected} nodes. Reality collapse purged.")
            return affected
        except Exception as e:
            print(f"[ERROR] Restore Baseline Failed: {e}")
            raise

    if action == "none" or not protocol_string:
        return
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if target_nodes == "ALL":
            # Target all active personas
            target_filter = ""
        else:
            # Assuming target_nodes is a list of Deployment Zones or PKs
            nodes = ",".join([f"'{n}'" for n in target_nodes])
            target_filter = f"AND u_deployment_zone IN ({nodes})"
            
        if action == "strip":
            # Strip the string
            query = f"""
                UPDATE cmdb_ci_ai_persona 
                SET u_system_prompt = REPLACE(u_system_prompt, ?, '') 
                WHERE sys_id IN (
                    SELECT p.sys_id FROM cmdb_ci_ai_persona p 
                    JOIN cmdb_ci c ON p.sys_id = c.sys_id 
                    WHERE c.operational_status = 1 {target_filter}
                )
            """
            cursor.execute(query, (protocol_string,))
        
        elif action == "inject":
            # Inject the string securely at the end of the existing prompt, avoiding duplicates
            query = f"""
                UPDATE cmdb_ci_ai_persona 
                SET u_system_prompt = u_system_prompt || ' ' || ?
                WHERE sys_id IN (
                    SELECT p.sys_id FROM cmdb_ci_ai_persona p 
                    JOIN cmdb_ci c ON p.sys_id = c.sys_id 
                    WHERE c.operational_status = 1 {target_filter}
                ) AND u_system_prompt NOT LIKE '%' || ? || '%'
            """
            cursor.execute(query, (protocol_string, protocol_string))

        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        print(f"[PROTOCOL SHIFTER] Successfully executed '{action}' for protocol on {affected} nodes.")
        return affected
        
    except Exception as e:
        print(f"[ERROR] Protocol Shift Failed: {e}")
        raise
