import os
import glob

image_dir = "/home/james/stacklabs/dna/media/character_maps"
html_output = "/home/james/stacklabs/08_FanStack/fanstack_character_blueprint.html"

extensions = ["*.png", "*.jpg", "*.jpeg", "*.webp"]
images = []
for ext in extensions:
    images.extend(glob.glob(os.path.join(image_dir, ext)))

images.sort()

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FanStack Cosmos - Master Character Blueprint</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --vm-deep-void: #0f1115;
            --vm-cyan: #00f2fe;
            --vm-border: #1e293b;
            --vm-text: #e2e8f0;
        }
        body {
            background-color: var(--vm-deep-void);
            color: var(--vm-text);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 2rem;
        }
        h1 {
            text-align: center;
            color: var(--vm-cyan);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 2rem;
            text-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        .vm-panel-glass {
            background: rgba(15, 17, 21, 0.6);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid var(--vm-border);
            border-radius: 12px;
            padding: 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
        .vm-panel-glass:hover {
            border-color: var(--vm-cyan);
            box-shadow: 0 0 15px rgba(0, 242, 254, 0.2);
            transform: translateY(-2px);
        }
        .persona-name {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-align: center;
            color: var(--vm-cyan);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .img-container {
            width: 100%;
            aspect-ratio: 1 / 1;
            overflow: hidden;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .img-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }
        .vm-panel-glass:hover .img-container img {
            transform: scale(1.05);
        }
    </style>
</head>
<body>
    <h1>FanStack Cosmos M.A.R.D. Roster</h1>
    <div class="grid">
"""

for img_path in images:
    filename = os.path.basename(img_path)
    persona_name = os.path.splitext(filename)[0].replace("_", " ").title()
    rel_path = f"../dna/media/character_maps/{filename}"
    
    html_content += f"""
        <div class="vm-panel-glass">
            <div class="persona-name">{persona_name}</div>
            <div class="img-container">
                <img src="{rel_path}" alt="{persona_name}" loading="lazy">
            </div>
        </div>
"""

html_content += """
    </div>
</body>
</html>
"""

os.makedirs(os.path.dirname(html_output), exist_ok=True)
with open(html_output, 'w') as f:
    f.write(html_content)
