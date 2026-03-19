import argparse
import sys
import math
import random
import logging
import numpy as np
import concurrent.futures
import multiprocessing
import os
from pathlib import Path

# Set start method to spawn for clean multiprocessing with numpy/sys.path
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeException:
    pass

from core.config import SimulationWeights
from scripts.evaluate_weights import evaluate_bracket

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Full historical window (2011-2024, excluding 2020)
YEARS = [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024]

def get_multi_year_results(weights: SimulationWeights, years_list, iterations=50):
    """Calculates metrics across years in parallel with stability focus."""
    results = []
    # Use max_workers=10 based on system thread count
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(10, multiprocessing.cpu_count())) as executor:
        future_to_year = {executor.submit(evaluate_bracket, year, weights, iterations): year for year in years_list}
        for future in concurrent.futures.as_completed(future_to_year):
            year = future_to_year[future]
            try:
                metrics = future.result()
                if metrics["avg_score"] >= 0:
                    metrics["year"] = year
                    results.append(metrics)
            except Exception as e:
                logging.error(f"Year {year} failed: {e}")
    return results

def cross_validate_weights(weights: SimulationWeights):
    """
    Performs stability-first fitness calculation.
    Fitness = sum(log(score)) * 50 + (Champ Acc * 1000) + (Elite Rate * 2000) - (Volatility)
    """
    results = get_multi_year_results(weights, YEARS)
    if not results:
        return 0, 0, 0
    
    # Use log to heavily penalize years with low scores, forcing consistency (Stability)
    # The user wants scores to be "the exact same" across years.
    scores = [r["avg_score"] for r in results]
    log_scores = [np.log(max(1, s)) for s in scores]
    
    accuracies = [r["champion_accuracy"] for r in results]
    elite_rates = [r["elite_rate"] for r in results]
    
    avg_score = np.mean(scores)
    avg_accuracy = np.mean(accuracies)
    avg_elite_rate = np.mean(elite_rates)
    std_score = np.std(scores)
    
    # Stability Score: Rewards bringing the "bottom" up more than pushing the "top" higher
    fitness = (np.sum(log_scores) * 50) + (avg_accuracy * 1000) + (avg_elite_rate * 2500) - (std_score * 3)
    return fitness, avg_score, avg_accuracy

def optimize_simulated_annealing(iterations=100000, cooling_rate=0.99998):
    """
    Exhaustive "Gold Standard" Optimization.
    Dynamically scans and jitters EVERY field in SimulationWeights.
    """
    current_weights = SimulationWeights()
    current_fitness, current_avg, current_acc = cross_validate_weights(current_weights)
    
    best_weights = current_weights
    best_fitness = current_fitness
    best_avg = current_avg
    best_acc = current_acc
    
    print(f"\n🚀 STARTING EXHAUSTIVE PHASE 6 SWEEP...")
    print(f"Window: 2011-2024 | Iterations: {iterations}")
    print(f"Current Fitness: {round(current_fitness, 2)} | Avg Score: {round(current_avg, 1)} | Champ: {round(current_acc * 100, 1)}%")
    print("===============================================================================\n")

    try:
        for i in range(iterations):
            temp_sa = iterations - i
            
            # Dynamic Jitter Core: Pull all parameters from the current best
            # This implements the user's "any and all metrics" requirement.
            new_params = vars(current_weights).copy()
            fields = list(new_params.keys())
            
            # Jitter 15-20% of fields per iteration to explore correlations
            k = max(2, len(fields) // 6)
            jitter_targets = random.sample(fields, k=k)
            
            for field in jitter_targets:
                val = new_params[field]
                if isinstance(val, bool):
                    if random.random() < 0.02: # Rare toggle
                        new_params[field] = not val
                elif isinstance(val, (int, float)):
                    # Adaptive jitter based on field name
                    # Primary weights get larger exploration range
                    if any(x in field for x in ["premium", "sos", "to", "eff", "weight"]):
                        step = random.uniform(-0.5, 0.5)
                    else:
                        step = random.uniform(-0.1, 0.1)
                    
                    new_val = val + step
                    
                    # Resilience Constraints
                    if field == "seed_weight":
                        new_params[field] = max(0.001, min(0.3, new_val))
                    elif field == "defense_premium":
                        new_params[field] = max(1.0, min(50.0, new_val))
                    elif field == "luck_weight":
                        new_params[field] = new_val # Allowed negative for regression
                    else:
                        new_params[field] = max(0, new_val)

            new_weights = SimulationWeights(**new_params)
            new_fitness, new_avg, new_acc = cross_validate_weights(new_weights)
            
            # Acceptance logic
            if new_fitness > current_fitness:
                # Update current and check if it's a global best
                current_weights = new_weights
                current_fitness = new_fitness
                
                if new_fitness > best_fitness:
                    best_weights = new_weights
                    best_fitness = new_fitness
                    best_avg = new_avg
                    best_acc = new_acc
                    print(f"[{i}] ⭐ NEW GLOBAL BEST! Fit: {round(best_fitness, 2)} | Avg: {round(best_avg, 1)} | Champ: {round(best_acc * 100, 1)}%")
                    
                    # Periodic Save to prevent data loss during long runs
                    if i % 10 == 0:
                        save_weights(best_weights, best_fitness, best_avg, best_acc, i)
            else:
                delta = new_fitness - current_fitness
                # Standard Simulated Annealing Acceptance
                if random.random() < math.exp(delta / max(1.0, temp_sa / 100.0)):
                    current_weights = new_weights
                    current_fitness = new_fitness

            if i % 100 == 0:
                print(f"Progress: {i}/{iterations} | Best Fitness: {round(best_fitness, 2)} | Progress: {round(i/iterations*100, 2)}%")

    except KeyboardInterrupt:
        print("\nOptimization paused by user. Saving results...")
    finally:
        save_weights(best_weights, best_fitness, best_avg, best_acc, "FINAL")
        print("\n=======================================================")
        print(f"Final Peak Fitness: {round(best_fitness, 2)}")
        print(f"Final Model Performance: {round(best_avg, 2)} avg points")
        print(f"Final Champion Certainty: {round(best_acc * 100, 1)}%")
        print("Optimization Complete.")
        print("=======================================================")

def save_weights(weights, fitness, avg, acc, iteration):
    try:
        save_path = Path("agents/optimization/best_weights.txt")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            f.write(f"Metadata: Iteration={iteration}, Fitness={fitness}, AvgPoints={avg}, ChampAcc={acc}\n")
            f.write(str(weights))
    except Exception as e:
        logging.error(f"Save failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100000)
    args = parser.parse_args()
    optimize_simulated_annealing(iterations=args.iterations)
