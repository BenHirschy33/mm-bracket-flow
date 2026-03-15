import json
from pathlib import Path

# Refined seeding for better backtesting (Top 4 seeds per year)
HISTORICAL_SEEDS = {
    "2023": {
        "East": {"1": "Purdue", "2": "Marquette", "3": "Kansas St.", "4": "Tennessee"},
        "West": {"1": "Kansas", "2": "UCLA", "3": "Gonzaga", "4": "UConn"},
        "South": {"1": "Alabama", "2": "Arizona", "3": "Baylor", "4": "Virginia"},
        "Midwest": {"1": "Houston", "2": "Texas", "3": "Xavier", "4": "Indiana"}
    },
    "2022": {
        "West": {"1": "Gonzaga", "2": "Duke", "3": "Texas Tech", "4": "Arkansas"},
        "East": {"1": "Baylor", "2": "Kentucky", "3": "Purdue", "4": "UCLA"},
        "South": {"1": "Arizona", "2": "Villanova", "3": "Tennessee", "4": "Illinois"},
        "Midwest": {"1": "Kansas", "2": "Auburn", "3": "Wisconsin", "4": "Providence"}
    },
    "2021": {
        "West": {"1": "Gonzaga", "2": "Iowa", "3": "Kansas", "4": "Virginia"},
        "East": {"1": "Michigan", "2": "Alabama", "3": "Texas", "4": "Florida St."},
        "South": {"1": "Baylor", "2": "Ohio St.", "3": "Arkansas", "4": "Purdue"},
        "Midwest": {"1": "Illinois", "2": "Houston", "3": "West Virginia", "4": "Oklahoma St."}
    }
}

def refine_brackets():
    for year, regions in HISTORICAL_SEEDS.items():
        p = Path(f"years/{year}/data/chalk_bracket.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        # Load existing or create fresh
        with open(p, 'w') as f:
            json.dump({"name": f"{year} Actual Seeds", "regions": regions}, f, indent=2)
            print(f"Refined {year} seeds.")

if __name__ == "__main__":
    refine_brackets()
