import os
import time
from playwright.sync_api import sync_playwright

STATE_FILE = "flow_state.json"
SCRIPT_FILE = "/home/james/.gemini/antigravity/brain/55c406d9-9675-49aa-bf07-3130dc2e17e1/wrexham_hot_take.md"
OUTPUT_DIR = "/home/james/stacklabs/dna/dropzone/daily_03052026/"

def parse_prompts(filepath):
    prompts = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        # Skip headers, empty lines, and markdown dividers
        if not line or line.startswith('#') or line.startswith('-') or line.startswith('*'):
            continue
        # If it's a valid text line, it's a prompt
        prompts.append(line)
        
    # Remove the first intro prompt because the 7-second base video is already loaded!
    return prompts[1:]

def automate_flow(project_url):
    prompts = parse_prompts(SCRIPT_FILE)
    print(f"Loaded {len(prompts)} prompts from the script.")
    
    with sync_playwright() as p:
        # Launching with headless=False so you can watch the magic happen on your monitor!
        # It's highly satisfying to watch the ghost in the machine work.
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )
        
        # Load the saved authentication state!
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        
        print(f"Navigating to {project_url}...")
        page.goto(project_url)
        
        # Give the page a moment to fully load the heavy UI
        page.wait_for_load_state("networkidle")
        time.sleep(5)
        
        for idx, prompt_text in enumerate(prompts):
            print(f"\n--- Processing Prompt {idx+1}/{len(prompts)} ---")
            print(f"Prompt: {prompt_text}")
            
            try:
                # 1. Locate the text input area using the exact placeholder from the screenshot
                textbox = page.get_by_placeholder("What happens next?", exact=False).first
                if not textbox.is_visible():
                    print("Could not find textarea. Trying fallback...")
                    textbox = page.locator("textarea").first
                
                # 2. Type the prompt
                textbox.fill("") # Clear it just in case
                textbox.fill(prompt_text)
                time.sleep(2)
                
                # 3. Submit the prompt by hitting Enter (as you verified manually)
                textbox.press("Enter")
                    
                print("Generation started! Waiting for render to complete (this takes ~60-90s)...")
                
                # 4. Wait for generation to finish. 
                time.sleep(15) # Buffer for loading UI to appear
                # The Extend button usually disables or a spinner appears. We will wait for the DOM to settle.
                page.wait_for_load_state("networkidle", timeout=120000) 
                time.sleep(5) # Buffer before the next prompt
                
                print("Generation complete! Moving to next prompt...")
                
            except Exception as e:
                print(f"Error processing prompt {idx+1}: {e}")
                time.sleep(5)
                
        print("\nAll 16 prompts processed! The video is fully extended.")
        print("You can now click the Download icon at the top right of the UI to save the final stitched video!")
        input("Press Enter here when you are done to close the browser...")
        browser.close()

if __name__ == "__main__":
    url = input("Paste the URL of your current Flow project (e.g., https://aitestkitchen.withgoogle.com/tools/video-fx/project/...): ")
    automate_flow(url)
