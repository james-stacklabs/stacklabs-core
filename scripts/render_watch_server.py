import os
import glob
from flask import Flask, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder='/home/james/stacklabs/dna/archives/uat_evidence', static_url_path='/frames')
CORS(app)

@app.route('/render-watch')
def render_watch():
    return send_file('/home/james/stacklabs/dna/render_watch.html')

@app.route('/api/status')
def status():
    # Poll directly from SD Card workspace
    lindor = len(glob.glob('/home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_LINDOR_*.png'))
    pickoff = len(glob.glob('/home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_PICKOFF_*.png'))
    gorman = len(glob.glob('/home/james/stacklabs/dna/archives/uat_evidence/EXHIBIT_GORMAN_*.png'))
    
    return jsonify({
        'lindor': lindor,
        'pickoff': pickoff,
        'gorman': gorman
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
