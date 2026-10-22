import socket
import json
import threading
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

import subprocess
import re

def get_active_ips():
    try:
        output = subprocess.check_output(['arp', '-an']).decode()
        # Find all IPs like (192.168.x.x)
        ips = re.findall(r'\((192\.168\.\d+\.\d+)\)', output)
        return list(set(ips))
    except:
        # Fallback to broad sweep if ARP fails
        return [f"192.168.1.{i}" for i in range(1, 255)]

GOVEE_IPS = get_active_ips()
GOVEE_PORT = 40033

def fire_udp_to_govee(color):
    """Sends a color command to all 8 Govee nodes simultaneously (The 'You Got Mail' sweep)."""
    msg = {
        "msg": {
            "cmd": "colorwc",
            "data": {
                "color": color,
                "colorTemInKelvin": 0
            }
        }
    }
    
    payload = json.dumps(msg).encode('utf-8')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Broadcast to all 8 IPs
    for ip in GOVEE_IPS:
        try:
            sock.sendto(payload, (ip, GOVEE_PORT))
            print(f"[UDP] Fired {color} to Node {ip}")
        except Exception as e:
            print(f"[UDP] Failed to fire to Node {ip}: {e}")
            
    sock.close()

@app.route('/')
def index():
    # Serve the Vesper UI directly
    html_path = os.path.join(os.path.dirname(__file__), 'fanstack_plie_dvr.html')
    return send_file(html_path)

@app.route('/api/govee/trigger', methods=['POST'])
def handle_govee_trigger():
    data = request.json
    event_type = data.get('event_type', 'default')
    
    print(f"\n[DVR SERVER] Received ROM Trigger Event: {event_type}")
    
    # Define our colors
    # New York Mets: Orange (#FF5500) and Blue (#0055FF)
    
    if event_type == "strikeout":
        color = {"r": 255, "g": 0, "b": 0} # Red
    elif event_type == "wild_pitch":
        color = {"r": 255, "g": 255, "b": 255} # Flash White
    elif event_type == "error":
        color = {"r": 255, "g": 85, "b": 0} # Mets Orange!
    elif event_type == "hit":
        color = {"r": 0, "g": 85, "b": 255} # Mets Blue
    else:
        color = {"r": 0, "g": 255, "b": 0} # Default Green

    # Run in thread so API doesn't block
    t = threading.Thread(target=fire_udp_to_govee, args=(color,))
    t.start()
    
    return jsonify({"status": "UDP Sweep Dispatched", "nodes": len(GOVEE_IPS)}), 200

# Route to serve the MP4 without CORS issues
@app.route('/media/<path:filename>')
def serve_media(filename):
    media_dir = '/home/james/stacklabs/dna/media/hailo_dropzone'
    return send_file(os.path.join(media_dir, filename))

if __name__ == '__main__':
    print("[SYS] Booting FanStack DVR Engine on Port 5058...")
    print(f"[SYS] Tracking 8 Govee Hardware Nodes via UDP.")
    app.run(host='0.0.0.0', port=5058)
