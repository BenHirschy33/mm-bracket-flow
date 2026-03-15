from dataclasses import dataclass

@dataclass
class SimulationWeights:
    """
    Configurable weights for the simulation engine.
    Set a weight to 0.0 to completely disable that metric's impact.
    Increase past 1.0 to over-index on a metric.
    """
    # 1.0 means baseline mathematical strength. 0.0 means off.
    pythagorean_weight: float = 1.0
    pace_variance_weight: float = 1.0
    efg_matchup_weight: float = 1.0
    turnover_matchup_weight: float = 1.0
    sos_weight: float = 1.0
    momentum_weight: float = 1.0
    intuition_weight: float = 0.015  # Default: 1.5% probability shift per Hirschy point

    # General modifiers
    # Multiplier to value defense slightly more in March (since defense travels)
    defense_premium: float = 1.1

# Standard instance to use across the app if no custom one is provided
DEFAULT_WEIGHTS = SimulationWeights()
