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
    
    # Rounds 11-15: Fine-Grained Context
    travel_weight: float = 0.0             # Penalty for dist > 150mi
    pressure_weight: float = 0.0           # Resilience in late game
    chemistry_weight: float = 0.0          # Portal reliance penalty
    freshman_weight: float = 0.0           # Usage concentration penalty for frosh
    
    # Rounds 16-20: Roster & Depth Suite
    backcourt_weight: float = 0.0          # Guard play resilience vs pressure
    bench_synergy_weight: float = 0.0      # Bonus for bench rebounding/shooting
    whistle_mastery_weight: float = 0.0    # Synergy of foul drawing + conversion
    heating_up_weight: float = 0.0         # Late-season momentum stability
    
    # Rounds 21-25: Strategy & Adaptability
    adjustment_weight: float = 0.0         # Halftime adjustment efficacy (Coaching)
    zone_defense_weight: float = 0.0       # Effectiveness against high 3PAr teams
    foul_management_weight: float = 0.0    # Resilience vs whistle/depth gap
    clutch_execution_weight: float = 0.0   # Last-minute efficiency (TO/FT synergy)
    
    # Rounds 26-30: Post-Season Volatility
    conference_weight: float = 0.0          # Multi-bid conference reliability boost
    neutral_variance_weight: float = 0.0    # Neutral site scoring consistency
    rust_penalty: float = 0.0              # Long layoff penalty for top seeds
    rhythm_bonus: float = 0.0              # Momentum from play-in/close R64 win
    
    # Rounds 31-33: Final Convergence
    hirschy_factor_weight: float = 0.0     # Composite metric dominance
    blue_blood_bonus: float = 0.0          # Historical program success weight
    
    # Global Modifiers
    defense_premium: float = 6.479         # Global multiplier for defensive metrics
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

    # Phase 5: Fatigue & Orchestration
    fatigue_sensitivity: float = 0.0      # Penalty for short rest (R32, E8, Champ)
    bench_rest_bonus: float = 0.0         # Rewards deep teams on short rest

    # Intuition weight: Disabled
    intuition_weight: float = 0.0

    # General modifiers
    # Multiplier to value defense slightly more in March (since defense travels)
    defense_premium: float = 7.236

    # Chaos Engine Toggle (Phase 3)
    chaos_mode: bool = False

# Optimizer-tuned defaults (1000-iteration SA sweep, CV fitness 178.40)
DEFAULT_WEIGHTS = SimulationWeights(
    efficiency_weight=0.153,
    to_weight=6.532,
    ft_weight=0.335,
    three_par_weight=1.607,
    pace_variance_weight=0.018,
    momentum_weight=0.435,
    sos_weight=7.688,
    foul_drawing_weight=0.0,
    stl_weight=0.408,
    blk_weight=0.420,
    orb_weight=1.170,
    luck_weight=-0.258,
    due_factor_sensitivity=0.027,
    momentum_regression_weight=0.024,
    road_dominance_weight=0.427,
    seed_weight=0.022,
    ast_weight=0.0,
    three_par_volatility_weight=0.134,
    ts_weight=0.400,
    experience_weight=0.0,
    late_round_def_premium=0.080,
    depth_weight=0.0,
    continuity_weight=0.120,
    pace_control_weight=0.0,
    cinderella_factor=0.096,
    luck_regression_weight=0.628,
    star_reliance_weight=0.228,
    neutral_weight=1.404,
    non_conf_weight=0.420,
    def_ft_rate_weight=1.092,
    intuition_weight=0.0,
    defense_premium=7.395,
    orb_density_weight=0.187,
    continuation_rule_bias=0.005,
    coach_tournament_weight=0.135,
    tempo_upset_weight=0.0
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
