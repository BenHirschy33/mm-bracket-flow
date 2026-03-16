
import os
import time
import subprocess
import json
import logging
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC_FILE = os.path.join(BASE_DIR, "docs", "agent_sync.json")
STATUS_FILE = os.path.join(BASE_DIR, "docs", "optimization_status.txt")
INDICATORS_FILE = os.path.join(BASE_DIR, "docs", "spec", "v2025_indicators.json")
OPTIMIZE_SCRIPT = os.path.join(BASE_DIR, "scripts", "optimize_weights.py")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "autonomous_optimizer.log")),
        logging.StreamHandler()
    ]
)

def log_heartbeat(iteration, fitness, avg_score):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_content = f"""OPTIMIZATION HEARTBEAT
TIMESTAMP: {timestamp}
STATUS: Deep Sweep Active
CURRENT CYCLE ITERATION: {iteration}
CURRENT BEST FITNESS: {fitness}
CURRENT AVG SCORE: {avg_score}

SYNC STATUS: Connected
MANAGER INSTRUCTION: {get_manager_instruction()}
"""
    with open(STATUS_FILE, "w") as f:
        f.write(status_content)
    logging.info(f"Heartbeat logged: Fitness {fitness}")

def get_manager_instruction():
    try:
        if os.path.exists(SYNC_FILE):
            with open(SYNC_FILE, "r") as f:
                data = json.load(f)
                return data.get("manager_instruction", "No instruction found")
    except Exception as e:
        return f"Error reading sync: {e}"
    return "Ready"

def run_sweep():
    logging.info("Starting new 10k cycle...")
    
    # Check for shifted parameters in indicators
    # For now, we just pass the default iterations
    cmd = ["python", OPTIMIZE_SCRIPT, "--iterations", "10000"]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        cwd=BASE_DIR
    )

    last_heartbeat = time.time()
    current_best_fitness = "N/A"
    current_avg_score = "N/A"
    iteration_count = 0

    for line in process.stdout:
        print(line, end="") # Echo to log
        
        # Parse output for progress
        # Example: [105] New Global Best! Fitness: 187.96 | Avg: 229.88 | Temp: 895
        if "New Global Best!" in line:
            try:
                parts = line.split("|")
                fitness_part = parts[0].split("Fitness:")[1].strip()
                avg_part = parts[1].split("Avg:")[1].strip()
                current_best_fitness = fitness_part
                current_avg_score = avg_part
            except:
                pass
        
        if "Iter" in line:
            try:
                iteration_count = line.split("/")[0].split("Iter")[1].strip()
            except:
                pass

        # Update heartbeat every 5 minutes
        if time.time() - last_heartbeat > 300:
            log_heartbeat(iteration_count, current_best_fitness, current_avg_score)
            last_heartbeat = time.time()

    process.wait()
    logging.info("Cycle completed.")

def main_loop():
    logging.info("Autonomous Optimization Agent Online.")
    while True:
        try:
            # Sync
            instruction = get_manager_instruction()
            logging.info(f"Sync complete. Instruction: {instruction}")
            
            # Execute
            run_sweep()
            
            # Self-Direct: Check indicators before next run
            if os.path.exists(INDICATORS_FILE):
                logging.info("Re-reading v2025_indicators.json for next cycle shift...")
            
            logging.info("Waiting 10 seconds before next infinite loop restart...")
            time.sleep(10)
            
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
