import time
import subprocess
import json
import os
import logging
import threading
from datetime import datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.v2025_tuner import get_v2025_adjustments

# Setup logging with timestamp
log_dir = Path("agents/optimization")
log_dir.mkdir(parents=True, exist_ok=True)
run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"autonomous_optimizer_{run_timestamp}.log"
heartbeat_file = log_dir / "heartbeat.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def log_heartbeat():
    try:
        with open(heartbeat_file, "a") as f:
            f.write(f"HEARTBEAT | {datetime.now().isoformat()} | Optimizer Active\n")
        logging.debug("Heartbeat logged.")
    except Exception as e:
        logging.error(f"Heartbeat failed: {e}")

def heartbeat_monitor(stop_event):
    """Threaded monitor to log heartbeats every 5 minutes."""
    while not stop_event.is_set():
        log_heartbeat()
        for _ in range(300):
            if stop_event.is_set(): break
            time.sleep(1)

def promote_weights(mode, fitness=None, avg=None, acc=None, iteration=None):
    gold_path = Path("agents/optimization/gold_standard.json")
    json_path = Path(f"agents/optimization/last_best_weights_{mode}.json")
    if not json_path.exists(): return
    try:
        time.sleep(0.5)
        with open(json_path, 'r') as f:
            new_weights = json.load(f)
        gold_data = {}
        if gold_path.exists():
            try:
                with open(gold_path, 'r') as f:
                    gold_data = json.load(f)
            except json.JSONDecodeError:
                gold_data = {}
        mode_map = {"balanced": "max_balanced", "perfect": "max_perfect", "average": "max_avg"}
        ui_key = mode_map.get(mode)
        if not ui_key: return
        gold_data[ui_key] = {
            "weights": new_weights,
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "mode": mode,
                "fitness": fitness,
                "avg_score": avg,
                "champ_acc": acc,
                "iteration": iteration
            }
        }
        with open(gold_path, 'w') as f:
            json.dump(gold_data, f, indent=2)
        iter_str = f" [Iter: {iteration}]" if iteration is not None else ""
        logging.info(f"⭐ [{mode.upper()}]{iter_str} PROMOTION SUCCESS: Updated {ui_key} | Fit: {fitness:.2f}")
    except Exception as e:
        logging.error(f"[{mode.upper()}] Promotion failed: {e}")

def run_mode_loop(mode, stop_event, iterations=1000000, load_state=None):
    logging.info(f"[{mode.upper()}] Starting independent loop (Hydration: {load_state if load_state else 'None'})...")
    best_fitness = -float('inf')
    jitter_scale = 1.0
    stagnation_counter = 0

    while not stop_event.is_set():
        try:
            logging.info(f"[{mode.upper()}] Starting sweep ({iterations} iterations, Jitter={jitter_scale:.2f})...")
            cmd = ["python3", "-u", "scripts/optimize_weights.py", "--iterations", str(iterations), "--jitter-scale", f"{jitter_scale:.4f}", "--mode", mode]
            if load_state: cmd += ["--load-state", load_state]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            last_fitness = -1000000
            progress_counter = 0
            while True:
                if stop_event.is_set():
                    process.terminate()
                    break
                line = process.stdout.readline()
                if not line: break
                line_str = line.strip()
                # Check for Progress line
                if "Progress:" in line_str:
                    # Phase 21.6: Prepend [MODE] to ensure clarity during Fork phase
                    logging.info(f"[{mode.upper()}] {line_str}")
                    continue

                if "⭐ NEW BEST!" in line_str:
                    try:
                        fit_val = float(line_str.split("Fit:")[1].split("|")[0].strip())
                        avg_val = float(line_str.split("Avg:")[1].split("|")[0].strip())
                        acc_val = float(line_str.split("Champ:")[1].split("%")[0].strip()) / 100.0
                        # Extract iteration [Iter: x]
                        iter_val = int(line_str.split("[Iter:")[1].split("]")[0].strip())
                        promote_weights(mode, fitness=fit_val, avg=avg_val, acc=acc_val, iteration=iter_val)
                    except Exception as e:
                        logging.error(f"[{mode.upper()}] Parsing failed on line '{line_str}': {e}")
                if "Peak Fitness:" in line_str:
                    try: last_fitness = float(line_str.split(":")[-1].strip())
                    except: pass
            process.wait()
            if process.returncode == 0:
                if last_fitness > best_fitness:
                    best_fitness = last_fitness
                    stagnation_counter = 0
                    jitter_scale = max(0.1, jitter_scale * 0.85)
                else:
                    stagnation_counter += 1
                    if stagnation_counter >= 3:
                        jitter_scale = min(5.0, jitter_scale * 1.5)
                        stagnation_counter = 0
            if "--one-shot" in sys.argv:
                stop_event.set()
                return
            if not stop_event.is_set(): time.sleep(10)
        except Exception as e:
            logging.error(f"[{mode.upper()}] Loop error: {e}")
            time.sleep(30)

