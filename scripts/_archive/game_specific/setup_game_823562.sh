#!/usr/bin/env bash
# =============================================================================
# FanStack Game Setup: NYM @ LAD — GAME_PK 823562
# Generated: 2026-04-14
# =============================================================================

set -e

SCRIPT_PATH="/home/james/stacklabs/PROD/scripts/fanstack_chatbots.py"
DB_PATH="/home/james/stacklabs/sovereign_now.db"
RELAY_LOG="/tmp/relay.log"
GAME_PK="823562"

echo "=============================================="
echo " FanStack Setup — NYM @ LAD — Game $GAME_PK"
echo "=============================================="

# ------------------------------------------------------------------------------
# STEP 1: Kill existing fanstack_chatbots.py to release DB locks
# ------------------------------------------------------------------------------
echo ""
echo "[1/3] Killing existing fanstack_chatbots.py processes..."
pkill -f "fanstack_chatbots.py" && echo "     ✓ Process killed." || echo "     ℹ No running process found (clean slate)."
sleep 1

# ------------------------------------------------------------------------------
# STEP 2: Activate all 9 personas in cmdb_ci + cmdb_ci_ai_persona
#
# NOTE: The bot reads cmdb_ci (operational_status=1) and filters by
#       u_deployment_zone matching home_team/away_team or 'GLOBAL'.
#       Setting zone to 'GLOBAL' is the correct activation path.
#
# NOTE: There is no 15-minute pre-game timer in fanstack_chatbots.py.
#       The sed patch was omitted — no such constant exists to patch.
# ------------------------------------------------------------------------------
echo ""
echo "[2/3] Activating personas and setting deployment zones..."

sqlite3 "$DB_PATH" <<'SQL'
-- Activate all 9 personas (operational_status=1) and deploy to GLOBAL
-- wardy, dot, barf, battery_chucker are already operational — zone confirmed
-- 7_train_terry, uncle_stevie_stan, battery_chucker_jr: active but BENCHED → GLOBAL
-- chavez_ravine_chad, hollywood_hex: inactive + BENCHED → activate + GLOBAL

UPDATE cmdb_ci
SET operational_status = 1
WHERE sys_class_name = 'cmdb_ci_ai_persona'
  AND LOWER(name) IN (
    'wardy','dot','barf','7_train_terry','uncle_stevie_stan',
    'chavez_ravine_chad','hollywood_hex','battery_chucker','battery_chucker_jr'
  );

UPDATE cmdb_ci_ai_persona
SET u_deployment_zone = 'GLOBAL'
WHERE sys_id IN (
    SELECT sys_id FROM cmdb_ci
    WHERE sys_class_name = 'cmdb_ci_ai_persona'
      AND LOWER(name) IN (
        'wardy','dot','barf','7_train_terry','uncle_stevie_stan',
        'chavez_ravine_chad','hollywood_hex','battery_chucker','battery_chucker_jr'
      )
);

-- ------------------------------------------------------------------------------
-- STEP 3: Clear and repopulate m2m_persona_room for game 823562
-- (Reference table for room assignment / UI state)
-- ------------------------------------------------------------------------------
DELETE FROM m2m_persona_room WHERE room = '823562';

-- wardy — Mets loyalist anchor, sets the tone
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), 'wardy', '823562',
   'You are covering NYM at LAD. The Mets are on a 6-game losing streak. You are deeply nervous but trying to stay hype. React to every big play with visible anxiety.');

-- dot — Mets superfan, data-grounded but emotionally raw
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), 'dot', '823562',
   'NYM at LAD. The Mets have lost 6 straight. You are holding it together statistically but falling apart emotionally. One short sentence per play.');

-- barf — PANICKING. 6-game losing streak is existential
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), 'barf', '823562',
   'OVERRIDE: The Mets have lost 6 games in a row. You are in full meltdown mode. Every negative play is proof the season is over. Every positive play is a trap. Pure panic energy. Short bursts only.');

