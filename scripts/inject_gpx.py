#!/usr/bin/env python3
import os
import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime

GPX_PATH = "/home/james/sovereign_inbox/needs_review/metsy_gps_export_05262026.gpx"
if not os.path.exists(GPX_PATH):
    GPX_PATH = "/home/james/sovereign_inbox/today/metsy_gps_export_05262026.gpx"
TARGET_FILES = [
    "/home/james/stacklabs/20_AetherVet/public/aethervet_telemetry.html",
    "/home/james/stacklabs/01_Sovereign_Portal/public/aethervet_telemetry.html",
]

def main():
    print(f"Reading GPX from: {GPX_PATH}")
    if not os.path.exists(GPX_PATH):
        print(f"ERROR: GPX file not found at {GPX_PATH}")
        return

    # Parse XML
    tree = ET.parse(GPX_PATH)
    ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
    
    raw_points = []
    for trkpt in tree.findall(".//gpx:trkpt", ns):
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        
        time_el = trkpt.find("gpx:time", ns)
        if time_el is None or not time_el.text:
            continue
            
        time_str = time_el.text.strip()
        # Parse timestamp to filter
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
            # Filter to May 24, 2026 and onwards
            if dt >= datetime(2026, 5, 24):
                raw_points.append({
                    "lat": lat,
                    "lon": lon,
                    "time": time_str
                })
        except Exception as e:
            print(f"Warning: skipped point due to parsing error: {e}")
            
    print(f"Successfully loaded and filtered {len(raw_points)} points spanning {raw_points[0]['time']} to {raw_points[-1]['time']}.")
    
    # Serialize JSON
    points_json = json.dumps(raw_points)
    
    # Direct JSON File Output paths
    JSON_OUTPUT_FILES = [
        "/home/james/stacklabs/20_AetherVet/public/data/metsy_gpx_points.json",
        "/home/james/stacklabs/01_Sovereign_Portal/public/data/metsy_gpx_points.json",
    ]
    
    for json_path in JSON_OUTPUT_FILES:
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(points_json)
        print(f"Successfully generated dynamic JSON data file: {json_path}")
        
    # Inject into HTML files
    for filepath in TARGET_FILES:
        if not os.path.exists(filepath):
            print(f"Skipping non-existent file: {filepath}")
            continue
            
        print(f"Injecting into: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Find the line defining rawGpxPoints
        # Match 'const rawGpxPoints = [...];' across lines if necessary or on a single line
        pattern = r"const\s+rawGpxPoints\s*=\s*\[.*?\];"
        
        if not re.search(pattern, content):
            print(f"Warning: Could not find rawGpxPoints definition in {filepath} (skipping html injection)")
            continue
            
        new_content, count = re.subn(pattern, f"const rawGpxPoints = {points_json};", content, flags=re.DOTALL)
        if count > 0:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Successfully injected rawGpxPoints array into {filepath} (matched {count} occurrence(s)).")
        else:
            print(f"Failed to replace rawGpxPoints in {filepath}.")

if __name__ == "__main__":
    main()
