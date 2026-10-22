#!/usr/bin/env python3
"""
StackLabs Horizon Surface Discovery & Route Extractor
Scans frontend trees and backend blueprints to compile an exhaustive route inventory.
Target Silicon: Clio Metal Forge | Python 3.12 (.venv)
"""

import os
import re
import json
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs")
OUTPUT_MANIFEST = BASE_DIR / "data/horizon_discovered_routes.json"

FRONTEND_SEARCH_DIRS = [
    BASE_DIR / "apps/horizon_scratchpad",
    BASE_DIR / "apps/horizon",
    BASE_DIR / "frontend",
    BASE_DIR / "dossiers/01_Pawel_Rudnicki_Horizon",
    BASE_DIR / "dossiers/05_StackLabs_Internal"
]

BLUEPRINT_DIR = BASE_DIR / "scripts/blueprints"

ROUTE_REGEXES = [
    re.compile(r'path=[\'"]([^\'"]+)[\'"]'),
    re.compile(r'<Route[^>]+path=[\'"]([^\'"]+)[\'"]'),
    re.compile(r'createBrowserRouter\(\[\s*\{[^}]*path:\s*[\'"]([^\'"]+)[\'"]'),
    re.compile(r'fetch\([\'"](/api/[^\'"]+)[\'"]'),
    re.compile(r'href=[\'"](/[^#\'"]+)[\'"]')
]

COMPONENT_FILE_REGEX = re.compile(r'\.(tsx|jsx|html|js)$')

def extract_frontend_routes():
    discovered_routes = set()
    orphaned_components = []

    for search_dir in FRONTEND_SEARCH_DIRS:
        if not search_dir.exists():
            continue

        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.venv', '.git', 'dist', 'build', '__pycache__')]
            for file in files:
                file_path = Path(root) / file
                if not COMPONENT_FILE_REGEX.search(file):
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                matched = False
                for pattern in ROUTE_REGEXES:
                    matches = pattern.findall(content)
                    for m in matches:
                        if m and not m.startswith("http") and not m.startswith("*"):
                            clean_route = m if m.startswith("/") else f"/{m}"
                            clean_route = clean_route.split("?")[0]
                            discovered_routes.add(clean_route)
                            matched = True

                if any(k in file for k in ["Inspector", "Drawer", "Horizon", "chat", "passport", "index"]):
                    orphaned_components.append({
                        "file": str(file_path.relative_to(BASE_DIR)),
                        "has_explicit_route": matched
                    })

    # Default canonical Horizon roots if router is dynamically declared
    fallback_routes = [
        "/",
        "/horizon",
        "/horizon/inspector",
        "/horizon/anomalies",
        "/horizon/provenance",
        "/horizon/audit"
    ]
    for r in fallback_routes:
        discovered_routes.add(r)

    return sorted(list(discovered_routes)), orphaned_components

def extract_backend_endpoints():
    endpoints = []
    if BLUEPRINT_DIR.exists():
        route_pattern = re.compile(r'@\w+\.route\([\'"]([^\'"]+)[\'"]')
        for root, dirs, files in os.walk(BLUEPRINT_DIR):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.venv', '.git', 'dist', 'build', '__pycache__')]
            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = Path(root) / file
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    matches = route_pattern.findall(content)
                    for m in matches:
                        if any(kw in m for kw in ["horizon", "evidence", "provenance", "market"]):
                            endpoints.append({
                                "file": str(file_path.relative_to(BASE_DIR)),
                                "endpoint": m
                            })
                except Exception:
                    continue
    return endpoints

def main():
    print("[*] Starting Horizon static surface discovery...")
    routes, orphans = extract_frontend_routes()
    endpoints = extract_backend_endpoints()

    payload = {
        "timestamp": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
        "routes": routes,
        "orphaned_or_subcomponents": orphans,
        "backend_endpoints": endpoints
    }

    OUTPUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[+] Route manifest written to {OUTPUT_MANIFEST}")
    print(f"[+] Total routes indexed: {len(routes)}")
    print(f"[+] Total inspected subcomponents: {len(orphans)}")

if __name__ == "__main__":
    main()
