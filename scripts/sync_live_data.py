import json
import logging
import requests
from pathlib import Path
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Mapping logic for ESPN team names to internal names
TEAM_MAP = {
    "UConn Huskies": "Connecticut",
    "UConn": "Connecticut",
    "TCU Horned Frogs": "TCU",
    "Duke Blue Devils": "Duke",
    "North Carolina Tar Heels": "North Carolina",
    "UNC": "North Carolina",
    "Kansas Jayhawks": "Kansas",
    "Kentucky Wildcats": "Kentucky",
    "UCLA Bruins": "UCLA",
    "Indiana Hoosiers": "Indiana",
    "Villanova Wildcats": "Villanova",
    "Michigan State Spartans": "Michigan State",
    "Gonzaga Bulldogs": "Gonzaga",
    "Purdue Boilermakers": "Purdue",
    "Alabama Crimson Tide": "Alabama",
    "Houston Cougars": "Houston",
    "Arizona Wildcats": "Arizona",
    "Tennessee Volunteers": "Tennessee",
    "Illinois Fighting Illini": "Illinois",
    "Creighton Bluejays": "Creighton",
    "Marquette Golden Eagles": "Marquette",
    "Baylor Bears": "Baylor",
    "Iowa State Cyclones": "Iowa State",
    "Texas Longhorns": "Texas",
    "Auburn Tigers": "Auburn",
    "Florida Gators": "Florida",
    "Wisconsin Badgers": "Wisconsin",
    "NC State Wolfpack": "NC State",
    "San Diego State Aztecs": "San Diego State",
    "Saint Mary's Gaels": "Saint Mary's (CA)",
    "Loyola Chicago Ramblers": "Loyola (IL)",
    "St. John's Red Storm": "St. John's (NY)",
    "Connecticut Huskies": "Connecticut",
    "Texas A&M Aggies": "Texas A&M",
    "Oklahoma Sooners": "Oklahoma",
    "Utah State Aggies": "Utah State",
}

def clean_team_name(espn_name):
    """Cleans ESPN team name by checking map and stripping common suffixes and nicknames."""
    # 0. Check hardcoded Map first
    if espn_name in TEAM_MAP:
        return TEAM_MAP[espn_name]
    
    # 1. Strip common suffixes and nicknames
    nicknames = [
        "Huskies", "Horned Frogs", "Blue Devils", "Tar Heels", "Jayhawks", "Wildcats", "Bruins", "Hoosiers", "Spartans", "Bulldogs", "Boilermakers", 
        "Crimson Tide", "Cougars", "Volunteers", "Fighting Illini", "Bluejays", "Golden Eagles", "Bears", "Cyclones", "Longhorns", "Tigers", 
        "Gators", "Badgers", "Wolfpack", "Aztecs", "Gaels", "Ramblers", "Red Storm", "Aggies", "Sooners", "Cavaliers", "Red Raiders", "Hurricanes", 
        "Hawkeyes", "Minutemen", "Ducks", "Beavers", "Commodores", "Gamecocks", "Mountaineers", "Bulls", "Knights", "Owls", "Panthers", "Seminoles"
    ]
    
    cleaned = espn_name
    for nick in nicknames:
        if cleaned.endswith(f" {nick}"):
            cleaned = cleaned.replace(f" {nick}", "").strip()
            break
            
    # 2. Specific fixes
    if cleaned == "Miami": cleaned = "Miami (FL)"
    if cleaned == "NC State": cleaned = "NC State"
    if cleaned == "UConn": cleaned = "Connecticut"
    if cleaned == "Penn State": cleaned = "Penn State"
    if cleaned == "Ohio State": cleaned = "Ohio State"
    if cleaned == "Michigan State": cleaned = "Michigan State"
    if cleaned == "Florida State": cleaned = "Florida State"
    if cleaned == "Arizona State": cleaned = "Arizona State"
    if cleaned == "Kansas State": cleaned = "Kansas State"
    if cleaned == "Iowa State": cleaned = "Iowa State"
    if cleaned == "Oklahoma State": cleaned = "Oklahoma State"
    if cleaned == "Oregon State": cleaned = "Oregon State"
    if cleaned == "Mississippi State": cleaned = "Mississippi State"
    
    return cleaned

def get_ncaa_round(event):
    """Heuristics to determine the NCAA tournament round from ESPN event data."""
    # Look at description or notes
    description = ""
    if "competitions" in event and len(event["competitions"]) > 0:
        comp = event["competitions"][0]
        if "notes" in comp and len(comp["notes"]) > 0:
            description = comp["notes"][0].get("headline", "").lower()
    
    if not description:
        description = event.get("shortName", "").lower()

    if "first round" in description or "1st round" in description:
        return "round_of_32"
    if "second round" in description or "2nd round" in description:
        return "sweet_sixteen"
    if "sweet 16" in description or "sweet sixteen" in description or "regional semifinal" in description:
        return "elite_eight"
    if "elite 8" in description or "elite eight" in description or "regional final" in description:
        return "final_four"
    if "final four" in description or "national semifinal" in description:
        return "championship_finalists" # Intermediate
    if "national championship" in description or "final" in description:
        return "champion"
    
    return None

def sync_live_data(year=2026):
    url = "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logging.error(f"Failed to fetch ESPN data: {e}")
        return

    base_dir = Path(f"years/{year}/data")
    actual_results_path = base_dir / "actual_results.json"
    
    if actual_results_path.exists():
        with open(actual_results_path, 'r') as f:
            content = f.read().strip()
            actual_results = json.loads(content) if content else {}
    else:
        actual_results = {
            "round_of_32": [],
            "sweet_sixteen": [],
            "elite_eight": [],
            "final_four": [],
            "champion": ""
        }

    updates_found = False
    events = data.get("events", [])
    for event in events:
        status = event.get("status", {}).get("type", {}).get("name", "")
        if status != "STATUS_FINAL":
            continue
            
        round_key = get_ncaa_round(event)
        if not round_key:
            # Fallback check if it's the post-season
            if data.get("leagues", [{}])[0].get("season", {}).get("type") != 3: # 3 is post-season
                 continue
            # If it's a game today and final, maybe we can't detect the round
            # Skip for now to avoid pollution from non-tournament games
            continue

        # Extract winner
        winner_name = None
        competitions = event.get("competitions", [])
        if competitions:
            competitors = competitions[0].get("competitors", [])
            for comp in competitors:
                if comp.get("winner") is True:
                    winner_name = clean_team_name(comp.get("team", {}).get("displayName", ""))
                    break
        
        if winner_name:
            if round_key not in actual_results:
                if round_key == "champion":
                    actual_results[round_key] = None
                else:
                    actual_results[round_key] = []

            if round_key == "champion":
                if actual_results["champion"] != winner_name:
                    actual_results["champion"] = winner_name
                    updates_found = True
                    logging.info(f"New Champion: {winner_name}")
            elif round_key == "championship_finalists":
                 # Not directly in our JSON structure, but could be useful
                 pass
            else:
                if winner_name not in actual_results[round_key]:
                    actual_results[round_key].append(winner_name)
                    updates_found = True
                    logging.info(f"Added {winner_name} to {round_key}")
                    logging.info(f"Added {winner_name} to {round_key}")

    if updates_found:
        with open(actual_results_path, 'w') as f:
            json.dump(actual_results, f, indent=2)
        logging.info(f"Updated actual_results.json for {year}")
    else:
        logging.info(f"No new tournament updates found for {year}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2026)
    args = parser.parse_args()
    sync_live_data(args.year)
