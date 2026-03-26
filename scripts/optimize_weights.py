import argparse
import sys
import math
import random
import logging
import json
import dataclasses
import numpy as np
import os
import time
import signal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import SimulationWeights
from scripts.evaluate_weights import evaluate_bracket

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Full historical window (2015-2025, excluding 2020)
YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]

# EXPERT-GUIDED PERSONALITIES (Rigid Configurations)
MODE_CONFIGS = {
    "average": {
        "total_iterations": 100000,
        "sample_count": 150,
        "snapback_interval": 15000,
        "heartbeat": 1000
    },
    "balanced": {
        "total_iterations": 250000,
        "sample_count": 750,
        "snapback_interval": 25000,
        "heartbeat": 250
    },
    "perfect": {
        "total_iterations": 500000,
        "sample_count": 2500,
        "snapback_interval": 50000,
        "heartbeat": 100
    }
}

class StateManager:
    """Manages serialization of optimization state to prevent loss on interrupt."""
    def __init__(self, mode: str):
        self.mode = mode
        self.path = Path(f"agents/optimization/checkpoint_{mode}.json")
        self.pid = os.getpid()

    def save(self, current_weights, best_weights, temp, iterations, best_metrics):
        state = {
            "pid": self.pid,
            "mode": self.mode,
            "current_weights": dataclasses.asdict(current_weights),
            "best_weights": dataclasses.asdict(best_weights),
            "temperature": temp,
            "total_iterations_run": iterations,
            "best_fitness": best_metrics.get("sa_fitness"),
            "best_espn_avg": best_metrics.get("espn_average"),
            "best_espn_max": best_metrics.get("espn_max"),
            "best_accuracy": best_metrics.get("accuracy"),
            "timestamp": time.time()
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic Write (Phase 112: PID Isolation)
        temp_path = self.path.with_suffix(f".tmp.{os.getpid()}")
        with open(temp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_path, self.path)

    def load(self):
        if not self.path.exists():
            return None
        with open(self.path, "r") as f:
            return json.load(f)

    def check_stale_process(self):
        state = self.load()
        if state and "pid" in state:
            old_pid = state["pid"]
            if old_pid != self.pid:
                try:
                    os.kill(old_pid, 0)
                    # Attempt to kill if stale (Phase 41)
                    logging.warning(f"⚠️ [{self.mode.upper()}] Stale process {old_pid} found. Evicting...")
                    os.kill(old_pid, signal.SIGTERM)
                    time.sleep(1)
                    return False # Successfully evicted
                except OSError:
                    pass
        return False

    def cleanup(self):
        if self.path.exists():
            try:
                self.path.unlink()
            except:
                pass

def get_multi_year_results(weights: SimulationWeights, years_list, iterations=100, **kwargs):
    """Calculates metrics across years LINEARLY for maximum stability and cooler CPU."""
    results = []
    for year in years_list:
        try:
            # High-precision: internal Monte Carlo runs per year
            metrics = evaluate_bracket(year, weights, iterations)
            if metrics["avg_score"] >= 0:
                metrics["year"] = year
                results.append(metrics)
        except Exception as e:
            logging.error(f"Year {year} failed: {e}")
    return results

def recency_weight(year):
    return 0.5 + 0.5 * ((year - 2015) / (2025 - 2015))

def cross_validate_weights(weights: SimulationWeights, mode: str = "balanced", samples: int = 100):
    """
    Performs Weighted Log-Likelihood fitness calculation (Linear).
    """
    results = get_multi_year_results(weights, YEARS, iterations=samples)
    if not results:
        # Default failure return with Shadow Scoring format
        return {
            "sa_fitness": -100000.0,
            "espn_average": 0.0,
            "espn_max": 0.0,
            "accuracy": 0.0
        }
    
    weighted_ll = np.sum([r.get("log_likelihood", -500.0) * recency_weight(r["year"]) for r in results])
    
    avg_score = np.mean([r["avg_score"] for r in results])
    avg_accuracy = np.mean([r["champion_accuracy"] for r in results])
    perfect_rate = np.mean([r["perfect_rate"] for r in results])
    avg_peak = np.mean([r.get("peak_score", 0.0) for r in results])
    
    if mode == "perfect":
        # CONVEX POWER-LAW TAIL OPTIMIZATION (Phase 64: Scientific Assessment V2)
        # We aggregate the top 1% performers across all years and apply a power-law exponent.
        # This creates an aggressive 'gravity well' for extreme high-scorers (1800+).
        all_top_scores = [s for r in results for s in r.get("top_scores", [])]
        if all_top_scores:
            # Normalize to 1920 scale and apply exponent (Gamma = 8)
            # A 90% bracket (1728) is ~110x more valuable than a 50% bracket (960).
            convex_tail_reward = np.mean([(s / 1920.0)**8 for s in all_top_scores]) * 1000000
        else:
            convex_tail_reward = (avg_peak / 1920.0)**8 * 1000000
            
        tripwire = 100000 if perfect_rate > 0 else 0
        fitness = (weighted_ll * 1.0) + convex_tail_reward + tripwire + (avg_accuracy * 5000)
    elif mode == "average":
        # V5.6: Cubic Power-Law for Elite Average Maximization
        # There is NO cap at 1000. We prioritize high-average upside exponentially.
        fitness = (avg_score ** 3) / 1000000.0 + (weighted_ll * 0.1)
    else: # "balanced"
        fitness = weighted_ll + (avg_score * 0.5) + (perfect_rate * 10000)
    
    return {
        "sa_fitness": fitness,
        "espn_average": avg_score,
        "espn_max": avg_peak,
        "accuracy": avg_accuracy
    }

def print_progress(mode, label, i, iterations, start_iter, start_time, fitness, avg, peak):
    """Unified progress formatter for heartbeats and new bests."""
    percent = ((i + 1) / max(1, iterations)) * 100
    elapsed = time.time() - start_time
    iter_rate = (i - start_iter + 1) / max(0.1, elapsed)
    eta_seconds = (iterations - i) / max(0.01, iter_rate)
    h_eta = int(eta_seconds // 3600); m_eta = int((eta_seconds % 3600) // 60)
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{mode.upper()}] [{i+1}/{iterations}] ({percent:.1f}%) ETA: {h_eta}h {m_eta}m | {label} | Fit: {fitness:.2f} | Avg: {avg:.2f} | Max: {peak:.2f}", flush=True)

def optimize_simulated_annealing(mode="balanced", jitter_scale=1.0, iterations=None, load_state=None, resume=False, restart=False):
    """
    Resumable State Machine Optimizer V5 (Hardcoded Profiles).
    """
    config = MODE_CONFIGS.get(mode)
    if not config:
        logging.error(f"❌ [CRITICAL] Unknown mode: {mode}")
        return

    if iterations is None:
        iterations = config["total_iterations"]
    samples = config["sample_count"]
    snapback_interval = config["snapback_interval"]
    heartbeat_interval = config["heartbeat"]

    start_time = time.time()
    state_mgr = StateManager(mode)
    
    # Check for stale process
    if restart and state_mgr.check_stale_process():
        logging.error(f"⚠️ [ABORT] Stale process detected for mode {mode}. Close it first!")
        return
          # 1. INITIAL HYDRATION (Gold Standard Baseline)
    gold_path = Path("agents/optimization/gold_standard.json")
    gold_weights = SimulationWeights()
    gold_fitness = -1e9
    gold_res = None
    
    if gold_path.exists():
        try:
            with open(gold_path, 'r') as f:
                gold_data = json.load(f)
                ui_key = {"balanced": "max_balanced", "perfect": "max_perfect", "average": "max_avg"}.get(mode)
                if ui_key in gold_data and "weights" in gold_data[ui_key]:
                    gold_weights = SimulationWeights(**gold_data[ui_key]["weights"])
                    print(f"🔍 [{mode.upper()}] Validating Gold Standard baseline...", flush=True)
                    gold_res = cross_validate_weights(gold_weights, mode=mode, samples=samples)
                    gold_fitness = gold_res["sa_fitness"]
                    print(f"🏆 [{mode.upper()}] Gold Standard Baseline: {gold_fitness:.2f}", flush=True)
        except Exception as e:
            logging.error(f"Gold load/validation failed: {e}")

    # 2. CHECKPOINT HYDRATION (Last Session State)
    checkpoint = state_mgr.load() if (resume and not restart) else None
    chk_weights = None
    chk_fitness = -1e9
    chk_res = None
    
    if checkpoint:
        try:
            chk_weights = SimulationWeights(**checkpoint["best_weights"])
            print(f"🔍 [{mode.upper()}] Validating Checkpoint session...", flush=True)
            chk_res = cross_validate_weights(chk_weights, mode=mode, samples=samples)
            chk_fitness = chk_res["sa_fitness"]
            print(f"🦾 [{mode.upper()}] Checkpoint Record: {chk_fitness:.2f}", flush=True)
        except Exception as e:
            logging.error(f"Checkpoint validation failed: {e}")

    # 3. THE DOUBLE-HYDRATION CONTEST (Winner becomes Start State)
    if chk_weights and chk_fitness > gold_fitness:
        print(f"🔥 [{mode.upper()}] Checkpoint wins the contest. Resuming from Iter {checkpoint['total_iterations_run']}", flush=True)
        best_weights = chk_weights
        best_fitness = chk_fitness
        best_avg = chk_res["espn_average"]
        best_max = chk_res["espn_max"]
        best_acc = chk_res["accuracy"]
        start_iter = checkpoint["total_iterations_run"]
        temp_sa = checkpoint["temperature"] * 1.25 # Thermal Re-heat
    else:
        winner_source = "Gold Standard" if gold_fitness > -1e9 else "Default"
        print(f"⭐ [{mode.upper()}] {winner_source} wins the contest. Starting Fresh @ Peak.", flush=True)
        best_weights = gold_weights
        best_fitness = gold_fitness
        if gold_res:
            best_avg = gold_res["espn_average"]
            best_max = gold_res["espn_max"]
            best_acc = gold_res["accuracy"]
        else:
            # Fallback for default weights
            init_res = cross_validate_weights(best_weights, mode=mode, samples=samples)
            best_avg = init_res["espn_average"]
            best_max = init_res["espn_max"]
            best_acc = init_res["accuracy"]
            best_fitness = init_res["sa_fitness"]
        
        start_iter = checkpoint["total_iterations_run"] if checkpoint else 0
        temp_sa = checkpoint["temperature"] * 1.25 if checkpoint else 1.0

    current_weights = best_weights
    current_fitness = best_fitness
    current_avg = best_avg
    current_acc = best_acc
    current_max = best_max
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    start_type = f"RESUMING FROM I: {start_iter}" if checkpoint else "FRESH START"
    focus_map = {
        "perfect": ("🎯 FOCUS: PERFECT BRACKETS (Convex Power-Law Tail / EVT V2)", 1000000),
        "balanced": ("⚖️ FOCUS: BALANCED (Linear Accuracy Reward)", 10000),
        "average": ("📈 FOCUS: AVERAGE SCORE (3.0x Consistency Focus)", 0)
    }
    focus_str, acc_reward = focus_map.get(mode, ("UNKNOWN FOCUS", 0))
    eff_jitter = jitter_scale * (2.0 if mode == "perfect" else 1.0)
    
    label = "Tail Multiplier" if mode == "perfect" else "Acc Reward"
    
    print(f"\n[{timestamp}] 🚀 {start_type}: {focus_str}", flush=True)
    print(f"W: 2015-2025 | I: {iterations} | S/year: {samples} | Snapback: {snapback_interval}", flush=True)
    print(f"T (Start): {temp_sa:.4f} | Jitter: {eff_jitter:.1f}x | {label}: {acc_reward:,} | Alpha: 0.9999", flush=True)
    print(f"Initial - Fit: {current_fitness:.2f} | ESPN_Avg: {current_avg:.2f} | ESPN_Max: {current_max:.2f} | Champ: {current_acc*100:.2f}%", flush=True)
    print("===============================================================================\n", flush=True)

    # Signal handling for graceful exit
    def signal_handler(sig, frame):
        print(f"\nSignal {sig} received. Saving checkpoint and exiting...")
        best_metrics = {"sa_fitness": best_fitness, "espn_average": best_avg, "espn_max": best_max, "accuracy": best_acc}
        state_mgr.save(current_weights, best_weights, temp_sa, i, best_metrics)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        last_best_iteration = start_iter
        stagnation_limit = iterations // 5

        for i in range(start_iter, iterations):
            # GEOMETRIC COOLING (Phase 27)
            alpha = 0.9999
            temp_sa *= alpha
            
            # Cyclic Re-heating: Temperature spikes at each snapback interval
            cycle_progress = (i % snapback_interval) / snapback_interval
            reheat_boost = 1.0 - (cycle_progress * 0.9)
            effective_temp = max(0.01, temp_sa * reheat_boost)
            
            # Dynamic Jitter (Phase 45: Enhanced exploration for Perfect mode)
            effective_jitter = jitter_scale * (2.0 if mode == "perfect" else 1.0)
            new_params = vars(current_weights).copy()
            fields = list(new_params.keys())
            
            # Phase 106: Cap k to ensure we don't sample more than available fields
            k = min(len(fields), max(2, int(len(fields) * (0.1 + 0.2 * effective_temp))))
            jitter_targets = random.sample(fields, k=k)
            
            for field in jitter_targets:
                val = new_params[field]
                if isinstance(val, (int, float)):
                    magnitude = max(0.1, abs(val) * (0.1 + 0.5 * effective_temp) * effective_jitter)
                    step = random.uniform(-magnitude, magnitude)
                    new_val = val + step
                    
                    if field == "seed_weight": new_params[field] = max(0.001, min(0.3, new_val))
                    elif field == "defense_premium": new_params[field] = max(1.0, min(50.0, new_val))
                    elif field == "base_volatility": new_params[field] = max(0.0, min(1.0, new_val))
                    elif "pct" in field or "rate" in field: new_params[field] = max(0, min(100, new_val))
                    else: new_params[field] = max(0, new_val)

            new_weights = SimulationWeights(**new_params)
            metrics = cross_validate_weights(new_weights, mode=mode, samples=samples)
            new_fitness = metrics["sa_fitness"]
            new_avg = metrics["espn_average"]
            new_acc = metrics["accuracy"]
            new_max = metrics["espn_max"]
            
            if new_fitness > current_fitness:
                current_weights = new_weights
                current_fitness = new_fitness
                
                if new_fitness > best_fitness:
                    best_weights = new_weights
                    best_fitness = new_fitness
                    best_avg = new_avg
                    best_acc = new_acc
                    best_max = new_max
                    last_best_iteration = i
                    
                    print_progress(mode, "⭐ NEW BEST!", i, iterations, start_iter, start_time, best_fitness, best_avg, best_max)
                    # For Perfect mode, emphasize if we hit a serious tail
                    if mode == "perfect" and best_max > 1000:
                        print(f"  >>> 🔥 HIGH-VALUE TAIL DISCOVERED! Peak: {best_max:.0f}/1920", flush=True)
                    
                    save_weights(best_weights, best_fitness, best_avg, best_acc, best_max, mode=mode)
                    # Force checkpoint on every new best (Phase 37)
                    best_metrics = {"sa_fitness": best_fitness, "espn_average": best_avg, "espn_max": best_max, "accuracy": best_acc}
                    state_mgr.save(current_weights, best_weights, temp_sa, i, best_metrics)
            else:
                delta = new_fitness - current_fitness
                accept_prob = math.exp(delta / max(0.01, 50.0 * effective_temp))
                if random.random() < accept_prob:
                    current_weights = new_weights
                    current_fitness = new_fitness
            
            # Checkpoint every 100 iterations or on heartbeat
            if i % 100 == 0 or i % heartbeat_interval == 0:
                best_metrics = {"sa_fitness": best_fitness, "espn_average": best_avg, "espn_max": best_max, "accuracy": best_acc}
                state_mgr.save(current_weights, best_weights, temp_sa, i, best_metrics)

            # STAGNATION BREAK
            if i - last_best_iteration > stagnation_limit and i > 5000:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] 🛑 STAGNATION BREAK: No improvement for {i - last_best_iteration} iterations. Exiting early.")
                break

            # SNAPBACK
            if i > 0 and i % snapback_interval == 0:
                current_weights = best_weights
                current_fitness = best_fitness
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] 🦾 [{mode.upper()}] [{i+1}] SNAPBACK (SA_Fit: {best_fitness:.2f})", flush=True)

            # HEARTBEAT (User-Requested Format)
            if i % heartbeat_interval == 0:
                print_progress(mode, "HEARTBEAT", i, iterations, start_iter, start_time, best_fitness, best_avg, best_max)

        # Only cleanup if we finish all iterations naturally (Phase 37)
        state_mgr.cleanup()

    finally:
        save_weights(best_weights, best_fitness, best_avg, best_acc, best_max, mode=mode)
        print("\n=======================================================", flush=True)
        print(f"Final Peak SA Fitness: {best_fitness:.2f}", flush=True)
        print(f"Final ESPN Average: {best_avg:.2f} | ESPN Max: {best_max:.2f}", flush=True)
        print("Optimization Complete.", flush=True)
        print("=======================================================", flush=True)

