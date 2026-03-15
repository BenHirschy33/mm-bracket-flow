import csv
import json
import argparse
from pathlib import Path

def csv_to_json(csv_filepath: str, year: int, output_dir: str):
    """
    Converts a standard CSV export of team statistics into the structured
    team_stats.json format required by MM-Bracket-Flow.
    
    Expected CSV Headers (case-insensitive, these are common columns we map):
    Team, Seed, AdjO, AdjD, Off_PPG, Def_PPG, Pace, eFG_Off, eFG_Def, TO_Off, TO_Def, SOS, Momentum
    """
    csv_path = Path(csv_filepath)
    if not csv_path.exists():
        print(f"Error: Could not find CSV file at {csv_path}")
        return
        
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "team_stats.json"
    
    data = {
        "year": year,
        "teams": {}
    }
    
    def safe_float(val):
        if not val or val.strip() == "" or val.strip().lower() in ("null", "none", "n/a"):
            return None
        return float(val)

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Create a lowercase mapping of the headers to be flexible
        # Example: if CSV has 'Adj_Tempo', we can map it to 'pace'
        for row in reader:
            # We assume a column named "Team" exists.
            team_name_key = next((k for k in row.keys() if k and k.lower() == 'team'), None)
            if not team_name_key:
                print("Skipping row: missing 'Team' column")
                continue
                
            name = row[team_name_key]
            
            # Map the standard KenPom/Torvik columns to our internal model.
            # If the column doesn't exist in the CSV, safe_float returns None safely.
            stats = {
                "seed": safe_float(row.get('Seed', 16)),
                "off_efficiency": safe_float(row.get('AdjO', 100.0)),
                "def_efficiency": safe_float(row.get('AdjD', 100.0)),
                "off_ppg": safe_float(row.get('Off_PPG', 70.0)),
                "def_ppg": safe_float(row.get('Def_PPG', 70.0)),
                "pace": safe_float(row.get('Pace')),
                "off_efg_pct": safe_float(row.get('eFG_Off')),
                "def_efg_pct": safe_float(row.get('eFG_Def')),
                "off_to_pct": safe_float(row.get('TO_Off')),
                "def_to_pct": safe_float(row.get('TO_Def')),
                "sos": safe_float(row.get('SOS')),
                "momentum": safe_float(row.get('Momentum')),
            }
            
            data["teams"][name] = stats
            
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        
    print(f"✅ Successfully converted CSV to JSON! Saved to {out_file}")
    print(f"Parsed {len(data['teams'])} teams.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert stat CSV to MM-Bracket-Flow JSON")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("year", type=int, help="Year of the tournament")
    parser.add_argument("--out", default=".", help="Output directory for team_stats.json")
    
    args = parser.parse_args()
    csv_to_json(args.csv_file, args.year, args.out)
