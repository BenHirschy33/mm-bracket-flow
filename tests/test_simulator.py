from core.team_model import Team
from core.simulator import SimulatorEngine
import pytest

def test_pythagorean_expectation():
    """Verify KenPom Log5 expectation math with known values."""
    # Duke 2026 Projections (Elite Offense/Defense)
    duke = Team("Duke", 1, 121.5, 92.1, 84.5, 65.2)
    
    # Expected log5 for an elite team should be very close to 1.0 (0.95+)
    exp = duke.pythagorean_expectation
    assert exp > 0.95
    assert exp < 1.0

def test_simulator_matchup_chalk():
    """Verify a 1 seed heavily favored over a 16 seed without intuition."""
    duke = Team("Duke", 1, 121.5, 92.1, 84.5, 65.2)
    fdu = Team("FDU", 16, 105.2, 112.4, 72.5, 75.1)
    
    engine = SimulatorEngine()
    prob_duke = engine.calculate_win_probability(duke, fdu)
    
    # Duke should be heavily favored (>90%)
    assert prob_duke > 0.90
    
    # The winner of a simulated game should be Duke deterministically 
    # since we return the higher probability for now.
    winner = engine.simulate_game(duke, fdu)
    assert winner.name == "Duke"

def test_simulator_intuition_modifier():
    """Verify the 'Hirschy Factor' correctly impacts probability."""
    # Two extremely evenly matched teams
    team_a = Team("A", 4, 115.0, 95.0, 75.0, 65.0)
    team_b = Team("B", 5, 115.0, 95.0, 75.0, 65.0)
    
    engine = SimulatorEngine(intuition_weight=0.015)  # 1.5% per point
    
    # Base probability should be exactly 50%
    base_prob = engine.calculate_win_probability(team_a, team_b)
    assert base_prob == 0.50
    
    # If we add +10 Intuition to Team A, their probability should rise by 15% (to 65%)
    team_a.intuition_score = 10.0
    mod_prob = engine.calculate_win_probability(team_a, team_b)
    assert mod_prob == 0.65
    
    # If we add +10 to both, it cancels out back to 50%
    team_b.intuition_score = 10.0
    cancel_prob = engine.calculate_win_probability(team_a, team_b)
    assert cancel_prob == 0.50
