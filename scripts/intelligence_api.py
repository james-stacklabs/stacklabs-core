import json
import sqlite3
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

DB_PATH = '/home/james/stacklabs/sovereign_intelligence.db'
PORT = 8082

class IntelligenceRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/stats/overview':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get Counts
                cursor.execute("SELECT count(*) as total, game_year FROM statcast_pitches GROUP BY game_year")
                rows = cursor.fetchall()
                counts = {str(row['game_year']): row['total'] for row in rows}
                
                # Get Latest 10 Pitches
                cursor.execute("SELECT player_name, release_speed, hit_distance_sc, launch_speed, events, des FROM statcast_pitches ORDER BY rowid DESC LIMIT 10")
                latest = [dict(row) for row in cursor.fetchall()]
                
                # Get DB Size
                db_size = os.path.getsize(DB_PATH) / (1024 * 1024) # MB
                
                response = {
                    "status": "LIVE",
                    "db_size_mb": round(db_size, 2),
                    "counts": counts,
                    "latest_pitches": latest
                }
                
                self.wfile.write(json.dumps(response).encode('utf-8'))
                conn.close()
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            super().do_GET()

if __name__ == '__main__':
    server_address = ('0.0.0.0', PORT)
    httpd = ThreadingHTTPServer(server_address, IntelligenceRequestHandler)
    print(f"[+] Sovereign Intelligence API Running on Port {PORT}")
    httpd.serve_forever()
