import subprocess
import os
import time
import signal
from pathlib import Path

def relaunch():
    print("🏔️ NCAA Optimizer Smart Relaunching...")
    
    # 1. Find and kill existing optimizer processes safely
    try:
        # Get PIDs of BOTH the manager and the individual mode workers
        targets = ['autonomous_optimizer.py', 'optimize_weights.py']
        pids_found = []
        
        for target in targets:
            result = subprocess.run(['pgrep', '-f', target], capture_output=True, text=True)
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    pids_found.append(pid)
                    print(f"🛑 Stopping existing process {pid} ({target})...")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass # Already gone
        
        if pids_found:
            time.sleep(3)
            
    except Exception as e:
        print(f"ℹ️ No existing processes to stop. ({e})")

    # 2. Launch the new stack in the background
    log_file = "optimize_run.log"
    print(f"🚀 Launching Parallel Autonomous V5 (1M One-Shot)...")
    print(f"📝 Logging to: {log_file}")
    
    # Standard background launch (relying on system 'prevent sleep' settings)
    with open(log_file, "a") as f:
        # python3 -u scripts/autonomous_optimizer.py --one-shot: stops after 1M iters
        subprocess.Popen(
            ["python3", "-u", "scripts/autonomous_optimizer.py", "--one-shot"],
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
    
    print("🦾 Optimizer is now running in the background.")
    print("✅ TIP: Run 'tail -f optimize_run.log' to watch progress.")

if __name__ == "__main__":
    relaunch()
