import os
import time
from playwright.sync_api import sync_playwright

STATE_FILE = "/home/james/stacklabs/flow_state.json"

def dump_dom(project_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"]
        )
        
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        print(f"Navigating to {project_url}...")
        page.goto(project_url)
        page.wait_for_load_state("networkidle")
        time.sleep(10)
        
        with open("/home/james/stacklabs/dom.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("DOM dumped to dom.html")
        browser.close()

if __name__ == "__main__":
    dump_dom("https://labs.google/fx/tools/flow/project/f2e3663a-4e34-41a6-b221-ed987161e731/edit/8451cb7e-5453-49bc-9e75-d9f99326b695")
