import os
import glob
import json
import time
from flask import Flask, send_from_directory, Response, jsonify

app = Flask(__name__, static_folder='/home/james/stacklabs/13_Bro_Decoder_UI')
BRAIN_DIR = '/home/james/.gemini/antigravity/brain'
OUTPUT_DIR = '/home/james/stacklabs/media_vault/05_Archive'

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

def parse_overview_log(file_path):
    """Generator that parses the raw JSON objects from an overview.txt file."""
    if not os.path.exists(file_path):
        return
        
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line.strip())
                
                # Extract User Prompts
                if data.get('source') == 'USER_EXPLICIT' and 'content' in data:
                    text = data['content']
                    # Try to extract just the <USER_REQUEST> part if present
                    if '<USER_REQUEST>' in text and '</USER_REQUEST>' in text:
                        text = text.split('<USER_REQUEST>')[1].split('</USER_REQUEST>')[0].strip()
                    else:
                        text = text.strip()
                        
                    if len(text) > 20: 
                        yield {"type": "data", "log_type": "prompt", "content": text}
                
                # Extract Model Implementation Plans or Artifact updates
                elif data.get('source') == 'MODEL' and 'tool_calls' in data:
                    for tool_call in data['tool_calls']:
                        func_name = tool_call.get('name')
                        if func_name in ['write_to_file', 'replace_file_content']:
                            args = tool_call.get('args', {})
                            
                            # Safely handle if args is a string (JSON string) or dict
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except json.JSONDecodeError:
                                    continue
                                    
                            target_file = args.get('TargetFile', '')
                            
                            # If it's an implementation plan
                            if 'implementation_plan.md' in target_file:
                                content = args.get('CodeContent', args.get('ReplacementContent', ''))
                                if content:
                                    snippet = content[:500] + "...\n[TRUNCATED FOR RAG EFFICIENCY]"
                                    yield {"type": "data", "log_type": "plan", "content": f"Implementation Plan Updated:\n{snippet}"}
                            
                            # If it's an architectural code edit
                            elif '/apiary/' in target_file and not any(x in target_file for x in ['node_modules', '.venv', '.git', 'scratch']):
                                desc = args.get('Description', 'Modified file.')
                                yield {"type": "data", "log_type": "file", "content": f"Edited: {os.path.basename(target_file)}\nContext: {desc}"}

            except json.JSONDecodeError:
                continue

@app.route('/api/stream_history')
def stream_history():
    def generate():
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        master_payload = []
        
        session_folders = sorted(glob.glob(os.path.join(BRAIN_DIR, '*')))
        
        for folder in session_folders:
            if not os.path.isdir(folder): continue
            
            session_id = os.path.basename(folder)
            overview_path = os.path.join(folder, '.system_generated', 'logs', 'overview.txt')
            
            if os.path.exists(overview_path):
                # Notify UI of progress
                yield f"data: {json.dumps({'type': 'progress', 'session_id': session_id})}\n\n"
                
                # Notify UI we are entering a new session
                yield f"data: {json.dumps({'type': 'data', 'log_type': 'session', 'session_id': session_id})}\n\n"
                
                master_payload.append(f"\n\n======================================\nSESSION: {session_id}\n======================================\n")
                
                for item in parse_overview_log(overview_path):
                    # Stream to UI
                    yield f"data: {json.dumps(item)}\n\n"
                    # Append to master text payload
                    prefix = f"[{item['log_type'].upper()}] "
                    master_payload.append(prefix + item['content'])
                    
                    # Small delay so the user can actually read the Matrix stream
                    time.sleep(0.05)
                    
        # Write the final artifact
        final_file = os.path.join(OUTPUT_DIR, 'BRO_DECODER_RAW_HISTORY.md')
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write("# SOVEREIGN OS: OMNISCIENT RAG MATRIX\n")
            f.write("Generated by the Bro-Decoder IDE Crawler.\n\n")
            f.write("\n\n".join(master_payload))
            
        yield f"data: {json.dumps({'type': 'complete', 'file': final_file})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("🚀 Bro-Decoder UI Portal active on Port 8085")
    app.run(host='0.0.0.0', port=8085, threaded=True)
