import logging
import random
from typing import Optional, List, Dict
from .team_model import Team
from .config import SimulationWeights, DEFAULT_WEIGHTS

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class SimulatorEngine:
    def __init__(self, teams: Dict[str, Team], weights: SimulationWeights, locks: Optional[Dict[str, str]] = None):
        self.teams = teams
        self.weights = weights
        self.locks = locks or {}
        # Stateful tracking for "Due Factor" (Reset per simulation run)
        self.upset_count = 0
        self.total_games = 0
        
    def reset_state(self):
        """Reset state for a new bracket simulation."""
        self.upset_count = 0
        self.total_games = 0

    def simulate_game(self, team_a: Team, team_b: Team, mode: str = "deterministic") -> Team:
        """Simulates a game and returns the winner."""
        prob_a = self.calculate_win_probability(team_a, team_b)
        
        if mode == "deterministic":
            return team_a if prob_a >= 0.5 else team_b
        else:
            return team_a if random.random() < prob_a else team_b

    def calculate_win_probability(self, team_a: Team, team_b: Team, round_num: int = 1) -> float:
        """Calculates win prob with defensive null checks."""
        # Ensure base efficiencies have defaults if None
        eff_a = team_a.pythagorean_expectation if team_a.off_efficiency is not None else 0.5
        eff_b = team_b.pythagorean_expectation if team_b.off_efficiency is not None else 0.5
        
        base_probability = eff_a / (eff_a + eff_b) if (eff_a + eff_b) > 0 else 0.5
        final_probability = base_probability
        
        # Step 2: Advanced Metric Modifiers
        # Defense Premium (Boosts the team with the better defense)
        # Refined Phase 2: If AdjD is missing (None), we skip this modifier instead of using 100.0
        if team_a.def_efficiency is not None and team_b.def_efficiency is not None:
            def_b = team_b.def_efficiency
            def_a = team_a.def_efficiency
            def_delta = def_b - def_a # lower def_efficiency is better
            final_probability += (def_delta * 0.001) * self.weights.defense_premium
        
        # 2. Seed Advantage (The "Chalk" baseline)
        seed_diff = team_b.seed - team_a.seed
        final_probability += seed_diff * self.weights.seed_weight
        # Refined SOS: Weighted by win percentage against that schedule
        if team_a.sos is not None and team_b.sos is not None:
            sos_a = team_a.sos * (team_a.total_win_pct or 0.5)
            sos_b = team_b.sos * (team_b.total_win_pct or 0.5)
            sos_delta = sos_a - sos_b
            final_probability += (sos_delta * 0.01) * self.weights.sos_weight
            
        # Turnover Margin
        if team_a.off_to_pct is not None and team_a.def_to_pct is not None and \
           team_b.off_to_pct is not None and team_b.def_to_pct is not None:
            margin_a = team_a.def_to_pct - team_a.off_to_pct
            margin_b = team_b.def_to_pct - team_b.off_to_pct
            margin_delta = margin_a - margin_b
            final_probability += (margin_delta * 0.01) * self.weights.to_weight
            
        # Momentum
        if team_a.momentum is not None and team_b.momentum is not None:
            momentum_delta = team_a.momentum - team_b.momentum
            final_probability += momentum_delta * self.weights.momentum_weight
            
        # Free Throw Advantage vs Defensive Fouling Tendency
        if team_a.off_ft_pct is not None and team_b.def_ft_rate is not None and \
           team_b.off_ft_pct is not None and team_a.def_ft_rate is not None:
            # Advantage = (Your shooting quality) * (Opponent fouling quantity)
            ft_a = (team_a.off_ft_pct / 100.0) * (team_b.def_ft_rate)
            ft_b = (team_b.off_ft_pct / 100.0) * (team_a.def_ft_rate)
            ft_advantage = ft_a - ft_b
            final_probability += ft_advantage * 0.1 * self.weights.ft_weight
            
        # 2. Foul Drawing Advantage (AGGRESSIVENESS)
        ftr_delta = (team_a.off_ft_rate or 0.0) - (team_b.off_ft_rate or 0.0)
        final_probability += ftr_delta * self.weights.foul_drawing_weight

        stl_delta = (team_a.off_stl_pct or 0.0) - (team_b.off_stl_pct or 0.0)
        final_probability += (stl_delta * 0.01) * self.weights.stl_weight

        blk_delta = (team_a.off_blk_pct or 0.0) - (team_b.off_blk_pct or 0.0)
        final_probability += (blk_delta * 0.01) * self.weights.blk_weight

        orb_delta = (team_a.off_orb_pct or 0.0) - (team_b.off_orb_pct or 0.0)
        final_probability += (orb_delta * 0.01) * self.weights.orb_weight

        # 5. Defensive Discipline (Phase 6)
        # Penality for fouling (allowing high FT Rate)
        if team_a.def_ft_rate is not None and team_b.def_ft_rate is not None:
            discipline_delta = team_b.def_ft_rate - team_a.def_ft_rate
            final_probability += discipline_delta * self.weights.def_ft_rate_weight

        # Phase 5: Fatigue & Short Rest (R32, E8, F4, Champ)
        # These rounds happen on ~48 hours rest.
        if round_num in [2, 4, 6] and self.weights.fatigue_sensitivity > 0:
            # Fatigue is higher for teams that play fast (high pace)
            # and offset by depth (bench_rest_bonus)
            fatigue_a = (team_a.pace or 70.0) * 0.01 * self.weights.fatigue_sensitivity
            fatigue_b = (team_b.pace or 70.0) * 0.01 * self.weights.fatigue_sensitivity
            
            # Apply bench bonus (rewards deep rotations)
            depth_a = (team_a.bench_minutes_pct or 25.0) * 0.01 * self.weights.bench_rest_bonus
            depth_b = (team_b.bench_minutes_pct or 25.0) * 0.01 * self.weights.bench_rest_bonus
            
            net_fatigue = (fatigue_a - depth_a) - (fatigue_b - depth_b)
            final_probability -= net_fatigue # higher net fatigue reduces win prob

        # 5. Luck Metric (Phase 4)
        # Luck = Win% - (SRS/40) - higher luck means a team might be over-seeded/over-valued
        if hasattr(team_a, 'sos') and hasattr(team_b, 'sos'): # Use SOS as SRS proxy if needed
            # For simplicity, if we have raw metrics we use them, else we approximate
            luck_a = getattr(team_a, 'luck', 0.0) or 0.0
            luck_b = getattr(team_b, 'luck', 0.0) or 0.0
            luck_advantage = (luck_b - luck_a) # Higher luck_b means team_b is "due" to lose/overachieved
            final_probability += luck_advantage * self.weights.luck_weight

        # 6. Momentum Regression (Phase 4)
        # If a team has extreme momentum (e.g. 0.9+), they might be "due" for a loss
        if team_a.momentum and team_a.momentum > 0.9:
            final_probability -= (team_a.momentum - 0.9) * self.weights.momentum_regression_weight
        if team_b.momentum and team_b.momentum > 0.9:
            final_probability += (team_b.momentum - 0.9) * self.weights.momentum_regression_weight

        # 11. Neutral Venue Shift is handled below at Neutral Site Mastery (Phase 5)

        # 12. Experience Bonus (Phase 4)

        # 8. Assist Rate (Phase 4)
        # Rewards unselfish cohesion
        ast_delta = (team_a.off_ast_pct or 0.0) - (team_b.off_ast_pct or 0.0)
        final_probability += (ast_delta * 0.01) * self.weights.ast_weight

        # 9. 3PAr Volatility (Phase 4)
        # Higher 3PAr increases game variance, pulling probabilities toward 50/50
        if team_a.three_par is not None and team_b.three_par is not None:
            avg_3par = (team_a.three_par + team_b.three_par) / 2
            # Pivot around 0.37 (modern average 3PAr)
            volatility_shift = (avg_3par - 0.37) * self.weights.three_par_volatility_weight
            if final_probability > 0.5:
                final_probability = max(0.5, final_probability - volatility_shift)
            else:
                final_probability = min(0.5, final_probability + volatility_shift)

        # 10. TS% Advantage (Phase 4)
        ts_delta = (team_a.off_ts_pct or 0.0) - (team_b.off_ts_pct or 0.0)
        final_probability += (ts_delta * 0.01) * self.weights.ts_weight

        # 11. Experience Bonus (Phase 4)
        exp_delta = (team_a.total_games or 0) - (team_b.total_games or 0)
        final_probability += exp_delta * self.weights.experience_weight

        # 12. Late-Round Defensive Premium (Phase 4)
        # Rewards elite defense more heavily in high-stakes late rounds
        if team_a.def_efficiency is not None and team_b.def_efficiency is not None:
            # Lower AdjD is better, so team_b.def - team_a.def is team_a's advantage
            def_advantage = (team_b.def_efficiency - team_a.def_efficiency)
            round_bonus = (round_num - 1) * self.weights.late_round_def_premium
            final_probability += (def_advantage * 0.01) * round_bonus

        # 13. Aggressive Marksman (Phase 4)
        # Bonus for teams that both draw many fouls and convert them at high rates
        # USER DEFINED 2025 FORMULAS
        # 1. Grit: 0.4 * (100 - AdjDE) + 0.3 * ORB_pct + 0.3 * (Math.abs(Luck) if Luck < 0 else 0)
        grit_a = 0.4 * (100 - (team_a.def_efficiency or 100)) + 0.3 * (team_a.off_orb_pct or 0.0) + 0.3 * abs(min(0, (team_a.luck or 0.0)))
        grit_b = 0.4 * (100 - (team_b.def_efficiency or 100)) + 0.3 * (team_b.off_orb_pct or 0.0) + 0.3 * abs(min(0, (team_b.luck or 0.0)))
        final_probability += (grit_a - grit_b) * 0.01 * self.weights.defense_premium

        # 2. Aggression: 0.3 * AdjT + 0.4 * FT_Rate + 0.3 * TO_pct_def
        # Using AdjT (pace) as a proxy if raw AdjT isn't explicit
        agg_a = 0.3 * (team_a.pace or 70) + 0.4 * (team_a.off_ft_rate or 0.0) + 0.3 * (team_a.def_to_pct or 0.0)
        agg_b = 0.3 * (team_b.pace or 70) + 0.4 * (team_b.off_ft_rate or 0.0) + 0.3 * (team_b.def_to_pct or 0.0)
        final_probability += (agg_a - agg_b) * 0.01 * self.weights.foul_drawing_weight

        # 3. Portal Stability: 0.5 * Minutes_Returning_pct + 0.3 * Scoring_Returning_pct - 0.2 * Transfer_Usage_pct
        # Note: These metrics are mapped to experience_weight and continuity_weight proxies
        stab_a = 0.5 * getattr(team_a, 'returning_minutes', 50.0) + 0.3 * getattr(team_a, 'returning_scoring', 50.0) - 0.2 * getattr(team_a, 'transfer_pct', 20.0)
        stab_b = 0.5 * getattr(team_b, 'returning_minutes', 50.0) + 0.3 * getattr(team_b, 'returning_scoring', 50.0) - 0.2 * getattr(team_b, 'transfer_pct', 20.0)
        final_probability += (stab_a - stab_b) * 0.01 * self.weights.continuity_weight

        if (team_a.off_ft_rate or 0.0) > 0.38 and (team_a.off_ft_pct or 0.0) > 78.0:
            final_probability += 0.02
        if (team_b.off_ft_rate or 0.0) > 0.38 and (team_b.off_ft_pct or 0.0) > 78.0:
            final_probability -= 0.02

        # 14. Neutral Site Mastery (Phase 5)
        neutral_delta = team_a.neutral_win_pct - team_b.neutral_win_pct
        final_probability += neutral_delta * self.weights.neutral_weight

        # 16. Bench Depth (Phase 7)
        # Deep teams (high AST% and TRB% synergy) thrive in late tournament weekends
        if round_num >= 4:
            depth_a = (team_a.off_ast_pct or 50.0) + (team_a.trb_pct or 50.0)
            depth_b = (team_b.off_ast_pct or 50.0) + (team_b.trb_pct or 50.0)
            depth_delta = depth_a - depth_b
            final_probability += (depth_delta * 0.01) * self.weights.depth_weight

        # 17. Roster Continuity (Phase 7)
        # Proxy: Experience (total_games) + stability.
        continuity_a = (team_a.total_games or 30) * (team_a.sos or 0.0)
        continuity_b = (team_b.total_games or 30) * (team_b.sos or 0.0)
        continuity_delta = continuity_a - continuity_b
        final_probability += (continuity_delta * 0.001) * self.weights.continuity_weight

        # 18. Coach Tournament Moxie (Research Loop 1)
        # Coaches with deep tournament experience (Elite Eight+) give their
        # teams a measurable edge. Research showed this is the strongest
        # single predictor for Final Four appearances.
        coach_wins_a = getattr(team_a, 'coach_tournament_wins', 0) or 0
        coach_wins_b = getattr(team_b, 'coach_tournament_wins', 0) or 0
        if coach_wins_a > 0 or coach_wins_b > 0:
            # Normalize: a coach with 20+ tourney wins is elite
            moxie_a = min(1.0, coach_wins_a / 20.0)
            moxie_b = min(1.0, coach_wins_b / 20.0)
            final_probability += (moxie_a - moxie_b) * 0.05 * self.weights.coach_tournament_weight


        # 18. Pace Control (Phase 7)
        # Teams that successfully impose their tempo (extreme pace + winning)
        pace_a = team_a.pace or 70.0
        pace_b = team_b.pace or 70.0
        
        # Calculate a successful-pace-control proxy
        win_a = team_a.off_ppg / (team_a.off_ppg + team_a.def_ppg) if (team_a.off_ppg and team_a.def_ppg) else 0.5
        win_b = team_b.off_ppg / (team_b.off_ppg + team_b.def_ppg) if (team_b.off_ppg and team_b.def_ppg) else 0.5
        
        control_a = abs(pace_a - 70.0) * win_a
        control_b = abs(pace_b - 70.0) * win_b
        control_delta = control_a - control_b
        final_probability += (control_delta * 0.01) * self.weights.pace_control_weight

        # 3PAr Advantage (High 3PAr = Chaos/Variance)
        if team_a.three_par is not None and team_b.three_par is not None:
            threepar_advantage = team_a.three_par - team_b.three_par
            final_probability += threepar_advantage * self.weights.three_par_weight
            
        # Pace Variance (Slow games neutralize favorites)
        # Research: underdogs outside top-100 tempo use slow pace
        # to compress the talent gap and increase upset probability
        if team_a.pace is not None and team_b.pace is not None:
            avg_pace = (team_a.pace + team_b.pace) / 2.0
            if avg_pace < 65.0:
                pace_diff = 65.0 - avg_pace
                neutralization = (pace_diff * 0.02) * self.weights.pace_variance_weight
                # Tempo upset bonus: if the underdog (higher seed) is slower,
                # they are deliberately controlling the tempo
                if team_a.seed > team_b.seed and (team_a.pace or 70) < 65:
                    neutralization += self.weights.tempo_upset_weight * 0.5
                elif team_b.seed > team_a.seed and (team_b.pace or 70) < 65:
                    neutralization += self.weights.tempo_upset_weight * 0.5
                if final_probability > 0.5:
                    final_probability = max(0.5, final_probability - neutralization)
                else:
                    final_probability = min(0.5, final_probability + neutralization)

        # eFG% Matchup (A's offense vs B's defense)
        if None not in (team_a.off_efg_pct, team_b.def_efg_pct, team_b.off_efg_pct, team_a.def_efg_pct):
            a_off_b_def_efg = team_a.off_efg_pct - team_b.def_efg_pct
            b_off_a_def_efg = team_b.off_efg_pct - team_a.def_efg_pct
            efg_advantage = (a_off_b_def_efg - b_off_a_def_efg) * 0.002
            final_probability += efg_advantage * self.weights.efficiency_weight

        # CHAOS ENGINE: Probability Shift
        # If chaos_mode is on, and an underdog (by seed) has a "Chaos Profile"
        # (High 3PAr or massive TO edge), we shift their probability up.
        if self.weights.chaos_mode:
            # Determine who is the underdog by seed
            if team_a.seed > team_b.seed:
                underdog = team_a
                underdog_idx = 1 # Shift final_prob UP
            elif team_b.seed > team_a.seed:
                underdog = team_b
                underdog_idx = -1 # Shift final_prob DOWN
            else:
                underdog = None
                
            if underdog:
                # Chaos Shift Logic: If underdog has >35% 3PAr or high TO margin
                is_chaos_potential = (underdog.three_par and underdog.three_par > 0.38) or \
                                     (underdog.def_to_pct and underdog.off_to_pct and \
                                      (underdog.def_to_pct - underdog.off_to_pct) > 3.0)
                
                if is_chaos_potential:
                    # Apply a shift scaled by the Cinderella Factor
                    shift = 0.05 * self.weights.cinderella_factor
                    final_probability += (shift * underdog_idx)

        # 4. The Due Factor (Phase 4)
        # If we have too many upsets, narrow the probability (make it more likely for the favorite)
        # If we have too few, widen it (make upsets more likely)
        if self.weights.due_factor_sensitivity > 0 and self.total_games > 5:
            historical_upset_rate = 0.25 # Approx 1/4 games are upsets
            current_rate = self.upset_count / self.total_games
            
            # If current rate > historical, favor favored team more
            due_correction = (current_rate - historical_upset_rate) * self.weights.due_factor_sensitivity
            
            # Apply correction: if due_correction is positive (too many upsets), 
            # and final_probability > 0.5 (Team A is favorite), increase final_probability.
            if final_probability > 0.5:
                final_probability += due_correction
            else:
                final_probability -= due_correction

        # 5. Luck Regression & Star Reliance (Phase 9)
        if team_a.luck is not None:
            final_probability -= (team_a.luck * self.weights.luck_regression_weight)
        if team_b.luck is not None:
            final_probability += (team_b.luck * self.weights.luck_regression_weight)
            
        if team_a.star_reliance is not None:
            final_probability -= (team_a.star_reliance * self.weights.star_reliance_weight)
        if team_b.star_reliance is not None:
            final_probability += (team_b.star_reliance * self.weights.star_reliance_weight)

        # 2025 Research Indicator: Continuation Rule (FTA/FGA Slasher Bonus)
        # Favors aggressive teams that draw fouls at the rim (NCAA 2025 Rule Change)
        if (team_a.off_ft_rate or 0.0) > 0.380:
            final_probability += self.weights.continuation_rule_bias
        if (team_b.off_ft_rate or 0.0) > 0.380:
            final_probability -= self.weights.continuation_rule_bias

        # 2025 Research Indicator: ORB Density (Historic Dominance)
        if (team_a.off_orb_pct or 0.0) > 34.0:
            final_probability += (team_a.off_orb_pct - 34.0) * 0.01 * self.weights.orb_density_weight
        if (team_b.off_orb_pct or 0.0) > 34.0:
            final_probability -= (team_b.off_orb_pct - 34.0) * 0.01 * self.weights.orb_density_weight

        # --- Rounds 11-15: Fine-Grained Context ---
        # Round 11: Geospatial Impact
        if self.weights.travel_weight > 0:
            if (team_a.travel_dist or 0) > 150:
                final_probability -= 0.02 * self.weights.travel_weight
            if team_a.travel_east:
                final_probability -= 0.015 * self.weights.travel_weight
            if (team_b.travel_dist or 0) > 150:
                final_probability += 0.02 * self.weights.travel_weight
            if team_b.travel_east:
                final_probability += 0.015 * self.weights.travel_weight
        
        # Round 12: Pressure Resilience
        if round_num >= 4 and self.weights.pressure_weight > 0:
            # Experience + FT% + Coach wins is the pressure-proof profile
            clutch_a = ((team_a.off_ft_pct or 70) / 100.0) + (min(1.0, (team_a.coach_tournament_wins or 0) / 10.0))
            clutch_b = ((team_b.off_ft_pct or 70) / 100.0) + (min(1.0, (team_b.coach_tournament_wins or 0) / 10.0))
            final_probability += (clutch_a - clutch_b) * 0.05 * self.weights.pressure_weight

        # Round 13: Roster Chemistry (Transfer Portal)
        if round_num >= 5 and self.weights.chemistry_weight > 0:
            chem_a = (team_a.portal_usage_pct or 20.0) / 100.0
            chem_b = (team_b.portal_usage_pct or 20.0) / 100.0
            # Higher portal usage = lower chemistry in high-stakes environments
            final_probability -= (chem_a - chem_b) * 0.1 * self.weights.chemistry_weight

        # Round 14: Elite Freshman Index
        if round_num >= 4 and self.weights.freshman_weight > 0:
            frosh_a = (team_a.freshman_usage_pct or 10.0) / 100.0
            frosh_b = (team_b.freshman_usage_pct or 10.0) / 100.0
            final_probability -= (frosh_a - frosh_b) * 0.08 * self.weights.freshman_weight

        # Round 15: Conference Tournament Aftermath
        momentum_boost_a = (team_a.tourney_momentum or 0.0) * 0.03
        momentum_boost_b = (team_b.tourney_momentum or 0.0) * 0.03
        final_probability += (momentum_boost_a - momentum_boost_b)

        # --- Rounds 16-20: Roster & Depth Suite ---
        # Round 16: Elite Backcourt Mastery
        # Mitigation of defense pressure for elite ball-handling teams
        if self.weights.backcourt_weight > 0:
            guard_a = (team_a.off_ast_pct or 50) * (100 - (team_a.off_to_pct or 20)) / 1000.0
            guard_b = (team_b.off_ast_pct or 50) * (100 - (team_b.off_to_pct or 20)) / 1000.0
            # If facing a top 50 defense, the guard play matters more
            defense_fac_a = (100 - (team_b.def_efficiency or 100)) / 10.0
            defense_fac_b = (100 - (team_a.def_efficiency or 100)) / 10.0
            final_probability += (guard_a * defense_fac_a - guard_b * defense_fac_b) * 0.01 * self.weights.backcourt_weight

        # Round 17: Bench Synergy (Depth-driven Rebounding)
        if self.weights.bench_synergy_weight > 0:
            syn_a = (team_a.bench_minutes_pct or 25) * (team_a.trb_pct or 50) / 100.0
            syn_b = (team_b.bench_minutes_pct or 25) * (team_b.trb_pct or 50) / 100.0
            final_probability += (syn_a - syn_b) * 0.005 * self.weights.bench_synergy_weight

        # Round 18: Whistle Mastery
        if self.weights.whistle_mastery_weight > 0:
            # Aggressive foul drawing + High FT% conversion
            whistle_a = (team_a.off_ft_rate or 0.3) * (team_a.off_ft_pct or 70) / 100.0
            whistle_b = (team_b.off_ft_rate or 0.3) * (team_b.off_ft_pct or 70) / 100.0
            final_probability += (whistle_a - whistle_b) * 0.1 * self.weights.whistle_mastery_weight

        # Round 19: Heating Up (Undervalued Momentum)
        if self.weights.heating_up_weight > 0:
            heat_a = (team_a.momentum or 0.5) * (1 - (team_a.luck or 0.0))
            heat_b = (team_b.momentum or 0.5) * (1 - (team_b.luck or 0.0))
            final_probability += (heat_a - heat_b) * 0.02 * self.weights.heating_up_weight

        # Round 20: Venue Stability Variance
        if round_num >= 1 and (self.teams.get(team_a.name) or team_a).home_w is not None:
            # Simple check for Home/Away win% delta. High variance = Low stability on neutral sites.
            def get_stability(t):
                h_win = t.home_w / max(1, t.home_w + (t.home_l or 0)) if t.home_w is not None else 0.7
                a_win = t.away_w / max(1, t.away_w + (t.away_l or 0)) if t.away_w is not None else 0.5
                return 1.0 - abs(h_win - a_win)
            
            stab_a = get_stability(team_a)
            stab_b = get_stability(team_b)
            final_probability += (stab_a - stab_b) * 0.03

        # --- Rounds 21-25: Strategy & Adaptability ---
        # Round 21: Zone Defense Effectiveness
        if self.weights.zone_defense_weight > 0:
            # If team_a has high 3PAr, they might struggle against a team_b "Zone Profile"
            # Proxy: team_b is "Zone Profile" if they have low STL but high BLK and good AdjD
            is_zone_b = (team_b.off_stl_pct or 9.0) < 8.0 and (team_b.off_blk_pct or 9.0) > 10.0
            if is_zone_b and (team_a.three_par or 0.35) > 0.40:
                final_probability -= 0.03 * self.weights.zone_defense_weight
            
            is_zone_a = (team_a.off_stl_pct or 9.0) < 8.0 and (team_a.off_blk_pct or 9.0) > 10.0
            if is_zone_a and (team_b.three_par or 0.35) > 0.40:
                final_probability += 0.03 * self.weights.zone_defense_weight

        # Round 22: Halftime Adjustments (Coaching Boost)
        # Favors the stronger team (favorite) to rally or pull away
        if self.weights.adjustment_weight > 0:
            favorite_boost = abs(final_probability - 0.5) * 0.1 * self.weights.adjustment_weight
            # Booster: If coach is elite, the adjustment is more effective
            coach_boost_a = min(1.0, (team_a.coach_tournament_wins or 0) / 20.0)
            coach_boost_b = min(1.0, (team_b.coach_tournament_wins or 0) / 20.0)
            final_probability += (coach_boost_a - coach_boost_b) * 0.02 * self.weights.adjustment_weight

        # Round 23: Foul Trouble Management
        if self.weights.foul_management_weight > 0:
            # High FOUL rate (def_ft_rate) + Small Rotation (bench_minutes_pct) = Danger
            danger_a = (team_a.def_ft_rate or 30.0) * (100 - (team_a.bench_minutes_pct or 25.0)) / 1000.0
            danger_b = (team_b.def_ft_rate or 30.0) * (100 - (team_b.bench_minutes_pct or 25.0)) / 1000.0
            final_probability -= (danger_a - danger_b) * 0.05 * self.weights.foul_management_weight

        # Round 24: Clutch Execution (Final 4 Min Synergy)
        if self.weights.clutch_execution_weight > 0:
            # Pure synergy of ball handling and foul shooting
            clutch_a = (100 - (team_a.off_to_pct or 20)) + (team_a.off_ft_pct or 70)
            clutch_b = (100 - (team_b.off_to_pct or 20)) + (team_b.off_ft_pct or 70)
            final_probability += (clutch_a - clutch_b) * 0.001 * self.weights.clutch_execution_weight

        # Round 25: Rotation Endurance (2nd Half depth)
        if round_num >= 4 and self.weights.bench_rest_bonus > 0: # Reusing bench weights
            endurance_a = (team_a.bench_minutes_pct or 25) * (team_a.pace or 70) / 100.0
            endurance_b = (team_b.bench_minutes_pct or 25) * (team_b.pace or 70) / 100.0
            final_probability += (endurance_a - endurance_b) * 0.01 * self.weights.bench_rest_bonus

        # --- Rounds 26-30: Post-Season Volatility ---
        # Round 26: Neutral Site Scoring Consistency
        if self.weights.neutral_variance_weight > 0:
            # Multiplier for neutral_win_pct: Teams that produce at neutral sites stay stable
            final_probability += (team_a.neutral_win_pct - team_b.neutral_win_pct) * self.weights.neutral_variance_weight

        # Round 27: Conference Strength Reliability
        if self.weights.conference_weight > 0:
            # Power conferences have higher consistency/depth in post-season
            conf_bonus_a = 0.05 if team_a.is_power_conf else 0.0
            conf_bonus_b = 0.05 if team_b.is_power_conf else 0.0
            final_probability += (conf_bonus_a - conf_bonus_b) * self.weights.conference_weight

        # Round 28: Seed-Based Luck Regression (Specialized for high seeds)
        if (team_a.seed or 1) <= 3 and (team_a.luck or 0) > 2.0:
            # Penalty for "over-seeded" top teams with high luck
            final_probability -= (team_a.luck - 2.0) * 0.02 * self.weights.luck_regression_weight
        if (team_b.seed or 1) <= 3 and (team_b.luck or 0) > 2.0:
            final_probability += (team_b.luck - 2.0) * 0.02 * self.weights.luck_regression_weight

        # Round 29: SOS-Weighted 3PT Defense
        if self.weights.defense_premium > 0:
            # Does their 3pt def hold up against elite opponents?
            def_3a = (team_a.def_efficiency or 100) * (team_a.sos or 0)
            def_3b = (team_b.def_efficiency or 100) * (team_b.sos or 0)
            final_probability += (def_3b - def_3a) * 0.0001 * self.weights.defense_premium

        # Round 30: Rust vs Rhythm
        # If a team won their conf tourney (tourney_momentum=1.0) but is a high seed (rest),
        # they might start slow. If they played a play-in, they might be in rhythm.
        if round_num == 1:
            # Proxy: If tourney_momentum is 1.0 (winner), possible rust
            rust_a = self.weights.rust_penalty if (team_a.tourney_momentum or 0) > 0.9 else 0.0
            rust_b = self.weights.rust_penalty if (team_b.tourney_momentum or 0) > 0.9 else 0.0
            final_probability -= (rust_a - rust_b)

        # --- Rounds 31-33: Final Convergence ---
        # Round 31: Hirschy Factor Dominance (Global Composite)
        if self.weights.hirschy_factor_weight > 0:
            hirschy_a = team_a.hirschy_factor
            hirschy_b = team_b.hirschy_factor
            final_probability += (hirschy_a - hirschy_b) * 0.005 * self.weights.hirschy_factor_weight

        # Round 32: Blue Blood Institutional Knowledge
        if self.weights.blue_blood_bonus > 0:
            hist_a = min(1.0, (team_a.historical_tourney_wins or 0) / 100.0)
            hist_b = min(1.0, (team_b.historical_tourney_wins or 0) / 100.0)
            # The "Pressure of the Jersey" bonus - slight edge in early rounds
            if round_num <= 2:
                final_probability += (hist_a - hist_b) * 0.05 * self.weights.blue_blood_bonus

        # Round 33: Multi-Objective Scaling
        # (Implicitly handled by the optimization of all weights simultaneously)

        # Clamp to valid probability bounds [0.01, 0.99]
        final_probability = max(0.01, min(0.99, final_probability))
        
        return final_probability

    def simulate_matchup(self, team_a_name: str, team_b_name: str, round_num: int = 1) -> str:
        """Simulates a game between two teams and returns the winner's name."""
        # Check for Matchup Locks (Phase 8)
        lock_key1 = f"{team_a_name} vs {team_b_name}"
        lock_key2 = f"{team_b_name} vs {team_a_name}"
        
        if lock_key1 in self.locks:
            return self.locks[lock_key1]
        if lock_key2 in self.locks:
            return self.locks[lock_key2]
            
        team_a = self.teams.get(team_a_name)
        team_b = self.teams.get(team_b_name)
        
        if not team_a: return team_b_name
        if not team_b: return team_a_name
        
        prob_a = self.calculate_win_probability(team_a, team_b, round_num)
        winner = team_a_name if random.random() < prob_a else team_b_name
        
        # State Update for Due Factor
        self.total_games += 1
        favored_team = team_a_name if prob_a > 0.5 else team_b_name
        if winner != favored_team:
            self.upset_count += 1
            
        return winner
