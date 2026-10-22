import os
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler

class RestHandler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/update_test_page':
            query = parse_qs(parsed_url.query)
            new_text = query.get('message', ['Hello James'])[0]
            html_content = f"""<html>
<head>
    <title>Extranet Test</title>
    <style>
        body {{ background-color: #0f1115; color: #38bdf8; font-family: monospace; display: flex; justify-content: center; align-items: center; height: 100vh; }}
    </style>
</head>
<body>
    <h1 id="message">{new_text}</h1>
</body>
</html>"""
            with open('/home/james/stacklabs/ferris_test.html', 'w') as f:
                f.write(html_content)
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'SUCCESS: DOM WRITTEN BY GET RPC')
        elif parsed_url.path == '/api/write_savant':
            import base64
            query = parse_qs(parsed_url.query)
            try:
                # Replace URI spaces with + for valid base64 parsing
                b64_payload = query.get('payload', [''])[0].replace(' ', '+')
                tsx_content = base64.b64decode(b64_payload).decode('utf-8')
                target_path = '/home/james/stacklabs/01_Sovereign_Portal/src/components/SavantQueryBlock.tsx'
                with open(target_path, 'w') as f:
                    f.write(tsx_content)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'SUCCESS: SAVANT DOM INJECTED VIA RPC')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif parsed_url.path == '/barb_pacemaker.html':
            try:
                with open('/home/james/stacklabs/01_Sovereign_Portal/public/barb_pacemaker.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/update_test_page':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                new_text = data.get('message', 'Hello James')
                
                html_content = f"""<html>
<head>
    <title>Extranet Test</title>
    <style>
        body {{ background-color: #0f1115; color: #38bdf8; font-family: monospace; display: flex; justify-content: center; align-items: center; height: 100vh; }}
    </style>
</head>
<body>
    <h1 id="message">{new_text}</h1>
</body>
</html>"""
                
                with open('/home/james/stacklabs/ferris_test.html', 'w') as f:
                    f.write(html_content)
                    
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
        elif self.path == '/api/download_youtube':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                url = data.get('url', '')
                if not url: raise ValueError("URL is missing")
                
                # Run download task in background
                import subprocess
                subprocess.Popen(['python3', 'scripts/download_youtube.py', url])
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "success", "message": "Extranet Download Dropzone Engaged"}')
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
        elif self.path == '/api/ingress':
            # Wardy Tracker Beacon
            import sqlite3
            from datetime import datetime
            import subprocess
            
            try:
                # Play physical chime
                print("\n🔔 [VIP INGRESS DETECTED] Wardy has entered the Sandbox 🔔\n")
                try:
                    subprocess.Popen(['paplay', '/usr/share/sounds/freedesktop/stereo/message.oga'], stderr=subprocess.DEVNULL)
                except:
                    print('\a') # Fallback to terminal bell

                # Log to DB Severity 0
                conn = sqlite3.connect('/home/james/stacklabs/dna/sovereign_now.db')
                c = conn.cursor()
                try:
                    c.execute('CREATE TABLE IF NOT EXISTS sys_alerts (timestamp TEXT, severity INTEGER, message TEXT, sys_created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP, sys_updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
                    c.execute('INSERT INTO sys_alerts (timestamp, severity, message) VALUES (?, ?, ?)', 
                              (datetime.now().isoformat(), 0, '[VIP INGRESS DETECTED] Wardy connected to FanStack Sandbox'))
                    conn.commit()
                finally:
                    conn.close()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "ingress_logged"}')
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    os.chdir('/home/james/stacklabs')
    server = HTTPServer(('127.0.0.1', 8090), RestHandler)
    print("Sovereign Extranet REST server active on Port 8090...")
    server.serve_forever()
