import json
import os
import dataclasses
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class SimulationWeights:
    # --- Performance & Efficiency ---
    trb_weight: float = 0.7106
    to_weight: float = 3.0491
    sos_weight: float = 0.6871
    momentum_weight: float = 0.1890
    efficiency_weight: float = 0.8647
    ft_weight: float = 1.0187
    three_par_weight: float = 0.8523
    pace_variance_weight: float = 3.4712
    foul_drawing_weight: float = 1.3781
    stl_weight: float = 0.0
    blk_weight: float = 0.4708
    orb_weight: float = 0.3818
    
    # --- Context & Environment ---
    neutral_weight: float = 1.0658
    non_conf_weight: float = 0.0782
    def_ft_rate_weight: float = 0.4491
    travel_weight: float = 0.4336
    pressure_weight: float = 1.6113
    chemistry_weight: float = 2.0138
    freshman_weight: float = 0.6155
    backcourt_weight: float = 1.1825
    bench_synergy_weight: float = 1.5210
    whistle_mastery_weight: float = 0.5343
    heating_up_weight: float = 0.6400
    adjustment_weight: float = 0.2256
    zone_defense_weight: float = 0.6174
    foul_management_weight: float = 0.2809
    clutch_execution_weight: float = 1.0818
    conference_weight: float = 2.1071
    neutral_variance_weight: float = 0.5738
    rust_penalty: float = 0.1749
    rhythm_bonus: float = 0.6864
    intuition_factor_weight: float = 5.7845
    blue_blood_bonus: float = 0.3211
    shot_clock_weight: float = 3.8487
    drought_weight: float = 1.0724
    follow_up_weight: float = 1.6911
    stopper_weight: float = 1.8550
    three_volatility_weight: float = 0.5708
    timeout_weight: float = 6.7800
    proximity_weight: float = 0.7297
    foul_resilience_weight: float = 1.0040
    ot_depth_weight: float = 1.7028
    usage_fatigue_weight: float = 0.0707
    portal_chemistry_weight: float = 0.6749
    rust_reset_weight: float = 0.7833
    playin_rhythm_weight: float = 3.1556
    three_def_sos_weight: float = 8.1002
    backcourt_exp_weight: float = 0.2946
    rim_protection_weight: float = 0.1250
    choke_factor_weight: float = 0.3945
    
    # --- Advanced Multi-Era Signals (2025/2026 Ready) ---
    defensive_grit_bias: float = 0.3899
    three_point_dominance: float = 0.1410
    rim_pressure_multiplier: float = 0.2669
    pace_sensitivity: float = 0.4562
    zone_efficiency_weight: float = 1.3265
    press_disruption_weight: float = 1.9569
    pace_control_weight: float = 0.0
    rotation_depth_weight: float = 6.2704
    half_adjustment_v2: float = 0.4690
    mid_major_boost: float = 0.0
    cinderella_momentum: float = 0.4356
    auto_qualifier_rhythm: float = 1.0317
    seed_12_5_bias: float = 0.1296
    clutch_efficiency_weight: float = 1.9688
    short_bench_boost: float = 0.0855
    pressure_stability_weight: float = 1.4025
    coach_clutch_multiplier: float = 0.4435
    blue_blood_aura: float = 0.2288
    committee_error_bias: float = 0.6198
    hand_check_penalty: float = 0.2900
    post_dominance_weight: float = 0.2466
    slow_pace_stability: float = 2.1395
    three_point_variance_multiplier: float = 1.1906
    freedom_of_movement_boost: float = 0.4582
    portal_instability_penalty: float = 0.0
    nil_resource_advantage: float = 0.3108
    conf_tourney_marathon_fatigue: float = 3.3903
    elite_conf_momentum_boost: float = 0.3429
    altitude_fatigue_penalty: float = 0.0354
    altitude_ft_decay: float = 0.5758
    star_reliance_penalty: float = 0.0
    deep_bench_stability: float = 0.8010
    coach_final_four_aura: float = 0.0250
    quad_1_resilience_weight: float = 1.2545
    three_point_gravity_weight: float = 0.2081
    era_crossover_stability: float = 0.2817
    glass_pace_interaction_weight: float = 0.3231
    small_ball_bias_modern: float = 0.6672
    low_seed_adrenaline_crash: float = 0.5862
    eleven_seed_sustainability: float = 0.1796
    composure_index_weight: float = 0.3135
    upset_delta_weight: float = 2.7000
    rim_contest_frequency_weight: float = 5.0227
    off_ball_movement_weight: float = 1.2358
    gravity_adjusted_3p_weight: float = 2.9080
    era_excellence_physicality_weight: float = 0.1648
    era_excellence_modern_weight: float = 0.2818
    portal_instability_coefficient_weight: float = 0.8187
    elite_eight_cinderella_wall: float = 0.1286
    blue_blood_final_weekend_boost: float = 0.2225
    veteran_backcourt_scaling: float = 1.8833
    defensive_switching_continuity: float = 0.5633
    mid_range_march_value: float = 0.0447
    defensive_versatility_index: float = 0.6681
    tournament_aura_boost: float = 2.9402
    accumulative_travel_fatigue: float = 0.1127
    championship_pedigree_weight: float = 1.8017
    defense_premium: float = 3.2097
    luck_weight: float = -0.3788
    due_factor_sensitivity: float = 2.6575
    momentum_regression_weight: float = 3.8471
    road_dominance_weight: float = 0.6102
    seed_weight: float = 0.001
    ast_weight: float = 0.6361
    three_par_volatility_weight: float = 12.8741
    ts_weight: float = 0.8500
    experience_weight: float = 10.5187
    late_round_def_premium: float = 0.2927
    depth_weight: float = 2.6914
    continuity_weight: float = 4.6453
    cinderella_factor: float = 4.3039
    luck_regression_weight: float = 0.0627
    star_reliance_weight: float = 0.2099
    orb_density_weight: float = 1.1116
    continuation_rule_bias: float = 0.7065
    coach_tournament_weight: float = 0.3550
    tempo_upset_weight: float = 0.5723
    fatigue_sensitivity: float = 0.1214
    bench_rest_bonus: float = 0.2261
    chaos_mode: bool = True

    def to_dict(self):
        return dataclasses.asdict(self)

    def __repr__(self):
        fields = dataclasses.fields(self)
        items = []
        for f in fields:
            val = getattr(self, f.name)
            items.append(f"{f.name}={val}")
        return f"SimulationWeights({', '.join(items)})"

# Default configuration derived from Gold Standard optimization iteration 1436.
# Achieving: Avg ESPN Score=327.8 across 24 historical years (2000-2024).
DEFAULT_WEIGHTS = SimulationWeights()
