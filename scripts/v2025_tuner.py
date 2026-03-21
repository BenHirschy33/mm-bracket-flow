import json
import logging
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import SimulationWeights

def get_v2025_adjustments(indicators_path="docs/spec/v2025_indicators.json"):
    """
    Parses v2025_indicators.json and returns a dict of suggested weight overrides.
    """
    path = Path(indicators_path)
    if not path.exists():
        logging.warning(f"Indicators file not found: {path}")
        return {}

    try:
        with open(path, "r") as f:
            data = json.load(f)
            
        adjustments = {}
        
        # 1. Volatility Markers
        vol = data.get("volatility_markers", {})
        if "continuation_rule" in vol:
            adjustments["continuation_rule_bias"] = 0.7  # Suggested starting value
        if "orb_density" in vol:
            adjustments["orb_density_weight"] = 1.1
            
        # 2. Luck Regression
        luck = data.get("luck_regression", {})
        if luck.get("config_param") == "luck_regression_weight":
            adjustments["luck_regression_weight"] = 0.06
            
        # 3. Research Loop 1
        research = data.get("research_loop_1", {})
        
        # Coach Moxie
        coach = research.get("coach_tournament_moxie", {})
        if "coach_tournament_weight" in coach.get("config_param", ""):
            adjustments["coach_tournament_weight"] = 0.35
            
        # Tempo Upset
        tempo = research.get("tempo_upset_strategy", {})
        if "tempo_upset_weight" in tempo.get("config_param", ""):
            adjustments["tempo_upset_weight"] = 0.57
            
        # Roster Continuity
        continuity = research.get("roster_continuity", {})
        if "continuity_weight" in continuity.get("config_param", ""):
            # Heuristic: "(bumped from 0.121 to 0.250)"
            adjustments["continuity_weight"] = 0.25
            
        return adjustments
    except Exception as e:
        logging.error(f"Failed to parse v2025 indicators: {e}")
        return {}

def apply_tuner_to_weights(weights: SimulationWeights, adjustments: dict):
    """Applies adjustments to a SimulationWeights instance."""
    for field, val in adjustments.items():
        if hasattr(weights, field):
            setattr(weights, field, val)
    return weights

if __name__ == "__main__":
    adjustments = get_v2025_adjustments()
    print("V2025 Indicator Adjustments:")
    for k, v in adjustments.items():
        print(f"  {k}: {v}")
