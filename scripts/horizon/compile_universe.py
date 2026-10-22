import io
import requests
import json
import pandas as pd

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# 1. S&P 500
resp_sp = requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', headers=headers)
dfs_sp = pd.read_html(io.StringIO(resp_sp.text))
sp500 = dfs_sp[0]

# 2. Nasdaq 100
resp_ndx = requests.get('https://en.wikipedia.org/wiki/Nasdaq-100', headers=headers)
dfs_ndx = pd.read_html(io.StringIO(resp_ndx.text))
# Find table with ticker column
ndx = None
for t in dfs_ndx:
    if 'Ticker' in t.columns:
        ndx = t
        break
    elif 'Symbol' in t.columns:
        ndx = t
        break

tickers_meta = {}
for _, row in sp500.iterrows():
    sym = str(row['Symbol']).strip().replace('.', '-')
    tickers_meta[sym] = {
        'symbol': sym,
        'security': row.get('Security', ''),
        'sector': row.get('GICS Sector', ''),
        'sub_industry': row.get('GICS Sub-Industry', ''),
        'exchange': 'NYSE/Nasdaq'
    }

if ndx is not None:
    sym_col = 'Ticker' if 'Ticker' in ndx.columns else 'Symbol'
    comp_col = 'Company' if 'Company' in ndx.columns else 'Security'
    sector_col = 'GICS Sector' if 'GICS Sector' in ndx.columns else 'Sector'
    for _, row in ndx.iterrows():
        sym = str(row[sym_col]).strip().replace('.', '-')
        if sym not in tickers_meta:
            tickers_meta[sym] = {
                'symbol': sym,
                'security': str(row.get(comp_col, '')) if comp_col in ndx.columns else '',
                'sector': str(row.get(sector_col, '')) if sector_col in ndx.columns else '',
                'sub_industry': '',
                'exchange': 'Nasdaq'
            }

# Add notable volatile high-liquidity momentum common stocks (e.g. COIN, PLTR, HOOD, SOFI, MARA, RIOT, RBLX, ARM, SMCI, IONQ, ASTS, CVNA, SHOP, SNOW, RIVN, LCID)
additional_active = [
    ("PLTR", "Palantir Technologies", "Information Technology"),
    ("COIN", "Coinbase Global", "Financials"),
    ("HOOD", "Robinhood Markets", "Financials"),
    ("SOFI", "SoFi Technologies", "Financials"),
    ("MARA", "MARA Holdings", "Information Technology"),
    ("RIOT", "Riot Platforms", "Information Technology"),
    ("RBLX", "Roblox Corp", "Communication Services"),
    ("ARM", "Arm Holdings", "Information Technology"),
    ("SMCI", "Super Micro Computer", "Information Technology"),
    ("IONQ", "IonQ Inc", "Information Technology"),
    ("ASTS", "AST SpaceMobile", "Telecommunications"),
    ("CVNA", "Carvana Co", "Consumer Discretionary"),
    ("SHOP", "Shopify Inc", "Information Technology"),
    ("SNOW", "Snowflake Inc", "Information Technology"),
    ("RIVN", "Rivian Automotive", "Consumer Discretionary"),
    ("LCID", "Lucid Group", "Consumer Discretionary"),
    ("AFRM", "Affirm Holdings", "Financials"),
    ("UPST", "Upstart Holdings", "Financials"),
    ("DKNG", "DraftKings Inc", "Consumer Discretionary"),
    ("PATH", "UiPath Inc", "Information Technology"),
    ("NET", "Cloudflare Inc", "Information Technology"),
    ("DDOG", "Datadog Inc", "Information Technology"),
    ("ZS", "Zscaler Inc", "Information Technology"),
    ("CRWD", "CrowdStrike", "Information Technology"),
    ("SQ", "Block Inc", "Financials"),
    ("PYPL", "PayPal Holdings", "Financials"),
    ("UBER", "Uber Technologies", "Industrials"),
    ("ABNB", "Airbnb Inc", "Consumer Discretionary"),
    ("DASH", "DoorDash Inc", "Consumer Discretionary"),
    ("TTD", "The Trade Desk", "Communication Services"),
    ("SNAP", "Snap Inc", "Communication Services"),
    ("PINS", "Pinterest Inc", "Communication Services"),
    ("RDDT", "Reddit Inc", "Communication Services"),
    ("APP", "AppLovin Corp", "Information Technology"),
    ("HIMS", "Hims & Hers Health", "Health Care"),
    ("CAVA", "CAVA Group", "Consumer Discretionary"),
    ("DUOL", "Duolingo Inc", "Communication Services"),
    ("MDB", "MongoDB Inc", "Information Technology"),
    ("CFLT", "Confluent Inc", "Information Technology"),
    ("GTLB", "GitLab Inc", "Information Technology"),
    ("S", "SentinelOne Inc", "Information Technology"),
    ("ALAB", "Astera Labs", "Information Technology"),
    ("TEM", "Tempus AI", "Health Care"),
    ("CELH", "Celsius Holdings", "Consumer Staples"),
    ("ELF", "e.l.f. Beauty", "Consumer Staples"),
    ("WING", "Wingstop Inc", "Consumer Discretionary"),
    ("DECK", "Deckers Outdoor", "Consumer Discretionary"),
    ("ONON", "On Holding AG", "Consumer Discretionary"),
    ("BIRK", "Birkenstock Holding", "Consumer Discretionary"),
    ("LUNR", "Intuitive Machines", "Industrials"),
    ("RKLB", "Rocket Lab USA", "Industrials")
]

for sym, sec, sect in additional_active:
    if sym not in tickers_meta:
        tickers_meta[sym] = {
            'symbol': sym,
            'security': sec,
            'sector': sect,
            'sub_industry': '',
            'exchange': 'NYSE/Nasdaq'
        }

print(f"Total curated universe: {len(tickers_meta)} stocks")
out_path = '/home/james/sovereign_inbox/today/us_common_stocks_universe.json'
with open(out_path, 'w') as f:
    json.dump(tickers_meta, f, indent=2)
print(f"Saved to {out_path}")
