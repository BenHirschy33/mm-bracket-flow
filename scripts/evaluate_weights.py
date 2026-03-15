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
    except FileNotFoundError:
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

    def get_team_safely(name, teams_dict):
        if name is None: return None
        if name in teams_dict: return teams_dict[name]
        alt_names = [
            name.replace("St.", "State"), name.replace("State", "St."),
            name.replace(" (NY)", ""), name.replace(" (NC)", ""),
            name + " State", name + " St."
        ]
        for alt in alt_names:
            if alt in teams_dict: return teams_dict[alt]
        return None

    for _ in range(iterations):
        sim_score = 0
        final_four_field = []
        
        for region_name, seeds_map in regions.items():
            # Round 1
            r1_winners = []
            for h_seed, l_seed in SEED_MATCHUPS:
                name_h = seeds_map.get(str(h_seed))
                name_l = seeds_map.get(str(l_seed))
                team_h = get_team_safely(name_h, teams_data)
                team_l = get_team_safely(name_l, teams_data)
                
                if team_h and team_l:
                    winner = engine.simulate_game(team_h, team_l, mode=mode)
                    r1_winners.append(winner)
                    if winner.name in actual_r32: sim_score += points[1]
                elif team_h:
                    r1_winners.append(team_h)
                    # No points for a bye to simplify
                elif team_l:
                    r1_winners.append(team_l)

            # Rounds 2 to 4
            current_teams = r1_winners
            round_idx = 2
            while len(current_teams) > 1:
                next_round = []
                for i in range(0, len(current_teams), 2):
                    # In case of odd teams due to byes, carry last one
                    if i + 1 < len(current_teams):
                        t_a = current_teams[i]
                        t_b = current_teams[i+1]
                        winner = engine.simulate_game(t_a, t_b, mode=mode)
                        next_round.append(winner)
                        if round_idx <= 4:
                            if winner.name in actuals[round_idx - 1]:
                                sim_score += points[round_idx]
                    else:
                        next_round.append(current_teams[i])
                
                current_teams = next_round
                round_idx += 1
                
            if current_teams:
                final_four_field.append(current_teams[0])

        # Final Four
        if len(final_four_field) == 4:
            ff1 = engine.simulate_game(final_four_field[0], final_four_field[1], mode=mode)
            ff2 = engine.simulate_game(final_four_field[2], final_four_field[3], mode=mode)
            # 160 points for picking champ game participants isn't strictly in my actual_results, 
            # so we just score the champion (320)
            champ = engine.simulate_game(ff1, ff2, mode=mode)
            if champ.name in actual_champ:
                sim_score += 320
        
        total_score += sim_score

    return total_score / iterations, 1920

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2024)
    args = parser.parse_args()
    
    test_weights = SimulationWeights()
    score, max_score = evaluate_bracket(args.year, test_weights)
    print(f"=====================================")
    print(f"Base Configuration Score: {round(score, 1)} / {max_score} Max")
    print(f"Percentile (Relative to ESPN perfection): {round((score/max_score)*100, 1)}%")
    print(f"=====================================")
