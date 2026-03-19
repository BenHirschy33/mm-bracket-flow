import json
import csv
import logging
from pathlib import Path
from typing import Dict
try:
    import yaml
except ImportError:
    yaml = None
from .team_model import Team

def normalize_team_name(name: str) -> str:
    """
    Standardizes team names to resolve 'St.' vs 'Saint' vs 'State' ambiguity
    and handle common aliases (e.g. UMBC).
    """
    if not name: return ""
    
    # 1. Basic Cleaning
    name = name.strip()
    
    # 2. Static Alias Mapping (High Priority)
    aliases = {
        "Connecticut": "UConn",
        "UMBC": "Maryland-Baltimore County",
        "UPenn": "Pennsylvania",
        "Penn": "Pennsylvania",
        "VPI": "Virginia Tech",
        "Ole Miss": "Mississippi",
        "LSU": "Louisiana State",
        "N.C. State": "NC State",
        "North Carolina St.": "NC State",
        "UNLV": "Nevada-Las Vegas",
        "USC": "Southern California",
        "SMU": "Southern Methodist",
        "TCU": "Texas Christian",
        "BYU": "Brigham Young",
        "St. Mary's (CA)": "Saint Mary's",
        "UL Lafayette": "Louisiana",
        "Umass": "Massachusetts"
    }
    if name in aliases:
        return aliases[name]

    # 3. Contextual 'St.' Rules
    # Rule A: Trailing 'St.' -> 'State' (e.g. Michigan St. -> Michigan State)
    if name.endswith(" St."):
        name = name[:-4] + " State"
    elif name.endswith(" St"):
        name = name[:-3] + " State"
        
    # Rule B: Leading 'St.' -> 'Saint' (e.g. St. John's -> Saint John's)
    if name.startswith("St. "):
        name = "Saint " + name[4:]
    elif name.startswith("St "):
        name = "Saint " + name[3:]
        
    return name

