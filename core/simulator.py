import logging
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
        final_probability = base_probability * self.weights.pythagorean_weight
        
        # Step 2: Advanced Metric Modifiers
        # Defense Premium (Boosts the team with the better defense)
        def_delta = team_b.def_efficiency - team_a.def_efficiency # lower def_efficiency is better
        defense_bonus = (def_delta * 0.001) * self.weights.defense_premium
        final_probability += defense_bonus
        
        # Pace Variance (Pace pushes probability closer to 50% for underdogs)
        if team_a.pace is not None and team_b.pace is not None:
            avg_pace = (team_a.pace + team_b.pace) / 2.0
            is_a_favorite = final_probability > 0.5
            pace_factor = (65.0 - avg_pace) * 0.005 # Baseline 65 possessions. Slower = positive pace_factor
            if is_a_favorite:
                final_probability -= pace_factor * self.weights.pace_variance_weight
            else:
                final_probability += pace_factor * self.weights.pace_variance_weight
            
        # eFG% Matchup (A's offense vs B's defense)
        if None not in (team_a.off_efg_pct, team_b.def_efg_pct, team_b.off_efg_pct, team_a.def_efg_pct):
            a_off_b_def_efg = team_a.off_efg_pct - team_b.def_efg_pct
            b_off_a_def_efg = team_b.off_efg_pct - team_a.def_efg_pct
            efg_advantage = (a_off_b_def_efg - b_off_a_def_efg) * 0.002
            final_probability += efg_advantage * self.weights.efg_matchup_weight
        
        # Turnover Matchup (A's ball protection vs B's pressure)
        if None not in (team_a.def_to_pct, team_a.off_to_pct, team_b.def_to_pct, team_b.off_to_pct):
            a_to_margin = team_a.def_to_pct - team_a.off_to_pct # Positive means they force more than they commit
            b_to_margin = team_b.def_to_pct - team_b.off_to_pct
            to_advantage = (a_to_margin - b_to_margin) * 0.002
            final_probability += to_advantage * self.weights.turnover_matchup_weight
        
        # SOS & Momentum
        if team_a.sos is not None and team_b.sos is not None:
            sos_advantage = (team_a.sos - team_b.sos) * 0.001
            final_probability += sos_advantage * self.weights.sos_weight
        
        if team_a.momentum is not None and team_b.momentum is not None:
            momentum_advantage = (team_a.momentum - team_b.momentum) * 0.05
            final_probability += momentum_advantage * self.weights.momentum_weight
        
        # Step 3: Apply human intuition modifier
        net_intuition = team_a.intuition_score - team_b.intuition_score
        intuition_modifier = net_intuition * self.weights.intuition_weight
        
        final_probability += intuition_modifier
        
        # Clamp to valid probability bounds [0.01, 0.99]
        final_probability = max(0.01, min(0.99, final_probability))
        
        team_a_pct = round(final_probability * 100, 1)
        logging.debug(
            f"Matchup: {team_a.name} vs {team_b.name} | "
            f"Base Stats: {round(base_probability * 100, 1)}% | "
            f"Intuition Delta: {net_intuition}pts | "
            f"Final: {team_a.name} {team_a_pct}%"
        )
        
        return final_probability

    def simulate_game(self, team_a: Team, team_b: Team) -> Team:
        """
        Simulates a single game between two teams using the calculated probability.
        Note: This is deterministic for testing purposes right now (highest prob wins).
        In the future, we will use random.random() for Monte Carlo simulations.
        """
        prob_a = self.calculate_win_probability(team_a, team_b)
        
        if prob_a >= 0.5:
            return team_a
        else:
            return team_b
