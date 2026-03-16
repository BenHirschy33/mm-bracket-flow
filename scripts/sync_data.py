import sys
import os
import time
from io import StringIO
from pathlib import Path

# Ensure local dependencies are prioritised
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "local_lib"))

import argparse
import csv
import json
import cloudscraper
import pandas as pd

def safe_float(val):
    try:
        if pd.isna(val) or str(val).strip() == "" or val == "None":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None

def fetch_table(year: int, mode: str) -> pd.DataFrame:
    urls = [
        f"https://www.sports-reference.com/cbb/seasons/men/{year}-{mode}.html",
        f"https://www.sports-reference.com/cbb/seasons/{year}-{mode}.html"
    ]
    scraper = cloudscraper.create_scraper()
    for url in urls:
        try:
            response = scraper.get(url)
            if response.status_code == 200:
                dfs = pd.read_html(StringIO(response.text))
                if dfs:
                    df = dfs[0]
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [col[1] if "Unnamed" not in col[0] else col[1] for col in df.columns]
                    df = df[df['School'].notna()]
                    df = df[df['School'] != 'School']
                    return df
        except Exception: pass
    return pd.DataFrame()

def parse_record(record_str):
    if pd.isna(record_str) or "-" not in str(record_str):
        return 0, 0
    parts = str(record_str).split("-")
    try:
        return int(parts[0]), int(parts[1])
    except: return 0, 0

def sync_data(year: int):
    base_dir = Path(f"years/{year}/data")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Fetch multiple tables for full coverage
    df_adv = fetch_table(year, "advanced-school-stats")
    df_basic = fetch_table(year, "school-stats")
    
    if df_adv.empty and df_basic.empty:
        print(f"❌ No data found for {year}")
        return
        
    team_data = {}
    
    # Process Basic (Records, PPG, SOS)
    for _, row in df_basic.iterrows():
        name = str(row.get('School', '')).replace('NCAA', '').strip()
        if not name: continue
        w, l = parse_record(row.get('W-L'))
        hw, hl = parse_record(row.get('Home'))
        aw, al = parse_record(row.get('Away'))
        
        team_data[name] = {
            "Team": name,
            "Wins": w, "Losses": l,
            "HomeW": hw, "HomeL": hl,
            "AwayW": aw, "AwayL": al,
            "Off_PPG": safe_float(row.get('PS/G')),
            "Def_PPG": safe_float(row.get('PA/G')),
            "SOS": safe_float(row.get('SOS'))
        }
    
    # Process Advanced (Efficiency, Pace, Factors)
    for _, row in df_adv.iterrows():
        name = str(row.get('School', '')).replace('NCAA', '').strip()
        if name not in team_data: team_data[name] = {"Team": name}
        
        team_data[name].update({
            "AdjO": safe_float(row.get('ORtg')),
            "Pace": safe_float(row.get('Pace')),
            "eFG_Off": safe_float(row.get('eFG%')),
            "TO_Off": safe_float(row.get('TOV%')),
            "TRB": safe_float(row.get('TRB%')),
            "ORB": safe_float(row.get('ORB%')),
            "3PAr": safe_float(row.get('3PAr')),
            "FTr": safe_float(row.get('FTr'))
        })

    # Derive missing stats from basic totals
    for name, data in team_data.items():
        # Find raw row in df_basic
        basic_rows = df_basic[df_basic['School'].str.contains(name, na=False)]
        if not basic_rows.empty:
            brow = basic_rows.iloc[0]
            fg = safe_float(brow.get('FG'))
            fga = safe_float(brow.get('FGA'))
            tp = safe_float(brow.get('3P'))
            tpa = safe_float(brow.get('3PA'))
            fta = safe_float(brow.get('FTA'))
            
            if data.get("eFG_Off") is None and fg is not None and fga and fga > 0:
                data["eFG_Off"] = (fg + 0.5 * (tp or 0)) / fga
            if data.get("3PAr") is None and tpa is not None and fga and fga > 0:
                data["3PAr"] = tpa / fga
            if data.get("FTr") is None and fta is not None and fga and fga > 0:
                data["FTr"] = fta / fga
            if data.get("ORB") is None:
                # Use raw ORB/G if % is missing
                orb = safe_float(brow.get('ORB'))
                data["ORB"] = (orb / 10.0) if orb else None # Scale to roughly match % range
            
    engine_csv = base_dir / "team_stats.csv"
    engine_headers = ["Team", "Seed", "AdjO", "AdjD", "Off_PPG", "Def_PPG", "Pace", "eFG_Off", "eFG_Def", "TO_Off", "TO_Def", "TRB", "ORB", "3PAr", "FTr", "SOS", "Wins", "Losses", "HomeW", "HomeL", "AwayW", "AwayL", "Momentum", "Intuition"]
    
    rows = []
    for team, data in team_data.items():
        rows.append({
            "Team": data.get("Team"),
            "Seed": "",
            "AdjO": data.get("AdjO"),
            "AdjD": None,
            "Off_PPG": data.get("Off_PPG"),
            "Def_PPG": data.get("Def_PPG"),
            "Pace": data.get("Pace"),
            "eFG_Off": data.get("eFG_Off"),
            "eFG_Def": None,
            "TO_Off": data.get("TO_Off"),
            "TO_Def": None,
            "TRB": data.get("TRB"),
            "ORB": data.get("ORB"),
            "3PAr": data.get("3PAr"),
            "FTr": data.get("FTr"),
            "SOS": data.get("SOS"),
            "Wins": data.get("Wins"),
            "Losses": data.get("Losses"),
            "HomeW": data.get("HomeW"),
            "HomeL": data.get("HomeL"),
            "AwayW": data.get("AwayW"),
            "AwayL": data.get("AwayL"),
            "Momentum": 0.0,
            "Intuition": 0.0
        })
            
    with open(engine_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=engine_headers)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"✅ Enhanced sync complete for {year}: {len(rows)} teams.")

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
