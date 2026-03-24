import json
import logging
import sys
import os
import math
import random
import numpy as np
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.simulator import SimulatorEngine
from core.parser import load_teams, load_bracket, normalize_team_name
from core.team_model import Team
from core.config import SimulationWeights

SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]

def evaluate_bracket(year: int, weights: SimulationWeights, iterations: int = 1):
    """
    Standard ESPN Bracket Scoring with Log-Likelihood for Perfect Bracket targeting.
    """
    base_dir = Path(f"years/{year}/data")
    
    try:
        teams_data = load_teams(base_dir / "team_stats.csv", year=year)
        bracket_data = load_bracket(base_dir / "chalk_bracket.json")
        with open(base_dir / "actual_results.json", 'r') as f:
            actual_results = json.load(f)
            if "champion" not in actual_results:
                return {"avg_score": -1.0, "log_likelihood": -1000.0}
    except FileNotFoundError:
        return {"avg_score": -1.0, "log_likelihood": -1000.0}

    engine = SimulatorEngine(teams=teams_data, weights=weights)
    
    # Pre-calculate actuals
    actual_r32 = {normalize_team_name(n) for n in actual_results.get("round_of_32", [])}
    actual_s16 = {normalize_team_name(n) for n in actual_results.get("sweet_sixteen", [])}
    actual_e8 = {normalize_team_name(n) for n in actual_results.get("elite_eight", [])}
    actual_ff = {normalize_team_name(n) for n in actual_results.get("final_four", [])}
    actual_champion = normalize_team_name(actual_results.get("champion", ""))
    actuals = [actual_r32, actual_s16, actual_e8, actual_ff]

    # --- Step 1: Analytic Log-Likelihood (Perfect Bracket Probability) ---
    # We walk through the ACTUAL bracket games and sum log(P_winner).
    # This is deterministic and requires only 1 walkthrough of the actual results.
    total_log_likelihood = 0.0
    
    def get_team_safely(name, teams_dict):
        if not name: return None
        norm_name = normalize_team_name(name)
        return teams_dict.get(norm_name) or teams_dict.get(name)

    # Reconstruct the tournament path of actual winners
    # This is complex because we need the matchups that actually happened.
    # Simpler proxy: Sum log(P(actual_winner vs actual_loser)) for all 63 games.
    # For now, we use a simplified likelihood: sum of log(P(actual_winner wins round X))
    # which is a very strong proxy for the joint probability.
    
    # --- Step 2: Monte Carlo Simulation (for Avg Score) ---
    total_score = 0
    champion_hits = 0
    elite_hits = 0
    perfect_hits = 0
    peak_score = 0
    
    points = {1: 10, 2: 20, 3: 40, 4: 80, 5: 160, 6: 320}
    regions = bracket_data.get("regions", {})

    all_scores = []
    for _ in range(iterations):
        engine.reset_state()
        sim_score = 0
        final_four_field = []
        
        for region_name, seeds_map in regions.items():
            current_teams = []
            # Round 1
            for h_seed, l_seed in SEED_MATCHUPS:
                t_h_name = seeds_map.get(str(h_seed)) or "TBD"
                t_l_name = seeds_map.get(str(l_seed)) or "TBD"
                
                t_h = get_team_safely(t_h_name, teams_data) or Team(name=t_h_name, seed=h_seed, off_efficiency=100.0, def_efficiency=100.0, off_ppg=70.0, def_ppg=70.0)
                t_l = get_team_safely(t_l_name, teams_data) or Team(name=t_l_name, seed=l_seed, off_efficiency=100.0, def_efficiency=100.0, off_ppg=70.0, def_ppg=70.0)

                t_h.seed = h_seed
                t_l.seed = l_seed
                
                if t_h and t_l:
                    prob_h = engine.calculate_win_probability(t_h, t_l, round_num=1)
                    winner_name = t_h.name if random.random() < prob_h else t_l.name
                    winner = teams_data.get(winner_name) or Team(name=winner_name, seed=16, off_efficiency=100.0, def_efficiency=100.0, off_ppg=70.0, def_ppg=70.0)
                    current_teams.append(winner)
                    
                    if _ == 0:
                        actual_winner_name = t_h.name if normalize_team_name(t_h.name) in actual_r32 else t_l.name
                        p_correct = prob_h if actual_winner_name == t_h.name else (1.0 - prob_h)
                        total_log_likelihood += math.log(max(0.001, p_correct))
                    
                    if normalize_team_name(winner.name) in actual_r32: sim_score += points[1]
                else:
                    current_teams.append(t_h or t_l)

            # Rounds 2-4
            for r_idx in range(2, 5):
                next_round = []
                for i in range(0, len(current_teams), 2):
                    t_a, t_b = current_teams[i], current_teams[i+1]
                    prob_a = engine.calculate_win_probability(t_a, t_b, round_num=r_idx)
                    winner_name = t_a.name if random.random() < prob_a else t_b.name
                    winner = teams_data.get(winner_name) or Team(name=winner_name, seed=16, off_efficiency=100.0, def_efficiency=100.0, off_ppg=70.0, def_ppg=70.0)
                    next_round.append(winner)
                    
                    if _ == 0:
                        is_a_actual = normalize_team_name(t_a.name) in actuals[r_idx-1]
                        is_b_actual = normalize_team_name(t_b.name) in actuals[r_idx-1]
                        if is_a_actual: total_log_likelihood += math.log(max(0.001, prob_a))
                        elif is_b_actual: total_log_likelihood += math.log(max(0.001, 1.0 - prob_a))
                    
                    if normalize_team_name(winner.name) in actuals[r_idx-1]: sim_score += points[r_idx]
                current_teams = next_round
            
            final_four_field.append(current_teams[0])

        if len(final_four_field) == 4:
            ff1_name = engine.simulate_matchup(final_four_field[0].name, final_four_field[1].name, round_num=5)
            ff2_name = engine.simulate_matchup(final_four_field[2].name, final_four_field[3].name, round_num=5)
            champ_name = engine.simulate_matchup(ff1_name, ff2_name, round_num=6)
            if normalize_team_name(champ_name) == actual_champion:
                sim_score += points[6]
                champion_hits += 1
        
        total_score += sim_score
        all_scores.append(sim_score)
        if sim_score > peak_score: peak_score = sim_score
        if sim_score >= 800: elite_hits += 1
        if sim_score == 1920: perfect_hits += 1

    sorted_scores = sorted(all_scores, reverse=True)
    top_subset = sorted_scores[:max(10, int(iterations * 0.01))]

    return {
        "avg_score": total_score / iterations,
        "log_likelihood": total_log_likelihood, 
        "champion_accuracy": champion_hits / iterations,
        "elite_rate": elite_hits / iterations,
        "perfect_rate": perfect_hits / iterations,
        "peak_score": float(peak_score),
        "top_scores": top_subset 
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2024)
    args = parser.parse_args()
    metrics = evaluate_bracket(args.year, SimulationWeights(), iterations=100)
    print(f"Results for {args.year}: Avg={metrics['avg_score']}, Likelihood={round(metrics['log_likelihood'], 2)}")
