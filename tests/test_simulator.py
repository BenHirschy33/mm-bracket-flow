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
    
    from core.config import SimulationWeights
    weights = SimulationWeights(intuition_weight=0.015)
    engine = SimulatorEngine(weights=weights)
    
    # Base probability should be exactly 50%
    base_prob = engine.calculate_win_probability(team_a, team_b)
    assert base_prob == 0.50
    
    # If we add +10 Intuition to Team A, their probability should rise by 15% (to 65%)
    team_a.intuition_score = 10.0
    mod_prob = engine.calculate_win_probability(team_a, team_b)
    assert round(mod_prob, 2) == 0.65
    
    # If we add +10 to both, it cancels out back to 50%
    team_b.intuition_score = 10.0
    cancel_prob = engine.calculate_win_probability(team_a, team_b)
    assert round(cancel_prob, 2) == 0.50

def test_advanced_metrics_toggle():
    """Verify we can completely disable advanced metrics returning to Pythagorean baseline."""
    from core.config import SimulationWeights
    # Create two heavily mismatched teams on advanced metrics, but identical pythagorean
    team_a = Team("A", 4, 115.0, 95.0, 75.0, 65.0, pace=75.0, off_efg_pct=60.0, def_efg_pct=50.0, off_to_pct=15.0, def_to_pct=15.0, sos=0.0, momentum=0.5)
    team_b = Team("B", 5, 115.0, 95.0, 75.0, 65.0, pace=60.0, off_efg_pct=40.0, def_efg_pct=50.0, off_to_pct=15.0, def_to_pct=15.0, sos=0.0, momentum=0.5)
    
    # With default weights, 'A' should have a massive advantage due to eFG% alone
    engine_default = SimulatorEngine()
    prob_a_default = engine_default.calculate_win_probability(team_a, team_b)
    
    # Now build an engine with everything zeroed out except pythagorean
    zero_weights = SimulationWeights(
        pythagorean_weight=1.0,
        pace_variance_weight=0.0,
        efg_matchup_weight=0.0,
        turnover_matchup_weight=0.0,
        sos_weight=0.0,
        momentum_weight=0.0,
        intuition_weight=0.0,
        defense_premium=0.0
    )
    engine_zeroed = SimulatorEngine(weights=zero_weights)
    prob_a_zeroed = engine_zeroed.calculate_win_probability(team_a, team_b)
    
    assert prob_a_default > 0.50
    assert round(prob_a_zeroed, 2) == 0.50

def test_simulator_null_handling():
    """Verify that if a stat is missing (None), the simulator gracefully skips it rather than crashing."""
    team_a = Team("A", 4, 115.0, 95.0, 75.0, 65.0, pace=75.0) # None for efg, to, sos
    team_b = Team("B", 5, 115.0, 95.0, 75.0, 65.0, pace=60.0) # None for efg, to, sos
    
    engine = SimulatorEngine()
    prob = engine.calculate_win_probability(team_a, team_b)
    
    # Base is 0.50. Defense is identical.
    # Pace logic: avg pace is 67.5. This is faster than 65.0.
    # pace_factor = (65.0 - 67.5) * 0.005 = -0.0125
    # A is underdog (or rather, not > 0.5 favorite), so it adds -0.0125 -> 0.4875.
    assert round(prob, 4) == 0.4875
