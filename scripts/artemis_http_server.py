#!/usr/bin/env python3
"""
StackLabs Artemis Quad-Grid HTTP Egress Server
Serves /dev/shm/vfs/mosaic/egress on port 8088 with CORS and low-latency headers.
"""
import sys
import os
import http.server
import socketserver

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
DIRECTORY = sys.argv[2] if len(sys.argv) > 2 else "/dev/shm/vfs/mosaic/egress"

class MosaicHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        '.m3u8': 'application/vnd.apple.mpegurl',
        '.ts': 'video/mp2t',
        '.js': 'application/javascript',
        '.html': 'text/html',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress routine chunk polling logs to avoid console spam
        if 'GET /master_grid' in args[0] or 'GET /segment_' in args[0]:
            return
        super().log_message(format, *args)

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == '__main__':
    os.makedirs(DIRECTORY, exist_ok=True)
    with ReusableTCPServer(("", PORT), MosaicHTTPRequestHandler) as httpd:
        print(f"⚡ Artemis Egress HTTP Server active on port {PORT} serving {DIRECTORY}", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down HTTP server.", flush=True)
