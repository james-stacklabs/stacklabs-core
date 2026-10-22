import os
import sys
import time
import warnings

# Suppress the deprecation warning to keep the output pristine for Wardy/System checks
warnings.filterwarnings('ignore')

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_postgame_context.py <path_to_mp4>")
        sys.exit(1)

    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"Error: Could not find file {video_path}")
        sys.exit(1)

    # Load API Key
    api_key = None
    try:
        with open('/home/james/stacklabs/.env') as f:
            for line in f:
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
                    break
    except Exception as e:
        print(f"[!] Error loading Gemini API key: {e}")
        sys.exit(1)

    from google import genai
    client = genai.Client(api_key=api_key)

    print(f"[*] Uploading {os.path.basename(video_path)} to Sovereign AI (Gemini 2.5 Flash)...")
    video_file = client.files.upload(file=video_path)

    print(f"[*] Upload complete. File URI: {video_file.uri}")
    print("[*] Awaiting video ingestion and temporal encoding...")
    
    while video_file.state.name == "PROCESSING":
        print('.', end='', flush=True)
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)
    print()

    if video_file.state.name == "FAILED":
        print("[!] Neural video processing failed.")
        sys.exit(1)

    print("[*] Ingestion stable. Extracting Wardy's unhinged narrative context...")

    prompt = (
        "You are the Sovereign Oracle monitoring Wardy, a volatile and deeply opinionated baseball podcaster/fan. "
        "Analyze this postgame show video. Your directive is to extract 4 to 5 highly specific, contextual highlights. "
        "Focus intensely on player call-outs, umpire grudges, bizarre analogies, controversial calls, and intense emotional peaks. "
        "Format your output as simple, punchy bullet points under 50 words each. "
        "Do not include any pleasantries or introductory text. Output ONLY the raw contextual data designed to be ingested directly into the Playcall Desk Hive Mind."
    )

    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=[video_file, prompt]
    )

    # Save output
    base_name = os.path.splitext(video_path)[0]
    out_path = f"{base_name}_context.txt"

    with open(out_path, 'w') as f:
        f.write(response.text)

    print(f"\n[+] SUCCESS! Context payload generated and saved to:")
    print(f"    {out_path}")
    print("\n================== EXTRACTED HIVE MIND CONTEXT ==================")
    print(response.text)
    print("=================================================================\n")

    # Clean up file from Gemini to save space/quota
    client.files.delete(name=video_file.name)
    print("[*] Source media purged from Gemini remote storage.")

if __name__ == "__main__":
    main()
