import sys
import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Ensure core and years modules are importable
sys.path.append(os.getcwd())

from core.parser import load_teams, load_bracket
from core.simulator import SimulatorEngine
from core.config import DEFAULT_WEIGHTS, SimulationWeights

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/teams/<int:year>')
def get_teams(year):
    try:
        base_dir = Path(f"years/{year}/data")
        teams = load_teams(base_dir / "team_stats.csv", year=year)
        # Convert to serializable dict
        teams_list = []
        for name, t in teams.items():
            teams_list.append({
                "name": name,
                "seed": t.seed,
                "off_efficiency": t.off_efficiency,
                "def_efficiency": t.def_efficiency,
                "trb_pct": t.trb_pct,
                "intuition_score": t.intuition_score,
                "momentum": t.momentum
            })
        return jsonify(teams_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
            
        custom_weights = SimulationWeights(
            trb_weight=float(weights_data.get('trb', 4.895)),
            to_weight=float(weights_data.get('to', 2.846)),
            sos_weight=float(weights_data.get('sos', 7.635)),
            momentum_weight=float(weights_data.get('momentum', 0.073)),
            efficiency_weight=float(weights_data.get('efficiency', 0.022))
        )
        engine = SimulatorEngine(weights=custom_weights)
        prob_a = engine.calculate_win_probability(team_a, team_b)
        winner = team_a if prob_a >= 0.5 else team_b
        
        return jsonify({
            "winner": winner.name,
            "probability": prob_a,
            "team_a": team_a_name,
            "team_b": team_b_name 
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
        
        custom_weights = SimulationWeights(
            trb_weight=float(weights_data.get('trb', 4.895)),
            to_weight=float(weights_data.get('to', 2.846)),
            sos_weight=float(weights_data.get('sos', 7.635)),
            momentum_weight=float(weights_data.get('momentum', 0.073)),
            efficiency_weight=float(weights_data.get('efficiency', 0.022))
        )
    else:
        year = request.args.get('year', default=2026, type=int)
        mode = request.args.get('mode', default='deterministic')
        locks = {}
        
        # Parse weights from query params (e.g., ?sos=7.5&trb=4.2)
        custom_weights = SimulationWeights(
            trb_weight=request.args.get('trb', default=4.895, type=float),
            to_weight=request.args.get('to', default=2.846, type=float),
            sos_weight=request.args.get('sos', default=7.635, type=float),
            momentum_weight=request.args.get('momentum', default=0.073, type=float),
            efficiency_weight=request.args.get('efficiency', default=0.022, type=float)
        )
    
    SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
    
    try:
        base_dir = Path(f"years/{year}/data")
        teams_data = load_teams(base_dir / "team_stats.csv", year=year)
        bracket_data = load_bracket(base_dir / "chalk_bracket.json")
        engine = SimulatorEngine(weights=custom_weights)
        
        sim_trace = {
            "regions": {},
            "final_four": [],
            "championship": None,
            "winner": None
        }
        
        final_four_field = []
        
        for region_name, seeds_map in bracket_data.get("regions", {}).items():
            region_trace = []
            current_round_teams = []
            
            # Round 1 Setup
            for high_seed, low_seed in SEED_MATCHUPS:
                ht_name = seeds_map.get(str(high_seed))
                lt_name = seeds_map.get(str(low_seed))
                
                ht = teams_data.get(ht_name)
                lt = teams_data.get(lt_name)
                
                if ht and lt:
                    # Injected seeds for teams that are found in the bracket config
                    ht.seed = int(high_seed)
                    lt.seed = int(low_seed)
                    current_round_teams.extend([ht, lt])
                elif ht:
                    ht.seed = int(high_seed)
                    current_round_teams.append(ht)
                elif lt:
                    lt.seed = int(low_seed)
                    current_round_teams.append(lt)
            
            if not current_round_teams:
                continue

            round_idx = 1
            while len(current_round_teams) > 1:
                next_round = []
                matchups = []
                region_locks = locks.get('regions', {}).get(region_name, {}).get(str(round_idx), {})
                # Ensure we handle odd numbers (though tournament brackets shouldn't have them)
                for i in range(0, len(current_round_teams) - 1, 2):
                    t_a = current_round_teams[i]
                    t_b = current_round_teams[i+1]
                    prob_a = engine.calculate_win_probability(t_a, t_b)
                    
                    if t_a.name in region_locks:
                        winner = t_a
                    elif t_b.name in region_locks:
                        winner = t_b
                    else:
                        winner = engine.simulate_game(t_a, t_b, mode=mode)
                        
                    next_round.append(winner)
                    
                    matchups.append({
                        "team_a": t_a.name, "seed_a": t_a.seed,
                        "team_b": t_b.name, "seed_b": t_b.seed,
                        "winner": winner.name,
                        "probability": prob_a
                    })
                
                # If odd team remains, they get a bye
                if len(current_round_teams) % 2 != 0:
                    next_round.append(current_round_teams[-1])

                region_trace.append({"round": round_idx, "matchups": matchups})
                current_round_teams = next_round
                round_idx += 1
                
            sim_trace["regions"][region_name] = region_trace
            if current_round_teams:
                final_four_field.append(current_round_teams[0])
                
        # Final Four (Safe Check)
        if len(final_four_field) < 4:
            # Pad with empty teams if regions failed
            while len(final_four_field) < 4:
                final_four_field.append(list(teams_data.values())[0])

        ff_locks = locks.get('final_four', {})
        if final_four_field[0].name in ff_locks:
            ff_1 = final_four_field[0]
        elif final_four_field[1].name in ff_locks:
            ff_1 = final_four_field[1]
        else:
            ff_1 = engine.simulate_game(final_four_field[0], final_four_field[1], mode=mode)
            
        if final_four_field[2].name in ff_locks:
            ff_2 = final_four_field[2]
        elif final_four_field[3].name in ff_locks:
            ff_2 = final_four_field[3]
        else:
            ff_2 = engine.simulate_game(final_four_field[2], final_four_field[3], mode=mode)
        
        sim_trace["final_four"] = [
            {"team_a": final_four_field[0].name, "team_b": final_four_field[1].name, "winner": ff_1.name},
            {"team_a": final_four_field[2].name, "team_b": final_four_field[3].name, "winner": ff_2.name}
        ]
        
        champ_locks = locks.get('championship', {})
        if ff_1.name in champ_locks:
            champ = ff_1
        elif ff_2.name in champ_locks:
            champ = ff_2
        else:
            champ = engine.simulate_game(ff_1, ff_2, mode=mode)
            
        sim_trace["championship"] = {"team_a": ff_1.name, "team_b": ff_2.name, "winner": champ.name}
        sim_trace["winner"] = champ.name
        
        return jsonify(sim_trace)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
