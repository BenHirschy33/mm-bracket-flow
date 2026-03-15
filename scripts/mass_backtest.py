import argparse
import sys
from pathlib import Path
from core.config import SimulationWeights
from scripts.evaluate_weights import evaluate_bracket

def run_mass_backtest(iterations=100, years=[2021, 2022, 2023, 2024, 2025]):
    print(f"--- Starting Mass Monte Carlo Backtest ({iterations} iterations per year) ---")
    
    overall_total_score = 0
    available_years = 0
    
    results = {}
    
    weights = SimulationWeights() # Uses the optimized defaults
    
    for year in years:
        print(f"Evaluating {year}...")
        avg_score, max_possible = evaluate_bracket(year, weights, iterations=iterations)
        
        # If score is 0, it likely means we are missing actual_results.json for that year
        if avg_score > 0:
            results[year] = avg_score
            overall_total_score += avg_score
            available_years += 1
            print(f"  {year} Average Score: {round(avg_score, 1)} / {max_possible}")
        else:
            print(f"  {year} Skipped: Missing historical results or bracket data.")
            
    if available_years > 0:
        grand_avg = overall_total_score / available_years
        print("\n=======================================================")
        print("          FINAL CROSS-YEAR PERFORMANCE REPORT")
        print("=======================================================")
        print(f"Grand Average ESPN Score: {round(grand_avg, 1)} / 1920")
        print(f"Performance across {available_years} years.")
        
        for yr, score in results.items():
            print(f"  - {yr}: {round(score, 1)}")
        print("=======================================================")
    else:
        print("\nNo historical data found for backtesting. Please ensure 'actual_results.json' exists in each year directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iter", type=int, default=100)
    args = parser.parse_args()
    
    run_mass_backtest(iterations=args.iter)
