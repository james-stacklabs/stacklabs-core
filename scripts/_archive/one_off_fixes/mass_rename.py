import os

TARGET_DIR = "/home/james/stacklabs"
OLD_STR = "SovereignOS"
NEW_STR = "SovereignOS"

EXTENSIONS = ('.py', '.sh', '.json', '.md', '.js', '.ts', '.tsx', '.env', '.html', '.css', '.txt')

def mass_replace():
    count = 0
    for root, dirs, files in os.walk(TARGET_DIR):
        # Skip node_modules, .git, .venv, etc.
        dirs[:] = [d for d in dirs if d not in ('.git', '.venv', 'node_modules', '__pycache__')]
        for file in files:
            if file.endswith(EXTENSIONS):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if OLD_STR in content:
                        new_content = content.replace(OLD_STR, NEW_STR)
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        count += 1
                        print(f"Updated: {path}")
                except Exception as e:
                    print(f"Failed to read/write {path}: {e}")
    print(f"Mass replace complete. Updated {count} files.")

if __name__ == "__main__":
    mass_replace()