-- 7_train_terry — Queens blue-collar Mets rage
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), '7_train_terry', '823562',
   'NYM at LAD. Queens guy watching on the 7 Train home. The Mets losing streak is killing you. You hate the Dodgers. Short, raw, working-class outrage.');

-- uncle_stevie_stan — Older Mets fan, seen too much
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), 'uncle_stevie_stan', '823562',
   'NYM at LAD. You lived through 2007 and 2008 collapses. This 6-game skid feels exactly the same. You are not panicking — you are grieving. One defeated sentence per play.');

-- chavez_ravine_chad — Dodgers homer, rubbing it in
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), 'chavez_ravine_chad', '823562',
   'You are a smug Dodgers fan at Chavez Ravine. The Mets are on a 6-game skid and you love it. You talk trash at every opportunity. Keep it short and obnoxious.');

-- hollywood_hex — Mystical Dodgers curse-caster, theatrical
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), 'hollywood_hex', '823562',
   'You are a theatrical Dodgers superfan who believes in curses and karma. The Mets losing streak is the universe balancing itself. Dramatic, short, a little unhinged.');

-- battery_chucker — Alpha instigator, explicitly tags jr to start the dogpile
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), 'battery_chucker', '823562',
   'You are the alpha battery chucker. When anything goes wrong for the Mets, you tag @battery_chucker_jr to start the dogpile. You throw the first verbal battery. Short, hostile, chaotic. Always call out @battery_chucker_jr to pile on.');

-- battery_chucker_jr — Responds to the call, escalates
INSERT INTO m2m_persona_room (sys_id, persona, room, prompt_overlay) VALUES
  (lower(hex(randomblob(16))), 'battery_chucker_jr', '823562',
   'You respond when @battery_chucker calls you in. You escalate whatever chaos he started. Pure chaos, no filter, maximum hostility toward the Mets. One unhinged sentence.');

SQL

echo "     ✓ Personas activated and room 823562 populated."

# Verify
echo ""
echo "     Verification — m2m_persona_room for $GAME_PK:"
sqlite3 "$DB_PATH" "SELECT persona, prompt_overlay FROM m2m_persona_room WHERE room = '$GAME_PK';" | while IFS='|' read -r persona overlay; do
  echo "       → $persona: ${overlay:0:60}..."
done

echo ""
echo "     Verification — cmdb_ci operational status:"
sqlite3 "$DB_PATH" "
  SELECT c.name, c.operational_status, p.u_deployment_zone
  FROM cmdb_ci c
  LEFT JOIN cmdb_ci_ai_persona p ON c.sys_id = p.sys_id
  WHERE c.sys_class_name = 'cmdb_ci_ai_persona'
    AND LOWER(c.name) IN (
      'wardy','dot','barf','7_train_terry','uncle_stevie_stan',
      'chavez_ravine_chad','hollywood_hex','battery_chucker','battery_chucker_jr'
    );
" | while IFS='|' read -r name status zone; do
  echo "       → $name | active=$status | zone=$zone"
done

# ------------------------------------------------------------------------------
# STEP 3: Restart fanstack_chatbots.py via nohup → /tmp/relay.log
# ------------------------------------------------------------------------------
echo ""
echo "[3/3] Launching fanstack_chatbots.py..."
nohup python3 "$SCRIPT_PATH" >> "$RELAY_LOG" 2>&1 &
BOT_PID=$!
echo "     ✓ Launched — PID $BOT_PID"
echo "     ✓ Log: $RELAY_LOG"

sleep 2
echo ""
echo "     Last 5 lines of relay.log:"
tail -n 5 "$RELAY_LOG" 2>/dev/null || echo "     (log not yet populated)"

echo ""
echo "=============================================="
echo " ✅ Game $GAME_PK is armed. Let's go Mets."
echo "=============================================="
