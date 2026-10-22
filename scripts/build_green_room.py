import os

jsx_path = '/home/james/stacklabs/scripts/fanstack_green_room.jsx'
html_path = '/home/james/stacklabs/scripts/green_room.html'

with open(jsx_path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('import '):
        new_lines.append('const { useState, useRef, useCallback } = React;\n')
    elif line.startswith('export default function GreenRoom()'):
        new_lines.append('function GreenRoom() {\n')
    else:
        new_lines.append(line)

jsx_content = "".join(new_lines)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Green Room Configuration</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body style="margin: 0; padding: 0; background: #08090d;">
    <div id="root"></div>
    <script type="text/babel">
{jsx_content}
ReactDOM.createRoot(document.getElementById('root')).render(<GreenRoom />);
    </script>
</body>
</html>
"""

with open(html_path, 'w') as f:
    f.write(html)
print("Created green_room.html successfully.")
