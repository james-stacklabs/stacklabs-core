import sys
import datetime
import requests
from bs4 import BeautifulSoup

def main():
    filepath = "/home/james/stacklabs/scripts/fanstack_live_context.txt"
    url = "https://www.yardbarker.com/rss/sport/2"
    print(f"[{datetime.datetime.now()}] Yardbarker Entropy Pump Initialized. Target: {filepath}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        headlines = []
        for item in items[:4]:  # Top 4 headlines
            headlines.append(item.title.text)
            
        if headlines:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Overwrite the context file to purge yesterday's drama
            with open(filepath, "w", encoding="utf-8") as f:
                for h in headlines:
                    entropy_string = f"[{timestamp}] AMBIENT YARDBARKER NEWS DROP: {h}\n"
                    f.write(entropy_string)
                    print(f"Injected context: {entropy_string.strip()}")
        else:
            print("No items found in RSS feed.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error fetching Yardbarker RSS: {e}")
        
if __name__ == "__main__":
    main()
