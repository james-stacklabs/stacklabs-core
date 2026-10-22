import sqlite3
import json

DB_PATH = '/home/james/stacklabs/dna/sovereign_now.db'

def generate_ui():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('SELECT sys_id, user_name, title, introduction FROM sys_user')
    users = cur.fetchall()
    con.close()
    
    users_json = json.dumps([{"sys_id": u[0], "username": u[1], "title": u[2], "intro": u[3]} for u in users])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Persona Audit</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white p-8">
        <h1 class="text-3xl font-bold mb-8">Persona Audit: Missing Media Assets</h1>
        <div id="app" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"></div>
        <script>
            const users = {users_json};
            const app = document.getElementById('app');
            users.forEach(u => {{
                app.innerHTML += `
                    <div class="bg-gray-800 p-6 rounded-lg border border-gray-700">
                        <h2 class="text-xl font-bold mb-2">${{u.username}}</h2>
                        <p class="text-sm text-gray-400 mb-4">${{u.title}}</p>
                        <textarea class="w-full h-32 bg-gray-700 text-white p-2 rounded mb-4">${{u.intro || ''}}</textarea>
                        <button class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Save</button>
                    </div>
                `;
            }});
        </script>
    </body>
    </html>
    """
    with open('/home/james/stacklabs/01_Sovereign_Portal/public/persona_audit.html', 'w') as f:
        f.write(html)

generate_ui()
