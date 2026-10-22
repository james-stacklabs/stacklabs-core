import json
import os
import sys
import time
import base64
import uuid
import datetime
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

CMDB_FILE = '04_Sovereign_Core/sovereign_cmdb.json'
PORT = 8082

# Utility to get cmdb_core
def get_cmdb():
    cmdb_path = os.path.dirname(__file__)
    if cmdb_path not in sys.path:
        sys.path.append(cmdb_path)
    import cmdb_core
    return cmdb_core.cmdb

class CMDBRequestHandler(SimpleHTTPRequestHandler):
    
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Connection', 'close')
        res = json.dumps(data).encode('utf-8')
        self.send_header('Content-Length', str(len(res)))
        self.end_headers()
        self.wfile.write(res)
        
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)

        if path == '/api/pipeline':
            def get_cnt(p):
                return len(os.listdir(p)) if os.path.exists(p) else 0
            def tail(p):
                try:
                    with open(p, 'r') as f:
                        return f.readlines()[-15:]
                except:
                    return ["[LOG UNAVAILABLE]"]
            
            dd_cnt = get_cnt('/home/james/stacklabs/staging/dead_drop')
            hailo_cnt = get_cnt('/home/james/stacklabs/dna/media/hailo_dropzone')
            quar_cnt = get_cnt('/home/james/stacklabs/staging/quarantine')
            
            dd_logs = tail('/home/james/stacklabs/staging/dead_drop.log')
            hc_logs = tail('/home/james/stacklabs/staging/hailo_crush.log')
            
            return self.send_json_response({
                "counts": {"dead_drop": dd_cnt, "hailo": hailo_cnt, "quarantine": quar_cnt},
                "logs": {"dead_drop": dd_logs, "hailo": hc_logs}
            })

        # ---------------------------------------------------------------------
        # API: /api/status (New)
        # ---------------------------------------------------------------------
        elif path == '/api/status':
            try:
                # Calculate pseudo metrics for S-Value
                # For now, return hardcoded stable baseline as per spec
                data = {
                    "s_value": 1.0000,
                    "temp": "31.2°C",
                    "throttle": "0x0",
                    "uptime": "99.9%",
                    "ghost_drive_pct": "1%"
                }
                return self.send_json_response(data)
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)

        # ---------------------------------------------------------------------
        # API: /api/tickets (New)
        # ---------------------------------------------------------------------
        elif path == '/api/tickets':
            try:
                cmdb = get_cmdb()
                sql = "SELECT * FROM sdlc_tickets"
                params = []
                
                status_filter = query.get('status', [None])[0]
                if status_filter:
                    sql += " WHERE status = ?"
                    params.append(status_filter)
                    
                limit = query.get('limit', [None])[0]
                if limit and limit.isdigit():
                    sql += " LIMIT ?"
                    params.append(int(limit))
                
                cursor = cmdb.conn.cursor()
                cursor.row_factory = __import__('sqlite3').Row
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                tickets = [dict(r) for r in rows]
                
                return self.send_json_response(tickets)
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)

        # ---------------------------------------------------------------------
        # API: /api/nodes (New)
        # ---------------------------------------------------------------------
        elif path == '/api/nodes':
            try:
                cmdb = get_cmdb()
                sql = "SELECT * FROM fleet_nodes"
                params = []
                
                exclude_filter = query.get('exclude', [None])[0]
                if exclude_filter == 'CI-AMZN':
                    sql += " WHERE node_id NOT LIKE 'CI-AMZN-%'"
                    
                cursor = cmdb.conn.cursor()
                cursor.row_factory = __import__('sqlite3').Row
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                nodes = [dict(r) for r in rows]
                
                return self.send_json_response(nodes)
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)

        # ---------------------------------------------------------------------
        # API: /api/cmdb (Legacy Monolithic Blob)
        # ---------------------------------------------------------------------
        elif path == '/api/cmdb':
            try:
                cmdb = get_cmdb()
                nodes = cmdb.get_all_nodes()
                tickets = cmdb.get_all_tickets()
                
                formatted_cis = []
                for n in nodes:
                    formatted_cis.append({
                        "id": n["node_id"],
                        "name": n["hardware"],
                        "status": n["status"],
                        "attributes": {"role": n["agent_class"]}
                    })
                    
                formatted_tickets = []
                for t in tickets:
                    formatted_tickets.append({
                        "id": t["ticket_id"],
                        "title": t["title"],
                        "status": t["status"],
                        "ci_link": t["ci_id"],
                        "data": t["description"]
                    })
                    
                response_data = {
                    "Environment": {
                        "global_status": "S=(A*Pw*T*C)*Pi",
                        "chindogu_level": 10.0
                    },
                    "Configuration_Items": formatted_cis,
                    "Tickets": formatted_tickets
                }
                return self.send_json_response(response_data)
            except Exception as e:
                return self.send_json_response({"Configuration_Items": [], "Tickets": []}, 500)
        
        # ---------------------------------------------------------------------
        # File Serving Fallback
        # ---------------------------------------------------------------------
        elif self.path == '/cmdb_admin.html':
            self.path = '/04_Sovereign_Core/cmdb_admin.html'
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # ---------------------------------------------------------------------
        # API: /api/tickets (New)
        # ---------------------------------------------------------------------
        if path == '/api/tickets':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return self.send_json_response({"error": "Empty body"}, 400)
                
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                cmdb = get_cmdb()
                
                title = data.get('title', 'New Ticket')
                priority = data.get('priority', 'Low')
                ci_id = data.get('ci_id', '')
                description = data.get('description', '')
                
                # Generate new ticket ID
                ticket_id = f"INC-{int(time.time())}-{str(uuid.uuid4()).split('-')[0].upper()[:4]}"
                
                cursor = cmdb.conn.cursor()
                cursor.execute('''
                    INSERT INTO sdlc_tickets (ticket_id, ci_id, title, description, priority, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (ticket_id, ci_id, title, description, priority, 'TODO', datetime.datetime.now().isoformat()))
                cmdb.conn.commit()
                
                return self.send_json_response({"status": "success", "ticket_id": ticket_id})
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)

        # ---------------------------------------------------------------------
        # API: /api/cmdb/save (Legacy Monolithic Blob)
        # ---------------------------------------------------------------------
        elif path == '/api/cmdb/save':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return self.send_json_response({"error": "Empty body"}, 400)
                
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                new_data = json.loads(post_data)
                cmdb = get_cmdb()
                
                # Update Fleet Nodes
                for ci in new_data.get("Configuration_Items", []):
                    cmdb.register_node(
                        node_id=ci.get("id", "UNKNOWN"),
                        hardware=ci.get("name", "Unknown Hardware"),
                        agent_class=ci.get("attributes", {}).get("role", "Node"),
                        status=ci.get("status", "OFFLINE"),
                        primary_directives=[],
                        manifest_path=""
                    )
                
                # Update Tickets
                for t in new_data.get("Tickets", []):
                    cursor = cmdb.conn.cursor()
                    cursor.execute('''
                        UPDATE sdlc_tickets 
                        SET ci_id=?, title=?, description=?, priority=?, status=?
                        WHERE ticket_id=?
                    ''', (
                        t.get("ci_link", "N/A"),
                        t.get("title", "Updated Ticket"),
                        t.get("data", ""),
                        t.get("priority", "Low"),
                        t.get("status", "Open"),
                        t.get("id")
                    ))
                    
                    if cursor.rowcount == 0:
                        cursor.execute('''
                            INSERT INTO sdlc_tickets (ticket_id, ci_id, title, description, priority, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            t.get("id"),
                            t.get("ci_link", "N/A"),
                            t.get("title", "Updated Ticket"),
                            t.get("data", ""),
                            t.get("priority", "Low"),
                            t.get("status", "Open"),
                            t.get("timestamp", datetime.datetime.now().isoformat())
                        ))
                cmdb.conn.commit()
                return self.send_json_response({"status": "success", "message": "SQLite Overwrite Complete"})
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)
                
        # ---------------------------------------------------------------------
        # API: /api/cmdb/friction
        # ---------------------------------------------------------------------
        elif path == '/api/cmdb/friction':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                cmdb = get_cmdb()
                cursor = cmdb.conn.cursor()
                cursor.execute('UPDATE fleet_nodes SET friction_level=? WHERE node_id=?',
                               (data.get('friction_level', 1.0), data.get('ci', 'Node.73')))
                cmdb.conn.commit()
                return self.send_json_response({"status": "success"})
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)

        # ---------------------------------------------------------------------
        # API: /api/cortex/log (New)
        # ---------------------------------------------------------------------
        elif path == '/api/cortex/log':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                cmdb = get_cmdb()
                
                event_type = data.get('event_type', 'CORTEX_LOG')
                source_node = data.get('source_node', 'MISTRAL')
                payload = data.get('payload', {})
                
                event_id = cmdb.log_event(event_type, source_node, payload)
                return self.send_json_response({"status": "success", "event_id": event_id})
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)

        # ---------------------------------------------------------------------
        # API: /api/cortex/export (New)
        # ---------------------------------------------------------------------
        elif path == '/api/cortex/export':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                content = data.get('content', '')
                filename = data.get('filename', f"mistral_session_{int(time.time())}.md")
                
                # Check for absolute path injection
                if '..' in filename or filename.startswith('/'):
                    return self.send_json_response({"error": "Invalid filename"}, 400)
                
                export_dir = "/home/james/stacklabs/dna/agents/MISTRAL/active_sessions/"
                os.makedirs(export_dir, exist_ok=True)
                
                full_path = os.path.join(export_dir, filename)
                with open(full_path, 'w') as f:
                    f.write(content)
                    
                return self.send_json_response({"status": "success", "filename": filename, "path": full_path})
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)

        # ---------------------------------------------------------------------
        # API: /api/cmdb/attach (NEW: Physical Payload Ingestion)
        # ---------------------------------------------------------------------
        elif path == '/api/cmdb/attach':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                target_id = data.get('target_id', f"unknown_{int(time.time())}")
                filename = data.get('filename', "attachment.bin")
                b64_data = data.get('base64_data', "")
                
                # Extract raw base64 if it has dataURL prefix
                if "," in b64_data:
                    raw_b64 = b64_data.split(",")[1]
                else:
                    raw_b64 = b64_data

                # Sanitize filename path traversal
                if '..' in filename or filename.startswith('/'):
                    filename = filename.replace('/', '_').replace('..', '_')

                # Hardcoded architectural path for physical CI attachment payloads
                save_dir = "/home/james/stacklabs/dna/ci/attachments"
                os.makedirs(save_dir, exist_ok=True)
                
                # Make names structurally explicit to prevent overwrite collisions
                safe_name = f"{target_id}_{int(time.time())}_{filename}"
                full_path = os.path.join(save_dir, safe_name)
                
                with open(full_path, "wb") as f:
                    f.write(base64.b64decode(raw_b64))

                return self.send_json_response({"status": "success", "file_path": full_path})
            except Exception as e:
                return self.send_json_response({"error": str(e)}, 500)

        else:
            self.send_error(404)

    def do_PATCH(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return self.send_json_response({"error": "Empty body"}, 400)
            
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data)
            cmdb = get_cmdb()
            cursor = cmdb.conn.cursor()
            
            # API: /api/tickets/{ticket_id}
            if path.startswith('/api/tickets/'):
                ticket_id = path.split('/')[-1]
                
                # Build dynamic update query based on provided fields
                update_fields = []
                params = []
                allowed_fields = ['title', 'description', 'priority', 'status', 'ci_id']
                
                for field in allowed_fields:
                    if field in data:
                        update_fields.append(f"{field}=?")
                        params.append(data[field])
                        
                if not update_fields:
                    return self.send_json_response({"error": "No valid fields to update"}, 400)
                    
                params.append(ticket_id)
                sql = f"UPDATE sdlc_tickets SET {', '.join(update_fields)} WHERE ticket_id=?"
                
                cursor.execute(sql, params)
                cmdb.conn.commit()
                
                return self.send_json_response({"status": "success", "updated_rows": cursor.rowcount})
                
            # API: /api/nodes/{node_id}
            elif path.startswith('/api/nodes/'):
                node_id = path.split('/')[-1]
                
                update_fields = []
                params = []
                allowed_fields = ['hardware', 'agent_class', 'status']
                
                for field in allowed_fields:
                    if field in data:
                        update_fields.append(f"{field}=?")
                        params.append(data[field])
                        
                if not update_fields:
                    return self.send_json_response({"error": "No valid fields to update"}, 400)
                    
                params.append(node_id)
                sql = f"UPDATE fleet_nodes SET {', '.join(update_fields)} WHERE node_id=?"
                
                cursor.execute(sql, params)
                cmdb.conn.commit()
                
                return self.send_json_response({"status": "success", "updated_rows": cursor.rowcount})
                
            else:
                self.send_error(404)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return self.send_json_response({"error": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, POST, PATCH')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()

if __name__ == '__main__':
    server_address = ('0.0.0.0', PORT)
    httpd = ThreadingHTTPServer(server_address, CMDBRequestHandler)
    print(f"[+] Sovereign CMDB Backend API Running.")
    print(f"[+] Access the Admin Dashboard at: http://clio.taila01894.ts.net:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] CMDB API Offline.")
        httpd.server_close()
