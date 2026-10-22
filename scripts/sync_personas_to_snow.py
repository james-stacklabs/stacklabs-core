import os
import json
import requests
from requests.auth import HTTPBasicAuth

CRED_PATH = "/home/james/stacklabs/dna/vault/sn_credentials.json"
PERSONAS_JSON_PATH = "/home/james/stacklabs/01_Sovereign_Portal/public/personas.json"
LORE_DIR = "/home/james/stacklabs/dna/agents/personas"

def main():
    if not os.path.exists(CRED_PATH):
        print("[!] Credentials missing.")
        return

    with open(CRED_PATH, "r") as f:
        creds = json.load(f)

    base_url = f"https://{creds['instance']}.service-now.com/api/now/table"
    auth = HTTPBasicAuth(creds['username'], creds['password'])
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    print("\n[*] Commencing Personas to ServiceNow Sys_User Sync...")

    with open(PERSONAS_JSON_PATH, "r") as f:
        personas = json.load(f)

    for persona in personas:
        call_sign = persona.get("name", "Unknown")
        prompt = persona.get("u_system_prompt", "")
        zone = persona.get("u_deployment_zone", "global")
        
        # Load Markdown File if it exists
        lore_content = prompt  # Fallback to system prompt
        normalized_name = call_sign.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
        lore_path = os.path.join(LORE_DIR, f"{normalized_name}.md")
        
        if os.path.exists(lore_path):
            with open(lore_path, "r") as lf:
                lore_content = lf.read()
        else:
            print(f"  [?] No long markdown found for {call_sign}. Using short prompt.")

        payload = {
            "first_name": call_sign,
            "last_name": "(Sovereign Entity)",
            "user_name": normalized_name,
            "title": prompt[:150] + "..." if len(prompt) > 150 else prompt,
            "introduction": lore_content[:4000],  # Use introduction for the Lore payload
            "city": zone,
            "department": "gemini",
            "active": "true"
        }

        # Check if user exists
        query_url = f"{base_url}/sys_user?sysparm_query=user_name={normalized_name}&sysparm_limit=1"
        try:
            get_res = requests.get(query_url, auth=auth, headers=headers)
            if get_res.status_code == 200 and len(get_res.json().get('result', [])) > 0:
                sys_id = get_res.json()['result'][0]['sys_id']
                put_url = f"{base_url}/sys_user/{sys_id}"
                resp = requests.put(put_url, auth=auth, headers=headers, json=payload)
                print(f"  [UPDATED] {call_sign} -> Sys ID: {sys_id}")
            else:
                post_url = f"{base_url}/sys_user"
                resp = requests.post(post_url, auth=auth, headers=headers, json=payload)
                if resp.status_code == 201:
                    sys_id = resp.json()['result']['sys_id']
                    print(f"  [CREATED] {call_sign} -> Sys ID: {sys_id}")
                else:
                    print(f"  [ERROR] {call_sign} failed to create: {resp.text}")
        except Exception as e:
            print(f"  [ERROR] Sync failed for {call_sign}: {e}")

if __name__ == "__main__":
    main()
