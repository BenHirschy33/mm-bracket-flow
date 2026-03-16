from dataclasses import dataclass

@dataclass
class SimulationWeights:
    """
    Configurable weights for the simulation engine.
    Set a weight to 0.0 to completely disable that metric's impact.
    Increase past 1.0 to over-index on a metric.
    """
    # Ultra-Deep Era-Agnostic Optimized Defaults (500 iterations, 2000-2025)
    trb_weight: float = 0.0
    to_weight: float = 6.046
    sos_weight: float = 7.635
    momentum_weight: float = 0.424
    efficiency_weight: float = 0.180
    ft_weight: float = 1.246
    three_par_weight: float = 0.0  # New research metric
    pace_variance_weight: float = 0.0  # Upset probability multiplier
    
    # Phase 4: Foul Drawing & Chaos Metrics
    foul_drawing_weight: float = 0.0
    stl_weight: float = 0.0
    blk_weight: float = 0.0
    orb_weight: float = 0.0
    neutral_weight: float = 0.0           # Rewards neutral site performance
    non_conf_weight: float = 0.0          # Rewards non-conference readiness
    def_ft_rate_weight: float = 0.0
    
    # Intuition / Manual Factors
    # Phase 4: Volatility & Luck
    luck_weight: float = 0.0
    due_factor_sensitivity: float = 0.0  # Self-correction multiplier
    momentum_regression_weight: float = 0.0 # Dampens extreme streaks
    road_dominance_weight: float = 0.0      # Rewards road warriors
    seed_weight: float = 0.02              # Win prob bonus per seed rank diff
    ast_weight: float = 0.0               # Rewards unselfish cohesion
    three_par_volatility_weight: float = 0.0 # Adjusts variance for 3P-heavy teams
    ts_weight: float = 0.0                # True Shooting % advantage
    experience_weight: float = 0.0        # Rewards seasoned stability
    late_round_def_premium: float = 0.0   # Defense multiplier per round
    depth_weight: float = 0.0             # Rewards bench resilience in late rounds
    continuity_weight: float = 0.0        # Rewards system/roster stability
    pace_control_weight: float = 0.0      # Rewards teams that control the tempo
    cinderella_factor: float = 0.0        # Multiplier for high-variance underdog bias
    luck_regression_weight: float = 0.0   # Penalty for over-performing Win% (Phase 9)
    star_reliance_weight: float = 0.0     # Penalty for dependency on star scorers (Phase 9)
    
    # Phase 2: 2025 Indicators (Research Hub)
    orb_density_weight: float = 0.0      # Multiplier for historic OR% (>34%)
    continuation_rule_bias: float = 0.0  # Volatility shift for aggressive slashers

    # Phase 3: Coach & Tempo (Research Loop 1)
    coach_tournament_weight: float = 0.0  # Rewards coaches with deep tournament experience
    tempo_upset_weight: float = 0.0       # Slow-tempo underdogs reduce the talent gap

    # Intuition weight: Disabled
    intuition_weight: float = 0.0

    # General modifiers
    # Multiplier to value defense slightly more in March (since defense travels)
    defense_premium: float = 7.236

    # Chaos Engine Toggle (Phase 3)
    chaos_mode: bool = False

# Optimizer-tuned defaults (500-iteration SA sweep, CV fitness 170.31)
DEFAULT_WEIGHTS = SimulationWeights(
    efficiency_weight=0.204,
    to_weight=6.860,
    ft_weight=2.028,
    three_par_weight=0.069,
    pace_variance_weight=0.079,
    momentum_weight=0.417,
    sos_weight=10.106,
    foul_drawing_weight=0.0,
    stl_weight=0.514,
    blk_weight=0.0,
    orb_weight=0.832,
    luck_weight=-0.975,
    due_factor_sensitivity=0.022,
    momentum_regression_weight=0.228,
    road_dominance_weight=0.073,
    seed_weight=0.024,
    ast_weight=0.109,
    three_par_volatility_weight=0.037,
    ts_weight=0.0,
    experience_weight=0.004,
    late_round_def_premium=0.047,
    depth_weight=0.100,
    continuity_weight=0.052,
    pace_control_weight=0.264,
    cinderella_factor=0.183,
    luck_regression_weight=0.0,
    star_reliance_weight=0.193,
    neutral_weight=0.515,
    non_conf_weight=0.365,
    def_ft_rate_weight=0.404,
    intuition_weight=0.0,
    defense_premium=6.680,
    orb_density_weight=0.0,
    continuation_rule_bias=0.012,
    coach_tournament_weight=0.193,
    tempo_upset_weight=0.112
)



# Optimized for #11-#15 seed upsets (Derived via optimize_chaos.py)
CHAOS_WEIGHTS = SimulationWeights(
    trb_weight=0.0,
    to_weight=9.276,
    sos_weight=9.182,
    momentum_weight=3.131,
    efficiency_weight=2.226,
    ft_weight=0.552,
    three_par_weight=10.269,
    pace_variance_weight=2.720,
    defense_premium=17.004,
    chaos_mode=True,
    foul_drawing_weight=2.0,  # Chaos teams draw fouls
    stl_weight=1.5,      # Chaos teams disrupt
    blk_weight=0.0,
    orb_weight=1.0
)
