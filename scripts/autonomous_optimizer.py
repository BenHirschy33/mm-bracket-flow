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

# Setup logging
log_dir = Path("agents/optimization")
log_dir.mkdir(parents=True, exist_ok=True)
heartbeat_file = log_dir / "heartbeat.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "autonomous_optimizer.log"),
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
        # Sleep in 1s chunks to allow faster termination
        for _ in range(300):
            if stop_event.is_set(): break
            time.sleep(1)

def promote_weights(mode, fitness=None, avg=None, acc=None):
    """
    Automates the promotion of optimized weights to the gold_standard.json 
    for UI consumption.
    """
    gold_path = Path("agents/optimization/gold_standard.json")
    json_path = Path(f"agents/optimization/last_best_weights_{mode}.json")
    
    if not json_path.exists():
        return
        
    try:
        with open(json_path, 'r') as f:
            new_weights = json.load(f)
            
        gold_data = {}
        if gold_path.exists():
            try:
                with open(gold_path, 'r') as f:
                    gold_data = json.load(f)
            except json.JSONDecodeError:
                gold_data = {}
                
        # Map mode to UI keys
        mode_map = {
            "balanced": "max_balanced",
            "perfect": "max_perfect",
            "average": "max_avg"
        }
        ui_key = mode_map.get(mode)
        if not ui_key: return
        
        gold_data[ui_key] = {
            "weights": new_weights,
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "mode": mode,
                "fitness": fitness,
                "avg_score": avg,
                "champ_acc": acc
            }
        }
        
        with open(gold_path, 'w') as f:
            json.dump(gold_data, f, indent=2)
        
        stats_str = f" | Fit: {fitness:.2f}" if fitness else ""
        logging.info(f"[{mode.upper()}] PROMOTION SUCCESS: Updated {ui_key}{stats_str}")
    except Exception as e:
        logging.error(f"[{mode.upper()}] Promotion failed: {e}")

def run_mode_loop(mode, stop_event):
    """Independent loop for a specific optimization mode."""
    logging.info(f"[{mode.upper()}] Starting independent loop...")
    best_fitness = -float('inf')
    jitter_scale = 1.0
    stagnation_counter = 0

    while not stop_event.is_set():
        try:
            # 1. Load 2025 Adjustments
            adjustments = get_v2025_adjustments()
            
            # 2. Sweep iterations (High-precision V5)
            iterations = 1000000 
            logging.info(f"[{mode.upper()}] Starting sweep ({iterations} iterations, Jitter={jitter_scale:.2f})...")
            
            # Use --workers 3 to manage 11-core load (3 modes * 3 workers = 9 + overhead)
            cmd = [
                "python3", "-u", "scripts/optimize_weights.py", 
                "--iterations", str(iterations),
                "--jitter-scale", f"{jitter_scale:.4f}",
                "--mode", mode
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            last_fitness = -1000000
            while True:
                if stop_event.is_set():
                    process.terminate()
                    break
                line = process.stdout.readline()
                if not line: break
                line_str = line.strip()
                if "BEST" in line_str.upper() or "GLOBAL" in line_str.upper():
                    logging.info(f"[{mode.upper()}] {line_str}")
                    # Parse stats from string like: "[balanced] [6] ⭐ NEW BEST! Fit: -88.17 | Avg: 451.0 | Champ: 30.3%"
                    try:
                        fit_val = float(line_str.split("Fit:")[1].split("|")[0].strip())
                        avg_val = float(line_str.split("Avg:")[1].split("|")[0].strip())
                        acc_val = float(line_str.split("Champ:")[1].split("%")[0].strip()) / 100.0
                        promote_weights(mode, fitness=fit_val, avg=avg_val, acc=acc_val)
                    except (IndexError, ValueError):
                        promote_weights(mode)
                
                if "Final Peak Fitness:" in line_str:
                    try:
                        last_fitness = float(line_str.split(":")[-1].strip())
                    except ValueError:
                        pass
            
            process.wait()
            
            if process.returncode == 0:
                logging.info(f"[{mode.upper()}] Sweep complete. Reported Fitness: {last_fitness}")
                
                if last_fitness > best_fitness:
                    logging.info(f"[{mode.upper()}] 🚀 NEW BEST: {last_fitness} (Prev: {best_fitness})")
                    best_fitness = last_fitness
                    stagnation_counter = 0
                    # Fine-tune: reduce jitter slightly if we found a good spot
                    jitter_scale = max(0.1, jitter_scale * 0.85)
                    # Redundant call at end of sweep for safety
                    promote_weights(mode)
                else:
                    stagnation_counter += 1
                    logging.info(f"[{mode.upper()}] No improvement. Stagnation Counter: {stagnation_counter}")
                    
                    if stagnation_counter >= 3:
                        # Re-heat: increase jitter to escape local maxima
                        jitter_scale = min(5.0, jitter_scale * 1.5)
                        logging.warning(f"[{mode.upper()}] STAGNATION DETECTED. Re-heating system (Jitter -> {jitter_scale:.2f})")
                        stagnation_counter = 0
                    else:
                        # Gradual increase if no immediate improvement
                        jitter_scale = min(2.0, jitter_scale * 1.05)
            
            else:
                if not stop_event.is_set():
                    error_msg = process.stderr.read()
                    logging.error(f"[{mode.upper()}] Sweep failed with code {process.returncode}: {error_msg}")
            
            if not stop_event.is_set():
                time.sleep(30)
                
        except Exception as e:
            logging.error(f"[{mode.upper()}] Loop encountered error: {e}")
            time.sleep(60)

def main():
    logging.info("Initializing Parallel Autonomous Optimization Protocol V4...")
    
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=heartbeat_monitor, args=(stop_event,), daemon=True)
    monitor_thread.start()
    
    modes = ["balanced", "perfect", "average"]
    threads = []
    
    for mode in modes:
        t = threading.Thread(target=run_mode_loop, args=(mode, stop_event), daemon=True)
        t.start()
        threads.append(t)
        # Stagger starts slightly
        time.sleep(5)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping Parallel Autonomous Optimizer...")
        stop_event.set()
        for t in threads:
            t.join(timeout=2)
        monitor_thread.join(timeout=2)

if __name__ == "__main__":
    main()
