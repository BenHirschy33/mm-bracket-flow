from dataclasses import dataclass

@dataclass
class SimulationWeights:
    """
    Configurable weights for the simulation engine.
    Set a weight to 0.0 to completely disable that metric's impact.
    Increase past 1.0 to over-index on a metric.
    """
    # Multi-year optimized defaults (2021-2025)
    trb_weight: float = 2.195
    to_weight: float = 1.976
    sos_weight: float = 5.530
    momentum_weight: float = 0.084
    efficiency_weight: float = 0.018
    
    # Intuition weight: 1 point = 1% probability shift
    intuition_weight: float = 0.01

    # General modifiers
    # Multiplier to value defense slightly more in March (since defense travels)
    defense_premium: float = 1.566

# Standard instance to use across the app if no custom one is provided
DEFAULT_WEIGHTS = SimulationWeights()
