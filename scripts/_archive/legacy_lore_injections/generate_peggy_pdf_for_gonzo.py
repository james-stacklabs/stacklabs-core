from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        url = "file:///home/james/stacklabs/peggy_character_blueprint.html"
        print(f"Loading {url}")
        
        # Load local file
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        pdf_path = "/home/james/stacklabs/dna/agents/GONZO/Peggy_Character_Blueprint.pdf"
        page.pdf(path=pdf_path, format="A3", margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"}, print_background=True)
        print(f"Generated PDF: {pdf_path}")
        browser.close()

if __name__ == "__main__":
    run()
