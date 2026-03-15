from dataclasses import dataclass

@dataclass
class SimulationWeights:
    """
    Configurable weights for the simulation engine.
    Set a weight to 0.0 to completely disable that metric's impact.
    Increase past 1.0 to over-index on a metric.
    """
    # Era-Agnostic Optimized Defaults (2000-2025)
    trb_weight: float = 4.895
    to_weight: float = 2.846
    sos_weight: float = 7.635
    momentum_weight: float = 0.073
    efficiency_weight: float = 0.022
    
    # Intuition weight: 1 point = 1% probability shift
    intuition_weight: float = 0.01

    # General modifiers
    # Multiplier to value defense slightly more in March (since defense travels)
    defense_premium: float = 1.566

# Standard instance to use across the app if no custom one is provided
DEFAULT_WEIGHTS = SimulationWeights()
