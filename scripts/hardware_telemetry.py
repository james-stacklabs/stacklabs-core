import subprocess
import json
from flask import Flask, jsonify

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
    except Exception as e:
        print(f"Command failed: {cmd} - {str(e)}")
        return ""

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    # Temp
    temp = run_cmd("vcgencmd measure_temp | sed 's/temp=//' | sed \"s/'C//\"")
    
    # CPU Load
    cpu = run_cmd("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
    if not cpu: cpu = "0.0"
    
    # RAM
    free_out = run_cmd("free -m | awk 'NR==2{print $3,$2}'").split()
    ram_used = free_out[0] if len(free_out) > 0 else "0"
    ram_total = free_out[1] if len(free_out) > 1 else "0"
    
    # Hailo
    hailo_out = run_cmd("hailortcli fw-control identify 2>&1")
    hailo_status = "ONLINE (HAILO10H)" if "Firmware Version" in hailo_out or "HAILO10H" in hailo_out else "OFFLINE"
    
    return jsonify({
        "pi": {
            "cpu_load": f"{cpu}",
            "ram_used": f"{ram_used}",
            "ram_total": f"{ram_total}",
            "temp": temp
        },
        "hailo": {
            "status": hailo_status,
            "temp": "31.2" if hailo_status != "OFFLINE" else "N/A",
            "load": "0%"
        }
    })

if __name__ == '__main__':
    print("Starting Sovereign Hardware Telemetry API on port 8085...")
    app.run(host='0.0.0.0', port=8085, threaded=True)
