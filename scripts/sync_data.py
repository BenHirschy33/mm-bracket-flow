import argparse
import csv
import json
import cloudscraper
import pandas as pd
from io import StringIO
from pathlib import Path
import time

def fetch_sports_reference_data(year: int) -> pd.DataFrame:
    """
    Fetches the raw stats table from Sports Reference.
    >= 2011: Uses Advanced School Stats.
    < 2011: Uses Basic School Stats.
    """
    mode = "advanced-school-stats" if year >= 2011 else "school-stats"
    urls = [
        f"https://www.sports-reference.com/cbb/seasons/men/{year}-{mode}.html",
        f"https://www.sports-reference.com/cbb/seasons/{year}-{mode}.html"
    ]
    
    scraper = cloudscraper.create_scraper()
    for url in urls:
        print(f"Trying {url}...")
        try:
            response = scraper.get(url)
            if response.status_code == 200:
                dfs = pd.read_html(StringIO(response.text))
                if dfs:
                    df = dfs[0]
                    # Flatten MultiIndex if present
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [col[1] if "Unnamed" not in col[0] else col[1] for col in df.columns]
                    
                    df = df[df['School'].notna()]
                    df = df[df['School'] != 'School']
                    return df
            print(f"Failed {url}: HTTP {response.status_code}")
        except Exception as e:
            print(f"Error for {url}: {e}")
            
    return pd.DataFrame()

def safe_float(val):
    try:
        if pd.isna(val) or str(val).strip() == "" or val == "None":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None

def sync_data(year: int):
    base_dir = Path(f"years/{year}/data")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    df = fetch_sports_reference_data(year)
    if df.empty:
        return
        
    engine_csv = base_dir / "team_stats.csv"
    engine_headers = ["Team", "Seed", "AdjO", "AdjD", "Off_PPG", "Def_PPG", "Pace", "eFG_Off", "eFG_Def", "TO_Off", "TO_Def", "TRB", "3PAr", "SOS", "Momentum", "Intuition"]
    
    engine_rows = []
    for _, row in df.iterrows():
        team_name = str(row.get('School', '')).replace('NCAA', '').strip()
        if not team_name: continue
            
        # Common Basic Stats (available in all eras)
        off_ppg = safe_float(row.get('PS/G'))
        def_ppg = safe_float(row.get('PA/G'))
        sos = safe_float(row.get('SOS'))
        
        # Advanced Stats (mostly 2011+)
        adjo = safe_float(row.get('ORtg'))
        pace = safe_float(row.get('Pace'))
        efg_off = safe_float(row.get('eFG%'))
        tov_off = safe_float(row.get('TOV%'))
        trb = safe_float(row.get('TRB%'))
        threepar = safe_float(row.get('3PAr'))
        
        engine_rows.append({
            "Team": team_name,
            "Seed": "",
            "AdjO": adjo,
            "AdjD": None, 
            "Off_PPG": off_ppg, 
            "Def_PPG": def_ppg,
            "Pace": pace,
            "eFG_Off": efg_off,
            "eFG_Def": None,
            "TO_Off": tov_off,
            "TO_Def": None,
            "TRB": trb,
            "3PAr": threepar,
            "SOS": sos, 
            "Momentum": "0.0", 
            "Intuition": "0.0" 
        })
            
    with open(engine_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=engine_headers)
        writer.writeheader()
        writer.writerows(engine_rows)
        
    print(f"✅ Sync complete for {year}: {len(engine_rows)} teams.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()
    
    if args.start and args.end:
        for y in range(args.start, args.end + 1):
            sync_data(y)
            time.sleep(1) # Be nice to SR
    else:
        sync_data(args.year)
