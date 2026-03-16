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
        final_probability += (def_delta * 0.001) * self.weights.defense_premium
        
        # Pace Variance (Pace pushes probability closer to 50% for underdogs)
        if team_a.pace is not None and team_b.pace is not None:
            avg_pace = (team_a.pace + team_b.pace) / 2.0
            is_a_favorite = final_probability > 0.5
            pace_factor = (65.0 - avg_pace) * 0.005 # Baseline 65 possessions. Slower = positive pace_factor
            # We'll use efficiency weight as a proxy for pace variance if needed, 
            # but for now we'll just use the dedicated weights
            pass
            
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
        
        # Step 3: Apply human intuition modifier
        def get_situational_intuition(team_eval: Team, opponent: Team) -> float:
            score = team_eval.intuition_score
            data = team_eval.intuition_data
            if not data:
                return score
                
            score = float(data.get("base", score))
            score += float(data.get("injuries_penalty", 0.0))
            score += float(data.get("conf_tourney_boost", 0.0))
            score += float(data.get("motivation_factor", 0.0))
            
            for vuln in data.get("vulnerabilities", []):
                metric = vuln.get("metric")
                thresh = float(vuln.get("threshold", 0.0))
                penalty = float(vuln.get("penalty", 0.0))
                
                opp_val = None
                if metric == "3PAr": opp_val = opponent.three_par
                elif metric == "Pace": opp_val = opponent.pace
                elif metric == "TO%_Def": opp_val = opponent.def_to_pct # Press vulnerability
                
                if opp_val is not None and opp_val >= thresh:
                    score += penalty
                    
            return score

        a_situational = get_situational_intuition(team_a, team_b)
        b_situational = get_situational_intuition(team_b, team_a)
        
        net_intuition = a_situational - b_situational
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
