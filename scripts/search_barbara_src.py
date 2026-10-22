import os

ignore_dirs = {'.git', 'node_modules', 'dist', 'media_vault', '.next'}
ignore_exts = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.db', '.pyc'}

for root, dirs, files in os.walk("/home/james/stacklabs"):
    # modify dirs in place to ignore specific directories
    dirs[:] = [d for d in dirs if d not in ignore_dirs]
    for file in files:
        if any(file.endswith(ext) for ext in ignore_exts):
            continue
        path = os.path.join(root, file)
        try:
            with open(path, 'r', errors='ignore') as f:
                content = f.read()
                if 'barbara' in content.lower():
                    print(f"Found in {path}")
        except Exception as e:
            pass

for root, dirs, files in os.walk("/home/james/sovereign_inbox"):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]
    for file in files:
        if any(file.endswith(ext) for ext in ignore_exts):
            continue
        path = os.path.join(root, file)
        try:
            with open(path, 'r', errors='ignore') as f:
                content = f.read()
                if 'barbara' in content.lower():
                    print(f"Found in {path}")
        except Exception as e:
            pass
