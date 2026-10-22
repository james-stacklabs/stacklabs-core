import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv('/home/james/stacklabs/.env')

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

try:
    for model in client.models.list_models():
        if "imagen" in model.name.lower() or "image" in model.name.lower():
            print(f"Found model: {model.name}")
except Exception as e:
    print(f"Error listing models: {e}")
