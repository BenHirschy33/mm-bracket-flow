import random
import sys
from pathlib import Path
from core.config import SimulationWeights
from scripts.mass_backtest import run_mass_backtest
from scripts.evaluate_weights import evaluate_bracket

import math

def get_decay_weight(year, current_year=2026, k=0.05):
    # Exponential decay: e^(-k * delta_t)
    return math.exp(-k * (current_year - year))

def optimize():
    print("--- Starting Multi-Year Parameter Optimization with Decay Weights ---")
    
    best_avg = 0
    best_weights = SimulationWeights()
    
    # Final Deep Sweep Parameters
    iterations = 500
    mc_iters = 25
    decay_rate = 0.07  # Emphasize modern era
    
    years = [2025, 2024, 2023, 2022, 2021, 2019, 2018, 2017, 2016, 2015, 2010, 2005, 2000]
    
    for i in range(iterations):
        test_weights = SimulationWeights()
        test_weights.trb_weight = random.uniform(1.0, 5.0)
        test_weights.to_weight = random.uniform(0.5, 3.0)
        test_weights.sos_weight = random.uniform(2.0, 8.0)
        test_weights.momentum_weight = random.uniform(0.01, 0.1)
        test_weights.efficiency_weight = random.uniform(0.01, 0.05)
        
        weighted_total_score = 0
        total_decay_weight = 0
        
        for y in years:
            score, _ = evaluate_bracket(y, test_weights, iterations=mc_iters)
            decay = get_decay_weight(y, k=decay_rate)
            weighted_total_score += (score * decay)
            total_decay_weight += decay
            
        avg = weighted_total_score / total_decay_weight
        
        if avg > best_avg:
            best_avg = avg
            best_weights = test_weights
            print(f"Iteration {i}: New Best Avg = {round(best_avg, 2)}")
            print(f"  TRB: {round(test_weights.trb_weight, 3)} | SOS: {round(test_weights.sos_weight, 3)}")

    print("\n==========================================")
    print("      OPTIMAL MULTI-YEAR WEIGHTS          ")
    print("==========================================")
    print(f"TRB Weight: {best_weights.trb_weight}")
    print(f"TO Weight: {best_weights.to_weight}")
    print(f"SOS Weight: {best_weights.sos_weight}")
    print(f"Momentum Weight: {best_weights.momentum_weight}")
    print(f"Efficiency Weight: {best_weights.efficiency_weight}")
    print(f"Final Average Cross-Year Score: {round(best_avg, 2)}")
    print("==========================================")
    
    # Save to a new config or report
    with open("optimal_multi_year_weights.txt", "w") as f:
        f.write(f"TRB: {best_weights.trb_weight}\n")
        f.write(f"TO: {best_weights.to_weight}\n")
        f.write(f"SOS: {best_weights.sos_weight}\n")
        f.write(f"Momentum: {best_weights.momentum_weight}\n")
        f.write(f"Efficiency: {best_weights.efficiency_weight}\n")
        f.write(f"Avg Score: {best_avg}\n")

if __name__ == "__main__":
    optimize()
