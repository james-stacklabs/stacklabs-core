#!/usr/bin/env python3
"""CORS proxy for Ollama — runs on port 11435"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error

class ProxyHandler(BaseHTTPRequestHandler):
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.cors()
        self.end_headers()

    def do_GET(self):
        self.proxy("GET")

    def do_POST(self):
        self.proxy("POST")

    def proxy(self, method):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:11434{self.path}",
                data=body,
                method=method,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                self.send_response(r.status)
                self.cors()
                self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
                self.end_headers()
                while chunk := r.read(512):
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except Exception as e:
            self.send_response(500)
            self.cors()
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, *args): pass

HTTPServer(("0.0.0.0", 11436), ProxyHandler).serve_forever()