def run_pipeline(stop_event):
    start_time = time.time()
    # Check for Stage Skipping (Phase 21.9)
    skip_scout = "--skip-scout" in sys.argv
    
    # 1. SCOUT PHASE (Hydrate from Gold Standard for Phase 21.5)
    # Phase 21.8 SPEED BOOST: Reduced to 125 samples for 4x faster iteration cycles.
    gold_standard = "agents/optimization/gold_standard.json"
    if not skip_scout:
        logging.info("🚀 PIPELINE INITIATED: Scout Phase (Balanced, 250k iterations)")
        logging.info(f"🧬 RE-EVALUATING BASELINE: {gold_standard} (Setting fresh statistical anchor...)")
        run_mode_loop("balanced", stop_event, iterations=250000, load_state=gold_standard)
        if stop_event.is_set(): return
        logging.info("🏁 SCOUT PHASE COMPLETE. Forking...")
    else:
        logging.info("⏭️ SKIPPING SCOUT PHASE: Proceeding directly to Fork Stage.")

    # 2. REFINEMENT / FORK PHASE
    # Adjusted for Cool-Running Concurrent Refinement (Phase 27)
    # Uses 3 cores total (one per mode) for maximum stability on laptops.
    fork_iters = {"balanced": 250000, "average": 100000, "perfect": 500000}
    threads = []
    
    # Determined which baseline to use (Refinement vs Forking)
    if skip_scout:
        logging.info("🔬 REFINEMENT MODE: Starting Balanced, Average, and Perfect concurrently (Cool Mode).")
        seed_path = None # Forces mode-specific refinement from Gold Standard
    else:
        scout_result = Path("agents/optimization/last_best_weights_balanced.json")
        if not scout_result.exists():
            logging.error("Scout result missing and --skip-scout not set. Cannot pipeline.")
            return
        seed_path = str(scout_result)
        logging.info(f"🔱 FORK MODE: Branching average/perfect from balanced baseline: {seed_path}")

    for mode in fork_iters:
        t = threading.Thread(
            target=run_mode_loop, 
            args=(mode, stop_event), 
            kwargs={"iterations": fork_iters[mode], "load_state": seed_path}, 
            daemon=True
        )
        t.start()
        threads.append(t)
    
    for t in threads: t.join()
    logging.info(f"🏆 PIPELINE COMPLETE. Total Time: {int(time.time() - start_time)}s")

def main():
    stop_event = threading.Event()
    threading.Thread(target=heartbeat_monitor, args=(stop_event,), daemon=True).start()
    if "--pipeline" in sys.argv:
        run_pipeline(stop_event)
    else:
        for mode in ["balanced", "perfect", "average"]:
            threading.Thread(target=run_mode_loop, args=(mode, stop_event), daemon=True).start()
            time.sleep(2)
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt: stop_event.set()

if __name__ == "__main__":
    main()
