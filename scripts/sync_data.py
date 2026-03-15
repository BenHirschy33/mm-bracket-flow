import argparse
import csv
import json
import cloudscraper
import pandas as pd
from io import StringIO
from pathlib import Path

def fetch_sports_reference_data(year: int) -> pd.DataFrame:
    """
    Fetches the raw advanced stats table from Sports Reference for a given year.
    Returns a Pandas DataFrame.
    """
    url = f"https://www.sports-reference.com/cbb/seasons/men/{year}-advanced-school-stats.html"
    print(f"Fetching raw data natively via Cloudscraper API from {url}...")
    
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        if response.status_code == 200:
            # Sports reference has multi-index headers, we grab the first table
            dfs = pd.read_html(StringIO(response.text))
            if dfs:
                df = dfs[0]
                # Flatten the MultiIndex columns
                df.columns = [col[1] if isinstance(col, tuple) else col for col in df.columns]
                # Filter out header rows that repeat in the middle of the table
                df = df[df['School'] != 'School']
                return df
        print(f"Error fetching data: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error fetching data: {e}")
        
    return pd.DataFrame()

def safe_float(val):
    try:
        if pd.isna(val) or str(val).strip() == "" or val == "None":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None

def sync_data(year: int):
    """
    The main pipeline.
    1. Fetches raw data from Sports Reference.
    2. Saves it as raw_team_stats.csv.
    3. Processes it into our engine's team_stats.csv format.
    """
    base_dir = Path(f"years/{year}/data")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    raw_csv = base_dir / "raw_team_stats.csv"
    engine_csv = base_dir / "team_stats.csv"
    
    df = fetch_sports_reference_data(year)
    if df.empty:
        print("Failed to fetch data. Exiting.")
        return
        
    print(f"Saving raw data to {raw_csv}...")
    df.to_csv(raw_csv, index=False)
        
    print(f"Processing and injecting data to {engine_csv}...")
    engine_rows = []
    engine_headers = ["Team", "Seed", "AdjO", "AdjD", "Off_PPG", "Def_PPG", "Pace", "eFG_Off", "eFG_Def", "TO_Off", "TO_Def", "SOS", "Momentum", "Intuition"]
    
    for _, row in df.iterrows():
        team_name = str(row.get('School', '')).replace('NCAA', '').strip()
        if not team_name:
            continue
            
        # Sports Reference column mapping
        # ORtg is closely correlated to AdjO
        adjo = safe_float(row.get('ORtg'))
        # They don't provide DRtg on the simple advanced page, so we will estimate or leave blank to fallback on base stats.
        adjd = None  
        pace = safe_float(row.get('Pace'))
        efg_off = safe_float(row.get('eFG%'))
        tov_off = safe_float(row.get('TOV%'))
        sos = safe_float(row.get('SOS'))
        
        engine_rows.append({
            "Team": team_name,
            "Seed": "", # Seed is injected during brackets
            "AdjO": adjo,
            "AdjD": adjd,
            "Off_PPG": "", 
            "Def_PPG": "",
            "Pace": pace,
            "eFG_Off": efg_off,
            "eFG_Def": "", # SR doesn't have defensive advanced splits on this table
            "TO_Off": tov_off,
            "TO_Def": "",
            "SOS": sos, 
            "Momentum": "", 
            "Intuition": "0.0" 
        })
            
    with open(engine_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=engine_headers)
        writer.writeheader()
        writer.writerows(engine_rows)
        
    print(f"✅ Successfully processed {len(engine_rows)} teams for the {year} season!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync live API data to local engine CSVs")
    parser.add_argument("--year", type=int, default=2025, help="Year of the tournament to fetch")
    args = parser.parse_args()
    
    sync_data(args.year)
