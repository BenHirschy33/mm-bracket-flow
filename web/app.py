import sys
import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Ensure core and years modules are importable
sys.path.append(os.getcwd())

from core.parser import load_teams, load_bracket
from core.simulator import SimulatorEngine
from core.config import DEFAULT_WEIGHTS

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

@app.route('/api/simulate/matchup', methods=['POST'])
def simulate_matchup():
    data = request.json
    year = data.get('year', 2026)
    team_a_name = data.get('team_a')
    team_b_name = data.get('team_b')
    
    try:
        base_dir = Path(f"years/{year}/data")
        teams = load_teams(base_dir / "team_stats.csv", year=year)
        team_a = teams.get(team_a_name)
        team_b = teams.get(team_b_name)
        
        if not team_a or not team_b:
            return jsonify({"error": "Team not found"}), 404
            
        engine = SimulatorEngine()
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

@app.route('/api/simulation/full', methods=['GET'])
def run_full_sim():
    year = request.args.get('year', default=2026, type=int)
    mode = request.args.get('mode', default='deterministic')
    
    SEED_MATCHUPS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
    
    try:
        base_dir = Path(f"years/{year}/data")
        teams_data = load_teams(base_dir / "team_stats.csv", year=year)
        bracket_data = load_bracket(base_dir / "chalk_bracket.json")
        engine = SimulatorEngine()
        
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
                ht = teams_data.get(seeds_map.get(str(high_seed)))
                lt = teams_data.get(seeds_map.get(str(low_seed)))
                if ht and lt:
                    current_round_teams.extend([ht, lt])
            
            round_idx = 1
            while len(current_round_teams) > 1:
                next_round = []
                matchups = []
                for i in range(0, len(current_round_teams), 2):
                    t_a = current_round_teams[i]
                    t_b = current_round_teams[i+1]
                    prob_a = engine.calculate_win_probability(t_a, t_b)
                    
                    winner = engine.simulate_game(t_a, t_b, mode=mode)
                    next_round.append(winner)
                    
                    matchups.append({
                        "team_a": t_a.name, "seed_a": t_a.seed,
                        "team_b": t_b.name, "seed_b": t_b.seed,
                        "winner": winner.name,
                        "probability": prob_a
                    })
                
                region_trace.append({"round": round_idx, "matchups": matchups})
                current_round_teams = next_round
                round_idx += 1
                
            sim_trace["regions"][region_name] = region_trace
            if current_round_teams:
                final_four_field.append(current_round_teams[0])
                
        # Final Four
        ff_1 = engine.simulate_game(final_four_field[0], final_four_field[1], mode=mode)
        ff_2 = engine.simulate_game(final_four_field[2], final_four_field[3], mode=mode)
        
        sim_trace["final_four"] = [
            {"team_a": final_four_field[0].name, "team_b": final_four_field[1].name, "winner": ff_1.name},
            {"team_a": final_four_field[2].name, "team_b": final_four_field[3].name, "winner": ff_2.name}
        ]
        
        champ = engine.simulate_game(ff_1, ff_2, mode=mode)
        sim_trace["championship"] = {"team_a": ff_1.name, "team_b": ff_2.name, "winner": champ.name}
        sim_trace["winner"] = champ.name
        
        return jsonify(sim_trace)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
