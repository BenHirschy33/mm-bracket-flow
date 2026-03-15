import json
from pathlib import Path

HISTORICAL_DATA = {
    "2025": {
        "round_of_32": ["Florida", "Duke", "Houston", "Auburn", "UConn", "Kansas", "Arizona", "Purdue"], # Partial
        "sweet_sixteen": ["Florida", "Duke", "Houston", "Auburn"], # Partial
        "elite_eight": ["Florida", "Duke", "Houston", "Auburn"],
        "final_four": ["Florida", "Duke", "Houston", "Auburn"],
        "champion": "Florida"
    },
    "2024": {
        "round_of_32": ["UConn", "San Diego St.", "Illinois", "Iowa St.", "North Carolina", "Alabama", "Clemson", "Arizona", "Houston", "Duke", "North Carolina St.", "Marquette", "Purdue", "Gonzaga", "Creighton", "Tennessee"],
        "sweet_sixteen": ["UConn", "Illinois", "Alabama", "Clemson", "Duke", "North Carolina St.", "Purdue", "Tennessee"],
        "elite_eight": ["UConn", "Alabama", "North Carolina St.", "Purdue"],
        "final_four": ["UConn", "Alabama", "North Carolina St.", "Purdue"],
        "champion": "UConn"
    },
    "2023": {
        "round_of_32": ["Alabama", "San Diego St.", "Creighton", "Princeton", "Purdue", "Florida Atlantic", "Kansas St.", "Michigan St.", "Houston", "Miami", "Xavier", "Texas", "Kansas", "Arkansas", "UConn", "Gonzaga"],
        "sweet_sixteen": ["San Diego St.", "Creighton", "Florida Atlantic", "Kansas St.", "Miami", "Texas", "Arkansas", "UConn"],
        "elite_eight": ["San Diego St.", "Florida Atlantic", "Miami", "UConn"],
        "final_four": ["San Diego St.", "Florida Atlantic", "Miami", "UConn"],
        "champion": "UConn"
    },
    "2022": {
        "round_of_32": ["Gonzaga", "Arkansas", "Texas Tech", "Duke", "Baylor", "North Carolina", "UCLA", "Purdue", "Arizona", "Houston", "Michigan", "Villanova", "Kansas", "Providence", "Iowa St.", "Miami"],
        "sweet_sixteen": ["Arkansas", "Duke", "North Carolina", "UCLA", "Houston", "Michigan", "Villanova", "Providence"],
        "elite_eight": ["Duke", "North Carolina", "Villanova", "Kansas"],
        "final_four": ["North Carolina", "Duke", "Villanova", "Kansas"],
        "champion": "Kansas"
    },
    "2021": {
        "round_of_32": ["Gonzaga", "Creighton", "USC", "Oregon", "Iowa", "Oregon St.", "Loyola Chicago", "Villanova", "Baylor", "Wisconsin", "Villanova", "Arkansas", "Oral Roberts", "Texas Tech", "Alabama", "UCLA"],
        "sweet_sixteen": ["Gonzaga", "Creighton", "USC", "Oregon", "Michigan", "Florida St.", "Alabama", "UCLA", "Baylor", "Villanova", "Arkansas", "Oral Roberts", "Oregon St.", "Loyola Chicago"],
        "elite_eight": ["Gonzaga", "USC", "Michigan", "UCLA", "Baylor", "Arkansas", "Oregon St.", "Houston"],
        "final_four": ["Gonzaga", "UCLA", "Baylor", "Houston"],
        "champion": "Baylor"
    }
}

def populate_results():
    for year, data in HISTORICAL_DATA.items():
        p = Path(f"years/{year}/data/actual_results.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w') as f:
            json.dump(data, f, indent=2)
            print(f"Populated {year} results.")

if __name__ == "__main__":
    populate_results()
