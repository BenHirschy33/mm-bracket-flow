import logging
import random
import math
from typing import Optional, List, Dict, Any
from .team_model import Team
from .config import SimulationWeights, DEFAULT_WEIGHTS

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class SimulatorEngine:
    def __init__(self, teams: Dict[str, Team], weights: SimulationWeights, locks: Optional[Dict[str, str]] = None):
        self.teams = teams
        self.weights = weights
        self.locks = locks or {}
        self.volatility = 0.0 # Blending factor (0.0 = pure metrics, 1.0 = pure random)
        # Stateful tracking for "Due Factor" (Reset per simulation run)
        self.upset_count = 0
        self.total_games = 0
        
    def reset_state(self):
        """Reset state for a new bracket simulation."""
        self.upset_count = 0
        self.total_games = 0

    def simulate_game(self, team_a: Team, team_b: Team, mode: str = "deterministic") -> Team:
        """Simulates a game and returns the winner, incorporating Volatility Index."""
        prob_a = self.calculate_win_probability(team_a, team_b)
        
        # Apply Volatility Index blending
        # If volatility is 1.0, prob_a becomes 0.5 (perfect coin flip)
        blended_prob = ((1.0 - self.volatility) * prob_a) + (self.volatility * 0.5)
        
        if mode == "deterministic":
            return team_a if blended_prob >= 0.5 else team_b
        else:
            return team_a if random.random() < blended_prob else team_b

    def _get_metric(self, team, attr, default=0.0):
        """Safely gets a numeric metric from a team object, defaulting if None."""
        val = getattr(team, attr, default)
        return val if val is not None else default

    def calculate_win_probability(self, team_a: Team, team_b: Team, round_num: int = 1) -> float:
        """Calculates win prob using a Logistic (Sigmoid) model for calibration."""
        # Step 1: Base Pythagorean Expectation (Initial Logit)
        # logit(p) = log(p / (1-p))
        eff_a = self._get_metric(team_a, 'pythagorean_expectation', 0.5)
        eff_b = self._get_metric(team_b, 'pythagorean_expectation', 0.5)
        
        # Avoid division by zero
        eff_a = max(0.0001, eff_a)
        eff_b = max(0.0001, eff_b)
        
        # Base delta in logit space
        # p = a / (a+b) -> logit(p) = log(a/b)
        delta = math.log(eff_a / eff_b)
        
        # Step 2: Advanced Metric Modifiers (Now additive in Logit space)
        # This prevents probability saturation and handles heavy weights gracefully.
        
        # Defense Premium
        def_a = self._get_metric(team_a, 'def_efficiency', 100.0)
        def_b = self._get_metric(team_b, 'def_efficiency', 100.0)
        delta += (def_b - def_a) * 0.05 * self.weights.defense_premium
        
        # Seed Advantage
        seed_diff = self._get_metric(team_b, 'seed', 16) - self._get_metric(team_a, 'seed', 16)
        delta += seed_diff * 0.2 * self.weights.seed_weight
        
        # SOS
        sos_a = self._get_metric(team_a, 'sos', 0.0) * self._get_metric(team_a, 'total_win_pct', 0.5)
        sos_b = self._get_metric(team_b, 'sos', 0.0) * self._get_metric(team_b, 'total_win_pct', 0.5)
        delta += (sos_a - sos_b) * 0.1 * self.weights.sos_weight
            
        # Turnover Margin
        margin_a = self._get_metric(team_a, 'def_to_pct', 20.0) - self._get_metric(team_a, 'off_to_pct', 20.0)
        margin_b = self._get_metric(team_b, 'def_to_pct', 20.0) - self._get_metric(team_b, 'off_to_pct', 20.0)
        delta += (margin_a - margin_b) * 0.1 * self.weights.to_weight
            
        # Momentum
        delta += (self._get_metric(team_a, 'momentum', 0.5) - self._get_metric(team_b, 'momentum', 0.5)) * 1.5 * self.weights.momentum_weight
            
        # Free Throw Advantage
        ft_a = (self._get_metric(team_a, 'off_ft_pct', 70.0) / 100.0) * self._get_metric(team_b, 'def_ft_rate', 0.3)
        ft_b = (self._get_metric(team_b, 'off_ft_pct', 70.0) / 100.0) * self._get_metric(team_a, 'def_ft_rate', 0.3)
        delta += (ft_a - ft_b) * 2.0 * self.weights.ft_weight
            
        # Foul Drawing
        delta += (self._get_metric(team_a, 'off_ft_rate', 0.3) - self._get_metric(team_b, 'off_ft_rate', 0.3)) * 2.0 * self.weights.foul_drawing_weight

        # Chaos Stats
        delta += (self._get_metric(team_a, 'off_stl_pct', 8.0) - self._get_metric(team_b, 'off_stl_pct', 8.0)) * 0.2 * self.weights.stl_weight
        delta += (self._get_metric(team_a, 'off_blk_pct', 8.0) - self._get_metric(team_b, 'off_blk_pct', 8.0)) * 0.2 * self.weights.blk_weight
        delta += (self._get_metric(team_a, 'off_orb_pct', 25.0) - self._get_metric(team_b, 'off_orb_pct', 25.0)) * 0.2 * self.weights.orb_weight
        delta += (self._get_metric(team_b, 'def_ft_rate', 0.3) - self._get_metric(team_a, 'def_ft_rate', 0.3)) * 2.0 * self.weights.def_ft_rate_weight

        # Luck & Momentum Regression
        luck_a = self._get_metric(team_a, 'luck', 0.0)
        luck_b = self._get_metric(team_b, 'luck', 0.0)
        delta += (luck_b - luck_a) * 0.5 * self.weights.luck_weight
        
        # 3PAr Volatility (Shrinks the delta towards zero if both teams are 3pt heavy)
        avg_3par = (self._get_metric(team_a, 'three_par', 0.37) + self._get_metric(team_b, 'three_par', 0.37)) / 2
        volatility_scale = 1.0 / (1.0 + (avg_3par - 0.37) * self.weights.three_par_volatility_weight)
        delta *= max(0.5, min(1.5, volatility_scale))

        # Efficiency Advantage
        delta += (self._get_metric(team_a, 'off_ts_pct', 55.0) - self._get_metric(team_b, 'off_ts_pct', 55.0)) * 0.1 * self.weights.ts_weight
        delta += (self._get_metric(team_a, 'total_games', 30) - self._get_metric(team_b, 'total_games', 30)) * 0.02 * self.weights.experience_weight

        # Round-Weighted Defense
        def_advantage = (self._get_metric(team_b, 'def_efficiency', 100.0) - self._get_metric(team_a, 'def_efficiency', 100.0))
        round_bonus = (round_num - 1) * self.weights.late_round_def_premium
        delta += def_advantage * 0.05 * round_bonus

        # Era-Specific Scaling
        year = team_a.year or 2024
        if year <= 2010: delta += (def_b - def_a) * 0.02 * self.weights.defensive_grit_bias
        if year >= 2015: delta += (self._get_metric(team_a, 'three_par', 0.35) - self._get_metric(team_b, 'three_par', 0.35)) * 1.5 * self.weights.three_point_dominance

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

        # Final Probability Calculation (Sigmoid)
        try:
            # P(A) = 1 / (1 + e^-delta)
            # Use k factor to scale the steepness if needed (default 1.0)
            final_probability = 1.0 / (1.0 + math.exp(-delta))
        except OverflowError:
            final_probability = 1.0 if delta > 0 else 0.0

        # Clamp to valid probability bounds [0.01, 0.99] to allow for upsets always
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
