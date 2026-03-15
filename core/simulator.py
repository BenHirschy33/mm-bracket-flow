import logging
from .team_model import Team

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class SimulatorEngine:
    """
    The mathematical core of MM-Bracket-Flow.
    Calculates matchup win probabilities based on advanced metrics and human intuition.
    """
    
    def __init__(self, intuition_weight: float = 0.015):
        """
        Args:
            intuition_weight: The percentage shift in probability per 1 point
                              of intuition score. Default is 1.5% per point.
        """
        self.intuition_weight = intuition_weight
        
    def calculate_win_probability(self, team_a: Team, team_b: Team) -> float:
        """
        Calculates the probability that Team A beats Team B.
        
        Step 1: Log5 Pythagorean Expectation matchup probability.
        Step 2: Apply the Net "Hirschy Factor" intuition delta.
        
        Returns:
            float: Probability (0.0 to 1.0) of Team A winning.
        """
        # Step 1: Base statistical probability (Log5 formula)
        # P(A wins) = (Pa - Pa*Pb) / (Pa + Pb - 2*Pa*Pb)
        p_a = team_a.pythagorean_expectation
        p_b = team_b.pythagorean_expectation
        
        base_probability = (p_a - (p_a * p_b)) / (p_a + p_b - (2 * p_a * p_b))
        
        # Step 2: Apply human intuition modifier
        # A net positive intuition score heavily favors Team A.
        net_intuition = team_a.intuition_score - team_b.intuition_score
        intuition_modifier = net_intuition * self.intuition_weight
        
        final_probability = base_probability + intuition_modifier
        
        # Clamp to valid probability bounds [0.01, 0.99]
        # (We never assume 100% certainty in March Madness)
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