def load_teams(csv_filepath: str | Path, year: int = None) -> Dict[str, Team]:
    """
    Parses a team_stats.csv file and returns a dictionary mapping team names
    to fully populated Team dataclasses. Optionally links YAML intuition data.
    """
    path = Path(csv_filepath)
    if not path.exists():
        raise FileNotFoundError(f"Could not find team stats at {path}")
        
    teams = {}
    
    def safe_float(val):
        """Converts string 'null' or empty blanks to Python's None type gracefully."""
        if not val or val.strip() == "" or val.strip().lower() in ("null", "none", "n/a"):
            return None
        return float(val)

    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Flexible column matching in case CSV headers slightly change
            name_key = next((k for k in row.keys() if k and k.lower() == 'team'), None)
            if not name_key:
                continue
            name = row[name_key].strip()
            
            # Skip empty or invalid team names (nan rows in scraped CSVs)
            if not name or name.lower() in ('nan', 'none', 'n/a', ''):
                continue
            
            team = Team(
                name=name,
                seed=int(safe_float(row.get("Seed", 16)) or 16),
                year=year,
                off_efficiency=safe_float(row.get("AdjO")) or 100.0,
                def_efficiency=safe_float(row.get("AdjD")) or 100.0,
                off_ppg=safe_float(row.get("Off_PPG")) or 70.0,
                def_ppg=safe_float(row.get("Def_PPG")) or 70.0,
                
                # Advanced metrics (allow None if missing)
                pace=safe_float(row.get("Pace")),
                off_efg_pct=safe_float(row.get("eFG_Off")),
                def_efg_pct=safe_float(row.get("eFG_Def")),
                off_to_pct=safe_float(row.get("TO_Off")),
                def_to_pct=safe_float(row.get("TO_Def")),
                trb_pct=safe_float(row.get("TRB")),
                three_par=safe_float(row.get("3PAr")),
                off_ft_pct=safe_float(row.get("FT_Off")),
                def_ft_pct=safe_float(row.get("FT_Def")),
                sos=safe_float(row.get("SOS")),
                momentum=safe_float(row.get("Momentum"))
            )
            teams[name] = team

    # Phase 4: Merge additional metrics from raw_team_stats.csv if it exists
    raw_path = path.parent / "raw_team_stats.csv"
    if raw_path.exists():
        with open(raw_path, 'r', encoding='utf-8') as f:
            # raw_team_stats.csv has 2 lines of header sometimes, let's detect and skip
            header_lines = [f.readline(), f.readline()]
            # Find which line is the actual data header
            header = header_lines[0].split(',')
            if 'School' not in header:
                header = header_lines[1].split(',')
                f.seek(0)
                f.readline() # Skip first
                f.readline() # Skip second
            else:
                f.seek(0)
                f.readline() # Skip first

            reader = csv.reader(f)
            headers = next(reader)
            if "School" not in headers: headers = next(reader)
            
            for row in reader:
                if len(row) < 2 or not row[1]: continue
                school = row[1].replace("\xa0NCAA", "").strip()
                if school.lower() in ('school', ''): continue
                
                matched_team = teams.get(school)
                
                # Try alternatives if not matched
                if not matched_team:
                    norm_school = normalize_team_name(school)
                    if norm_school in teams:
                        matched_team = teams[norm_school]
                    else:
                        # Secondary check: loop through normalized keys
                        for t_name, t_obj in teams.items():
                            if normalize_team_name(t_name) == norm_school:
                                matched_team = t_obj
                                break

                if matched_team:
                    # Metrics (approximate indices based on previous audit)
                    # Pace is around 21, ORtg 22, FTr 23, etc.
                    try:
                        total_w = int(row[3]) if row[3] else 0
                        total_l = int(row[4]) if row[4] else 0
                        matched_team.total_games = int(row[2]) if row[2] else 0
                        
                        # Phase 5+: Provenance                        # Based on header: Rk:0, School:1, G:2, W:3, L:4, W-L%:5, SRS:6, SOS:7, Sep:8, HW:9, HL:10, Sep:11, AW:12, AL:13, Sep:14, NW:15, NL:16
                        try:
                            # Record components
                            matched_team.home_w = int(row[9]) if row[9].strip() else 0
                            matched_team.home_l = int(row[10]) if row[10].strip() else 0
                            matched_team.away_w = int(row[12]) if row[12].strip() else 0
                            matched_team.away_l = int(row[13]) if row[13].strip() else 0
                            matched_team.neutral_w = int(row[15]) if row[15].strip() else 0
                            matched_team.neutral_l = int(row[16]) if row[16].strip() else 0
                            
                            # Advanced stats: Pace:20, ORtg:21 (Wait, let's verify)
                            # Actually from head: Separator at 20. Pace is 21. ORtg is 22.
                            pace = safe_float(row[21]) or 70.0
                            matched_team.pace = pace
                        except (ValueError, IndexError) as e:
                            logging.warning(f"Error parsing record components for {school}: {e}")
                            # Fallback to derived neutral stats if direct parsing fails
                            home_w = matched_team.home_w or 0
                            away_w = matched_team.away_w or 0
                            matched_team.neutral_w = max(0, total_w - home_w - away_w)
                            
                            home_l = matched_team.home_l or 0
                            away_l = matched_team.away_l or 0
                            matched_team.neutral_l = max(0, total_l - home_l - away_l)

                        # Phase 5+: Derived Efficiency Baseline
                        # pace = matched_team.pace if (matched_team.pace and matched_team.pace > 0) else 70.0 # Now set above
                        total_games = matched_team.total_games if matched_team.total_games else 30
                        
                        # Derive Efficiency (AdjO/AdjD)
                        points_tm = safe_float(row[18]) or 0.0
                        points_opp = safe_float(row[19]) or 0.0
                        
                        if points_tm > 0:
                            matched_team.off_efficiency = (points_tm / total_games) / pace * 100
                        if points_opp > 0:
                            matched_team.def_efficiency = (points_opp / total_games) / pace * 100
                        
                        # Phase 4/5/6 Metrics (Corrected Indices)
                        # Pace:21, ORtg:22, FTr:23, 3PAr:24, TS%:25, TRB%:26, AST%:27, STL%:28, BLK%:29, eFG%:30, TOV%:31, ORB%:32, FT/FGA:33
                        matched_team.off_ts_pct = safe_float(row[25])
                        matched_team.off_ft_rate = safe_float(row[23])
                        matched_team.off_ast_pct = safe_float(row[27])
                        matched_team.off_stl_pct = safe_float(row[28])
                        matched_team.off_blk_pct = safe_float(row[29])
                        matched_team.off_orb_pct = safe_float(row[32])
                        matched_team.def_ft_rate = safe_float(row[33]) 
                        
                        # Phase 9: Advanced Regression Signals
                        wl_pct = safe_float(row[5])
                        
                        # Better Luck: Actual Win% vs Pythagorean Expectation
                        if wl_pct is not None and matched_team.off_efficiency and matched_team.def_efficiency:
                            pyth = (matched_team.off_efficiency**11.5) / (matched_team.off_efficiency**11.5 + matched_team.def_efficiency**11.5)
                            matched_team.luck = wl_pct - pyth
                            matched_team.total_win_pct = wl_pct
                        
                        # Star Reliance Proxy: Slashers (FTR) + Independent Scorers (Low AST%)
                        if matched_team.off_ft_rate is not None and matched_team.off_ast_pct is not None:
                            # Scale AST% to 0-1 (inverse) and combine with FTR
                            ast_inv = (100.0 - matched_team.off_ast_pct) / 100.0
                            matched_team.star_reliance = (matched_team.off_ft_rate * 0.5) + ast_inv
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Error parsing raw stats for {school}: {e}")
                        continue
                    
                    # Backfill TRB% if missing from main
                    if matched_team.trb_pct is None:
                        try:
                            matched_team.trb_pct = safe_float(row[25]) # Index 25 for TRB%
                        except (ValueError, IndexError):
                            pass
            
    return teams

def load_bracket(json_filepath: str | Path) -> dict:
    """
    Parses the bracket JSON file (e.g. chalk_bracket.json) which defines the starting matchups.
    Returns the raw dictionary data.
    """
    path = Path(json_filepath)
    if not path.exists():
        raise FileNotFoundError(f"Could not find bracket file at {path}")
        
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    return data
