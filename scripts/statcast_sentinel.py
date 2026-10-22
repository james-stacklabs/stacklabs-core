#!/home/james/stacklabs/.venv/bin/python3
# statcast_sentinel.py — Sovereign OS: Continuous Savant Polling Daemon
# CRITICAL: Must execute via the project venv. pybaseball + sqlalchemy are
# not installed in the system Python. Shebang enforces correct interpreter.
import time
import random
import argparse
from datetime import datetime, tzinfo
from zoneinfo import ZoneInfo
import sqlite3
import pandas as pd
from pybaseball import statcast
from sqlalchemy import create_engine, text
import os

DB_PATH    = '/home/james/stacklabs/sovereign_intelligence.db'
TABLE_NAME = 'statcast_pitches'

# ---------------------------------------------------------------------------
# SCHEMA BOOTSTRAP DDL
# ---------------------------------------------------------------------------
# sovereign_intelligence.db is currently a 0-byte empty file.
# df.to_sql(if_exists='append') does NOT create the table — it only appends
# to an existing one. Without this DDL, the sentinel throws:
#   OperationalError: no such table: statcast_pitches
# on every single run, discarding all Statcast data silently.
#
# Column list matches the canonical pybaseball.statcast() DataFrame schema.
# All columns default to NULL-permissive to handle version drift in the
# pybaseball library without crashing the insert pipeline.
# ---------------------------------------------------------------------------
STATCAST_DDL = """
CREATE TABLE IF NOT EXISTS statcast_pitches (
    pitch_type                          TEXT,
    game_date                           TEXT,
    release_speed                       REAL,
    release_pos_x                       REAL,
    release_pos_z                       REAL,
    player_name                         TEXT,
    batter                              INTEGER,
    pitcher                             INTEGER,
    events                              TEXT,
    description                         TEXT,
    spin_dir                            REAL,
    spin_rate_deprecated                REAL,
    break_angle_deprecated              REAL,
    break_length_deprecated             REAL,
    zone                                INTEGER,
    des                                 TEXT,
    game_type                           TEXT,
    stand                               TEXT,
    p_throws                            TEXT,
    home_team                           TEXT,
    away_team                           TEXT,
    type                                TEXT,
    hit_location                        INTEGER,
    bb_type                             TEXT,
    balls                               INTEGER,
    strikes                             INTEGER,
    game_year                           INTEGER,
    pfx_x                               REAL,
    pfx_z                               REAL,
    plate_x                             REAL,
    plate_z                             REAL,
    on_3b                               REAL,
    on_2b                               REAL,
    on_1b                               REAL,
    outs_when_up                        INTEGER,
    inning                              INTEGER,
    inning_topbot                       TEXT,
    hc_x                                REAL,
    hc_y                                REAL,
    fielder_2                           REAL,
    umpire                              REAL,
    sv_id                               TEXT,
    vx0                                 REAL,
    vy0                                 REAL,
    vz0                                 REAL,
    ax                                  REAL,
    ay                                  REAL,
    az                                  REAL,
    sz_top                              REAL,
    sz_bot                              REAL,
    hit_distance_sc                     REAL,
    launch_speed                        REAL,
    launch_angle                        REAL,
    effective_speed                     REAL,
    release_spin_rate                   REAL,
    release_extension                   REAL,
    game_pk                             INTEGER,
    fielder_3                           REAL,
    fielder_4                           REAL,
    fielder_5                           REAL,
    fielder_6                           REAL,
    fielder_7                           REAL,
    fielder_8                           REAL,
    fielder_9                           REAL,
    release_pos_y                       REAL,
    estimated_ba_using_speedangle       REAL,
    estimated_woba_using_speedangle     REAL,
    woba_value                          REAL,
    woba_denom                          INTEGER,
    babip_value                         INTEGER,
    iso_value                           INTEGER,
    launch_speed_angle                  INTEGER,
    at_bat_number                       INTEGER,
    pitch_number                        INTEGER,
    pitch_name                          TEXT,
    home_score                          INTEGER,
    away_score                          INTEGER,
    bat_score                           INTEGER,
    fld_score                           INTEGER,
    post_away_score                     INTEGER,
    post_home_score                     INTEGER,
    post_bat_score                      INTEGER,
    post_fld_score                      INTEGER,
    if_fielding_alignment               TEXT,
    of_fielding_alignment               TEXT,
    delta_home_win_exp                  REAL,
    delta_run_exp                       REAL,
    bat_speed                           REAL,
    swing_length                        REAL
);
"""


