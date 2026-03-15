import json
import sys
from pathlib import Path
from core.simulator import SimulatorEngine
from core.parser import load_teams, load_bracket
from core.config import SimulationWeights

SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]

def evaluate_bracket(year: int, weights: SimulationWeights, iterations: int = 1):
    """
    Standard ESPN Bracket Scoring with optional Monte Carlo support.
    """
    base_dir = Path(f"years/{year}/data")
    
    try:
        teams_data = load_teams(base_dir / "team_stats.csv", year=year)
        bracket_data = load_bracket(base_dir / "chalk_bracket.json")
        with open(base_dir / "actual_results.json", 'r') as f:
            actual_results = json.load(f)
    except FileNotFoundError as e:
        return 0, 1920

    engine = SimulatorEngine(weights=weights)
    total_score = 0
    
    # Pre-calculate actuals
    actual_r32 = set(actual_results.get("round_of_32", []))
    actual_s16 = set(actual_results.get("sweet_sixteen", []))
    actual_e8 = set(actual_results.get("elite_eight", []))
    actual_ff = set(actual_results.get("final_four", []))
    actual_champ = set([actual_results.get("champion", "")])
    actuals = [actual_r32, actual_s16, actual_e8, actual_ff]
    
    points = {1: 10, 2: 20, 3: 40, 4: 80, 5: 160, 6: 320}
    regions = bracket_data.get("regions", {})
    mode = "probabilistic" if iterations > 1 else "deterministic"

    for _ in range(iterations):
        sim_score = 0
        final_four_teams = []
        
        for region_name, seeds_map in regions.items():
            current_round_teams = []
            # Re-initialize SEED_MATCHUPS for each iteration if it's meant to be a fresh bracket setup
            # However, SEED_MATCHUPS is a global constant, so it doesn't need to be re-declared here.
            # The original code had it inside the loop, which is redundant.
            # Keeping it as per the instruction, but noting it's not strictly necessary.
            # SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
            for high_seed, low_seed in SEED_MATCHUPS:
                ht_name = seeds_map.get(str(high_seed))
                lt_name = seeds_map.get(str(low_seed))
                if ht_name and lt_name:
                    current_round_teams.extend([teams_data[ht_name], teams_data[lt_name]])
            
            round_num = 1
            while len(current_round_teams) > 1:
                next_round_teams = []
                for i in range(0, len(current_round_teams), 2):
                    winner = engine.simulate_game(current_round_teams[i], current_round_teams[i+1], mode=mode)
                    next_round_teams.append(winner)
                    
                    # Score this pick for advancing to the next round
                    # actuals[round_num - 1] contains teams that advanced TO round_num + 1
                    # So if round_num is 1 (R64 games), actuals[0] is actual_r32 (teams that advanced to R32)
                    if winner.name in actuals[round_num - 1]:
                        sim_score += points[round_num]
                
                current_round_teams = next_round_teams
                round_num += 1
            
            if current_round_teams:
                final_four_teams.append(current_round_teams[0])

        if len(final_four_teams) == 4:
            ff_winner_1 = engine.simulate_game(final_four_teams[0], final_four_teams[1], mode=mode)
            ff_winner_2 = engine.simulate_game(final_four_teams[2], final_four_teams[3], mode=mode)
            champ = engine.simulate_game(ff_winner_1, ff_winner_2, mode=mode)
            if champ.name in actual_champ:
                sim_score += 320
        
        total_score += sim_score

    return total_score / iterations, 1920

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    
    test_weights = SimulationWeights() # Defaults
    score, max_score = evaluate_bracket(args.year, test_weights)
    print(f"=====================================")
    print(f"Base Configuration Score: {score} / {1920} Max")
    print(f"Percentile (Relative to ESPN perfection): {round((score/1920)*100, 1)}%")
    print(f"=====================================")
