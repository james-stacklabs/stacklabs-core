import io
import requests
import pandas as pd

url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
resp = requests.get(url, headers=headers)
dfs = pd.read_html(io.StringIO(resp.text))
df = dfs[0]
print("S&P 500 count:", len(df))
print(df[['Symbol', 'Security', 'GICS Sector']].head())
symbols = df['Symbol'].str.replace('.', '-', regex=False).tolist()
with open('/home/james/sovereign_inbox/today/sp500_tickers.json', 'w') as f:
    import json
    json.dump(symbols, f)
print(f"Saved {len(symbols)} symbols to /home/james/sovereign_inbox/today/sp500_tickers.json")
