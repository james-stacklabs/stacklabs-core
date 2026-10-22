import yfinance as yf
import pandas as pd
from datetime import timedelta
import warnings

# Suppress warnings for cleaner terminal output
warnings.filterwarnings('ignore')

def main():
    ticker = "^VIX"
    
    try:
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    if data.empty:
        print("Failed to download VIX data.")
        return

    # Extract Close prices safely
    if isinstance(data.columns, pd.MultiIndex):
        close_prices = data['Close'].iloc[:, 0]
    else:
        close_prices = data['Close']

    # Calculate day-over-day percentage deltas
    pct_change = close_prices.pct_change() * 100
    
    # Isolate the Top 5 largest unexplained spikes
    top_5 = pct_change.sort_values(ascending=False).dropna().head(5)
    
    print("==========================================================")
    print("        OPERATION RETRO-CAUSALITY SWEEP: VIX SPIKES       ")
    print("==========================================================")
    print("    CORRELATING COGNITIVE LINGUISTIC COLLAPSE WITH VIX    ")
    print("----------------------------------------------------------\n")
    
    for i, (date, spike_pct) in enumerate(top_5.items(), 1):
        event_date = pd.to_datetime(date)
        
        # Define Catalyst Window (24 to 48 hours strictly prior)
        target_start = event_date - timedelta(days=2)
        target_end = event_date - timedelta(days=1)
        
        event_date_str = f"{event_date.strftime('%B')} {event_date.day}, {event_date.year}"
        
        if target_start.month == target_end.month:
            window_str = f"{target_start.strftime('%B')} {target_start.day}-{target_end.day}, {target_end.year}"
        else:
            window_str = f"{target_start.strftime('%B')} {target_start.day} - {target_end.strftime('%B')} {target_end.day}, {target_end.year}"
            
        print(f"[{i}] VIX CRASH DATE: {event_date_str}")
        print(f"    SPIKE MAGNITUDE: +{spike_pct:.2f}%")
        print(f"    TARGET INGESTION WINDOW: {window_str}\n")
        
    print("==========================================================")
    print("    SWEEP COMPLETE. AWAITING PILOT TARGET CONFIRMATION    ")
    print("==========================================================")

if __name__ == "__main__":
    main()
