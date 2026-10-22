import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

CONTEXT_DB = "/home/james/stacklabs/dna/context_database.json"

def fetch_mlb_news():
    url = "https://www.espn.com/espn/rss/mlb/news"
    print(f"Fetching MLB news from {url}...")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        news_items = []
        
        for item in root.findall('./channel/item')[:5]:
            title = item.find('title').text if item.find('title') is not None else ""
            desc = item.find('description').text if item.find('description') is not None else ""
            news_items.append({"title": title, "summary": desc})
            
        return news_items
    except Exception as e:
        print(f"Failed to fetch MLB news: {e}")
        return []

def main():
    news = fetch_mlb_news()
    
    # Load existing context if any
    context_data = {"mlb_news": [], "last_updated": ""}
    if os.path.exists(CONTEXT_DB):
        try:
            with open(CONTEXT_DB, "r") as f:
                context_data = json.load(f)
        except Exception:
            pass

    if news:
        context_data["mlb_news"] = news
        context_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONTEXT_DB), exist_ok=True)
        with open(CONTEXT_DB, "w") as f:
            json.dump(context_data, f, indent=4)
            
        print(f"Extracted {len(news)} news items and saved to Context Database.")
    else:
        print("No news to update.")

if __name__ == "__main__":
    main()
