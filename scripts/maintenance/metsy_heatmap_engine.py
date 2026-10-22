import json
import xml.etree.ElementTree as ET
from datetime import datetime
import os

# PATH CONFIGURATIONS
GPX_PATH = "/home/james/stacklabs/04_Sovereign_Core/Historical_Archive/metsy_tractive_history.gpx"
PETKIT_PATH = "/home/james/stacklabs/04_Sovereign_Core/Historical_Archive/petkit_history.json"
OUTPUT_HTML = "/home/james/stacklabs/metsy_heatmap.html"

def parse_gpx(file_path):
    print(f"Parsing GPX: {{file_path}}...")
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {{'gpx': 'http://www.topografix.com/GPX/1/1'}}
    points = []
    for trk in root.findall('gpx:trk', ns):
        for trkseg in trk.findall('gpx:trkseg', ns):
            for trkpt in trkseg.findall('gpx:trkpt', ns):
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                time_elt = trkpt.find('gpx:time', ns)
                if time_elt is not None:
                    time_str = time_elt.text
                    dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
                    points.append({{'lat': lat, 'lon': lon, 'time': dt}})
    return points

def parse_petkit(file_path):
    print(f"Parsing Petkit: {{file_path}}...")
    with open(file_path, 'r') as f:
        data = json.load(f)
    events = []
    for kit_id in data:
        records = data[kit_id].get('history_records', [])
        for record in records:
            if record.get('petName') == 'Metsy':
                ts = record.get('timestamp')
                weight = record.get('content', {{}}).get('petWeight')
                dt = datetime.fromtimestamp(ts)
                events.append({{'time': dt, 'weight': weight}})
    return events

def generate_heatmap_html(points, petkit_data):
    # Process GPX points into list of [lat, lon, intensity]
    heat_data = [[p['lat'], p['lon'], 0.5] for p in points]
    
    # Process Petkit markers
    markers = []
    for event in petkit_data:
        markers.append({{
            "lat": 33.885107, 
            "lon": -84.530763, 
            "label": f"Petkit Event: {{event['time'].strftime('%m/%d %H:%M')}} - Weight: {{event['weight']}}g"
        }})

    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Metsy Behavioral Heatmap // Sigma-9</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script src="https://leaflet.github.io/Leaflet.heat/dist/leaflet-heat.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background: #050505; color: #002D72; font-family: 'Courier New', Courier, monospace; overflow: hidden; }}
        #map {{ height: 100vh; width: 100vw; }}
        .header {{ position: absolute; top: 10px; left: 50px; z-index: 1000; background: rgba(0, 45, 114, 0.9); padding: 15px; border-left: 5px solid #FF5910; box-shadow: 0 0 15px rgba(255, 89, 16, 0.5); }}
        .header h1 {{ margin: 0; font-size: 20px; color: #FF5910; letter-spacing: 2px; }}
        .header p {{ margin: 5px 0 0 0; color: #fff; font-size: 11px; text-transform: uppercase; }}
        .stats {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.2); }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SCIENCE VESSEL SIGMA-9 // BEHAVIORAL MESH</h1>
        <p>Target: Metsy (Node .171)</p>
        <p>S = 1.0000 // TOPOGRAPHICAL AUDIT</p>
        <div class="stats">
            <p>GPS Points: {{len(points)}}</p>
            <p>Bio-Events: {{len(petkit_data)}}</p>
        </div>
    </div>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([33.885107, -84.530763], 18);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png', {{
            maxZoom: 20,
            attribution: '&copy; CartoDB &copy; OpenStreetMap contributors'
        }}).addTo(map);

        var points = {json.dumps(heat_data)};
        var heat = L.heatLayer(points, {{
            radius: 15,
            blur: 10,
            maxZoom: 18,
            gradient: {{0.4: '#002D72', 0.6: '#0055A4', 0.8: '#FF5910', 1.0: '#FFFFFF'}}
        }}).addTo(map);

        var markers = {json.dumps(markers)};
        markers.forEach(function(m) {{
            L.circleMarker([m.lat, m.lon], {{ 
                color: '#FF5910', 
                fillColor: '#FF5910', 
                fillOpacity: 0.8, 
                radius: 4 
            }}).addTo(map).bindPopup(m.label);
        }});
    </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html_template)
    print(f"Sigma-9 Topographical Heatmap generated: {{OUTPUT_HTML}}")

if __name__ == "__main__":
    if os.path.exists(GPX_PATH) and os.path.exists(PETKIT_PATH):
        gpx_points = parse_gpx(GPX_PATH)
        petkit_events = parse_petkit(PETKIT_PATH)
        generate_heatmap_html(gpx_points, petkit_events)
    else:
        print("Error: Files not found. System check required.")
