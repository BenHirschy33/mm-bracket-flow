import argparse
import sys
import math
import random
import logging
import numpy as np
import os
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set start method to spawn for clean multiprocessing with numpy/sys.path
# Removed multiprocessing.set_start_method

from core.config import SimulationWeights
from scripts.evaluate_weights import evaluate_bracket

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Full historical window (2015-2025, excluding 2020)
YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]

def get_multi_year_results(weights: SimulationWeights, years_list, iterations=100):
    """Calculates metrics across years LINEARLY to avoid macOS process leaks."""
    results = []
    for year in years_list:
        try:
            # High-precision: 100 internal Monte Carlo runs per year
            metrics = evaluate_bracket(year, weights, iterations)
            if metrics["avg_score"] >= 0:
                metrics["year"] = year
                results.append(metrics)
        except Exception as e:
            logging.error(f"Year {year} failed: {e}")
    return results

def recency_weight(year):
    return 0.5 + 0.5 * ((year - 2015) / (2025 - 2015))

def cross_validate_weights(weights: SimulationWeights, mode: str = "balanced"):
    """
    Performs Weighted Log-Likelihood fitness calculation (Linear).
    """
    results = get_multi_year_results(weights, YEARS)
    if not results:
        return -100000, 0, 0
    
    weighted_ll = np.sum([r.get("log_likelihood", -500.0) * recency_weight(r["year"]) for r in results])
    
    avg_score = np.mean([r["avg_score"] for r in results])
    avg_accuracy = np.mean([r["champion_accuracy"] for r in results])
    perfect_rate = np.mean([r["perfect_rate"] for r in results])
    
    if mode == "perfect":
        fitness = (weighted_ll * 2.0) + (perfect_rate * 20000)
    elif mode == "average":
        fitness = (avg_score * 3.0) + (weighted_ll * 0.5)
    else: # "balanced"
        fitness = weighted_ll + (avg_score * 0.2) + (perfect_rate * 8000)
    
    return fitness, avg_score, avg_accuracy

