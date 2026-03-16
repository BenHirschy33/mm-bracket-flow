import sys
import os
import csv
import json
import time
from pathlib import Path
from io import StringIO

# Ensure local dependencies are prioritised
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "local_lib"))

import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup

def fetch_tournament_results(year: int):
    """
    Fetches the NCAA tournament results for a given year from Sports Reference.
    """
    url = f"https://www.sports-reference.com/cbb/postseason/{year}-ncaa.html"
    scraper = cloudscraper.create_scraper()
    
    print(f"Fetching results for {year} from {url}...")
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch {url}: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # We want to find the winners of each round.
        # Sports Reference structure for brackets is complex, but we can look for 'winner' classes or similar.
        # Alternatively, we can find all games and their winners.
        
        results = {
            "round_of_32": [],
            "sweet_sixteen": [],
            "elite_eight": [],
            "final_four": [],
            "champion": ""
        }
        
        # Find all winner divs in the page
        winners = soup.find_all('div', class_='winner')
        
        winner_counts = {}
        for winner in winners:
            link = winner.find('a')
            if link and '/cbb/schools/' in link['href']:
                name = link.text.strip()
                winner_counts[name] = winner_counts.get(name, 0) + 1
        
        # Sort by wins
        sorted_winners = sorted(winner_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Mapping wins to round reached:
        # Win 1 Game -> Round of 32 Participant
        # Win 2 Games -> Sweet Sixteen Participant
        # Win 3 Games -> Elite Eight Participant
        # Win 4 Games -> Final Four Participant
        # Win 6 Games -> Champion (in some structures, win 5 = Final, win 6 = Champ)
        
        results["round_of_32"] = [t for t, c in winner_counts.items() if c >= 1]
        results["sweet_sixteen"] = [t for t, c in winner_counts.items() if c >= 2]
        results["elite_eight"] = [t for t, c in winner_counts.items() if c >= 3]
        results["final_four"] = [t for t, c in winner_counts.items() if c >= 4]
        
        if sorted_winners:
            # The champion is the one with 6 wins (or the most)
            results["champion"] = sorted_winners[0][0]

        # Save to file
        output_path = Path(f"years/{year}/data/actual_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"✅ Global winner count results saved for {year}: {len(winner_counts)} winners found.")
                
        # Save to file
        output_path = Path(f"years/{year}/data/actual_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"✅ Flexible results saved for {year}")
        
    except Exception as e:
        print(f"Error fetching results for {year}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        year = int(sys.argv[1])
        fetch_tournament_results(year)
    else:
        # Default to 2024
        fetch_tournament_results(2024)