def _ensure_schema(engine) -> None:
    """
    Idempotently bootstraps the statcast_pitches table in sovereign_intelligence.db.

    Uses CREATE TABLE IF NOT EXISTS — safe to call on every daemon startup.
    Must be called BEFORE any df.to_sql() or DELETE operation in sentinel_loop()
    to prevent OperationalError on a fresh or 0-byte database file.

    Args:
        engine: A SQLAlchemy Engine connected to sovereign_intelligence.db.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(STATCAST_DDL))
            conn.commit()
        print(f"[SENTINEL] Schema bootstrap complete: '{TABLE_NAME}' table verified in {DB_PATH}")
    except Exception as e:
        # Schema failure is fatal — raise immediately rather than letting the
        # loop proceed and silently discard every Statcast payload.
        raise RuntimeError(f"[SENTINEL] FATAL: Schema bootstrap failed: {e}") from e

def print_banner():
    print("="*60)
    print(" ⚾ SOVEREIGN OS: CONTINUOUS SAVANT POLLING DAEMON ⚾")
    print(" NODE: node.73 (Master Studio Node)")
    print(" STATUS: VANGUARD AIRGAP PIPELINE SECURED.")
    print(" MISSION: PREDICTIVE LATENCY INTERCEPTION ENGINE (PLIE)")
    print("="*60)

def is_active_game_hours(current_time_est):
    """
    Determine if current time is within typical MLB active game hours.
    Typically, 1:00 PM EST to 2:00 AM EST the next day.
    """
    hour = current_time_est.hour
    
    # Active between 12:00 (Noon) and 02:59 AM
    if hour >= 12 or hour < 3:
        return True
    return False

def sentinel_loop():
    engine = create_engine(f'sqlite:///{DB_PATH}')

    # CRITICAL: Bootstrap schema BEFORE entering the ingestion loop.
    # If sovereign_intelligence.db is 0-bytes or statcast_pitches table is
    # absent, every df.to_sql() call will throw OperationalError and silently
    # discard the entire Statcast payload. _ensure_schema() is idempotent.
    _ensure_schema(engine)

    est_tz = ZoneInfo('America/New_York')

    print_banner()
    print("[+] Sentinel daemon initialized. Beginning telemetry hoarding loop.\n")
    
    while True:
        try:
            now_est = datetime.now(est_tz)
            today_str = now_est.strftime('%Y-%m-%d')
            current_time_str = now_est.strftime('%H:%M:%S EST')
            
            if not is_active_game_hours(now_est):
                print(f"[{current_time_str}] Outside active MLB windows. Sleeping for 60 minutes...")
                time.sleep(3600)
                continue
                
            print(f"[{current_time_str}] Active game window. Initiating stealth micro-batch pull for {today_str}...")
            
            # 1. Pull current day's events
            df = statcast(start_dt=today_str, end_dt=today_str)
            
            if df is not None and not df.empty:
                # 2. Extract and cast composite keys for idempotency checking
                df['game_pk'] = df['game_pk'].astype(float).fillna(0).astype(int)
                df['at_bat_number'] = df['at_bat_number'].astype(float).fillna(0).astype(int)
                df['pitch_number'] = df['pitch_number'].astype(float).fillna(0).astype(int)

                # Fetch existing keys from db
                existing_keys = set()
                with engine.connect() as conn:
                    result = conn.execute(text(
                        f"SELECT game_pk, at_bat_number, pitch_number FROM {TABLE_NAME} WHERE game_date LIKE '{today_str}%'"
                    )).fetchall()
                    for r in result:
                        existing_keys.add((int(r[0]), int(r[1]), int(r[2])))
                
                # Filter df to find only new pitches
                new_rows = []
                for _, row in df.iterrows():
                    key = (int(row['game_pk']), int(row['at_bat_number']), int(row['pitch_number']))
                    if key not in existing_keys:
                        new_rows.append(row)
                
                if new_rows:
                    df_new = pd.DataFrame(new_rows)
                    df_new.to_sql(TABLE_NAME, engine, if_exists='append', index=False)
                    print(f"  [+] SUCCESS: Injected {len(df_new)} new payload events (out of {len(df)} fetched) into sovereign_intelligence.db")
                else:
                    print("  [-] No new events to inject. All fetched events already exist in database.")
            else:
                print("  [-] No new events found for today's micro-batch.")
                
            # 4. Stealth Mode: Sleep for a random interval between 15 and 30 minutes
            sleep_mins = random.uniform(15.0, 30.0)
            sleep_secs = int(sleep_mins * 60)
            
            next_pull = (now_est + pd.Timedelta(seconds=sleep_secs)).strftime('%H:%M:%S EST')
            print(f"  [z] Evasion active. Next Savant strike scheduled for ~{next_pull} ({sleep_mins:.1f} minutes).")
            
            time.sleep(sleep_secs)

        except Exception as e:
            print(f"  [ERROR] Savant connection failed or DB lock: {e}")
            print("  [z] Retrying in 5 minutes...")
            time.sleep(300)

if __name__ == "__main__":
    sentinel_loop()
