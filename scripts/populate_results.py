import json
from pathlib import Path

# Expanded dataset (1985 is the start of the 64-team era)
# This is a sample of the expansion. In a real scenario, this would be a full DB.
HISTORICAL_DATA = {
    "2025": {"champion": "Florida", "final_four": ["Florida", "Duke", "Houston", "Auburn"]},
    "2024": {"champion": "UConn", "final_four": ["UConn", "Alabama", "NC State", "Purdue"]},
    "2023": {"champion": "UConn", "final_four": ["UConn", "San Diego St.", "Miami", "FAU"]},
    "2022": {"champion": "Kansas", "final_four": ["Kansas", "UNC", "Duke", "Villanova"]},
    "2021": {"champion": "Baylor", "final_four": ["Baylor", "Gonzaga", "Houston", "UCLA"]},
    "2019": {"champion": "Virginia", "final_four": ["Virginia", "Texas Tech", "Michigan St.", "Auburn"]},
    "2018": {"champion": "Villanova", "final_four": ["Villanova", "Michigan", "Kansas", "Loyola Chicago"]},
    "2017": {"champion": "UNC", "final_four": ["UNC", "Gonzaga", "Oregon", "South Carolina"]},
    "2016": {"champion": "Villanova", "final_four": ["Villanova", "UNC", "Oklahoma", "Syracuse"]},
    "2015": {"champion": "Duke", "final_four": ["Duke", "Wisconsin", "Kentucky", "Michigan St."]},
    "2014": {"champion": "UConn", "final_four": ["UConn", "Kentucky", "Florida", "Wisconsin"]},
    "2013": {"champion": "Louisville", "final_four": ["Louisville", "Michigan", "Wichita St.", "Syracuse"]},
    "2012": {"champion": "Kentucky", "final_four": ["Kentucky", "Kansas", "Ohio St.", "Louisville"]},
    "2011": {"champion": "UConn", "final_four": ["UConn", "Butler", "Kentucky", "VCU"]},
    "2010": {"champion": "Duke", "final_four": ["Duke", "Butler", "West Virginia", "Michigan St."]},
    "2005": {"champion": "UNC", "final_four": ["UNC", "Illinois", "Louisville", "Michigan St."]},
    "2000": {"champion": "Michigan St.", "final_four": ["Michigan St.", "Florida", "UNC", "Wisconsin"]},
    "1990": {"champion": "UNLV", "final_four": ["UNLV", "Duke", "Georgia Tech", "Arkansas"]},
    "1985": {"champion": "Villanova", "final_four": ["Villanova", "Georgetown", "St. John's", "Memphis"]}
}

def populate_results():
    for year, data in HISTORICAL_DATA.items():
        p = Path(f"years/{year}/data/actual_results.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        # We ensure round information exists even if empty for the engine
        full_data = {
            "round_of_32": data.get("round_of_32", []),
            "sweet_sixteen": data.get("sweet_sixteen", []),
            "elite_eight": data.get("elite_eight", []),
            "final_four": data.get("final_four", []),
            "champion": data.get("champion", "")
        }
        with open(p, 'w') as f:
            json.dump(full_data, f, indent=2)
            print(f"Populated {year} results.")

if __name__ == "__main__":
    populate_results()
