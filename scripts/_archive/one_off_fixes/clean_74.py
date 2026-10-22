import os
import re

ROOT_DIR = "/home/james/stacklabs/"
EXTS = (".py", ".sh", ".md", ".json", ".txt", ".html", ".csv")

replacements = [
    (r'Pegasus \(\.74\)', 'Pi 5 (.74)'),
    (r'Pegasus \(Node \.74\)', 'Pi 5 (Node .74)'),
    (r'Pegasus \.74', 'Pi 5 .74'),
    (r'Node \.74 \(Pegasus[^)]*\)', 'Node .74 (Pi 5)'),
    (r'CI-PEGASUS", "Pegasus", "HARDWARE", "\.74"', 'CI-PI5", "Pi 5", "HARDWARE", ".74"'),
    (r'"Pegasus", data\.get\("node_74"\)', '"Pi 5", data.get("node_74")'),
    (r'Pegasus Dreadnought Terminal \(Node \.74\)', 'Pi 5 Terminal (Node .74)'),
]

for root, dirs, files in os.walk(ROOT_DIR):
    if any(skip in root for skip in [".venv", "node_modules", ".git", "chroma_db", "archives", "archive"]):
        continue
        
    for file in files:
        if not file.endswith(EXTS):
            continue
            
        path = os.path.join(root, file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except:
            continue
            
        if "74" in content and "Pegasus" in content:
            new_content = content
            for pattern, repl in replacements:
                new_content = re.sub(pattern, repl, new_content, flags=re.IGNORECASE)
                
            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {path}")
