import argparse
import sys
from pathlib import Path
from collections import defaultdict

from core.parser import load_teams, load_bracket
from core.simulator import SimulatorEngine
from core.config import SimulationWeights
from scripts.run_bracket import SEED_MATCHUPS

def run_monte_carlo(year: int, iterations: int):
    print(f"Loading data for year {year}...")
    base_dir = Path(f"years/{year}/data")
    
    try:
        teams_data = load_teams(base_dir / "team_stats.csv", year=year)
        bracket_data = load_bracket(base_dir / "chalk_bracket.json")
    except FileNotFoundError as e:
        print(f"Error loading data: {e}")
        sys.exit(1)
        
    engine = SimulatorEngine()
    
    # Tracking dictionaries: { team_name: count }
    results_tracker = {
        "Sweet 16": defaultdict(int),
        "Elite 8": defaultdict(int),
        "Final 4": defaultdict(int),
        "Championship": defaultdict(int)
    }
    
    regions_map = bracket_data.get("regions", {})
    
    print(f"\nRunning {iterations} Monte Carlo simulations for {year}...")
    
    # Progress bar configuration
    print_interval = max(1, iterations // 10)
    
    for i in range(iterations):
        if i > 0 and i % print_interval == 0:
            print(f"  ... {i}/{iterations} simulations completed")
            
        final_four = []
        
        # Simulate each region
        for region_name, seeds_map in regions_map.items():
            current_round_teams = []
            for high_seed, low_seed in SEED_MATCHUPS:
                ht_name = seeds_map.get(str(high_seed))
                lt_name = seeds_map.get(str(low_seed))
                if ht_name and lt_name:
                    current_round_teams.extend([teams_data[ht_name], teams_data[lt_name]])
            
            round_num = 1
            while len(current_round_teams) > 1:
                next_round = []
                for j in range(0, len(current_round_teams), 2):
                    winner = engine.simulate_game(current_round_teams[j], current_round_teams[j+1], mode="probabilistic")
                    next_round.append(winner)
                    
                    if round_num == 2: # Entering Sweet 16
                        results_tracker["Sweet 16"][winner.name] += 1
                    elif round_num == 3: # Entering Elite 8
                        results_tracker["Elite 8"][winner.name] += 1
                    elif round_num == 4: # Regional Champ (Final 4)
                        results_tracker["Final 4"][winner.name] += 1
                        
                current_round_teams = next_round
                round_num += 1
                
            if current_round_teams:
                final_four.append(current_round_teams[0])
                
        # Final Four matches
        if len(final_four) == 4:
            ff_winner_1 = engine.simulate_game(final_four[0], final_four[1], mode="probabilistic")
            ff_winner_2 = engine.simulate_game(final_four[2], final_four[3], mode="probabilistic")
            champ = engine.simulate_game(ff_winner_1, ff_winner_2, mode="probabilistic")
            results_tracker["Championship"][champ.name] += 1

    print("\n==========================================")
    print("      MONTE CARLO TOURNAMENT REPORT       ")
    print("==========================================")
    
    for round_name, tracker in results_tracker.items():
        print(f"\n--- Probable {round_name} Teams ---")
        # Sort by most frequent appearances
        sorted_teams = sorted(tracker.items(), key=lambda x: x[1], reverse=True)
        # Display top 15 most likely for the round
        for rank, (team, count) in enumerate(sorted_teams[:15], 1):
            seed = teams_data[team].seed if team in teams_data else "?"
            pct = (count / iterations) * 100
            print(f"{rank:2}. {team:<20} (Seed {seed:>2}) - {pct:>5.1f}%")
            
    print("\n--- 👠 CINDERELLA WATCH (Seeds 10+) ---")
    cinderellas = []
    # Identify low seeds moving to Sweet 16 or beyond frequently
    s16_tracker = results_tracker["Sweet 16"]
    for team, count in s16_tracker.items():
        if team in teams_data and teams_data[team].seed >= 10:
            pct = (count / iterations) * 100
            if pct > 5.0: # At least a 5% chance of Sweet 16
                cinderellas.append((team, teams_data[team].seed, pct))
                
    if cinderellas:
        cinderellas.sort(key=lambda x: x[2], reverse=True)
        print("Most Likely Double-Digit Seeds to reach Sweet 16:")
        for team, seed, pct in cinderellas[:10]:
            print(f"  {team} ({seed}) -> {pct:.1f}%")
    else:
        print("  Algorithm favors chalk this year. No highly likely Cinderellas.")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monte Carlo Simulator for Cinderellas")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    
    run_monte_carlo(args.year, args.iterations)