def optimize_simulated_annealing(iterations=100000, mode="balanced", jitter_scale=1.0):
    """
    Stable Linear Optimizer V4. No multiprocessing = No process leaks.
    """
    start_time = time.time()
    current_weights = SimulationWeights()
    current_fitness, current_avg, current_acc = cross_validate_weights(current_weights, mode=mode)
    
    best_weights = current_weights
    best_fitness = current_fitness
    best_avg = current_avg
    best_acc = current_acc
    
    print(f"\n🚀 STARTING LINEAR STABLE OPTIMIZATION V4 ({mode.upper()} FOCUS)...")
    print(f"Window: 2015-2025 | Iterations: {iterations}")
    print(f"Current Fitness: {round(current_fitness, 2)} | Avg Score: {round(current_avg, 1)} | Champ: {round(current_acc * 100, 1)}%")
    print("===============================================================================\n")

    try:
        for i in range(iterations):
            # Dynamic Jitter
            new_params = vars(current_weights).copy()
            fields = list(new_params.keys())
            
            temp_sa = 1.0 - (i / iterations)
            k = max(2, int(len(fields) * (0.1 + 0.2 * temp_sa)))
            jitter_targets = random.sample(fields, k=k)
            
            for field in jitter_targets:
                val = new_params[field]
                if isinstance(val, bool):
                    if random.random() < 0.05: 
                        new_params[field] = not val
                elif isinstance(val, (int, float)):
                    magnitude = max(0.1, abs(val) * (0.1 + 0.4 * temp_sa) * jitter_scale)
                    step = random.uniform(-magnitude, magnitude)
                    new_val = val + step
                    
                    if field == "seed_weight":
                        new_params[field] = max(0.001, min(0.3, new_val))
                    elif field == "defense_premium":
                        new_params[field] = max(1.0, min(50.0, new_val))
                    elif field == "luck_weight":
                        new_params[field] = new_val
                    elif field == "base_volatility":
                        new_params[field] = max(0.0, min(1.0, new_val))
                    elif "pct" in field or "rate" in field:
                        new_params[field] = max(0, min(100, new_val))
                    else:
                        new_params[field] = max(0, new_val)

            new_weights = SimulationWeights(**new_params)
            new_fitness, new_avg, new_acc = cross_validate_weights(new_weights, mode=mode)
            
            if new_fitness > current_fitness:
                current_weights = new_weights
                current_fitness = new_fitness
                
                if new_fitness > best_fitness:
                    best_weights = new_weights
                    best_fitness = new_fitness
                    best_avg = new_avg
                    best_acc = new_acc
                    print(f"[{mode}] [{i}] ⭐ NEW BEST! Fit: {round(best_fitness, 2)} | Avg: {round(best_avg, 1)} | Champ: {round(best_acc * 100, 1)}%")
                    save_weights(best_weights, best_fitness, best_avg, best_acc, i, mode=mode)
            else:
                delta = new_fitness - current_fitness
                accept_prob = math.exp(delta / max(0.01, 50.0 * temp_sa))
                if random.random() < accept_prob:
                    current_weights = new_weights
                    current_fitness = new_fitness

            if i > 0 and i % 100 == 0:
                elapsed = time.time() - start_time
                iter_rate = i / elapsed
                remaining_iters = iterations - i
                eta_seconds = remaining_iters / iter_rate
                
                def fmt_time(s):
                    h = int(s // 3600); m = int((s % 3600) // 60); s = int(s % 60)
                    return f"{h:02d}:{m:02d}:{s:02d}"

                print(f"[{mode}] Progress: {i}/{iterations} ({round(i/iterations*100, 1)}%) | Best: {round(best_fitness, 1)} | Elapsed: {fmt_time(elapsed)} | ETA: {fmt_time(eta_seconds)}", flush=True)

    except KeyboardInterrupt:
        print("\nOptimization paused by user. Saving results...", flush=True)
    finally:
        save_weights(best_weights, best_fitness, best_avg, best_acc, "FINAL", mode=mode)
        print("\n=======================================================", flush=True)
        print(f"Final Peak Fitness: {round(best_fitness, 2)}", flush=True)
        print(f"Final Model Performance: {round(best_avg, 2)} avg points", flush=True)
        print(f"Final Champion Certainty: {round(best_acc * 100, 1)}%", flush=True)
        print("Optimization Complete.", flush=True)
        print("=======================================================", flush=True)

def save_weights(weights, fitness, avg, acc, iteration, mode="unknown"):
    try:
        import dataclasses, json
        # Save mode-specific text file for human review
        save_path = Path(f"agents/optimization/best_weights_{mode}.txt")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            f.write(f"Metadata: Iteration={iteration}, Fitness={fitness}, AvgPoints={avg}, ChampAcc={acc}, Mode={mode}\n")
            f.write(str(weights))
        
        # Save JSON version for specific mode promotion
        json_path = Path(f"agents/optimization/last_best_weights_{mode}.json")
        with open(json_path, "w") as f:
            json.dump(dataclasses.asdict(weights), f, indent=2)
    except Exception as e:
        logging.error(f"Save failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100000)
    parser.add_argument("--jitter-scale", type=float, default=1.0)
    parser.add_argument("--mode", type=str, choices=["balanced", "average", "perfect"], default="balanced")
    parser.add_argument("--dry-run", action="store_true", help="Run once without optimizing to verify metrics")
    args = parser.parse_args()
    
    if args.dry_run:
        print(f"--- DRY RUN ({args.mode.upper()}) ---")
        fit, avg, acc = cross_validate_weights(SimulationWeights(), mode=args.mode)
        print(f"Baseline Fitness: {fit:.2f} | Avg: {avg:.2f} | Champ: {acc*100:.1f}%")
    else:
        optimize_simulated_annealing(iterations=args.iterations, mode=args.mode, jitter_scale=args.jitter_scale)
