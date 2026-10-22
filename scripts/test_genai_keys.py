import os
import dotenv
from google import genai

dotenv.load_dotenv("/home/james/stacklabs/.env")

g_key = os.environ.get("GEMINI_API_KEY")
v_key = os.environ.get("VERTEX_API_KEY")

print(f"Testing GEMINI_API_KEY ({g_key[:8]}...)...")
try:
    client_g = genai.Client(api_key=g_key)
    res_g = client_g.models.generate_content(
        model="gemini-3.8-flash",
        contents="Give a 1-sentence Subway series baseball prediction."
    )
    print("SUCCESS GEMINI_API_KEY (gemini-3.8-flash):", res_g.text)
except Exception as e:
    print("FAIL GEMINI_API_KEY (gemini-3.8-flash):", e)

try:
    res_g_lite = client_g.models.generate_content(
        model="gemini-3.8-pro",
        contents="Give a 1-sentence Subway series baseball prediction."
    )
    print("SUCCESS GEMINI_API_KEY (3.8-pro):", res_g_lite.text)
except Exception as e:
    print("FAIL GEMINI_API_KEY (3.8-pro):", e)

print(f"\nTesting VERTEX_API_KEY ({v_key[:8] if v_key else 'None'}...)...")
if v_key:
    try:
        client_v = genai.Client(vertexai=True, api_key=v_key)
        res_v = client_v.models.generate_content(
            model="gemini-3.8-flash",
            contents="Say hello"
        )
        print("SUCCESS VERTEX_API_KEY:", res_v.text)
    except Exception as e:
        print("FAIL VERTEX_API_KEY:", e)
