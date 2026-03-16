import argparse
import sys
import math
import random
import logging
from pathlib import Path

# Ensure we use the local core package
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import SimulationWeights
from scripts.evaluate_weights import evaluate_bracket

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Years to use for multi-year optimization (focus on modern era)
YEARS = [2018, 2019, 2021, 2022, 2023, 2024]

def get_multi_year_score(weights: SimulationWeights):
    """Calculates the average score across multiple tournament years."""
    total_score = 0
    count = 0
    for year in YEARS:
        score, _ = evaluate_bracket(year, weights)
        if score > 0: # Skip if data is missing
            total_score += score
            count += 1
    return total_score / count if count > 0 else 0

def optimize_simulated_annealing(iterations=2000, temp=1.0, cooling_rate=0.999):
    """
    Final Deep Optimization Sweep.
    Focuses on locking in the dominant SOS/Efficiency/Defense pillars.
    """
    # Start with current optimized weights
    current_weights = SimulationWeights()
    current_score = get_multi_year_score(current_weights)
    
    best_weights = current_weights
    best_score = current_score
    
    print(f"Starting Final Deep Optimization Sweep...")
    print(f"Initial Multi-Year Score: {round(current_score, 2)}")
    
    for i in range(iterations):
        # Precise tweaks for fine-tuning
        new_params = {
            "trb_weight": 0.0,
            "to_weight": max(0, current_weights.to_weight + random.uniform(-0.2, 0.2)),
            "sos_weight": max(0, current_weights.sos_weight + random.uniform(-0.5, 0.5)),
            "momentum_weight": max(0, current_weights.momentum_weight + random.uniform(-0.01, 0.01)),
            "efficiency_weight": max(0, current_weights.efficiency_weight + random.uniform(-0.01, 0.01)),
            "ft_weight": max(0, current_weights.ft_weight + random.uniform(-0.05, 0.05)),
            "three_par_weight": 0.0,
            "pace_variance_weight": 0.0,
            "defense_premium": max(0.5, current_weights.defense_premium + random.uniform(-0.2, 0.2)),
            "intuition_weight": 0.0
        }
        
        new_weights = SimulationWeights(**new_params)
        new_score = get_multi_year_score(new_weights)
        
        # Acceptance probability
        if new_score > current_score:
            acceptance_prob = 1.0
        else:
            # Boltzman distribution (even if score is worse, maybe accept it to escape local optima)
            # Dividing by temp allows higher exploration early on
            acceptance_prob = math.exp((new_score - current_score) / max(0.0001, temp))
            
        if random.random() < acceptance_prob:
            current_weights = new_weights
            current_score = new_score
            
            if current_score > best_score:
                best_score = current_score
                best_weights = new_weights
                print(f"[{i}] New Global Best! Score: {round(best_score, 2)} | Temp: {round(temp, 4)}")
        
        # Cool down
        temp *= cooling_rate
        
        if i % 100 == 0:
            print(f"Iter {i}/{iterations} | Temp: {round(temp, 4)} | Best Score: {round(best_score, 2)}")

    print("\n=======================================================")
    print(f"Optimization Complete!")
    print(f"Final Best Multi-Year Score: {round(best_score, 2)}")
    print(f"Best Configuration: \n{best_weights}")
    print("=======================================================")
    
    # Save results to a file
    with open("optimal_multi_year_weights.txt", "w") as f:
        f.write(f"Multi-Year Best Score: {best_score}\n")
        f.write(str(best_weights))
    
    return best_weights

if __name__ == "__main__":
    optimize_simulated_annealing(iterations=1000)
