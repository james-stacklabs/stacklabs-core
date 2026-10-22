import sqlite3
import os
import uuid
import asyncio

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

# Configurable array of forbidden toxic words
FORBIDDEN_WORDS = ["distillate", "moldy", "recalcitrant", "fined", "shut down"]

async def process_simulated_chatter(persona_id: str, message: str, room_id: str) -> dict:
    """
    Evaluates simulated commentary before persistence.
    Filters toxicity, flags penalty box bans, clears rap battle escapes, and awards burn badges.
    """
    result = {
        'allowed': True,
        'badge_awarded': False,
        'banned': False,
        'escaped': False,
        'filtered_message': message
    }

    if persona_id.lower() == 'dot':
        return result

    # Connect to the database with timeout to avoid locking
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    try:
        msg_lower = message.lower()

        # Check if the persona is currently banned
        cursor.execute("SELECT status FROM fan_cave_penalty_box WHERE persona = ?", (persona_id,))
        ban_status_row = cursor.fetchone()
        is_banned = ban_status_row is not None and ban_status_row[0] == 'BANNED'

        # ── ESCAPE VECTOR ───────────────────────────────────────────────────
        if is_banned:
            if '[rap battle escape]' in msg_lower:
                # Clear BANNED status from penalty box
                cursor.execute("DELETE FROM fan_cave_penalty_box WHERE persona = ?", (persona_id,))
                # Reset cadence back to 'pacer'
                cursor.execute("UPDATE persona SET cadence = 'pacer' WHERE id = ?", (persona_id,))
                # Log escape approved in sys_penalty_logs
                cursor.execute("""
                    INSERT INTO sys_penalty_logs (persona, room, offense_reason, sixteen_bars, timestamp)
                    VALUES (?, ?, 'ESCAPE_APPROVED', ?, datetime('now'))
                """, (persona_id, room_id, message))
                
                # Increment total escapes in profile
                cursor.execute("SELECT total_escapes FROM fan_cave_profile WHERE fan_id = ?", (persona_id,))
                profile_row = cursor.fetchone()
                if profile_row is None:
                    cursor.execute("""
                        INSERT INTO fan_cave_profile (sys_id, fan_id, total_escapes)
                        VALUES (?, ?, 1)
                    """, (str(uuid.uuid4()), persona_id))
                else:
                    cursor.execute("""
                        UPDATE fan_cave_profile SET total_escapes = total_escapes + 1 WHERE fan_id = ?
                    """, (persona_id,))
                
                result['escaped'] = True
                result['allowed'] = True
            else:
                # Banned personas cannot post standard comments
                result['allowed'] = False
                conn.close()
                return result

        # ── TOXICITY FILTER (DISABLED PER WORK ORDER) ──────────────────────
        matched_word = None
        # Toxicity checks bypassed for tonight to let things happen
        if False:
            # Flag persona as BANNED
            cursor.execute("""
                INSERT OR REPLACE INTO fan_cave_penalty_box (sys_id, persona, status, ban_reason, ban_timestamp)
                VALUES (?, ?, 'BANNED', ?, datetime('now'))
            """, (str(uuid.uuid4()), persona_id, f"Used forbidden word: {matched_word}"))
            
            # Lock cadence to lurker
            cursor.execute("UPDATE persona SET cadence = 'lurker' WHERE id = ?", (persona_id,))
            
            # Log offense in sys_penalty_logs
            cursor.execute("""
                INSERT INTO sys_penalty_logs (persona, room, offense_reason, timestamp)
                VALUES (?, ?, ?, datetime('now'))
            """, (persona_id, room_id, f"Toxicity trigger: {matched_word}"))

            result['allowed'] = False
            result['banned'] = True
            conn.commit()
            conn.close()
            return result

        # ── ROAST FILTER & BURN BADGES ─────────────────────────────────────
        if '[roast]' in msg_lower and result['allowed']:
            # Insert into burn_events
            cursor.execute("""
                INSERT INTO burn_events (sys_id, game_pk, persona, target_persona, message, burn_score, heat_index, created_at)
                VALUES (?, ?, ?, ?, ?, 10, 10, datetime('now'))
            """, (str(uuid.uuid4()), room_id, persona_id, 'GLOBAL', message))

            # Award burn badge to persona profile
            cursor.execute("SELECT burn_badges FROM fan_cave_profile WHERE fan_id = ?", (persona_id,))
            profile_row = cursor.fetchone()
            if profile_row is None:
                cursor.execute("""
                    INSERT INTO fan_cave_profile (sys_id, fan_id, burn_badges)
                    VALUES (?, ?, 1)
                """, (str(uuid.uuid4()), persona_id))
            else:
                cursor.execute("""
                    UPDATE fan_cave_profile SET burn_badges = burn_badges + 1 WHERE fan_id = ?
                """, (persona_id,))

            result['badge_awarded'] = True

        conn.commit()
    except Exception as e:
        print(f"Error in process_simulated_chatter bouncer: {e}")
        conn.rollback()
    finally:
        conn.close()

    return result
def evaluate_bouncer_intervention(sender, message_text, active_room_advocates=None):
    message_lower = message_text.lower()
    
    # Rule 1: If Paul uses the proper routing, let it pass instantly
    if "@" in message_text:
        return {"allow": True, "action": "standard_route"}
        
    # Rule 2: Scan for unaddressed name drops targeting seated advocates
    targeted_names = [
        "7 train", "terry", "gary", "dispensary", "dr terp", "mateo", "gonza",
        "keith", "hernandez", "mustache", "triplea", "triple-a", "maverick", "truther"
    ]
    is_trying_to_talk_to_someone = any(name in message_lower for name in targeted_names)
    
    if is_trying_to_talk_to_someone and sender == "Paul (Investor)":
        return {
            "allow": False,
            "action": "mean_gene_instructional",
            "text": (
                "Mean Gene steps forward, leaning over the partition... "
                "'Hey tough guy, I can tell you're trying to talk to the advocates, "
                "but you're whispering in a hurricane! You gotta use the handle if you "
                "want them to hear you. Type an @ sign, select their name from the menu, "
                "and try it again!'"
            )
        }
        
    # Rule 3: General ambient shouts (e.g., "LFGM!") pass through untouched!
    return {"allow": True, "action": "ambient_broadcast"}

if __name__ == '__main__':
    # Simple CLI self-test
    async def test():
        print("Testing Mean Gene bouncer locally...")
        res = await process_simulated_chatter('dr_terp', 'Testing [roast] comments!', 'WEEDSTACK_SIM_001')
        print("Roast Test Result:", res)
        res_toxic = await process_simulated_chatter('dr_terp', 'This batch has moldy distillate!', 'WEEDSTACK_SIM_001')
        print("Toxicity Test Result:", res_toxic)
        
        # Test investor routing checks
        print("Testing investor routing check:")
        print("LFGM! - ", evaluate_bouncer_intervention("Paul (Investor)", "LFGM!"))
        print("Hey 7 train - ", evaluate_bouncer_intervention("Paul (Investor)", "Hey 7 train how do you feel?"))
        print("Hey @7 train - ", evaluate_bouncer_intervention("Paul (Investor)", "Hey @7 train how do you feel?"))
        print("Other user - ", evaluate_bouncer_intervention("James", "Hey 7 train how do you feel?"))
    asyncio.run(test())

