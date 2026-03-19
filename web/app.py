import sys
import os
# Ensure local dependencies are prioritised
sys.path.insert(0, os.path.join(os.getcwd(), 'local_lib_v2'))
sys.path.append(os.getcwd())

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from pathlib import Path

from core.parser import load_teams, load_bracket
from core.simulator import SimulatorEngine
from core.team_model import Team
from core.config import DEFAULT_WEIGHTS, SimulationWeights

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

def extract_weights(data):
    """Robustly extracts weights from request data, handling hyphens and underscores."""
    from core.config import SimulationWeights
    weights_dict = {}
    
    # Get all field names from SimulationWeights
    import dataclasses
    fields = [f.name for f in dataclasses.fields(SimulationWeights)]
    
    for field in fields:
        # Try underscore, then hyphen
        val = data.get(field)
        if val is None:
            hyphen_key = field.replace('_', '-')
            val = data.get(hyphen_key)
        
        # Specific short-codes used by the frontend
        if field == 'efficiency_weight' and val is None:
            val = data.get('eff')
        if field == 'sos_weight' and val is None:
            val = data.get('sos')
        if field == 'trb_weight' and val is None:
            val = data.get('trb')
        if field == 'to_weight' and val is None:
            val = data.get('to')
        if field == 'momentum_weight' and val is None:
            val = data.get('momentum')
        if field == 'ft_weight' and val is None:
            val = data.get('ft')
        
        if val is not None:
            try:
                weights_dict[field] = float(val)
            except (ValueError, TypeError):
                weights_dict[field] = getattr(DEFAULT_WEIGHTS, field)
        else:
            weights_dict[field] = getattr(DEFAULT_WEIGHTS, field)
            
    return SimulationWeights(**weights_dict)

