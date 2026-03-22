import logging
import random
import math
from typing import Optional, List, Dict, Any
from .team_model import Team
from .config import SimulationWeights, DEFAULT_WEIGHTS

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class SimulatorEngine:
    def __init__(self, teams: Dict[str, Team], weights: SimulationWeights, locks: Optional[Dict[str, str]] = None, actual_results: Optional[Dict[str, Any]] = None):
        self.teams = teams
        self.weights = weights
        self.locks = locks or {}
        self.actual_results = actual_results or {}
        self.volatility = 0.0 # Blending factor (0.0 = pure metrics, 1.0 = pure random)
        # Stateful tracking for "Due Factor" (Reset per simulation run)
        self.upset_count = 0
        self.total_games = 0
        
    def reset_state(self):
        """Reset state for a new bracket simulation."""
        self.upset_count = 0
        self.total_games = 0

    def get_locked_winner(self, team_a_name: str, team_b_name: str, round_num: int) -> Optional[str]:
        """Checks both explicit matchup locks and live actual results."""
        # 1. Check explicit Matchup Locks
        lock_key1 = f"{team_a_name} vs {team_b_name}"
        lock_key2 = f"{team_b_name} vs {team_a_name}"
        if lock_key1 in self.locks: return self.locks[lock_key1]
        if lock_key2 in self.locks: return self.locks[lock_key2]

        # 2. Check Actual Results (Live Sync)
        round_map = {1: "round_of_32", 2: "sweet_sixteen", 3: "elite_eight", 4: "final_four", 6: "champion"}
        round_key = round_map.get(round_num)
        if round_key and self.actual_results:
            historical_winners = self.actual_results.get(round_key, [])
            if isinstance(historical_winners, list):
                if team_a_name in historical_winners: return team_a_name
                if team_b_name in historical_winners: return team_b_name
            elif isinstance(historical_winners, str) and historical_winners: # For 'champion'
                if team_a_name == historical_winners: return team_a_name
                if team_b_name == historical_winners: return team_b_name
        
        return None

    def simulate_game(self, team_a: Team, team_b: Team, mode: str = "deterministic", round_num: int = 1) -> Team:
        """Simulates a game and returns the winner, incorporating Volatility Index and Locks."""
        # Check for Locks first
        locked_winner_name = self.get_locked_winner(team_a.name, team_b.name, round_num)
        if locked_winner_name:
            return team_a if team_a.name == locked_winner_name else team_b

        prob_a = self.calculate_win_probability(team_a, team_b, round_num)
        
        # Apply Volatility Index blending
        blended_prob = ((1.0 - self.volatility) * prob_a) + (self.volatility * 0.5)
        
        if mode == "deterministic":
            return team_a if blended_prob >= 0.5 else team_b
        else:
            return team_a if random.random() < blended_prob else team_b

    def _get_metric(self, team, attr, default=0.0):
        """Safely gets a numeric metric from a team object, defaulting if None."""
        val = getattr(team, attr, default)
        if val is None: return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def calculate_win_probability(self, team_a: Team, team_b: Team, round_num: int = 1) -> float:
        """Calculates win prob using a Logistic (Sigmoid) model for calibration."""
        if not team_a or not team_b:
            return 0.5
        # Step 1: Base Process-Based EV (Adj SQ Margin)
        # logit(p) = log(p / (1-p)) or directly using the SQ delta
        sq_off_a = self._get_metric(team_a, 'adj_off_sq', team_a.off_efficiency or 100.0)
        sq_def_a = self._get_metric(team_a, 'adj_def_sq', team_a.def_efficiency or 100.0)
        sq_off_b = self._get_metric(team_b, 'adj_off_sq', team_b.off_efficiency or 100.0)
        sq_def_b = self._get_metric(team_b, 'adj_def_sq', team_b.def_efficiency or 100.0)
        
        sq_margin_a = sq_off_a - sq_def_a
        sq_margin_b = sq_off_b - sq_def_b
        
        # Foundational matchup math shift (Phase 3.1)
        delta = (sq_margin_a - sq_margin_b) * 0.1 * self.weights.sq_margin_weight
        
        # Step 2: Advanced Metric Modifiers
        # Seed Advantage (Psychological / Historical baseline)
        seed_diff = self._get_metric(team_b, 'seed', 16) - self._get_metric(team_a, 'seed', 16)
        delta += seed_diff * 0.15 * self.weights.seed_weight
        
        # Peaking Indicator (Recent Form)
        recent_a = self._get_metric(team_a, 'recent_form', 0.0)
        recent_b = self._get_metric(team_b, 'recent_form', 0.0)
        delta += (recent_a - recent_b) * 0.2 * self.weights.momentum_weight
            
        # Turnover Margin (Chaos factor)
        margin_a = self._get_metric(team_a, 'def_to_pct', 20.0) - self._get_metric(team_a, 'off_to_pct', 20.0)
        margin_b = self._get_metric(team_b, 'def_to_pct', 20.0) - self._get_metric(team_b, 'off_to_pct', 20.0)
        delta += (margin_a - margin_b) * 0.05 * self.weights.to_weight

        # Luck Regression (Mean reversion)
        luck_a = self._get_metric(team_a, 'luck', 0.0)
        luck_b = self._get_metric(team_b, 'luck', 0.0)
        delta += (luck_b - luck_a) * 0.3 * self.weights.luck_weight
        delta += (self._get_metric(team_a, 'total_games', 30) - self._get_metric(team_b, 'total_games', 30)) * 0.02 * self.weights.experience_weight

        # --- Advanced Modern Metrics (Cycle 4) ---
        # Adj SQ Margin (Process-based Expected Value)
        sq_off_a = self._get_metric(team_a, 'adj_off_sq', team_a.off_efficiency or 100.0)
        sq_def_a = self._get_metric(team_a, 'adj_def_sq', team_a.def_efficiency or 100.0)
        sq_off_b = self._get_metric(team_b, 'adj_off_sq', team_b.off_efficiency or 100.0)
        sq_def_b = self._get_metric(team_b, 'adj_def_sq', team_b.def_efficiency or 100.0)
        
        sq_margin_a = sq_off_a - sq_def_a
        sq_margin_b = sq_off_b - sq_def_b
        delta += (sq_margin_a - sq_margin_b) * 0.05 * self.weights.sq_margin_weight

        # Kill Shot Differential (Momentum Multiplier)
        ks_diff_a = self._get_metric(team_a, 'kill_shots_scored', 0.0) - self._get_metric(team_a, 'kill_shots_conceded', 0.0)
        ks_diff_b = self._get_metric(team_b, 'kill_shots_scored', 0.0) - self._get_metric(team_b, 'kill_shots_conceded', 0.0)
        delta += (ks_diff_a - ks_diff_b) * 0.3 * self.weights.kill_shot_momentum_weight

        # BPR (Bayesian Performance Rating)
        bpr_a = self._get_metric(team_a, 'bpr', 0.0)
        bpr_b = self._get_metric(team_b, 'bpr', 0.0)
        delta += (bpr_a - bpr_b) * 0.1 # Direct logit contribution

        # Round-Weighted Defense
        def_advantage = (self._get_metric(team_b, 'def_efficiency', 100.0) - self._get_metric(team_a, 'def_efficiency', 100.0))
        round_bonus = (round_num - 1) * self.weights.late_round_def_premium
        delta += def_advantage * 0.05 * round_bonus

        # Era-Specific Scaling & 2025 Indicators
        year = team_a.year or 2024
        if year <= 2010: delta += (def_b - def_a) * 0.02 * self.weights.defensive_grit_bias
        if year >= 2015: delta += (self._get_metric(team_a, 'three_par', 0.35) - self._get_metric(team_b, 'three_par', 0.35)) * 1.5 * self.weights.three_point_dominance
        
        # 2025 Specific Rules (v2025_indicators.json)
        if year >= 2025:
            # Continuation Rule (Impact on Offensive Efficiency)
            delta += (self._get_metric(team_a, 'off_efficiency', 100.0) - self._get_metric(team_b, 'off_efficiency', 100.0)) * 0.01 * self.weights.continuation_rule_bias
            
            # ORB Density (Second Chance Multiplier)
            if self._get_metric(team_a, 'off_orb_pct', 25.0) > 35.0:
                delta += 0.5 * self.weights.orb_density_weight
            if self._get_metric(team_b, 'off_orb_pct', 25.0) > 35.0:
                delta -= 0.5 * self.weights.orb_density_weight
                
            # Tempo Upset Strategy (Slow tempo underdog neutralization)
            if self._get_metric(team_a, 'pace', 70.0) < 65.0 and self._get_metric(team_a, 'seed', 16) > self._get_metric(team_b, 'seed', 1):
                delta += 0.3 * self.weights.tempo_upset_weight
            elif self._get_metric(team_b, 'pace', 70.0) < 65.0 and self._get_metric(team_b, 'seed', 16) > self._get_metric(team_a, 'seed', 1):
                delta -= 0.3 * self.weights.tempo_upset_weight

        # Bench & Continuity
        delta += (self._get_metric(team_a, 'bench_minutes_pct', 25.0) - self._get_metric(team_b, 'bench_minutes_pct', 25.0)) * 0.05 * self.weights.bench_rest_bonus
        delta += (self._get_metric(team_a, 'total_games', 30) - self._get_metric(team_b, 'total_games', 30)) * 0.01 * self.weights.continuity_weight

        # Coach & Aura
        moxie_a = min(1.0, self._get_metric(team_a, 'coach_tournament_wins', 0) / 20.0)
        moxie_b = min(1.0, self._get_metric(team_b, 'coach_tournament_wins', 0) / 20.0)
        delta += (moxie_a - moxie_b) * 1.0 * self.weights.coach_tournament_weight
        
        # Intuition Factor (Global Score)
        delta += (team_a.intuition_factor - team_b.intuition_factor) * 0.1 * self.weights.intuition_factor_weight

        # Blue Blood Legacy
        if round_num <= 2:
            blue_bloods = ["Kansas", "Kentucky", "Duke", "North Carolina", "UCLA", "Indiana", "UConn", "Villanova", "Michigan State"]
            aura_a = 0.5 if any(bb in team_a.name for bb in blue_bloods) else 0.0
            aura_b = 0.5 if any(bb in team_b.name for bb in blue_bloods) else 0.0
            delta += (aura_a - aura_b) * self.weights.blue_blood_bonus

        # Final Probability Calculation (Sigmoid / Logistic)
        # Replacing linear certainty with a calibrated logistic curve
        try:
            # Scale delta by a normalization factor to prevent saturation
            # Higher variance_scale = more 50/50 games (more upsets)
            # Lower variance_scale = more chalky (saturated)
            
            # Rim-and-3 Rate Volatility Scale
            # Teams with high Rim-and-3 rates have higher variance (3-point dependence)
            rim_3_a = self._get_metric(team_a, 'rim_3_rate', 0.4)
            rim_3_b = self._get_metric(team_b, 'rim_3_rate', 0.4)
            avg_rim_3 = (rim_3_a + rim_3_b) / 2.0
            variance_multiplier = 1.0 + (avg_rim_3 * 2.0 * self.weights.rim_3_volatility_weight)
            
            variance_scale = (1.0 + (self.volatility * 2.0)) * variance_multiplier
            final_probability = 1.0 / (1.0 + math.exp(-delta / variance_scale))
        except OverflowError:
            final_probability = 1.0 if delta > 0 else 0.0

        # Clamp to valid probability bounds [0.001, 0.999] for Log-Likelihood stability
        final_probability = max(0.001, min(0.999, final_probability))
        
        return final_probability

    def simulate_matchup(self, team_a_name: str, team_b_name: str, round_num: int = 1) -> str:
        """
        Simulates a game using a possession-scaled resolution loop.
        Integrates Pace Delta, Kill Shot triggers, and FT Floor survival.
        """
        # 1. Check for Locks
        locked_winner = self.get_locked_winner(team_a_name, team_b_name, round_num)
        if locked_winner: return locked_winner
            
        team_a = self.teams.get(team_a_name)
        team_b = self.teams.get(team_b_name)
        if not team_a: return team_b_name
        if not team_b: return team_a_name
        
        # 2. Base Configuration
        prob_a = self.calculate_win_probability(team_a, team_b, round_num)
        
        # 3. Pace Scaling (Phase 3.2)
        pace_a = self._get_metric(team_a, 'pace', 70.0)
        pace_b = self._get_metric(team_b, 'pace', 70.0)
        # Determine who controls the pace based on recent form/momentum
        form_a = self._get_metric(team_a, 'momentum', 0.5)
        form_b = self._get_metric(team_b, 'momentum', 0.5)
        pace_controller_weight = form_a / (form_a + form_b) if (form_a + form_b) > 0 else 0.5
        base_possessions = (pace_a * pace_controller_weight) + (pace_b * (1 - pace_controller_weight))
        
        # Add random variance based on PaceVar
        var_a = self._get_metric(team_a, 'pace_variance', 2.0)
        var_b = self._get_metric(team_b, 'pace_variance', 2.0)
        total_possessions = int(random.gauss(base_possessions, (var_a + var_b) / 2))
        
        # 4. Simulation Resolution Loop (Phase 3.3)
        score_a = 0.0
        score_b = 0.0
        
        # Kill Shot triggers (Phase 3.3.1)
        ks_scored_a = self._get_metric(team_a, 'kill_shots_scored', 7.0)
        ks_scored_b = self._get_metric(team_b, 'kill_shots_scored', 7.0)
        ks_conc_a = self._get_metric(team_a, 'kill_shots_conceded', 7.0)
        ks_conc_b = self._get_metric(team_b, 'kill_shots_conceded', 7.0)
        
        # Resolve in segments to allow for "Run States"
        segments = 4 
        poss_per_segment = total_possessions // segments
        
        for _ in range(segments):
            # Probability trigger for a "Run State"
            if random.random() < 0.15: # 15% chance of a run state segment
                # Run is triggered, weight segment toward team with higher Kill Shot diff
                ks_diff_a = ks_scored_a - ks_conc_a
                ks_diff_b = ks_scored_b - ks_conc_b
                run_bias = (ks_diff_a - ks_diff_b) * 0.02 * self.weights.kill_shot_momentum_weight
                seg_prob = max(0.1, min(0.9, prob_a + run_bias))
            else:
                seg_prob = prob_a
            
            # Simplified point resolution for the segment
            # (Roughly: possessions * points per possession ~ scoring)
            # We use the probability to determine who 'wins' the segment points
            seg_winner_a = (random.random() < seg_prob)
            pts = (poss_per_segment * 1.1) + random.uniform(-5, 5) # NCAA avg PPP is ~1.0-1.1
            if seg_winner_a:
                score_a += pts
                score_b += (pts * 0.9) # Loser stays close in segment
            else:
                score_b += pts
                score_a += (pts * 0.9)
        
        # 5. Late-Game Free Throw Floor (Phase 3.3.2)
        if abs(score_a - score_b) < 5:
            ftr_a = self._get_metric(team_a, 'off_ft_rate', 0.3)
            ftr_b = self._get_metric(team_b, 'off_ft_rate', 0.3)
            if ftr_a > ftr_b:
                score_a += 1.5 # Clutch survival bonus
            elif ftr_b > ftr_a:
                score_b += 1.5
        
        winner = team_a_name if score_a >= score_b else team_b_name
        
        # State Update
        self.total_games += 1
        favored_team = team_a_name if prob_a > 0.5 else team_b_name
        if winner != favored_team:
            self.upset_count += 1
            
        return winner
