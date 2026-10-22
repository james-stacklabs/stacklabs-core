import os

def replace_port(directory, old_port, new_port):
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.log') or '.git' in root or '__pycache__' in root:
                continue
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                if old_port in content:
                    content = content.replace(old_port, new_port)
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(content)
                    print(f"Updated {path}")
            except Exception as e:
                pass

replace_port('/home/james/stacklabs/UAT', '8008', '8009')
replace_port('/home/james/stacklabs/SANDBOX', '8008', '8010')
