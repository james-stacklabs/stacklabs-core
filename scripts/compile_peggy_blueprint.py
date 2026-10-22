import os
import glob

PEGGY_DIR = "/home/james/stacklabs/dna/agents/PEGGY/"
OUT_FILE = "/home/james/stacklabs/peggy_character_blueprint.html"
EXTENSIONS = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif"]

def gather_images():
    images = []
    if os.path.exists(PEGGY_DIR):
        for ext in EXTENSIONS:
            images.extend(glob.glob(os.path.join(PEGGY_DIR, ext)))
            images.extend(glob.glob(os.path.join(PEGGY_DIR, ext.upper())))
    return sorted(list(set(images)))

def generate_html(images):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PEGGY MASTER CHARACTER BLUEPRINT</title>
    <style>
        body { 
            background-color: #0f1115; 
            color: #e2e8f0; 
            font-family: monospace; 
            margin: 0; 
            padding: 40px; 
        }
        h1.main-title { 
            color: #38bdf8; 
            text-transform: uppercase; 
            letter-spacing: 0.2em; 
            border-bottom: 2px solid #1e293b; 
            padding-bottom: 10px; 
            margin-bottom: 40px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 30px;
        }
        .card {
            background-color: #1e293b;
            border: 1px solid #334155;
            padding: 15px;
            display: flex;
            flex-direction: column;
        }
        .card-header {
            color: #38bdf8;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 15px;
            border-bottom: 1px solid #334155;
            padding-bottom: 8px;
            word-wrap: break-word;
        }
        .card img {
            max-width: 100%;
            height: auto;
            border: 1px solid #0f1115;
            flex-grow: 1;
            object-fit: cover;
        }
        .empty-state {
            color: #ef4444;
            font-size: 14px;
            margin-top: 20px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
    </style>
</head>
<body>
    <h1 class="main-title">PEGGY \\ MASTER CHARACTER BLUEPRINT</h1>
    <div class="grid">
"""
    
    if not images:
        html += '<p class="empty-state">NO VISUAL ARTIFACTS FOUND IN ROOT DIRECTORY.</p>'
        
    for path in images:
        filename = os.path.basename(path)
        # Use relative pathing so the browser can serve it via port 8000 which is hosted at apiary
        # APIARY_ROOT is /home/james/stacklabs/
        relative_path = os.path.relpath(path, "/home/james/stacklabs/")
        html += f"""
        <div class="card">
            <div class="card-header">{filename}</div>
            <img src="{relative_path}" alt="{filename}" loading="lazy" />
        </div>
        """
        
    html += """
    </div>
</body>
</html>
"""
    return html

if __name__ == "__main__":
    images = gather_images()
    print(f"[PEGGY BLUEPRINT] Found {len(images)} valid visual artifacts.")
    
    html_content = generate_html(images)
    
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"[PEGGY BLUEPRINT] Successfully forged to: {OUT_FILE}")
