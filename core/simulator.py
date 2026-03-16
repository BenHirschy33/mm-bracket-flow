import logging
import random
from .team_model import Team
from .config import SimulationWeights, DEFAULT_WEIGHTS

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class SimulatorEngine:
    """
    The mathematical core of MM-Bracket-Flow.
    Calculates matchup win probabilities based on advanced metrics, historical weights,
    and human intuition, gracefully handling missing 'null' data.
    """
    
    def __init__(self, weights: SimulationWeights = None):
        """
        Args:
            weights: Configuration object for toggling/scaling metrics.
        """
        self.weights = weights or DEFAULT_WEIGHTS
        
    def calculate_win_probability(self, team_a: Team, team_b: Team) -> float:
        """
        Calculates the probability that Team A beats Team B.
        Skips advanced metric calculations if the data is None.
        """
        # Step 1: Base statistical probability (Log5 formula)
        p_a = team_a.pythagorean_expectation
        p_b = team_b.pythagorean_expectation
        
        base_probability = (p_a - (p_a * p_b)) / (p_a + p_b - (2 * p_a * p_b))
        final_probability = base_probability
        
        # Step 2: Advanced Metric Modifiers
        # Defense Premium (Boosts the team with the better defense)
        def_b = team_b.def_efficiency or 100.0
        def_a = team_a.def_efficiency or 100.0
        def_delta = def_b - def_a # lower def_efficiency is better
        # We'll bake defense premium into efficiency weight for simplicity in optimization
        final_probability += (def_delta * 0.001) * self.weights.efficiency_weight
        
        # Pace Variance (Slow games increase underdog win probability by reducing possessions)
        if team_a.pace is not None and team_b.pace is not None:
            avg_pace = (team_a.pace + team_b.pace) / 2.0
            # Standard pace baseline is ~65-68. 
            # If pace is below 65, we consider it a 'variance-heavy' game.
            if avg_pace < 65.0:
                pace_diff = 65.0 - avg_pace
                # Shift probability towards 0.5 (the middle)
                # The higher the weight, the more the favorite's edge is neutralized
                neutralization_factor = (pace_diff * 0.02) * self.weights.pace_variance_weight
                if final_probability > 0.5:
                    final_probability = max(0.5, final_probability - neutralization_factor)
                else:
                    final_probability = min(0.5, final_probability + neutralization_factor)
            
        # eFG% Matchup (A's offense vs B's defense)
        if None not in (team_a.off_efg_pct, team_b.def_efg_pct, team_b.off_efg_pct, team_a.def_efg_pct):
            a_off_b_def_efg = team_a.off_efg_pct - team_b.def_efg_pct
            b_off_a_def_efg = team_b.off_efg_pct - team_a.def_efg_pct
            efg_advantage = (a_off_b_def_efg - b_off_a_def_efg) * 0.002
            final_probability += efg_advantage * self.weights.efficiency_weight
        
        # Turnover Matchup (A's ball protection vs B's pressure)
        if None not in (team_a.def_to_pct, team_a.off_to_pct, team_b.def_to_pct, team_b.off_to_pct):
            a_to_margin = team_a.def_to_pct - team_a.off_to_pct # Positive means they force more than they commit
            b_to_margin = team_b.def_to_pct - team_b.off_to_pct
            to_advantage = (a_to_margin - b_to_margin) * 0.002
            final_probability += to_advantage * self.weights.to_weight
            
        # Rebounding Advantage (TRB% > 50 means they get more than half of all available rebounds)
        if team_a.trb_pct is not None and team_b.trb_pct is not None:
            reb_advantage = (team_a.trb_pct - team_b.trb_pct) * 0.003
            final_probability += reb_advantage * self.weights.trb_weight
        
        # SOS & Momentum
        if team_a.sos is not None and team_b.sos is not None:
            sos_advantage = (team_a.sos - team_b.sos) * 0.001
            final_probability += sos_advantage * self.weights.sos_weight
        
        if team_a.momentum is not None and team_b.momentum is not None:
            momentum_advantage = (team_a.momentum - team_b.momentum) * 0.05
            final_probability += momentum_advantage * self.weights.momentum_weight
            
        # Free Throw Advantage (proxy for efficiency and drawing fouls)
        if team_a.off_ft_pct is not None and team_b.def_ft_pct is not None and \
           team_b.off_ft_pct is not None and team_a.def_ft_pct is not None:
            ft_advantage = (team_a.off_ft_pct - team_b.def_ft_pct) - (team_b.off_ft_pct - team_a.def_ft_pct)
            final_probability += ft_advantage * 0.01 * self.weights.ft_weight
            
        # 3PAr Advantage (higher 3PAr can mean more variance, but also efficiency if they make them)
        if team_a.three_par is not None and team_b.three_par is not None:
            threepar_advantage = (team_a.three_par - team_b.three_par) * 0.01
            final_probability += threepar_advantage * self.weights.three_par_weight
        
        # Clamp to valid probability bounds [0.01, 0.99]
        final_probability = max(0.01, min(0.99, final_probability))
        
        team_a_pct = round(final_probability * 100, 1)
        logging.debug(
            f"Matchup: {team_a.name} vs {team_b.name} | "
            f"Base Stats: {round(base_probability * 100, 1)}% | "
            f"Final: {team_a.name} {team_a_pct}%"
        )
        
        return final_probability

    def simulate_game(self, team_a: Team, team_b: Team, mode: str = "deterministic") -> Team:
        """
        Simulates a single game between two teams using the calculated probability.
        If mode="probabilistic", it rolls a random number against the win probability.
        """
        prob_a = self.calculate_win_probability(team_a, team_b)
        
        if mode == "probabilistic":
            if random.random() < prob_a:
                return team_a
            return team_b
        else:
            if prob_a >= 0.5:
                return team_a
            return team_b
