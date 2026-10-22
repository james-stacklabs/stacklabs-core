from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        # Give it a good viewport size so the UI lays out nicely.
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        print("Navigating to FanStack Dashboard...")
        
        # Wait for "load" instead of "networkidle" since WebSockets prevent networkidle.
        page.goto("http://localhost:3000/", wait_until="load")
        
        # Explicitly wait 7 seconds to let all react components, avatars, and fonts hydrate
        page.wait_for_timeout(7000)
        
        pdf_path = "/home/james/stacklabs/dna/agents/GONZO/FanStack_Tour.pdf"
        page.pdf(path=pdf_path, format="A3", margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"}, print_background=True)
        print(f"Generated PDF: {pdf_path}")
        browser.close()

if __name__ == "__main__":
    run()