def save_weights(weights, fitness, avg, acc, peak, mode="unknown"):
    try:
        # 1. Save Session-Specific Last Best (Phase 37)
        json_path = Path(f"agents/optimization/last_best_weights_{mode}.json")
        data = dataclasses.asdict(weights)
        meta = {
            "sa_fitness": fitness,
            "espn_average": avg,
            "espn_max": peak,
            "accuracy": acc,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        data["_metadata"] = meta
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        # 2. Sync to Master Gold Standard (Phase 107: Auto-Sync)
        gold_path = Path("agents/optimization/gold_standard.json")
        for attempt in range(5):
            try:
                if gold_path.exists():
                    with open(gold_path, "r") as f:
                        gold_data = json.load(f)
                    
                    ui_key = {"balanced": "max_balanced", "perfect": "max_perfect", "average": "max_avg"}.get(mode)
                    if ui_key:
                        gold_data[ui_key] = {
                            "weights": dataclasses.asdict(weights),
                            "meta": {
                                "mode": mode,
                                "fitness": fitness,
                                "avg_score": avg,
                                "espn_max": peak,
                                "timestamp": meta["timestamp"]
                            }
                        }
                        # Atomic Write (Phase 112: PID Isolation / Prevent JSON Corruption)
                        temp_gold = gold_path.with_suffix(f".tmp.{os.getpid()}")
                        with open(temp_gold, "w") as f:
                            json.dump(gold_data, f, indent=2)
                        os.replace(temp_gold, gold_path)
                    break # Success!
            except Exception as e:
                if attempt < 4:
                    time.sleep(0.1 * (attempt+1)) # Exponential backoff
                    continue
                logging.error(f"✨ [{mode.upper()}] Save to Gold Standard failed after 5 attempts: {e}")

    except Exception as e:
        logging.error(f"Save failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["balanced", "average", "perfect"], default="balanced")
    parser.add_argument("--jitter-scale", type=float, default=1.0)
    # parser.add_argument("--iterations", type=int) # Removed to ensure rigid topology
    parser.add_argument("--load-state", type=str)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    if args.dry_run:
        config = MODE_CONFIGS[args.mode]
        res = cross_validate_weights(SimulationWeights(), mode=args.mode, samples=config["sample_count"])
        fit, avg, acc = res["sa_fitness"], res["espn_average"], res["accuracy"]
        print(f"Baseline Fitness: {fit:.2f} | Avg: {avg:.2f} | Champ: {acc*100:.1f}%")
    else:
        optimize_simulated_annealing(
            mode=args.mode, 
            jitter_scale=args.jitter_scale,
            iterations=None, # Use rigid MODE_CONFIGS
            load_state=args.load_state,
            resume=args.resume,
            restart=args.restart
        )
