#!/home/james/stacklabs/.venv/bin/python3
import os
import sys

# Force execution within the SovereignOS virtual environment
VENV_PYTHON = "/home/james/stacklabs/.venv/bin/python3"
if sys.executable != VENV_PYTHON and os.path.exists(VENV_PYTHON):
    os.execl(VENV_PYTHON, VENV_PYTHON, *sys.argv)

import argparse
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser(description="Automated Barf Twitter Bot via Gemini UI")
    parser.add_argument("--dry-run", action="store_true", help="Generate the hot take but do not post to X.")
    parser.add_argument("--login", action="store_true", help="Run headful mode to allow manual login to Google and X.")
    args = parser.parse_args()

    # Define the persistent profile directory for Barf on the local Linux node
    profile_dir = "/home/james/.config/playwright-barf-profile"
    
    with sync_playwright() as p:
        print(f"Launching Chrome profile at {profile_dir}...")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=not args.login,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = browser.new_page()

        print("Navigating to Gemini...")
        page.goto("https://gemini.google.com/app")

        # Handle potential splash screens with a simple sleep, wait_for_load_state is too flaky on SPAs
        time.sleep(5)
        time.sleep(3)
        
        if args.login:
            print("LOGIN MODE: Please manually log into Gemini and X if not already authenticated. Waiting 60 seconds...")
            page.goto("https://x.com")
            time.sleep(60)
            page.goto("https://gemini.google.com/app")
            time.sleep(5)

        prompt = """Look up today's upcoming New York Mets game on the MLB slate. I need you to generate 3 separate Twitter posts previewing today's matchup.
1. The main tweet from the 'BARF' persona (agitated, pessimistic, trauma-laden Mets fan). Raw hot take, specific players/stats. No emojis.
2. A reply tweet from 'Sovereign FanStack' persona (analytical/studio voice, citing data or metrics).
3. A reply tweet from 'jc2pointzero' (die-hard, energetic fan voice).

Format your response EXACTLY like this with these exact tags:
[BARF]
(tweet text)
[FANSTACK]
(tweet text)
[JC2POINTZERO]
(tweet text)"""
        
        try:
            # Gemini input box
            input_box = page.locator("rich-textarea").first
            input_box.wait_for(state="visible", timeout=10000)
            input_box.fill(prompt)
            page.keyboard.press("Enter")
        except Exception as e:
            print("Failed to find Gemini input box. Are you logged in? Fallback to generic textbox...")
            input_box = page.get_by_role("textbox").first
            input_box.fill(prompt)
            page.keyboard.press("Enter")

        print("Waiting for Barf to cook (15 seconds)...")
        # Wait for the response to stream completely
        # We wait for the 'Copy' button or just a hard sleep to be safe with streaming responses
        time.sleep(15)
        
        # Scrape the latest response
        print("Extracting hot take...")
        try:
            # The responses are usually in a message-content block. We take the last one.
            responses = page.locator("message-content")
            responses.last.wait_for(state="visible", timeout=10000)
            hot_take_text = responses.last.inner_text()
        except:
            print("Could not find standard message-content. Attempting fallback extraction...")
            # Fallback if DOM changes
            responses = page.locator(".model-response-text")
            hot_take_text = responses.last.inner_text() if responses.count() > 0 else "ERROR: Could not extract response."

        # Clean up any Markdown bolding since X doesn't support it natively
        hot_take_text = hot_take_text.replace("**", "")

        # Parse the three sections
        barf_tweet = ""
        fanstack_tweet = ""
        jc_tweet = ""
        
        try:
            parts = hot_take_text.split("[BARF]")
            rest = parts[1].split("[FANSTACK]")
            barf_tweet = rest[0].strip()
            rest2 = rest[1].split("[JC2POINTZERO]")
            fanstack_tweet = rest2[0].strip()
            jc_tweet = rest2[1].strip()
        except Exception as e:
            print("Failed to parse the three personas perfectly. Using raw text for Barf.")
            barf_tweet = hot_take_text

        tags = "\n\n#LGM #Mets #MetsTwitter #NYM #CitiField @Mets @SNY_Mets @StevenACohen2 @AnthonyDiComo @SteveGelbs @TheWardyNYM"
        
        final_post = f"{barf_tweet}{tags}"
        if fanstack_tweet: fanstack_tweet = f"{fanstack_tweet}{tags}"
        if jc_tweet: jc_tweet = f"{jc_tweet}{tags}"
        
        print("\n--- GENERATED TWEET (BARF) ---")
        print(final_post)
        print("-----------------------\n")
        
        print("--- ALGORITHMIC TRACTION REPLIES ---")
        print(f"[FanStack]: {fanstack_tweet}")
        print(f"[jc2pointzero]: {jc_tweet}")
        print("------------------------------------\n")

        # Save tweets to persistent inbox storage
        try:
            inbox_dir = "/home/james/sovereign_inbox/today"
            os.makedirs(inbox_dir, exist_ok=True)
            
            tweet_data = {
                "timestamp": datetime.now().isoformat(),
                "barf_tweet": final_post,
                "fanstack_reply": fanstack_tweet,
                "jc_reply": jc_tweet
            }
            
            latest_file = os.path.join(inbox_dir, "barf_tweets_latest.json")
            with open(latest_file, "w") as f:
                json.dump(tweet_data, f, indent=2)
                
            queue_file = os.path.join(inbox_dir, "tweet_queue.log")
            with open(queue_file, "a") as f:
                f.write(f"\n--- [{datetime.now().isoformat()}] BARF TWEET BATCH ---\n")
                f.write(f"[BARF]: {final_post}\n")
                f.write(f"[FANSTACK]: {fanstack_tweet}\n")
                f.write(f"[JC2POINTZERO]: {jc_tweet}\n")
                f.write("="*50 + "\n")
            print(f"✅ Generated tweets persisted to:\n   - {latest_file}\n   - {queue_file}")
        except Exception as save_err:
            print(f"Warning: Failed to save tweet files to inbox: {save_err}")

        if args.dry_run:
            print("DRY RUN ACTIVE. Skipping post to X.")
            browser.close()
            return

        print("Navigating to X to post...")
        page.goto("https://x.com/compose/post")
        time.sleep(5)
        
        try:
            # Find the tweet composer
            composer = page.locator("[data-testid='tweetTextarea_0']")
            composer.wait_for(state="visible", timeout=15000)
            composer.fill(final_post)
            time.sleep(2) # Brief pause for X to register text
            
            print("Clicking Post...")
            post_button = page.locator("[data-testid='tweetButton']")
            post_button.click()
            time.sleep(5) # Wait for post to submit
            print("Successfully posted to X!")
            
        except Exception as e:
            print(f"Failed to post to X. Error: {e}")

        browser.close()

if __name__ == "__main__":
    main()
