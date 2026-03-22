from dataclasses import dataclass
from typing import Optional, Dict, Any

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
    year: Optional[int] = None # The tournament year for era-aware simulation
    
    # Advanced Metrics (with defaults so instantiation without them doesn't fail)
    pace: Optional[float] = None           # Adjusted Tempo (Possessions per 40 min)
    off_efg_pct: Optional[float] = None    # Offensive Effective Field Goal %
    def_efg_pct: Optional[float] = None    # Defensive Effective Field Goal %
    off_to_pct: Optional[float] = None     # Offensive Turnover %
    def_to_pct: Optional[float] = None     # Defensive Turnover %
    sos: Optional[float] = None            # Strength of Schedule (e.g., KenPom SOS rating)
    momentum: Optional[float] = None       # Win % over the last 10 games
    recent_form: Optional[float] = None    # Peaking Indicator: Net Rating over last 10 games
    pace_variance: Optional[float] = None # Variance in possessions p/game
    trb_pct: Optional[float] = None        # Total Rebound Percentage
    three_par: Optional[float] = None      # 3-Point Attempt Rate
    off_ft_pct: Optional[float] = None     # Offensive Free Throw % (Percentage made)
    def_ft_pct: Optional[float] = None     # Defensive Free Throw % Allowed
    
    # Chaos/Grit Metrics (Phase 4)
    off_ft_rate: Optional[float] = None    # FTr: FTA / FGA (Aggressiveness)
    off_ast_pct: Optional[float] = None    # AST%: Assisted field goals
    off_stl_pct: Optional[float] = None    # STL%: Steal percentage
    off_blk_pct: Optional[float] = None    # BLK%: Block percentage
    off_orb_pct: Optional[float] = None    # ORB%: Offensive rebound percentage
    luck: Optional[float] = None           # Luck/Overachievement metric
    off_ts_pct: Optional[float] = None    # True Shooting Percentage (Phase 4)
    def_ft_rate: Optional[float] = None    # FTr Allowed (Phase 5+)
    total_games: Optional[int] = None      # Experience proxy (Phase 4)
    bench_minutes_pct: Optional[float] = None # Bench usage % (Phase 5 fatigue logic)
    coach_tournament_wins: Optional[int] = None # Coach Moxie metric (Research Loop 1)
    star_reliance: Optional[float] = None # Pricing index for usage concentration (Phase 9)
    total_win_pct: Optional[float] = None # Cumulative Win % (Phase 2 refined SOS)
    
    # Advanced Modern Metrics (Cycle 4)
    adj_off_sq: Optional[float] = None    # ShotQuality Adjusted Offensive Efficiency
    adj_def_sq: Optional[float] = None    # ShotQuality Adjusted Defensive Efficiency
    rim_3_rate: Optional[float] = None    # Rim-and-3 Shooting Rate
    kill_shots_scored: Optional[float] = None # EvanMiya Kill Shots (10-0 runs)
    kill_shots_conceded: Optional[float] = None
    bpr: Optional[float] = None           # EvanMiya Bayesian Performance Rating
    
    # Advanced Matchup Metrics (Cycle 3)
    off_three_pt_pct: Optional[float] = None
    def_three_pt_pct: Optional[float] = None
    off_two_pt_pct: Optional[float] = None
    def_two_pt_pct: Optional[float] = None
    rim_protection_eff: Optional[float] = None
    def_steal_rate: Optional[float] = None
    def_orb_pct: Optional[float] = None
    def_adj_eff: Optional[float] = None
    distance_from_home: Optional[float] = None # Alias for travel_dist used in some logic
    
    # Career/Venue Performance
    home_w: Optional[int] = None
    home_l: Optional[int] = None
    away_w: Optional[int] = None
    away_l: Optional[int] = None
    conf_w: Optional[int] = None        # Conference record (Phase 5)
    conf_l: Optional[int] = None        # Conference record (Phase 5)

    # Rounds 11-15: Fine-Grained Context
    travel_dist: Optional[float] = None # Miles from home to venue
    travel_east: Optional[bool] = None # True if traveling across time zones eastward
    portal_usage_pct: Optional[float] = None # % of usage from transfers
    freshman_usage_pct: Optional[float] = None # % of usage from freshmen
    tourney_momentum: Optional[float] = None # Momentum from conference tourney (0-1)
    neutral_w: Optional[int] = None        # Derived (Phase 5)
    neutral_l: Optional[int] = None        # Derived (Phase 5)
    conference: Optional[str] = None       # Conference name
    is_power_conf: Optional[bool] = None   # SEC, Big12, BigTen, ACC, BigEast, Pac12
    historical_tourney_wins: Optional[int] = None # Program history (Blue Blood proxy)
    
    @property
    def road_dominance(self) -> float:
        """Road win % minus home win %."""
        home_total = (self.home_w or 0) + (self.home_l or 0)
        away_total = (self.away_w or 0) + (self.away_l or 0)
        
        home_pct = (self.home_w / home_total) if home_total > 0 else 0.5
        away_pct = (self.away_w / away_total) if away_total > 0 else 0.5
        
        return away_pct - home_pct

    @property
    def neutral_win_pct(self) -> float:
        """
        Neutral site win percentage.
        USER Feedback: Neutral sites are not 50/50; they shift more towards 'Away' 
        for the higher seed/favorite. We weight existing neutral record, 
        but default to a slightly away-leaning baseline (0.45) if no data.
        """
        total = (self.neutral_w or 0) + (self.neutral_l or 0)
        if total == 0:
            # USER: Neutral is 0.25 on a [0=Away, 1=Home] scale.
            return 0.25 
        
        # Factor in true road dominance: if a team is great away, they likely handle neutral better
        road_perf = self.road_dominance # (Win% Away - Win% Home)
        return max(0.0, (self.neutral_w / total) + (road_perf * 0.1)) # Subtle adjustment

    @property
    def non_conf_win_pct(self) -> float:
        """Non-conference win percentage."""
        total_w = (self.home_w or 0) + (self.away_w or 0) + (self.neutral_w or 0)
        total_l = (self.home_l or 0) + (self.away_l or 0) + (self.neutral_l or 0)
        
        non_conf_w = max(0, total_w - (self.conf_w or 0))
        non_conf_l = max(0, total_l - (self.conf_l or 0))
        
        total = non_conf_w + non_conf_l
        if total == 0:
            return 0.5
        return non_conf_w / total
