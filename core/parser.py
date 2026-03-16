import json
import csv
from pathlib import Path
from typing import Dict
try:
    import yaml
except ImportError:
    yaml = None
from .team_model import Team

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
            
            team = Team(
                name=name,
                seed=int(safe_float(row.get("Seed", 16)) or 16),
                off_efficiency=safe_float(row.get("AdjO", 100.0)),
                def_efficiency=safe_float(row.get("AdjD", 100.0)),
                off_ppg=safe_float(row.get("Off_PPG", 70.0)),
                def_ppg=safe_float(row.get("Def_PPG", 70.0)),
                
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
