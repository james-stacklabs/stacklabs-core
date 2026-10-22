import os

jsx_path = '/tmp/claude_deltas/wardy_console.jsx'
html_path = '/home/james/stacklabs/scripts/wardy_console.html'

with open(jsx_path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('import '):
        new_lines.append('const { useState, useEffect, useRef, useCallback } = React;\n')
    elif line.startswith('export default function WardyConsole()'):
        new_lines.append('function WardyConsole() {\n')
    else:
        new_lines.append(line)

jsx_content = "".join(new_lines)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wardy Console - FanStack God Mode</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body style="margin: 0; padding: 0; background: #08090d;">
    <div id="root"></div>
    <script type="text/babel">
{jsx_content}
ReactDOM.createRoot(document.getElementById('root')).render(<WardyConsole />);
    </script>
</body>
</html>
"""

with open(html_path, 'w') as f:
    f.write(html)
print("Created wardy_console.html successfully.")
