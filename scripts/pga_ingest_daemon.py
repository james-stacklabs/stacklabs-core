#!/usr/bin/env python3
import socket
import json
import sqlite3
import requests
import traceback
import sys

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'
PULSE_URL = 'http://127.0.0.1:8000/api/pga/pulse'

def process_packet(data):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Determine if it's a shot telemetry or leaderboard update
        is_shot = "ball_speed_mph" in data or "shot_number" in data
        is_leaderboard = "current_position" in data or "score_to_par" in data
        
        if is_shot:
            player_id = int(data.get("player_id", 0))
            # Resolve name from leaderboard if not provided
            player_name = data.get("player_name")
            if not player_name:
                c.execute("SELECT player_name FROM pga_active_leaderboard WHERE player_id = ?", (player_id,))
                row = c.fetchone()
                player_name = row[0] if row else f"Player #{player_id}"
                
            hole_number = int(data.get("hole_number", 1))
            shot_number = int(data.get("shot_number", 1))
            ball_speed = float(data.get("ball_speed_mph", 0.0))
            launch_angle = float(data.get("launch_angle_deg", 0.0))
            spin_rate = float(data.get("spin_rate_rpm", 0.0))
            distance = float(data.get("distance_to_pin_yds", 0.0))
            surface = str(data.get("surface_type", "fairway"))
            
            # Insert telemetry
            c.execute("""
                INSERT INTO pga_tournament_telemetry 
                (player_id, hole_number, shot_number, ball_speed_mph, launch_angle_deg, spin_rate_rpm, distance_to_pin_yds, surface_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (player_id, hole_number, shot_number, ball_speed, launch_angle, spin_rate, distance, surface))
            
            # Update leaderboard player hole
            c.execute("""
                UPDATE pga_active_leaderboard 
                SET current_hole = ? 
                WHERE player_id = ?
            """, (hole_number, player_id))
            conn.commit()
            
            # Format commentary cue
            desc = f"{player_name} hits shot #{shot_number} on Hole {hole_number}. Ball Speed: {ball_speed} mph, Launch Angle: {launch_angle}°, Spin: {int(spin_rate)} rpm. Landed {distance} yards from the pin on the {surface}."
            print(f"[SHOT] {desc}", flush=True)
            
            # Trigger pulse to chatbots
            try:
                requests.post(PULSE_URL, json={"text": desc}, timeout=2)
            except Exception as e:
                print(f"[ERROR] Failed to send pulse to relay: {e}", flush=True)
                
        elif is_leaderboard:
            player_id = int(data.get("player_id", 0))
            player_name = str(data.get("player_name", "Unknown Player"))
            pos = int(data.get("current_position", 1))
            score = int(data.get("score_to_par", 0))
            hole = int(data.get("current_hole", 18))
            status = str(data.get("status", "ACTIVE"))
            
            c.execute("""
                INSERT OR REPLACE INTO pga_active_leaderboard 
                (player_id, player_name, current_position, score_to_par, current_hole, status, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (player_id, player_name, pos, score, hole, status))
            conn.commit()
            
            score_str = f"+{score}" if score > 0 else ("E" if score == 0 else str(score))
            desc = f"[LEADERBOARD UPDATE] {player_name} is now in position P{pos} at {score_str} to par (Hole {hole})."
            print(f"[LEADERBOARD] {desc}", flush=True)
            
            try:
                requests.post(PULSE_URL, json={"text": desc}, timeout=2)
            except Exception as e:
                print(f"[ERROR] Failed to send pulse to relay: {e}", flush=True)
                
        else:
            print(f"[WARNING] Unknown packet structure: {data}", flush=True)
            
        conn.close()
    except Exception as e:
        print(f"[ERROR] Exception during processing: {e}", flush=True)
        traceback.print_exc()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Bind to all interfaces to allow UDP input
    sock.bind(("0.0.0.0", 4005))
    print("[PGA DAEMON] Listening on UDP Port 4005...", flush=True)
    
    while True:
        try:
            data, addr = sock.recvfrom(65535)
            try:
                payload = json.loads(data.decode("utf-8"))
            except Exception as ex:
                print(f"[ERROR] Failed to decode JSON from {addr}: {ex}", flush=True)
                continue
                
            if isinstance(payload, list):
                for item in payload:
                    process_packet(item)
            else:
                process_packet(payload)
                
        except KeyboardInterrupt:
            print("[PGA DAEMON] Shutting down.", flush=True)
            break
        except Exception as e:
            print(f"[PGA DAEMON] Critical loop error: {e}", flush=True)
            traceback.print_exc()

if __name__ == "__main__":
    main()
