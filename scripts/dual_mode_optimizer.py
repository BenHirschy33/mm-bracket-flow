"""
Dual-Mode Optimizer V2: Analytic Perfectionist Focus
   - MAX_AVG: Maximizes average ESPN score across all backtest years.
   - MAX_PERFECT: Maximizes the analytic Log-Likelihood (probability) of perfect brackets.

Refactored to use Sigmoid (Logistic) win probability for better calibration.
"""
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
import dataclasses
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import SimulationWeights, DEFAULT_WEIGHTS
from scripts.evaluate_weights import evaluate_bracket

logging.basicConfig(level=logging.WARNING, format="%(message)s")

ALL_YEARS = [
    2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
    2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019,
    2021, 2022, 2023, 2024
]

def recency_weight(year):
    return 0.5 + 0.5 * ((year - 2000) / (2024 - 2000))

YEAR_WEIGHTS = {y: recency_weight(y) for y in ALL_YEARS}
N_CORES = min(12, multiprocessing.cpu_count())
EVAL_ITERATIONS = 50  # Balanced for speed and accuracy

def evaluate_all_years(weights: SimulationWeights, iterations=EVAL_ITERATIONS):
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=N_CORES) as executor:
        futures = {executor.submit(evaluate_bracket, yr, weights, iterations): yr for yr in ALL_YEARS}
        for future in concurrent.futures.as_completed(futures):
            yr = futures[future]
            try:
                m = future.result()
                if m["avg_score"] >= 0:
                    m["year"] = yr
                    results.append(m)
            except Exception:
                pass
    return results

def fitness_avg_score(results):
    if not results: return -1000
    scores = [r["avg_score"] * YEAR_WEIGHTS.get(r["year"], 1.0) for r in results]
    # Reward pure score average
    return np.mean(scores) * 10

def fitness_perfect_bracket(results):
    if not results: return -10000
    # log_likelihood is the sum of log(p) of correct outcomes
    # Maximizing this = Maximizing the joint probability of a perfect bracket.
    weighted_ll = np.sum([r.get("log_likelihood", -500.0) * YEAR_WEIGHTS.get(r["year"], 1.0) for r in results])
    return weighted_ll

def jitter_weights(weights: SimulationWeights, step_fraction: float = 0.15) -> SimulationWeights:
    params = vars(weights).copy()
    fields = list(params.keys())
    k = max(2, int(len(fields) * step_fraction))
    targets = random.sample(fields, k=k)
    for field in targets:
        val = params[field]
        if isinstance(val, bool):
            if random.random() < 0.05: params[field] = not val
        elif isinstance(val, (int, float)):
            magnitude = max(0.1, abs(val) * 0.25)
            params[field] = val + random.uniform(-magnitude, magnitude)
            # Basic constraints
            if field == "seed_weight": params[field] = max(0.001, min(0.3, params[field]))
            elif field not in ["luck_weight"]: params[field] = max(0.0, params[field])
    return SimulationWeights(**params)

def run_sweep(mode: str, iterations: int):
    print(f"\n[V2 {mode.upper()}] Starting sweep ({iterations} iters)")
    current = SimulationWeights()
    results = evaluate_all_years(current)
    current_fitness = fitness_avg_score(results) if mode == "avg" else fitness_perfect_bracket(results)
    
    best = current
    best_fitness = current_fitness
    best_results = results

    for i in range(iterations):
        # Adaptive jump size based on iteration
        step = 0.3 * (1.0 - i/iterations) + 0.05
        candidate = jitter_weights(current, step_fraction=step)
        cand_results = evaluate_all_years(candidate)
        cand_fitness = fitness_avg_score(cand_results) if mode == "avg" else fitness_perfect_bracket(cand_results)

        if cand_fitness > current_fitness:
            current, current_fitness = candidate, cand_fitness
            if cand_fitness > best_fitness:
                best, best_fitness, best_results = candidate, cand_fitness, cand_results
                avg = np.mean([r["avg_score"] for r in cand_results])
                ll = np.mean([r.get("log_likelihood", 0) for r in cand_results])
                print(f"[{mode.upper()}] [{i}] NEW BEST Fit={round(best_fitness, 2)} Avg={round(avg,1)} LL={round(ll,1)}")
                save_checkpoint(best, best_fitness, mode, i, avg, ll)
        else:
            # Simulated Annealing acceptance
            temp = 100.0 * (1.0 - i/iterations) + 0.1
            if random.random() < math.exp((cand_fitness - current_fitness) / temp):
                current, current_fitness = candidate, cand_fitness

        if i % 25 == 0:
            print(f"[{mode.upper()}] Progress {i}/{iterations} | Best={round(best_fitness, 2)}")

    return best, best_fitness, best_results

def save_checkpoint(weights: SimulationWeights, fitness: float, mode: str, iteration: int, avg: float, ll: float):
    path = Path(f"agents/optimization/best_{mode}_weights_v2.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(f"Mode={mode} Iteration={iteration} Fitness={fitness} Avg={avg} LL={ll}\n")
        f.write(str(weights))

def write_final_config(avg_weights, avg_meta, perfect_weights, perfect_meta):
    out_path = Path("agents/optimization/gold_standard.json")
    out = {}
    if out_path.exists():
        try:
            with open(out_path, "r") as f: out = json.load(f)
        except: pass
    if avg_meta: out["max_avg"] = {"meta": avg_meta, "weights": dataclasses.asdict(avg_weights)}
    if perfect_meta: out["max_champion"] = {"meta": perfect_meta, "weights": dataclasses.asdict(perfect_weights)}
    with open(out_path, "w") as f: json.dump(out, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--mode", choices=["avg", "perfect", "both"], default="both")
    args = parser.parse_args()

    avg_weights = perf_weights = SimulationWeights()
    avg_meta = perf_meta = {}

    if args.mode in ("avg", "both"):
        best, fit, res = run_sweep("avg", args.iterations)
        avg_meta = {"fitness": fit, "avg_score": np.mean([r["avg_score"] for r in res])}
        avg_weights = best
    if args.mode in ("perfect", "both"):
        best, fit, res = run_sweep("perfect", args.iterations)
        perf_meta = {"fitness": fit, "avg_score": np.mean([r["avg_score"] for r in res]), "ll": np.mean([r.get("log_likelihood") for r in res])}
        perf_weights = best

    write_final_config(avg_weights, avg_meta, perf_weights, perf_meta)
    print("\nV2 Optimization Complete. Gold Standard updated.")
