from flask import Flask, render_template_string, request, jsonify
import os
from google import genai
from google.genai import types

app = Flask(__name__)

PERSONAS_DIR = '/home/james/stacklabs/dna/agents/personas/'

# Load API Key
api_key = None
try:
    with open('/home/james/stacklabs/.env') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                api_key = line.strip().split('=', 1)[1]
                break
except Exception as e:
    print(f"Warning: Could not load API key: {e}")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sovereign Persona Responder</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #121212;
            color: #E0E0E0;
            margin: 0;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #FF5910; /* Mets Orange */
            margin-bottom: 1.5rem;
        }
        .container {
            width: 100%;
            max-width: 800px;
            background-color: #1E1E1E;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: bold;
            color: #A0A0A0;
        }
        textarea, select {
            width: 100%;
            padding: 0.75rem;
            background-color: #2D2D2D;
            border: 1px solid #404040;
            color: #FFF;
            border-radius: 4px;
            font-family: inherit;
            box-sizing: border-box;
        }
        textarea {
            resize: vertical;
            min-height: 150px;
        }
        button {
            background-color: #FF5910;
            color: white;
            border: none;
            padding: 1rem 2rem;
            font-size: 1.1rem;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
            width: 100%;
        }
        button:hover {
            background-color: #E04800;
        }
        button:disabled {
            background-color: #666;
            cursor: not-allowed;
        }
        #result-container {
            margin-top: 2rem;
            display: none;
        }
        #result-text {
            background-color: #2D2D2D;
            border-left: 4px solid #FF5910;
            padding: 1.5rem;
            font-size: 1.2rem;
            border-radius: 4px;
            white-space: pre-wrap;
        }
        .copy-btn {
            background-color: #333;
            margin-top: 1rem;
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
            width: auto;
        }
        .copy-btn:hover {
            background-color: #444;
        }
    </style>
</head>
<body>
    <h1>Sovereign Persona Responder</h1>
    <div class="container">
        <div class="form-group">
            <label for="persona">Select Attacking Persona:</label>
            <select id="persona">
                <option value="">Loading personas...</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="chat-input">Paste Wardy's Chat Context:</label>
            <textarea id="chat-input" placeholder="Paste the live chat or specific comment here..."></textarea>
        </div>

        <button id="generate-btn" onclick="generateResponse()">Generate Response</button>

        <div id="result-container">
            <label>Persona Response:</label>
            <div id="result-text"></div>
            <button class="copy-btn" onclick="copyToClipboard()">Copy to Clipboard</button>
        </div>
    </div>

    <script>
        // Load personas on load
        fetch('/api/personas')
            .then(res => res.json())
            .then(personas => {
                const select = document.getElementById('persona');
                select.innerHTML = '';
                personas.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p;
                    // Make it look pretty by replacing underscores and capitalizing
                    opt.textContent = p.replace('.md', '').split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                    select.appendChild(opt);
                });
            });

        async function generateResponse() {
            const persona = document.getElementById('persona').value;
            const chatContext = document.getElementById('chat-input').value;
            const btn = document.getElementById('generate-btn');
            const resultContainer = document.getElementById('result-container');
            const resultText = document.getElementById('result-text');

            if (!chatContext.trim()) {
                alert('Please paste some chat context first!');
                return;
            }

            btn.disabled = true;
            btn.textContent = 'Generating...';
            resultContainer.style.display = 'none';

            try {
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ persona, chat_context: chatContext })
                });
                
                const data = await res.json();
                if (data.error) throw new Error(data.error);

                resultText.textContent = data.response;
                resultContainer.style.display = 'block';
            } catch (err) {
                alert('Error generating response: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Generate Response';
            }
        }

        function copyToClipboard() {
            const text = document.getElementById('result-text').textContent;
            navigator.clipboard.writeText(text).then(() => {
                const btn = document.querySelector('.copy-btn');
                const origText = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(() => btn.textContent = origText, 2000);
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/personas', methods=['GET'])
def list_personas():
    try:
        files = [f for f in os.listdir(PERSONAS_DIR) if f.endswith('.md')]
        files.sort()
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    persona_file = data.get('persona')
    chat_context = data.get('chat_context')

    if not persona_file or not chat_context:
        return jsonify({"error": "Missing persona or chat context"}), 400

    persona_path = os.path.join(PERSONAS_DIR, persona_file)
    try:
        with open(persona_path, 'r') as f:
            persona_lore = f.read()
    except Exception as e:
        return jsonify({"error": f"Could not load persona lore: {e}"}), 500

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are acting as the persona described below. 
        
Persona Lore:
{persona_lore}

You are watching a live stream about the Mets. Here is the latest chat context you need to react to:
"{chat_context}"

Task: Write ONE single, highly punchy, character-accurate response to this chat. Do not use hashtags or emojis. Keep it STRICTLY UNDER 200 CHARACTERS. React directly to what was said in the chat context provided above."""

        res = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8
            )
        )
        return jsonify({"response": res.text.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=False)
