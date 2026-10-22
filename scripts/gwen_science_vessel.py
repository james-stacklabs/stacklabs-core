import os
import glob
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import math

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAILO_DROP = os.path.join(BASE_DIR, "dna", "media", "hailo_dropzone")
DATA_DIR = os.path.join(BASE_DIR, "dna", "agents", "GWEN", "data")
OUTPUT_HTML = os.path.join(BASE_DIR, "dna", "agents", "GWEN", "science_vessel_dashboard.html")

PETKIT_JSON = os.path.join(DATA_DIR, "petkit_history.json")
THRONE_JSON = os.path.join(DATA_DIR, "throne_rooms.json")

def parse_gpx_files():
    points = []
    # Check both HAILO_DROP and DATA_DIR for GPX files
    gpx_files = glob.glob(os.path.join(HAILO_DROP, "*.gpx")) + glob.glob(os.path.join(DATA_DIR, "*.gpx"))
    for file in set(gpx_files): # set to remove duplicates if dirs are same
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            namespace = ""
            if "}" in root.tag:
                namespace = root.tag.split("}")[0] + "}"
            
            for trkpt in root.findall(f".//{namespace}trkpt"):
                lat = float(trkpt.attrib.get("lat"))
                lon = float(trkpt.attrib.get("lon"))
                time_node = trkpt.find(f".//{namespace}time")
                timestamp = time_node.text if time_node is not None else None
                points.append({"lat": lat, "lon": lon, "time": timestamp})
        except Exception as e:
            print(f"Error parsing GPX {file}: {e}")
    # Sort points chronologically
    points.sort(key=lambda x: x["time"] if x["time"] else "")
    return points

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def generate_html(gpx_points, petkit_data, throne_data):
    throne_js = "[]"
    if throne_data and "throne_rooms" in throne_data:
        throne_js = json.dumps(throne_data["throne_rooms"])
    
    petkit_events_js = "[]"
    petkit_events = []
    if petkit_data and "100036188" in petkit_data and "history_records" in petkit_data["100036188"]:
        for record in petkit_data["100036188"]["history_records"]:
            if record.get("enumEventType") == "pet_out":
                dt = datetime.fromtimestamp(record.get("timestamp", 0))
                petkit_events.append({
                    "time": dt.isoformat(), 
                    "weight": record.get("content", {}).get("petWeight", 0) / 1000.0,
                    "duration": record.get("content", {}).get("timeOut", 0) - record.get("content", {}).get("timeIn", 0)
                })
        petkit_events_js = json.dumps(petkit_events)

    gpx_points_js = json.dumps(gpx_points) if gpx_points else "[]"
        
    start_lat = gpx_points[0]["lat"] if gpx_points else 33.8849
    start_lon = gpx_points[0]["lon"] if gpx_points else -84.5308

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gwen // Science Vessel // Metsy Counter-Recon</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Outfit:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {{
            --bg-void: #05050a;
            --panel: rgba(18, 20, 31, 0.85);
            --border: rgba(99, 102, 241, 0.3);
            --accent-cyan: #2DD4BF;
            --accent-indigo: #6366F1;
            --accent-amber: #FBBF24;
            --alert-red: #FF3366;
            --text: #ffffff;
            --text-dim: #8b9bb4;
            --font-body: 'Inter', sans-serif;
            --font-header: 'Outfit', sans-serif;
        }}
        body, html {{ margin: 0; padding: 0; height: 100%; font-family: var(--font-body); background: var(--bg-void); color: var(--text); overflow: hidden; }}
        #container {{ display: flex; height: 100vh; flex-direction: column; }}
        #header {{ background: var(--panel); padding: 15px 30px; border-bottom: 2px solid var(--accent-indigo); display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 20px rgba(99, 102, 241, 0.2); z-index: 1000; }}
        h1 {{ margin: 0; font-family: var(--font-header); font-size: 1.5rem; letter-spacing: 2px; }}
        h1 span {{ color: var(--accent-cyan); text-shadow: 0 0 10px rgba(45, 212, 191, 0.5); }}
        .header-meta {{ font-size: 0.9rem; color: var(--text-dim); display:flex; gap: 20px; }}
        .header-meta strong {{ color: var(--accent-indigo); }}
        #content {{ display: flex; flex: 1; position: relative; }}
        #map {{ flex: 3; height: 100%; z-index: 1; }}
        #sidebar {{ flex: 1; min-width: 350px; max-width: 450px; padding: 20px; overflow-y: auto; border-left: 1px solid var(--border); background: var(--panel); z-index: 10; backdrop-filter: blur(10px); }}
        .hud-card {{ background: rgba(99, 102, 241, 0.05); border: 1px solid var(--border); padding: 20px; margin-bottom: 20px; border-radius: 12px; transition: 0.3s; }}
        .hud-card:hover {{ border-color: var(--accent-cyan); box-shadow: 0 0 15px rgba(45, 212, 191, 0.1); }}
        h2 {{ margin-top: 0; font-family: var(--font-header); font-size: 1.1rem; letter-spacing: 1px; color: var(--text); border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
        h2 span {{ color: var(--accent-amber); }}
        .metric-value {{ font-size: 1.8rem; font-weight: 800; color: var(--accent-cyan); text-shadow: 0 0 10px rgba(45, 212, 191, 0.3); }}
        
        /* Temporal Scrubber Custom CSS */
        .scrubber-container {{ padding: 15px 0; }}
        input[type="range"] {{ width: 100%; margin: 10px 0; -webkit-appearance: none; background: transparent; }}
        input[type="range"]::-webkit-slider-runnable-track {{ width: 100%; height: 6px; background: rgba(99, 102, 241, 0.3); border-radius: 3px; border: 1px solid var(--border); }}
        input[type="range"]::-webkit-slider-thumb {{ -webkit-appearance: none; height: 18px; width: 18px; border-radius: 50%; background: var(--accent-cyan); cursor: pointer; margin-top: -6px; box-shadow: 0 0 10px var(--accent-cyan); }}
        .time-labels {{ display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-dim); }}
        
        .alert {{ color: var(--alert-red); font-weight: bold; background: rgba(255, 51, 102, 0.1); padding: 10px; border-radius: 6px; border: 1px solid rgba(255, 51, 102, 0.3); margin-top:10px; }}
        .recon-log {{ font-family: monospace; font-size: 0.85rem; color: var(--accent-amber); margin-top: 10px; max-height: 150px; overflow-y: auto; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 6px; }}
        .recon-log div {{ margin-bottom: 4px; border-bottom: 1px dashed rgba(251, 191, 36, 0.2); padding-bottom:2px; }}
    </style>
</head>
<body>
    <div id="container">
        <div id="header">
            <h1>G.W.E.N. <span>VESPER VET</span></h1>
            <div class="header-meta">
                <span><strong>OP:</strong> COUNTER-RECON</span>
                <span><strong>SUBJECT:</strong> METSY (NODE .171)</span>
                <span><strong>TARGET:</strong> SAM (14LB UNIT)</span>
            </div>
        </div>
        <div id="content">
            <div id="map"></div>
            <div id="sidebar">
                <div class="hud-card">
                    <h2>THE TEMPORAL <span>SCRUBBER</span></h2>
                    <div class="scrubber-container">
                        <div id="scrubber-date" style="font-weight: bold; color: var(--accent-cyan); text-align: center; margin-bottom: 10px;">Loading Timeline...</div>
                        <input type="range" id="time-slider" min="0" max="100" value="100">
                        <div class="time-labels">
                            <span id="start-time">Start</span>
                            <span id="end-time">End</span>
                        </div>
                    </div>
                </div>

                <div class="hud-card">
                    <h2>METRIC <span>HUB</span></h2>
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <div style="color:var(--text-dim); font-size:0.8rem; text-transform:uppercase;">Distance Extracted</div>
                            <div class="metric-value" id="distance-calc">0.00 mi</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color:var(--text-dim); font-size:0.8rem; text-transform:uppercase;">Data Points</div>
                            <div style="color:var(--accent-indigo); font-weight:bold; font-size:1.2rem;" id="point-count">0</div>
                        </div>
                    </div>
                </div>
                
                <div class="hud-card" style="border-color: var(--alert-red);">
                    <h2 style="color: var(--alert-red); border-bottom-color: var(--alert-red);">PREDICTIVE <span>ANOMALY LOOP</span></h2>
                    <p style="font-size:0.85rem; color:var(--text-dim);">Analyzing historical GNSS excursions against known Sam safehouses (Crestwood & Hillside).</p>
                    <div class="alert">⚠️ TARGET LOCK: COUNTER-SURVEILLANCE DETECTED</div>
                    <div class="recon-log" id="recon-log">
                        <!-- Recon events populated here -->
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://leaflet.github.io/Leaflet.heat/dist/leaflet-heat.js"></script>
    <script>
        const rawGpxPoints = {gpx_points_js};
        const throneData = {throne_js};
        
        // Map initialization
        const map = L.map('map', {{ zoomControl: false }}).setView([{start_lat}, {start_lon}], 18);
        L.control.zoom({{ position: 'bottomright' }}).addTo(map);

        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            subdomains: 'abcd',
            maxZoom: 22
        }}).addTo(map);

        // Layers
        let heatLayer = null;
        let traceLayer = null;
        const anomalyMarkers = L.layerGroup().addTo(map);

        // Core Centroid (Home Base approximation based on average of first 50 points)
        let homeLat = {start_lat}, homeLon = {start_lon};
        if(rawGpxPoints.length > 50) {{
            homeLat = rawGpxPoints.slice(0,50).reduce((sum, p) => sum + p.lat, 0) / 50;
            homeLon = rawGpxPoints.slice(0,50).reduce((sum, p) => sum + p.lon, 0) / 50;
        }}

        // Sam's Known Safehouses (Approximations based on outliers)
        // We will scan the data to find the furthest East (Crestwood) and furthest South (Hillside)
        let crestwood = {{lat: homeLat, lon: homeLon}};
        let hillside = {{lat: homeLat, lon: homeLon}};
        
        rawGpxPoints.forEach(p => {{
            if(p.lon > crestwood.lon) crestwood = p; // Furthest East
            if(p.lat < hillside.lat) hillside = p;   // Furthest South
        }});

        // Render Anomaly Markers for Safehouses
        const crestwoodIcon = L.divIcon({{className: 'custom-div-icon', html: "<div style='background:rgba(255, 191, 36, 0.8); border:2px solid #FBBF24; color:#000; padding:2px 5px; border-radius:4px; font-weight:bold; font-size:10px; white-space:nowrap;'>🎯 SAM: CRESTWOOD</div>"}});
        const hillsideIcon = L.divIcon({{className: 'custom-div-icon', html: "<div style='background:rgba(255, 191, 36, 0.8); border:2px solid #FBBF24; color:#000; padding:2px 5px; border-radius:4px; font-weight:bold; font-size:10px; white-space:nowrap;'>🎯 SAM: HILLSIDE</div>"}});
        
        L.marker([crestwood.lat, crestwood.lon], {{icon: crestwoodIcon}}).addTo(anomalyMarkers);
        L.marker([hillside.lat, hillside.lon], {{icon: hillsideIcon}}).addTo(anomalyMarkers);

        // Haversine distance formula
        function calculateDistance(points) {{
            if(points.length < 2) return 0;
            let dist = 0;
            for(let i=1; i<points.length; i++) {{
                const p1 = points[i-1], p2 = points[i];
                const R = 3958.8; // Radius of earth in miles
                const dLat = (p2.lat - p1.lat) * Math.PI / 180;
                const dLon = (p2.lon - p1.lon) * Math.PI / 180;
                const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                        Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
                        Math.sin(dLon/2) * Math.sin(dLon/2);
                const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
                dist += R * c;
            }}
            return dist;
        }}

        function updateMap(endIndex) {{
            const visiblePoints = rawGpxPoints.slice(0, endIndex);
            
            // Update Metric Hub
            const dist = calculateDistance(visiblePoints);
            document.getElementById('distance-calc').innerText = dist.toFixed(2) + " mi";
            document.getElementById('point-count').innerText = visiblePoints.length;

            if(visiblePoints.length > 0) {{
                const d = new Date(visiblePoints[visiblePoints.length-1].time);
                document.getElementById('scrubber-date').innerText = d.toLocaleString();
            }}

            // 1. Heat Layer (The Thrones)
            if(heatLayer) map.removeLayer(heatLayer);
            const heatData = visiblePoints.map(p => [p.lat, p.lon, 1]);
            heatLayer = L.heatLayer(heatData, {{radius: 20, blur: 15, maxZoom: 17, gradient: {{0.4: '#6366F1', 0.6: '#2DD4BF', 1.0: '#FF3366'}}}}).addTo(map);

            // 2. Trace Layer (Thick Blue Movement Axes)
            if(traceLayer) map.removeLayer(traceLayer);
            const latlngs = visiblePoints.map(p => [p.lat, p.lon]);
            traceLayer = L.polyline(latlngs, {{color: '#6366F1', weight: 4, opacity: 0.6, lineJoin: 'round'}}).addTo(map);

            // 3. Predictive Anomaly Loop (Log excursions)
            const logElement = document.getElementById('recon-log');
            logElement.innerHTML = '';
            let excursionCount = 0;
            
            // Analyze the last 100 points of the visible set for anomalies
            const recentPoints = visiblePoints.slice(-100);
            for(let p of recentPoints) {{
                // Check distance from home base
                const dLat = (p.lat - homeLat) * Math.PI / 180;
                const dLon = (p.lon - homeLon) * Math.PI / 180;
                const distHome = 3958.8 * 2 * Math.atan2(Math.sqrt(Math.sin(dLat/2)**2 + Math.cos(homeLat*Math.PI/180)*Math.cos(p.lat*Math.PI/180)*Math.sin(dLon/2)**2), Math.sqrt(1-(Math.sin(dLat/2)**2 + Math.cos(homeLat*Math.PI/180)*Math.cos(p.lat*Math.PI/180)*Math.sin(dLon/2)**2)));
                
                if(distHome > 0.05) {{ // Escaped normal perimeter (> ~250ft)
                    excursionCount++;
                    const timeStr = new Date(p.time).toLocaleTimeString();
                    if(excursionCount < 10) {{
                        let target = "UNKNOWN";
                        if(p.lon > homeLon) target = "CRESTWOOD APPROACH";
                        if(p.lat < homeLat) target = "HILLSIDE APPROACH";
                        logElement.innerHTML += `<div>[${{timeStr}}] EXCURSION: ${{target}}</div>`;
                    }}
                }}
            }}
            if(excursionCount >= 10) {{
                logElement.innerHTML += `<div>...[+${{excursionCount-10}} sustained boundary breaches]</div>`;
            }}
            if(excursionCount === 0 && visiblePoints.length > 0) {{
                logElement.innerHTML = `<div>[${{new Date(visiblePoints[visiblePoints.length-1].time).toLocaleTimeString()}}] PERIMETER SECURE.</div>`;
            }}
        }}

        // Initialize Scrubber
        if(rawGpxPoints.length > 0) {{
            const slider = document.getElementById('time-slider');
            slider.max = rawGpxPoints.length;
            slider.value = rawGpxPoints.length;
            
            document.getElementById('start-time').innerText = new Date(rawGpxPoints[0].time).toLocaleDateString();
            document.getElementById('end-time').innerText = new Date(rawGpxPoints[rawGpxPoints.length-1].time).toLocaleDateString();

            slider.addEventListener('input', (e) => {{
                updateMap(e.target.value);
            }});

            updateMap(rawGpxPoints.length);
        }}
    </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding='utf-8') as f:
        f.write(html_template)
    print(f"Science Vessel Dashboard generated: {OUTPUT_HTML}")

def main():
    print("Initializing Gwen's Science Vessel Dashboard (Moda Aesthetic / Tracker Mode)...")
    gpx_points = parse_gpx_files()
    if not gpx_points:
        print("[WARNING] No GPX data found in HAILO_DROP or DATA_DIR.")
    
    petkit_data = load_json(PETKIT_JSON)
    throne_data = load_json(THRONE_JSON)
    
    generate_html(gpx_points, petkit_data, throne_data)
    print("Mission parameters complete.")

if __name__ == "__main__":
    main()