@app.route('/api/teams/<int:year>')
def get_teams(year):
    try:
        base_dir = Path(f"years/{year}/data")
        teams = load_teams(base_dir / "team_stats.csv", year=year)
        
        # Merge seeds from bracket
        try:
            bracket = load_bracket(base_dir / "chalk_bracket.json")
            seeds_by_name = {}
            for reg_name, seeds in bracket.get("regions", {}).items():
                for s_str, name in seeds.items():
                    # Extract numeric seed
                    seeds_by_name[name] = int(''.join(c for c in s_str if c.isdigit()))
            
            for name, t in teams.items():
                if name in seeds_by_name:
                    t.seed = seeds_by_name[name]
        except Exception:
            pass # Fallback to CSV seeds

        # Convert to serializable dict
        teams_list = []
        for name, t in teams.items():
            teams_list.append({
                "name": name,
                "seed": t.seed,
                "momentum": t.momentum,
                "sos": getattr(t, 'sos', 0),
                "to_pct": getattr(t, 'to_pct', 0),
                "off_efficiency": t.off_efficiency,
                "def_efficiency": t.def_efficiency,
                "trb_pct": t.trb_pct,
                "off_ft_pct": getattr(t, 'off_ft_pct', 0),
                "def_ft_pct": getattr(t, 'def_ft_pct', 0),
                "archetype": t.archetype,
                "intuition_score": t.intuition_factor
            })
        return jsonify(teams_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/weights/optimal')
def get_optimal_weights():
    return jsonify({
        "trb": DEFAULT_WEIGHTS.trb_weight,
        "to": DEFAULT_WEIGHTS.to_weight,
        "sos": DEFAULT_WEIGHTS.sos_weight,
        "momentum": DEFAULT_WEIGHTS.momentum_weight,
        "efficiency": DEFAULT_WEIGHTS.efficiency_weight,
        "ft": DEFAULT_WEIGHTS.ft_weight,
        "def_premium": DEFAULT_WEIGHTS.defense_premium,
        "orb_density": DEFAULT_WEIGHTS.orb_density_weight,
        "luck_regression": DEFAULT_WEIGHTS.luck_regression_weight,
        "coach_moxie": DEFAULT_WEIGHTS.coach_tournament_weight,
        "tempo_upset": DEFAULT_WEIGHTS.tempo_upset_weight,
        "fatigue": DEFAULT_WEIGHTS.fatigue_sensitivity,
        "bench": DEFAULT_WEIGHTS.bench_rest_bonus
    })

@app.route('/api/weights/preset')
def get_preset_weights():
    """
    Returns the optimizer-tuned weight set for a given mode.
    mode=avg      -> MAX_AVG_WEIGHTS (highest average ESPN score)
    mode=champion -> MAX_CHAMPION_WEIGHTS (highest perfect-bracket / champion accuracy)
    Falls back to DEFAULT_WEIGHTS if gold_standard.json doesn't exist yet.
    """
    import json as _json
    mode = request.args.get('mode', 'avg')  # 'avg' or 'champion'
    gold_path = Path("agents/optimization/gold_standard.json")

    if gold_path.exists():
        try:
            with open(gold_path) as f:
                gold = _json.load(f)
            key = "max_avg" if mode == "avg" else "max_champion"
            weights_dict = gold[key]["weights"]
            meta = gold[key].get("meta", {})
            return jsonify({"mode": mode, "meta": meta, "weights": weights_dict})
        except Exception as e:
            pass  # Fall through to default

    # Fallback: return DEFAULT_WEIGHTS as a flat dict
    import dataclasses as _dc
    return jsonify({
        "mode": mode,
        "meta": {"note": "gold_standard.json not yet generated — using defaults"},
        "weights": _dc.asdict(DEFAULT_WEIGHTS)
    })


@app.route('/api/bracket/<int:year>', methods=['GET'])
def get_bracket(year):
    try:
        base_dir = Path(f"years/{year}/data")
        bracket_data = load_bracket(base_dir / "chalk_bracket.json")
        SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
        
        bracket_res = {"regions": {}}
        for region_name, seeds_map in bracket_data.get("regions", {}).items():
            matchups = []
            for high_seed, low_seed in SEED_MATCHUPS:
                ht_name = seeds_map.get(str(high_seed))
                lt_name = seeds_map.get(str(low_seed))
                matchups.append({
                    "team_a": ht_name, "seed_a": high_seed,
                    "team_b": lt_name, "seed_b": low_seed
                })
            bracket_res["regions"][region_name] = matchups
            
        return jsonify(bracket_res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/simulate/matchup', methods=['POST'])
def simulate_matchup():
    data = request.json
    year = data.get('year', 2026)
    team_a_name = data.get('team_a')
    team_b_name = data.get('team_b')
    weights_data = data.get('weights', {})
    
    try:
        base_dir = Path(f"years/{year}/data")
        teams = load_teams(base_dir / "team_stats.csv", year=year)
        team_a = teams.get(team_a_name)
        team_b = teams.get(team_b_name)
        
        if not team_a or not team_b:
            return jsonify({"error": "Team not found"}), 404
            
        custom_weights = extract_weights(weights_data)
        engine = SimulatorEngine(teams=teams, weights=custom_weights)
        prob_a = engine.calculate_win_probability(team_a, team_b)
            
        # Debug UCLA/UCF specifically
        if (team_a.name == "UCLA" and team_b.name == "UCF") or (team_b.name == "UCLA" and team_a.name == "UCF"):
            import logging
            logging.info(f"MATCHUP DEBUG: {team_a.name} ({team_a.seed}) vs {team_b.name} ({team_b.seed})")
            # Pythagorean expectation is not a direct attribute, calculate or use efficiency
            # For now, using off_efficiency and def_efficiency as proxies for "Eff"
            logging.info(f"  Off Eff A: {team_a.off_efficiency:.4f}, Def Eff A: {team_a.def_efficiency:.4f}")
            logging.info(f"  Off Eff B: {team_b.off_efficiency:.4f}, Def Eff B: {team_b.def_efficiency:.4f}")
            logging.info(f"  SOS A: {team_a.sos}, SOS B: {team_b.sos}")
            logging.info(f"  Result Prob A: {prob_a:.4f}")
        winner = team_a if prob_a >= 0.5 else team_b
        
        return jsonify({
            "winner": winner.name,
            "probability": prob_a,
            "team_a": team_a_name,
            "team_b": team_b_name 
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/matchup/detail', methods=['GET', 'POST'])
def get_matchup_detail():
    if request.method == 'POST':
        data = request.json or {}
    else:
        # Robustly collect all GET params
        data = request.args.to_dict()
        if 'year' in data: data['year'] = int(data['year'])
        
    year = data.get('year', 2026)
    team_a_name = data.get('team_a')
    team_b_name = data.get('team_b')
    weights_data = data.get('weights', data)

    try:
        base_dir = Path(f"years/{year}/data")
        teams = load_teams(base_dir / "team_stats.csv", year=year)
        
        # Synchronize seeds from bracket
        bracket = load_bracket(base_dir / "chalk_bracket.json")
        seeds_by_name = {}
        for reg_name, seeds in bracket.get("regions", {}).items():
            for s_str, name in seeds.items():
                seeds_by_name[name] = int(''.join(c for c in s_str if c.isdigit()))

        t_a = teams.get(team_a_name)
        t_b = teams.get(team_b_name)
        
        if t_a and t_a.name in seeds_by_name:
            t_a.seed = seeds_by_name[t_a.name]
        if t_b and t_b.name in seeds_by_name:
            t_b.seed = seeds_by_name[t_b.name]
        
        if not t_a or not t_b:
            return jsonify({"error": "Team not found"}), 404
            
        custom_weights = extract_weights(weights_data)
        engine = SimulatorEngine(teams=teams, weights=custom_weights)
        prob_a = engine.calculate_win_probability(t_a, t_b)
        # Generate dynamic "Why" analysis
        analysis = []
        
        # SOS Check
        sos_diff = (t_a.sos or 0) - (t_b.sos or 0)
        if abs(sos_diff) > 2.0:
            analysis.append({
                "factor": "Strength of Schedule",
                "importance": "High",
                "description": f"{t_a.name if sos_diff > 0 else t_b.name} has been battle-tested against a tougher schedule (+{abs(sos_diff):.1f} SOS)."
            })
            
        # Overall Efficiency Check
        eff_a = (t_a.off_efficiency or 100) - (t_a.def_efficiency or 100)
        eff_b = (t_b.off_efficiency or 100) - (t_b.def_efficiency or 100)
        eff_diff = eff_a - eff_b
        if abs(eff_diff) > 5.0:
            analysis.append({
                "factor": "Efficiency Margin",
                "importance": "Critical",
                "description": f"{t_a.name if eff_diff > 0 else t_b.name} owns a major analytical advantage in overall net efficiency."
            })

        # Free Throw Factor
        ft_a_val = (t_a.off_ft_pct or 70) - (t_b.def_ft_pct or 70)
        ft_b_val = (t_b.off_ft_pct or 70) - (t_a.def_ft_pct or 70)
        ft_diff = ft_a_val - ft_b_val
        if abs(ft_diff) > 4.0:
            analysis.append({
                "factor": "Free Throw Advantage",
                "importance": "Situational",
                "description": f"{t_a.name if ft_diff > 0 else t_b.name} is significantly more effective at the charity stripe."
            })

        # 2025 Specific Indicators
        # Luck
        luck_a = getattr(t_a, 'luck', 0.0) or 0.0
        luck_b = getattr(t_b, 'luck', 0.0) or 0.0
        if abs(luck_a) > 0.05 or abs(luck_b) > 0.05:
            # If luck_b > luck_a, t_b is overachieving
            analysis.append({
                "factor": "Luck Regression",
                "importance": "Medium",
                "description": f"{t_b.name if luck_b > luck_a else t_a.name} has consistently overachieved their analytical profile; they are statistically 'due' for regression."
            })

        # Aggressiveness (Continuation Rule Proxy)
        ftr_a = t_a.off_ft_rate or 0.0
        ftr_b = t_b.off_ft_rate or 0.0
        if ftr_a > 0.38 or ftr_b > 0.38:
            analysis.append({
                "factor": "Aggression Index",
                "importance": "High",
                "description": f"{t_a.name if ftr_a > ftr_b else t_b.name}'s ability to draw fouls aligns perfectly with the {year} 'Continuation' emphasis."
            })

        # Star Reliance
        star_a = getattr(t_a, 'star_reliance', 0.5)
        star_b = getattr(t_b, 'star_reliance', 0.5)
        if abs(star_a - star_b) > 0.15:
            analysis.append({
                "factor": "Roster Depth",
                "importance": "Medium",
                "description": f"{t_a.name if star_a < star_b else t_b.name} has a more balanced scoring attack, making them harder to scout and shut down than the star-dependent {t_b.name if star_a < star_b else t_a.name}."
            })

        # ORB Density
        orb_a = t_a.off_orb_pct or 25.0
        orb_b = t_b.off_orb_pct or 25.0
        if orb_a > 33.0 or orb_b > 33.0:
            analysis.append({
                "factor": "ORB Density",
                "importance": "High",
                "description": f"{t_a.name if orb_a > orb_b else t_b.name} is a glass-crashing juggernaut, generating critical second-chance opportunities."
            })

        return jsonify({
            "team_a": {
                "name": t_a.name, "seed": t_a.seed,
                "off_eff": t_a.off_efficiency, "def_eff": t_a.def_efficiency,
                "sos": t_a.sos, "trb": t_a.trb_pct, "mom": t_a.momentum, "ft": t_a.off_ft_pct,
                "luck": luck_a, "star_reliance": star_a, "orb_pct": orb_a, "ft_rate": ftr_a,
                "archetype": t_a.archetype
            },
            "team_b": {
                "name": t_b.name, "seed": t_b.seed,
                "off_eff": t_b.off_efficiency, "def_eff": t_b.def_efficiency,
                "sos": t_b.sos, "trb": t_b.trb_pct, "mom": t_b.momentum, "ft": t_b.off_ft_pct,
                "luck": luck_b, "star_reliance": star_b, "orb_pct": orb_b, "ft_rate": ftr_b,
                "archetype": t_b.archetype
            },
            "probability": prob_a,
            "analysis": analysis
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/simulation/full', methods=['GET', 'POST'])
def run_full_sim():
    if request.method == 'POST':
        data = request.json or {}
        year = data.get('year', 2026)
        mode = data.get('mode', 'deterministic')
        weights_data = data.get('weights', {})
        locks = data.get('locks', {})
        volatility = data.get('volatility', 0.0)
        
        custom_weights = extract_weights(weights_data)
    else:
        year = request.args.get('year', default=2026, type=int)
        mode = request.args.get('mode', default='deterministic')
        locks = {}
        
        # Parse weights from query params (e.g., ?sos=7.5&trb=4.2)
        custom_weights = extract_weights(request.args)
    
    SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
    
    try:
        base_dir = Path(f"years/{year}/data")
        teams_data = load_teams(base_dir / "team_stats.csv", year=year)
        bracket_data = load_bracket(base_dir / "chalk_bracket.json")
        
        # Load actual results if they exist (for historical years)
        results_path = base_dir / "actual_results.json"
        actual_results = {}
        if results_path.exists():
            import json
            with open(results_path, 'r') as f:
                actual_results = json.load(f)

        engine = SimulatorEngine(teams=teams_data, weights=custom_weights)
        engine.volatility = volatility # Inject volatility
        
        sim_trace = {
            "regions": {},
            "final_four": [],
            "championship": None,
            "winner": None
        }
        
        # Collect regional winners by name for explicit pairing
        winners_by_region = {}
        regions_ordered = ['East', 'South', 'West', 'Midwest'] # Match main.js order
        
        for region_name in regions_ordered:
            if region_name not in bracket_data.get("regions", {}):
                continue
            
            seeds_map = bracket_data["regions"][region_name]
            region_trace = []
            current_round_teams = []
            
            # Round 1 Setup
            for high_seed, low_seed in SEED_MATCHUPS:
                def get_team_from_seed(seed_str):
                    if seed_str in seeds_map: return seeds_map[seed_str]
                    if f"{seed_str}a" in seeds_map: return seeds_map[f"{seed_str}a"]
                    if f"{seed_str}b" in seeds_map: return seeds_map[f"{seed_str}b"]
                    return None

                ht_name = get_team_from_seed(str(high_seed))
                lt_name = get_team_from_seed(str(low_seed))
                
                ht = teams_data.get(ht_name)
                lt = teams_data.get(lt_name)
                
                if not ht:
                    ht = Team(name=ht_name or f"TBD ({high_seed})", seed=int(high_seed), off_efficiency=100.0, def_efficiency=100.0, off_ppg=70.0, def_ppg=70.0)
                else: ht.seed = int(high_seed)
                
                if not lt:
                    lt = Team(name=lt_name or f"TBD ({low_seed})", seed=int(low_seed), off_efficiency=100.0, def_efficiency=100.0, off_ppg=70.0, def_ppg=70.0)
                else: lt.seed = int(low_seed)

                current_round_teams.extend([ht, lt])

            round_names = {1: "round_of_32", 2: "sweet_sixteen", 3: "elite_eight", 4: "final_four"}
            round_idx = 1
            while len(current_round_teams) > 1:
                next_round = []
                matchups = []
                region_locks = locks.get('regions', {}).get(region_name, {}).get(str(round_idx), {})
                historical_winners = actual_results.get(round_names.get(round_idx, ""), [])

                for i in range(0, len(current_round_teams) - 1, 2):
                    t_a = current_round_teams[i]
                    t_b = current_round_teams[i+1]
                    prob_a = engine.calculate_win_probability(t_a, t_b)
                    
                    # LOGGING ANOMALY DEBUG
                    if (t_a.name == "UCLA" and t_b.name == "UCF") or (t_b.name == "UCLA" and t_a.name == "UCF"):
                        import logging
                        logging.info(f"MATCHUP DEBUG: {t_a.name} ({t_a.seed}) vs {t_b.name} ({t_b.seed})")
                        logging.info(f"  Eff A: {t_a.pythagorean_expectation:.4f}, Eff B: {t_b.pythagorean_expectation:.4f}")
                        logging.info(f"  SOS A: {t_a.sos}, SOS B: {t_b.sos}")
                        logging.info(f"  TO A: {t_a.off_to_pct}, TO B: {t_b.off_to_pct}")
                        logging.info(f"  Result Prob A: {prob_a:.4f}")
                    
                    if t_a.name in historical_winners: winner = t_a
                    elif t_b.name in historical_winners: winner = t_b
                    elif t_a.name in region_locks: winner = t_a
                    elif t_b.name in region_locks: winner = t_b
                    else: winner = engine.simulate_game(t_a, t_b, mode=mode)
                        
                    next_round.append(winner)
                    matchups.append({"team_a": t_a.name, "seed_a": t_a.seed, "team_b": t_b.name, "seed_b": t_b.seed, "winner": winner.name, "probability": prob_a})
                
                region_trace.append({"round": round_idx, "matchups": matchups})
                current_round_teams = next_round
                round_idx += 1
                
            sim_trace["regions"][region_name] = region_trace
            winners_by_region[region_name] = current_round_teams[0] if current_round_teams else None

        # Final Four (Explicit Pairings)
        # Semi 1: East vs South
        e_win = winners_by_region.get('East')
        s_win = winners_by_region.get('South')
        # Semi 2: West vs Midwest
        w_win = winners_by_region.get('West')
        m_win = winners_by_region.get('Midwest')
        
        # Fallback for missing regions
        dummy_team = list(teams_data.values())[0]
        e_win = e_win or dummy_team
        s_win = s_win or dummy_team
        w_win = w_win or dummy_team
        m_win = m_win or dummy_team

        ff_winners = actual_results.get("final_four", [])
        champ_winner = actual_results.get("champion")
        ff_locks = locks.get('final_four', {})

        # Semi 1 Simulation
        if e_win.name in ff_winners: ff_1 = e_win
        elif s_win.name in ff_winners: ff_1 = s_win
        elif e_win.name in ff_locks: ff_1 = e_win
        elif s_win.name in ff_locks: ff_1 = s_win
        else: ff_1 = engine.simulate_game(e_win, s_win, mode=mode)

        # Semi 2 Simulation
        if w_win.name in ff_winners: ff_2 = w_win
        elif m_win.name in ff_winners: ff_2 = m_win
        elif w_win.name in ff_locks: ff_2 = w_win
        elif m_win.name in ff_locks: ff_2 = m_win
        else: ff_2 = engine.simulate_game(w_win, m_win, mode=mode)
        
        sim_trace["final_four"] = [
            {"team_a": e_win.name, "seed_a": e_win.seed, "team_b": s_win.name, "seed_b": s_win.seed, "winner": ff_1.name},
            {"team_a": w_win.name, "seed_a": w_win.seed, "team_b": m_win.name, "seed_b": m_win.seed, "winner": ff_2.name}
        ]
        
        # Championship
        champ_locks = locks.get('championship', {})
        if ff_1.name == champ_winner: champ = ff_1
        elif ff_2.name == champ_winner: champ = ff_2
        elif ff_1.name in champ_locks: champ = ff_1
        elif ff_2.name in champ_locks: champ = ff_2
        else: champ = engine.simulate_game(ff_1, ff_2, mode=mode)
            
        sim_trace["championship"] = {"team_a": ff_1.name, "seed_a": ff_1.seed, "team_b": ff_2.name, "seed_b": ff_2.seed, "winner": champ.name}
        sim_trace["winner"] = champ.name
        
        return jsonify(sim_trace)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
