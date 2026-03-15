import argparse
import sys
from pathlib import Path

from core.parser import load_teams, load_bracket
from core.simulator import SimulatorEngine
from core.config import SimulationWeights

# Standard tournament seed matchup ordering for the Round of 64
SEED_MATCHUPS = [
    (1, 16),
    (8, 9),
    (5, 12),
    (4, 13),
    (6, 11),
    (3, 14),
    (7, 10),
    (2, 15)
]

def simulate_region(region_name, seeds_map, teams_data, engine):
    """
    Simulates a single region down to a regional champion (Final Four representative).
    """
    print(f"\n--- Simulating {region_name} Region ---")
    
    # Initialize the Round of 64 Field in the correct bracket order
    current_round_teams = []
    for high_seed, low_seed in SEED_MATCHUPS:
        high_team_name = seeds_map.get(str(high_seed))
        low_team_name = seeds_map.get(str(low_seed))
        
        # If teams are missing, we skip appending them (useful for testing with partial brackets)
        if high_team_name and low_team_name:
            team_high = teams_data.get(high_team_name)
            team_low = teams_data.get(low_team_name)
            
            if team_high and team_low:
                current_round_teams.append(team_high)
                current_round_teams.append(team_low)
            else:
                print(f"Warning: Missing stats for {high_team_name} or {low_team_name}")
                
    round_num = 1
    round_names = {1: "Round of 64", 2: "Round of 32", 3: "Sweet Sixteen", 4: "Elite Eight"}
    
    while len(current_round_teams) > 1:
        print(f"\n>> {round_names.get(round_num, f'Round {round_num}')} <<")
        next_round_teams = []
        
        # Process teams in pairs
        for i in range(0, len(current_round_teams), 2):
            team_a = current_round_teams[i]
            team_b = current_round_teams[i+1]
            
            winner = engine.simulate_game(team_a, team_b)
            prob_a = engine.calculate_win_probability(team_a, team_b)
            
            if winner.name == team_a.name:
                win_pct = prob_a
            else:
                win_pct = 1.0 - prob_a
                
            print(f"  {team_a.name} ({team_a.seed}) vs {team_b.name} ({team_b.seed}) -> {winner.name} wins ({round(win_pct*100, 1)}%)")
            next_round_teams.append(winner)
            
        current_round_teams = next_round_teams
        round_num += 1
        
    regional_champ = current_round_teams[0] if current_round_teams else None
    if regional_champ:
        print(f"\n{region_name} Regional Champion: {regional_champ.name}!")
        
    return regional_champ

def run_tournament(year: int):
    print(f"Loading data for year {year}...")
    base_dir = Path(f"years/{year}/data")
    
    try:
        teams_data = load_teams(base_dir / "team_stats.csv")
        bracket_data = load_bracket(base_dir / "chalk_bracket.json")
    except FileNotFoundError as e:
        print(f"Error loading data: {e}")
        sys.exit(1)
        
    # We can inject custom SimulationWeights here later via CLI args.
    engine = SimulatorEngine()
    
    final_four = []
    
    regions = bracket_data.get("regions", {})
    # Define standard region progression into Final Four (East plays West, South plays Midwest implicitly)
    for region_name, seeds_map in regions.items():
        champ = simulate_region(region_name, seeds_map, teams_data, engine)
        if champ:
            final_four.append(champ)
            
    if len(final_four) < 4:
        print("\nNot enough data to run a full Final Four.")
        return
        
    print("\n==============================")
    print("         FINAL FOUR           ")
    print("==============================")
    
    # Simple hardcode for now depending on order of dictionary keys
    # Usually: Team 0 vs Team 1, Team 2 vs Team 3
    ff_winner_1 = engine.simulate_game(final_four[0], final_four[1])
    print(f"Final Four: {final_four[0].name} vs {final_four[1].name} -> {ff_winner_1.name} wins!")
    
    ff_winner_2 = engine.simulate_game(final_four[2], final_four[3])
    print(f"Final Four: {final_four[2].name} vs {final_four[3].name} -> {ff_winner_2.name} wins!")
    
    print("\n==============================")
    print("     NATIONAL CHAMPIONSHIP    ")
    print("==============================")
    
    national_champ = engine.simulate_game(ff_winner_1, ff_winner_2)
    print(f"Championship: {ff_winner_1.name} vs {ff_winner_2.name} -> {national_champ.name} wins!")
    
    print(f"\n🏆 {national_champ.name} ARE THE {year} NATIONAL CHAMPIONS! 🏆\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the MM-Bracket-Flow simulation.")
    parser.add_argument("--year", type=int, default=2026, help="Year of the tournament to simulate")
    args = parser.parse_args()
    run_tournament(args.year)