# Actually I'll use the record logic.

    @property
    def archetype(self) -> str:
        """Returns a string label representing the team's playing style."""
        if (self.off_efficiency or 100) > 118 and (self.def_efficiency or 100) < 94:
            return "Juggernaut"
        if (self.pace or 70) < 66 and (self.def_efficiency or 100) < 96:
            return "Pace Killer"
        if (self.off_orb_pct or 0) > 34.0:
            return "Glass Crasher"
        if (self.three_par or 0) > 0.45 and (self.def_to_pct or 0) > 21.0:
            return "Chaos Engine"
        if (self.seed or 1) >= 11 and (self.pace or 70) < 67:
            return "Cinderella Thread"
        return "Standard"

    @property
    def pythagorean_expectation(self) -> float:
        """
        Calculates the team's expected win percentage against an average Div I team
        using the standard KenPom exponent of 11.5.
        
        Formula: AdjO^11.5 / (AdjO^11.5 + AdjD^11.5)
        """
        exponent = 11.5
        adj_o_exp = (self.off_efficiency or 100.0) ** exponent
        adj_d_exp = (self.def_efficiency or 100.0) ** exponent
        return adj_o_exp / (adj_o_exp + adj_d_exp)

    @property
    def experience(self) -> float:
        """Normalized experience proxy (0.0 to 4.0)."""
        # Average games in a 4-year career is ~120. Scale total_games to 0-4.
        return min(4.0, (self.total_games or 30) / 30.0)

    @property
    def intuition_factor(self) -> float:
        """
        The Definitive Composite Metric.
        Weights: Efficiency (40%), SOS (30%), Experience (15%), Momentum (15%).
        Normalized to 0-100 scale.
        """
        eff = self.pythagorean_expectation * 100.0
        s = min(100.0, max(0.0, (self.sos or 0.0) * 5.0 + 50.0)) # Scale SOS
        e = min(100.0, (self.total_games or 30) * 2.0)
        m = (self.momentum or 0.5) * 100.0
        
        return (eff * 0.4) + (s * 0.3) + (e * 0.15) + (m * 0.15)
