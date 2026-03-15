from dataclasses import dataclass
from typing import Optional

@dataclass
class Team:
    """
    Standardized data model representing a tournament team and their
    advanced statistical profile for the simulation engine.
    """
    name: str
    seed: int
    off_efficiency: float  # e.g., KenPom Adjusted Offensive Efficiency (AdjO)
    def_efficiency: float  # e.g., KenPom Adjusted Defensive Efficiency (AdjD)
    off_ppg: float         # Raw Offensive Points Per Game
    def_ppg: float         # Raw Defensive Points Per Game Allowed
    
    # Advanced Metrics (with defaults so instantiation without them doesn't fail)
    pace: Optional[float] = None           # Adjusted Tempo (Possessions per 40 min)
    off_efg_pct: Optional[float] = None    # Offensive Effective Field Goal %
    def_efg_pct: Optional[float] = None    # Defensive Effective Field Goal %
    off_to_pct: Optional[float] = None     # Offensive Turnover %
    def_to_pct: Optional[float] = None     # Defensive Turnover %
    sos: Optional[float] = None            # Strength of Schedule (e.g., KenPom SOS rating)
    momentum: Optional[float] = None       # Win % over the last 10 games
    
    intuition_score: float = 0.0  # The 'Hirschy Factor' (-10 to +10)
    
    @property
    def pythagorean_expectation(self) -> float:
        """
        Calculates the team's expected win percentage against an average Div I team
        using the standard KenPom exponent of 11.5.
        
        Formula: AdjO^11.5 / (AdjO^11.5 + AdjD^11.5)
        """
        exponent = 11.5
        adj_o_exp = self.off_efficiency ** exponent
        adj_d_exp = self.def_efficiency ** exponent
        return adj_o_exp / (adj_o_exp + adj_d_exp)
