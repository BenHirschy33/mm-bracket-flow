import json
from pathlib import Path
from core.simulator import SimulatorEngine
from core.parser import load_teams
from core.config import SimulationWeights

def evaluate_bracket(year: int, weights: SimulationWeights):
    """
    Runs the simulation with the provided weights and scores it against
    the actual_results.json for that year.
    Returns a score based on standard ESPN bracket rules (10, 20, 40, 80, 160, 320).
    """
    base_dir = Path(f"years/{year}/data")
    
    try:
        teams_data = load_teams(base_dir / "team_stats.csv")
        with open(base_dir / "actual_results.json", 'r') as f:
            actual_results = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading evaluation data: {e}")
        return 0

    # Build the engine with the provided weights
    engine = SimulatorEngine(weights=weights)
    
    # We will simulate the same matchups that happened in reality
    # For now, as a placeholder test, if actual_results isn't structured yet:
    print(f"Loaded actual results for {year}. Ready to score bracket.")
    
    score = 0
    # In a full run, we would iterate through actual_results and check if engine.predict(teamA, teamB) matches the winner.
    
    return score

if __name__ == "__main__":
    test_weights = SimulationWeights() # Default
    score = evaluate_bracket(2025, test_weights)
    print(f"Base Configuration Score: {score}")
