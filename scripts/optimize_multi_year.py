import random
import sys
from pathlib import Path
from core.config import SimulationWeights
from scripts.mass_backtest import run_mass_backtest
from scripts.evaluate_weights import evaluate_bracket

def optimize():
    print("--- Starting Multi-Year Parameter Optimization ---")
    
    best_avg = 0
    best_weights = SimulationWeights()
    
    # Range of metrics to perturb
    # TRB, TO, SOS, Momentum, etc.
    
    for i in range(50): # 50 iterations of improvement
        test_weights = SimulationWeights()
        test_weights.trb_weight = random.uniform(1.0, 5.0)
        test_weights.to_weight = random.uniform(0.5, 3.0)
        test_weights.sos_weight = random.uniform(2.0, 8.0)
        test_weights.momentum_weight = random.uniform(0.01, 0.1)
        test_weights.efficiency_weight = random.uniform(0.01, 0.05)
        
        # Evaluate across the 5 years
        total_score = 0
        years = [2021, 2022, 2023, 2024, 2025]
        for y in years:
            score, _ = evaluate_bracket(y, test_weights, iterations=5)
            total_score += score
            
        avg = total_score / len(years)
        
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
