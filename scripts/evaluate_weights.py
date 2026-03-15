import json
import sys
from pathlib import Path
from core.simulator import SimulatorEngine
from core.parser import load_teams, load_bracket
from core.config import SimulationWeights

SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]

def evaluate_bracket(year: int, weights: SimulationWeights):
    """
    Standard ESPN Bracket Scoring:
    Round of 64 picks: 10 pts per correct pick
    Round of 32 (Sweet 16 teams): 20 pts per correct pick
    Sweet 16 (Elite 8 teams): 40 pts per correct pick
    Elite 8 (Final 4 teams): 80 pts per correct pick
    Final 4 (Championship teams): 160 pts per correct pick
    Champion: 320 pts per correct pick
    """
    base_dir = Path(f"years/{year}/data")
    
    try:
        teams_data = load_teams(base_dir / "team_stats.csv", year=year)
        bracket_data = load_bracket(base_dir / "chalk_bracket.json") # Base structure definition
        with open(base_dir / "actual_results.json", 'r') as f:
            actual_results = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading evaluation data: {e}")
        return 0

    engine = SimulatorEngine(weights=weights)
    score = 0
    max_score = 1920 # 320 + 320 + 320 + 320 + 320 + 320
    
    # What really happened (who made it TO the next round)
    actual_r32 = set(actual_results.get("round_of_32", [])) # 32 teams who WON their first game
    actual_s16 = set(actual_results.get("sweet_sixteen", []))
    actual_e8 = set(actual_results.get("elite_eight", []))
    actual_ff = set(actual_results.get("final_four", []))
    actual_champ = set([actual_results.get("champion", "")])
    
    actuals = [actual_r32, actual_s16, actual_e8, actual_ff] # We only have 4 explicit array levels, + champ
    
    points = {1: 10, 2: 20, 3: 40, 4: 80, 5: 160, 6: 320}
    
    regions = bracket_data.get("regions", {})
    final_four_teams = []
    
    # SIMULATE THE BRACKET ONCE AND TRACK ROUND-BY-ROUND PREDICTIONS
    predicted_rounds = {1: [], 2: [], 3: [], 4: []}
    
    for region_name, seeds_map in regions.items():
        # INITIAL REGION FIELD (16 teams)
        current_round_teams = []
        for high_seed, low_seed in SEED_MATCHUPS:
            ht_name = seeds_map.get(str(high_seed))
            lt_name = seeds_map.get(str(low_seed))
            if ht_name and lt_name:
                current_round_teams.extend([teams_data[ht_name], teams_data[lt_name]])
        
        round_num = 1
        # Loop until Regional Champ (Round 4 completed)
        while len(current_round_teams) > 1:
            next_round_teams = []
            for i in range(0, len(current_round_teams), 2):
                team_a = current_round_teams[i]
                team_b = current_round_teams[i+1]
                winner = engine.simulate_game(team_a, team_b)
                next_round_teams.append(winner)
                predicted_rounds[round_num].append(winner.name)
            
            # Score this region's picks for this round
            actual_advancers = actuals[round_num - 1]
            for pick in next_round_teams:
                if pick.name in actual_advancers:
                    score += points[round_num]
            
            current_round_teams = next_round_teams
            round_num += 1
            
        if current_round_teams:
            final_four_teams.append(current_round_teams[0])

    # Final Four -> Championship Scoring
    if len(final_four_teams) == 4:
        # Score the picks for making the Championship game (we don't have the runner up in actuals, so we just proxy check the FF winner against actual champ?)
        # Wait, the ESPN bracket rewards you if you picked a team to make the championship, IF they actually made the championship.
        # Since we only have the champion, we'll give 160 points if one of our FF winners is the actual champ. 
        # Ideally actual_results would have "championship_game": ["Conn", "Purdue"]
        # For this script we will skip the Title Game 160pt logic specifically, and just score the Champion.
        pass
        
        ff_winner_1 = engine.simulate_game(final_four_teams[0], final_four_teams[1])
        ff_winner_2 = engine.simulate_game(final_four_teams[2], final_four_teams[3])
        champ = engine.simulate_game(ff_winner_1, ff_winner_2)
        
        # If we pick the actual champion, we get 320 points
        if champ.name in actual_champ:
            score += 320

    return score, max_score

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    args = parser.parse_args()
    
    test_weights = SimulationWeights() # Defaults
    score, max_score = evaluate_bracket(args.year, test_weights)
    print(f"=====================================")
    print(f"Base Configuration Score: {score} / {1920} Max")
    print(f"Percentile (Relative to ESPN perfection): {round((score/1920)*100, 1)}%")
    print(f"=====================================")
