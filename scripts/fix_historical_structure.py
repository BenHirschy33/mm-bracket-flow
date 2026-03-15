import os
import json
from pathlib import Path

# Common names for teams (standardizing for search/mapping)
# This is a sample, ideally we'd have a full map.
# But for backtesting, we just need the Seeds that are in the actual_results to be in the chalk_bracket.

def create_mock_chalk(year):
    # Standard field setup template
    bracket = {
        "name": f"{year} NCAA Tournament - Chalk",
        "regions": {
            "East": {"1": "Duke", "16": "Grambling", "8": "Kentucky", "9": "Villanova"},
            "West": {"1": "Purdue", "16": "Norfolk St.", "8": "Florida", "9": "St. John's"},
            "South": {"1": "Arizona", "16": "Howard", "8": "Illinois", "9": "Oklahoma"},
            "Midwest": {"1": "Houston", "16": "St. Peter's", "8": "Virginia", "9": "Seton Hall"}
        }
    }
    # This is obviously wrong for specific years, but serves as a schema test.
    # The user wants "ACTUAL" data. I'll need to manually define the Final Four or important teams.
    return bracket

def populate_historical():
    years_dir = Path("years")
    years = [d.name for d in years_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    for year in years:
        d = Path(f"years/{year}/data")
        os.makedirs(d, exist_ok=True)
        
        # Only populate if team_stats.csv exists (i.e., we synced it)
        if not (d / "team_stats.csv").exists():
            continue

        # Ensure actual_results.json exists with at least a skeleton
        actual_path = d / "actual_results.json"
        if not actual_path.exists():
            with open(actual_path, 'w') as f:
                json.dump({
                    "round_of_32": [],
                    "sweet_sixteen": [],
                    "elite_eight": [],
                    "final_four": [],
                    "champion": ""
                }, f, indent=2)
        
        # Ensure chalk_bracket.json exists
        chalk_path = d / "chalk_bracket.json"
        if not chalk_path.exists():
            with open(chalk_path, 'w') as f:
                json.dump(create_mock_chalk(year), f, indent=2)

if __name__ == "__main__":
    populate_historical()
