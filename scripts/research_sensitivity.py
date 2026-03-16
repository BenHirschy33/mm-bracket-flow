
import sys
from pathlib import Path
import numpy as np

# Ensure we use the local core package
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import DEFAULT_WEIGHTS, SimulationWeights
from scripts.evaluate_weights import evaluate_bracket

YEARS = [2021, 2022, 2023, 2024, 2025]

def test_sensitivity():
    baseline = DEFAULT_WEIGHTS
    metrics = [
        "efficiency_weight", "to_weight", "ft_weight", "three_par_weight",
        "sos_weight", "defense_premium", "orb_weight", "luck_weight",
        "neutral_weight", "non_conf_weight", "seed_weight"
    ]
    
    results = {}
    
    print("Calculating baseline performance...")
    baseline_scores = []
    for y in YEARS:
        s, _ = evaluate_bracket(y, baseline, iterations=5)
        baseline_scores.append(s)
    baseline_avg = np.mean(baseline_scores)
    print(f"Baseline Avg Score: {baseline_avg}")

    for metric in metrics:
        print(f"Testing sensitivity for {metric}...")
        # Jitter the metric by +20%
        original_val = getattr(baseline, metric)
        jitter = original_val * 0.2 if original_val != 0 else 0.5
        
        new_params = {k: getattr(baseline, k) for k in baseline.__dict__}
        new_params[metric] = original_val + jitter
        
        test_weights = SimulationWeights(**new_params)
        
        test_scores = []
        for y in YEARS:
            s, _ = evaluate_bracket(y, test_weights, iterations=20)
            test_scores.append(s)
        
        test_avg = np.mean(test_scores)
        sensitivity = abs(test_avg - baseline_avg)
        results[metric] = sensitivity
        print(f"{metric}: Δ Score = {sensitivity:.2f}")

    print("\nRESUTLS SUMMARY (Sorted by Sensitivity):")
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    for m, s in sorted_results:
        print(f"{m}: {s:.2f}")

if __name__ == "__main__":
    test_sensitivity()
