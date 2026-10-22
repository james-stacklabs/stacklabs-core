import http.server
import socketserver
import json
import os
import base64

PORT = 80
DIRECTORY = "/home/james/stacklabs"
CMDB_PATH = os.path.join(DIRECTORY, "04_Sovereign_Core/sovereign_cmdb.json")
SMUGGLER_BAY_PATH = os.path.join(DIRECTORY, "dna/archives/smuggler_dropzone")

# Ensure the Smuggler Bay exists natively on the local filesystem
os.makedirs(SMUGGLER_BAY_PATH, exist_ok=True)

class SovereignHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/telemetry':
            telemetry_path = os.path.join(DIRECTORY, "04_Sovereign_Core/telemetry.json")
            if os.path.exists(telemetry_path):
                self.send_response(200)
                self._set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                with open(telemetry_path, 'r') as f:
                    self.wfile.write(f.read().encode())
            else:
                self.send_response(404)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"error": "Telemetry not found"}')
        elif self.path == '/api/ledger':
            ledger_path = os.path.join(DIRECTORY, "master_ledger.json")
            if os.path.exists(ledger_path):
                self.send_response(200)
                self._set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                with open(ledger_path, 'r') as f:
                    self.wfile.write(f.read().encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'{"error": "Ledger not found"}')
        elif self.path == '/api/gwen/sessions':
            sessions_path = os.path.join(DIRECTORY, "dna/agents/GWEN/active_sessions")
            if os.path.exists(sessions_path):
                self.send_response(200)
                self._set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                items = sorted(os.listdir(sessions_path))
                self.wfile.write(json.dumps(items).encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'{"error": "Session directory not found"}')
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        if self.path == '/api/save_cmdb':
            try:
                data = json.loads(post_data)
                with open(CMDB_PATH, 'w') as f:
                    json.dump(data, f, indent=4)
                self.send_response(200)
                self._set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
            except Exception as e:
                self.send_response(500)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(f'{{"error": "{str(e)}"}}'.encode())
        
        elif self.path == '/api/upload':
            try:
                # The payload has pure Base64 images to bypass multipart boundaries!
                data = json.loads(post_data)
                assets = data.get("assets", [])
                
                # Write the text payload metadata into an event log
                event_log_path = os.path.join(SMUGGLER_BAY_PATH, f"payload_{data.get('timestamp', 'unknown').replace(':', '')}.json")
                with open(event_log_path, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Extract and decode all physical Blobs
                for asset in assets:
                    name = asset.get("name", "unknown_file.bin")
                    b64_data = asset.get("data", "")
                    
                    # Split 'data:image/png;base64,iVBORw0KGg...' to get the raw bytes
                    if "," in b64_data:
                        raw_b64 = b64_data.split(",")[1]
                    else:
                        raw_b64 = b64_data
                        
                    file_path = os.path.join(SMUGGLER_BAY_PATH, name)
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(raw_b64))

                print(f"[SMUGGLER BAY] Extracted {len(assets)} files into the zero-trust pipeline.")

                self.send_response(200)
                self._set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "assets_secured"}')
                
            except Exception as e:
                print(f"[API ERROR] {str(e)}")
                self.send_response(500)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(f'{{"error": "{str(e)}"}}'.encode())

        elif self.path == '/api/mission_notes':
            try:
                data = json.loads(post_data)
                notes_path = os.path.join(DIRECTORY, "dna/ci/mission_notes.json")
                
                # Load existing or start new
                current_notes = []
                if os.path.exists(notes_path):
                    with open(notes_path, 'r') as f:
                        current_notes = json.load(f)
                
                current_notes.append(data)
                
                with open(notes_path, 'w') as f:
                    json.dump(current_notes, f, indent=4)
                
                self.send_response(200)
                self._set_cors_headers()
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "captured"}')
            except Exception as e:
                self.send_response(500)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(f'{{"error": "{str(e)}"}}'.encode())
        else:
            self.send_response(404)
            self._set_cors_headers()
            self.end_headers()

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == '__main__':
    with ReusableTCPServer(("", PORT), SovereignHandler) as httpd:
        print(f"Sovereign Core API (Port {PORT}) online with Smuggler Bay & Ω CAST endpoints.")
        httpd.serve_forever()
