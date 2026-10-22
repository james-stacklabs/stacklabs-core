import pandas as pd
import json

file_path = '/home/james/stacklabs/dna/dropzone/daily_13042026/mlb_schedule_2026.xlsx'
df = pd.read_excel(file_path, header=None)

# Find header row (usually contains team names)
header_row_idx = 14 # Hardcoded based on inspection, or we can search for a row with many teams
header_row = df.iloc[header_row_idx]

# Find the NYM column
nym_col_idx = -1
for i, val in enumerate(header_row):
    if str(val).strip() == 'NYM':
        nym_col_idx = i
        break

if nym_col_idx == -1:
    print("NYM column not found at row 14, searching...")
    for idx, row in df.iterrows():
        if 'NYM' in [str(v).strip() for v in row.values]:
            header_row_idx = idx
            nym_col_idx = list(row.values).index('NYM')
            break

print(f"NYM found at Row {header_row_idx}, Col {nym_col_idx}")

# Date column is likely column 1 or something similar
date_col_idx = 1 # Based on previous output

schedule = []
for idx in range(header_row_idx + 1, len(df)):
    date_val = str(df.iloc[idx, date_col_idx]).strip()
    opponent = str(df.iloc[idx, nym_col_idx]).strip()
    
    # Filter out header repetitions, row numbers, or empty rows
    is_valid_date = '-' in date_val and len(date_val) > 4
    is_valid_opponent = opponent and opponent not in ['nan', 'NaN', 'NYM', 'opponent'] and len(opponent) >= 2
    
    if is_valid_date and is_valid_opponent:
        if opponent.startswith('@'):
            game_str = f"NYM {opponent}"
        else:
            game_str = f"{opponent} @ NYM"
            
        schedule.append({
            "date": date_val,
            "game": game_str,
            "opponent": opponent.replace('@', '').strip()
        })

# Save to json
output_path = '/home/james/stacklabs/01_Sovereign_Portal/public/mlb_schedule_2026.json'
with open(output_path, 'w') as f:
    json.dump(schedule, f, indent=4)

print(f"Schedule exported to {output_path}")
print(schedule[:10])
