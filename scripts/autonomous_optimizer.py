import time
import subprocess
import json
import os
import logging
import threading
from datetime import datetime
from pathlib import Path
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

def promote_weights(best_weights_file):
    """
    Placeholder for future auto-promotion logic.
    Could automatically update core/config.py if fitness improves significantly.
    """
    logging.info(f"Checking {best_weights_file} for potential promotion...")

def main():
    logging.info("Initializing Autonomous Optimization Protocol V2...")
    
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=heartbeat_monitor, args=(stop_event,), daemon=True)
    monitor_thread.start()
    
    try:
        while True:
            # 1. Load 2025 Adjustments
            adjustments = get_v2025_adjustments()
            logging.info(f"Loaded {len(adjustments)} 2025 indicators from research.")
            
            # 2. Run Sweep (Infinite Loop)
            # Increase iterations for deeper research
            iterations = 50000 
            logging.info(f"Starting sweep ({iterations} iterations)...")
            
            # We call the refined optimize_weights.py
            cmd = ["python3", "scripts/optimize_weights.py", "--iterations", str(iterations)]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Stream output to log (filtering for bests)
            while True:
                line = process.stdout.readline()
                if not line: break
                if "BEST" in line.upper() or "GLOBAL" in line.upper():
                    logging.info(f"OPTIMIZER: {line.strip()}")
            
            process.wait()
            
            if process.returncode == 0:
                logging.info("Sweep complete. Checking for promotion...")
                promote_weights("agents/optimization/best_weights.txt")
            else:
                error_msg = process.stderr.read()
                logging.error(f"Sweep failed with code {process.returncode}: {error_msg}")
            
            logging.info("Cycle complete. Cooldown (60s) before next sweep...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        logging.info("Stopping Autonomous Optimizer...")
        stop_event.set()
        monitor_thread.join(timeout=2)

if __name__ == "__main__":
    main()
